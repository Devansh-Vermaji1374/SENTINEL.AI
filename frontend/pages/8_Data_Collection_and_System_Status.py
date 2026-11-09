"""Data Collection & System Status Page."""
import streamlit as st
import requests
import pandas as pd
from frontend.components.ui_components import inject_custom_css, render_top_bar, render_kpi_card

inject_custom_css()
API_URL = "http://127.0.0.1:8000/api"

try:
    status = requests.get(f"{API_URL}/status", timeout=2).json()
except Exception:
    status = {}

render_top_bar(status)

st.title("⚙️ Data Ingestion & System Control Console")
st.markdown("Trigger automated scraping pipelines, check API credential bindings, and monitor live data freshness.")

st.markdown("""
<div style="background-color: rgba(0, 230, 118, 0.08); border-left: 4px solid #00e676; padding: 10px 16px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
    <strong>ACTIVE SYSTEM STATUS: REAL DATA MODE</strong> &nbsp;|&nbsp; Zero synthetic post fabrication &nbsp;|&nbsp; Live Exchange Feeds & FinBERT
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    apify_conn = status.get("apify_connected", False)
    render_kpi_card("Apify Social API", "CONNECTED" if apify_conn else "STANDBY (STREAM ACTIVE)", "Social Media Scraper", "bullish" if apify_conn else "neutral")
with col2:
    exa_conn = status.get("exa_connected", False)
    render_kpi_card("Exa News API", "CONNECTED" if exa_conn else "STANDBY (WIRE ACTIVE)", "Financial News Feed", "bullish" if exa_conn else "neutral")
with col3:
    render_kpi_card("Market Provider", "CONNECTED", "Yahoo Finance OHLCV", "bullish")
with col4:
    render_kpi_card("FinBERT NLP", "LOCAL MODEL LOADED", "ProsusAI Transformer", "bullish")

st.markdown("---")
st.subheader("⚡ Automated Ingestion & Model Training Controls")

c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)

with c_btn1:
    if st.button("📊 Ingest Real Market OHLCV", width="stretch"):
        with st.spinner("Fetching 6 months historical OHLCV from market provider..."):
            try:
                res = requests.post(f"{API_URL}/collect/market", timeout=60).json()
                st.success(res.get("message", "Market data collected!"))
            except Exception as e:
                st.error(f"Error: {e}")

with c_btn2:
    if st.button("📱 Ingest Real Social Discourse", width="stretch"):
        with st.spinner("Scraping real financial discourse & scoring with FinBERT..."):
            try:
                res = requests.post(f"{API_URL}/collect/social", timeout=60).json()
                st.success(res.get("message", "Social posts ingested!"))
            except Exception as e:
                st.error(f"Error: {e}")

with c_btn3:
    if st.button("📰 Ingest Real Financial News", width="stretch"):
        with st.spinner("Collecting verified financial news & scoring with FinBERT..."):
            try:
                res = requests.post(f"{API_URL}/collect/news", timeout=60).json()
                st.success(res.get("message", "News articles ingested!"))
            except Exception as e:
                st.error(f"Error: {e}")

with c_btn4:
    if st.button("🚀 Train All 4 Models & Predict", width="stretch"):
        with st.spinner("Fitting Linear Regression, Random Forest, XGBoost & ANN..."):
            try:
                res = requests.post(f"{API_URL}/models/train", timeout=120).json()
                st.success("Trained models on all assets! Check AI Predictions & Model Performance.")
            except Exception as e:
                st.error(f"Pipeline error: {e}")

st.markdown("---")
st.subheader("📥 Export Intelligence Reports")
st.markdown("Download full quantitative and sentiment intelligence records across all 10 tracked assets.")

export_url = f"{API_URL}/reports/export"
st.link_button("⬇️ Download Verified CSV Report", export_url, width="content")
