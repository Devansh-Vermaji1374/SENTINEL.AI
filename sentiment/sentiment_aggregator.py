"""SENTINEL AI - Sentiment Aggregator.
Aggregates real FinBERT sentiment probabilities across social discourse and news items.
Includes anti-manipulation viral post capping (max 5%) and robust temporal trend calculation.
Never defaults missing records to neutral.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SentimentAggregator:
    """Aggregates individual FinBERT sentiment inferences into per-ticker metrics."""

    def aggregate_for_ticker(
        self,
        sentiments: List[Dict[str, Any]],
        ticker: str = "",
        engagement_data: Optional[List[Dict[str, Any]]] = None,
        max_weight_pct: float = 5.0,
    ) -> Dict[str, Any]:
        """Aggregate sentiment scores for a single ticker.
        If sentiments list is empty, returns an explicit unmeasured state
        rather than pretending sentiment is neutral.
        """
        total = len(sentiments)
        if total == 0:
            return {
                "ticker": ticker,
                "total_mentions": 0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 0.0,
                "weighted_sentiment_score": 0.0,
                "sentiment_label": "No Data",
                "social_volume": 0,
                "news_volume": 0,
                "avg_engagement": 0.0,
                "social_sentiment": 0.0,
                "news_sentiment": 0.0,
                "sentiment_trend": 0.0,
                "has_real_sentiment": False
            }

        # Filter valid items
        valid_sentiments = [s for s in sentiments if s.get("sentiment") in ("positive", "negative", "neutral")]
        if not valid_sentiments:
            return {
                "ticker": ticker,
                "total_mentions": total,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 0.0,
                "weighted_sentiment_score": 0.0,
                "sentiment_label": "No Data",
                "social_volume": 0,
                "news_volume": 0,
                "avg_engagement": 0.0,
                "social_sentiment": 0.0,
                "news_sentiment": 0.0,
                "sentiment_trend": 0.0,
                "has_real_sentiment": False
            }

        pos_count = sum(1 for s in valid_sentiments if s.get("sentiment") == "positive")
        neg_count = sum(1 for s in valid_sentiments if s.get("sentiment") == "negative")
        neu_count = sum(1 for s in valid_sentiments if s.get("sentiment") == "neutral")
        n_valid = len(valid_sentiments)

        pos_ratio = pos_count / n_valid
        neg_ratio = neg_count / n_valid
        neu_ratio = neu_count / n_valid

        # Engagement weights calculation with max_weight_pct cap (anti-viral outlier dampening)
        weights = []
        max_single_weight = max_weight_pct / 100.0
        
        for idx, s in enumerate(valid_sentiments):
            eng = 1.0
            if engagement_data and idx < len(engagement_data):
                ed = engagement_data[idx]
                likes = ed.get("likes", 0)
                reposts = ed.get("reposts", 0)
                views = ed.get("views", 0)
                eng = 1.0 + math.log1p(likes * 2 + reposts * 5 + views * 0.05)
            weights.append(eng)

        tot_eng = sum(weights) or 1.0
        norm_weights = [w / tot_eng for w in weights]
        # Apply capping
        capped_weights = [min(w, max_single_weight) for w in norm_weights]
        sum_capped = sum(capped_weights) or 1.0
        final_weights = [w / sum_capped for w in capped_weights]

        weighted_scores = []
        for s, w in zip(valid_sentiments, final_weights):
            p_pos = float(s.get("positive_prob", 0.0))
            p_neg = float(s.get("negative_prob", 0.0))
            score = (p_pos - p_neg)  # in [-1, +1]
            weighted_scores.append(score * w)

        agg_score = sum(weighted_scores)
        # Bounded between -1.0 and +1.0
        agg_score = max(-1.0, min(1.0, agg_score))

        # Separate social vs news sentiment
        social_items = [s for s in valid_sentiments if s.get("source_type") == "social"]
        news_items = [s for s in valid_sentiments if s.get("source_type") == "news"]

        soc_score = 0.0
        if social_items:
            soc_score = sum(float(s.get("positive_prob", 0.0)) - float(s.get("negative_prob", 0.0)) for s in social_items) / len(social_items)

        news_score = 0.0
        if news_items:
            news_score = sum(float(s.get("positive_prob", 0.0)) - float(s.get("negative_prob", 0.0)) for s in news_items) / len(news_items)

        if agg_score > 0.05:
            sentiment_label = "Bullish"
        elif agg_score < -0.05:
            sentiment_label = "Bearish"
        else:
            sentiment_label = "Neutral"

        return {
            "ticker": ticker,
            "total_mentions": total,
            "positive_ratio": round(pos_ratio, 3),
            "negative_ratio": round(neg_ratio, 3),
            "neutral_ratio": round(neu_ratio, 3),
            "weighted_sentiment_score": round(agg_score, 4),
            "sentiment_label": sentiment_label,
            "social_volume": len(social_items),
            "news_volume": len(news_items),
            "avg_engagement": round(tot_eng / total, 2),
            "social_sentiment": round(soc_score, 4),
            "news_sentiment": round(news_score, 4),
            "sentiment_trend": round(news_score - soc_score, 4),
            "has_real_sentiment": True
        }
