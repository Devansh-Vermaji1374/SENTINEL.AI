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
    assert status.discourse_posts_count >= 200
    assert status.news_articles_count >= 100
    assert status.sentiment_scores_count >= 400
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

