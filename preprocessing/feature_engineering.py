"""Feature engineering module for SENTINEL AI.

Computes technical indicators, social-sentiment features, and news
features, then merges them into a single feature matrix suitable for
ML model training and inference.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Generate features for ML models from market, social, and news data."""

    # ------------------------------------------------------------------
    # Technical features
    # ------------------------------------------------------------------

    def compute_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to an OHLCV DataFrame.

        The DataFrame must contain at least the columns ``close`` and
        ``volume`` (case-insensitive).  Additional columns (``open``,
        ``high``, ``low``) are used when present.

        Added features:
        * **Returns**: ``daily_return``, ``log_return``.
        * **Moving averages**: ``sma_5``, ``sma_10``, ``sma_20``,
          ``sma_50``, ``ema_12``, ``ema_26``.
        * **RSI (14)**: ``rsi_14``.
        * **MACD (12, 26, 9)**: ``macd``, ``macd_signal``,
          ``macd_histogram``.
        * **Bollinger Bands (20, 2σ)**: ``bb_upper``, ``bb_middle``,
          ``bb_lower``.
        * **Volatility**: ``volatility_5``, ``volatility_20``.
        * **Volume**: ``volume_sma_20``, ``volume_ratio``.

        Args:
            df: OHLCV DataFrame.

        Returns:
            Copy of *df* with extra feature columns appended.
        """
        df = df.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        if "close" not in df.columns:
            raise ValueError("DataFrame must contain a 'close' column.")

        close: pd.Series = df["close"].astype(float)

        # Returns
        df["daily_return"] = close.pct_change()
        df["log_return"] = np.log(close / close.shift(1))

        # Simple Moving Averages
        for window in (5, 10, 20, 50):
            df[f"sma_{window}"] = close.rolling(window=window, min_periods=1).mean()

        # Exponential Moving Averages
        df["ema_12"] = close.ewm(span=12, adjust=False).mean()
        df["ema_26"] = close.ewm(span=26, adjust=False).mean()

        # RSI
        df["rsi_14"] = self._rsi(close, period=14)

        # MACD
        macd_line, signal_line, histogram = self._macd(
            close, fast=12, slow=26, signal=9
        )
        df["macd"] = macd_line
        df["macd_signal"] = signal_line
        df["macd_histogram"] = histogram

        # Bollinger Bands (20-period, 2 std)
        bb_mid = close.rolling(window=20, min_periods=1).mean()
        bb_std = close.rolling(window=20, min_periods=1).std()
        df["bb_middle"] = bb_mid
        df["bb_upper"] = bb_mid + 2 * bb_std
        df["bb_lower"] = bb_mid - 2 * bb_std

        # Volatility (rolling std of returns)
        df["volatility_5"] = df["daily_return"].rolling(window=5, min_periods=1).std()
        df["volatility_20"] = df["daily_return"].rolling(window=20, min_periods=1).std()

        # Volume features
        if "volume" in df.columns:
            vol = df["volume"].astype(float)
            df["volume_sma_20"] = vol.rolling(window=20, min_periods=1).mean()
            df["volume_ratio"] = vol / df["volume_sma_20"].replace(0, np.nan)

        return df

    # ------------------------------------------------------------------
    # Social features
    # ------------------------------------------------------------------

    def compute_social_features(
        self,
        sentiment_data: dict[str, Any],
        trading_day: date,
    ) -> dict[str, Any]:
        """Compute social features for a given trading day.

        Args:
            sentiment_data: Aggregated sentiment dict (output of
                :class:`SentimentAggregator`).
            trading_day: The trading day these features correspond to.

        Returns:
            Dict with keys: ``trading_day``, ``mention_count``,
            ``positive_ratio``, ``negative_ratio``,
            ``weighted_sentiment``, ``sentiment_momentum``,
            ``engagement_score``.
        """
        return {
            "trading_day": trading_day,
            "mention_count": int(sentiment_data.get("total_mentions", 0)),
            "positive_ratio": float(sentiment_data.get("positive_ratio", 0.0)),
            "negative_ratio": float(sentiment_data.get("negative_ratio", 0.0)),
            "weighted_sentiment": float(
                sentiment_data.get("weighted_sentiment_score", 0.0)
            ),
            "sentiment_momentum": float(
                sentiment_data.get("sentiment_trend", 0.0)
            ),
            "engagement_score": float(sentiment_data.get("avg_engagement", 0.0)),
        }

    # ------------------------------------------------------------------
    # News features
    # ------------------------------------------------------------------

    def compute_news_features(
        self,
        news_sentiments: list[dict[str, Any]],
        trading_day: date,
    ) -> dict[str, Any]:
        """Compute news-derived features for a given trading day.

        Args:
            news_sentiments: List of per-article sentiment dicts with at
                least ``positive_prob`` and ``negative_prob`` keys.
            trading_day: The trading day these features correspond to.

        Returns:
            Dict with keys: ``trading_day``, ``news_count``,
            ``news_sentiment_avg``, ``news_recency_score``.
        """
        count = len(news_sentiments)
        if count == 0:
            return {
                "trading_day": trading_day,
                "news_count": 0,
                "news_sentiment_avg": 0.0,
                "news_recency_score": 0.0,
            }

        scores = [
            float(s.get("positive_prob", 0.0)) - float(s.get("negative_prob", 0.0))
            for s in news_sentiments
        ]
        avg_score = sum(scores) / count

        # Recency: more recent articles (later in the list) get higher weight.
        # Simple linear weighting: weight_i = (i+1) / sum(1..n)
        weight_sum = count * (count + 1) / 2
        recency_score = sum(
            (i + 1) * s / weight_sum for i, s in enumerate(scores)
        )

        return {
            "trading_day": trading_day,
            "news_count": count,
            "news_sentiment_avg": round(avg_score, 6),
            "news_recency_score": round(recency_score, 6),
        }

    # ------------------------------------------------------------------
    # Feature matrix assembly
    # ------------------------------------------------------------------

    def build_feature_matrix(
        self,
        market_df: pd.DataFrame,
        social_features: pd.DataFrame,
        news_features: pd.DataFrame,
    ) -> pd.DataFrame:
        """Combine all features into a single matrix aligned by date.

        Adds a ``next_day_return`` target column computed as::

            next_day_return_t = (close_{t+1} − close_t) / close_t

        .. warning::
           The target is shifted **forward** by one period to avoid
           data leakage – it represents the *next* day's return.

        Args:
            market_df: DataFrame with technical features and a ``date``
                column (or date index).
            social_features: DataFrame with social features and a
                ``trading_day`` column.
            news_features: DataFrame with news features and a
                ``trading_day`` column.

        Returns:
            Merged DataFrame indexed by date, containing all features
            and the ``next_day_return`` target.
        """
        df = market_df.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        # Ensure a 'date' column exists.
        if "date" not in df.columns and df.index.name == "date":
            df = df.reset_index()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        # Target: next-day return (shift -1 so row t has return for t→t+1).
        if "close" in df.columns:
            close = df["close"].astype(float)
            df["next_day_return"] = close.shift(-1) / close - 1.0

        # Merge social features.
        if not social_features.empty:
            sf = social_features.copy()
            if "trading_day" in sf.columns:
                sf["trading_day"] = pd.to_datetime(sf["trading_day"]).dt.date
                sf = sf.rename(columns={"trading_day": "date"})
            df = df.merge(sf, on="date", how="left")

        # Merge news features.
        if not news_features.empty:
            nf = news_features.copy()
            if "trading_day" in nf.columns:
                nf["trading_day"] = pd.to_datetime(nf["trading_day"]).dt.date
                nf = nf.rename(columns={"trading_day": "date"})
            df = df.merge(nf, on="date", how="left")

        # Fill NaN social/news features with 0 (no mentions ≈ neutral).
        social_cols = [
            "mention_count",
            "positive_ratio",
            "negative_ratio",
            "weighted_sentiment",
            "sentiment_momentum",
            "engagement_score",
        ]
        news_cols = ["news_count", "news_sentiment_avg", "news_recency_score"]
        for col in social_cols + news_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0.0)

        return df

    # ------------------------------------------------------------------
    # Support / Resistance
    # ------------------------------------------------------------------

    def compute_support_resistance(
        self,
        df: pd.DataFrame,
        window: int = 20,
    ) -> dict[str, Any]:
        """Calculate support and resistance levels.

        Uses rolling local minima / maxima and classic pivot points.

        Args:
            df: OHLCV DataFrame with ``high``, ``low``, ``close`` columns.
            window: Rolling window size for extrema detection.

        Returns:
            Dict with ``support`` (list of levels), ``resistance``
            (list of levels), and ``pivot`` (float).
        """
        df = df.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        required = {"high", "low", "close"}
        if not required.issubset(df.columns):
            raise ValueError(f"DataFrame must contain columns: {required}")

        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)

        # Pivot point from the most recent bar.
        last_high = high.iloc[-1]
        last_low = low.iloc[-1]
        last_close = close.iloc[-1]
        pivot = (last_high + last_low + last_close) / 3.0

        # Local maxima (resistance candidates).
        rolling_max = high.rolling(window=window, center=True, min_periods=1).max()
        resistance_mask = high == rolling_max
        resistance_levels = sorted(high[resistance_mask].unique().tolist())

        # Local minima (support candidates).
        rolling_min = low.rolling(window=window, center=True, min_periods=1).min()
        support_mask = low == rolling_min
        support_levels = sorted(low[support_mask].unique().tolist())

        # Keep only levels near the current price (within ±20%).
        price_ref = last_close
        resistance_levels = [
            round(r, 4)
            for r in resistance_levels
            if price_ref * 0.8 <= r <= price_ref * 1.2
        ]
        support_levels = [
            round(s, 4)
            for s in support_levels
            if price_ref * 0.8 <= s <= price_ref * 1.2
        ]

        return {
            "support": support_levels,
            "resistance": resistance_levels,
            "pivot": round(pivot, 4),
        }

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate the Relative Strength Index.

        Args:
            series: Price series (typically close prices).
            period: Look-back period.

        Returns:
            RSI values as a pandas Series.
        """
        delta = series.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        avg_gain = gain.ewm(
            alpha=1.0 / period, min_periods=period, adjust=False
        ).mean()
        avg_loss = loss.ewm(
            alpha=1.0 / period, min_periods=period, adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi

    @staticmethod
    def _macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, signal line, and histogram.

        Args:
            series: Price series.
            fast: Fast EMA span.
            slow: Slow EMA span.
            signal: Signal line EMA span.

        Returns:
            Tuple of ``(macd_line, signal_line, histogram)`` as Series.
        """
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
