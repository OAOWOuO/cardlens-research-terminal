"""
CardLens Research Terminal — Live Chat Left · Analysis Right
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
/* Sticky right analysis column */
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {
    position: sticky;
    top: 3rem;
    height: calc(100vh - 4rem);
    overflow-y: auto;
    border-left: 1px solid #1f2937;
    padding-left: 1.5rem !important;
}
/* Metric cards */
[data-testid="stMetric"] {
    background: #111827;
    border-radius: 8px;
    padding: 8px 12px;
}
/* Send button */
button[kind="secondary"][data-testid="baseButton-secondary"] {
    border-radius: 50% !important;
    padding: 0.35rem 0.7rem !important;
}
/* Quick question chips */
div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
    border-radius: 20px !important;
    font-size: 0.73rem !important;
    border: 1px solid #374151 !important;
    background: #111827 !important;
    color: #9ca3af !important;
    white-space: normal !important;
    text-align: left !important;
    line-height: 1.3 !important;
}
div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    border-color: #6b7280 !important;
    color: #e5e7eb !important;
    background: #1f2937 !important;
}
/* Chat input field */
div[data-testid="stTextInput"] input {
    border-radius: 24px !important;
    padding: 10px 18px !important;
    border: 1px solid #374151 !important;
    background: #111827 !important;
    color: #f9fafb !important;
    font-size: 0.95rem !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.25) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Market data ────────────────────────────────────────────────────────────────
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
rsi_val = float("nan")
if hist is not None and not hist.empty:
    _c = hist["Close"]
    _sma50 = _c.rolling(50).mean().iloc[-1]
    _sma200 = _c.rolling(200).mean().iloc[-1]
    _dlt = _c.diff()
    _g = _dlt.clip(lower=0).rolling(14).mean()
    _l = (-_dlt.clip(upper=0)).rolling(14).mean()
    rsi_val = (100 - 100 / (1 + _g / _l.replace(0, float("nan")))).iloc[-1]
    _last = _c.iloc[-1]
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

# ── Chat helpers ───────────────────────────────────────────────────────────────
CHIPS = [
    "What is Mastercard Agent Suite?",
    "Cloudflare partnership — key terms?",
    "Is MA fairly valued right now?",
    "Top risks to the investment thesis?",
    "Give me a Buy / Hold / Avoid call",
    "How does Agent Suite earn revenue?",
    "MA vs Visa — which is better?",
    "What does the 10-K say about growth?",
]


def _system() -> str:
    return (
        "You are an expert financial analyst for Mastercard (NYSE: MA) — MBA course MGMT690.\n\n"
        f"LIVE DATA: Price ${price:.2f} | Mkt Cap ${mktcap:.0f}B | P/E {pe:.1f}x (fwd {fpe:.1f}x) | "
        f"Revenue ${rev:.1f}B | Net Margin {margin:.1f}% | ROE {roe:.1f}% | FCF ${fcf_b:.1f}B | "
        f"Beta {beta:.2f} | 1Y return {ytd:+.1f}% | DCF IV ${iv:.0f} | MoS {mos:+.1f}%\n\n"
        "Case events: Agent Suite (Jan 2026) — AI-native payment infrastructure. "
        "Cloudflare partnership (Feb 2026) — cyber-defense for agentic commerce.\n"
        "Documents available: Agent Suite PR, Cloudflare PRs, Mastercard 10-K 2024.\n\n"
        "Instructions: Be direct and analytical. Use specific numbers. "
        "Cite documents when relevant. Use bullet points for clarity."
    )


def _rag(q: str) -> str:
    try:
        from src.retrieval import retrieve

        chunks = retrieve(q, top_k=4)
        if not chunks:
            return ""
        return "\n\nCase document excerpts:\n" + "\n".join(f"[{c['citation']}]: {c['text'][:400]}" for c in chunks)
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


# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# ── COLUMNS: Chat Left | Analysis Right ───────────────────────────────────────
left, right = st.columns([6, 4])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEFT — Live Chat (bigger)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with left:
    st.subheader("💬 Live AI Research Chat")
    st.caption("GPT-4o-mini · live market data · Agent Suite PR · Cloudflare PRs · 10-K · streams in real time")

    # ── Onboarding card (only when no messages yet) ───────────────────────────
    if not st.session_state.messages:
        st.markdown(
            """
