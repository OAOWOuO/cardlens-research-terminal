"""
CardLens Research Terminal — Live AI Research Chat
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import yfinance as yf

# ── Load API key (priority: session_state → st.secrets → .env) ────────────────
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
    initial_sidebar_state="expanded",
)

# ── Custom CSS — live chat look ────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Chat message bubbles */
[data-testid="stChatMessage"] {
    border-radius: 12px;
    padding: 6px 4px;
    margin-bottom: 4px;
}
/* User bubble */
[data-testid="stChatMessage"][data-testid*="user"] {
    background: #1e3a5f;
}
/* Chip buttons */
div[data-testid="column"] button {
    border-radius: 20px !important;
    font-size: 0.75rem !important;
    padding: 4px 10px !important;
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
/* Metric labels */
[data-testid="stMetric"] {
    background: #111827;
    border-radius: 8px;
    padding: 8px 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar — API key + nav ────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 CardLens")
    st.caption("MGMT690 · Project 2 · Mastercard (MA)")
    st.divider()

    st.markdown("**OpenAI API Key**")
    entered_key = st.text_input(
        "Paste your key here",
        type="password",
        value=st.session_state.get("_oai_key", ""),
        placeholder="sk-proj-...",
        label_visibility="collapsed",
    )
    if entered_key:
        st.session_state["_oai_key"] = entered_key
        os.environ["OPENAI_API_KEY"] = entered_key

    # Resolve key
    _api_key = st.session_state.get("_oai_key") or os.environ.get("OPENAI_API_KEY", "")

    if _api_key and len(_api_key) > 10:
        st.success("API key active ✅", icon="🔑")
    else:
        st.warning("Paste your OpenAI API key above to enable AI chat.", icon="⚠️")

    st.divider()
    st.markdown("**Analysis Pages**")
    st.markdown(
        "- 📄 Case Overview\n"
        "- 📊 Fundamentals\n"
        "- 📈 Technicals\n"
        "- 💰 Valuation\n"
        "- 📰 News\n"
        "- 💬 AI Chat (extended)\n"
        "- ⭐ Decision"
    )
    st.caption("Use the page selector at the top of the sidebar ↑")


# ── Live MA metrics bar ────────────────────────────────────────────────────────
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


st.title("🔍 CardLens — Mastercard Research Terminal")
st.caption(
    "MGMT690 Project 2 · Powered by GPT-4o-mini + live market data + case documents (Agent Suite · Cloudflare · 10-K)"
)

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
    st.info("Live market data loading…")

st.divider()

# ── Live Chat ─────────────────────────────────────────────────────────────────
st.subheader("💬 Live AI Research Chat")
st.caption(
    "Ask anything about Mastercard — financials, strategy, valuation, Agent Suite, Cloudflare, risks. "
    "Responses stream live."
)

# Quick question chips
CHIPS = [
    "What is Mastercard Agent Suite?",
    "Explain the Cloudflare partnership",
    "Is Mastercard fairly valued?",
    "What are the main investment risks?",
    "Give me a Buy / Hold / Avoid call",
    "How does Agent Suite generate revenue?",
    "MA vs Visa — which is better?",
    "What does the 10-K say about growth?",
]

chip_cols = st.columns(4)
for i, q in enumerate(CHIPS):
    if chip_cols[i % 4].button(q, key=f"chip_{i}", use_container_width=True):
        st.session_state["_pending"] = q


# ── Streaming chat function ────────────────────────────────────────────────────
def _build_system() -> str:
    try:
        s = _snap()
        fin = (
            f"LIVE MA DATA: Price ${s['price']:.2f} | Mkt Cap ${s['mktcap']:.0f}B | "
            f"P/E {s['pe']:.1f}x (fwd {s['fpe']:.1f}x) | Revenue ${s['revenue']:.1f}B | "
            f"Net Margin {s['margin']:.1f}% | ROE {s['roe']:.1f}% | FCF ${s['fcf']:.1f}B | "
            f"Beta {s['beta']:.2f} | 1Y return {s['ytd']:+.1f}%"
        )
    except Exception:
        fin = "Live market data unavailable."

    doc_hint = ""
    try:
        # We'll inject RAG per-question; just note docs exist
        doc_hint = "You have access to: Mastercard Agent Suite PR (Jan 2026), Cloudflare partnership PRs (2025/2026), Mastercard 10-K (2024)."
    except Exception:
        pass

    return f"""You are an expert financial analyst and live research assistant for Mastercard (NYSE: MA) for an MBA equity research course (MGMT690).

{fin}

Case context: {doc_hint}

Your role:
- Answer financial, strategic, and valuation questions about Mastercard with depth and precision.
- Use the live financial data above in every relevant answer.
- Cite case documents when relevant (Agent Suite PR, Cloudflare PR, 10-K).
- Be analytical, direct, and insightful — like a top-tier equity research report.
- For valuation questions: provide DCF logic, peer multiples context, and a clear view.
- For strategy: tie Agent Suite and Cloudflare to revenue/moat implications.
- Format responses with bullet points or short paragraphs for clarity.
"""


def _rag_context(question: str) -> str:
    """Get relevant case document excerpts for the question."""
    try:
        from src.retrieval import retrieve

        chunks = retrieve(question, top_k=4)
        if not chunks:
            return ""
        return "\n\nRelevant case document excerpts:\n" + "\n".join(
            f"[{c['citation']}]: {c['text'][:400]}" for c in chunks
        )
    except Exception:
        return ""


def _stream(api_key: str, chat_history: list[dict], question: str):
    """Yield streaming tokens from OpenAI."""
    from openai import OpenAI

    rag = _rag_context(question)
    system = _build_system()
    if rag:
        system += rag

    messages = [{"role": "system", "content": system}] + chat_history

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


# ── Chat history display ───────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Handle input ──────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask about Mastercard, Agent Suite, Cloudflare, valuation, risks…")
if not prompt and "_pending" in st.session_state:
    prompt = st.session_state.pop("_pending")

if prompt:
    api_key = st.session_state.get("_oai_key") or os.environ.get("OPENAI_API_KEY", "")

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key or len(api_key) < 10:
            answer = "⚠️ Please paste your OpenAI API key in the sidebar to enable the live chat."
            st.markdown(answer)
        else:
            try:
                answer = st.write_stream(_stream(api_key, st.session_state.messages[:-1], prompt))
            except Exception as e:
                answer = f"❌ Error: {e}"
                st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

# ── Controls ──────────────────────────────────────────────────────────────────
if st.session_state.messages:
    if st.button("🗑 Clear conversation"):
        st.session_state.messages = []
        st.rerun()

st.divider()
st.caption(
    "Live data from Yahoo Finance · Case docs: Agent Suite PR, Cloudflare PR, MA 10-K · "
    "Educational only — not investment advice."
)
