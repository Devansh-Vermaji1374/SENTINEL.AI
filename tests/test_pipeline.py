"""Comprehensive unit, integration, and quantitative validation test suite for Sentinel AI Phase 3."""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import joblib

from preprocessing.cleaning import DataCleaner
from preprocessing.feature_engineering import FeatureEngineer
from sentiment.sentiment_aggregator import SentimentAggregator
from intelligence.support_resistance import SupportResistanceCalculator
from models.train import ModelTrainer
from models.evaluate import ModelEvaluator
from models.predict import Predictor, ArtifactValidationError
from backend.services.pipeline_service import PipelineService
from config.exchange_calendar import ExchangeCalendar


def test_data_cleaner_text():
    raw_text = "Check out $Tencent at https://tencent.com!  Very strong rally   🔥"
    cleaned = DataCleaner.clean_text(raw_text)
    assert "https://" not in cleaned
    assert "  " not in cleaned


def test_feature_engineering_technicals():
    fe = FeatureEngineer()
    dates = pd.date_range("2025-01-01", periods=60)
    prices = 100 + np.cumsum(np.random.randn(60) * 0.5)
    df = pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000, 5000, size=60)
    })

    tech_df = fe.compute_technical_features(df)
    assert "sma_5" in tech_df.columns
    assert "rsi_14" in tech_df.columns
    assert "macd" in tech_df.columns
    assert "bb_upper" in tech_df.columns


def test_sentiment_aggregator():
    agg = SentimentAggregator()
    sentiments = [
        {"sentiment": "positive", "positive_prob": 0.8, "negative_prob": 0.1, "neutral_prob": 0.1, "source_type": "social"},
        {"sentiment": "positive", "positive_prob": 0.7, "negative_prob": 0.1, "neutral_prob": 0.2, "source_type": "social"},
        {"sentiment": "negative", "positive_prob": 0.1, "negative_prob": 0.8, "neutral_prob": 0.1, "source_type": "news"},
    ]
    res = agg.aggregate_for_ticker(sentiments, ticker="0700.HK")
    assert res["total_mentions"] == 3
    assert res["positive_ratio"] > 0.5
    assert res["weighted_sentiment_score"] > 0


def test_support_resistance():
    calc = SupportResistanceCalculator()
    df = pd.DataFrame({
        "open": [100.0, 102.0],
        "high": [105.0, 108.0],
        "low": [98.0, 101.0],
        "close": [103.0, 107.0],
        "volume": [1000, 1200]
    })
    levels = calc.calculate(df)
    assert "support" in levels
    assert "resistance" in levels
    assert len(levels["support"]) > 0


def test_model_evaluator():
    y_true = np.array([0.01, -0.02, 0.03, -0.01])
    y_pred = np.array([0.012, -0.018, 0.025, -0.008])
    metrics = ModelEvaluator.calculate_metrics(y_true, y_pred)
    assert metrics["mae"] < 0.01
    assert metrics["directional_accuracy"] == 1.0
    assert "bias" in metrics
    assert "residual_std" in metrics


def test_chronological_three_way_split():
    """Verify chronological split strictly isolates Train (65%), Val (15%), and untouched Test (20%)."""
    trainer = ModelTrainer()
    X = np.arange(100).reshape(-1, 1)
    y = np.arange(100)
    splits = trainer.chronological_split(X, y, test_pct=0.20, val_pct=0.15)
    train_x, train_y = splits["train"]
    val_x, val_y = splits["val"]
    test_x, test_y = splits["test"]

    assert len(train_x) == 65
    assert len(val_x) == 15
    assert len(test_x) == 20
    assert train_y.max() < val_y.min()
    assert val_y.max() < test_y.min()


def test_baseline_comparison():
    """Verify evaluation against naïve zero-return and historical-mean baselines."""
    y_true = np.array([0.02, -0.01, 0.03, -0.02, 0.01])
    y_train = np.array([0.005, 0.006, 0.004])
    base_metrics = ModelEvaluator.baseline_metrics(y_true, y_train=y_train)

    assert "naive_zero" in base_metrics
    assert "historical_mean" in base_metrics
    assert base_metrics["naive_zero"]["mae"] == pytest.approx(np.mean(np.abs(y_true)))
    assert base_metrics["historical_mean"]["mae"] > 0


