"""
CardLens Research Terminal — Home
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

# Load secrets from Streamlit Cloud if available (overrides .env)
try:
    for _key in ["OPENAI_API_KEY", "DEFAULT_TICKER"]:
        if _key in st.secrets:
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass

st.set_page_config(
    page_title="CardLens Research Terminal",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.title("🔍 CardLens")
    st.caption("MGMT690 · Project 2 · Mastercard Case")
    st.divider()
    st.markdown(
        "Navigate the pages using the menu above.\n\n**💬 AI Research Chat** is always ready — no setup needed."
    )

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🔍 CardLens Research Terminal")
st.subheader("MGMT690 Project 2 · Mastercard (MA) Equity Research")

st.markdown(
    """
Welcome to **CardLens Research Terminal** — a case-grounded intelligent equity research workbench
focused on **Mastercard (NYSE: MA)** and two landmark case events:

> 🤖 **Agent Suite** (Jan 2026) — Mastercard's infrastructure for AI-native agentic commerce
> 🔒 **Cloudflare Partnership** (Feb 2026) — Comprehensive cyber-defense for agentic payments
"""
)

st.divider()

st.subheader("📋 Research Pages")
st.markdown(
    """
| # | Page | What it covers |
|---|------|----------------|
| 1 | **📄 Case Overview** | Agent Suite + Cloudflare thesis, event timeline, key analytical questions |
| 2 | **📊 Fundamentals** | Revenue, margins, ROE, FCF, quality checklist — cited to 10-K |
| 3 | **📈 Technicals** | Candlestick chart, SMA 20/50/200, RSI, MACD, rolling volatility, max drawdown |
| 4 | **💰 Valuation** | DCF-lite with sliders, WACC × TG sensitivity table, peer comps (V, AXP, PYPL, FIS) |
| 5 | **📰 News** | Pinned case press releases + live Mastercard newsroom RSS + Google News |
| 6 | **💬 AI Research Chat** | Ask anything — grounded in Agent Suite PR, Cloudflare PR, and 10-K with citations |
| 7 | **⭐ Decision** | Buy / Hold / Avoid signal scoring + data-derived horizon return ranges |
"""
)

st.divider()

# ── Status ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
index_file = PROJECT_ROOT / "data" / "index" / "embeddings.npz"
raw_dir = PROJECT_ROOT / "data" / "raw"
raw_files = [f for f in raw_dir.iterdir() if f.suffix.lower() in {".pdf", ".txt", ".md"}] if raw_dir.exists() else []

s1, s2, s3 = st.columns(3)
s1.metric("Case Documents", len(raw_files))
s2.metric("AI Chat Index", "✅ Ready" if index_file.exists() else "❌ Missing")
s3.metric("Ticker", "MA · Mastercard")
