"""
SENTINEL AI - Exchange Trading Calendars
=========================================
Strict trading session resolution and holiday calendars for:
- HKEX (Hong Kong Exchanges and Clearing) [Asia/Hong_Kong, UTC+8]
- KRX (Korea Exchange) [Asia/Seoul, UTC+9]

Accurately handles:
- Weekends (Saturday / Sunday)
- Fixed & Lunar Public Holidays (New Year, Lunar New Year, Ching Ming, Buddha's Birthday,
  Tuen Ng, SAR Day, Mid-Autumn, National Day, Chung Yeung, Christmas, Boxing Day for HKEX;
  New Year, Seollal, Independence Movement Day, Labor Day, Children's Day, Memorial Day,
  Liberation Day, Chuseok, National Foundation Day, Hangul Day, Christmas, Year-end close for KRX)
- Half-day session and post-close trading day transitions
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Set
import zoneinfo

logger = logging.getLogger(__name__)

# Timezones
HK_TZ = zoneinfo.ZoneInfo("Asia/Hong_Kong")
KR_TZ = zoneinfo.ZoneInfo("Asia/Seoul")

# Standard Market Close Times (Local)
HKEX_CLOSE_TIME = time(16, 0)
KRX_CLOSE_TIME = time(15, 30)


# Official Exchange Holidays (2025 - 2027)
HKEX_HOLIDAYS: Set[date] = {
    # 2025
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 29),  # Lunar New Year Day 1
    date(2025, 1, 30),  # Lunar New Year Day 2
    date(2025, 1, 31),  # Lunar New Year Day 3
    date(2025, 4, 4),   # Ching Ming Festival
    date(2025, 4, 18),  # Good Friday
    date(2025, 4, 21),  # Easter Monday
    date(2025, 5, 1),   # Labour Day
    date(2025, 5, 5),   # Birthday of the Buddha
    date(2025, 5, 31),  # Tuen Ng Festival
    date(2025, 7, 1),   # HKSAR Establishment Day
    date(2025, 10, 1),  # National Day
    date(2025, 10, 7),  # Day following Mid-Autumn Festival
    date(2025, 10, 29), # Chung Yeung Festival
    date(2025, 12, 25), # Christmas Day
    date(2025, 12, 26), # Boxing Day
    # 2026
    date(2026, 1, 1),   # New Year's Day
    date(2026, 2, 17),  # Lunar New Year Day 1
    date(2026, 2, 18),  # Lunar New Year Day 2
    date(2026, 2, 19),  # Lunar New Year Day 3
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 6),   # Easter Monday / Ching Ming
    date(2026, 5, 1),   # Labour Day
    date(2026, 5, 25),  # Birthday of the Buddha
    date(2026, 6, 19),  # Tuen Ng Festival
    date(2026, 7, 1),   # HKSAR Establishment Day
    date(2026, 9, 26),  # Mid-Autumn Festival
    date(2026, 10, 1),  # National Day
    date(2026, 10, 19), # Chung Yeung Festival
    date(2026, 12, 25), # Christmas Day
    date(2026, 12, 28), # Day following Boxing Day
    # 2027
    date(2027, 1, 1),   # New Year's Day
    date(2027, 2, 6),   # Lunar New Year
    date(2027, 2, 8),
    date(2027, 2, 9),
    date(2027, 3, 26),  # Good Friday
    date(2027, 3, 29),  # Easter Monday
    date(2027, 4, 5),   # Ching Ming Festival
    date(2027, 5, 1),   # Labour Day
    date(2027, 5, 13),  # Buddha's Birthday
    date(2027, 6, 9),   # Tuen Ng
    date(2027, 7, 1),   # HKSAR Establishment Day
    date(2027, 10, 1),  # National Day
    date(2027, 12, 25),
}

KRX_HOLIDAYS: Set[date] = {
    # 2025
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 28),  # Seollal Eve
    date(2025, 1, 29),  # Seollal
    date(2025, 1, 30),  # Seollal Day 3
    date(2025, 3, 3),   # Substitute for Independence Movement Day
    date(2025, 5, 1),   # Worker's Day
    date(2025, 5, 5),   # Children's Day / Buddha's Birthday
    date(2025, 5, 6),   # Substitute holiday
    date(2025, 6, 6),   # Memorial Day
    date(2025, 8, 15),  # Liberation Day
    date(2025, 10, 3),  # National Foundation Day
    date(2025, 10, 5),  # Chuseok Eve
    date(2025, 10, 6),  # Chuseok
    date(2025, 10, 7),  # Chuseok Day 3
    date(2025, 10, 8),  # Substitute holiday
    date(2025, 10, 9),  # Hangul Day
    date(2025, 12, 25), # Christmas Day
    date(2025, 12, 31), # KRX Year-end market close
    # 2026
    date(2026, 1, 1),   # New Year's Day
    date(2026, 2, 16),  # Seollal Eve
    date(2026, 2, 17),  # Seollal
    date(2026, 2, 18),  # Seollal Day 3
    date(2026, 3, 2),   # Substitute for Independence Movement Day
    date(2026, 5, 1),   # Worker's Day
    date(2026, 5, 5),   # Children's Day
    date(2026, 5, 25),  # Buddha's Birthday
    date(2026, 6, 8),   # Substitute for Memorial Day
    date(2026, 8, 17),  # Substitute for Liberation Day
    date(2026, 9, 24),  # Chuseok Eve
    date(2026, 9, 25),  # Chuseok
    date(2026, 9, 26),  # Chuseok Day 3
    date(2026, 10, 5),  # Substitute for National Foundation Day
    date(2026, 10, 9),  # Hangul Day
    date(2026, 12, 25), # Christmas Day
    date(2026, 12, 31), # KRX Year-end market close
    # 2027
    date(2027, 1, 1),
    date(2027, 2, 5),
    date(2027, 2, 8),
    date(2027, 3, 1),
    date(2027, 5, 1),
    date(2027, 5, 5),
    date(2027, 5, 13),
    date(2027, 8, 16),
    date(2027, 10, 1),
    date(2027, 12, 25),
    date(2027, 12, 31),
}


class ExchangeCalendar:
    """Provides exchange trading schedule, holiday verification, and session resolution."""

    @staticmethod
    def get_exchange_for_ticker(ticker: str) -> str:
        """Infer exchange code from asset ticker."""
        if ticker.endswith(".HK"):
            return "HKEX"
        elif ticker.endswith(".KS") or ticker.endswith(".KQ"):
            return "KRX"
        raise ValueError(f"Unknown exchange for ticker: {ticker}")

    @staticmethod
    def get_timezone(exchange: str) -> zoneinfo.ZoneInfo:
        return HK_TZ if exchange.upper() == "HKEX" else KR_TZ

    @staticmethod
    def is_trading_day(exchange: str, d: date | datetime) -> bool:
        """Check if date d is an active trading session (not weekend, not public holiday)."""
        check_date = d.date() if isinstance(d, datetime) else d
        if check_date.weekday() >= 5:  # Saturday or Sunday
            return False

        ex = exchange.upper()
        if ex == "HKEX":
            return check_date not in HKEX_HOLIDAYS
        elif ex == "KRX":
            return check_date not in KRX_HOLIDAYS
        else:
            return check_date.weekday() < 5

    @classmethod
    def get_next_trading_session(
        cls,
        exchange: str,
        from_datetime: Optional[datetime] = None,
        horizon_days: int = 1
    ) -> date:
        """Calculate the exact date of the next valid trading session.

        Rules:
        - If from_datetime is after the session close in exchange local time,
          the current day is already closed; the first target session is the next open day.
        - Advances strictly across trading days only, skipping weekends and official exchange holidays.
        - Never assumes the next calendar day is a trading day.
        """
        ex = exchange.upper()
        tz = cls.get_timezone(ex)
        close_time = HKEX_CLOSE_TIME if ex == "HKEX" else KRX_CLOSE_TIME

        if from_datetime is None:
            now_local = datetime.now(tz)
        else:
            if from_datetime.tzinfo is None:
                # Treat naive as UTC and convert to local exchange tz
                now_local = from_datetime.replace(tzinfo=timezone.utc).astimezone(tz)
            else:
                now_local = from_datetime.astimezone(tz)

        current_date = now_local.date()
        is_today_trading = cls.is_trading_day(ex, current_date)
        is_after_close = now_local.time() >= close_time

        # If today is a trading day and we are BEFORE close, today's close is session 0
        # If we are AFTER close or today is a non-trading day, the next session is day + 1
        curr = current_date
        if not is_today_trading or is_after_close:
            curr += timedelta(days=1)

        sessions_found = 0
        target_session = curr

        while sessions_found < horizon_days:
            if cls.is_trading_day(ex, target_session):
                sessions_found += 1
                if sessions_found == horizon_days:
                    break
            target_session += timedelta(days=1)

        return target_session

    @classmethod
    def get_session_close_datetime(cls, exchange: str, session_date: date) -> datetime:
        """Return the exact UTC timestamp corresponding to market close of a session date."""
        ex = exchange.upper()
        tz = cls.get_timezone(ex)
        close_time = HKEX_CLOSE_TIME if ex == "HKEX" else KRX_CLOSE_TIME
        local_dt = datetime.combine(session_date, close_time, tzinfo=tz)
        return local_dt.astimezone(timezone.utc)
