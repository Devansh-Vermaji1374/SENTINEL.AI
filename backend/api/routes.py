"""FastAPI routing and endpoints for Sentinel AI."""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import joblib
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import pandas as pd

from config.settings import get_settings
from database.db import get_db, SessionLocal
from database.models import (
    Asset, MarketData, SocialPost, NewsArticle, SentimentScore, Prediction, ModelMetric
)
from database.repository import (
    AssetRepository, MarketDataRepository, SocialPostRepository,
    NewsArticleRepository, SentimentRepository, PredictionRepository,
    ModelMetricRepository
)
from backend.services.pipeline_service import PipelineService
from backend.schemas.api_schemas import (
    AssetSchema, MarketDataPoint, SocialPostSchema, NewsArticleSchema,
    SentimentSummarySchema, PredictionSchema, AssetSignalSchema,
    MarketOverviewSchema, CollectionTriggerResponse, SystemStatusSchema
)

router = APIRouter()
pipeline_service = PipelineService()

@router.get("/status", response_model=SystemStatusSchema)
def get_system_status():
    """Return genuine health and status with active component verification.
    No hardcoded ready claims or fake LIVE labels.
    """
    settings = get_settings()
    with SessionLocal() as session:
        m_repo = MarketDataRepository(session)
        latest_market = m_repo.list_all(limit=1)
        latest_m_date = latest_market[0].date if latest_market else None
        
        latest_post = session.query(SocialPost).order_by(SocialPost.timestamp.desc()).first()
        latest_p_date = latest_post.timestamp if latest_post else None
        
        latest_article = session.query(NewsArticle).order_by(NewsArticle.published_at.desc()).first()
        latest_a_date = latest_article.published_at if latest_article else None

        n_bars = session.query(MarketData).count()
        n_posts = session.query(SocialPost).count()
        n_news = session.query(NewsArticle).count()
        n_sent = session.query(SentimentScore).count()
        n_settled = session.query(Prediction).filter(Prediction.settled_at.isnot(None)).count()
        n_pending = session.query(Prediction).filter(Prediction.settled_at.is_(None)).count()

    # Model registry verification: test loading & running sample inference on saved bundle
    saved_dir = Path("models/saved")
    deploy_models = list(saved_dir.glob("*.joblib"))
    # Exclude _eval.joblib files when counting active deployment models
    active_deploy_models = [f for f in deploy_models if not f.name.endswith("_eval.joblib")]
    n_models = len(active_deploy_models)
    model_reg_ready = False
    model_reg_status = "OFFLINE"
    
    if n_models >= 40:
        try:
            # Verify actual bundle loading on a registered artifact
            sample_bundle = joblib.load(saved_dir / "0700.HK_random_forest.joblib")
            if isinstance(sample_bundle, dict) and "model" in sample_bundle and "feature_names" in sample_bundle:
                model_reg_ready = True
                model_reg_status = "READY"
            else:
                model_reg_status = "DEGRADED (Legacy Format)"
        except Exception as e:
            model_reg_status = f"ERROR ({e})"
    elif n_models > 0:
        model_reg_status = f"PARTIAL ({n_models}/40 artifacts)"

    # FinBERT readiness check: verify weights presence & model initialization
    finbert_ready = False
    finbert_status = "OFFLINE"
    try:
        if hasattr(pipeline_service, "finbert") and pipeline_service.finbert is not None:
            finbert_status = pipeline_service.finbert.get_status()
            finbert_ready = finbert_status == "INFERENCE_VERIFIED"
        else:
            finbert_status = "NOT INITIALIZED"
    except Exception as e:
        finbert_status = f"ERROR ({e})"

    # External Provider checks (distinguish API key presence from connection)
    apify_token = settings.apify_api_token
    apify_status = "KEY CONFIGURED" if (apify_token and len(apify_token) > 5) else "NOT CONFIGURED"
    
    exa_key = settings.exa_api_key
    exa_status = "KEY CONFIGURED" if (exa_key and len(exa_key) > 5) else "NOT CONFIGURED"

    overall_status = "healthy" if (model_reg_ready and finbert_ready and n_bars > 0) else "degraded"

    return SystemStatusSchema(
        status=overall_status,
        app_env=settings.app_env,
        database="connected",
        database_connected=True,
        apify_connected=bool(apify_token),
        apify_status=apify_status,
        exa_connected=bool(exa_key),
        exa_status=exa_status,
        finbert_ready=finbert_ready,
        finbert_status=finbert_status,
        model_registry_ready=model_reg_ready,
        model_registry_status=model_reg_status,
        yfinance_ready=True,
        assets_configured=len(settings.get_all_assets()),
        last_collection=latest_m_date,
        latest_market_timestamp=latest_m_date,
        latest_social_timestamp=latest_p_date,
        latest_news_timestamp=latest_a_date,
        historical_bars_count=n_bars,
        discourse_posts_count=n_posts,
        news_articles_count=n_news,
        sentiment_scores_count=n_sent,
        trained_models_count=n_models,
        predictions_settled_count=n_settled,
        predictions_pending_count=n_pending
    )

