"""
SENTINEL AI - Model Registry
=============================
Persist and retrieve trained models with accompanying metadata.
Uses *joblib* for model serialisation and JSON for metadata.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Save, load, list, and retrieve the best trained models.

    Directory layout::

        <save_dir>/
            <ticker>/
                <model_name>.joblib
                <model_name>_meta.json
    """

    def __init__(self, save_dir: str = "models/saved") -> None:
        self.save_dir = Path(save_dir)
        os.makedirs(self.save_dir, exist_ok=True)
        logger.info("ModelRegistry initialised — save dir: %s", self.save_dir)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def save_model(
        self,
        model: Any,
        model_name: str,
        ticker: str,
        metadata: dict[str, Any],
    ) -> str:
        """Save a model to disk alongside its metadata.

        Args:
            model: A fitted model object (scikit-learn / xgboost / etc.).
            model_name: Descriptive name (e.g. ``'random_forest'``).
            ticker: Stock ticker the model was trained for.
            metadata: Arbitrary metadata dict (metrics, feature names, …).

        Returns:
            Absolute path to the saved model file.
        """
        ticker_dir = self.save_dir / ticker.upper()
        os.makedirs(ticker_dir, exist_ok=True)

        model_path = ticker_dir / f"{model_name}.joblib"
        meta_path = ticker_dir / f"{model_name}_meta.json"

        # Persist model
        joblib.dump(model, model_path)

        # Enrich & persist metadata
        metadata_out = {
            **metadata,
            "model_name": model_name,
            "ticker": ticker.upper(),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "model_path": str(model_path),
        }

        # Convert numpy types inside metrics for JSON serialisation
        _sanitise_for_json(metadata_out)

        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(metadata_out, fh, indent=2, default=str)

        logger.info("Saved model '%s' for %s → %s", model_name, ticker, model_path)
        return str(model_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_model(
        self,
        model_name: str,
        ticker: str,
    ) -> tuple[Any, dict[str, Any]]:
        """Load a model and its metadata from disk.

        Args:
            model_name: Model name used when saving.
            ticker: Stock ticker.

        Returns:
            ``(model, metadata)`` tuple.

        Raises:
            FileNotFoundError: If the model file does not exist.
        """
        ticker_dir = self.save_dir / ticker.upper()
        model_path = ticker_dir / f"{model_name}.joblib"
        meta_path = ticker_dir / f"{model_name}_meta.json"

        if not model_path.exists():
            raise FileNotFoundError(
                f"No saved model found at {model_path}"
            )

        model = joblib.load(model_path)

        metadata: dict[str, Any] = {}
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as fh:
                metadata = json.load(fh)

        logger.info("Loaded model '%s' for %s from %s", model_name, ticker, model_path)
        return model, metadata

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_models(self) -> list[dict[str, Any]]:
        """List all saved models with their metadata.

        Returns:
            A list of metadata dicts, one per saved model.
        """
        models: list[dict[str, Any]] = []

        if not self.save_dir.exists():
            return models

        for ticker_dir in sorted(self.save_dir.iterdir()):
            if not ticker_dir.is_dir():
                continue
            for meta_file in sorted(ticker_dir.glob("*_meta.json")):
                try:
                    with open(meta_file, "r", encoding="utf-8") as fh:
                        meta = json.load(fh)
                    models.append(meta)
                except (json.JSONDecodeError, OSError):
                    logger.warning("Could not read metadata from %s", meta_file)

        logger.info("Registry contains %d model(s).", len(models))
        return models

    # ------------------------------------------------------------------
    # Best model selection
    # ------------------------------------------------------------------

    def get_best_model(
        self,
        ticker: str,
        metric: str = "rmse",
    ) -> tuple[Any, dict[str, Any]]:
        """Return the best-performing model for a ticker.

        "Best" is defined as the model with the **lowest** value of the
        given *metric* (appropriate for error metrics like RMSE / MAE).
        For metrics where higher is better (e.g. ``directional_accuracy``),
        the caller should invert the sort externally.

        Args:
            ticker: Stock ticker.
            metric: Metric key inside the metadata's ``metrics`` dict.

        Returns:
            ``(model, metadata)`` tuple for the winning model.

        Raises:
            FileNotFoundError: If no models exist for the ticker.
        """
        ticker_dir = self.save_dir / ticker.upper()
        if not ticker_dir.exists():
            raise FileNotFoundError(
                f"No saved models found for ticker '{ticker}'."
            )

        candidates: list[tuple[float, str]] = []

        for meta_file in ticker_dir.glob("*_meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                metric_val = meta.get("metrics", {}).get(metric)
                if metric_val is not None:
                    model_name = meta["model_name"]
                    candidates.append((float(metric_val), model_name))
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        if not candidates:
            raise FileNotFoundError(
                f"No models with metric '{metric}' found for '{ticker}'."
            )

        # Sort ascending — lowest error wins
        candidates.sort(key=lambda x: x[0])
        best_metric_val, best_model_name = candidates[0]

        logger.info(
            "Best model for %s by %s: '%s' (%.6f)",
            ticker,
            metric,
            best_model_name,
            best_metric_val,
        )
        return self.load_model(best_model_name, ticker)


# ======================================================================
# Helpers
# ======================================================================

def _sanitise_for_json(obj: Any) -> None:
    """In-place convert numpy / non-serialisable types inside dicts/lists."""
    import numpy as _np

    if isinstance(obj, dict):
        for key in list(obj.keys()):
            val = obj[key]
            if isinstance(val, (_np.integer,)):
                obj[key] = int(val)
            elif isinstance(val, (_np.floating,)):
                obj[key] = float(val)
            elif isinstance(val, _np.ndarray):
                obj[key] = val.tolist()
            elif isinstance(val, (dict, list)):
                _sanitise_for_json(val)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            if isinstance(val, (_np.integer,)):
                obj[i] = int(val)
            elif isinstance(val, (_np.floating,)):
                obj[i] = float(val)
            elif isinstance(val, _np.ndarray):
                obj[i] = val.tolist()
            elif isinstance(val, (dict, list)):
                _sanitise_for_json(val)
