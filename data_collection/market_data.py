"""
SENTINEL AI - Market Data Collector
====================================
Collects historical and real-time OHLCV data from Yahoo Finance
for HKEX and KRX listed assets.

Uses yfinance to pull data, handles international ticker formats
(.HK for Hong Kong, .KS for Korea), and normalizes all timestamps
to UTC for consistent storage.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """Collects market data for configured assets via yfinance.

    Handles HKEX (.HK) and KRX (.KS) ticker formats, converts all
    timestamps to timezone-aware UTC, and returns clean DataFrames
    ready for database insertion.
    """

    # Exchange metadata keyed by ticker suffix
    _EXCHANGE_META: dict[str, dict[str, str]] = {
        ".HK": {"exchange": "HKEX", "tz": "Asia/Hong_Kong", "currency": "HKD"},
        ".KS": {"exchange": "KRX", "tz": "Asia/Seoul", "currency": "KRW"},
    }

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        """Initialise with runtime settings.

        Parameters
        ----------
        settings:
            Dictionary typically loaded from ``config/assets.yaml``.
            Expected keys:
              - ``exchanges``: mapping of exchange configs with ``assets`` lists.
              - ``collection.market_history_months`` (int, default 6).
        """
        if settings is None:
            from config.settings import get_settings
            s = get_settings()
            settings = {
                "exchanges": {k: v.model_dump() for k, v in s.yaml_config.exchanges.items()},
                "collection": s.yaml_config.collection.model_dump(),
            }
        self._settings = settings
        self._exchanges: dict = settings.get("exchanges", {})
        collection_cfg = settings.get("collection", {})
        self._default_months: int = int(collection_cfg.get("market_history_months", 6))

        # Flatten asset list for convenience
        self._all_assets: list[dict[str, Any]] = []
        for _exch_key, exch in self._exchanges.items():
            for asset in exch.get("assets", []):
                self._all_assets.append(asset)

        logger.info(
            "MarketDataCollector initialised – tracking %d assets across %d exchanges",
            len(self._all_assets),
            len(self._exchanges),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect_historical(
        self,
        ticker: str,
        months: int | None = None,
    ) -> pd.DataFrame:
        """Download historical OHLCV data for *ticker*.

        Parameters
        ----------
        ticker:
            Yahoo Finance ticker symbol (e.g. ``0700.HK``, ``005930.KS``).
        months:
            Number of months of history to fetch.  Falls back to the
            configured ``market_history_months`` when *None*.

        Returns
        -------
        pd.DataFrame
            Columns: ``date``, ``open``, ``high``, ``low``, ``close``,
            ``volume``, ``adjusted_close``.  The ``date`` column contains
            timezone-aware UTC timestamps.  An empty DataFrame (with the
            correct columns) is returned when no data is available.
        """
        months = months or self._default_months
        period = f"{months}mo"
        exchange_info = self._exchange_info(ticker)
        exchange_tz = exchange_info.get("tz", "UTC")

        logger.info(
            "Collecting %s of historical data for %s (exchange tz: %s)",
            period,
            ticker,
            exchange_tz,
        )

        empty = self._empty_frame()

        try:
            df: pd.DataFrame = yf.download(
                ticker,
                period=period,
                interval="1d",
                auto_adjust=False,
                progress=False,
            )
        except Exception:
            logger.exception("yfinance download failed for %s", ticker)
            return empty

        if df.empty:
            logger.warning("No data returned by yfinance for %s", ticker)
            return empty

        return self._normalise(df, ticker, exchange_tz)

    def collect_all(self) -> dict[str, pd.DataFrame]:
        """Collect historical data for every configured asset.

        Returns
        -------
        dict[str, pd.DataFrame]
            Mapping of ``ticker -> DataFrame``.
        """
        results: dict[str, pd.DataFrame] = {}
        for asset in self._all_assets:
            ticker: str = asset["ticker"]
            results[ticker] = self.collect_historical(ticker)
        logger.info(
            "Finished collecting data for %d / %d assets",
            sum(1 for v in results.values() if not v.empty),
            len(results),
        )
        return results

    def get_latest_price(self, ticker: str) -> dict[str, Any]:
        """Return the most recent available price point for *ticker*.

        Returns
        -------
        dict
            Keys: ``ticker``, ``date``, ``open``, ``high``, ``low``,
            ``close``, ``volume``, ``adjusted_close``, ``currency``,
            ``exchange``.  Returns an empty dict on failure.
        """
        logger.info("Fetching latest price for %s", ticker)
        exchange_info = self._exchange_info(ticker)

        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="5d")
        except Exception:
            logger.exception("Failed to fetch latest price for %s", ticker)
            return {}

        if hist.empty:
            logger.warning("No recent price data for %s", ticker)
            return {}

        last = hist.iloc[-1]
        idx = hist.index[-1]

        # Ensure timezone-aware UTC
        if hasattr(idx, "tzinfo") and idx.tzinfo is not None:
            ts = idx.tz_convert("UTC")
        else:
            ts = idx.tz_localize("UTC")

        return {
            "ticker": ticker,
            "date": ts.isoformat(),
            "open": float(last.get("Open", 0)),
            "high": float(last.get("High", 0)),
            "low": float(last.get("Low", 0)),
            "close": float(last.get("Close", 0)),
            "volume": int(last.get("Volume", 0)),
            "adjusted_close": float(last.get("Close", 0)),
            "currency": exchange_info.get("currency", ""),
            "exchange": exchange_info.get("exchange", ""),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _exchange_info(self, ticker: str) -> dict[str, str]:
        """Derive exchange metadata from the ticker suffix."""
        for suffix, meta in self._EXCHANGE_META.items():
            if ticker.upper().endswith(suffix):
                return meta
        return {"exchange": "UNKNOWN", "tz": "UTC", "currency": ""}

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        """Return an empty DataFrame with the canonical column schema."""
        return pd.DataFrame(
            columns=[
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adjusted_close",
            ]
        )

    def _normalise(
        self,
        df: pd.DataFrame,
        ticker: str,
        exchange_tz: str,
    ) -> pd.DataFrame:
        """Clean and normalise a raw yfinance DataFrame.

        * Flattens any ``MultiIndex`` columns produced by ``yf.download``.
        * Renames columns to lowercase snake_case.
        * Converts the index to a timezone-aware UTC ``date`` column.
        * Drops rows with missing close prices (holidays / half-days).
        * Adds a ``ticker`` column for downstream joins.
        """
        # yfinance may return MultiIndex columns when downloading a single
        # ticker – flatten to simple strings.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                col[0] if isinstance(col, tuple) else col for col in df.columns
            ]

        # Standardise column names
        col_map: dict[str, str] = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Adj Close": "adjusted_close",
        }
        df = df.rename(columns=col_map)

        # Ensure we have all required columns
        for col in ("open", "high", "low", "close", "volume"):
            if col not in df.columns:
                logger.warning("Column '%s' missing from %s data", col, ticker)
                df[col] = 0.0

        # If 'adjusted_close' is absent, fall back to 'close'
        if "adjusted_close" not in df.columns:
            df["adjusted_close"] = df["close"]

        # Convert index to UTC-aware datetime column
        idx = df.index
        if hasattr(idx, "tz") and idx.tz is not None:
            df["date"] = idx.tz_convert("UTC")
        else:
            # Localise to exchange tz first, then convert to UTC
            try:
                df["date"] = idx.tz_localize(exchange_tz).tz_convert("UTC")
            except Exception:
                df["date"] = idx.tz_localize("UTC")

        df = df.reset_index(drop=True)

        # Drop rows where close is NaN (weekends / holidays artefacts)
        df = df.dropna(subset=["close"])

        # Keep only canonical columns + ticker
        df["ticker"] = ticker
        canonical = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
            "ticker",
        ]
        df = df[[c for c in canonical if c in df.columns]]

        logger.info(
            "Normalised %d rows for %s (range %s → %s)",
            len(df),
            ticker,
            df["date"].min() if not df.empty else "N/A",
            df["date"].max() if not df.empty else "N/A",
        )
        return df
