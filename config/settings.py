"""SENTINEL AI - Central Settings Manager.

Loads environment variables via pydantic-settings and asset configuration
from config/assets.yaml. Provides typed access to all configuration through
a singleton ``Settings`` instance.
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
ASSETS_YAML_PATH = CONFIG_DIR / "assets.yaml"

# ---------------------------------------------------------------------------
# Asset / Exchange Pydantic models
# ---------------------------------------------------------------------------


class AssetConfig(BaseModel):
    """Configuration for a single tracked financial asset."""

    ticker: str
    name: str
    sector: str
    search_terms: list[str]


class TradingHoursConfig(BaseModel):
    """Market open / close times (local exchange timezone)."""

    open: str
    close: str


class ExchangeConfig(BaseModel):
    """Configuration for one stock exchange and its tracked assets."""

    name: str
    timezone: str
    currency: str
    trading_hours: TradingHoursConfig
    assets: list[AssetConfig]


class CollectionConfig(BaseModel):
    """Settings governing data-collection behaviour."""

    social_lookback_days: int = 10
    market_history_months: int = 6
    max_posts_per_source: int = 100
    max_news_per_ticker: int = 50


class SentimentConfig(BaseModel):
    """Settings governing the sentiment-analysis pipeline."""

    model: str = "ProsusAI/finbert"
    max_post_weight_pct: float = 5.0
    batch_size: int = 32


class MLConfig(BaseModel):
    """Settings governing the ML training pipeline."""

    test_size_pct: int = 20
    validation_size_pct: int = 15
    walk_forward_windows: int = 5
    models: list[str] = [
        "linear_regression",
        "random_forest",
        "xgboost",
    ]


class AssetsYAMLConfig(BaseModel):
    """Top-level representation of ``assets.yaml``."""

    exchanges: dict[str, ExchangeConfig] = {}
    collection: CollectionConfig = CollectionConfig()
    sentiment: SentimentConfig = SentimentConfig()
    ml: MLConfig = MLConfig()


# ---------------------------------------------------------------------------
# Main Settings (env-driven)
# ---------------------------------------------------------------------------

# Map service names to the env-var that controls demo mode.
_SERVICE_API_KEY_MAP: dict[str, str] = {
    "apify": "apify_api_token",
    "social": "apify_api_token",
    "exa": "exa_api_key",
    "news": "exa_api_key",
    "market_data": "market_data_api_key",
    "market": "market_data_api_key",
}


class Settings(BaseSettings):
    """Application-wide settings populated from ``.env`` and environment variables.

    Also loads ``config/assets.yaml`` and exposes helper methods for
    looking up exchanges and assets.
    """

    # --- API keys (empty → demo mode for that service) ---
    apify_api_token: str = ""
    exa_api_key: str = ""
    market_data_api_key: str = ""
    automation_api_key: str = ""
    dashboard_admin_key: str = ""

    # --- Security & CORS ---
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000,http://127.0.0.1:3000"

    # --- Application settings ---
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./sentinel.db"

    # --- Server settings ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 8501

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- YAML-derived config (populated post-init) ---
    _yaml_config: AssetsYAMLConfig | None = PrivateAttr(default=None)

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        return v.upper()

    # ------------------------------------------------------------------ #
    # YAML loading
    # ------------------------------------------------------------------ #

    @property
    def yaml_config(self) -> AssetsYAMLConfig:
        """Lazily load and cache the YAML configuration."""
        if self._yaml_config is None:
            self._yaml_config = self._load_yaml()
        return self._yaml_config

    @staticmethod
    def _load_yaml() -> AssetsYAMLConfig:
        """Read and parse ``assets.yaml``."""
        if not ASSETS_YAML_PATH.exists():
            logger.warning(
                "assets.yaml not found at %s – using empty defaults.",
                ASSETS_YAML_PATH,
            )
            return AssetsYAMLConfig()

        with open(ASSETS_YAML_PATH, encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}

        logger.info("Loaded asset configuration from %s", ASSETS_YAML_PATH)
        return AssetsYAMLConfig.model_validate(raw)

    # ------------------------------------------------------------------ #
    # Convenience helpers — Exchanges
    # ------------------------------------------------------------------ #

    def get_exchange_config(self, code: str) -> ExchangeConfig:
        """Return the :class:`ExchangeConfig` for the given exchange *code*.

        Args:
            code: Exchange code as it appears in ``assets.yaml`` (e.g. ``"HKEX"``).

        Raises:
            KeyError: If the exchange code is not found.
        """
        try:
            return self.yaml_config.exchanges[code]
        except KeyError:
            available = list(self.yaml_config.exchanges.keys())
            raise KeyError(
                f"Exchange '{code}' not found. Available: {available}"
            ) from None

    # ------------------------------------------------------------------ #
    # Convenience helpers — Assets
    # ------------------------------------------------------------------ #

    def get_all_assets(self) -> list[AssetConfig]:
        """Return a flat list of every tracked asset across all exchanges."""
        assets: list[AssetConfig] = []
        for exchange in self.yaml_config.exchanges.values():
            assets.extend(exchange.assets)
        return assets

    def get_assets_by_exchange(self, code: str) -> list[AssetConfig]:
        """Return assets belonging to the exchange identified by *code*.

        Args:
            code: Exchange code (e.g. ``"HKEX"``, ``"KRX"``).

        Raises:
            KeyError: If the exchange code is not found.
        """
        return self.get_exchange_config(code).assets

    def get_asset_by_ticker(self, ticker: str) -> AssetConfig:
        """Look up an :class:`AssetConfig` by its *ticker* symbol.

        Performs a case-insensitive comparison.

        Args:
            ticker: Ticker string (e.g. ``"0700.HK"``).

        Raises:
            KeyError: If the ticker is not tracked.
        """
        ticker_upper = ticker.upper()
        for asset in self.get_all_assets():
            if asset.ticker.upper() == ticker_upper:
                return asset
        raise KeyError(
            f"Ticker '{ticker}' not found in tracked assets."
        )

    # ------------------------------------------------------------------ #
    # Demo-mode detection
    # ------------------------------------------------------------------ #

    def is_demo_mode(self, service: str) -> bool:
        """Return ``True`` when the relevant API key for *service* is empty.

        Recognised service names: ``"apify"``, ``"social"``, ``"exa"``,
        ``"news"``, ``"market_data"``, ``"market"``.

        Args:
            service: Logical service name.

        Raises:
            ValueError: If the service name is not recognised.
        """
        key_attr = _SERVICE_API_KEY_MAP.get(service.lower())
        if key_attr is None:
            raise ValueError(
                f"Unknown service '{service}'. "
                f"Known services: {list(_SERVICE_API_KEY_MAP.keys())}"
            )
        return getattr(self, key_attr) == ""

    # ------------------------------------------------------------------ #
    # Collection / Sentiment / ML shorthand
    # ------------------------------------------------------------------ #

    @property
    def collection(self) -> CollectionConfig:
        """Shortcut to ``yaml_config.collection``."""
        return self.yaml_config.collection

    @property
    def sentiment(self) -> SentimentConfig:
        """Shortcut to ``yaml_config.sentiment``."""
        return self.yaml_config.sentiment

    @property
    def ml(self) -> MLConfig:
        """Shortcut to ``yaml_config.ml``."""
        return self.yaml_config.ml

    # ------------------------------------------------------------------ #
    # repr
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Settings(app_env={self.app_env!r}, "
            f"log_level={self.log_level!r}, "
            f"database_url={self.database_url!r})"
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton :class:`Settings` instance.

    On first call the settings are loaded from ``.env`` + environment
    variables and ``assets.yaml``.  Subsequent calls return the cached
    instance.
    """
    settings = Settings()
    logger.info("Settings initialised: %r", settings)
    return settings