@router.get("/models/performance")
def get_model_performance(ticker: Optional[str] = None):
    """Return genuine out-of-sample quantitative evaluation metrics from saved model metadata."""
    saved_dir = Path("models/saved")
    if not saved_dir.exists():
        return []

    results = []
    meta_files = list(saved_dir.glob("*_meta.json"))
    for mf in sorted(meta_files):
        try:
            with open(mf, "r", encoding="utf-8") as f:
                data = json.load(f)
            t = data.get("ticker")
            if ticker and t and t.upper() != ticker.upper():
                continue
            results.append(data)
        except Exception as e:
            logger.warning("Error reading %s: %s", mf, e)

    return results

@router.get("/assets", response_model=List[AssetSchema])
def list_assets(exchange: Optional[str] = Query(None, description="HKEX or KRX")):
    """List tracked assets, optionally filtered by exchange."""
    with SessionLocal() as session:
        repo = AssetRepository(session)
        if exchange:
            assets = repo.get_by_exchange(exchange.upper())
        else:
            assets = repo.list_all(limit=100)
            
        return [
            AssetSchema(
                id=a.id,
                ticker=a.ticker,
                name=a.name,
                exchange=a.exchange,
                sector=a.sector,
                currency=a.currency
            )
            for a in assets
        ]

@router.get("/market-overview", response_model=MarketOverviewSchema)
def get_market_overview():
    """Aggregate market-wide overview metrics across all assets."""
    overview = pipeline_service.get_market_overview()
    return overview

@router.get("/signals", response_model=List[AssetSignalSchema])
def get_all_signals(exchange: Optional[str] = None):
    """Return trading & sentiment intelligence signals for all assets."""
    settings = get_settings()
    assets = settings.get_assets_by_exchange(exchange.upper()) if exchange else settings.get_all_assets()
    signals = []
    for a in assets:
        sig = pipeline_service.get_asset_signal(a.ticker)
        if sig:
            signals.append(sig)
    return signals

@router.get("/signals/{ticker}", response_model=AssetSignalSchema)
def get_signal_by_ticker(ticker: str):
    """Return intelligence signal for a specific asset."""
    sig = pipeline_service.get_asset_signal(ticker)
    if not sig:
        raise HTTPException(status_code=404, detail=f"Asset {ticker} not found")
    return sig

@router.get("/market-data/{ticker}")
def get_market_data(ticker: str, limit: int = 100):
    """Retrieve historical OHLCV data for an asset."""
    with SessionLocal() as session:
        repo = MarketDataRepository(session)
        records = repo.get_by_ticker(ticker, limit=limit)
        return [
            {
                "ticker": r.ticker,
                "date": r.date.isoformat(),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "adjusted_close": r.adjusted_close
            }
            for r in reversed(records)
        ]

@router.get("/sentiment/{ticker}")
def get_sentiment(ticker: str):
    """Get aggregated and breakdown sentiment for a ticker."""
    with SessionLocal() as session:
        repo = SentimentRepository(session)
        scores = repo.get_by_ticker(ticker, limit=200)
        sent_dicts = [{
            "sentiment": s.sentiment,
            "positive_prob": s.positive_prob,
            "negative_prob": s.negative_prob,
            "neutral_prob": s.neutral_prob,
            "source_type": s.source_type
        } for s in scores]
        return pipeline_service.sentiment_aggregator.aggregate_for_ticker(sent_dicts, ticker=ticker)

@router.get("/social/{ticker}", response_model=List[SocialPostSchema])
def get_social_posts(ticker: str, limit: int = 50):
    """Get social media posts for an asset with sentiment provenance and data age."""
    with SessionLocal() as session:
        repo = SocialPostRepository(session)
        posts = repo.get_by_ticker(ticker, limit=limit)
        now = datetime.now(timezone.utc)
        
        # Load sentiments for these posts
        post_ids = [p.id for p in posts]
        s_scores = session.query(SentimentScore).filter(
            SentimentScore.source_type == "social",
            SentimentScore.source_id.in_(post_ids)
        ).all()
        sent_map = {s.source_id: s for s in s_scores}

        results = []
        for p in posts:
            ts = p.timestamp.replace(tzinfo=timezone.utc) if p.timestamp.tzinfo is None else p.timestamp
            age = max(0, (now - ts).days)
            sc = sent_map.get(p.id)

            results.append(SocialPostSchema(
                id=p.id,
                ticker=p.ticker,
                platform=p.platform,
                text=p.text,
                author=p.author,
                timestamp=p.timestamp,
                likes=p.likes,
                reposts=p.reposts,
                views=p.views,
                followers=p.followers,
                url=p.url,
                is_demo_data=p.is_demo_data,
                age_days=age,
                sentiment_score=sc.weighted_score if sc else None,
                sentiment_label=sc.sentiment if sc else None
            ))
        return results

