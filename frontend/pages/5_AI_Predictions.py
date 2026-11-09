"""AI Predictions Page - Multi-model forecast consensus."""
import streamlit as st
import requests
import pandas as pd
from frontend.components.ui_components import inject_custom_css, render_top_bar, render_kpi_card
from frontend.components.table_renderer import render_styled_table

inject_custom_css()
API_URL = "http://127.0.0.1:8000/api"
render_top_bar()

st.title("🤖 AI Predictions & Model Architecture Audit")
st.markdown("Predictive consensus across **Linear Regression**, **Random Forest**, **XGBoost**, and **Deep Learning ANN**.")

TICKERS = [
    "0700.HK", "9988.HK", "1299.HK", "0005.HK", "3690.HK",
    "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS"
]
selected_ticker = st.selectbox("Select Asset for Detailed Prediction Audit:", TICKERS, index=0)

try:
    sig = requests.get(f"{API_URL}/signals/{selected_ticker}", timeout=5).json()
    preds = requests.get(f"{API_URL}/predictions/{selected_ticker}", timeout=5).json()
except Exception:
    sig, preds = {}, []

curr = sig.get('currency', 'HKD' if '.HK' in selected_ticker else 'KRW')

col1, col2, col3 = st.columns(3)
with col1:
    render_kpi_card("Current Market Close", f"{sig.get('latest_price', 0):,.2f} {curr}", "Real Historical Baseline", "neutral")
with col2:
    p_price = sig.get('predicted_price', 0)
    p_ret = sig.get('predicted_return_pct', 0)
    render_kpi_card("Consensus Target", f"{p_price:,.2f} {curr}", f"Predicted Return: {p_ret:+.2f}%", "bullish" if p_ret >= 0 else "bearish")
with col3:
    render_kpi_card("Consensus Bias", sig.get('direction', 'No Data'), "Multi-Architecture Consensus", "bullish" if sig.get('direction') == 'Bullish' else "bearish")

st.markdown("### 🔬 Multi-Architecture Prediction Audit Table")
if preds:
    display_rows = []
    for p in preds:
        m_name = p.get("model_name", "").replace("_", " ").title()
        p_val = p.get("predicted_price", 0.0)
        r_val = p.get("predicted_return_pct", 0.0)
        c_low = p.get("confidence_lower")
        c_high = p.get("confidence_upper")
        
        display_rows.append({
            "Architecture": m_name,
            "Target Price Forecast": f"{p_val:,.2f} {curr}",
            "Expected Return": f"{r_val:+.2f}%",
            "95% Confidence Lower": f"{c_low:,.2f} {curr}" if c_low else "N/A",
            "95% Confidence Upper": f"{c_high:,.2f} {curr}" if c_high else "N/A",
            "Validation Scheme": "Walk-Forward (Zero Leakage)"
        })
    df = pd.DataFrame(display_rows)
    render_styled_table(df)
else:
    st.info("Real models not trained for this asset yet. Head to Data Collection & System Status to train all 4 architectures.")

st.markdown("### 🛡️ Rigorous Methodology Disclosure")
st.caption("""
All model predictions are trained strictly on chronologically sequenced observations with zero future look-ahead bias. The primary optimization objective is next-period return. Models are evaluated against the naïve previous-close persistence baseline.
""")
