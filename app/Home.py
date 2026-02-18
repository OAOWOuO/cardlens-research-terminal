"""
CardLens Research Terminal — AI Research Chat + Live Dashboard
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

# Load Streamlit Cloud secrets
try:
    for _key in ["OPENAI_API_KEY"]:
        if _key in st.secrets:
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass

st.set_page_config(
    page_title="CardLens · Mastercard Research",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── Live MA snapshot (cached 5 min) ───────────────────────────────────────────
@st.cache_data(ttl=300)
def _ma_snapshot() -> dict:
    info = yf.Ticker("MA").info
    hist = yf.Ticker("MA").history(period="1y")
    ytd_ret = 0.0
    if not hist.empty:
        first = hist["Close"].iloc[0]
        last = hist["Close"].iloc[-1]
        ytd_ret = (last - first) / first * 100
    return {
        "price": info.get("currentPrice") or info.get("regularMarketPrice") or 0,
        "pe": info.get("trailingPE") or 0,
        "mktcap": (info.get("marketCap") or 0) / 1e9,
        "margin": (info.get("profitMargins") or 0) * 100,
        "roe": (info.get("returnOnEquity") or 0) * 100,
        "fcf": (info.get("freeCashflow") or 0) / 1e9,
        "revenue": (info.get("totalRevenue") or 0) / 1e9,
        "ytd": ytd_ret,
        "beta": info.get("beta") or 0,
        "forward_pe": info.get("forwardPE") or 0,
    }


# ── AI chat function (RAG + live financials + full model knowledge) ────────────
def _chat(messages: list[dict]) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "⚠️ No OpenAI API key found. Add `OPENAI_API_KEY` to your Streamlit secrets or `.env` file."

    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    # Build financial context
    try:
        snap = _ma_snapshot()
        fin_ctx = f"""
LIVE MASTERCARD (MA) MARKET DATA (as of today):
• Price: ${snap["price"]:.2f}
• Market Cap: ${snap["mktcap"]:.0f}B
• Trailing P/E: {snap["pe"]:.1f}x  |  Forward P/E: {snap["forward_pe"]:.1f}x
• Revenue (TTM): ${snap["revenue"]:.1f}B
• Net Margin: {snap["margin"]:.1f}%
• ROE: {snap["roe"]:.1f}%
• Free Cash Flow: ${snap["fcf"]:.1f}B
• Beta: {snap["beta"]:.2f}
• 1-Year Return: {snap["ytd"]:+.1f}%
"""
    except Exception:
        fin_ctx = "Live financial data temporarily unavailable."

    # RAG context from case documents
    doc_ctx = ""
    citations = []
    try:
        from src.retrieval import retrieve

        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        chunks = retrieve(last_user, top_k=5)
        if chunks:
            doc_ctx = "\n".join(f"[{c['citation']}]\n{c['text']}" for c in chunks)
            citations = list({c["citation"] for c in chunks})
    except Exception:
        pass

    system = f"""You are an expert financial analyst and AI research assistant for Mastercard (NYSE: MA).
You are helping MBA students at MGMT690 analyze two landmark case events:
• Mastercard Agent Suite (Jan 2026) — AI-native agentic commerce infrastructure
• Cloudflare × Mastercard partnership (Feb 2026) — Comprehensive cyber-defense for agentic payments

You have access to:
1. LIVE FINANCIAL DATA: {fin_ctx}
2. CASE DOCUMENTS (excerpts below from Agent Suite PR, Cloudflare PR, Mastercard 10-K 2024)

CASE DOCUMENT EXCERPTS:
{doc_ctx if doc_ctx else "No relevant excerpts retrieved for this question."}

Instructions:
- Answer analytically and thoroughly. Use specific numbers from the financial data above.
- When drawing on case documents, cite them (e.g., "Per the Agent Suite press release...").
- You MAY use your own financial knowledge beyond the documents — this is for an MBA analysis.
- Be direct and insightful. Avoid vague answers.
- If asked about valuation, give a clear perspective with supporting data.
- Format with bullet points or short paragraphs where helpful.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.3,
        max_tokens=1200,
    )
    answer = response.choices[0].message.content.strip()

    if citations:
        answer += "\n\n*Sources: " + " · ".join(citations) + "*"

    return answer


# ── Page layout ───────────────────────────────────────────────────────────────
st.title("🔍 CardLens — Mastercard Research Terminal")
st.caption("MGMT690 Project 2 · AI-powered equity research · Agent Suite + Cloudflare case")

# Live metrics bar
try:
    snap = _ma_snapshot()
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("MA Price", f"${snap['price']:.2f}", f"{snap['ytd']:+.1f}% 1Y")
    m2.metric("Market Cap", f"${snap['mktcap']:.0f}B")
    m3.metric("P/E (Trailing)", f"{snap['pe']:.1f}x")
    m4.metric("Net Margin", f"{snap['margin']:.1f}%")
    m5.metric("ROE", f"{snap['roe']:.1f}%")
    m6.metric("FCF", f"${snap['fcf']:.1f}B")
except Exception:
    st.warning("Live market data unavailable — check your connection.", icon="⚠️")

st.divider()

# ── Chat interface ─────────────────────────────────────────────────────────────
st.subheader("💬 AI Research Assistant")
st.caption(
    "Ask anything — financials, valuation, Agent Suite strategy, Cloudflare partnership, risks, trade decision. "
    "The AI has live market data + case documents."
)

# Quick question chips
CHIPS = [
    "What is Mastercard Agent Suite and why does it matter?",
    "What are the key terms of the Cloudflare partnership?",
    "Is Mastercard fairly valued right now?",
    "What are the main risks to the investment thesis?",
    "Give me a Buy / Hold / Avoid recommendation with reasons.",
    "How does Agent Suite create a new revenue stream for Mastercard?",
    "What does the 10-K say about Mastercard's competitive moat?",
    "What is Mastercard's valuation vs Visa?",
]

chip_cols = st.columns(4)
for i, q in enumerate(CHIPS):
    if chip_cols[i % 4].button(q, key=f"chip_{i}", use_container_width=True):
        st.session_state["pending"] = q

# Init chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle input
prompt = st.chat_input("Ask about Mastercard, Agent Suite, Cloudflare, valuation, risks…")
if not prompt and "pending" in st.session_state:
    prompt = st.session_state.pop("pending")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing…"):
            answer = _chat(st.session_state.messages)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

if st.session_state.messages:
    if st.button("🗑 Clear chat", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

st.divider()
st.caption(
    "📄 Detailed analysis: use the sidebar → **Fundamentals · Technicals · Valuation · News · Decision**  |  "
    "Educational only — not investment advice."
)
