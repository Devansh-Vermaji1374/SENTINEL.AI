"""UI Reusable visual elements and Plotly financial charts."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

def inject_custom_css():
    """Inject institutional dark styles."""
    with open("frontend/styles/custom.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def render_top_bar(status_data: Dict[str, Any] = None):
    """Render top financial ticker bar."""
    env = status_data.get("app_env", "PROD").upper() if status_data else "DEV"
    apify_status = "ONLINE (LIVE)" if status_data and status_data.get("apify_connected") else "DEMO MODE"
    exa_status = "ONLINE (LIVE)" if status_data and status_data.get("exa_connected") else "DEMO MODE"
    
    st.markdown(f"""
    <div class="bloomberg-bar">
        <div><strong>SENTINEL AI TERMINAL</strong> | HKEX / KRX DUAL-MARKET INTELLIGENCE</div>
        <div>
            APIFY: <span class="{'tag-bullish' if 'LIVE' in apify_status else 'tag-demo'}">{apify_status}</span> &nbsp;|&nbsp; 
            EXA: <span class="{'tag-bullish' if 'LIVE' in exa_status else 'tag-demo'}">{exa_status}</span> &nbsp;|&nbsp;
            SYS: <span class="tag-bullish">OPERATIONAL</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_kpi_card(title: str, value: str, subtext: str = "", trend: str = "neutral"):
    tag_class = f"tag-{trend.lower()}"
    st.markdown(f"""
    <div class="sentinel-card">
        <div style="color: #9ca3af; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">{title}</div>
        <div style="color: #ffffff; font-size: 1.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;">{value}</div>
        <div style="margin-top: 6px;"><span class="{tag_class}">{subtext}</span></div>
    </div>
    """, unsafe_allow_html=True)

def create_candlestick_chart(df: pd.DataFrame, ticker: str, support_levels: List[float] = None, resistance_levels: List[float] = None):
    """Render institutional TradingView-style candlestick chart."""
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=pd.to_datetime(df['date']),
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price',
        increasing_line_color='#00e676',
        decreasing_line_color='#ff3d57'
    ))

    # Support Levels
    if support_levels:
        for s in support_levels:
            fig.add_hline(y=s, line_dash="dash", line_color="#00e676", annotation_text=f"Support {s:.2f}", annotation_position="bottom right")

    # Resistance Levels
    if resistance_levels:
        for r in resistance_levels:
            fig.add_hline(y=r, line_dash="dash", line_color="#ff3d57", annotation_text=f"Resistance {r:.2f}", annotation_position="top right")

    fig.update_layout(
        title=f"<b>{ticker}</b> — Price Action & Technical Levels",
        template="plotly_dark",
        plot_bgcolor="#0a0e17",
        paper_bgcolor="#141d2e",
        xaxis_rangeslider_visible=False,
        margin=dict(l=30, r=30, t=40, b=30),
        height=450,
        font=dict(family="JetBrains Mono, sans-serif")
    )
    return fig

def create_sentiment_gauge(score: float, label: str):
    """Gauge showing sentiment from -1.0 (Bearish) to +1.0 (Bullish)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': f"Sentiment: {label}", 'font': {'size': 16, 'color': '#ffffff'}},
        gauge={
            'axis': {'range': [-1, 1], 'tickwidth': 1, 'tickcolor': "#9ca3af"},
            'bar': {'color': "#00b0ff"},
            'steps': [
                {'range': [-1, -0.15], 'color': "rgba(255, 61, 87, 0.4)"},
                {'range': [-0.15, 0.15], 'color': "rgba(107, 114, 128, 0.4)"},
                {'range': [0.15, 1], 'color': "rgba(0, 230, 118, 0.4)"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 3},
                'thickness': 0.8,
                'value': score
            }
        }
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#141d2e",
        font=dict(family="JetBrains Mono, sans-serif"),
        height=240,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    return fig

def create_actual_vs_predicted_chart(dates: List, actuals: List[float], predictions: List[float], title: str = "Actual vs Predicted Price"):
    """Evaluate prediction tracking over historical samples."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=actuals, mode='lines+markers', name='Actual', line=dict(color='#00b0ff', width=2)))
    fig.add_trace(go.Scatter(x=dates, y=predictions, mode='lines+markers', name='Predicted', line=dict(color='#ffd600', width=2, dash='dot')))
    
    fig.update_layout(
        title=title,
        template="plotly_dark",
        plot_bgcolor="#0a0e17",
        paper_bgcolor="#141d2e",
        height=380,
        margin=dict(l=30, r=30, t=40, b=30),
        font=dict(family="JetBrains Mono, sans-serif")
    )
    return fig