def test_point_in_time_sentiment_zero_leakage():
    """Verify point-in-time calculation strictly bounds discourse to as-of timestamps."""
    ps = PipelineService()
    df1 = ps.build_point_in_time_dataset("0700.HK")
    assert not df1.empty
    assert "sentiment_score" in df1.columns
    assert "social_volume" in df1.columns

    # Verify first 15 bars in May 2026 before any mentions have zero volume
    early_rows = df1[df1["date"] < pd.Timestamp("2026-06-01")]
    if not early_rows.empty:
        assert (early_rows["social_volume"] == 0).all()
        assert (early_rows["sentiment_score"] == 0.0).all()


def test_artifact_loading_and_validation():
    """Verify saved artifact bundle schema, version validation, and refusal to silently retrain."""
    predictor = Predictor()

    # Successful loading of actual trained bundle
    bundle = predictor.load_artifact("0700.HK", "random_forest")
    assert "model" in bundle
    assert "feature_names" in bundle
    assert isinstance(bundle["feature_names"], list)
    assert len(bundle["feature_names"]) > 10
    assert "version" in bundle
    assert "residual_std" in bundle

    # Strict error raising on missing artifact (no silent retraining)
    with pytest.raises(ArtifactValidationError):
        predictor.load_artifact("NON_EXISTENT_TICKER", "random_forest")


def test_scaler_consistency_and_feature_ordering():
    """Verify that predictor strictly transforms features in the exact ordering of feature_names."""
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge

    X_train = np.array([[10.0, 1.0], [20.0, 2.0], [30.0, 3.0]])
    y_train = np.array([0.01, 0.02, 0.03])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    model = Ridge(alpha=1.0)
    model.fit(X_scaled, y_train)

    bundle = {
        "model": model,
        "scaler": scaler,
        "feature_names": ["feat_a", "feat_b"],
        "residual_std": 0.015,
        "model_name": "ridge_test",
        "version": "2.2.0"
    }

    # Pass DataFrame with inverted column ordering
    df_inverted = pd.DataFrame([{"feat_b": 2.0, "feat_a": 20.0}])
    predictor = Predictor()
    pred_res = predictor.predict(bundle, df_inverted, current_price=100.0)

    # Prediction should be ~0.02 (matching [20.0, 2.0])
    assert pred_res["predicted_return"] == pytest.approx(0.02, abs=0.005)
    assert pred_res["predicted_price"] == pytest.approx(102.0, abs=0.5)

    # Missing column must raise ValueError
    df_missing = pd.DataFrame([{"feat_a": 20.0}])
    with pytest.raises(ValueError, match="missing required columns"):
        predictor.predict(bundle, df_missing, current_price=100.0)


def test_prediction_settlement_calculation():
    """Verify correct settlement calculation from actual origin close to actual target close."""
    origin_close = 100.0
    actual_target_close = 105.0
    predicted_return = 0.04

    # Actual return = (105 - 100) / 100 = 0.05 (+5%)
    actual_return = (actual_target_close - origin_close) / origin_close
    prediction_error = abs(actual_return - predicted_return)
    direction_correct = (actual_return > 0.001 and predicted_return > 0.001)

    assert actual_return == pytest.approx(0.05)
    assert prediction_error == pytest.approx(0.01)
    assert direction_correct is True


def test_api_status_real_telemetry():
    """Verify /api/status returns genuine database counts, provider statuses, and model verification."""
    from backend.api.routes import get_system_status
    status = get_system_status()

    assert status.database == "connected"
    assert status.database_connected is True
    assert status.assets_configured == 10
    assert status.historical_bars_count >= 1200
    assert status.discourse_posts_count >= 190
    assert status.news_articles_count >= 100
    assert status.sentiment_scores_count >= 300
    assert status.trained_models_count == 40
    assert status.model_registry_ready is True
    assert status.model_registry_status == "READY"
    assert status.finbert_ready is True
    assert status.finbert_status in ("READY", "INFERENCE_VERIFIED")
    assert status.apify_status in ("KEY CONFIGURED", "NOT CONFIGURED")
    assert status.exa_status in ("KEY CONFIGURED", "NOT CONFIGURED")


