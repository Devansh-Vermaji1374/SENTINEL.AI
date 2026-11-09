"""SENTINEL AI - Repository Pattern for Database Operations.

Provides typed, session-safe CRUD helpers for every ORM model.  Each
repository class wraps a SQLAlchemy ``Session`` and exposes domain-specific
query methods (deduplication, upsert, aggregation, etc.).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, select, func, and_, delete
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.orm import Session

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

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=Base)


# ======================================================================== #
#  Base Repository
# ======================================================================== #


class BaseRepository(Generic[ModelT]):
    """Generic repository providing common CRUD operations.

    Subclasses must set ``model`` to the appropriate ORM class.
    """

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Read ----------------------------------------------------------- #

    def get(self, record_id: int) -> ModelT | None:
        """Fetch a single record by primary key."""
        return self.db.get(self.model, record_id)

    def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """Return a paginated list of records."""
        stmt = select(self.model).offset(offset).limit(limit)
        return self.db.scalars(stmt).all()

    def count(self) -> int:
        """Return the total number of records."""
        stmt = select(func.count()).select_from(self.model)
        result = self.db.execute(stmt).scalar()
        return result or 0

    # -- Write ---------------------------------------------------------- #

    def create(self, obj: ModelT) -> ModelT:
        """Add a new record to the session and flush to get its id."""
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_many(self, objects: list[ModelT]) -> list[ModelT]:
        """Add multiple records in one go."""
        self.db.add_all(objects)
        self.db.flush()
        return objects

    def save(self) -> None:
        """Commit the current transaction."""
        self.db.commit()

    # -- Delete --------------------------------------------------------- #

    def delete(self, record_id: int) -> bool:
        """Delete a record by primary key.  Returns ``True`` if found."""
        obj = self.get(record_id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True

    def delete_all(self) -> int:
        """Delete **all** rows. Returns count of deleted rows."""
        stmt = delete(self.model)
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount  # type: ignore[return-value]


# ======================================================================== #
#  Asset Repository
# ======================================================================== #


class AssetRepository(BaseRepository[Asset]):
    """Repository for :class:`Asset` records."""

    model = Asset

    def get_by_ticker(self, ticker: str) -> Asset | None:
        """Look up an asset by its ticker symbol."""
        stmt = select(Asset).where(Asset.ticker == ticker)
        return self.db.scalars(stmt).first()

    def get_by_exchange(self, exchange: str) -> Sequence[Asset]:
        """Return all assets on a given exchange."""
        stmt = select(Asset).where(Asset.exchange == exchange)
        return self.db.scalars(stmt).all()

    def upsert(self, asset: Asset) -> Asset:
        """Insert or update an asset keyed by ticker."""
        existing = self.get_by_ticker(asset.ticker)
        if existing is not None:
            existing.name = asset.name
            existing.exchange = asset.exchange
            existing.sector = asset.sector
            existing.currency = asset.currency
            self.db.flush()
            return existing
        return self.create(asset)


# ======================================================================== #
#  SocialPost Repository
# ======================================================================== #


class SocialPostRepository(BaseRepository[SocialPost]):
    """Repository for :class:`SocialPost` records with dedup logic."""

    model = SocialPost

    def get_by_ticker(
        self,
        ticker: str,
        *,
        limit: int = 100,
    ) -> Sequence[SocialPost]:
        """Return posts for a ticker, most recent first."""
        stmt = (
            select(SocialPost)
            .where(SocialPost.ticker == ticker)
            .order_by(SocialPost.timestamp.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def exists(self, url: str | None, platform: str) -> bool:
        """Check whether a post with the same *url* + *platform* exists."""
        if url is None:
            return False
        stmt = select(SocialPost.id).where(
            and_(SocialPost.url == url, SocialPost.platform == platform)
        )
        return self.db.execute(stmt).first() is not None

    def bulk_insert_dedup(self, posts: list[SocialPost]) -> int:
        """Insert posts that do not already exist (dedup by url+platform).

        Returns:
            Number of posts actually inserted.
        """
        inserted = 0
        for post in posts:
            if not self.exists(post.url, post.platform):
                self.db.add(post)
                inserted += 1
        self.db.flush()
        logger.info(
            "SocialPost bulk insert: %d/%d new posts inserted.",
            inserted,
            len(posts),
        )
        return inserted


# ======================================================================== #
#  NewsArticle Repository
# ======================================================================== #


class NewsArticleRepository(BaseRepository[NewsArticle]):
    """Repository for :class:`NewsArticle` records with dedup logic."""

    model = NewsArticle

    def get_by_ticker(
        self,
        ticker: str,
        *,
        limit: int = 50,
    ) -> Sequence[NewsArticle]:
        """Return articles for a ticker, most recent first."""
        stmt = (
            select(NewsArticle)
            .where(NewsArticle.ticker == ticker)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def exists_by_url(self, url: str) -> bool:
        """Check whether an article with the given *url* already exists."""
        stmt = select(NewsArticle.id).where(NewsArticle.url == url)
        return self.db.execute(stmt).first() is not None

    def bulk_insert_dedup(self, articles: list[NewsArticle]) -> int:
        """Insert articles that do not already exist (dedup by url).

        Returns:
            Number of articles actually inserted.
        """
        inserted = 0
        for article in articles:
            if not self.exists_by_url(article.url):
                self.db.add(article)
                inserted += 1
        self.db.flush()
        logger.info(
            "NewsArticle bulk insert: %d/%d new articles inserted.",
            inserted,
            len(articles),
        )
        return inserted


# ======================================================================== #
#  MarketData Repository
# ======================================================================== #


class MarketDataRepository(BaseRepository[MarketData]):
    """Repository for :class:`MarketData` records with upsert by ticker+date."""

    model = MarketData

    def get_latest(self, ticker: str) -> MarketData | None:
        """Return the most recent market-data row for *ticker*."""
        stmt = (
            select(MarketData)
            .where(MarketData.ticker == ticker)
            .order_by(MarketData.date.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def get_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Sequence[MarketData]:
        """Return market data for *ticker* between *start_date* and *end_date* (inclusive)."""
        stmt = (
            select(MarketData)
            .where(
                and_(
                    MarketData.ticker == ticker,
                    MarketData.date >= start_date,
                    MarketData.date <= end_date,
                )
            )
            .order_by(MarketData.date.asc())
        )
        return self.db.scalars(stmt).all()

    def get_by_ticker(
        self,
        ticker: str,
        *,
        limit: int = 200,
    ) -> Sequence[MarketData]:
        """Return recent market data rows for *ticker*."""
        stmt = (
            select(MarketData)
            .where(MarketData.ticker == ticker)
            .order_by(MarketData.date.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def _find_existing(self, ticker: str, date: datetime) -> MarketData | None:
        """Look up a row by ticker + date."""
        stmt = select(MarketData).where(
            and_(MarketData.ticker == ticker, MarketData.date == date)
        )
        return self.db.scalars(stmt).first()

    def upsert(self, row: MarketData) -> MarketData:
        """Insert or update a market-data row keyed by (ticker, date)."""
        existing = self._find_existing(row.ticker, row.date)
        if existing is not None:
            existing.open = row.open
            existing.high = row.high
            existing.low = row.low
            existing.close = row.close
            existing.volume = row.volume
            existing.adjusted_close = row.adjusted_close
            self.db.flush()
            return existing
        return self.create(row)

    def bulk_upsert(self, rows: list[MarketData]) -> int:
        """Upsert a batch of market-data rows.

        Returns:
            Number of rows processed.
        """
        for row in rows:
            self.upsert(row)
        logger.info(
            "MarketData bulk upsert: %d rows processed.",
            len(rows),
        )
        return len(rows)


# ======================================================================== #
#  Sentiment Repository
# ======================================================================== #


class SentimentRepository(BaseRepository[SentimentScore]):
    """Repository for :class:`SentimentScore` records."""

    model = SentimentScore

    def get_by_ticker(
        self,
        ticker: str,
        *,
        source_type: str | None = None,
        limit: int = 200,
    ) -> Sequence[SentimentScore]:
        """Return sentiment scores for *ticker*, optionally filtered by source type."""
        stmt = select(SentimentScore).where(SentimentScore.ticker == ticker)
        if source_type is not None:
            stmt = stmt.where(SentimentScore.source_type == source_type)
        stmt = stmt.order_by(SentimentScore.created_at.desc()).limit(limit)
        return self.db.scalars(stmt).all()

    def get_aggregated(
        self,
        ticker: str,
        *,
        source_type: str | None = None,
    ) -> dict[str, Any]:
        """Return aggregated sentiment statistics for *ticker*.

        Returns a dict with keys: ``count``, ``avg_weighted_score``,
        ``positive_count``, ``negative_count``, ``neutral_count``.
        """
        stmt = select(
            func.count(SentimentScore.id).label("count"),
            func.avg(SentimentScore.weighted_score).label("avg_weighted_score"),
            func.sum(
                func.case(
                    (SentimentScore.sentiment == "positive", 1),
                    else_=0,
                )
            ).label("positive_count"),
            func.sum(
                func.case(
                    (SentimentScore.sentiment == "negative", 1),
                    else_=0,
                )
            ).label("negative_count"),
            func.sum(
                func.case(
                    (SentimentScore.sentiment == "neutral", 1),
                    else_=0,
                )
            ).label("neutral_count"),
        ).where(SentimentScore.ticker == ticker)

        if source_type is not None:
            stmt = stmt.where(SentimentScore.source_type == source_type)

        row = self.db.execute(stmt).first()
        if row is None or row.count == 0:
            return {
                "count": 0,
                "avg_weighted_score": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }
        return {
            "count": row.count,
            "avg_weighted_score": float(row.avg_weighted_score or 0.0),
            "positive_count": int(row.positive_count or 0),
            "negative_count": int(row.negative_count or 0),
            "neutral_count": int(row.neutral_count or 0),
        }

    def bulk_insert(self, scores: list[SentimentScore]) -> int:
        """Insert a batch of sentiment scores.

        Returns:
            Number of scores inserted.
        """
        self.db.add_all(scores)
        self.db.flush()
        logger.info("SentimentScore bulk insert: %d scores inserted.", len(scores))
        return len(scores)

    def get_by_source(
        self,
        source_type: str,
        source_id: int,
    ) -> SentimentScore | None:
        """Look up sentiment by source type + id."""
        stmt = select(SentimentScore).where(
            and_(
                SentimentScore.source_type == source_type,
                SentimentScore.source_id == source_id,
            )
        )
        return self.db.scalars(stmt).first()


# ======================================================================== #
#  Prediction Repository
# ======================================================================== #


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for :class:`Prediction` records."""

    model = Prediction

    def get_by_ticker(
        self,
        ticker: str,
        *,
        model_name: str | None = None,
        limit: int = 50,
    ) -> Sequence[Prediction]:
        """Return predictions for *ticker*, optionally filtered by model."""
        stmt = select(Prediction).where(Prediction.ticker == ticker)
        if model_name is not None:
            stmt = stmt.where(Prediction.model_name == model_name)
        stmt = stmt.order_by(Prediction.target_date.desc()).limit(limit)
        return self.db.scalars(stmt).all()

    def get_latest(
        self,
        ticker: str,
        model_name: str | None = None,
    ) -> Prediction | None:
        """Return the most recent prediction for *ticker*."""
        stmt = select(Prediction).where(Prediction.ticker == ticker)
        if model_name is not None:
            stmt = stmt.where(Prediction.model_name == model_name)
        stmt = stmt.order_by(Prediction.created_at.desc()).limit(1)
        return self.db.scalars(stmt).first()

    def update_actuals(
        self,
        prediction_id: int,
        *,
        actual_price: float | None = None,
        actual_return: float | None = None,
    ) -> Prediction | None:
        """Fill in the actual price/return once the target date has passed."""
        pred = self.get(prediction_id)
        if pred is None:
            return None
        if actual_price is not None:
            pred.actual_price = actual_price
        if actual_return is not None:
            pred.actual_return = actual_return
        self.db.flush()
        return pred


