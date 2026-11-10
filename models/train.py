"""
SENTINEL AI - Model Training Pipeline
======================================
Trains verified machine learning architectures:
1. Linear Regression (Ridge regularized for indicator collinearity)
2. Random Forest Regressor
3. XGBoost Regressor
4. Deep Learning MLP ANN (bounded regularized architecture)

Strict Quantitative Validation Methodology:
- Chronological Train (65%), Validation (15%), and Untouched Holdout Test (20%).
- Validation fold used solely for hyperparameter tuning / early stopping.
- Final test fold is kept untouched until final evaluation.
- All models evaluated against Naïve Previous-Close (Zero-Return) & Historical Mean Return benchmarks.
- Reports MAE, RMSE, Directional Accuracy (with deadband), Bias, and Out-of-Sample R².
- Complete self-contained artifact bundles saved with version, scaler, feature list, and residual std.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from models.evaluate import ModelEvaluator

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Trains predictive models using strictly chronological historical data."""

    def __init__(self, model_save_dir: str = "models/saved") -> None:
        self.model_save_dir = Path(model_save_dir)
        self.model_save_dir.mkdir(parents=True, exist_ok=True)

    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        target_col: str = "target_return"
    ) -> Tuple[np.ndarray, np.ndarray, List[str], pd.Series]:
        """Extract chronological feature matrix X and target y.
        Never shuffles observations.
        """
        df = df.copy()
        if target_col not in df.columns:
            if "close" in df.columns:
                df[target_col] = df["close"].pct_change().shift(-1)
            else:
                raise ValueError("DataFrame must contain 'close' or specified target_col")

        if feature_cols is None:
            # Exclude non-stationary raw price levels, volume scales, unnormalized indicators, and identifiers
            exclude_cols = {
                "date", "ticker", "id", "created_at", target_col,
                "open", "high", "low", "close", "adjusted_close",
                "sma_5", "sma_10", "sma_20", "sma_50", "ema_12", "ema_26",
                "bb_middle", "bb_upper", "bb_lower", "volume", "volume_sma_20",
                "macd", "macd_signal", "macd_histogram"  # Replaced by macd_norm, macd_signal_norm, macd_hist_norm
            }
            feature_cols = [
                c for c in df.columns
                if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])
            ]

        # Clean NaN values strictly
        clean_df = df.dropna(subset=feature_cols + [target_col]).copy()
        clean_df = clean_df.sort_values(by="date" if "date" in clean_df.columns else clean_df.index)

        X = clean_df[feature_cols].values.astype(np.float64)
        y = clean_df[target_col].values.astype(np.float64)
        dates = clean_df["date"] if "date" in clean_df.columns else pd.Series(clean_df.index)

        return X, y, feature_cols, dates

    def chronological_split(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_pct: float = 0.20,
        val_pct: float = 0.15
    ) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """Split data chronologically into train, validation, and untouched test partitions.

        Train: 0 -> n - (test_size + val_size)
        Val:   n - (test_size + val_size) -> n - test_size  (used for validation/tuning)
        Test:  n - test_size -> n  (strictly untouched test partition)
        """
        n = len(X)
        test_size = int(n * test_pct)
        val_size = int(n * val_pct)
        train_size = n - test_size - val_size

        if train_size < 20:
            train_size = max(10, int(n * 0.70))
            test_size = n - train_size
            val_size = 0

        X_train, y_train = X[:train_size], y[:train_size]
        X_val = X[train_size:train_size + val_size] if val_size > 0 else np.empty((0, X.shape[1]))
        y_val = y[train_size:train_size + val_size] if val_size > 0 else np.empty(0)
        X_test, y_test = X[train_size + val_size:], y[train_size + val_size:]

        return {
            "train": (X_train, y_train),
            "val": (X_val, y_val),
            "test": (X_test, y_test)
        }

    def walk_forward_validate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_name: str = "random_forest",
        n_windows: int = 4,
        min_train_size: int = 40
    ) -> List[Dict[str, Any]]:
        """Perform expanding-window chronological walk-forward validation.
        Fits scaler strictly on each window's training partition.
        """
        n = len(y)
        available = n - min_train_size
        if available < n_windows:
            return []

        step = available // n_windows
        results = []

        for w in range(n_windows):
            split_idx = min_train_size + w * step
            end_idx = min(split_idx + step, n)

            X_tr, y_tr = X[:split_idx], y[:split_idx]
            X_te, y_te = X[split_idx:end_idx], y[split_idx:end_idx]

            if len(X_te) == 0:
                continue

            model = self._instantiate_model(model_name)

            if m_needs_scaling(model_name):
                scaler = StandardScaler()
                X_tr_proc = np.clip(scaler.fit_transform(X_tr), -3.0, 3.0)
                X_te_proc = np.clip(scaler.transform(X_te), -3.0, 3.0)
                model.fit(X_tr_proc, y_tr)
                preds = model.predict(X_te_proc)
            else:
                model.fit(X_tr, y_tr)
                preds = model.predict(X_te)

            metrics = ModelEvaluator.calculate_metrics(y_te, preds)
            results.append({
                "window": w + 1,
                "train_size": len(X_tr),
                "test_size": len(X_te),
                "metrics": metrics
            })

        return results

    def _instantiate_model(self, model_name: str) -> Any:
        if model_name == "linear_regression":
            # Well-regularized Ridge regression to combat multicollinearity in stationary financial ratios
            return Ridge(alpha=50.0, random_state=42)
        elif model_name == "random_forest":
            # Shallow trees with high leaf regularization to prevent fitting noise on small time-series samples
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=3,
                min_samples_leaf=6,
                max_features="sqrt",
                random_state=42
            )
        elif model_name == "xgboost":
            # Highly regularized shallow trees with conservative learning rate
            return XGBRegressor(
                n_estimators=50,
                max_depth=2,
                learning_rate=0.02,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=1.0,
                reg_lambda=5.0,
                random_state=42
            )
        elif model_name in ("deep_learning_ann", "ann"):
            # Compact regularized MLP with high weight decay to avoid overfitting noise
            return MLPRegressor(
                hidden_layer_sizes=(8,),
                activation="relu",
                alpha=50.0,
                max_iter=500,
                random_state=42,
                early_stopping=False
            )
        else:
            raise ValueError(f"Unknown model architecture: {model_name}")

    def train_all(
        self,
        df: pd.DataFrame,
        ticker: str,
        feature_cols: Optional[List[str]] = None,
        target_col: str = "target_return"
    ) -> Dict[str, Dict[str, Any]]:
        """Fit all 4 model architectures on actual historical data and save self-contained bundles.

        Strict chronological 3-way split:
        - Train fold (65%): Used to fit models and transformers.
        - Validation fold (15%): Used for validation checks.
        - Untouched Test fold (20%): Evaluated once for reported holdout metrics.
        """
        X, y, features, dates = self.prepare_data(df, feature_cols, target_col)
        splits = self.chronological_split(X, y, test_pct=0.20, val_pct=0.15)
        X_train, y_train = splits["train"]
        X_val, y_val = splits["val"]
        X_test, y_test = splits["test"]

        # Calculate Naïve Previous-Close baseline and Mean baseline on untouched test fold
        baseline_metrics = ModelEvaluator.baseline_metrics(y_test, y_train=y_train)

        model_names = ["linear_regression", "random_forest", "xgboost", "deep_learning_ann"]
        results = {}

        # Standardize features for linear model & neural network (fitted strictly on train fold)
        scaler = StandardScaler()
        X_train_scaled = np.clip(scaler.fit_transform(X_train), -3.0, 3.0)
        X_test_scaled = np.clip(scaler.transform(X_test), -3.0, 3.0)
        X_val_scaled = np.clip(scaler.transform(X_val), -3.0, 3.0) if len(X_val) > 0 else np.empty(0)

        for m_name in model_names:
            try:
                model = self._instantiate_model(m_name)
                saved_scaler = None

                if m_needs_scaling(m_name):
                    model.fit(X_train_scaled, y_train)
                    val_preds = model.predict(X_val_scaled) if len(X_val) > 0 else None
                    preds = model.predict(X_test_scaled)
                    saved_scaler = scaler
                    wf_results = self.walk_forward_validate(X, y, model_name=m_name)
                else:
                    model.fit(X_train, y_train)
                    val_preds = model.predict(X_val) if len(X_val) > 0 else None
                    preds = model.predict(X_test)
                    wf_results = self.walk_forward_validate(X, y, model_name=m_name)

                # Validation fold metrics (for selection/audit)
                val_metrics = (
                    ModelEvaluator.calculate_metrics(y_val, val_preds, y_train_mean=float(np.mean(y_train)))
                    if val_preds is not None and len(y_val) > 0 else {}
                )

                # Final untouched test fold metrics
                metrics = ModelEvaluator.calculate_metrics(
                    y_test, preds, y_train_mean=float(np.mean(y_train))
                )
                residuals = preds - y_test
                residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else float(np.std(residuals))

                # Bundle evaluation artifact dictionary
                eval_bundle = {
                    "model": model,
                    "scaler": saved_scaler,
                    "feature_names": features,
                    "target_col": target_col,
                    "horizon": 1,
                    "ticker": ticker,
                    "model_name": m_name,
                    "artifact_type": "evaluation",
                    "version": "2.2.0",
                    "trained_at": datetime.now(timezone.utc).isoformat(),
                    "training_samples": len(X_train),
                    "validation_samples": len(X_val),
                    "test_samples": len(X_test),
                    "residual_std": residual_std,
                    "validation_metrics": val_metrics,
                    "test_metrics": metrics,
                    "baseline_metrics": baseline_metrics
                }

                # Fit deployment model on full historical dataset
                deploy_model = self._instantiate_model(m_name)
                deploy_scaler = None
                if m_needs_scaling(m_name):
                    deploy_scaler = StandardScaler()
                    X_full_scaled = np.clip(deploy_scaler.fit_transform(X), -3.0, 3.0)
                    deploy_model.fit(X_full_scaled, y)
                else:
                    deploy_model.fit(X, y)

                deploy_bundle = {
                    "model": deploy_model,
                    "scaler": deploy_scaler,
                    "feature_names": features,
                    "target_col": target_col,
                    "horizon": 1,
                    "ticker": ticker,
                    "model_name": m_name,
                    "artifact_type": "deployment",
                    "version": "2.2.0",
                    "trained_at": datetime.now(timezone.utc).isoformat(),
                    "training_samples": len(X),
                    "validation_samples": len(X_val),
                    "test_samples": len(X_test),
                    "residual_std": residual_std,
                    "validation_metrics": val_metrics,
                    "test_metrics": metrics,
                    "baseline_metrics": baseline_metrics
                }

                # Save evaluation bundle
                eval_file = self.model_save_dir / f"{ticker}_{m_name}_eval.joblib"
                joblib.dump(eval_bundle, eval_file)

                # Save deployment bundle (the live inference source)
                model_file = self.model_save_dir / f"{ticker}_{m_name}.joblib"
                joblib.dump(deploy_bundle, model_file)

                # Save JSON metadata for telemetry & API inspection
                meta = {
                    "ticker": ticker,
                    "model_name": m_name,
                    "version": "2.2.0",
                    "trained_at": deploy_bundle["trained_at"],
                    "artifact_type": "deployment",
                    "training_samples": len(X),
                    "holdout_training_samples": len(X_train),
                    "validation_samples": len(X_val),
                    "test_samples": len(X_test),
                    "features": features,
                    "residual_std": residual_std,
                    "metrics": metrics,
                    "val_metrics": val_metrics,
                    "baseline_metrics": baseline_metrics,
                    "walk_forward": wf_results
                }
                meta_file = self.model_save_dir / f"{ticker}_{m_name}_meta.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)

                results[m_name] = {
                    "model": deploy_model,
                    "scaler": deploy_scaler,
                    "metrics": metrics,
                    "baseline_metrics": baseline_metrics,
                    "residual_std": residual_std,
                    "walk_forward": wf_results,
                    "model_path": str(model_file),
                    "meta_path": str(meta_file),
                    "predictions": preds.tolist(),
                    "actuals": y_test.tolist()
                }
            except Exception as e:
                logger.error("Failed to train %s for %s: %s", m_name, ticker, e)

        return results


def m_needs_scaling(model_name: str) -> bool:
    """Helper to check if model architecture requires feature scaling."""
    return model_name in ("deep_learning_ann", "ann", "linear_regression")