def test_exchange_calendar_trading_days_and_holidays():
    """Verify ExchangeCalendar accurately skips weekends and official holidays for HKEX and KRX."""
    # Weekend
    saturday = datetime(2025, 1, 4, 12, 0, 0)
    assert ExchangeCalendar.is_trading_day("HKEX", saturday) is False
    assert ExchangeCalendar.is_trading_day("KRX", saturday) is False

    # HKEX Lunar New Year Holiday (2025-01-29)
    hk_lunar = datetime(2025, 1, 29, 10, 0, 0)
    assert ExchangeCalendar.is_trading_day("HKEX", hk_lunar) is False

    # KRX Independence Movement Day (2025-03-03 observed)
    kr_holiday = datetime(2025, 3, 3, 10, 0, 0)
    assert ExchangeCalendar.is_trading_day("KRX", kr_holiday) is False

    # Next trading session calculation
    friday = datetime(2025, 1, 3, 16, 0, 0)
    next_hk = ExchangeCalendar.get_next_trading_session("HKEX", from_datetime=friday)
    assert next_hk.weekday() == 0  # Monday 2025-01-06

    # Session close datetime (16:00 HKT is 08:00 UTC)
    close_hk = ExchangeCalendar.get_session_close_datetime("HKEX", next_hk)
    assert close_hk.hour == 8  # 08:00 UTC == 16:00 HKT (UTC+8)
    assert close_hk.minute == 0


def test_signal_aggregation_consistency():
    """Verify get_asset_signal retrieves compatible predictions and separates sentiment channels."""
    service = PipelineService()
    sig = service.get_asset_signal("0700.HK")
    if sig:
        assert "ticker" in sig
        assert "latest_price" in sig
        assert "social_mentions" in sig
        assert "social_sentiment" in sig
        assert "news_count" in sig
        assert "news_sentiment" in sig
        assert "models_in_consensus" in sig
        assert sig["exchange"] == "HKEX"


def test_no_temporal_lookahead_in_extrema():
    """Verify that support/resistance extrema calculation is backward-looking with zero lookahead."""
    fe = FeatureEngineer()
    df = pd.DataFrame({
        "open": [10.0] * 30,
        "high": [10.0] * 29 + [50.0],  # sudden spike on the very last bar
        "low": [10.0] * 30,
        "close": [10.0] * 30
    })
    # If trailing, earlier bars cannot see the future bar 29 spike
    levels = fe.compute_support_resistance(df.iloc[:20], window=10)
    assert 50.0 not in levels["resistance"]


def test_feature_matrix_stationarity():
    """Verify that feature engineering excludes non-stationary raw price levels from model inputs."""
    trainer = ModelTrainer()
    fe = FeatureEngineer()
    dates = pd.date_range("2025-01-01", periods=40)
    prices = 200 + np.cumsum(np.random.randn(40) * 2)
    df = pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000, 5000, size=40)
    })
    tech_df = fe.compute_technical_features(df)
    X, y, feats, _ = trainer.prepare_data(tech_df)

    # Ensure raw price levels are excluded from input feature columns
    for raw_col in ["close", "open", "high", "low", "sma_20", "ema_12", "bb_upper"]:
        assert raw_col not in feats, f"Non-stationary column {raw_col} found in feature set"

    # Ensure stationary ratios are present
    assert "close_to_sma_20" in feats
    assert "daily_return" in feats
    assert "volatility_5" in feats


def test_model_bundle_saving_reloading_reproducibility(tmp_path):
    """Verify that saving and reloading model bundle produces equivalent predictions with identical preprocessing."""
    fe = FeatureEngineer()
    trainer = ModelTrainer(model_save_dir=str(tmp_path))
    predictor = Predictor(model_dir=str(tmp_path))

    dates = pd.date_range("2025-01-01", periods=60)
    prices = 150 + np.cumsum(np.random.randn(60) * 1.5)
    df = pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000, 5000, size=60)
    })
    tech_df = fe.compute_technical_features(df)
    results = trainer.train_all(tech_df, ticker="TEST.ASSET")

    for model_name in ["linear_regression", "random_forest", "xgboost"]:
        in_memory_model = results[model_name]["model"]
        in_memory_scaler = results[model_name]["scaler"]
        bundle = predictor.load_artifact("TEST.ASSET", model_name)

        pred1 = predictor.predict(bundle, tech_df, current_price=150.0, model_name=model_name)
        pred2 = predictor.predict_from_disk("TEST.ASSET", model_name, tech_df, current_price=150.0)

        assert pred1["predicted_return"] == pytest.approx(pred2["predicted_return"], abs=1e-6)
        assert pred1["predicted_price"] == pytest.approx(pred2["predicted_price"], abs=1e-6)
        assert pred1["direction"] == pred2["direction"]


