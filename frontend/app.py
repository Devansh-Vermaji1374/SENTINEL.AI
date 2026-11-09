"""SENTINEL AI - Streamlit Dashboard Entry Point."""
from __future__ import annotations

import streamlit as st
import requests
import pandas as pd
from frontend.components.ui_components import inject_custom_css, render_top_bar, render_kpi_card

st.set_page_config(
    page_title="SENTINEL AI | Financial Intelligence Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Institutional Dark Styles
inject_custom_css()

# API Base URL
API_URL = "http://127.0.0.1:8000/api"

def get_system_status():
    try:
        r = requests.get(f"{API_URL}/status", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"status": "offline", "app_env": "local", "apify_connected": False, "exa_connected": False}

status_data = get_system_status()
render_top_bar(status_data)

# Sidebar Navigation
st.sidebar.markdown("""
<div style="padding: 10px 0 16px 0;">
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; font-weight: 800; color: #ffffff; letter-spacing: 0.08em;">
        🛡️ SENTINEL<span style="color: #00b0ff;">.AI</span>
    </div>
    <div style="color: #6b7280; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 2px;">
        Institutional Terminal v2.0
    </div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

st.sidebar.markdown("""
<div style="background: #141d2e; border: 1px solid #1f2d42; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
    <div style="color: #00b0ff; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 6px;">Active Feeds</div>
    <div style="font-size: 0.8rem; color: #d1d5db; line-height: 1.6;">
        <div>🇭🇰 <strong>HKEX:</strong> 5 Equities (HKD)</div>
        <div>🇰🇷 <strong>KRX:</strong> 5 Equities (KRW)</div>
    </div>
    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #1f2d42; font-size: 0.72rem; color: #9ca3af;">
        NLP: <strong style="color: #00e676;">FinBERT Transformer</strong><br/>
        Models: <strong style="color: #00e676;">4 Architectures</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# Quick Navigation helper
st.sidebar.markdown("---")
st.sidebar.caption("Navigate using the Pages menu above.")

# Welcome Landing
st.title("Welcome to Sentinel AI Intelligence Terminal")
st.markdown("""
Sentinel AI is an institutional-grade multi-market intelligence platform designed to extract alpha from financial social media discourse, breaking news sentiment, and technical market microstructure.
""")

col1, col2, col3 = st.columns(3)
with col1:
    render_kpi_card("Exchange Coverage", "2 Markets", "HKEX & KRX", trend="neutral")
with col2:
    render_kpi_card("Assets Tracked", "10 Equities", "5 HK / 5 KR", trend="bullish")
with col3:
    render_kpi_card("Prediction Engine", "Active", "XGBoost + RF + LR", trend="bullish")

st.markdown("### Terminal Navigation Guide")
st.markdown("""
- **Market Overview**: Cross-exchange macro dashboard, mention volume & directional sentiment distribution.
- **Hong Kong Market**: Dedicated deep-dive for Tencent, Alibaba, AIA, HSBC, and Meituan.
- **South Korea Market**: Dedicated deep-dive for Samsung, SK Hynix, LG Energy, Hyundai, and Naver.
- **Asset Intelligence**: Single-asset microanalysis, live interactive candlestick, support/resistance.
- **AI Predictions**: Multi-model next-period price and return forecast consensus.
- **News & Social Intelligence**: Social stream, news feed, and FinBERT sentiment probability distributions.
- **Model Performance**: Walk-forward validation, RMSE/MAE metrics, and baseline comparison.
- **Data Collection & System Status**: Live ingestion console, Apify & Exa trigger controls.
""")
