"""
Final Recommendation — merges Fundamentals + Valuation + Technicals + RAG signals.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Recommendation · CardLens", page_icon="⭐", layout="wide")

st.title("⭐ Final Recommendation")
st.caption("Synthesizes Fundamentals · Valuation · Technicals · Case RAG signals")

ticker_sym = st.session_state.get("ticker", "MA")
horizon = st.session_state.get("horizon", "3M")
risk_profile = st.session_state.get("risk_profile", "Balanced")

st.info(
    f"**Active settings**: Ticker = **{ticker_sym}** · Horizon = **{horizon}** · Risk Profile = **{risk_profile}**  \n"
    "Adjust in the Home sidebar.",
    icon="⚙️",
)

# ── Fetch data ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_info(sym: str) -> dict:
    return yf.Ticker(sym).info or {}

@st.cache_data(ttl=900)
def get_hist(sym: str) -> pd.DataFrame:
    return yf.Ticker(sym).history(period="1y")

with st.spinner("Gathering signals…"):
    try:
        info = get_info(ticker_sym)
        hist = get_hist(ticker_sym)
    except Exception as e:
        st.error(f"Data fetch failed: {e}")
        st.stop()

# ── 1. Fundamentals signal ─────────────────────────────────────────────────
op_margin = info.get("operatingMargins", 0) or 0
net_margin = info.get("profitMargins", 0) or 0
roe = info.get("returnOnEquity", 0) or 0
fcf = info.get("freeCashflow", 0) or 0

fund_score = 0
fund_notes = []
if op_margin > 0.20:
    fund_score += 1; fund_notes.append(f"Strong operating margin ({op_margin*100:.1f}%)")
else:
    fund_score -= 1; fund_notes.append(f"Weak operating margin ({op_margin*100:.1f}%)")
if roe > 0.15:
    fund_score += 1; fund_notes.append(f"High ROE ({roe*100:.1f}%) — moat proxy")
else:
    fund_notes.append(f"ROE below 15% ({roe*100:.1f}%)")
if fcf > 0:
    fund_score += 1; fund_notes.append(f"Positive FCF (${fcf/1e9:.1f}B)")
else:
    fund_score -= 1; fund_notes.append("Negative FCF — watch")

fund_label = "Strong" if fund_score >= 2 else ("Moderate" if fund_score >= 0 else "Weak")

# ── 2. Valuation signal ────────────────────────────────────────────────────
current_price = info.get("currentPrice", 0) or 0
trailing_eps = info.get("trailingEps", 0) or 0
trailing_pe = info.get("trailingPE", 0) or 0

val_score = 0
val_notes = []
mos_thresholds = {"Conservative": 20, "Balanced": 10, "Aggressive": 5}
mos_threshold = mos_thresholds[risk_profile]

if trailing_eps > 0 and current_price > 0:
    base_pe = 28
    implied = trailing_eps * base_pe
    mos = (implied - current_price) / implied * 100
    if mos >= mos_threshold:
        val_score += 2; val_notes.append(f"Attractive: {mos:.1f}% margin of safety vs base PE ({base_pe}x)")
    elif mos >= 0:
        val_score += 1; val_notes.append(f"Fair: {mos:.1f}% margin of safety (below {mos_threshold}% threshold)")
    else:
        val_score -= 1; val_notes.append(f"Stretched: {mos:.1f}% — stock trading above base PE fair value")
else:
    val_notes.append("Insufficient EPS data for PE-based valuation")

if trailing_pe and trailing_pe > 0:
    if trailing_pe < 25:
        val_score += 1; val_notes.append(f"Reasonable trailing P/E ({trailing_pe:.1f}x)")
    elif trailing_pe > 40:
        val_score -= 1; val_notes.append(f"Elevated trailing P/E ({trailing_pe:.1f}x)")
    else:
        val_notes.append(f"Moderate trailing P/E ({trailing_pe:.1f}x)")

val_label = "Attractive" if val_score >= 2 else ("Fair" if val_score >= 0 else "Stretched")

# ── 3. Technicals signal ───────────────────────────────────────────────────
tech_score = 0
tech_notes = []

if not hist.empty:
    close = hist["Close"]
    last_close = close.iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]
    sma200 = close.rolling(200).mean().iloc[-1]

    delta_c = close.diff()
    gain = delta_c.clip(lower=0).rolling(14).mean()
    loss = (-delta_c.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = (100 - 100 / (1 + rs)).iloc[-1]

    ema12 = close.ewm(span=12).mean().iloc[-1]
    ema26 = close.ewm(span=26).mean().iloc[-1]
    macd = ema12 - ema26
    signal_line = close.ewm(span=12).mean().ewm(span=9).mean().iloc[-1]

    import math
    if not math.isnan(sma50):
        if last_close > sma50:
            tech_score += 1; tech_notes.append(f"Price above SMA50 (${sma50:.0f})")
        else:
            tech_score -= 1; tech_notes.append(f"Price below SMA50 (${sma50:.0f})")
    if not math.isnan(sma200):
        if last_close > sma200:
            tech_score += 1; tech_notes.append(f"Price above SMA200 (${sma200:.0f})")
        else:
            tech_score -= 1; tech_notes.append(f"Price below SMA200 (${sma200:.0f})")
    if not math.isnan(rsi):
        if 40 < rsi < 65:
            tech_score += 1; tech_notes.append(f"RSI in constructive zone ({rsi:.1f})")
        elif rsi >= 70:
            tech_score -= 1; tech_notes.append(f"RSI overbought ({rsi:.1f})")
        else:
            tech_notes.append(f"RSI neutral ({rsi:.1f})")

tech_label = "Bullish" if tech_score >= 2 else ("Neutral" if tech_score >= 0 else "Bearish")

# ── 4. RAG catalysts & risks ───────────────────────────────────────────────
from pathlib import Path as _P
index_exists = (_P(__file__).parent.parent / "data" / "index" / "embeddings.npz").exists()

rag_catalysts = []
rag_risks = []
rag_available = False

if index_exists:
    try:
        from src.qa import answer_question
        cat_result = answer_question(
            f"What are the key growth catalysts and competitive advantages for {ticker_sym} based on the case?",
            top_k=4,
        )
        risk_result = answer_question(
            f"What are the key risks and threats facing {ticker_sym} based on the case?",
            top_k=4,
        )
        if not cat_result.get("no_index"):
            rag_catalysts = [cat_result["answer"]] if cat_result["answer"] else []
            rag_risks = [risk_result["answer"]] if risk_result["answer"] else []
            rag_available = True
    except Exception:
        pass

# ── Decision logic ─────────────────────────────────────────────────────────
total_score = fund_score + val_score + tech_score

if total_score >= 4:
    decision = "BUY"
    decision_color = "green"
    confidence = "High"
elif total_score >= 2:
    decision = "BUY"
    decision_color = "green"
    confidence = "Medium"
elif total_score >= 0:
    decision = "HOLD"
    decision_color = "orange"
    confidence = "Medium"
elif total_score >= -2:
    decision = "HOLD"
    decision_color = "orange"
    confidence = "Low"
else:
    decision = "AVOID"
    decision_color = "red"
    confidence = "Medium"

# Horizon scenario ranges (labeled as illustrative scenarios, NOT certainty)
horizon_scenarios = {
    "1W":  {"Bull": "+2% to +4%", "Base": "-1% to +2%", "Bear": "-3% to -1%"},
    "1M":  {"Bull": "+5% to +10%", "Base": "-2% to +5%", "Bear": "-8% to -2%"},
    "3M":  {"Bull": "+10% to +20%", "Base": "-5% to +10%", "Bear": "-15% to -5%"},
    "6M":  {"Bull": "+15% to +30%", "Base": "-8% to +15%", "Bear": "-20% to -8%"},
}
scenarios = horizon_scenarios.get(horizon, horizon_scenarios["3M"])

# ── Render ─────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"## Decision: :{decision_color}[{decision}]")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Decision", decision)
col2.metric("Confidence", confidence)
col3.metric("Horizon", horizon)
col4.metric("Composite Score", f"{total_score:+d} / {fund_score + val_score + tech_score:+d}")

st.divider()

# Signal breakdown
st.subheader("Signal Breakdown")
signal_df = pd.DataFrame([
    {"Signal", "Fundamentals", fund_label, fund_score},
    {"Signal", "Valuation", val_label, val_score},
    {"Signal", "Technicals", tech_label, tech_score},
])

cols = st.columns(3)
with cols[0]:
    color = "green" if fund_score > 0 else ("orange" if fund_score == 0 else "red")
    st.markdown(f"**Fundamentals**: :{color}[{fund_label}]")
    for n in fund_notes:
        st.markdown(f"- {n}")

with cols[1]:
    color = "green" if val_score > 0 else ("orange" if val_score == 0 else "red")
    st.markdown(f"**Valuation**: :{color}[{val_label}]")
    for n in val_notes:
        st.markdown(f"- {n}")

with cols[2]:
    color = "green" if tech_score > 0 else ("orange" if tech_score == 0 else "red")
    st.markdown(f"**Technicals**: :{color}[{tech_label}]")
    for n in tech_notes:
        st.markdown(f"- {n}")

st.divider()

# Horizon outlook
st.subheader(f"Horizon Outlook ({horizon}) — Illustrative Scenario Ranges")
st.caption(
    "These are scenario ranges based on signal analysis, NOT return guarantees or predictions. "
    "Actual outcomes depend on many factors outside this model."
)
scen_cols = st.columns(3)
scen_cols[0].metric("Bull Scenario", scenarios["Bull"])
scen_cols[1].metric("Base Scenario", scenarios["Base"])
scen_cols[2].metric("Bear Scenario", scenarios["Bear"])

st.divider()

# RAG catalysts & risks
st.subheader("Case-Grounded Catalysts & Risks")
if rag_available:
    col_cat, col_risk = st.columns(2)
    with col_cat:
        st.markdown("**Key Catalysts (from case docs)**")
        for c in rag_catalysts:
            st.markdown(c)
    with col_risk:
        st.markdown("**Key Risks (from case docs)**")
        for r in rag_risks:
            st.markdown(r)
else:
    st.info(
        "Case-grounded catalysts and risks require document index. "
        "Go to **Sources** → Rebuild Index after adding files to `data/raw/`.",
        icon="📚",
    )

st.divider()
st.caption(
    "Recommendation is generated by a rules-based heuristic combining public market data and case documents. "
    "This is NOT financial advice. For educational purposes only (MGMT690 Project 2)."
)