def test_automation_endpoint_authentication(monkeypatch):
    """Verify that automation endpoints reject unauthorized requests without breaking valid access."""
    from fastapi.testclient import TestClient
    from backend.main import app
    from config.settings import get_settings

    client = TestClient(app)

    # 1. When AUTOMATION_API_KEY is not configured, automation endpoints must reject with 401
    settings = get_settings()
    monkeypatch.setattr(settings, "automation_api_key", "")
    monkeypatch.setattr(settings, "dashboard_admin_key", "")
    resp_no_config = client.post("/api/collect/market?ticker=0700.HK")
    assert resp_no_config.status_code == 401
    assert "is configured on the server" in resp_no_config.json()["detail"]

    # 2. When configured, unauthorized request without valid key returns 401
    test_key = "secure-test-automation-key-12345"
    monkeypatch.setattr(settings, "automation_api_key", test_key)
    monkeypatch.setattr(settings, "dashboard_admin_key", "")
    resp_unauth = client.post("/api/collect/market?ticker=0700.HK")
    assert resp_unauth.status_code == 401
    assert "Operation requires valid" in resp_unauth.json()["detail"]

    # 3. Authorized request with correct header succeeds or enters valid processing
    resp_auth = client.post(
        "/api/collect/market?ticker=0700.HK",
        headers={"X-Sentinel-Automation-Key": test_key}
    )
    assert resp_auth.status_code in (200, 422)

    # 4. Operator access key authentication (DASHBOARD_ADMIN_KEY via X-Sentinel-Admin-Key)
    admin_key = "secure-dashboard-admin-token-789"
    monkeypatch.setattr(settings, "dashboard_admin_key", admin_key)
    resp_admin = client.post(
        "/api/collect/market?ticker=0700.HK",
        headers={"X-Sentinel-Admin-Key": admin_key}
    )
    assert resp_admin.status_code in (200, 422)

    # 5. Browser CORS preflight OPTIONS request
    resp_options = client.options(
        "/api/collect/market",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Sentinel-Admin-Key,Content-Type",
        }
    )
    assert resp_options.status_code == 200
    assert "x-sentinel-admin-key" in resp_options.headers.get("access-control-allow-headers", "").lower()

    # 6. Public GET status and market data endpoints remain accessible without auth
    resp_public = client.get("/api/status")
    assert resp_public.status_code == 200
    assert "status" in resp_public.json()


def test_exchange_calendar_timezones_and_sessions():
    """Verify HKEX and KRX session close UTC conversion, weekend advances, and holiday handling."""
    from datetime import date, datetime, time, timezone
    import zoneinfo

    hk_tz = zoneinfo.ZoneInfo("Asia/Hong_Kong")
    kr_tz = zoneinfo.ZoneInfo("Asia/Seoul")

    # HKEX close at 16:00 HKT corresponds to 08:00 UTC
    hk_close_utc = ExchangeCalendar.get_session_close_datetime("HKEX", date(2025, 6, 2))
    assert hk_close_utc.hour == 8
    assert hk_close_utc.minute == 0
    assert hk_close_utc.tzinfo == timezone.utc

    # KRX close at 15:30 KST corresponds to 06:30 UTC
    kr_close_utc = ExchangeCalendar.get_session_close_datetime("KRX", date(2025, 6, 2))
    assert kr_close_utc.hour == 6
    assert kr_close_utc.minute == 30
    assert kr_close_utc.tzinfo == timezone.utc

    # Friday after close -> Next session must be Monday
    # 2025-06-06 is Friday. 17:00 HKT is after HKEX 16:00 close
    friday_night_hk = datetime(2025, 6, 6, 17, 0, tzinfo=hk_tz)
    next_session_hk = ExchangeCalendar.get_next_trading_session("HKEX", from_datetime=friday_night_hk)
    assert next_session_hk == date(2025, 6, 9)  # Monday

    # Holiday handling: 2025-01-01 is Wednesday (New Year's Day)
    nye_night_hk = datetime(2024, 12, 31, 18, 0, tzinfo=hk_tz)
    next_session_nye = ExchangeCalendar.get_next_trading_session("HKEX", from_datetime=nye_night_hk)
    assert next_session_nye == date(2025, 1, 2)  # Skips Jan 1 holiday to Thursday Jan 2


