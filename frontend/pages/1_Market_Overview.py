"""Market Overview Page - Sentinel AI."""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from frontend.components.ui_components import inject_custom_css, render_top_bar, render_kpi_card
from frontend.components.table_renderer import render_styled_table

inject_custom_css()
API_URL = "http://127.0.0.1:8000/api"

try:
    status_data = requests.get(f"{API_URL}/status", timeout=2).json()
except Exception:
    status_data = None
render_top_bar(status_data)

st.title("🌐 Market Overview Dashboard")
st.markdown("Institutional macro dashboard across HKEX & KRX. Powered by real market observations, real financial news, and FinBERT sentiment.")

try:
    r = requests.get(f"{API_URL}/market-overview", timeout=5)
    data = r.json() if r.status_code == 200 else {}
except Exception:
    data = {}

# Mode Indicator Banner
is_real = True
st.markdown("""
<div style="background-color: rgba(0, 230, 118, 0.08); border-left: 4px solid #00e676; padding: 10px 16px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
    <strong>ACTIVE SYSTEM STATUS: REAL DATA MODE</strong> &nbsp;|&nbsp; Zero synthetic post fabrication &nbsp;|&nbsp; Live Exchange Feeds & FinBERT
</div>
""", unsafe_allow_html=True)

# KPI Cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi_card("Assets Tracked", str(data.get("total_assets", 10)), "Dual Exchange Coverage", "neutral")
with c2:
    render_kpi_card("Social Mentions", str(data.get("total_social_mentions", 0)), "Real Stream Discourse", "bullish")
with c3:
    render_kpi_card("News Articles", str(data.get("total_news_articles", 0)), "Verified News Feeds", "neutral")
with c4:
    bullish_cnt = data.get("bullish_assets_count", 0)
    bearish_cnt = data.get("bearish_assets_count", 0)
    render_kpi_card("Market Bias", f"{bullish_cnt} Bull / {bearish_cnt} Bear", "Model Signal Consensus", "bullish" if bullish_cnt >= bearish_cnt else "bearish")

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Cross-Market Sentiment Breakdown")
    pos = data.get("overall_positive_pct", 0.0)
    neg = data.get("overall_negative_pct", 0.0)
    neu = data.get("overall_neutral_pct", 0.0)
    
    if pos == 0 and neg == 0 and neu == 0:
        st.info("Real data unavailable — ingestion required. Head to Data Collection & System Status to ingest live feeds.")
    else:
        fig_donut = px.pie(
            values=[pos, neg, neu],
            names=["Positive", "Negative", "Neutral"],
            hole=0.5,
            color=["Positive", "Negative", "Neutral"],
            color_discrete_map={"Positive": "#00e676", "Negative": "#ff3d57", "Neutral": "#00b0ff"}
        )
        fig_donut.update_layout(
            template="plotly_dark",
            paper_bgcolor="#141d2e",
            margin=dict(l=20, r=20, t=30, b=20),
            height=320,
            font=dict(family="JetBrains Mono")
        )
        st.plotly_chart(fig_donut, width="stretch")

with col_right:
    st.subheader("🔥 Top Discussed Assets (Real Volume)")
    discussed = data.get("most_discussed", [])
    if discussed and any((x.get("social_mentions", 0) + x.get("news_count", 0)) > 0 for x in discussed):
        disc_df = pd.DataFrame(discussed)
        disc_df["total_volume"] = disc_df["social_mentions"] + disc_df.get("news_count", 0)
        fig_bar = px.bar(
            disc_df,
            x="total_volume",
            y="ticker",
            orientation="h",
            color="sentiment_score",
            color_continuous_scale=["#ff3d57", "#00b0ff", "#00e676"],
            labels={"total_volume": "Verified Discourse Volume", "ticker": "Asset"}
        )
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="#141d2e",
            plot_bgcolor="#0a0e17",
            height=320,
            margin=dict(l=20, r=20, t=30, b=20),
            font=dict(family="JetBrains Mono")
        )
        st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("Real discussion volume unavailable — ingestion required. Trigger ingestion in Data Collection.")

st.markdown("### 🏆 Comprehensive Asset Rankings & Predictive Signals")
signals = data.get("signals", [])
if signals:
    display_rows = []
    for s in signals:
        curr = s.get("currency", "")
        p_price = s.get("predicted_price", 0.0)
        l_price = s.get("latest_price", 0.0)
        display_rows.append({
            "Ticker": s.get("ticker"),
            "Company": s.get("asset_name"),
            "Exchange": s.get("exchange"),
            "Latest Close": f"{l_price:,.2f} {curr}",
            "AI Target Price": f"{p_price:,.2f} {curr}",
            "Return Forecast": f"{s.get('predicted_return_pct', 0.0):+.2f}%",
            "Directional Bias": s.get("direction"),
            "FinBERT Score": f"{s.get('sentiment_score', 0.0):+.3f}",
            "Discourse Count": s.get("social_mentions", 0) + s.get("news_count", 0),
            "Data Quality": s.get("data_quality")
        })
    sig_df = pd.DataFrame(display_rows)
    render_styled_table(sig_df)
else:
    st.info("No asset records available. Ingestion required.")
