"""Hong Kong Market Dashboard."""
import streamlit as st
import requests
import pandas as pd
from frontend.components.ui_components import inject_custom_css, render_top_bar, render_kpi_card
from frontend.components.table_renderer import render_styled_table

inject_custom_css()
API_URL = "http://127.0.0.1:8000/api"
render_top_bar()

st.title("🇭🇰 Hong Kong Stock Exchange (HKEX)")
st.caption("Active monitoring: 0700.HK (Tencent), 9988.HK (Alibaba), 1299.HK (AIA), 0005.HK (HSBC), 3690.HK (Meituan)")

try:
    r = requests.get(f"{API_URL}/signals?exchange=HKEX", timeout=5)
    signals = r.json() if r.status_code == 200 else []
except Exception:
    signals = []

if signals:
    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi_card("HKEX Assets", str(len(signals)), "Trading Currency: HKD", "neutral")
    with c2:
        top_bull = max(signals, key=lambda x: x.get("predicted_return_pct", 0.0))
        render_kpi_card("Top HK Asset", f"{top_bull['ticker']} ({top_bull.get('predicted_return_pct', 0.0):+.2f}%)", top_bull["asset_name"], "bullish" if top_bull.get("predicted_return_pct", 0.0) >= 0 else "bearish")
    with c3:
        tot_mentions = sum(s.get("social_mentions", 0) + s.get("news_count", 0) for s in signals)
        render_kpi_card("HK Discourse Items", str(tot_mentions), "Real Scraped Items", "neutral")

    st.markdown("### 📋 HKEX Asset Intelligence Board")
    display_rows = []
    for s in signals:
        curr = s.get("currency", "HKD")
        display_rows.append({
            "Ticker": s.get("ticker"),
            "Company": s.get("asset_name"),
            "Sector": s.get("sector"),
            "Latest Price": f"{s.get('latest_price', 0.0):,.2f} {curr}",
            "Target Price": f"{s.get('predicted_price', 0.0):,.2f} {curr}",
            "Return Target": f"{s.get('predicted_return_pct', 0.0):+.2f}%",
            "Direction": s.get("direction"),
            "FinBERT Score": f"{s.get('sentiment_score', 0.0):+.3f}",
            "Discourse Volume": s.get("social_mentions", 0) + s.get("news_count", 0),
            "Data Quality": s.get("data_quality")
        })
    df = pd.DataFrame(display_rows)
    render_styled_table(df)
else:
    st.info("Real data unavailable — ingestion required. Please trigger collection in Data Collection.")
