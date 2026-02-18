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

# Load secrets from Streamlit Cloud secrets if available (overrides .env)
try:
    for _key in ["OPENAI_API_KEY", "DEFAULT_TICKER"]:
        if _key in st.secrets:
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass  # No secrets file — fall back to .env

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

    st.markdown("**🌐 Fetch & Index Documents**")
    st.caption("Downloads case press releases + 10-K, then builds the AI search index.")

    if st.button("🌐 Fetch & Index Documents", use_container_width=True):
        with st.spinner("Fetching case documents from the web…"):
            try:
                from src.fetch_docs import fetch_all

                results = fetch_all()
                ok = [r for r in results if r["status"] == "ok"]
                fail = [r for r in results if r["status"] != "ok"]
                if ok:
                    st.success(f"Fetched {len(ok)} document(s).")
                if fail:
                    for r in fail:
                        st.warning(f"⚠ {r['filename']}: {r.get('error', 'failed')}")
            except Exception as e:
                st.error(f"Fetch error: {e}")

        with st.spinner("Ingesting & chunking documents…"):
            try:
                from src.ingest import ingest_all

                n_chunks = ingest_all()
            except Exception as e:
                st.error(f"Ingest error: {e}")
                n_chunks = 0

        with st.spinner("Building embeddings index…"):
            try:
                from src.embeddings import build_index

                n_emb = build_index()
            except Exception as e:
                st.error(f"Embeddings error: {e}")
                n_emb = 0

        if n_emb == 0 and n_chunks == 0:
            st.warning("No documents indexed. Check fetch errors above.")
        else:
            st.success(f"✅ Indexed {n_chunks} chunks · {n_emb} embeddings built. AI Chat is ready!")

    st.divider()

    st.markdown("**📊 Settings**")
    horizon = st.selectbox("Analysis Horizon", ["1W", "1M", "3M", "6M"], index=2)
    st.session_state["horizon"] = horizon

    st.divider()
    st.caption(
        "**About**: CardLens is a case-grounded equity research terminal built for "
        "MGMT690 Project 2. All analysis is educational — not investment advice."
    )

# ── Main content ──────────────────────────────────────────────────────────────
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

# ── Getting started ────────────────────────────────────────────────────────────
st.subheader("🚀 Getting Started")

col_gs1, col_gs2 = st.columns([1, 2])
with col_gs1:
    st.markdown(
        """
**Two steps to unlock AI Chat:**

1. Click **🌐 Fetch & Index Documents** in the sidebar
2. Navigate to **💬 AI Research Chat** and ask anything

That's it — no manual file uploads needed.
        """
    )
with col_gs2:
    st.info(
        "The fetch step downloads four case documents directly from the web "
        "(Mastercard newsroom, Cloudflare press releases, SEC EDGAR 10-K) "
        "and builds a semantic search index. "
        "Requires an **OpenAI API key** in your environment or Streamlit secrets.",
        icon="💡",
    )

st.divider()

# ── Page map ──────────────────────────────────────────────────────────────────
st.subheader("📋 Research Pages")

st.markdown(
    """
| # | Page | What it covers |
|---|------|----------------|
| 1 | **📄 Case Overview** | Agent Suite + Cloudflare thesis, event timeline, key analytical questions |
| 2 | **📊 Fundamentals** | Revenue, margins, ROE, FCF, quality checklist — cited to 10-K |
| 3 | **📈 Technicals** | Candlestick chart, SMA 20/50/200, RSI, MACD, rolling volatility, max drawdown |
| 4 | **💰 Valuation** | DCF-lite with sliders, WACC × terminal-growth sensitivity table, peer comps |
| 5 | **📰 News** | Pinned case press releases + live Mastercard newsroom RSS + Google News |
| 6 | **💬 AI Research Chat** | Ask anything — answers grounded in case documents with citations |
| 7 | **⭐ Decision** | Buy / Hold / Avoid signal, data-derived horizon return ranges |
"""
)

st.divider()

# ── Index status dashboard ─────────────────────────────────────────────────────
st.subheader("📦 Document Index Status")

PROJECT_ROOT = Path(__file__).parent.parent
index_file = PROJECT_ROOT / "data" / "index" / "embeddings.npz"
raw_dir = PROJECT_ROOT / "data" / "raw"
raw_files = [f for f in raw_dir.iterdir() if f.suffix.lower() in {".pdf", ".txt", ".md"}] if raw_dir.exists() else []

s1, s2, s3 = st.columns(3)
s1.metric("Documents in data/raw", len(raw_files))
s2.metric("Search Index", "✅ Ready" if index_file.exists() else "❌ Not built")
s3.metric("Ticker", "MA · Mastercard")

if raw_files:
    with st.expander("View indexed documents"):
        for f in sorted(raw_files):
            size_kb = f.stat().st_size / 1024
            st.markdown(f"- `{f.name}` — {size_kb:.1f} KB")
else:
    st.caption("No documents yet — click **🌐 Fetch & Index Documents** in the sidebar.")
