"""Timestamp alignment utilities for SENTINEL AI.

Maps social-media and news timestamps to the relevant trading session
so that sentiment data can be joined to market data correctly.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import pandas as pd
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class TimestampAligner:
    """Align social / news timestamps to exchange trading sessions.

    Each exchange defines a local timezone and session open/close times.
    Timestamps are mapped to the *relevant* trading day according to:

    * **During trading hours** → that calendar day.
    * **Before market open** → that calendar day.
    * **After market close** → next trading day.
    * **Weekend / holiday** → next trading day.
    """

    # Timezone per exchange.
    EXCHANGE_TIMEZONES: dict[str, str] = {
        "HKEX": "Asia/Hong_Kong",
        "KRX": "Asia/Seoul",
    }

    # Trading session hours (local time).  Extend as needed.
    EXCHANGE_SESSIONS: dict[str, tuple[time, time]] = {
        "HKEX": (time(9, 30), time(16, 0)),   # 09:30 – 16:00 HKT
        "KRX": (time(9, 0), time(15, 30)),    # 09:00 – 15:30 KST
    }

    # Known public holidays (YYYY-MM-DD).  Extend each year.
    # Only a small sample is provided; production should use a calendar API.
    EXCHANGE_HOLIDAYS: dict[str, set[date]] = {
        "HKEX": set(),
        "KRX": set(),
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def align_to_trading_day(
        self,
        timestamp: datetime,
        exchange: str,
    ) -> date:
        """Map a timestamp to the relevant trading day.

        Args:
            timestamp: A timezone-aware datetime.
            exchange: Exchange identifier (e.g. ``"HKEX"``, ``"KRX"``).

        Returns:
            The :class:`date` of the relevant trading session.

        Raises:
            ValueError: If *timestamp* is naïve or *exchange* is unknown.
        """
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")

        tz_name = self._get_tz(exchange)
        local_tz = ZoneInfo(tz_name)
        local_dt = timestamp.astimezone(local_tz)

        _, session_close = self.EXCHANGE_SESSIONS.get(
            exchange, (time(9, 0), time(16, 0))
        )

        candidate = local_dt.date()

        # If after market close, move to next calendar day.
        if local_dt.time() > session_close:
            candidate += timedelta(days=1)

        # Roll forward past weekends and holidays.
        candidate = self._next_trading_day(candidate, exchange)

        return candidate

    def get_trading_days(
        self,
        start_date: date,
        end_date: date,
        exchange: str,
    ) -> list[date]:
        """Return a list of trading days between *start_date* and *end_date* (inclusive).

        Excludes weekends (Saturday, Sunday) and known holidays for the
        given exchange.

        Args:
            start_date: First date of the range.
            end_date: Last date of the range.
            exchange: Exchange identifier.

        Returns:
            Sorted list of trading :class:`date` objects.
        """
        holidays = self.EXCHANGE_HOLIDAYS.get(exchange, set())
        trading_days: list[date] = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5 and current not in holidays:
                trading_days.append(current)
            current += timedelta(days=1)
        return trading_days

    def align_social_to_market(
        self,
        social_df: pd.DataFrame,
        market_df: pd.DataFrame,
        exchange: str,
    ) -> pd.DataFrame:
        """Align social data to market trading days.

        Adds a ``trading_day`` column to *social_df* by mapping each row's
        timestamp to the relevant trading session.  Rows that cannot be
        aligned (e.g. timestamp is ``NaT``) are dropped.

        Args:
            social_df: DataFrame with a ``timestamp`` column (tz-aware).
            market_df: Market DataFrame used to obtain the valid set of
                trading days.  Must contain a ``date`` column or a date
                index.
            exchange: Exchange identifier.

        Returns:
            A copy of *social_df* with an extra ``trading_day`` column
            and rows filtered to dates present in *market_df*.
        """
        social = social_df.copy()

        if "timestamp" not in social.columns:
            raise ValueError("social_df must contain a 'timestamp' column.")

        # Ensure timestamps are tz-aware datetimes.
        social["timestamp"] = pd.to_datetime(social["timestamp"], utc=True)

        # Map each timestamp.
        social["trading_day"] = social["timestamp"].apply(
            lambda ts: self.align_to_trading_day(ts.to_pydatetime(), exchange)
            if pd.notna(ts)
            else None
        )

        # Drop rows where alignment failed.
        social = social.dropna(subset=["trading_day"])
        social["trading_day"] = pd.to_datetime(social["trading_day"]).dt.date

        # Build set of valid market dates.
        market_dates = self._extract_market_dates(market_df)

        if market_dates:
            social = social[social["trading_day"].isin(market_dates)]

        logger.info(
            "Aligned %d social posts to %d unique trading days.",
            len(social),
            social["trading_day"].nunique(),
        )

        return social.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tz(self, exchange: str) -> str:
        """Resolve exchange to IANA timezone name."""
        tz = self.EXCHANGE_TIMEZONES.get(exchange)
        if tz is None:
            raise ValueError(
                f"Unknown exchange '{exchange}'. "
                f"Supported: {list(self.EXCHANGE_TIMEZONES)}"
            )
        return tz

    def _next_trading_day(self, candidate: date, exchange: str) -> date:
        """Roll a date forward to the next valid trading day."""
        holidays = self.EXCHANGE_HOLIDAYS.get(exchange, set())
        # Safety cap to avoid infinite loop.
        for _ in range(14):
            if candidate.weekday() < 5 and candidate not in holidays:
                return candidate
            candidate += timedelta(days=1)
        return candidate  # fallback

    @staticmethod
    def _extract_market_dates(market_df: pd.DataFrame) -> set[date]:
        """Extract the set of dates present in a market DataFrame."""
        if market_df.empty:
            return set()

        if "date" in market_df.columns:
            return set(pd.to_datetime(market_df["date"]).dt.date)

        if hasattr(market_df.index, "date"):
            return set(market_df.index.date)

        return set()
