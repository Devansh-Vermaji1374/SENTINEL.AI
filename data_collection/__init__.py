"""
SENTINEL AI - Data Collection Package
=======================================
Exports the three collector classes used to ingest market data,
social media posts, and financial news articles.
"""

from data_collection.apify_scraper import ApifyScraper
from data_collection.exa_news import ExaNewsCollector
from data_collection.market_data import MarketDataCollector

__all__ = [
    "ApifyScraper",
    "ExaNewsCollector",
    "MarketDataCollector",
]
