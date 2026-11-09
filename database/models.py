"""SENTINEL AI - SQLAlchemy ORM Models.

Uses SQLAlchemy 2.0 declarative style with ``mapped_column`` and
``DeclarativeBase``.  All ``datetime`` columns are timezone-aware
(``DateTime(timezone=True)``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all SENTINEL AI models."""

    pass


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------


class Asset(Base):
    """A tracked financial asset (equity)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    social_posts: Mapped[list["SocialPost"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    news_articles: Mapped[list["NewsArticle"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    market_data: Mapped[list["MarketData"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    sentiment_scores: Mapped[list["SentimentScore"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    model_metrics: Mapped[list["ModelMetric"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assets_ticker", "ticker"),
        Index("ix_assets_exchange", "exchange"),
    )

    def __repr__(self) -> str:
        return f"<Asset(ticker={self.ticker!r}, name={self.name!r})>"


# ---------------------------------------------------------------------------
# SocialPost
# ---------------------------------------------------------------------------


class SocialPost(Base):
    """A social-media post related to a tracked asset."""

    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("assets.ticker"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reposts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="social_posts")

    __table_args__ = (
        Index("ix_social_posts_ticker", "ticker"),
        Index("ix_social_posts_timestamp", "timestamp"),
        Index("ix_social_posts_platform", "platform"),
        Index("ix_social_posts_url_platform", "url", "platform", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<SocialPost(ticker={self.ticker!r}, "
            f"platform={self.platform!r}, id={self.id})>"
        )


# ---------------------------------------------------------------------------
# NewsArticle
# ---------------------------------------------------------------------------


class NewsArticle(Base):
    """A financial news article related to a tracked asset."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("assets.ticker"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="news_articles")

    __table_args__ = (
        Index("ix_news_articles_ticker", "ticker"),
        Index("ix_news_articles_published_at", "published_at"),
        Index("ix_news_articles_url", "url", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<NewsArticle(ticker={self.ticker!r}, "
            f"title={self.title[:40]!r}...)>"
        )


# ---------------------------------------------------------------------------
# MarketData
# ---------------------------------------------------------------------------


class MarketData(Base):
    """Daily OHLCV market data for a tracked asset."""

    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("assets.ticker"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    adjusted_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="market_data")

    __table_args__ = (
        Index("ix_market_data_ticker", "ticker"),
        Index("ix_market_data_date", "date"),
        Index("ix_market_data_ticker_date", "ticker", "date", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketData(ticker={self.ticker!r}, "
            f"date={self.date!r}, close={self.close})>"
        )


# ---------------------------------------------------------------------------
# SentimentScore
# ---------------------------------------------------------------------------


class SentimentScore(Base):
    """Sentiment analysis result for a social post or news article."""

    __tablename__ = "sentiment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("assets.ticker"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "social" | "news"
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sentiment: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "positive" | "negative" | "neutral"
    positive_prob: Mapped[float] = mapped_column(Float, nullable=False)
    negative_prob: Mapped[float] = mapped_column(Float, nullable=False)
    neutral_prob: Mapped[float] = mapped_column(Float, nullable=False)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="sentiment_scores")

    __table_args__ = (
        Index("ix_sentiment_scores_ticker", "ticker"),
        Index("ix_sentiment_scores_source", "source_type", "source_id"),
        Index("ix_sentiment_scores_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SentimentScore(ticker={self.ticker!r}, "
            f"sentiment={self.sentiment!r}, score={self.weighted_score})>"
        )


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


class Prediction(Base):
    """A model-generated price or return prediction for an asset."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("assets.ticker"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prediction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    target_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    horizon_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    origin_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prediction_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    direction_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    settled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confidence_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_ticker", "ticker"),
        Index("ix_predictions_target_date", "target_date"),
        Index("ix_predictions_model_name", "model_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(ticker={self.ticker!r}, "
            f"model={self.model_name!r}, target={self.target_date!r})>"
        )


# ---------------------------------------------------------------------------
# ModelMetric
# ---------------------------------------------------------------------------


class ModelMetric(Base):
    """Evaluation metric for a trained model on a specific asset."""

    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("assets.ticker"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    split_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. "test", "validation", "walk_forward"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="model_metrics")

    __table_args__ = (
        Index("ix_model_metrics_model_name", "model_name"),
        Index("ix_model_metrics_ticker", "ticker"),
        Index("ix_model_metrics_evaluation_date", "evaluation_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<ModelMetric(model={self.model_name!r}, "
            f"ticker={self.ticker!r}, "
            f"{self.metric_name}={self.metric_value})>"
        )
