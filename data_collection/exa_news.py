"""SENTINEL AI - Exa Financial News Collector.
Supports Real API Ingestion via Exa API key and Live Verified Financial News Wire (Google News RSS).
Strict data hygiene: Filters corrupted metadata (e.g. META_TITLE_QUOTE), extracts publisher names,
and never fabricates synthetic articles in Real Data Mode.
"""
from __future__ import annotations

import email.utils
import json
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ExaNewsCollector:
    """Collects actual financial news for configured assets."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or ""
        self.is_connected = bool(self.api_key.strip())

    def check_connection(self) -> bool:
        """Verify if Exa API key is valid and connected."""
        if not self.api_key:
            return False
        try:
            req = urllib.request.Request(
                "https://api.exa.ai/search",
                data=b'{"query": "finance", "numResults": 1}',
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "SentinelAI/2.0"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def clean_headline(self, title: str, source: str) -> Optional[str]:
        """Filter out corrupted RSS titles such as 'META_TITLE_QUOTE' and clean suffix."""
        if not title or "META_TITLE_QUOTE" in title or len(title.strip()) < 10:
            return None

        # Clean trailing source suffix like ' - Yahoo Finance'
        cleaned = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
        return cleaned if len(cleaned) >= 10 else title.strip()

    def collect_for_ticker(
        self,
        ticker: str,
        asset_name: str,
        search_terms: List[str],
        days_back: int = 10,
        max_results: int = 15
    ) -> List[Dict[str, Any]]:
        """Collect actual financial news from Exa or real Financial News RSS."""
        articles = []

        # 1. Try Exa API if key is provided
        if self.api_key:
            try:
                query = f"{asset_name} ({ticker}) stock earnings financial news"
                payload = json.dumps({
                    "query": query,
                    "numResults": max_results,
                    "useAutoprompt": True,
                    "type": "neural"
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.exa.ai/search",
                    data=payload,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "User-Agent": "SentinelAI/2.0"
                    }
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results", [])
                    for item in results:
                        raw_title = item.get("title", "")
                        clean_t = self.clean_headline(raw_title, "Exa")
                        if not clean_t:
                            continue

                        pub_date = item.get("publishedDate")
                        if pub_date:
                            try:
                                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                            except Exception:
                                dt = datetime.now(timezone.utc)
                        else:
                            dt = datetime.now(timezone.utc)

                        # Enforce days_back filter
                        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
                        if dt < cutoff_dt:
                            continue

                        articles.append({
                            "ticker": ticker,
                            "title": clean_t,
                            "source_name": item.get("author") or "Exa Financial News",
                            "url": item.get("url", f"https://exa.ai/search?q={ticker}"),
                            "text": item.get("text") or clean_t,
                            "published_at": dt,
                            "is_demo_data": False,
                            "collector": "Exa Neural API"
                        })
                if articles:
                    return articles
            except Exception as e:
                logger.warning("Exa API query failed: %s. Falling back to real financial news stream.", e)

        # 2. Live verified financial news wire (Google News RSS / Yahoo Finance)
        try:
            is_krx = ".KS" in ticker
            lang = "ko" if is_krx else "en"
            gl = "KR" if is_krx else "US"
            ceid = "KR:ko" if is_krx else "US:en"

            clean_ticker = ticker.replace(".HK", "").replace(".KS", "")
            q = urllib.parse.quote(f"{asset_name} {clean_ticker} stock")
            url = f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={gl}&ceid={ceid}"

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SentinelAI/2.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                xml_data = resp.read()
                tree = ET.fromstring(xml_data)
                items = tree.findall(".//item")

                for it in items:
                    if len(articles) >= max_results:
                        break

                    title_elem = it.find("title")
                    link_elem = it.find("link")
                    pub_elem = it.find("pubDate")
                    source_elem = it.find("source")

                    raw_title = title_elem.text if title_elem is not None else ""
                    source_name = source_elem.text if source_elem is not None else "Financial Wire"
                    link = link_elem.text if link_elem is not None else ""

                    clean_t = self.clean_headline(raw_title, source_name)
                    if not clean_t or not link:
                        continue

                    dt = datetime.now(timezone.utc)
                    if pub_elem is not None and pub_elem.text:
                        try:
                            parsed_tuple = email.utils.parsedate_tz(pub_elem.text)
                            if parsed_tuple:
                                timestamp = email.utils.mktime_tz(parsed_tuple)
                                dt = datetime.fromtimestamp(timestamp, timezone.utc)
                        except Exception:
                            pass

                    # Enforce strict 10-day lookback filter
                    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
                    if dt < cutoff_dt:
                        continue

                    articles.append({
                        "ticker": ticker,
                        "title": clean_t,
                        "source_name": source_name,
                        "url": link,
                        "text": clean_t,
                        "published_at": dt,
                        "is_demo_data": False,
                        "collector": "Live Financial Wire (Real Data)"
                    })
        except Exception as e:
            logger.error("Real news collection failed for %s: %s", ticker, e)

        return articles
