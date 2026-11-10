"""Database migration: Add and idempotently backfill persistent prediction status.

Guarantees:
- Never overwrites INVALID_TARGET_DATE or explicitly classified statuses.
- Never resets SETTLED or LEGACY_UNSETTLEABLE records.
- Idempotent across multiple runs: identical state before and after.
- Preserves all historical records, IDs, and fields.
"""
import sqlite3

def run_migration(db_path: str = 'sentinel.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('PRAGMA table_info(predictions)')
    cols = [r[1] for r in c.fetchall()]
    if 'status' not in cols:
        c.execute("ALTER TABLE predictions ADD COLUMN status VARCHAR(50) DEFAULT 'PENDING_SETTLEMENT'")
        print("Added status column to predictions table.")
    else:
        print("status column already exists.")

    # Idempotent classification: Only classify records that do NOT already have a valid explicit status
    # 1. Unclassified legacy records lacking origin_price
    c.execute("""
        UPDATE predictions
        SET status = 'LEGACY_UNSETTLEABLE'
        WHERE (status IS NULL OR status = '')
          AND (origin_price IS NULL OR origin_price <= 0)
    """)

    # 2. Unclassified settled records
    c.execute("""
        UPDATE predictions
        SET status = 'SETTLED'
        WHERE (status IS NULL OR status = '')
          AND settled_at IS NOT NULL
    """)

    # 3. Unclassified valid modern pending records
    c.execute("""
        UPDATE predictions
        SET status = 'PENDING_SETTLEMENT'
        WHERE (status IS NULL OR status = '')
          AND settled_at IS NULL
          AND origin_price IS NOT NULL
          AND origin_price > 0
    """)

    conn.commit()
    c.execute("SELECT status, COUNT(*) FROM predictions GROUP BY status")
    counts = c.fetchall()
    print("Status counts:", counts)
    conn.close()
    return counts

if __name__ == '__main__':
    run_migration()
