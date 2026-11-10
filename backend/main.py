"""FastAPI application entry point for Sentinel AI."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from database.db import init_db
from backend.api.routes import router, pipeline_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinel")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    logger.info("Initializing SENTINEL AI backend...")
    init_db()
    pipeline_service.sync_assets_to_db()
    logger.info("Database and asset configurations initialized.")
    yield
    logger.info("Shutting down SENTINEL AI backend...")

app = FastAPI(
    title="SENTINEL AI - Market Intelligence & Stock Prediction API",
    description="Multi-market sentiment intelligence and stock price prediction platform for HKEX & KRX.",
    version="1.0.0",
    lifespan=lifespan
)

settings = get_settings()

# Parse configurable CORS allowlist (reject wildcard '*')
allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip() and origin.strip() != "*"
]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8501"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Sentinel-Automation-Key", "X-Sentinel-Admin-Key", "Authorization"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {
        "platform": "SENTINEL AI",
        "description": "Multi-Market Sentiment Intelligence & Stock Price Prediction",
        "docs_url": "/docs",
        "health": "/api/status"
    }

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("backend.main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
