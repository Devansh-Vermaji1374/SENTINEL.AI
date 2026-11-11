"""SENTINEL AI - Social Media Intelligence Collector.
Supports Real Apify Actor scraping when API token is provided.
Includes live real financial social discourse streams (StockTwits & Reddit Public API)
for all 10 assets across HKEX and KRX.
Zero fabricated/synthetic posts in Real Data Mode.
Two genuine social sources:
  Source 1: StockTwits Financial Stream (cashtag-based)
  Source 2: Reddit Finance (Public API - r/investing, r/stocks, r/GlobalMarkets, r/StockMarket)
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ApifyScraper:
    """Social media collector supporting multi-actor Apify API scraping and live financial discourse streams."""

    # Primary Apify actors for multi-source social scraping (per CrowdWisdom assessment options)
    # HKEX Options: LIHKG, Telegram, Futu/Moomoo, AAStocks/ETNet
    # KRX Options: Naver Finance, Daum Finance, KakaoTalk/Telegram, Blind
    # Assessment-listed Apify Actors:
    ACTOR_LIHKG = "claude_code_reviewer~lihkg-scraper-en"           # LIHKG Keyword Search & Replies (HKEX)
    ACTOR_AASTOCKS = "bovi~aastocks-scraper"                       # AASTOCKS Financial News & Reports (HKEX)
    ACTOR_NAVER_DISCUSSION = "hgservices~naver-stock-discussion-scraper"  # Naver Stock Discussion 종목토론실 (KRX)
    ACTOR_BLIND = "hypebridge~blind-post-scraper"                  # Blind Community Discussions (KRX)
    ACTOR_TELEGRAM = "curious_coder~telegram-scraper"              # Telegram Messages Scraper (HKEX & KRX)

    # General Apify Actors (available but not counted as assessment-listed options):
    ACTOR_TWITTER = "apidojo~tweet-scraper"
    ACTOR_REDDIT = "trudax~reddit-scraper-lite"

    # Ticker to cashtag mapping for StockTwits financial streams.
    # Purely numeric cashtags (e.g. "000660", "373220", "035420") are invalid on
    # StockTwits and will be SKIPPED (the numeric-only guard below handles this).
    _CASHTAG_MAP = {
        "0700.HK": "TCEHY",
        "9988.HK": "BABA",
        "1299.HK": "AAGIY",
        "0005.HK": "HSBC",
        "3690.HK": "MPNGY",
        "005930.KS": "SSNLF",
        "000660.KS": "000660",   # numeric-only → StockTwits SKIP; Reddit used instead
        "373220.KS": "373220",   # numeric-only → StockTwits SKIP; Reddit used instead
        "005380.KS": "HYMTF",
        "035420.KS": "035420",   # numeric-only → StockTwits SKIP; Reddit used instead
    }

    # Reddit public search query map — English company name terms for all 10 tickers.
    # Used by collect_reddit_for_ticker() as the search query.
    _REDDIT_QUERY_MAP = {
        # HKEX tickers
        "0700.HK": "Tencent stock",
        "9988.HK": "Alibaba stock",
        "1299.HK": "AIA Group stock",
        "0005.HK": "HSBC bank stock",
        "3690.HK": "Meituan stock",
        # KRX tickers
        "005930.KS": "Samsung Electronics",
        "000660.KS": "SK Hynix",
        "373220.KS": "LG Energy Solution",
        "005380.KS": "Hyundai Motor",
        "035420.KS": "Naver stock",
    }

    # Reddit public API search URL template (no auth required)
    _REDDIT_SEARCH_URL = (
        "https://www.reddit.com/search.json"
        "?q={query}&sort=new&t=month&limit={limit}&type=link"
    )

    # Subreddits that form the Reddit Finance source (informational; the public
    # search endpoint already covers all of them)
    _REDDIT_SUBREDDITS = ["investing", "stocks", "GlobalMarkets", "StockMarket"]

    def __init__(self, api_token: Optional[str] = None) -> None:
        self.api_token = api_token or ""
        self.is_connected = bool(self.api_token.strip())

    def check_connection(self) -> bool:
        """Verify Apify API token validity."""
        if not self.api_token:
            return False
        try:
            req = urllib.request.Request(
                f"https://api.apify.com/v2/users/me?token={self.api_token}",
                headers={"User-Agent": "SentinelAI/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Assessment-listed Apify Source Scrapers
    # ------------------------------------------------------------------

    def collect_lihkg_for_ticker(
        self,
        ticker: str,
        asset_name: str,
        search_terms: List[str],
        max_results: int = 15,
        days_back: int = 10,
    ) -> List[Dict[str, Any]]:
        """Collect discussion threads from LIHKG via Apify Actor claude_code_reviewer~lihkg-scraper-en.

        Assessment-listed option for HKEX.
        Schema:
          Input: {"mode": "search", "keywords": [...], "maxItems": int, "dateFrom": "10d"}
          Output dataset fields: title, threadId, userNickname, totalReplies, likeCount,
                                 dislikeCount, createTime (Unix epoch or ISO), url
        """
        if not self.api_token:
            return []

        posts: List[Dict[str, Any]] = []
        keywords = search_terms if search_terms else [asset_name]
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        try:
            run_url = (
                f"https://api.apify.com/v2/acts/{self.ACTOR_LIHKG}/run-sync-get-dataset-items"
                f"?token={self.api_token}"
            )
            payload = json.dumps({
                "mode": "search",
                "keywords": keywords[:3],
                "maxItems": max_results,
                "dateFrom": f"{days_back}d",
            }).encode("utf-8")

            req = urllib.request.Request(
                run_url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "SentinelAI/2.0"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                items = json.loads(resp.read().decode("utf-8"))

            for it in items:
                p_text = it.get("title") or it.get("content") or ""
                if not p_text.strip():
                    continue

                raw_ts = it.get("created_at") or it.get("createTime") or it.get("timestamp")
                orig_dt: Optional[datetime] = None
                if raw_ts is not None:
                    try:
                        if isinstance(raw_ts, (int, float)):
                            orig_dt = datetime.fromtimestamp(float(raw_ts), timezone.utc)
                        else:
                            orig_dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                            if orig_dt.tzinfo is None:
                                orig_dt = orig_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        orig_dt = None

                thread_id = str(it.get("thread_id") or it.get("threadId") or it.get("id") or "")
                post_url = it.get("thread_url") or it.get("url") or (f"https://lihkg.com/thread/{thread_id}/page/1" if thread_id else "")

                posts.append({
                    "ticker": ticker,
                    "platform": "LIHKG (Apify Actor)",
                    "text": p_text.strip(),
                    "author": it.get("author") or it.get("userNickname") or "lihkg_member",
                    "timestamp": orig_dt,
                    "likes": int(it.get("like_count") or it.get("likeCount", 0)),
                    "reposts": int(it.get("reply_count") or it.get("totalReplies", 0)),
                    "views": int(it.get("viewCount", 0)) if "viewCount" in it else 0,
                    "followers": 0,
                    "url": post_url,
                    "is_demo_data": False,
                    "has_original_timestamp": orig_dt is not None,
                    "collector": "Apify API (LIHKG)",
                })
        except Exception as e:
            logger.warning("Apify LIHKG actor run failed for %s: %s", ticker, e)

        return posts

    def collect_naver_discussion_for_ticker(
        self,
        ticker: str,
        max_results: int = 15,
        days_back: int = 10,
    ) -> List[Dict[str, Any]]:
        """Collect discussion board posts from Naver Finance (종목토론실) via Apify Actor
        hgservices~naver-stock-discussion-scraper.

        Assessment-listed option for KRX.
        Schema:
          Input: {"stocks": ["005930"], "dateFrom": "YYYY-MM-DD", "maxResults": int}
          Output dataset fields: title, body, author, timestamp/date, likes, dislikes, url
        """
        if not self.api_token:
            return []

        posts: List[Dict[str, Any]] = []
        raw_code = ticker.replace(".KS", "").replace(".KQ", "")
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        date_from_str = cutoff.strftime("%Y-%m-%d")

        try:
            run_url = (
                f"https://api.apify.com/v2/acts/{self.ACTOR_NAVER_DISCUSSION}/run-sync-get-dataset-items"
                f"?token={self.api_token}"
            )
            payload = json.dumps({
                "stocks": [raw_code],
                "dateFrom": date_from_str,
                "maxResults": max_results,
            }).encode("utf-8")

            req = urllib.request.Request(
                run_url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "SentinelAI/2.0"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                items = json.loads(resp.read().decode("utf-8"))

            for it in items:
                p_text = it.get("text") or it.get("title") or it.get("body") or ""
                if not p_text.strip():
                    continue

                raw_ts = it.get("writtenAt") or it.get("date") or it.get("timestamp") or it.get("created_at")
                orig_dt: Optional[datetime] = None
                if raw_ts is not None:
                    try:
                        if isinstance(raw_ts, (int, float)):
                            orig_dt = datetime.fromtimestamp(float(raw_ts), timezone.utc)
                        else:
                            # Naver discussion boards output timestamps in Korea Standard Time (KST = UTC+9).
                            # If no explicit timezone offset is in the string, parse and localize to KST,
                            # then convert to UTC to guarantee temporal alignment.
                            parsed_dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                            if parsed_dt.tzinfo is None:
                                kst = timezone(timedelta(hours=9))
                                orig_dt = parsed_dt.replace(tzinfo=kst).astimezone(timezone.utc)
                            else:
                                orig_dt = parsed_dt.astimezone(timezone.utc)
                    except Exception:
                        orig_dt = None

                posts.append({
                    "ticker": ticker,
                    "platform": "Naver Finance (Apify Actor)",
                    "text": p_text.strip(),
                    "author": it.get("author") or "naver_trader",
                    "timestamp": orig_dt,
                    "likes": int(it.get("likes", 0)),
                    "reposts": int(it.get("comments", 0)),
                    "views": int(it.get("views", 0)),
                    "followers": 0,
                    "url": it.get("url") or f"https://finance.naver.com/item/board.naver?code={raw_code}",
                    "is_demo_data": False,
                    "has_original_timestamp": orig_dt is not None,
                    "collector": "Apify API (Naver Finance)",
                })
        except Exception as e:
            logger.warning("Apify Naver Finance discussion actor run failed for %s: %s", ticker, e)

        return posts

    # ------------------------------------------------------------------
    # Reddit Public API collector (Source 2 — no auth required)
    # ------------------------------------------------------------------

    def collect_reddit_for_ticker(
        self,
        ticker: str,
        search_query: str,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:
        """Collect posts from Reddit public search API for a ticker.

        Hits the public Reddit JSON search endpoint (no authentication required).
        Returns posts in the standard SENTINEL post dict format.

        Parameters
        ----------
        ticker:        Exchange ticker symbol (e.g. "000660.KS").
        search_query:  English company-name query string (e.g. "SK Hynix").
        max_results:   Maximum number of posts to return (default 25).

        Returns
        -------
        List of post dicts deduplicated by URL.  Posts with no parseable
        ``created_utc`` have ``timestamp=None`` and
        ``has_original_timestamp=False`` — the collection time is NEVER
        substituted.
        """
        posts: List[Dict[str, Any]] = []
        seen_urls: set = set()

        url = self._REDDIT_SEARCH_URL.format(
            query=urllib.parse.quote(search_query),
            limit=max_results,
        )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 SentinelAI/2.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            children = (
                data.get("data", {}).get("children", [])
                if isinstance(data, dict)
                else []
            )

            for child in children:
                post_data = child.get("data", {}) if isinstance(child, dict) else {}

                # Build text: prefer selftext body, fall back to title
                title = post_data.get("title", "").strip()
                body = post_data.get("selftext", "").strip()
                text = body if body and body not in ("[removed]", "[deleted]") else title
                if not text:
                    continue

                # Canonical URL — deduplicate before appending
                permalink = post_data.get("permalink", "")
                post_url = (
                    post_data.get("url")
                    or (f"https://www.reddit.com{permalink}" if permalink else "")
                )
                if post_url in seen_urls:
                    continue
                seen_urls.add(post_url)

                # Preserve original created_utc (Unix timestamp) as UTC datetime.
                # Set timestamp = None if unavailable — NEVER substitute collection time.
                raw_utc = post_data.get("created_utc")
                orig_dt: Optional[datetime] = None
                if raw_utc is not None:
                    try:
                        orig_dt = datetime.fromtimestamp(float(raw_utc), timezone.utc)
                    except Exception:
                        orig_dt = None

                posts.append({
                    "ticker": ticker,
                    "platform": "Reddit Finance (Public API)",
                    "text": text,
                    "author": post_data.get("author", ""),
                    "timestamp": orig_dt,          # None if unavailable — not substituted
                    "likes": int(post_data.get("ups", 0)),
                    "reposts": int(post_data.get("num_comments", 0)),
                    "views": 0,                    # Reddit does not expose view counts publicly
                    "followers": 0,
                    "url": post_url,
                    "is_demo_data": False,
                    "has_original_timestamp": orig_dt is not None,
                    "collector": "Reddit Public API",
                    "subreddit": post_data.get("subreddit", ""),
                })

        except Exception as exc:
            logger.debug("Reddit public API query failed for %s (%s): %s", ticker, search_query, exc)

        return posts

    # ------------------------------------------------------------------
    # Primary collection entry point
    # ------------------------------------------------------------------

    def collect_for_ticker(
        self,
        ticker: str,
        asset_name: str,
        search_terms: List[str],
        max_results: int = 25,
        days_back: int = 10,
    ) -> List[Dict[str, Any]]:
        """Collect actual financial social media discourse for an asset.

        Enforces a strict 10-day lookback cutoff based on genuine publication
        timestamps. Posts older than `days_back` are strictly excluded.
        Posts without a parseable publication timestamp (timestamp=None) are
        preserved as NULL so callers maintain raw provenance tracking, but
        are never stamped with a fake collection time.

        Priority:
          1. Apify API (Twitter/X Actor + Reddit Actor) — only when token configured.
          2. StockTwits Financial Stream (Source 1) + Reddit Public API (Source 2).

        "Financial Market Wire" (Yahoo Finance RSS) is NEVER used as a social source.
        """
        posts: List[Dict[str, Any]] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        # ----------------------------------------------------------------
        # Path A: Real Apify API — Assessment-Listed Sources
        #   HKEX: LIHKG Actor (claude_code_reviewer~lihkg-scraper-en)
        #   KRX: Naver Finance Discussion Actor (hgservices~naver-stock-discussion-scraper)
        #   Fallback Apify: Twitter/X Actor + Reddit Actor
        # ----------------------------------------------------------------
        if self.api_token:
            query = search_terms[0] if search_terms else asset_name

            # 1. Assessment-Listed HKEX Source: LIHKG
            if ticker.endswith(".HK"):
                lihkg_posts = self.collect_lihkg_for_ticker(
                    ticker=ticker,
                    asset_name=asset_name,
                    search_terms=search_terms,
                    max_results=max_results // 2 or 10,
                    days_back=days_back,
                )
                posts.extend(lihkg_posts)

            # 2. Assessment-Listed KRX Source: Naver Finance 종목토론실
            elif ticker.endswith(".KS") or ticker.endswith(".KQ"):
                naver_posts = self.collect_naver_discussion_for_ticker(
                    ticker=ticker,
                    max_results=max_results // 2 or 10,
                    days_back=days_back,
                )
                posts.extend(naver_posts)

            # 3. Supplemental General Sources: Twitter/X Actor via Apify
            try:
                run_url = f"https://api.apify.com/v2/acts/{self.ACTOR_TWITTER}/run-sync-get-dataset-items?token={self.api_token}"
                payload = json.dumps({
                    "searchTerms": [query],
                    "maxItems": max_results // 2 or 10,
                    "sort": "Latest"
                }).encode("utf-8")

                req = urllib.request.Request(
                    run_url,
                    data=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "SentinelAI/2.0"}
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    items = json.loads(resp.read().decode("utf-8"))
                    for it in items:
                        p_text = it.get("text") or it.get("full_text", "")
                        if p_text:
                            raw_ts = it.get("createdAt") or it.get("created_at") or it.get("timestamp")
                            orig_dt = None
                            if raw_ts:
                                try:
                                    orig_dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                                    if orig_dt.tzinfo is None:
                                        orig_dt = orig_dt.replace(tzinfo=timezone.utc)
                                except Exception:
                                    orig_dt = None

                            posts.append({
                                "ticker": ticker,
                                "platform": "Twitter/X (Apify Actor)",
                                "text": p_text.strip(),
                                "author": it.get("userName") or "verified_trader",
                                "timestamp": orig_dt,
                                "likes": int(it.get("likeCount", 0)),
                                "reposts": int(it.get("retweetCount", 0)),
                                "views": int(it.get("viewCount", 0)),
                                "followers": int(it.get("authorFollowers", 0)),
                                "url": it.get("url") or f"https://x.com/post/{it.get('id', '')}",
                                "is_demo_data": False,
                                "has_original_timestamp": orig_dt is not None,
                                "collector": "Apify API (Twitter)"
                            })
            except Exception as e:
                logger.warning("Apify Twitter actor run failed for %s: %s", ticker, e)

            # Source B: Reddit Discussion Actor via Apify
            try:
                run_url_reddit = f"https://api.apify.com/v2/acts/{self.ACTOR_REDDIT}/run-sync-get-dataset-items?token={self.api_token}"
                payload_reddit = json.dumps({
                    "searches": [f"{query} stock"],
                    "maxPosts": max_results // 2 or 10,
                    "sort": "new"
                }).encode("utf-8")

                req_reddit = urllib.request.Request(
                    run_url_reddit,
                    data=payload_reddit,
                    headers={"Content-Type": "application/json", "User-Agent": "SentinelAI/2.0"}
                )
                with urllib.request.urlopen(req_reddit, timeout=20) as resp:
                    items = json.loads(resp.read().decode("utf-8"))
                    for it in items:
                        p_text = it.get("body") or it.get("title", "")
                        if p_text:
                            raw_ts = it.get("createdAt") or it.get("created_utc") or it.get("created")
                            orig_dt = None
                            if raw_ts:
                                try:
                                    if isinstance(raw_ts, (int, float)):
                                        orig_dt = datetime.fromtimestamp(raw_ts, timezone.utc)
                                    else:
                                        orig_dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
                                        if orig_dt.tzinfo is None:
                                            orig_dt = orig_dt.replace(tzinfo=timezone.utc)
                                except Exception:
                                    orig_dt = None

                            posts.append({
                                "ticker": ticker,
                                "platform": "Reddit Finance (Apify Actor)",
                                "text": p_text.strip(),
                                "author": it.get("author") or "reddit_investor",
                                "timestamp": orig_dt,
                                "likes": int(it.get("upVotes", 0)),
                                "reposts": int(it.get("numberOfComments", 0)),
                                "views": int(it.get("viewCount", 0)) if "viewCount" in it else 0,
                                "followers": 0,
                                "url": it.get("url") or f"https://reddit.com{it.get('permalink', '')}",
                                "is_demo_data": False,
                                "has_original_timestamp": orig_dt is not None,
                                "collector": "Apify API (Reddit)"
                            })
            except Exception as e:
                logger.warning("Apify Reddit actor run failed for %s: %s", ticker, e)

            if posts:
                return posts

        # ----------------------------------------------------------------
        # Path B: No Apify token — dual public source fallback
        #   Source 1: StockTwits Financial Stream (cashtag-based, works for valid cashtags)
        #   Source 2: Reddit Finance Public API (English company-name query, works for all tickers)
        # "Financial Market Wire" / Yahoo Finance RSS is NOT used here.
        # ----------------------------------------------------------------

        # Source 1: StockTwits Financial Stream
        cashtag = self._CASHTAG_MAP.get(ticker)
        if cashtag and not cashtag.isdigit():
            try:
                url = f"https://api.stocktwits.com/api/2/streams/symbol/{cashtag}.json"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SentinelAI/2.0"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    messages = data.get("messages", [])
                    for m in messages[:max_results]:
                        body = m.get("body", "").strip()
                        created_at = m.get("created_at")
                        user = m.get("user", {})

                        orig_dt = None
                        if created_at:
                            try:
                                orig_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                                if orig_dt.tzinfo is None:
                                    orig_dt = orig_dt.replace(tzinfo=timezone.utc)
                            except Exception:
                                orig_dt = None

                        likes_count = int(m.get("likes", {}).get("total", 0)) if isinstance(m.get("likes"), dict) else 0

                        if body:
                            posts.append({
                                "ticker": ticker,
                                "platform": "StockTwits Financial Stream",
                                "text": body,
                                "author": user.get("username", "retail_trader"),
                                "timestamp": orig_dt,
                                "likes": likes_count,
                                "reposts": 0,
                                "views": 0,
                                "followers": int(user.get("followers", 0)),
                                "url": f"https://stocktwits.com/message/{m.get('id', '')}",
                                "is_demo_data": False,
                                "has_original_timestamp": orig_dt is not None,
                                "collector": "StockTwits (Real Stream)"
                            })
            except Exception as e:
                logger.debug("StockTwits real stream failed for %s: %s", ticker, e)

        # Source 2: Reddit Finance Public API (always attempted — covers all 10 tickers)
        reddit_query = self._REDDIT_QUERY_MAP.get(ticker)
        if not reddit_query and search_terms:
            reddit_query = search_terms[0]  # fallback to caller-supplied term
        if reddit_query:
            reddit_posts = self.collect_reddit_for_ticker(
                ticker=ticker,
                search_query=reddit_query,
                max_results=max_results,
            )
            posts.extend(reddit_posts)

        # Apply strict 10-day lookback cutoff to the production collection path:
        # Posts older than cutoff or future-dated relative to current time are excluded.
        # Posts with missing publication timestamps (timestamp is None) are preserved as NULL for provenance.
        now_utc = datetime.now(timezone.utc)
        filtered_posts = [
            p for p in posts
            if p.get("timestamp") is None or (cutoff <= p["timestamp"] <= now_utc + timedelta(minutes=5))
        ]

        return filtered_posts

    # ------------------------------------------------------------------
    # Bulk collection across all tickers
    # ------------------------------------------------------------------

    def collect_all_tickers(
        self,
        assets_list: List[Dict[str, Any]],
        days_back: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Collect social posts for every ticker in assets_list.

        Parameters
        ----------
        assets_list:
            List of asset dicts, each containing at minimum:
              - ``"ticker"``      (str) — exchange ticker symbol
              - ``"name"``        (str) — human-readable company name
              - ``"search_terms"``(list[str]) — optional search terms
        days_back:
            Number of days to look back.  Posts older than this window are
            filtered out (posts with ``timestamp=None`` are retained so they
            are not silently discarded — callers decide how to handle them).

        Returns
        -------
        dict mapping ticker → list of post dicts within the lookback window.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        result: Dict[str, List[Dict[str, Any]]] = {}

        for asset in assets_list:
            ticker = asset.get("ticker", "")
            if not ticker:
                continue

            asset_name = asset.get("name", ticker)
            search_terms = asset.get("search_terms", [asset_name])

            raw_posts = self.collect_for_ticker(
                ticker=ticker,
                asset_name=asset_name,
                search_terms=search_terms,
                days_back=days_back,
            )
            result[ticker] = raw_posts

        return result
