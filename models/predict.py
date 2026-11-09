"""
SENTINEL AI - Prediction Engine
================================
Generate predictions using trained model bundles, with exact feature schema
matching, pre-saved scalers, and calibrated statistical uncertainty bounds.

Persisted Model Inference Rules:
- Saved model bundles on disk are the actual inference source.
- Validates bundle schema: model, feature_names, version, scaler, residual_std.
- Never silently retrains if an artifact is missing or invalid; raises descriptive errors.
- Strict feature column alignment matching the saved training schema.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_BUNDLE_VERSIONS = {"2.0.0", "2.1.0", "2.2.0"}


class ArtifactValidationError(Exception):
    """Raised when an artifact bundle is missing, corrupted, or incompatible."""
    pass


class Predictor:
    """Generate predictions strictly using validated model artifact bundles."""

    BULLISH_THRESHOLD: float = 0.001   # +0.1%
    BEARISH_THRESHOLD: float = -0.001  # -0.1%

    def __init__(self, model_dir: Union[str, Path] = "models/saved") -> None:
        self.model_dir = Path(model_dir)

    def load_artifact(self, ticker: str, model_name: str) -> Dict[str, Any]:
        """Load and strictly validate a saved model artifact bundle from disk.

        Raises ArtifactValidationError if artifact is missing or invalid.
        Never silently retrains.
        """
        artifact_path = self.model_dir / f"{ticker}_{model_name}.joblib"
        if not artifact_path.exists():
            raise ArtifactValidationError(
                f"Artifact bundle not found on disk: {artifact_path}. "
                f"Model must be explicitly trained before inference."
            )

        try:
            bundle = joblib.load(artifact_path)
        except Exception as e:
            raise ArtifactValidationError(
                f"Failed to load artifact {artifact_path}: {e}"
            ) from e

        # Validate structure
        if not isinstance(bundle, dict):
            raise ArtifactValidationError(
                f"Artifact {artifact_path} is legacy bare estimator without bundle metadata. "
                f"Expected dictionary with 'model', 'feature_names', 'version'."
            )

        if "model" not in bundle or bundle["model"] is None:
            raise ArtifactValidationError(f"Artifact {artifact_path} missing 'model' estimator.")

        if "feature_names" not in bundle or not isinstance(bundle["feature_names"], list):
            raise ArtifactValidationError(f"Artifact {artifact_path} missing valid 'feature_names' list.")

        version = bundle.get("version", "unknown")
        if version not in SUPPORTED_BUNDLE_VERSIONS:
            logger.warning(
                "Artifact %s has version %s; supported versions are %s.",
                artifact_path, version, SUPPORTED_BUNDLE_VERSIONS
            )

        return bundle

    def predict(
        self,
        artifact: Union[Any, Dict[str, Any]],
        features: pd.DataFrame,
        current_price: Optional[float] = None,
        model_name: str = "unknown",
    ) -> Dict[str, Any]:
        """Generate a statistically calibrated prediction for the latest feature observation.

        Args:
            artifact: Saved bundle dict or bare estimator.
            features: DataFrame containing feature row(s). The last row is used.
            current_price: Current asset price for translation to predicted price.
            model_name: Optional fallback model identifier.

        Returns:
            Dictionary with predicted return, price, confidence bounds, and direction.
        """
        if features.empty:
            raise ValueError("Cannot predict — features DataFrame is empty.")

        # Extract bundle metadata if present
        if isinstance(artifact, dict) and "model" in artifact:
            model = artifact["model"]
            scaler = artifact.get("scaler")
            feature_names = artifact.get("feature_names")
            residual_std = artifact.get("residual_std", 0.02)
            m_name = artifact.get("model_name", model_name)
        else:
            model = artifact
            scaler = None
            feature_names = None
            residual_std = 0.02
            m_name = model_name

        # Ensure correct column ordering and subsetting against saved training schema
        if feature_names is not None:
            missing_cols = [c for c in feature_names if c not in features.columns]
            if missing_cols:
                raise ValueError(
                    f"Features DataFrame missing required columns from training schema: {missing_cols}"
                )
            eval_row = features[feature_names].iloc[[-1]].values.astype(np.float64)
        else:
            eval_row = features.iloc[[-1]].values.astype(np.float64)

        eval_row = np.nan_to_num(eval_row, nan=0.0, posinf=0.0, neginf=0.0)

        # Apply saved scaler if present
        if scaler is not None:
            eval_proc = np.clip(scaler.transform(eval_row), -3.0, 3.0)
            raw_return = float(model.predict(eval_proc)[0])
        else:
            raw_return = float(model.predict(eval_row)[0])

        predicted_return = raw_return

        # Price translation and 95% confidence bounds (±1.96 * residual_std)
        predicted_price: Optional[float] = None
        confidence_lower: Optional[float] = None
        confidence_upper: Optional[float] = None

        if current_price is not None and current_price > 0:
            predicted_price = float(current_price * (1.0 + predicted_return))
            margin = 1.96 * residual_std
            confidence_lower = float(current_price * (1.0 + predicted_return - margin))
            confidence_upper = float(current_price * (1.0 + predicted_return + margin))

        direction = self._label_direction(predicted_return)

        result: Dict[str, Any] = {
            "predicted_return": predicted_return,
            "predicted_price": predicted_price,
            "current_price": current_price,
            "confidence_lower": confidence_lower,
            "confidence_upper": confidence_upper,
            "residual_std": residual_std,
            "direction": direction,
            "model_name": m_name,
        }

        return result

    def predict_from_disk(
        self,
        ticker: str,
        model_name: str,
        features: pd.DataFrame,
        current_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Load artifact bundle from disk and generate prediction.
        Raises ArtifactValidationError if artifact is missing.
        """
        bundle = self.load_artifact(ticker, model_name)
        return self.predict(bundle, features, current_price=current_price, model_name=model_name)

    def _label_direction(self, predicted_return: float) -> str:
        if predicted_return > self.BULLISH_THRESHOLD:
            return "Bullish"
        elif predicted_return < self.BEARISH_THRESHOLD:
            return "Bearish"
        return "Neutral"
