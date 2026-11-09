"""Data cleaning and normalisation utilities for SENTINEL AI.

Provides methods to sanitise social-media posts, news articles, and
market OHLCV data before they enter the analytics pipeline.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class DataCleaner:
    """Clean and normalise collected data for downstream consumption.

    All methods are ``@staticmethod`` so the class can be used without
    instantiation while still providing a logical grouping.
    """

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean social / news text for NLP ingestion.

        Applies the following transformations in order:

        1. Unicode NFC normalisation.
        2. URL removal.
        3. HTML entity decoding (``&amp;`` → ``&``).
        4. Strip excessive whitespace.
        5. Remove zero-width / invisible control characters.

        Args:
            text: Raw text string.

        Returns:
            Cleaned text string.
        """
        if not text:
            return ""

        # 1. Normalise unicode
        text = unicodedata.normalize("NFC", text)

        # 2. Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # 3. Basic HTML entity cleanup
        html_entities: dict[str, str] = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
            "&nbsp;": " ",
        }
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)

        # 4. Remove invisible / zero-width characters
        text = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", text)

        # 5. Collapse whitespace
        text = re.sub(r"[\r\n\t]+", " ", text)
        text = re.sub(r"\s{2,}", " ", text)

        return text.strip()

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def remove_duplicate_posts(
        posts: list[dict[str, Any]],
        key_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Remove duplicate posts based on key fields or content hash.

        Duplicates are detected by computing a SHA-256 digest over the
        concatenation of *key_fields*.  When *key_fields* is ``None``
        the method falls back to ``["url"]``, then ``["text"]``.

        Args:
            posts: List of post dicts.
            key_fields: Fields to use for the uniqueness key.

        Returns:
            De-duplicated list preserving original order.
        """
        if not posts:
            return []

        if key_fields is None:
            # Auto-detect: prefer url, then text
            sample = posts[0]
            if "url" in sample:
                key_fields = ["url"]
            elif "text" in sample:
                key_fields = ["text"]
            else:
                logger.warning(
                    "No key_fields specified and no 'url'/'text' field found; "
                    "returning posts as-is."
                )
                return list(posts)

        seen: set[str] = set()
        unique: list[dict[str, Any]] = []

        for post in posts:
            parts = [str(post.get(f, "")) for f in key_fields]
            digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
            if digest not in seen:
                seen.add(digest)
                unique.append(post)

        removed = len(posts) - len(unique)
        if removed:
            logger.info("Removed %d duplicate posts out of %d.", removed, len(posts))

        return unique

    # ------------------------------------------------------------------
    # Market data cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def clean_market_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean OHLCV market data.

        Steps:
        1. Ensure chronological order by index (or ``date`` column).
        2. Drop rows where *all* OHLCV columns are zero.
        3. Forward-fill missing price columns (weekends/holidays are
           assumed to already be excluded).
        4. Replace negative volumes with NaN, then forward-fill.
        5. Drop any remaining rows with NaN in critical columns.

        Args:
            df: DataFrame with columns ``open``, ``high``, ``low``,
                ``close``, ``volume`` (case-insensitive).

        Returns:
            Cleaned DataFrame.
        """
        if df.empty:
            return df.copy()

        df = df.copy()

        # Normalise column names to lowercase.
        df.columns = [c.lower().strip() for c in df.columns]

        # Ensure chronological order.
        if "date" in df.columns and df.index.name != "date":
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.sort_values("date").reset_index(drop=True)
        else:
            df = df.sort_index()

        ohlcv = ["open", "high", "low", "close", "volume"]
        present = [c for c in ohlcv if c in df.columns]

        if not present:
            logger.warning("No OHLCV columns found in DataFrame.")
            return df

        # Remove rows with all-zero OHLCV values.
        all_zero_mask = (df[present] == 0).all(axis=1)
        if all_zero_mask.any():
            logger.info(
                "Dropping %d rows with all-zero OHLCV.", all_zero_mask.sum()
            )
            df = df[~all_zero_mask]

        # Forward-fill missing prices.
        price_cols = [c for c in ["open", "high", "low", "close"] if c in df.columns]
        if price_cols:
            df[price_cols] = df[price_cols].ffill()

        # Negative volumes → NaN → forward-fill.
        if "volume" in df.columns:
            df.loc[df["volume"] < 0, "volume"] = pd.NA
            df["volume"] = df["volume"].ffill()

        # Drop remaining NaN rows in critical columns.
        df = df.dropna(subset=present)

        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Timestamp normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_timestamp(
        ts: str | int | float | datetime,
        target_tz: str = "UTC",
    ) -> datetime:
        """Convert any timestamp representation to a timezone-aware datetime.

        Supported inputs:
        * ``datetime`` objects (naive → assumed UTC, aware → converted).
        * ISO-8601 strings.
        * Unix epoch seconds (``int`` / ``float``).

        Args:
            ts: Timestamp in any supported format.
            target_tz: IANA timezone name for the output.

        Returns:
            Timezone-aware ``datetime`` in *target_tz*.

        Raises:
            ValueError: If *ts* cannot be parsed.
        """
        tz = ZoneInfo(target_tz)

        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                # Assume UTC for naïve datetimes.
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(tz)

        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz)

        if isinstance(ts, str):
            # Try ISO-8601 first (handles most cases).
            try:
                parsed = datetime.fromisoformat(ts)
            except ValueError:
                # Fallback: pandas is very lenient.
                parsed = pd.Timestamp(ts).to_pydatetime()

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(tz)

        raise ValueError(f"Unsupported timestamp type: {type(ts).__name__}")
