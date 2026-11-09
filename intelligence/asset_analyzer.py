"""
SENTINEL AI - Asset Analyzer
=============================
Comprehensive per-asset analysis combining market data, sentiment,
ML predictions, news, and social data into a single intelligence report.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from intelligence.signal_extractor import SignalExtractor
from intelligence.support_resistance import SupportResistanceCalculator

logger = logging.getLogger(__name__)


class AssetAnalyzer:
    """Comprehensive per-asset analysis combining all data sources.

    Orchestrates :class:`SignalExtractor` and
    :class:`SupportResistanceCalculator` to produce a unified
    intelligence report for each asset.
    """

    def __init__(self) -> None:
        self.signal_extractor = SignalExtractor()
        self.sr_calculator = SupportResistanceCalculator()

    def analyze(
        self,
        ticker: str,
        market_data: pd.DataFrame,
        sentiment: dict[str, Any],
        prediction: dict[str, Any],
        news: list[dict[str, Any]],
        social: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Full analysis for a single asset.

        Args:
            ticker: Stock ticker symbol.
            market_data: OHLCV DataFrame (must include ``high``, ``low``,
                ``close``, and ``volume`` columns).
            sentiment: Sentiment analysis results.
            prediction: ML model prediction results.
            news: List of news article dicts (``title``, ``sentiment``,
                ``source``, ``published_at``).
            social: List of social-media post dicts (``text``,
                ``sentiment``, ``platform``, ``posted_at``).

        Returns:
            Comprehensive intelligence dictionary.
        """
        # Normalise column names to lowercase
        mkt = market_data.copy()
        mkt.columns = [c.lower() for c in mkt.columns]

        # --- Support / Resistance ----------------------------------------
        try:
            sr_levels = self.sr_calculator.calculate(mkt, method="combined")
        except Exception:
            logger.warning("S/R calculation failed for %s; using empty levels.", ticker)
            sr_levels = {"support": [], "resistance": [], "pivot": None}

        # --- Price summary -----------------------------------------------
        latest_price = float(mkt["close"].iloc[-1]) if "close" in mkt.columns else 0.0
        price_change_1d = self._calc_pct_change(mkt["close"], periods=1)
        price_change_5d = self._calc_pct_change(mkt["close"], periods=5)
        price_change_20d = self._calc_pct_change(mkt["close"], periods=20)

        avg_volume = float(mkt["volume"].tail(20).mean()) if "volume" in mkt.columns else 0.0
        latest_volume = float(mkt["volume"].iloc[-1]) if "volume" in mkt.columns else 0.0

        # Determine data quality label
        data_quality = sentiment.get("data_quality", prediction.get("data_quality", "demo"))

        # --- Build market-data dict for signal extractor -----------------
        market_dict: dict[str, Any] = {
            "latest_price": latest_price,
            "asset_name": sentiment.get("asset_name", ticker),
            "support_levels": sr_levels.get("support", []),
            "resistance_levels": sr_levels.get("resistance", []),
            "data_quality": data_quality,
        }

        # --- Signal extraction -------------------------------------------
        signal = self.signal_extractor.extract_signal(
            ticker=ticker,
            sentiment_data=sentiment,
            prediction_data=prediction,
            market_data=market_dict,
        )

        # --- News digest -------------------------------------------------
        top_news = sorted(
            news,
            key=lambda n: abs(n.get("sentiment", 0.0)),
            reverse=True,
        )[:5]

        # --- Social digest -----------------------------------------------
        social_summary = {
            "total_posts": len(social),
            "avg_sentiment": (
                float(np.mean([s.get("sentiment", 0.0) for s in social]))
                if social
                else 0.0
            ),
            "platforms": list({s.get("platform", "unknown") for s in social}),
        }

        # --- Assemble final intelligence report --------------------------
        analysis: dict[str, Any] = {
            "ticker": ticker.upper(),
            "asset_name": market_dict["asset_name"],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "data_quality": data_quality,
            # Price action
            "latest_price": latest_price,
            "price_change_1d_pct": price_change_1d,
            "price_change_5d_pct": price_change_5d,
            "price_change_20d_pct": price_change_20d,
            "avg_volume_20d": avg_volume,
            "latest_volume": latest_volume,
            "volume_vs_avg": (
                round(latest_volume / avg_volume, 2) if avg_volume > 0 else None
            ),
            # S/R
            "support_levels": sr_levels.get("support", []),
            "resistance_levels": sr_levels.get("resistance", []),
            "pivot_point": sr_levels.get("pivot"),
            # Signal
            "signal": signal,
            "direction": signal.get("direction", "Neutral"),
            "signal_strength": signal.get("signal_strength", 0.0),
            # Sentiment
            "sentiment_score": signal.get("sentiment_score", 0.0),
            "overall_sentiment": signal.get("overall_sentiment", "Neutral"),
            # Prediction
            "predicted_return_pct": signal.get("predicted_return_pct", 0.0),
            "predicted_price": signal.get("predicted_price"),
            # News
            "top_news": top_news,
            # Social
            "social_summary": social_summary,
        }

        logger.info(
            "Analysis complete for %s: direction=%s, strength=%.2f",
            ticker,
            analysis["direction"],
            analysis["signal_strength"],
        )
        return analysis

    # ------------------------------------------------------------------
    # Ranking & summaries
    # ------------------------------------------------------------------

    def rank_assets(
        self,
        analyses: list[dict[str, Any]],
        sort_by: str = "sentiment_score",
    ) -> list[dict[str, Any]]:
        """Rank analysed assets by a specified criterion.

        Args:
            analyses: List of analysis dicts as returned by :meth:`analyze`.
            sort_by: Key to sort by.  Common choices:
                ``'sentiment_score'``, ``'signal_strength'``,
                ``'predicted_return_pct'``, ``'price_change_1d_pct'``.

        Returns:
            The input list sorted descending by *sort_by*.
        """
        ranked = sorted(
            analyses,
            key=lambda a: a.get(sort_by, 0.0) or 0.0,
            reverse=True,
        )

        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank

        logger.info(
            "Ranked %d assets by '%s'. Top: %s",
            len(ranked),
            sort_by,
            ranked[0]["ticker"] if ranked else "N/A",
        )
        return ranked

    def get_market_summary(
        self,
        all_analyses: list[dict[str, Any]],
        exchange: str | None = None,
    ) -> dict[str, Any]:
        """Generate market-level summary statistics.

        Args:
            all_analyses: List of per-asset analysis dicts.
            exchange: Optional exchange filter (currently informational).

        Returns:
            Dictionary with aggregate market statistics.
        """
        if not all_analyses:
            return {
                "exchange": exchange,
                "total_assets": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        sentiment_scores = [
            a.get("sentiment_score", 0.0) for a in all_analyses
        ]
        signal_strengths = [
            a.get("signal_strength", 0.0) for a in all_analyses
        ]
        directions = [a.get("direction", "Neutral") for a in all_analyses]

        bullish_count = directions.count("Bullish")
        bearish_count = directions.count("Bearish")
        neutral_count = directions.count("Neutral")

        avg_sentiment = float(np.mean(sentiment_scores))
        avg_strength = float(np.mean(signal_strengths))

        # Determine overall market mood
        if bullish_count > bearish_count and avg_sentiment > 0.05:
            market_mood = "Bullish"
        elif bearish_count > bullish_count and avg_sentiment < -0.05:
            market_mood = "Bearish"
        else:
            market_mood = "Mixed"

        summary: dict[str, Any] = {
            "exchange": exchange,
            "total_assets": len(all_analyses),
            "market_mood": market_mood,
            "avg_sentiment_score": round(avg_sentiment, 4),
            "avg_signal_strength": round(avg_strength, 4),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "strongest_bullish": self._top_by(
                all_analyses, "signal_strength", direction="Bullish"
            ),
            "strongest_bearish": self._top_by(
                all_analyses, "signal_strength", direction="Bearish"
            ),
            "most_mentioned": self._top_by(
                all_analyses, "social_summary.total_posts"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "Market summary: %d assets, mood=%s, avg_sentiment=%.3f",
            len(all_analyses),
            market_mood,
            avg_sentiment,
        )
        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_pct_change(series: pd.Series, periods: int) -> float | None:
        """Safely calculate percentage change over *periods* bars."""
        if len(series) <= periods:
            return None
        current = float(series.iloc[-1])
        past = float(series.iloc[-1 - periods])
        if abs(past) < 1e-12:
            return None
        return round((current - past) / past * 100, 4)

    @staticmethod
    def _top_by(
        analyses: list[dict[str, Any]],
        key: str,
        direction: str | None = None,
    ) -> str | None:
        """Return the ticker of the top asset by a dotted key path."""
        filtered = analyses
        if direction is not None:
            filtered = [a for a in analyses if a.get("direction") == direction]
        if not filtered:
            return None

        def _get(d: dict, k: str) -> float:
            parts = k.split(".")
            val: Any = d
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p, 0.0)
                else:
                    return 0.0
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

        best = max(filtered, key=lambda a: _get(a, key))
        return best.get("ticker")