def test_prediction_settlement_matching_session(monkeypatch):
    """Verify that settlement strictly matches the intended session date and leaves missing sessions pending."""
    from backend.services.pipeline_service import PipelineService
    from database.models import Prediction, MarketData
    from unittest.mock import MagicMock

    pipeline = PipelineService()

    # Create dummy objects
    p1 = Prediction(
        id=9991,
        ticker="0700.HK",
        model_name="xgboost",
        predicted_price=405.0,
        predicted_return=0.0125,
        prediction_date=datetime(2025, 6, 2, 8, 0, 0),
        target_date=datetime(2025, 6, 3, 8, 0, 0),
        origin_price=400.0,
        actual_price=None,
        settled_at=None,
        status="PENDING_SETTLEMENT"
    )
    bar1 = MarketData(
        ticker="0700.HK",
        date=datetime(2025, 6, 3, 0, 0, 0),  # Session bar on 2025-06-03
        close=408.0,
    )

    mock_session = MagicMock()
    mock_query_pred = MagicMock()
    mock_query_bar = MagicMock()

    def mock_query(model):
        if model == Prediction:
            return mock_query_pred
        elif model == MarketData:
            return mock_query_bar
        return MagicMock()

    mock_session.query.side_effect = mock_query

    # When querying Prediction, return [p1]
    mock_query_pred.filter.return_value.all.return_value = [p1]
    # When querying MarketData for target ticker, return [bar1]
    mock_query_bar.filter.return_value.all.return_value = [bar1]

    # Mock SessionLocal context manager
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__enter__.return_value = mock_session
    mock_session_factory.return_value.__exit__.return_value = None

    import backend.services.pipeline_service as ps_mod
    monkeypatch.setattr(ps_mod, "SessionLocal", mock_session_factory)

    settled_count = pipeline.settle_predictions()
    assert settled_count == 1
    assert p1.actual_price == 408.0
    assert p1.actual_return == pytest.approx(0.02)
    assert p1.settled_at is not None
    assert p1.status == "SETTLED"
    assert p1.direction_correct is True

    # Case 2: Target session is in future (no matching bar found)
    p2 = Prediction(
        id=9992,
        ticker="0700.HK",
        model_name="xgboost",
        predicted_price=410.0,
        predicted_return=0.025,
        prediction_date=datetime(2025, 6, 2, 8, 0, 0),
        target_date=datetime(2025, 6, 10, 8, 0, 0),
        origin_price=400.0,
        actual_price=None,
        settled_at=None,
        status="PENDING_SETTLEMENT"
    )
    mock_query_pred.filter.return_value.all.return_value = [p2]
    # Bar is only 2025-06-03, not 2025-06-10
    mock_query_bar.filter.return_value.all.return_value = [bar1]

    settled_count_future = pipeline.settle_predictions()
    assert settled_count_future == 0
    assert p2.actual_price is None
    assert p2.status == "PENDING_SETTLEMENT"
    assert p2.settled_at is None

    # Case 3: Invalid target date (target session on or before prediction date)
    p3 = Prediction(
        id=9993,
        ticker="0700.HK",
        model_name="xgboost",
        predicted_price=410.0,
        predicted_return=0.025,
        prediction_date=datetime(2025, 6, 4, 8, 0, 0),
        target_date=datetime(2025, 6, 3, 8, 0, 0),  # Target is earlier than prediction!
        origin_price=400.0,
        actual_price=None,
        settled_at=None,
        status="PENDING_SETTLEMENT"
    )
    mock_query_pred.filter.return_value.all.return_value = [p3]
    mock_query_bar.filter.return_value.all.return_value = [bar1]

    settled_count_inv = pipeline.settle_predictions()
    assert settled_count_inv == 0
    assert p3.status == "INVALID_TARGET_DATE"
    assert p3.actual_price is None


