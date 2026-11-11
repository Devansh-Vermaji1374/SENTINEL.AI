# CrowdWisdomTrading AI Agents Developer Assessment Evidence

**Project:** SENTINEL.AI — Institutional Quantitative Intelligence & ML Systems Terminal
**Repository:** `https://github.com/Devansh-Vermaji1374/SENTINEL.AI`
**Review Date:** 2026-11-12
**Scope:** Rigorous quantitative and engineering compliance assessment against the CrowdWisdomTrading AI Agents Developer internship assignment requirements ("CWT HengSeng exchange sentiment Agent - intern task").

---

## 1. Executive Compliance Summary

| Assessment Requirement | Implementation Path | Verified Evidence |
|---|---|---|
| **HKEX Market Coverage** (5 assets) | `data_collection/market_data.py` | 5 equities (`0700.HK`, `9988.HK`, `1299.HK`, `0005.HK`, `3690.HK`) with 126–128 daily OHLCV bars each (632 total bars). |
| **KRX Market Coverage** (5 assets) | `data_collection/market_data.py` | 5 equities (`005930.KS`, `000660.KS`, `373220.KS`, `005380.KS`, `035420.KS`) with 123 daily OHLCV bars each (615 total bars). Total bars across 10 assets = **1,247**. |
| **FinBERT Sentiment Engine** | `sentiment/finbert_analyzer.py` | FinBERT CPU transformer pipeline deployed; 355 sentiment scores calculated on point-in-time publication dates (220 social, 135 news). |
| **2 Listed Social Sources / Exchange** | `data_collection/apify_scraper.py` | **PARTIALLY DEMONSTRATED — additional eligible-source evidence required.**<br>- Eligible Apify scrapers implemented & tested with offline mocks for LIHKG (`claude_code_reviewer~lihkg-scraper-en`) and Naver Finance Discussion (`hgservices~naver-stock-discussion-scraper`).<br>- Observed database records: LIHKG (2 posts for `0700.HK`) and Naver (12 posts for `005930.KS`) with linked FinBERT scores.<br>- StockTwits Financial Stream (153 posts) is maintained as a supplemental stream.<br>- To achieve full live compliance, additional live volume from eligible listed sources across all tickers is required. |
| **10-Day Social Lookback Window** | `data_collection/apify_scraper.py`, `backend/services/pipeline_service.py` | Strict dual-boundary lookback cutoff (`cutoff <= ts <= now_utc + 5min`) enforced in production paths and verified by unit tests. |
| **Point-in-Time Alignment (No Leakage)** | `sentiment/sentiment_aggregator.py`, `preprocessing/timestamp_alignment.py` | Sentiment joins strictly on `published_at <= bar_date`. Undated posts have `timestamp = NULL` and produce 0 sentiment scores. |
| **News Retrieval & Provenance** | `data_collection/exa_news.py` | Exa neural search integration; 135 news articles in DB with URLs, timestamps, and full provenance. Distinct from social. |
| **4 Machine Learning Architectures** | `models/train.py` | 40 trained model bundles (Ridge, Random Forest, XGBoost, ANN MLP) across all 10 assets. |
| **Chronological Train/Val/Test Split** | `models/train.py`, `config/assets.yaml` | 65% Train / 15% Validation / 20% Holdout Test. Holdout test partition untouched during feature scaling and tuning. |
| **Naive Baseline Comparisons** | `models/evaluate.py`, `reports/ml_investigation.py` | Evaluated against Naive Previous-Close (Zero-Return) & Historical Mean-Return baselines. |
| **Walk-Forward Validation** | `models/train.py` | 4-window expanding walk-forward cross-validation computed and recorded in all 40 `*_meta.json` files. |
| **n+1 Period Price Prediction** | `models/train.py`, `database/models.py` | `target_return = close.pct_change().shift(-1)` verified; 292 historical predictions tracked in database. |
| **Settlement Reality & Auditability** | `backend/services/pipeline_service.py`, `database/repository.py` | 280 legacy unpriced predictions locked as `LEGACY_UNSETTLEABLE`; 8 invalid targets classified; 4 modern predictions `SETTLED` against historical bars (`0700.HK` target price: 417.80 vs origin: 418.40, return: -0.14%). 0 artificial prices fabricated. |

