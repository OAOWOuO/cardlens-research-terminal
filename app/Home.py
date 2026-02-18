"""
CardLens Research Terminal — Chat Left (30%) · Analysis Right (70%)
Question input at top · Answer box below
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

st.markdown(
    """
<style>
/* Compact metric cards */
[data-testid="stMetric"] {
    background: #111827;
    border-radius: 6px;
    padding: 6px 10px;
}
[data-testid="stMetricLabel"] { font-size: 0.72rem !important; }
[data-testid="stMetricValue"] { font-size: 1.05rem !important; }
[data-testid="stMetricDelta"] { font-size: 0.68rem !important; }

/* Left chat panel — simple border separator */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) {
    border-right: 1px solid #1f2937;
    padding-right: 1rem !important;
}

/* Chat text input */
div[data-testid="stTextInput"] input {
    border-radius: 20px !important;
    padding: 8px 14px !important;
    border: 1px solid #374151 !important;
    background: #111827 !important;
    color: #f9fafb !important;
    font-size: 0.88rem !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}

/* Quick Q chip buttons */
div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
    border-radius: 12px !important;
    font-size: 0.68rem !important;
    padding: 4px 6px !important;
    border: 1px solid #374151 !important;
    background: #0f172a !important;
    color: #94a3b8 !important;
    white-space: normal !important;
    text-align: left !important;
    line-height: 1.25 !important;
    min-height: 36px !important;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    border-color: #6366f1 !important;
    color: #e0e7ff !important;
    background: #1e1b4b !important;
}
/* Tighter spacing overall */
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Data ───────────────────────────────────────────────────────────────────────
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
rev = (info.get("totalRevenue") or 0) / 1e9
beta = info.get("beta") or 0
ytd = 0.0
if hist is not None and not hist.empty:
    ytd = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100

# Quick DCF
_sh = info.get("sharesOutstanding") or 1
_nd = ((info.get("totalDebt") or 0) - (info.get("totalCash") or 0)) / 1e9
_fcf = max((info.get("freeCashflow") or 0) / 1e9, 11.0)
_pv, _f = 0.0, _fcf
for _yr in range(1, 6):
    _f *= 1.12
    _pv += _f / 1.09**_yr
_pv += _f * 1.03 / 0.06 / 1.09**5
iv = (_pv - _nd) * 1e9 / _sh if _sh > 0 else 0
mos = (iv - price) / iv * 100 if iv > 0 and price > 0 else 0

# Technical signal
tech_score = 0
if hist is not None and not hist.empty:
    _c = hist["Close"]
    _sma50 = _c.rolling(50).mean().iloc[-1]
    _sma200 = _c.rolling(200).mean().iloc[-1]
    _dlt = _c.diff()
    _g = _dlt.clip(lower=0).rolling(14).mean()
    _l = (-_dlt.clip(upper=0)).rolling(14).mean()
    _rsi = (100 - 100 / (1 + _g / _l.replace(0, float("nan")))).iloc[-1]
    _last = _c.iloc[-1]
    if not math.isnan(_sma50):
        tech_score += 1 if _last > _sma50 else -1
    if not math.isnan(_sma200):
        tech_score += 1 if _last > _sma200 else -1
    if not math.isnan(_rsi):
        if 40 < _rsi < 65:
            tech_score += 1
        elif _rsi >= 70:
            tech_score -= 1

tech_label = "🟢 Bullish" if tech_score >= 2 else ("🔴 Bearish" if tech_score <= -2 else "🟡 Neutral")

# ── Chat helpers ───────────────────────────────────────────────────────────────
CHIPS = [
    "What is Agent Suite?",
    "Cloudflare partnership?",
    "Is MA fairly valued?",
    "Top risks?",
    "Buy / Hold / Avoid?",
    "Agent Suite revenue?",
    "MA vs Visa?",
    "10-K growth outlook?",
]


