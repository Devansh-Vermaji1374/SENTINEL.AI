"""
SENTINEL AI - Model Evaluation
==============================
Financial-aware evaluation metrics including directional accuracy,
financial loss metrics, residual statistics, and baseline (previous-close
and mean-return) comparisons.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluate financial predictive model performance with rigorous quantitative metrics.

    All methods are static to allow invocation across training, validation,
    and live backtesting routines.
    """

    @staticmethod
    def calculate_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        neutral_threshold: float = 0.001,
        y_train_mean: Optional[float] = None,
    ) -> Dict[str, float]:
        """Calculate a comprehensive set of financial ML evaluation metrics.

        Metrics computed:
        - **MAE** – Mean Absolute Error
        - **RMSE** – Root Mean Squared Error
        - **MARE / Mean Return Error** – Absolute percentage return error
        - **Directional Accuracy** – Correct sign prediction with neutral threshold handling
        - **Bias** – Mean prediction error (mean(y_pred - y_true))
        - **Residual Std** – Standard deviation of residuals for confidence intervals
        - **R² / Out-of-Sample R²** – Coefficient of determination vs mean

        Args:
            y_true: Actual returns.
            y_pred: Predicted returns.
            neutral_threshold: Threshold below which return is considered neutral (default 0.1% or 0.001).
            y_train_mean: Optional mean of training targets for true out-of-sample R².

        Returns:
            Dictionary keyed by metric name.
        """
        y_true = np.asarray(y_true, dtype=np.float64)
        y_pred = np.asarray(y_pred, dtype=np.float64)

        if len(y_true) == 0:
            logger.warning("Empty arrays passed to calculate_metrics.")
            return {
                "mae": np.nan,
                "rmse": np.nan,
                "directional_accuracy": np.nan,
                "bias": np.nan,
                "residual_std": np.nan,
                "r_squared": np.nan,
            }

        residuals = y_pred - y_true  # positive if model overpredicts
        errors = y_true - y_pred

        # 1. MAE
        mae = float(np.mean(np.abs(errors)))

        # 2. RMSE
        rmse = float(np.sqrt(np.mean(errors ** 2)))

        # 3. Bias
        bias = float(np.mean(residuals))

        # 4. Residual standard deviation (unbiased estimator)
        if len(residuals) > 1:
            residual_std = float(np.std(residuals, ddof=1))
        else:
            residual_std = float(np.std(residuals))

        # 5. Directional Accuracy with neutral zone
        # Both positive (> eps) or both negative (< -eps) or both neutral (|y| <= eps)
        true_dir = np.where(y_true > neutral_threshold, 1, np.where(y_true < -neutral_threshold, -1, 0))
        pred_dir = np.where(y_pred > neutral_threshold, 1, np.where(y_pred < -neutral_threshold, -1, 0))
        directional_accuracy = float(np.mean(true_dir == pred_dir))

        # 6. Out-of-sample R²
        ss_res = np.sum(errors ** 2)
        benchmark_mean = y_train_mean if y_train_mean is not None else np.mean(y_true)
        ss_tot = np.sum((y_true - benchmark_mean) ** 2)
        r_squared = float(1.0 - ss_res / ss_tot) if ss_tot > 1e-12 else np.nan

        # 7. MAPE (Mean Absolute Percentage Error on returns, handled safely)
        # In financial return forecasting, y_true is near zero, causing MAPE to explode.
        # We cap or mask extreme divisors to avoid mathematical artifact inflation.
        abs_true = np.abs(y_true)
        valid_mask = abs_true > 0.005  # only on return moves > 0.5%
        if np.any(valid_mask):
            mape = float(np.mean(np.abs(errors[valid_mask]) / abs_true[valid_mask]))
        else:
            mape = float(mae / (np.mean(abs_true) + 1e-6))

        metrics = {
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "directional_accuracy": directional_accuracy,
            "bias": bias,
            "residual_std": residual_std,
            "r_squared": r_squared,
        }

        return metrics

    @staticmethod
    def baseline_metrics(
        y_true: np.ndarray,
        y_train: Optional[np.ndarray] = None,
        neutral_threshold: float = 0.001,
    ) -> Dict[str, Any]:
        """Calculate benchmark metrics for:
        1. Naïve previous-close baseline (predicted return = 0.0).
        2. Historical mean-return baseline (predicted return = mean(y_train)).

        Args:
            y_true: Actual test returns.
            y_train: Historical training returns for mean baseline.
            neutral_threshold: Threshold for neutral direction classification.

        Returns:
            Dict containing 'naive_zero' metrics and 'historical_mean' metrics.
        """
        y_true = np.asarray(y_true, dtype=np.float64)
        zero_preds = np.zeros_like(y_true)
        naive_metrics = ModelEvaluator.calculate_metrics(
            y_true, zero_preds, neutral_threshold=neutral_threshold
        )

        mean_val = float(np.mean(y_train)) if (y_train is not None and len(y_train) > 0) else 0.0
        mean_preds = np.full_like(y_true, mean_val)
        mean_metrics = ModelEvaluator.calculate_metrics(
            y_true, mean_preds, neutral_threshold=neutral_threshold, y_train_mean=mean_val
        )

        return {
            "naive_zero": naive_metrics,
            "historical_mean": mean_metrics,
            "mae": naive_metrics["mae"],
            "rmse": naive_metrics["rmse"],
            "directional_accuracy": naive_metrics["directional_accuracy"],
            "r_squared": 0.0,
        }

    @staticmethod
    def compare_models(results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Compare metrics across all trained models."""
        rows: List[Dict[str, Any]] = []

        for model_name, data in results.items():
            metrics = data.get("metrics", {})
            row = {"model": model_name, **metrics}
            rows.append(row)

        if not rows:
            logger.warning("No model results to compare.")
            return pd.DataFrame()

        return pd.DataFrame(rows).set_index("model").sort_values("rmse", ascending=True)

    @staticmethod
    def prediction_vs_actual(
        predictions: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """Create a DataFrame of predicted vs. actual values."""
        records: List[Dict[str, Any]] = []

        for entry in predictions:
            actuals = np.asarray(entry.get("actuals", []))
            preds = np.asarray(entry.get("predictions", []))
            window_id = entry.get("window", 0)

            for a, p in zip(actuals, preds, strict=False):
                records.append(
                    {"actual": float(a), "predicted": float(p), "window": window_id}
                )

        return pd.DataFrame(records)
