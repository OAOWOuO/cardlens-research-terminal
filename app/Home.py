"""
CardLens Research Terminal — Home / Control Panel
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="CardLens Research Terminal",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 CardLens")
    st.caption("MGMT690 · Project 2 · Mastercard Case")
    st.divider()

    ticker = st.text_input("Ticker", value=os.environ.get("DEFAULT_TICKER", "MA"), max_chars=10)
    st.session_state["ticker"] = ticker.upper().strip()

    horizon = st.selectbox("Horizon", ["1W", "1M", "3M", "6M"], index=2)
    st.session_state["horizon"] = horizon

    risk_profile = st.selectbox(
        "Risk Profile",
        ["Conservative", "Balanced", "Aggressive"],
        index=1,
    )
    st.session_state["risk_profile"] = risk_profile

    st.divider()

    if st.button("🔄 Rebuild Document Index", use_container_width=True):
        with st.spinner("Ingesting documents…"):
            from src.ingest import ingest_all
            n_chunks = ingest_all()
        with st.spinner("Building embeddings…"):
            from src.embeddings import build_index
            n_emb = build_index()
        if n_emb == 0 and n_chunks == 0:
            st.warning("No documents found in data/raw/. Add PDF/TXT/MD files and try again.")
        else:
            st.success(f"Indexed {n_chunks} chunks, built {n_emb} embeddings.")

    if st.button("📊 Run Full Report", use_container_width=True):
        st.info("Navigate to each tab to view the full analysis.")

    st.divider()
    st.caption("**Risk Profile Guide**")
    st.markdown(
        """
- **Conservative**: Higher margin-of-safety threshold (≥20%), smaller position sizing suggestion, emphasis on downside risks.
- **Balanced**: Standard thresholds (≥10% margin of safety), moderate sizing.
- **Aggressive**: Lower threshold (≥5%), larger sizing, emphasis on catalysts.
        """,
        unsafe_allow_html=False,
    )

# ── Main content ──────────────────────────────────────────────────────────────
st.title("🔍 CardLens Research Terminal")
st.subheader("MGMT690 Project 2 · Mastercard (MA) Equity Research")

st.markdown(
    """
Welcome to **CardLens Research Terminal** — a case-grounded intelligent equity research workbench.

Use the **sidebar** to configure your ticker, analysis horizon, and risk profile, then navigate the pages:

| Page | What it does |
|------|-------------|
| **Q&A Chat** | Ask questions answered from your case documents (RAG, cited) |
| **Fundamentals** | Revenue, margins, quality checklist from market data |
| **Valuation** | DCF-lite + multiples, margin of safety |
| **Technicals** | Price chart, SMA 50/200, RSI, MACD, trend signal |
| **News** | Latest headlines for the ticker |
| **Sources** | Document library — view, reindex |
| **Recommendation** | Final Buy/Hold/Avoid + horizon outlook |
    """
)

st.info(
    "**Getting started**: Drop your Mastercard case materials (PDF, TXT, or MD) into `data/raw/`, "
    "then click **Rebuild Document Index** in the sidebar before using Q&A Chat.",
    icon="💡",
)

# Show index status
from pathlib import Path as _P

index_file = _P(__file__).parent.parent / "data" / "index" / "embeddings.npz"
raw_dir = _P(__file__).parent.parent / "data" / "raw"
raw_files = [f for f in raw_dir.iterdir() if f.suffix.lower() in {".pdf", ".txt", ".md"}] if raw_dir.exists() else []

col1, col2, col3 = st.columns(3)
col1.metric("Documents in data/raw", len(raw_files))
col2.metric("Index built", "Yes" if index_file.exists() else "No")
col3.metric("Active ticker", st.session_state.get("ticker", "MA"))