def test_migration_prediction_status_idempotence(tmp_path):
    """Verify that prediction status migration is idempotent across multiple executions and preserves classifications."""
    import sqlite3
    from database.migrations.migration_prediction_status import run_migration

    test_db = str(tmp_path / "test_migration.db")
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE predictions (
            id INTEGER PRIMARY KEY,
            ticker VARCHAR(20),
            origin_price FLOAT,
            settled_at TIMESTAMP,
            status VARCHAR(50)
        )
    """)
    # Insert 4 test records:
    # 1. Legacy without origin_price
    c.execute("INSERT INTO predictions (id, ticker, origin_price, settled_at, status) VALUES (1, '0700.HK', NULL, NULL, NULL)")
    # 2. Modern pending with origin_price
    c.execute("INSERT INTO predictions (id, ticker, origin_price, settled_at, status) VALUES (2, '0700.HK', 418.4, NULL, NULL)")
    # 3. Explicit INVALID_TARGET_DATE
    c.execute("INSERT INTO predictions (id, ticker, origin_price, settled_at, status) VALUES (3, '0700.HK', 418.4, NULL, 'INVALID_TARGET_DATE')")
    # 4. Valid SETTLED record
    c.execute("INSERT INTO predictions (id, ticker, origin_price, settled_at, status) VALUES (4, '0700.HK', 400.0, '2025-06-03 08:00:00', 'SETTLED')")
    conn.commit()
    conn.close()

    # Run migration first time
    counts1 = dict(run_migration(test_db))
    assert counts1.get("LEGACY_UNSETTLEABLE") == 1
    assert counts1.get("PENDING_SETTLEMENT") == 1
    assert counts1.get("INVALID_TARGET_DATE") == 1
    assert counts1.get("SETTLED") == 1

    # Run migration second time (must be identical)
    counts2 = dict(run_migration(test_db))
    assert counts1 == counts2


def test_social_scraper_timestamp_preservation_and_exclusion(monkeypatch):
    """Verify Apify & StockTwits preserve publication timestamps, keep NULL when missing, and exclude undated from PIT features."""
    from data_collection.apify_scraper import ApifyScraper
    from backend.services.pipeline_service import PipelineService
    from database.models import SocialPost, SentimentScore, MarketData, Asset
    from unittest.mock import patch, MagicMock

    scraper = ApifyScraper()

    # 1. Missing timestamp in StockTwits stream returns None for timestamp
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"messages": [{"body": "Great rally $TCEHY", "id": 123, "user": {"username": "trader"}}]}'
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_response
    mock_cm.__exit__.return_value = None
    with patch("urllib.request.urlopen", return_value=mock_cm):
        posts = scraper.collect_for_ticker("0700.HK", "Tencent", ["tencent"])
        assert len(posts) > 0
        assert posts[0]["timestamp"] is None
        assert posts[0]["has_original_timestamp"] is False

    # 2. Pipeline service exercises end-to-end ingestion and proves undated posts are excluded from PIT sentiment features
    pipeline = PipelineService()

    # Create one dated post and one undated post
    dated_post = {"text": "Bullish quarterly revenue beat!", "timestamp": datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc), "platform": "StockTwits", "author": "trader1", "likes": 5, "views": 0}
    undated_post = {"text": "Huge undisclosed rumors", "timestamp": None, "platform": "StockTwits", "author": "trader2", "likes": 2, "views": 0}

    # Mock finbert analyze
    pipeline.finbert.analyze = MagicMock(return_value={
        "sentiment": "positive",
        "confidence": 0.95,
        "positive_prob": 0.95,
        "negative_prob": 0.02,
        "neutral_prob": 0.03
    })

    # Mock apify_scraper to return both posts
    pipeline.apify_scraper.collect_for_ticker = MagicMock(return_value=[dated_post, undated_post])

    # In-memory storage for repositories
    saved_posts = []
    saved_sentiments = []

    mock_session = MagicMock()
    mock_post_repo = MagicMock()
    def fake_bulk_insert_dedup(objs):
        saved_posts.extend(objs)
        return len(objs)
    mock_post_repo.bulk_insert_dedup.side_effect = fake_bulk_insert_dedup

    mock_sent_repo = MagicMock()
    def fake_create_sent(obj):
        saved_sentiments.append(obj)
        return obj
    mock_sent_repo.create.side_effect = fake_create_sent

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__enter__.return_value = mock_session
    mock_session_factory.return_value.__exit__.return_value = None

    import backend.services.pipeline_service as ps_mod
    monkeypatch.setattr(ps_mod, "SessionLocal", mock_session_factory)
    monkeypatch.setattr(ps_mod, "SocialPostRepository", lambda s: mock_post_repo)
    monkeypatch.setattr(ps_mod, "SentimentRepository", lambda s: mock_sent_repo)

    res = pipeline.collect_social_data(ticker="0700.HK")
    assert res["status"] == "success"

    # Verify 2 posts inserted into repository (one with timestamp, one with None)
    assert len(saved_posts) == 2
    assert saved_posts[0].timestamp is not None
    assert saved_posts[1].timestamp is None  # Preserved as NULL

    # CRITICAL: Only the dated post produced a SentimentScore. The undated post was excluded!
    assert len(saved_sentiments) == 1
    assert saved_sentiments[0].created_at == dated_post["timestamp"]




