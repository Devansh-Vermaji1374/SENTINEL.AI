"""SENTINEL AI - UI Table Helper with Bulletproof Native HTML / Arrow Fallback."""
import streamlit as st
import pandas as pd
from typing import Any

def render_styled_table(df: pd.DataFrame, use_container_width: bool = True):
    """Render a financial dataframe.
    Uses st.dataframe if PyArrow is functional; seamlessly falls back
    to a dark Bloomberg-styled native HTML table if PyArrow encounters OS DLL block.
    """
    if df is None or df.empty:
        st.info("No records to display.")
        return

    try:
        # Try standard Streamlit dataframe
        st.dataframe(df, width="stretch" if use_container_width else "content")
    except Exception:
        # High-elegance Bloomberg Terminal HTML table fallback
        html = df.to_html(classes="bloomberg-table", index=False, escape=False)
        styled_html = f"""
        <style>
            .bloomberg-table {{
                width: 100%;
                border-collapse: collapse;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                background-color: #141d2e;
                color: #e5e7eb;
                margin-top: 10px;
                margin-bottom: 15px;
                border: 1px solid #1f2d42;
            }}
            .bloomberg-table th {{
                background-color: #0d1522;
                color: #9ca3af;
                text-align: left;
                padding: 10px 12px;
                border-bottom: 2px solid #00b0ff;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .bloomberg-table td {{
                padding: 8px 12px;
                border-bottom: 1px solid #1f2d42;
            }}
            .bloomberg-table tr:hover {{
                background-color: #1a263d;
            }}
        </style>
        <div style="overflow-x: auto;">
            {html}
        </div>
        """
        st.markdown(styled_html, unsafe_allow_html=True)