<div style="background:#0f172a;border:1px solid #1e3a5f;border-radius:14px;padding:20px 24px;margin-bottom:16px">
<div style="font-size:1.1rem;font-weight:600;color:#e2e8f0;margin-bottom:14px">👋 Welcome to CardLens AI Research Assistant</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
  <div style="background:#111827;border-radius:10px;padding:12px">
    <span style="font-size:1.3rem">📊</span><br>
    <span style="color:#93c5fd;font-weight:500">Live Market Data</span><br>
    <span style="color:#6b7280;font-size:0.82rem">Real-time MA price, P/E, margins, FCF, ROE</span>
  </div>
  <div style="background:#111827;border-radius:10px;padding:12px">
    <span style="font-size:1.3rem">📚</span><br>
    <span style="color:#86efac;font-weight:500">Case Documents</span><br>
    <span style="color:#6b7280;font-size:0.82rem">Agent Suite PR · Cloudflare PRs · 10-K 2024</span>
  </div>
  <div style="background:#111827;border-radius:10px;padding:12px">
    <span style="font-size:1.3rem">🤖</span><br>
    <span style="color:#f9a8d4;font-weight:500">AI Analysis</span><br>
    <span style="color:#6b7280;font-size:0.82rem">Valuation, strategy, risks, trade decision</span>
  </div>
  <div style="background:#111827;border-radius:10px;padding:12px">
    <span style="font-size:1.3rem">⚡</span><br>
    <span style="color:#fde68a;font-weight:500">How to start</span><br>
    <span style="color:#6b7280;font-size:0.82rem">Type below or click a quick question ↓</span>
  </div>
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── Scrollable chat area ──────────────────────────────────────────────────
    msgs = st.session_state.messages
    has_pending = bool(msgs) and msgs[-1]["role"] == "user"

    chat_box = st.container(height=480)
    with chat_box:
        confirmed = msgs if not has_pending else msgs[:-1]
        for msg in confirmed:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Stream response here, inside the chat box
        if has_pending:
            _api_key = os.environ.get("OPENAI_API_KEY", "")
            with st.chat_message("user"):
                st.markdown(msgs[-1]["content"])
            with st.chat_message("assistant"):
                if not _api_key:
                    answer = (
                        "⚠️ OpenAI API key not found. Go to **Streamlit Cloud → App settings → Secrets** "
                        'and add:\n```\nOPENAI_API_KEY = "sk-proj-..."\n```'
                    )
                    st.warning(answer)
                else:
                    try:
                        answer = st.write_stream(_stream(_api_key, msgs[:-1], msgs[-1]["content"]))
                    except Exception as e:
                        answer = f"❌ {e}"
                        st.error(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

    # ── Text input + Send button ───────────────────────────────────────────────
    in_col, btn_col = st.columns([11, 1])
    with in_col:
        user_text = st.text_input(
            "msg",
            placeholder="Ask about Mastercard, Agent Suite, Cloudflare, valuation, risks…",
            label_visibility="collapsed",
            key=f"chat_field_{st.session_state.input_key}",
        )
    with btn_col:
        send = st.button("➤", key="send_btn", help="Send message")

    prompt = None
    if send and user_text.strip():
        prompt = user_text.strip()
        st.session_state.input_key += 1  # clears the text field on rerun
    elif "_pending" in st.session_state:
        prompt = st.session_state.pop("_pending")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # ── Clear button ───────────────────────────────────────────────────────────
    if st.session_state.messages:
        if st.button("🗑 Clear conversation", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()

    st.divider()

    # ── Quick question chips — BELOW the chat box ─────────────────────────────
    st.markdown("**💡 Quick questions — click to ask:**")
    chip_c1, chip_c2 = st.columns(2)
    for i, q in enumerate(CHIPS):
        if (chip_c1 if i % 2 == 0 else chip_c2).button(q, key=f"chip_{i}", use_container_width=True):
            st.session_state["_pending"] = q
            st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RIGHT — Analysis & Reports (sticky)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with right:
    st.markdown("### 🔍 Mastercard (NYSE: MA)")
    st.caption("MGMT690 Project 2 · CardLens Equity Research Terminal")

    # Live snapshot
    st.markdown("**📊 Live Market Snapshot**")
    ra, rb, rc = st.columns(3)
    ra.metric("Price", f"${price:.2f}", f"{ytd:+.1f}% 1Y")
    rb.metric("Mkt Cap", f"${mktcap:.0f}B")
    rc.metric("Beta", f"{beta:.2f}")
    rd, re, rf = st.columns(3)
    rd.metric("P/E (Trail.)", f"{pe:.1f}x")
    re.metric("Fwd P/E", f"{fpe:.1f}x")
    rf.metric("FCF", f"${fcf_b:.1f}B")

    st.divider()

    # Case thesis
    st.markdown("**📄 Case Thesis**")
    st.markdown(
        "🤖 **Agent Suite (Jan 2026)** — AI-native payment infra for autonomous agents. "
        "Token-based auth, new monetization layer, MA as agentic economy gatekeeper."
    )
    st.markdown(
        "🔒 **Cloudflare (Feb 2026)** — Cyber-defense for agentic commerce. "
        "Cloudflare AI validates agent authenticity, extends MA trust model."
    )

    st.divider()

    # Fundamentals
    st.markdown("**📈 Fundamentals**")
    fa, fb = st.columns(2)
    fa.metric("Op Margin", f"{op_m:.1f}%", "✅ >30%" if op_m > 30 else "⚠ <30%", delta_color="off")
    fb.metric("Net Margin", f"{margin:.1f}%")
    fc, fd = st.columns(2)
    fc.metric("ROE", f"{roe:.1f}%", "✅ >30%" if roe > 30 else "", delta_color="off")
    fd.metric("Revenue (TTM)", f"${rev:.1f}B")

    st.divider()

    # Valuation & signal
    st.markdown("**💰 Valuation & Signal**")
    va, vb = st.columns(2)
    va.metric("DCF Intrinsic Value", f"${iv:.0f}")
    vb.metric(
        "Margin of Safety",
        f"{mos:+.1f}%",
        "Undervalued" if mos > 0 else "Overvalued",
        delta_color="normal" if mos > 0 else "inverse",
    )
    st.metric("Technical Trend", tech_label)

    st.divider()

    # Navigation
    st.markdown("**🗂 Detailed Pages** *(open sidebar ›)*")
    st.markdown("📄 Case Overview · 📊 Fundamentals  \n📈 Technicals · 💰 Valuation  \n📰 News · ⭐ Decision")
    st.caption("Data: Yahoo Finance · Educational only · Not investment advice.")