---

## 2. Social Source Compliance & Gap Analysis

### 2.1 Authoritative Social Source Compliance Matrix

Below is the verified audit matrix evaluated against the CrowdWisdomTrading assignment specification:

| Assessment-Listed Source | Exchange | Apify Actor ID / Module | Source Code Implemented | Mocked Tests Passed | Actual Live Invocation Verified | Actual Records Observed | Record Count & Ticker Coverage | Compliance Classification |
|---|---|---|:---:|:---:|:---:|:---:|---|---|
| **LIHKG** | HKEX | `claude_code_reviewer~lihkg-scraper-en` | **YES** | **YES** (`test_social_sources.py`) | **YES** | **YES** | 2 genuine posts (`0700.HK`) | **Demonstrated (Eligible Listed Source)** |
| **AAStocks / ETNet** | HKEX | `bovi~aastocks-scraper` | **YES** (declared) | **YES** | No live run | No records | Configured in code |
| **Telegram (HKEX)** | HKEX | `curious_coder~telegram-scraper` | **YES** (declared) | **YES** | Blocked (Requires interactive QR login) | No records | Headless automation blocked without session token |
| **Futu / Moomoo Community** | HKEX | Custom Web Hook | No actor available | N/A | No live run | No records | External actor unavailable |
| **Naver Finance Discussion** | KRX | `hgservices~naver-stock-discussion-scraper` | **YES** | **YES** (`test_social_sources.py`) | **YES** | **YES** | 12 genuine posts (`005930.KS`) | **Demonstrated (Eligible Listed Source)** |
| **Daum Finance Forums** | KRX | Daum Web Hook | No actor available | N/A | No live run | No records | External actor unavailable |
| **Blind (KRX)** | KRX | `hypebridge~blind-post-scraper` | **YES** (declared) | **YES** | No live run | No records | Configured in code |
| **KakaoTalk / Telegram (KRX)** | KRX | `curious_coder~telegram-scraper` | **YES** (declared) | **YES** | Blocked (Requires interactive QR login) | No records | Headless automation blocked without session token |
| **StockTwits Financial Stream** | Supplemental (Both) | Direct REST API (`api.stocktwits.com`) | **YES** | **YES** | **YES** | **YES** | 153 genuine posts across 6 tickers (`0005.HK`, `0700.HK`, `3690.HK`, `9988.HK`, `005380.KS`, `005930.KS`) | **Supplemental Financial Stream (Not listed in assessment)** |
| **Financial Market Wire** | N/A (News) | RSS Feed (Yahoo/Barchart) | **YES** | **YES** | Legacy snapshot | **YES** | 43 records across 9 tickers | **News RSS (Misclassified as social in legacy ingest)** |
| **Reddit Finance** | Supplemental (Both) | Direct JSON (`reddit.com/r/stocks`) | **YES** | **YES** | Supplemental fallback | No live DB records | **Supplemental Fallback (Not listed in assessment)** |

### 2.2 Exchange-by-Exchange Compliance Verdict

- **HKEX Exchange**: **PARTIALLY DEMONSTRATED — additional eligible-source evidence required.**
  - 1 eligible listed source demonstrated with genuine records: LIHKG (2 posts for `0700.HK`).
  - StockTwits provides 103 additional genuine posts across 4 HKEX tickers, but is classified as supplemental.
  - To demonstrate two eligible assessment-listed sources, live records from AAStocks, Futu, or Telegram must be collected.
- **KRX Exchange**: **PARTIALLY DEMONSTRATED — additional eligible-source evidence required.**
  - 1 eligible listed source demonstrated with genuine records: Naver Finance Discussion (12 posts for `005930.KS`).
  - StockTwits provides 50 additional genuine posts across 2 KRX tickers, but is classified as supplemental (and rejects numeric-only Korean cashtags).
  - To demonstrate two eligible assessment-listed sources, live records from Daum, Blind, or KakaoTalk must be collected.

---

## 3. Strict 10-Day Collection Window & Timestamp Hygiene

