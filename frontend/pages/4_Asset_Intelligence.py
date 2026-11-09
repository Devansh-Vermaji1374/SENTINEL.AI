"""Single Asset Micro-Intelligence Page."""
import streamlit as st
import requests
import pandas as pd
from frontend.components.ui_components import (
    inject_custom_css, render_top_bar, render_kpi_card,
    create_candlestick_chart, create_sentiment_gauge
)

inject_custom_css()
API_URL = "http://127.0.0.1:8000/api"
render_top_bar()

TICKERS = [
    "0700.HK", "9988.HK", "1299.HK", "0005.HK", "3690.HK",
    "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS"
]

selected_ticker = st.selectbox("Select Asset to Inspect:", TICKERS, index=0)

try:
    sig = requests.get(f"{API_URL}/signals/{selected_ticker}", timeout=5).json()
except Exception:
    sig = {}

st.title(f"🔍 {selected_ticker} — {sig.get('asset_name', 'Asset Intelligence')}")
curr = sig.get('currency', 'HKD' if '.HK' in selected_ticker else 'KRW')
st.caption(f"Exchange: {sig.get('exchange', 'N/A')} | Sector: {sig.get('sector', 'N/A')} | Data Source: {sig.get('data_quality', 'Real Data')}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_kpi_card("Latest Real Close", f"{sig.get('latest_price', 0):,.2f} {curr}", "Real Market Price", "neutral")
with col2:
    pred_ret = sig.get('predicted_return_pct', 0.0)
    render_kpi_card("AI Predicted Return", f"{pred_ret:+.2f}%", f"Next Session: {sig.get('predicted_price', 0):,.2f}", "bullish" if pred_ret >= 0 else "bearish")
with col3:
    render_kpi_card("Directional Bias", sig.get('direction', 'No Data'), f"Signal Strength: {sig.get('signal_strength', 0)}/100", "bullish" if sig.get('direction') == 'Bullish' else ("bearish" if sig.get('direction') == 'Bearish' else "neutral"))
with col4:
    tot_disc = sig.get('social_mentions', 0) + sig.get('news_count', 0)
    render_kpi_card("FinBERT Score", f"{sig.get('sentiment_score', 0):+.3f}", f"Discourse Items: {tot_disc}", "bullish" if sig.get('sentiment_score', 0) > 0 else "bearish")

st.markdown("---")

col_chart, col_side = st.columns([2.5, 1])

with col_chart:
    st.subheader("📈 Real Price Action & Pivot Levels")
    try:
        m_data = requests.get(f"{API_URL}/market-data/{selected_ticker}?limit=120", timeout=5).json()
        if m_data:
            m_df = pd.DataFrame(m_data)
            fig_candle = create_candlestick_chart(
                m_df,
                selected_ticker,
                support_levels=sig.get("support_levels", []),
                resistance_levels=sig.get("resistance_levels", [])
            )
            st.plotly_chart(fig_candle, width="stretch")
        else:
            st.warning("Real data unavailable — ingestion required. Please trigger collection.")
    except Exception as e:
        st.error(f"Failed to fetch market data: {e}")

with col_side:
    st.subheader("🧭 Real FinBERT Gauge")
    fig_gauge = create_sentiment_gauge(sig.get("sentiment_score", 0.0), sig.get("overall_sentiment", "No Data"))
    st.plotly_chart(fig_gauge, width="stretch")

    st.markdown("#### Technical & Fundamental Levels")
    st.markdown(f"""
    - **Primary Support:** `{sig.get('support_levels', ['N/A'])[0] if sig.get('support_levels') else 'N/A'} {curr}`
    - **Primary Resistance:** `{sig.get('resistance_levels', ['N/A'])[0] if sig.get('resistance_levels') else 'N/A'} {curr}`
    - **FinBERT News Score:** `{sig.get('news_sentiment', 0.0):+.3f}`
    - **Social Discourse Score:** `{sig.get('social_sentiment', 0.0):+.3f}`
    """)