def _system() -> str:
    return (
        "You are an expert financial analyst for Mastercard (NYSE: MA) — MBA course MGMT690.\n"
        f"LIVE DATA: Price ${price:.2f} | Cap ${mktcap:.0f}B | P/E {pe:.1f}x (fwd {fpe:.1f}x) | "
        f"Rev ${rev:.1f}B | Net Margin {margin:.1f}% | ROE {roe:.1f}% | FCF ${fcf_b:.1f}B | "
        f"Beta {beta:.2f} | 1Y {ytd:+.1f}% | DCF IV ${iv:.0f} | MoS {mos:+.1f}%\n"
        "Case: Agent Suite (Jan 2026) — AI-native payments. Cloudflare (Feb 2026) — agentic cyber-defense.\n"
        "Docs: Agent Suite PR, Cloudflare PRs, 10-K 2024.\n"
        "Answer the question asked — directly and only that. "
        "Keep answers under 120 words. No preamble, no 'Great question', no repetition of the question. "
        "Use bullet points for lists. Lead with the key fact or number."
    )


def _rag(q: str) -> str:
    try:
        from src.retrieval import retrieve

        chunks = retrieve(q, top_k=4)
        if not chunks:
            return ""
        return "\nDoc excerpts:\n" + "\n".join(f"[{c['citation']}]: {c['text'][:350]}" for c in chunks)
    except Exception:
        return ""


def _stream(api_key: str, history: list[dict], question: str):
    from openai import OpenAI

    msgs = [{"role": "system", "content": _system() + _rag(question)}] + history
    client = OpenAI(api_key=api_key)
    with client.chat.completions.create(
        model="gpt-4o-mini", messages=msgs, stream=True, temperature=0.2, max_tokens=350
    ) as s:
        for chunk in s:
            d = chunk.choices[0].delta.content
            if d:
                yield d


# ── Session ────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# ── LAYOUT: Chat (L 30%) | Analysis (R 70%) ───────────────────────────────────
chat, analysis = st.columns([3, 7])

