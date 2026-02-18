"""
CardLens Research Terminal — Analysis Left · Live Chat Right
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import streamlit as st
import yfinance as yf

# Streamlit Cloud secrets (takes priority over .env)
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

# ── CSS: sticky right panel + chat input pinned bottom-right ──────────────────
st.markdown(
    """
<style>
/* Sticky right chat column */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {
    position: sticky;
    top: 3rem;
    height: calc(100vh - 4rem);
    overflow-y: auto;
    border-left: 1px solid #1f2937;
    padding-left: 1.5rem !important;
}

/* Pin chat input to bottom-right */
div[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    right: 0 !important;
    width: 41% !important;
    z-index: 9999 !important;
    background: #0e1117 !important;
    border-top: 1px solid #1f2937 !important;
    padding: 0.6rem 1rem !important;
}

/* Chip buttons */
div[data-testid="column"] button {
    border-radius: 16px !important;
    font-size: 0.72rem !important;
    border: 1px solid #374151 !important;
    background: #111827 !important;
    color: #9ca3af !important;
    white-space: normal !important;
    text-align: left !important;
    line-height: 1.3 !important;
}
div[data-testid="column"] button:hover {
    border-color: #6b7280 !important;
    color: #e5e7eb !important;
    background: #1f2937 !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #111827;
    border-radius: 8px;
    padding: 8px 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _get_data():
    info = yf.Ticker("MA").info
    hist = yf.Ticker("MA").history(period="2y")
    return info, hist


try:
    info, hist = _get_data()
except Exception:
    info, hist = {}, None

price = info.get("currentPrice") or 0
mktcap = (info.get("marketCap") or 0) / 1e9
pe = info.get("trailingPE") or 0
fpe = info.get("forwardPE") or 0
margin = (info.get("profitMargins") or 0) * 100
op_m = (info.get("operatingMargins") or 0) * 100
roe = (info.get("returnOnEquity") or 0) * 100
fcf_b = (info.get("freeCashflow") or 0) / 1e9
revenue = (info.get("totalRevenue") or 0) / 1e9
beta = info.get("beta") or 0
ytd = 0.0
if hist is not None and not hist.empty:
    ytd = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100

# Quick DCF
_shares = info.get("sharesOutstanding") or 1
_nd = ((info.get("totalDebt") or 0) - (info.get("totalCash") or 0)) / 1e9
_fcf = max((info.get("freeCashflow") or 0) / 1e9, 11.0)
_pv, _f = 0.0, _fcf
for _yr in range(1, 6):
    _f *= 1.12
    _pv += _f / 1.09**_yr
_pv += _f * 1.03 / 0.06 / 1.09**5
iv = (_pv - _nd) * 1e9 / _shares if _shares > 0 else 0
mos = (iv - price) / iv * 100 if iv > 0 and price > 0 else 0

# Technical signal
tech_score = 0
rsi_val = float("nan")
if hist is not None and not hist.empty:
    _close = hist["Close"]
    _last = _close.iloc[-1]
    _sma50 = _close.rolling(50).mean().iloc[-1]
    _sma200 = _close.rolling(200).mean().iloc[-1]
    _delta = _close.diff()
    _gain = _delta.clip(lower=0).rolling(14).mean()
    _loss = (-_delta.clip(upper=0)).rolling(14).mean()
    rsi_val = (100 - 100 / (1 + _gain / _loss.replace(0, float("nan")))).iloc[-1]
    if not math.isnan(_sma50):
        tech_score += 1 if _last > _sma50 else -1
    if not math.isnan(_sma200):
        tech_score += 1 if _last > _sma200 else -1
    if not math.isnan(rsi_val):
        if 40 < rsi_val < 65:
            tech_score += 1
        elif rsi_val >= 70:
            tech_score -= 1

tech_label = "🟢 Bullish" if tech_score >= 2 else ("🔴 Bearish" if tech_score <= -2 else "🟡 Neutral")

# ── Chat helpers ──────────────────────────────────────────────────────────────
CHIPS = [
    "What is Agent Suite?",
    "Cloudflare partnership details",
    "Is MA fairly valued?",
    "Main investment risks?",
    "Buy / Hold / Avoid call?",
    "Agent Suite revenue model",
    "MA vs Visa — which is better?",
    "10-K revenue growth outlook",
]


def _system() -> str:
    return (
        "You are an expert financial analyst for Mastercard (NYSE: MA) — MBA course MGMT690.\n\n"
        f"LIVE DATA: Price ${price:.2f} | Mkt Cap ${mktcap:.0f}B | P/E {pe:.1f}x (fwd {fpe:.1f}x) | "
        f"Revenue ${revenue:.1f}B | Net Margin {margin:.1f}% | ROE {roe:.1f}% | FCF ${fcf_b:.1f}B | "
        f"Beta {beta:.2f} | 1Y {ytd:+.1f}% | DCF IV ${iv:.0f} | MoS {mos:+.1f}%\n\n"
        "Case: Agent Suite (Jan 2026) — AI agentic payments infra. "
        "Cloudflare (Feb 2026) — cyber-defense for agentic commerce.\n"
        "Docs: Agent Suite PR, Cloudflare PRs, Mastercard 10-K 2024.\n\n"
        "Be direct, analytical, cite specific numbers. Cite docs when relevant. Use bullet points."
    )


def _rag(q: str) -> str:
    try:
        from src.retrieval import retrieve

        chunks = retrieve(q, top_k=4)
        if not chunks:
            return ""
        return "\n\nCase doc excerpts:\n" + "\n".join(f"[{c['citation']}]: {c['text'][:400]}" for c in chunks)
    except Exception:
        return ""


def _stream(api_key: str, history: list[dict], question: str):
    from openai import OpenAI

    msgs = [{"role": "system", "content": _system() + _rag(question)}] + history
    client = OpenAI(api_key=api_key)
    with client.chat.completions.create(
        model="gpt-4o-mini", messages=msgs, stream=True, temperature=0.3, max_tokens=1200
    ) as s:
        for chunk in s:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ── Handle chat input BEFORE rendering columns ────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat input is called here; renders pinned bottom-right via CSS
prompt = st.chat_input("Ask about Mastercard, Agent Suite, Cloudflare, valuation…")
if not prompt and "_pending" in st.session_state:
    prompt = st.session_state.pop("_pending")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

# ── COLUMNS ───────────────────────────────────────────────────────────────────
left, right = st.columns([6, 4])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEFT — Analysis & Reports
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with left:
    st.title("🔍 CardLens — Mastercard (MA)")
    st.caption("MGMT690 Project 2 · Equity Research Terminal · Agent Suite + Cloudflare Case")

    # Live metrics
    st.subheader("📊 Live Market Snapshot")
    r1c1, r1c2, r1c3 = st.columns(3)
    r1c1.metric("Price", f"${price:.2f}", f"{ytd:+.1f}% 1Y")
    r1c2.metric("Market Cap", f"${mktcap:.0f}B")
    r1c3.metric("Beta", f"{beta:.2f}")
    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("P/E (Trailing)", f"{pe:.1f}x")
    r2c2.metric("Forward P/E", f"{fpe:.1f}x")
    r2c3.metric("Free Cash Flow", f"${fcf_b:.1f}B")

    st.divider()

    # Case thesis
    st.subheader("📄 Case Thesis")
    ca, cb = st.columns(2)
    with ca:
        st.markdown("**🤖 Agent Suite (Jan 2026)**")
        st.markdown(
            "- First payment infra built for AI agents\n"
            "- Token-based auth — no card credentials\n"
            "- New monetization on existing MA network\n"
            "- MA as gatekeeper of the agentic economy\n"
            "- Targets enterprise AI workflow adoption"
        )
    with cb:
        st.markdown("**🔒 Cloudflare Partnership (Feb 2026)**")
        st.markdown(
            "- Cyber-defense layer for agentic payments\n"
            "- Cloudflare AI validates agent authenticity\n"
            "- Extends MA trust model to AI transactions\n"
            "- Reduces fraud risk in agentic commerce\n"
            "- Enterprise-grade security moat signal"
        )

    st.divider()

    # Fundamentals
    st.subheader("📈 Fundamentals at a Glance")
    fa, fb, fc, fd = st.columns(4)
    fa.metric("Op Margin", f"{op_m:.1f}%", "✅ >30%" if op_m > 30 else "⚠ <30%", delta_color="off")
    fb.metric("Net Margin", f"{margin:.1f}%")
    fc.metric("ROE", f"{roe:.1f}%", "✅ >30%" if roe > 30 else "", delta_color="off")
    fd.metric("Revenue (TTM)", f"${revenue:.1f}B")

    st.divider()

    # Valuation & signal
    st.subheader("💰 Valuation & Technical Signal")
    va, vb, vc = st.columns(3)
    va.metric("DCF Intrinsic Value", f"${iv:.0f}")
    vb.metric(
        "Margin of Safety",
        f"{mos:+.1f}%",
        "Undervalued" if mos > 0 else "Overvalued",
        delta_color="normal" if mos > 0 else "inverse",
    )
    vc.metric("Technical Trend", tech_label)

    st.divider()

    # Nav
    st.subheader("🗂 Detailed Analysis Pages")
    st.markdown(
        "Open the **sidebar ›** to navigate:\n\n"
        "| Page | What's inside |\n"
        "|------|---------------|\n"
        "| 📄 Case Overview | Full thesis, timeline, key questions |\n"
        "| 📊 Fundamentals | Income statement, quality checklist |\n"
        "| 📈 Technicals | Chart, SMA 20/50/200, RSI, MACD, drawdown |\n"
        "| 💰 Valuation | DCF sliders, sensitivity table, peer comps |\n"
        "| 📰 News | Pinned case PRs + live newsroom RSS |\n"
        "| ⭐ Decision | Signal scoring + horizon return ranges |"
    )
    st.caption("Data: Yahoo Finance · Educational only · Not investment advice.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RIGHT — Live Chat (sticky)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with right:
    st.subheader("💬 Live Research Chat")
    st.caption("GPT-4o-mini · live data · case docs · streams in real time")

    # Quick question chips (2 per row)
    chip_c1, chip_c2 = st.columns(2)
    for i, q in enumerate(CHIPS):
        if (chip_c1 if i % 2 == 0 else chip_c2).button(q, key=f"chip_{i}", use_container_width=True):
            st.session_state["_pending"] = q

    st.divider()

    # Determine if there's a new user message awaiting AI response
    msgs = st.session_state.messages
    has_pending = bool(msgs) and msgs[-1]["role"] == "user"

    # Display all confirmed messages
    confirmed = msgs if not has_pending else msgs[:-1]
    for msg in confirmed:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # If pending user message, show it then stream AI response
    if has_pending:
        _api_key = os.environ.get("OPENAI_API_KEY", "")
        with st.chat_message("user"):
            st.markdown(msgs[-1]["content"])
        with st.chat_message("assistant"):
            if not _api_key:
                answer = (
                    "⚠️ OpenAI API key not found. "
                    "Go to Streamlit Cloud → App settings → Secrets and add:\n\n"
                    '`OPENAI_API_KEY = "sk-proj-..."`'
                )
                st.warning(answer)
            else:
                try:
                    answer = st.write_stream(_stream(_api_key, msgs[:-1], msgs[-1]["content"]))
                except Exception as e:
                    answer = f"❌ {e}"
                    st.error(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    # Clear button
    if msgs:
        if st.button("🗑 Clear chat", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()