# ======================================================================== #
#  ModelMetric Repository
# ======================================================================== #


class ModelMetricRepository(BaseRepository[ModelMetric]):
    """Repository for :class:`ModelMetric` records."""

    model = ModelMetric

    def get_by_model(
        self,
        model_name: str,
        *,
        ticker: str | None = None,
    ) -> Sequence[ModelMetric]:
        """Return metrics for a named model, optionally filtered by ticker."""
        stmt = select(ModelMetric).where(ModelMetric.model_name == model_name)
        if ticker is not None:
            stmt = stmt.where(ModelMetric.ticker == ticker)
        stmt = stmt.order_by(ModelMetric.evaluation_date.desc())
        return self.db.scalars(stmt).all()

    def get_latest_metrics(
        self,
        model_name: str,
        ticker: str,
    ) -> Sequence[ModelMetric]:
        """Return the latest set of metrics for a model+ticker combination.

        "Latest" is defined as all metrics sharing the most recent
        ``evaluation_date``.
        """
        # Sub-query: find the latest evaluation_date
        latest_date_stmt = (
            select(func.max(ModelMetric.evaluation_date))
            .where(
                and_(
                    ModelMetric.model_name == model_name,
                    ModelMetric.ticker == ticker,
                )
            )
            .scalar_subquery()
        )
        stmt = (
            select(ModelMetric)
            .where(
                and_(
                    ModelMetric.model_name == model_name,
                    ModelMetric.ticker == ticker,
                    ModelMetric.evaluation_date == latest_date_stmt,
                )
            )
            .order_by(ModelMetric.metric_name)
        )
        return self.db.scalars(stmt).all()

    def bulk_insert(self, metrics: list[ModelMetric]) -> int:
        """Insert a batch of model metrics.

        Returns:
            Number of metrics inserted.
        """
        self.db.add_all(metrics)
        self.db.flush()
        logger.info("ModelMetric bulk insert: %d metrics inserted.", len(metrics))
        return len(metrics)
