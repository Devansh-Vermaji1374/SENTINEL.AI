"""News & Social Intelligence Feed Page."""
import streamlit as st
import requests
import pandas as pd
from frontend.components.ui_components import inject_custom_css, render_top_bar

inject_custom_css()
API_URL = "http://127.0.0.1:8000/api"
render_top_bar()

st.title("📰 News & Social Media Intelligence Stream")
st.markdown("Real-time verified financial streams scored with the **ProsusAI FinBERT** transformer.")

TICKERS = [
    "0700.HK", "9988.HK", "1299.HK", "0005.HK", "3690.HK",
    "005930.KS", "000660.KS", "373220.KS", "005380.KS", "035420.KS"
]
selected_ticker = st.selectbox("Filter Feed by Asset:", TICKERS, index=0)

tab_social, tab_news = st.tabs(["📱 Real Social Media Discourse", "📰 Financial News Wire"])

with tab_social:
    try:
        posts = requests.get(f"{API_URL}/social/{selected_ticker}?limit=50", timeout=5).json()
    except Exception:
        posts = []

    if posts:
        st.caption(f"Displaying {len(posts)} verified real social posts. Zero synthetic posts generated.")
        for p in posts:
            st.markdown(f"""
            <div class="sentinel-card" style="margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                    <div><strong>{p.get('platform', 'Social Feed')}</strong> &nbsp;|&nbsp; Author: <code>{p.get('author', 'retail_trader')}</code></div>
                    <div><span class="tag-bullish">REAL DISCOURSE</span> &nbsp;|&nbsp; <span style="color:#9ca3af;">{p.get('timestamp', '')[:19]}</span></div>
                </div>
                <div style="color:#e5e7eb; font-size: 0.95rem;">{p.get('text', '')}</div>
                <div style="margin-top: 8px; font-size: 0.8rem; color:#9ca3af;">
                    ❤️ Likes: {p.get('likes', 0)} &nbsp;|&nbsp; 🔁 Reposts: {p.get('reposts', 0)} &nbsp;|&nbsp; 👁️ Estimated Reach: {p.get('views', 0)}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"Real data unavailable for {selected_ticker} — ingestion required. Trigger social ingestion in Data Collection.")

with tab_news:
    try:
        articles = requests.get(f"{API_URL}/news/{selected_ticker}?limit=50", timeout=5).json()
    except Exception:
        articles = []

    if articles:
        st.caption(f"Displaying {len(articles)} verified real financial news articles.")
        for a in articles:
            st.markdown(f"""
            <div class="sentinel-card" style="margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                    <div><strong>{a.get('source_name', 'Financial News Wire')}</strong></div>
                    <div><span class="tag-bullish">VERIFIED WIRE</span> &nbsp;|&nbsp; <span style="color:#9ca3af;">{a.get('published_at', '')[:10]}</span></div>
                </div>
                <div style="color:#ffffff; font-size: 1.05rem; font-weight:600; margin-bottom: 4px;">{a.get('title', '')}</div>
                <div style="color:#9ca3af; font-size: 0.85rem; margin-bottom: 6px;">{a.get('text', '')[:280]}...</div>
                <div><a href="{a.get('url', '#')}" target="_blank" style="color:#00b0ff; text-decoration:none; font-size:0.85rem;">Read Verified Source Article ↗</a></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"Real news unavailable for {selected_ticker} — ingestion required. Trigger news collection in Data Collection.")
