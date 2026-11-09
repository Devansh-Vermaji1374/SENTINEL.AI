"""Pydantic schemas for Sentinel AI API endpoints."""
from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AssetSchema(BaseModel):
    id: Optional[int] = None
    ticker: str
    name: str
    exchange: str
    sector: str
    currency: str

class MarketDataPoint(BaseModel):
    ticker: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: Optional[float] = None

class SocialPostSchema(BaseModel):
    id: Optional[int] = None
    ticker: str
    platform: str
    text: str
    author: Optional[str] = None
    timestamp: datetime
    likes: int = 0
    reposts: int = 0
    views: int = 0
    followers: Optional[int] = None
    url: Optional[str] = None
    is_demo_data: bool = False
    age_days: Optional[int] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

class NewsArticleSchema(BaseModel):
    id: Optional[int] = None
    ticker: str
    title: str
    source_name: Optional[str] = None
    url: str
    text: Optional[str] = None
    published_at: datetime
    is_demo_data: bool = False
    age_days: Optional[int] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None

class SentimentSummarySchema(BaseModel):
    ticker: str
    total_mentions: int
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    weighted_sentiment_score: float
    sentiment_label: str
    social_volume: int
    news_volume: int
    social_sentiment_score: float = 0.0
    news_sentiment_score: float = 0.0
    social_latest_timestamp: Optional[datetime] = None
    news_latest_timestamp: Optional[datetime] = None
    social_provenance: str = "Apify / Financial Discourse Stream"
    news_provenance: str = "Exa AI / Financial News Wire"
    avg_engagement: float
    sentiment_trend: float

class PredictionSchema(BaseModel):
    id: Optional[int] = None
    ticker: str
    model_name: str
    origin_price: Optional[float] = None
    predicted_price: Optional[float] = None
    predicted_return: Optional[float] = None
    predicted_return_pct: Optional[float] = None
    direction: str
    actual_price: Optional[float] = None
    actual_return: Optional[float] = None
    prediction_error: Optional[float] = None
    direction_correct: Optional[bool] = None
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    prediction_date: datetime
    target_date: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    horizon_days: int = 1

class AssetSignalSchema(BaseModel):
    ticker: str
    asset_name: str
    exchange: str
    sector: str
    currency: str
    latest_price: float
    overall_sentiment: str
    sentiment_score: float
    social_mentions: int
    news_sentiment: float
    predicted_price: float
    predicted_return_pct: float
    direction: str
    support_levels: List[float] = []
    resistance_levels: List[float] = []
    signal_strength: float
    data_quality: str

class MarketOverviewSchema(BaseModel):
    total_assets: int
    total_social_mentions: int
    total_news_articles: int
    overall_positive_pct: float
    overall_negative_pct: float
    overall_neutral_pct: float
    bullish_assets_count: int
    bearish_assets_count: int
    neutral_assets_count: int
    top_bullish: List[Dict[str, Any]]
    top_bearish: List[Dict[str, Any]]
    most_discussed: List[Dict[str, Any]]
    signals: List[Dict[str, Any]] = []

class CollectionTriggerResponse(BaseModel):
    status: str
    service: str
    records_collected: int
    is_demo: bool
    message: str

class SystemStatusSchema(BaseModel):
    status: str
    app_env: str
    database: str
    database_connected: bool = True
    apify_connected: bool
    apify_status: str = "OFFLINE"
    exa_connected: bool
    exa_status: str = "OFFLINE"
    finbert_ready: bool = False
    finbert_status: str = "OFFLINE"
    model_registry_ready: bool = False
    model_registry_status: str = "OFFLINE"
    yfinance_ready: bool
    assets_configured: int
    last_collection: Optional[datetime] = None
    latest_market_timestamp: Optional[datetime] = None
    latest_social_timestamp: Optional[datetime] = None
    latest_news_timestamp: Optional[datetime] = None
    historical_bars_count: int = 0
    discourse_posts_count: int = 0
    news_articles_count: int = 0
    sentiment_scores_count: int = 0
    trained_models_count: int = 0
    predictions_settled_count: int = 0
    predictions_pending_count: int = 0
