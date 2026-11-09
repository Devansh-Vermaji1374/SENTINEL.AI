"""SENTINEL AI - Database Package.

Re-exports the most commonly used symbols for convenient imports::

    from database import init_db, get_db, SessionLocal
    from database.models import Asset, SocialPost, ...
    from database.repository import AssetRepository, ...
"""

from database.db import SessionLocal, engine, get_db, init_db
from database.models import (
    Asset,
    Base,
    MarketData,
    ModelMetric,
    NewsArticle,
    Prediction,
    SentimentScore,
    SocialPost,
)
from database.repository import (
    AssetRepository,
    MarketDataRepository,
    ModelMetricRepository,
    NewsArticleRepository,
    PredictionRepository,
    SentimentRepository,
    SocialPostRepository,
)

__all__ = [
    # db
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    # models
    "Base",
    "Asset",
    "SocialPost",
    "NewsArticle",
    "MarketData",
    "SentimentScore",
    "Prediction",
    "ModelMetric",
    # repositories
    "AssetRepository",
    "SocialPostRepository",
    "NewsArticleRepository",
    "MarketDataRepository",
    "SentimentRepository",
    "PredictionRepository",
    "ModelMetricRepository",
]
