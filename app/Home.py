"""
CardLens Research Terminal — Live AI Research Chat
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env from project root (works regardless of where streamlit is launched from)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import streamlit as st
import yfinance as yf

# Load Streamlit Cloud secrets if available (overrides .env on cloud)
try:
    for _k in ["OPENAI_API_KEY"]:
        if _k in st.secrets:
            os.environ[_k] = st.secrets[_k]
except Exception:
    pass

st.set_page_config(
    page_title="CardLens · Mastercard Research",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
div[data-testid="column"] button {
    border-radius: 20px !important;
    font-size: 0.75rem !important;
    border: 1px solid #444 !important;
    background: #1a1a2e !important;
    color: #ccc !important;
    white-space: normal !important;
    text-align: left !important;
}
div[data-testid="column"] button:hover {
    background: #16213e !important;
    border-color: #888 !important;
    color: #fff !important;
}
[data-testid="stMetric"] {
    background: #111827;
    border-radius: 8px;
    padding: 8px 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Live MA metrics (cached 5 min) ────────────────────────────────────────────
@st.cache_data(ttl=300)
def _snap() -> dict:
    info = yf.Ticker("MA").info
    hist = yf.Ticker("MA").history(period="1y")
    ytd = 0.0
    if not hist.empty:
        ytd = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100
    return {
        "price": info.get("currentPrice") or 0,
        "pe": info.get("trailingPE") or 0,
        "fpe": info.get("forwardPE") or 0,
        "mktcap": (info.get("marketCap") or 0) / 1e9,
        "margin": (info.get("profitMargins") or 0) * 100,
        "roe": (info.get("returnOnEquity") or 0) * 100,
        "fcf": (info.get("freeCashflow") or 0) / 1e9,
        "revenue": (info.get("totalRevenue") or 0) / 1e9,
        "beta": info.get("beta") or 0,
        "ytd": ytd,
    }


# ── Page header ───────────────────────────────────────────────────────────────
st.title("🔍 CardLens — Mastercard Research Terminal")
st.caption("MGMT690 Project 2 · GPT-4o-mini + live market data + case documents (Agent Suite · Cloudflare · 10-K)")

try:
    snap = _snap()
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("MA Price", f"${snap['price']:.2f}", f"{snap['ytd']:+.1f}% 1Y")
    m2.metric("Mkt Cap", f"${snap['mktcap']:.0f}B")
    m3.metric("P/E (Trail.)", f"{snap['pe']:.1f}x")
    m4.metric("Net Margin", f"{snap['margin']:.1f}%")
    m5.metric("ROE", f"{snap['roe']:.1f}%")
    m6.metric("FCF", f"${snap['fcf']:.1f}B")
except Exception:
    st.info("Loading live market data…")

st.divider()

# ── Chat ──────────────────────────────────────────────────────────────────────
st.subheader("💬 Live AI Research Chat")
st.caption(
    "Ask anything about Mastercard — financials, valuation, Agent Suite, "
    "Cloudflare partnership, risks, trade decision. Responses stream live."
)

CHIPS = [
    "What is Mastercard Agent Suite?",
    "Explain the Cloudflare partnership",
    "Is Mastercard fairly valued?",
    "What are the main investment risks?",
    "Give me a Buy / Hold / Avoid recommendation",
    "How does Agent Suite generate new revenue?",
    "MA vs Visa — which is the better investment?",
    "What does the 10-K say about Mastercard's growth?",
]

chip_cols = st.columns(4)
for i, q in enumerate(CHIPS):
    if chip_cols[i % 4].button(q, key=f"chip_{i}", use_container_width=True):
        st.session_state["_pending"] = q


def _build_system() -> str:
    try:
        s = _snap()
        fin = (
            f"LIVE MA DATA — Price ${s['price']:.2f} | Mkt Cap ${s['mktcap']:.0f}B | "
            f"P/E {s['pe']:.1f}x (fwd {s['fpe']:.1f}x) | Revenue ${s['revenue']:.1f}B TTM | "
            f"Net Margin {s['margin']:.1f}% | ROE {s['roe']:.1f}% | "
            f"FCF ${s['fcf']:.1f}B | Beta {s['beta']:.2f} | 1Y return {s['ytd']:+.1f}%"
        )
    except Exception:
        fin = "Live market data unavailable."

    return f"""You are an expert financial analyst and live research assistant for Mastercard (NYSE: MA) for MBA course MGMT690.

{fin}

You have access to case documents: Mastercard Agent Suite PR (Jan 2026), Cloudflare partnership PRs (2025/2026), Mastercard 10-K (2024).

Instructions:
- Answer analytically and directly. Use specific numbers from the live data above.
- Cite case documents when drawing on them (e.g. "Per the Agent Suite PR...").
- For valuation: give DCF logic, peer multiples context, and a clear view.
- For strategy: tie Agent Suite and Cloudflare to revenue and moat implications.
- Be concise but insightful — like a top-tier equity research report.
- Format with bullet points or short paragraphs for clarity.
"""


def _rag_context(question: str) -> str:
    try:
        from src.retrieval import retrieve

        chunks = retrieve(question, top_k=4)
        if not chunks:
            return ""
        return "\n\nCase document excerpts:\n" + "\n".join(f"[{c['citation']}]: {c['text'][:400]}" for c in chunks)
    except Exception:
        return ""


def _stream(api_key: str, history: list[dict], question: str):
    from openai import OpenAI

    system = _build_system() + _rag_context(question)
    messages = [{"role": "system", "content": system}] + history
    client = OpenAI(api_key=api_key)
    with client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
        temperature=0.3,
        max_tokens=1200,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask about Mastercard, Agent Suite, Cloudflare, valuation, risks…")
if not prompt and "_pending" in st.session_state:
    prompt = st.session_state.pop("_pending")

if prompt:
    _api_key = os.environ.get("OPENAI_API_KEY", "")

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not _api_key:
            answer = (
                "⚠️ OpenAI API key not found. "
                "The app admin needs to add it to Streamlit Cloud secrets or the `.env` file."
            )
            st.warning(answer)
        else:
            try:
                answer = st.write_stream(_stream(_api_key, st.session_state.messages[:-1], prompt))
            except Exception as e:
                answer = f"❌ {e}"
                st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

if st.session_state.messages:
    if st.button("🗑 Clear conversation"):
        st.session_state.messages = []
        st.rerun()

st.divider()
st.caption(
    "Live data: Yahoo Finance · Case docs: Agent Suite PR, Cloudflare PRs, MA 10-K · "
    "Educational only — not investment advice."
)
