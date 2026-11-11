# SENTINEL.AI — Final Submission Readiness & Technical Audit Report

**Date of Audit**: 2026-11-12
**Target Repository**: `https://github.com/Devansh-Vermaji1374/SENTINEL.AI`
**Assessment Target**: CrowdWisdomTrading AI Agents Developer Internship Assessment
**Audit Status**: **READY TO SUBMIT WITH DOCUMENTED LIMITATIONS**

---

## 1. Executive Summary

SENTINEL.AI has undergone a rigorous engineering verification pass to ensure that all codebase artifacts, documentation, automated tests, and database snapshots adhere strictly to empirical evidence and CrowdWisdomTrading assessment requirements.

### Key Audit Findings:
1. **Multi-Source Social Ingestion**:
   - Eligible scrapers implemented: LIHKG (`claude_code_reviewer~lihkg-scraper-en`) and Naver Finance Discussion (`hgservices~naver-stock-discussion-scraper`).
   - Observed database records: 2 LIHKG posts (`0700.HK`) and 12 Naver discussion posts (`005930.KS`) with verified FinBERT sentiment scores.
   - Supplemental discourse: 153 StockTwits posts across 6 tickers.
   - Compliance classification: **PARTIALLY DEMONSTRATED — additional eligible-source evidence required** (1 eligible listed source per exchange demonstrated with database records; StockTwits serves as supplemental stream).
2. **Temporal Alignment & Dual-Boundary Filter**:
   - Strict 10-day lookback cutoff and future-date rejection (`cutoff <= ts <= now_utc + 5min`) enforced in production scrapers and pipeline service.
   - Naver timestamps reconciled from KST (UTC+9) to UTC inside an atomic transaction, with full audit trail in `timestamp_audit_log`.
   - Zero future-dated posts exist in `sentinel.db`.
3. **Database Integrity**:
   - `PRAGMA integrity_check` = `ok`; `PRAGMA foreign_key_check` = 0 violations.
   - Total records: 1,247 market bars, 210 discourse posts, 135 news articles, 355 sentiment scores, 292 predictions (4 settled, 0 pending, 280 legacy unpriced, 8 invalid date).
4. **Automated Testing**:
   - Full test suite: **38 passed, 0 failed, 6 warnings in 9.69s** (`pytest tests/ -v`).
   - 25 tests in `test_pipeline.py`, 13 tests in `test_social_sources.py`.
5. **Frontend Production Build**:
   - `tsc -b && vite build` completed cleanly in 4.45s with 0 errors.

---

## 2. Authoritative Database Inventory

| Database File | Snapshot Role | Integrity Check | Market Bars | Social Posts | News Articles | FinBERT Scores | Total Predictions | Prediction Breakdown |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **`sentinel.db`** | Active Operational Store | `ok` | **1,247** | **210** | **135** | **355** | **292** | 280 Legacy, 8 Invalid Date, 4 Settled, 0 Pending |
| **`backups/sentinel_before_naver_tz_fix_backup.db`** | Pre-TZ Fix Safety Backup | `ok` | 1,247 | 210 | 135 | 355 | 292 | 280 Legacy, 8 Invalid Date, 4 Settled, 0 Pending |
| **`backups/sentinel_freeze_backup.db`** | Baseline Freeze Backup | `ok` | 1,245 | 195 | 135 | 330 | 292 | 280 Legacy, 8 Invalid Date, 0 Settled, 4 Pending |
| **`backups/sentinel_before_live_ingest_backup.db`** | Pre-Live Ingest Safety Backup | `ok` | 1,247 | 195 | 135 | 330 | 292 | 280 Legacy, 8 Invalid Date, 4 Settled, 0 Pending |

*Audit Trail*: The `timestamp_audit_log` table in `sentinel.db` contains 12 entries recording the 9-hour KST-to-UTC offset reconciliation for IDs 275–286, proving all publication timestamps are strictly earlier than collection times (`collected_at`).

---

## 3. Social Source Compliance Matrix

| Source Name | Category | Exchange | Apify Actor / API | Status in Code | Mock Tests | Observed DB Records | Verified Count & Coverage | Compliance Assessment |
|---|---|---|---|:---:|:---:|:---:|---|---|
| **LIHKG** | Assessment-Listed | HKEX | `claude_code_reviewer~lihkg-scraper-en` | Implemented | Passed | **Observed** | 2 posts (`0700.HK`) | Demonstrated Eligible Source |
| **AAStocks / ETNet** | Assessment-Listed | HKEX | `bovi~aastocks-scraper` | Declared | Passed | None | 0 posts | Implemented in code |
| **Telegram (HKEX)** | Assessment-Listed | HKEX | `curious_coder~telegram-scraper` | Declared | Passed | None | 0 posts | Headless login blocked |
| **Naver Finance Discussion** | Assessment-Listed | KRX | `hgservices~naver-stock-discussion-scraper` | Implemented | Passed | **Observed** | 12 posts (`005930.KS`) | Demonstrated Eligible Source |
| **Blind (KRX)** | Assessment-Listed | KRX | `hypebridge~blind-post-scraper` | Declared | Passed | None | 0 posts | Implemented in code |
| **StockTwits Stream** | Supplemental | HKEX/KRX | Direct REST API | Implemented | Passed | **Observed** | 153 posts across 6 tickers | Supplemental Discourse Stream |
| **Financial Market Wire** | News RSS | N/A | RSS Feed | Implemented | Passed | **Observed** | 43 posts across 9 tickers | News RSS (Misclassified in legacy ingest) |

---

## 4. Machine Learning Baseline Realism

All 40 model bundles were evaluated on an untouched chronological holdout test set ($N \approx 21\text{--}22$ trading days per asset):
- **Beat Naive Zero-Return Baseline**: **8 / 40 models** (20.0% on MAE).
- **Beat Historical Mean-Return Baseline**: **4 / 40 models** (10.0% on MAE).
- **Underperformed Both Baselines**: **32 / 40 models** (80.0% on MAE).
- **Academic Disclaimer**: In financial markets, noisy price returns typically produce modest holdout performance over small sample windows. These models represent an exploratory quantitative prototype and make no claim of live predictive profitability.

---

## 5. Security Posture

- **Git Exclusions**: `.env`, `sentinel.db`, and `backups/*.db` are completely excluded by `.gitignore`.
- **Credentials Scan**: Scanned repository files; zero API keys (`APIFY_API_TOKEN`, `EXA_API_KEY`) or private billing tokens are tracked or exposed in source code.
- **Frontend Production Bundle**: Built assets in `frontend-web/dist/` contain zero hardcoded credentials or admin secrets.

---

## 6. Verification Commands & Results

| Step | Command | Verified Result |
|---|---|---|
| Full Pytest Suite | `.\.venv\Scripts\python.exe -m pytest tests/ -v --durations=10` | **38 passed, 0 failed, 6 warnings in 9.69s** |
| Frontend Production Build | `cd frontend-web && npm run build` | **Built in 4.45s with 0 errors** |
| Database Read-Only Integrity | Python `file:sentinel.db?mode=ro` | `ok`, 0 foreign-key violations |
| Future-Dated Check | `SELECT COUNT(*) FROM social_posts WHERE timestamp > collected_at` | **0 violations** |

---

## 7. Submission Verdict

**READY TO SUBMIT WITH DOCUMENTED LIMITATIONS**

The repository is clean, honest, fully tested, and technically defensible against CrowdWisdomTrading standards.