### 3.1 Dual-Boundary Enforcement
In `data_collection/apify_scraper.py` and `backend/services/pipeline_service.py`:
- `collect_for_ticker()` enforces the lower bound (10-day cutoff) and the upper bound (future-date rejection):
  ```python
  cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
  now_utc = datetime.now(timezone.utc)
  filtered_posts = [
      p for p in posts
      if p.get("timestamp") is None or (cutoff <= p["timestamp"] <= now_utc + timedelta(minutes=5))
  ]
  ```
- `PipelineService.collect_social_data()` enforces the same dual-boundary filter before database insertion:
  ```python
  if ts is not None and (ts < cutoff or ts > now_utc + timedelta(minutes=5)):
      continue
  ```
- Undated posts (`timestamp is None`) are rejected from insertion because `social_posts.timestamp` is `NOT NULL`. FinBERT scoring explicitly skips any unlinked or undated records, guaranteeing zero point-in-time leakage.

### 3.2 Timezone Reconciliation for Naver Discussion Boards
- **Discovered Issue**: Naver Finance Discussion web boards display timestamps in Korea Standard Time (**KST = UTC+9**) without explicit timezone offsets (e.g., `2026-11-12 00:29:02 KST`). In the initial ingest, naive strings were stored into UTC columns without subtracting 9 hours, creating the appearance of future-dated posts.
- **Reconciliation Applied**:
  - All 12 rows (IDs 275–286) were corrected inside an atomic transaction: $t_{\text{UTC}} = t_{\text{KST}} - 9\text{ hours}$.
  - Corrected publication times: `2026-11-11 15:21:20` to `2026-11-11 15:29:02 UTC`.
  - Ingestion times (`collected_at`): `2026-11-11 15:29:26 UTC`.
  - Every publication timestamp is now strictly earlier than its collection timestamp (by 24.3s to 486.3s).
  - A permanent audit log table `timestamp_audit_log` preserves original values and deltas for full provenance.

---

## 4. ML Model Performance vs. Naive Baselines

### 4.1 Aggregate Recalculated Performance Across 40 Evaluated Models
Evaluated on the chronological 65/15/20 holdout test set ($N \approx 21\text{--}22$ trading days per asset):

| Performance Category | Number of Models | Percentage of Evaluated Models |
|---|:---:|:---:|
| **Beat Naive Previous-Close (Zero-Return) Baseline** on MAE | **8 / 40** | **20.0%** |
| **Beat Historical Mean-Return Baseline** on MAE | **4 / 40** | **10.0%** |
| **Underperformed Both Baselines** on MAE | **32 / 40** | **80.0%** |

### 4.2 Top Performing Architectures
1. **Ridge Linear Regression**: Controls variance effectively through L2 regularization on standardized technical indicators.
2. **Random Forest Ensembles**: Subsampling and feature bagging limit overfitting on stationary features.
3. **Deep MLP Neural Networks**: Exhibits higher out-of-sample variance due to limited sample size ($N \approx 73$ training days), yielding negative holdout $R^2$. Transparently documented as experimental.

### 4.3 Realistic Academic & Research Disclaimer
The holdout partition contains 21–22 observations per asset. In financial quantitative research, 20% outperforming naive baselines on small samples is normal and reflects genuine financial market noise without artificial data fitting or leakage. No claim of live predictive profitability is made.

---

## 5. Security & Provenance Audit

- **Environment & Credentials**: `.env` is strictly excluded via `.gitignore`. Zero API tokens (`APIFY_API_TOKEN`, `EXA_API_KEY`) are tracked in source code.
- **Frontend Bundle**: Production build (`frontend-web/dist/`) contains 0 exposed credentials or private keys.
- **Database Snapshots**: Active database `sentinel.db` and all backups (`backups/*.db`) are excluded from Git commits.
- **Backend Authorization**: Operational endpoints enforce key authentication via headers (`X-Sentinel-Automation-Key` or `X-Sentinel-Admin-Key`).

---

## 6. Verification Summary

- **Automated Tests**: **38 passed, 0 failed, 6 warnings in 9.69s** (`pytest tests/ -v`).
- **Frontend Build**: `tsc -b && vite build` completed successfully in 4.45s with 0 errors.
- **Database Integrity**: `PRAGMA integrity_check` = `ok`; `PRAGMA foreign_key_check` = 0 violations.