# ══════════════════════════════════════════════════════════════════════════════
# LEFT — Chat Panel (sticky, 30%) · Question on top · Answers below
# ══════════════════════════════════════════════════════════════════════════════
with chat:
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("**💬 AI Research Chat**")
    st.caption("GPT-4o-mini · live data · case docs")

    # ── QUESTION INPUT — top of panel ─────────────────────────────────────────
    in_c, btn_c = st.columns([9, 1])
    with in_c:
        user_text = st.text_input(
            "q",
            placeholder="Ask about Mastercard…",
            label_visibility="collapsed",
            key=f"cf_{st.session_state.input_key}",
        )
    with btn_c:
        send = st.button("➤", key="send", help="Send")

    if st.session_state.messages:
        if st.button("🗑", key="clear", help="Clear chat"):
            st.session_state.messages = []
            st.rerun()

    # Resolve prompt
    prompt = None
    if send and user_text.strip():
        prompt = user_text.strip()
        st.session_state.input_key += 1
    elif "_pending" in st.session_state:
        prompt = st.session_state.pop("_pending")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # ── Quick questions — right below input ───────────────────────────────────
    st.markdown(
        "<p style='font-size:0.75rem;color:#6b7280;margin:4px 0 3px'>💡 Quick questions:</p>",
        unsafe_allow_html=True,
    )
    qc1, qc2 = st.columns(2)
    for i, q in enumerate(CHIPS):
        if (qc1 if i % 2 == 0 else qc2).button(q, key=f"chip_{i}", use_container_width=True):
            st.session_state["_pending"] = q
            st.rerun()

    # ── ANSWER BOX — below input & chips ──────────────────────────────────────
    msgs = st.session_state.messages
    has_pending = bool(msgs) and msgs[-1]["role"] == "user"

    if not msgs:
        st.markdown(
            """
<div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:10px;padding:10px;font-size:0.78rem;color:#94a3b8;margin-top:6px">
📊 <b style="color:#93c5fd">Live MA data</b> &nbsp;·&nbsp;
📚 <b style="color:#86efac">Case docs</b> &nbsp;·&nbsp;
🤖 <b style="color:#f9a8d4">AI analysis</b><br><br>
Type above or click a quick question ↑
</div>
""",
            unsafe_allow_html=True,
        )

    chat_box = st.container(height=360)
    with chat_box:
        confirmed = msgs if not has_pending else msgs[:-1]
        for msg in confirmed:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if has_pending:
            _api_key = os.environ.get("OPENAI_API_KEY", "")
            with st.chat_message("user"):
                st.markdown(msgs[-1]["content"])
            with st.chat_message("assistant"):
                if not _api_key:
                    answer = "⚠️ Add OPENAI_API_KEY to Streamlit Cloud secrets."
                    st.warning(answer)
                else:
                    try:
                        answer = st.write_stream(_stream(_api_key, msgs[:-1], msgs[-1]["content"]))
                    except Exception as e:
                        answer = f"❌ {e}"
                        st.error(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT — Analysis & Reports (70%)
# ══════════════════════════════════════════════════════════════════════════════
with analysis:
    st.markdown("### 🔍 CardLens — Mastercard (MA) · MGMT690 Project 2")

    # ── Live metrics ──────────────────────────────────────────────────────────
    st.caption("📊 **Live Market Snapshot** · auto-refreshes every 5 min")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"${price:.2f}", f"{ytd:+.1f}% 1Y")
    c2.metric("Market Cap", f"${mktcap:.0f}B")
    c3.metric("P/E (Trail)", f"{pe:.1f}x")
    c4.metric("Fwd P/E", f"{fpe:.1f}x")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Net Margin", f"{margin:.1f}%")
    c6.metric("ROE", f"{roe:.1f}%")
    c7.metric("FCF", f"${fcf_b:.1f}B")
    c8.metric("Beta", f"{beta:.2f}")

    st.divider()

    # ── Case thesis ───────────────────────────────────────────────────────────
    st.caption("📄 **Case Thesis**")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(
            "**🤖 Agent Suite — Jan 2026**\n"
            "- AI-native infra for autonomous agents\n"
            "- Token-based auth (no card credentials)\n"
            "- New monetization on existing MA network\n"
            "- MA as gatekeeper of the agentic economy"
        )
    with t2:
        st.markdown(
            "**🔒 Cloudflare Partnership — Feb 2026**\n"
            "- Cyber-defense for agentic commerce\n"
            "- Cloudflare AI validates agent authenticity\n"
            "- Extends MA trust model to AI transactions\n"
            "- Enterprise-grade security moat"
        )

    st.divider()

    # ── Fundamentals ──────────────────────────────────────────────────────────
    st.caption("📈 **Fundamentals**")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Op Margin", f"{op_m:.1f}%", "✅ >30%" if op_m > 30 else "⚠ <30%", delta_color="off")
    f2.metric("Net Margin", f"{margin:.1f}%")
    f3.metric("ROE", f"{roe:.1f}%", "✅ >30%" if roe > 30 else "", delta_color="off")
    f4.metric("Revenue TTM", f"${rev:.1f}B")

    st.divider()

    # ── Valuation & signal ────────────────────────────────────────────────────
    st.caption("💰 **Valuation & Signal**")
    v1, v2, v3 = st.columns(3)
    v1.metric("DCF Intrinsic Value", f"${iv:.0f}")
    v2.metric(
        "Margin of Safety",
        f"{mos:+.1f}%",
        "Undervalued" if mos > 0 else "Overvalued",
        delta_color="normal" if mos > 0 else "inverse",
    )
    v3.metric("Technical Trend", tech_label)

    st.divider()

    # ── Navigation ────────────────────────────────────────────────────────────
    st.caption("🗂 **Detailed Pages** — open sidebar ›")
    st.markdown(
        "📄 Case Overview &nbsp;·&nbsp; 📊 Fundamentals &nbsp;·&nbsp; "
        "📈 Technicals &nbsp;·&nbsp; 💰 Valuation &nbsp;·&nbsp; "
        "📰 News &nbsp;·&nbsp; ⭐ Decision",
        unsafe_allow_html=True,
    )
    st.caption("Data: Yahoo Finance · Educational only · Not investment advice.")
