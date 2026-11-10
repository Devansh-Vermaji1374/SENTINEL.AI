# SENTINEL.AI — n8n Orchestration & Automation Guide

## Architecture Overview

In SENTINEL.AI, **Python and FastAPI remain the single source of truth** for:
- Financial mathematical calculations and technical indicators.
- Transformer-based FinBERT NLP inference.
- Machine learning model training, walk-forward validation, and artifact persistence.
- Prediction lifecycle management and settlement logic.

**n8n** operates purely as an external scheduling and workflow automation layer that triggers FastAPI endpoints using secure header-authenticated HTTP requests.

---

## Workflows Included (`workflows/n8n/`)

| Workflow File | Name | Purpose | Trigger Schedule | Protected Endpoint Called |
| :--- | :--- | :--- | :--- | :--- |
| `workflow_a_market_data.json` | Workflow A | Market Data Ingestion | Every 4 hours | `POST /api/collect/market` |
| `workflow_b_social_data.json` | Workflow B | Social Media Scraper | Every 6 hours | `POST /api/collect/social` |
| `workflow_c_news_data.json` | Workflow C | News Wire Ingestion | Every 6 hours | `POST /api/collect/news` |
| `workflow_d_sentiment.json` | Workflow D | FinBERT Alignment | Every 6 hours | `POST /api/collect/all` |
| `workflow_e_predictions.json` | Workflow E | Model Inference Generation | Every 12 hours | `POST /api/models/train` |
| `workflow_f_settlement.json` | Workflow F | Prediction Settlement | Every 4 hours | `POST /api/predictions/settle` |
| `workflow_g_daily_report.json`| Workflow G | Daily Intelligence Report | Daily 18:00 M-F | `GET /api/market-overview`, `GET /api/status` |
| `workflow_h_failure_alerts.json`| Workflow H | Platform Failure Alerts | Hourly | `GET /api/status` |

---

## Authentication & Security

Automation endpoints require an authentication header:
```http
X-Sentinel-Automation-Key: <AUTOMATION_API_KEY>
```
Or a Bearer token:
```http
Authorization: Bearer <AUTOMATION_API_KEY>
```
If an unauthenticated request is sent, FastAPI returns:
```json
{
  "detail": "Unauthorized: Valid X-Sentinel-Automation-Key header or Bearer token required for automation endpoints."
}
```

---

## Running with Docker Compose

To run SENTINEL.AI and n8n together:
```bash
docker compose -f docker-compose.n8n.yml up -d
```
1. Open n8n in your browser at `http://localhost:5678`.
2. Go to **Workflows -> Import from File** and select any workflow from `workflows/n8n/`.
3. Set the environment variable `SENTINEL_AUTOMATION_KEY` in your n8n settings or `.env`.

> [!NOTE]
> **Operational Distinction**: Generating and providing importable workflow JSON files enables reproducible automation. In environments where Docker or n8n CLI is not locally installed, workflows are marked as *Specification Ready / Exported* rather than *Live Executing*.
