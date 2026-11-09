"""
SENTINEL AI - Signal Extractor
===============================
Combine sentiment analysis, ML predictions, and market data into
unified trading signals.

.. important::

   The ``direction`` field is inferred from model predictions and
   sentiment — it is **not** an actual trading position.  It is
   labelled as a *Model Signal* throughout the codebase.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SignalExtractor:
    """Extract trading signals from combined data sources.

    Aggregates three data streams — sentiment, model predictions, and
    raw market data — into a single, structured signal dictionary per
    asset.
    """

    # Thresholds for overall direction classification
    BULLISH_THRESHOLD: float = 0.15
    BEARISH_THRESHOLD: float = -0.15

    def extract_signal(
        self,
        ticker: str,
        sentiment_data: dict[str, Any],
        prediction_data: dict[str, Any],
        market_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a comprehensive signal for a single ticker.

        Args:
            ticker: Stock ticker symbol.
            sentiment_data: Dictionary with at least:
                - ``overall_sentiment`` (str)
                - ``sentiment_score`` (float, –1 to 1)
                - ``social_mentions`` (int)
                - ``news_sentiment`` (float, –1 to 1)
            prediction_data: Dictionary with at least:
                - ``predicted_price`` (float | None)
                - ``predicted_return`` (float)
                - ``direction`` (str)
            market_data: Dictionary with at least:
                - ``latest_price`` (float)
                - ``asset_name`` (str)
                - ``support_levels`` (list[float])
                - ``resistance_levels`` (list[float])
                - ``data_quality`` (str) — ``'live'``, ``'demo'``, or ``'partial'``

        Returns:
            A unified signal dictionary.  The ``direction`` key carries
            the label *"Model Signal"* qualifier and should never be
            interpreted as trading advice.
        """
        # --- Extract sub-fields with safe defaults -----------------------

        # Sentiment
        sentiment_score = float(sentiment_data.get("sentiment_score", 0.0))
        overall_sentiment = sentiment_data.get("overall_sentiment", "Neutral")
        social_mentions = int(sentiment_data.get("social_mentions", 0))
        news_sentiment = float(sentiment_data.get("news_sentiment", 0.0))

        # Prediction
        predicted_return = float(prediction_data.get("predicted_return", 0.0))
        predicted_price = prediction_data.get("predicted_price")
        model_direction = prediction_data.get("direction", "Neutral")

        # Market
        latest_price = float(market_data.get("latest_price", 0.0))
        asset_name = market_data.get("asset_name", ticker)
        support_levels: list[float] = market_data.get("support_levels", [])
        resistance_levels: list[float] = market_data.get("resistance_levels", [])
        data_quality = market_data.get("data_quality", "demo")

        # --- Compute composite direction --------------------------------
        direction = self._composite_direction(
            sentiment_score=sentiment_score,
            predicted_return=predicted_return,
            model_direction=model_direction,
        )

        # --- Signal strength (0-1) --------------------------------------
        signal_strength = self._calculate_signal_strength(
            sentiment_score=sentiment_score,
            predicted_return=predicted_return,
            model_direction=model_direction,
            overall_sentiment=overall_sentiment,
        )

        signal: dict[str, Any] = {
            "ticker": ticker.upper(),
            "asset_name": asset_name,
            "latest_price": latest_price,
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "social_mentions": social_mentions,
            "news_sentiment": news_sentiment,
            "predicted_price": predicted_price,
            "predicted_return_pct": round(predicted_return * 100, 4),
            "direction": direction,  # Model Signal — NOT a trading position
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "signal_strength": round(signal_strength, 4),
            "data_quality": data_quality,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "Direction is a Model Signal derived from ML predictions and "
                "sentiment analysis. It is NOT investment advice or an actual "
                "trading position."
            ),
        }

        logger.info(
            "Signal [%s]: direction=%s, strength=%.2f, quality=%s",
            ticker,
            direction,
            signal_strength,
            data_quality,
        )
        return signal

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _composite_direction(
        self,
        sentiment_score: float,
        predicted_return: float,
        model_direction: str,
    ) -> str:
        """Derive a composite direction from sentiment + prediction.

        The composite score is a weighted blend:
        ``0.6 × predicted_return_sign + 0.4 × sentiment_score``.

        Returns:
            ``'Bullish'``, ``'Bearish'``, or ``'Neutral'``.
        """
        # Normalise predicted return to [-1, 1] range (clip extreme values)
        pred_signal = max(-1.0, min(1.0, predicted_return * 100))  # scale up for weighting

        composite = 0.6 * pred_signal + 0.4 * sentiment_score

        if composite > self.BULLISH_THRESHOLD:
            return "Bullish"
        elif composite < self.BEARISH_THRESHOLD:
            return "Bearish"
        return "Neutral"

    @staticmethod
    def _calculate_signal_strength(
        sentiment_score: float,
        predicted_return: float,
        model_direction: str,
        overall_sentiment: str,
    ) -> float:
        """Compute signal strength on a 0–1 scale.

        Factors:
        * Magnitude of the predicted return
        * Magnitude of the sentiment score
        * Agreement between prediction direction and sentiment direction
        """
        # Base strength from prediction magnitude (capped)
        pred_magnitude = min(abs(predicted_return) * 50, 0.5)

        # Sentiment magnitude contribution
        sent_magnitude = min(abs(sentiment_score) * 0.5, 0.3)

        # Agreement bonus: +0.2 if prediction and sentiment agree
        agreement_bonus = 0.0
        sentiment_bullish = overall_sentiment == "Bullish" or sentiment_score > 0.1
        sentiment_bearish = overall_sentiment == "Bearish" or sentiment_score < -0.1
        if (model_direction == "Bullish" and sentiment_bullish) or (
            model_direction == "Bearish" and sentiment_bearish
        ):
            agreement_bonus = 0.2

        strength = pred_magnitude + sent_magnitude + agreement_bonus
        return min(1.0, max(0.0, strength))