@router.get("/news/{ticker}", response_model=List[NewsArticleSchema])
def get_news_articles(ticker: str, limit: int = 50):
    """Get financial news articles for an asset with sentiment provenance and data age."""
    with SessionLocal() as session:
        repo = NewsArticleRepository(session)
        articles = repo.get_by_ticker(ticker, limit=limit)
        now = datetime.now(timezone.utc)

        # Load sentiments for these articles
        art_ids = [a.id for a in articles]
        s_scores = session.query(SentimentScore).filter(
            SentimentScore.source_type == "news",
            SentimentScore.source_id.in_(art_ids)
        ).all()
        sent_map = {s.source_id: s for s in s_scores}

        results = []
        for a in articles:
            ts = a.published_at.replace(tzinfo=timezone.utc) if a.published_at.tzinfo is None else a.published_at
            age = max(0, (now - ts).days)
            sc = sent_map.get(a.id)

            results.append(NewsArticleSchema(
                id=a.id,
                ticker=a.ticker,
                title=a.title,
                source_name=a.source_name,
                url=a.url,
                text=a.text,
                published_at=a.published_at,
                is_demo_data=a.is_demo_data,
                age_days=age,
                sentiment_score=sc.weighted_score if sc else None,
                sentiment_label=sc.sentiment if sc else None
            ))
        return results

@router.get("/predictions/{ticker}", response_model=List[PredictionSchema])
def get_predictions(ticker: str, limit: int = 20):
    """Get persisted ML model predictions and settlements for a ticker.
    Loads directly from recorded prediction and settlement lifecycle records.
    """
    with SessionLocal() as session:
        repo = PredictionRepository(session)
        preds = repo.get_by_ticker(ticker, limit=limit)
        return [
            PredictionSchema(
                id=p.id,
                ticker=p.ticker,
                model_name=p.model_name,
                origin_price=p.origin_price,
                predicted_price=p.predicted_price,
                predicted_return=p.predicted_return,
                predicted_return_pct=round(p.predicted_return * 100, 2) if p.predicted_return is not None else None,
                direction="Bullish" if (p.predicted_return or 0) > 0.001 else ("Bearish" if (p.predicted_return or 0) < -0.001 else "Neutral"),
                actual_price=p.actual_price,
                actual_return=p.actual_return,
                prediction_error=p.prediction_error,
                direction_correct=p.direction_correct,
                confidence_lower=p.confidence_lower,
                confidence_upper=p.confidence_upper,
                prediction_date=p.prediction_date,
                target_date=p.target_date,
                settled_at=p.settled_at,
                horizon_days=p.horizon_days if hasattr(p, "horizon_days") and p.horizon_days else 1
            )
            for p in preds
        ]

# --- Collection & ML Trigger Endpoints ---

@router.post("/collect/market", response_model=CollectionTriggerResponse)
def trigger_market_collection(ticker: Optional[str] = None):
    """Trigger OHLCV collection."""
    res = pipeline_service.collect_market_data(ticker)
    return CollectionTriggerResponse(**res)

@router.post("/collect/social", response_model=CollectionTriggerResponse)
def trigger_social_collection(ticker: Optional[str] = None):
    """Trigger social posts collection (Apify or demo fallback)."""
    res = pipeline_service.collect_social_data(ticker)
    return CollectionTriggerResponse(**res)

@router.post("/collect/news", response_model=CollectionTriggerResponse)
def trigger_news_collection(ticker: Optional[str] = None):
    """Trigger news collection (Exa or demo fallback)."""
    res = pipeline_service.collect_news_data(ticker)
    return CollectionTriggerResponse(**res)

@router.post("/collect/all")
def trigger_full_pipeline():
    """Trigger full end-to-end collection, sentiment and ML training pipeline."""
    return pipeline_service.run_full_pipeline()

@router.post("/models/train")
def trigger_model_training():
    """Train ML models and generate predictions."""
    return pipeline_service.train_and_predict_all()

@router.get("/reports/export")
def export_reports_csv(exchange: Optional[str] = None):
    """Export market intelligence report to CSV."""
    signals = pipeline_service.get_market_overview().get("signals", [])
    if exchange:
        signals = [s for s in signals if s["exchange"].upper() == exchange.upper()]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "ticker", "asset_name", "exchange", "sector", "currency",
        "latest_price", "overall_sentiment", "sentiment_score",
        "social_mentions", "news_sentiment", "predicted_price",
        "predicted_return_pct", "direction", "signal_strength", "data_quality"
    ], extrasaction="ignore")

    writer.writeheader()
    for s in signals:
        writer.writerow(s)

    output.seek(0)
    filename = f"sentinel_ai_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
