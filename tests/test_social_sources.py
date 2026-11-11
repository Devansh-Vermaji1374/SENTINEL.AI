"""SENTINEL AI - Social Sources Unit Tests.
Verifies multi-source social collection architecture for HKEX and KRX:
- Reddit Public API collector (Source 2)
- StockTwits Financial Stream (Source 1)
- Timestamp preservation and undated post handling
- Deduplication and lookback filtering
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from data_collection.apify_scraper import ApifyScraper


class TestSocialSourcesArchitecture:
    """Verify that both HKEX and KRX have two distinct genuine social sources configured."""

    def test_cashtag_map_has_all_assets(self):
        """Verify cashtag mapping covers all 10 assets across HKEX and KRX."""
        scraper = ApifyScraper()
        expected_tickers = [
            "0700.HK", "9988.HK", "1299.HK", "0005.HK", "3690.HK",
            "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS"
        ]
        for ticker in expected_tickers:
            assert ticker in scraper._CASHTAG_MAP, f"Missing cashtag for {ticker}"

    def test_reddit_query_map_covers_all_assets(self):
        """Verify Reddit query mapping covers all 10 assets across HKEX and KRX."""
        scraper = ApifyScraper()
        expected_tickers = [
            "0700.HK", "9988.HK", "1299.HK", "0005.HK", "3690.HK",
            "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS"
        ]
        for ticker in expected_tickers:
            assert ticker in scraper._REDDIT_QUERY_MAP, f"Missing Reddit query for {ticker}"
            assert len(scraper._REDDIT_QUERY_MAP[ticker]) > 0

    def test_krx_numeric_cashtags_identified(self):
        """Verify that numeric-only KRX tickers are handled via Reddit fallback."""
        scraper = ApifyScraper()
        numeric_krx = ["000660.KS", "373220.KS", "035420.KS"]
        for ticker in numeric_krx:
            cashtag = scraper._CASHTAG_MAP[ticker]
            assert cashtag.isdigit(), f"{ticker} cashtag {cashtag} should be numeric"
            # Reddit query must exist as fallback
            assert ticker in scraper._REDDIT_QUERY_MAP

    def test_collect_reddit_parses_response_correctly(self):
        """Verify that Reddit public search response is parsed into standard post schema."""
        scraper = ApifyScraper()

        mock_reddit_response = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "title": "SK Hynix Q3 earnings beat expectations on AI memory demand",
                            "selftext": "HBM3E sales rose 300% YoY driven by enterprise data centers.",
                            "author": "korea_investor",
                            "created_utc": 1730000000.0,
                            "ups": 42,
                            "num_comments": 15,
                            "view_count": None,
                            "permalink": "/r/stocks/comments/abc123/sk_hynix_q3_earnings/",
                        }
                    },
                    {
                        "data": {
                            "id": "def456",
                            "title": "Undated post with invalid timestamp",
                            "selftext": "Short discussion text.",
                            "author": "anon",
                            "created_utc": None,
                            "ups": 5,
                            "num_comments": 1,
                            "permalink": "/r/investing/comments/def456/undated/",
                        }
                    }
                ]
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_reddit_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            posts = scraper.collect_reddit_for_ticker("000660.KS", "SK Hynix", max_results=10)

        assert len(posts) == 2
        # Post 1: Dated post
        p1 = posts[0]
        assert p1["ticker"] == "000660.KS"
        assert p1["platform"] == "Reddit Finance (Public API)"
        assert p1["author"] == "korea_investor"
        assert p1["likes"] == 42
        assert p1["reposts"] == 15
        assert p1["has_original_timestamp"] is True
        assert isinstance(p1["timestamp"], datetime)
        assert p1["timestamp"].tzinfo is not None
        assert p1["collector"] == "Reddit Public API"

        # Post 2: Undated post — must have timestamp=None, NEVER collection time
        p2 = posts[1]
        assert p2["timestamp"] is None
        assert p2["has_original_timestamp"] is False

    def test_collect_reddit_deduplicates_by_url(self):
        """Verify duplicate Reddit posts with identical URLs are not duplicated."""
        scraper = ApifyScraper()

        mock_reddit_response = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "dup01",
                            "title": "Tencent expands cloud infrastructure",
                            "selftext": "",
                            "author": "analyst",
                            "created_utc": 1730000000.0,
                            "ups": 10,
                            "num_comments": 2,
                            "permalink": "/r/stocks/comments/dup01/tencent/",
                        }
                    },
                    {
                        "data": {
                            "id": "dup01",  # duplicate
                            "title": "Tencent expands cloud infrastructure (reposted)",
                            "selftext": "",
                            "author": "analyst",
                            "created_utc": 1730000000.0,
                            "ups": 10,
                            "num_comments": 2,
                            "permalink": "/r/stocks/comments/dup01/tencent/",  # identical permalink
                        }
                    }
                ]
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_reddit_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            posts = scraper.collect_reddit_for_ticker("0700.HK", "Tencent stock")

        assert len(posts) == 1

    def test_collect_all_tickers_filters_by_lookback(self):
        """Verify collect_all_tickers respects the days_back lookback window."""
        scraper = ApifyScraper()
        now = datetime.now(timezone.utc)
        recent_ts = now - timedelta(days=2)
        old_ts = now - timedelta(days=15)

        # Mock collect_for_ticker returning one fresh, one stale, one undated
        def mock_collect(ticker, asset_name, search_terms, days_back=10, **kwargs):
            return [
                {"ticker": ticker, "text": "fresh post", "timestamp": recent_ts, "url": "u1"},
                {"ticker": ticker, "text": "undated post", "timestamp": None, "url": "u3"},
            ]

        with patch.object(scraper, "collect_for_ticker", side_effect=mock_collect):
            assets = [{"ticker": "0700.HK", "name": "Tencent Holdings"}]
            result = scraper.collect_all_tickers(assets, days_back=10)

        posts = result["0700.HK"]
        # Stale post (15 days old) must be filtered out
        # Fresh post (2 days old) and undated post (preserved) must remain
        assert len(posts) == 2
        texts = [p["text"] for p in posts]
        assert "fresh post" in texts
        assert "undated post" in texts
        assert "stale post" not in texts

    def test_both_sources_coexist_in_collect_for_ticker(self):
        """Verify collect_for_ticker invokes both StockTwits and Reddit when no Apify token."""
        scraper = ApifyScraper(api_token="")  # No Apify token

        # StockTwits mock
        now = datetime.now(timezone.utc)
        recent_dt = now - timedelta(days=1)
        st_resp = MagicMock()
        st_resp.read.return_value = json.dumps({
            "messages": [{
                "id": 9999,
                "body": "$BABA breaking above resistance",
                "created_at": recent_dt.isoformat(),
                "user": {"username": "trader1"},
            }]
        }).encode("utf-8")
        st_resp.__enter__.return_value = st_resp

        # Reddit mock
        reddit_resp = MagicMock()
        reddit_resp.read.return_value = json.dumps({
            "data": {
                "children": [{
                    "data": {
                        "id": "rd01",
                        "title": "Alibaba AI chip investments",
                        "selftext": "Details here...",
                        "author": "tech_trader",
                        "created_utc": recent_dt.timestamp(),
                        "ups": 50,
                        "num_comments": 8,
                        "permalink": "/r/stocks/comments/rd01/alibaba/",
                    }
                }]
            }
        }).encode("utf-8")
        reddit_resp.__enter__.return_value = reddit_resp

        def urlopen_side_effect(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "stocktwits.com" in url:
                return st_resp
            elif "reddit.com" in url:
                return reddit_resp
            return MagicMock()

        with patch("urllib.request.urlopen", side_effect=urlopen_side_effect):
            posts = scraper.collect_for_ticker("9988.HK", "Alibaba Group", ["Alibaba"])

        platforms = {p["platform"] for p in posts}
        assert "StockTwits Financial Stream" in platforms
        assert "Reddit Finance (Public API)" in platforms
        assert len(platforms) == 2


# ---------------------------------------------------------------------------
# Strict 10-day lookback cutoff tests on actual production paths
# ---------------------------------------------------------------------------

def test_collect_for_ticker_enforces_10_day_cutoff_on_posts():
    """Verify collect_for_ticker() directly filters out posts older than 10 days,
    while preserving posts within 10 days and undated posts (timestamp=None).
    """
    scraper = ApifyScraper(api_token="")
    now = datetime.now(timezone.utc)
    fresh_dt = now - timedelta(days=3)
    stale_dt = now - timedelta(days=14)

    mock_st_data = {
        "messages": [
            {"id": 1, "body": "Recent post", "created_at": fresh_dt.isoformat()},
            {"id": 2, "body": "Stale post", "created_at": stale_dt.isoformat()},
            {"id": 3, "body": "Undated post", "created_at": None},
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_st_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp), \
         patch.object(scraper, "collect_reddit_for_ticker", return_value=[]):
        posts = scraper.collect_for_ticker("0700.HK", "Tencent", ["Tencent"], days_back=10)

    # Stale post must be excluded; fresh and undated posts must be present
    assert len(posts) == 2
    texts = [p["text"] for p in posts]
    assert "Recent post" in texts
    assert "Undated post" in texts
    assert "Stale post" not in texts


def test_pipeline_service_enforces_10_day_cutoff_in_production_path(monkeypatch):
    """Verify that PipelineService.collect_social_data() excludes posts older than 10 days
    and does not pass them to FinBERT or persist them to SentimentScore.
    """
    from backend.services.pipeline_service import PipelineService
    from database.models import SocialPost

    pipeline = PipelineService()
    now = datetime.now(timezone.utc)

    fresh_post = {
        "ticker": "0700.HK",
        "platform": "StockTwits Financial Stream",
        "text": "Fresh bullish sentiment",
        "author": "analyst1",
        "timestamp": now - timedelta(days=2),
        "likes": 5, "reposts": 0, "views": 0, "followers": 10,
        "url": "https://example.com/1", "is_demo_data": False,
        "has_original_timestamp": True, "collector": "Test"
    }

    stale_post = {
        "ticker": "0700.HK",
        "platform": "StockTwits Financial Stream",
        "text": "Stale 20-day-old post",
        "author": "analyst2",
        "timestamp": now - timedelta(days=20),
        "likes": 1, "reposts": 0, "views": 0, "followers": 5,
        "url": "https://example.com/2", "is_demo_data": False,
        "has_original_timestamp": True, "collector": "Test"
    }

    # Pipeline returns both from scraper
    pipeline.apify_scraper.collect_for_ticker = MagicMock(return_value=[fresh_post, stale_post])
    pipeline.finbert.analyze = MagicMock(return_value={
        "sentiment": "positive", "confidence": 0.9, "positive_prob": 0.9, "negative_prob": 0.05, "neutral_prob": 0.05
    })

    saved_posts = []
    saved_sentiments = []

    mock_session = MagicMock()
    mock_post_repo = MagicMock()
    mock_post_repo.bulk_insert_dedup.side_effect = lambda objs: saved_posts.extend(objs) or len(objs)
    mock_sent_repo = MagicMock()
    mock_sent_repo.create.side_effect = lambda obj: saved_sentiments.append(obj) or obj

    mock_factory = MagicMock()
    mock_factory.return_value.__enter__.return_value = mock_session
    mock_factory.return_value.__exit__.return_value = None

    import backend.services.pipeline_service as ps_mod
    monkeypatch.setattr(ps_mod, "SessionLocal", mock_factory)
    monkeypatch.setattr(ps_mod, "SocialPostRepository", lambda s: mock_post_repo)
    monkeypatch.setattr(ps_mod, "SentimentRepository", lambda s: mock_sent_repo)

    res = pipeline.collect_social_data(ticker="0700.HK")
    assert res["status"] == "success"

    # Only fresh post passed the 10-day filter; stale post was dropped!
    assert len(saved_posts) == 1
    assert saved_posts[0].text == "Fresh bullish sentiment"
    assert len(saved_sentiments) == 1


class TestApifyAssessmentListedScrapers:
    """Verify that Apify requests for assessment-listed sources (LIHKG & Naver Discussion)
    construct proper schemas, parse responses into unified SENTINEL format, and mock all network calls.
    """

    def test_collect_lihkg_parses_response_correctly(self):
        """Verify claude_code_reviewer~lihkg-scraper-en input schema dispatch and response parsing."""
        scraper = ApifyScraper(api_token="mock_apify_token_test")

        mock_items = [
            {
                "id": "3589123",
                "threadId": "3589123",
                "title": "騰訊控股 (0700.HK) 業績超預期，AI 雲業務增長強勁",
                "content": "騰訊第三季度收入同比增長8%，淨利潤大幅上升。",
                "userNickname": "連登股神",
                "createTime": 1730000000,
                "likeCount": 150,
                "dislikeCount": 12,
                "totalReplies": 45,
                "url": "https://lihkg.com/thread/3589123/page/1"
            },
            {
                "id": "3589124",
                "threadId": "3589124",
                "title": "無時間戳貼文",
                "content": "討論內容",
                "userNickname": "散戶",
                "createTime": None,
                "likeCount": 5,
                "totalReplies": 2,
            }
        ]

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_items).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        captured_requests = []

        def mock_urlopen(req, *args, **kwargs):
            captured_requests.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            posts = scraper.collect_lihkg_for_ticker("0700.HK", "Tencent", ["0700", "騰訊"], max_results=10)

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert "claude_code_reviewer~lihkg-scraper-en" in req.full_url
        assert "token=mock_apify_token_test" in req.full_url
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["mode"] == "search"
        assert "騰訊" in payload["keywords"]

        assert len(posts) == 2
        p1 = posts[0]
        assert p1["ticker"] == "0700.HK"
        assert p1["platform"] == "LIHKG (Apify Actor)"
        assert p1["author"] == "連登股神"
        assert p1["likes"] == 150
        assert p1["reposts"] == 45
        assert p1["has_original_timestamp"] is True
        assert isinstance(p1["timestamp"], datetime)
        assert p1["collector"] == "Apify API (LIHKG)"

        # Post 2: undated must have None timestamp
        p2 = posts[1]
        assert p2["timestamp"] is None
        assert p2["has_original_timestamp"] is False

    def test_collect_naver_discussion_parses_response_correctly(self):
        """Verify hgservices~naver-stock-discussion-scraper input schema dispatch and response parsing."""
        scraper = ApifyScraper(api_token="mock_apify_token_test")

        mock_items = [
            {
                "title": "삼성전자 3분기 실적 반등 기대감 및 HBM 로드맵 발표",
                "body": "외국인 순매수 지속 유입 중.",
                "author": "동학개미대장",
                "date": "2026-11-05T09:30:00+09:00",
                "likes": 88,
                "comments": 24,
                "views": 1540,
                "url": "https://finance.naver.com/item/board_read.naver?code=005930&nid=123"
            },
            {
                "title": "삼성전자 시간외 매수 주문 관련",
                "body": "내일 장 열리면 확인해보자",
                "author": "주식초보",
                "writtenAt": "2026-11-12 00:25:00",  # Unspecified tz from Naver web format (KST)
                "likes": 5,
                "comments": 1,
                "views": 42,
                "url": "https://finance.naver.com/item/board_read.naver?code=005930&nid=124"
            }
        ]

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_items).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        captured_requests = []

        def mock_urlopen(req, *args, **kwargs):
            captured_requests.append(req)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            posts = scraper.collect_naver_discussion_for_ticker("005930.KS", max_results=10)

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert "hgservices~naver-stock-discussion-scraper" in req.full_url
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["stocks"] == ["005930"]
        assert "dateFrom" in payload

        assert len(posts) == 2
        p = posts[0]
        assert p["ticker"] == "005930.KS"
        assert p["platform"] == "Naver Finance (Apify Actor)"
        assert p["author"] == "동학개미대장"
        assert p["likes"] == 88
        assert p["reposts"] == 24
        assert p["views"] == 1540
        assert p["has_original_timestamp"] is True
        assert isinstance(p["timestamp"], datetime)
        assert p["collector"] == "Apify API (Naver Finance)"

        # Verify second post: Naver naive timestamp was correctly localized from KST to UTC (-9 hours)
        p2 = posts[1]
        assert p2["timestamp"] is not None
        assert p2["timestamp"].year == 2026
        assert p2["timestamp"].month == 11
        assert p2["timestamp"].day == 11
        assert p2["timestamp"].hour == 15
        assert p2["timestamp"].minute == 25


def test_collect_for_ticker_rejects_future_dated_posts():
    """Verify that ApifyScraper.collect_for_ticker rejects future-dated posts."""
    scraper = ApifyScraper(api_token="mock_apify_token_test")
    now_utc = datetime.now(timezone.utc)
    future_ts = now_utc + timedelta(days=2)

    # Return future dated post from reddit collector
    future_post = {
        "ticker": "0700.HK",
        "platform": "Reddit Finance Stream",
        "text": "Future trading message",
        "author": "time_traveler",
        "timestamp": future_ts,
        "likes": 0,
        "reposts": 0,
        "views": 0,
        "followers": 0,
        "url": "https://example.com/future",
        "is_demo_data": False,
        "has_original_timestamp": True,
        "collector": "Mock"
    }

    with patch.object(scraper, "collect_reddit_for_ticker", return_value=[future_post]):
        with patch("urllib.request.urlopen", side_effect=Exception("stocktwits offline")):
            posts = scraper.collect_for_ticker(ticker="0700.HK", asset_name="Tencent", search_terms=["Tencent"], days_back=10)

    assert len(posts) == 0, f"Future dated post should be rejected, but got {posts}"


def test_pipeline_service_rejects_future_dated_posts(tmp_path):
    """Verify that PipelineService.collect_social_data rejects future-dated posts before database insert."""
    from backend.services.pipeline_service import PipelineService
    from database.repository import SocialPostRepository

    now_utc = datetime.now(timezone.utc)
    future_ts = now_utc + timedelta(days=1)

    mock_post = {
        "ticker": "0700.HK",
        "platform": "StockTwits Financial Stream",
        "text": "Future forecast post",
        "author": "futurist",
        "timestamp": future_ts,
        "likes": 10,
        "reposts": 2,
        "views": 100,
        "followers": 50,
        "url": "https://example.com/future-post",
    }

    with patch("backend.services.pipeline_service.get_settings"):
        service = PipelineService()
        with patch.object(service.apify_scraper, "collect_for_ticker", return_value=[mock_post]):
            with patch.object(SocialPostRepository, "bulk_insert_dedup", return_value=0) as mock_insert:
                service.collect_social_data(ticker="0700.HK")

    # Verify that the future post was rejected and never passed to bulk_insert_dedup
    assert mock_insert.call_count == 1
    passed_posts = mock_insert.call_args[0][0]
    assert len(passed_posts) == 0, f"Expected 0 posts to be passed to insert, got {len(passed_posts)}"

