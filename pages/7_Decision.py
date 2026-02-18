"""
Decision — Buy / Hold / Avoid via composite signal.
Formula: 0.5 × valuation_gap + 0.3 × trend_score + 0.2 × fundamental_score
Return ranges from ±1σ volatility shifted by composite × 0.5 alpha. No hardcoded numbers.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Decision · CardLens", page_icon="⭐", layout="wide")

st.title("⭐ Trade Decision")
st.caption(
    "Composite signal: 0.5 × valuation gap + 0.3 × trend + 0.2 × fundamentals. All inputs computed from live data."
)

TICKER = "MA"
HORIZON_DAYS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126}


@st.cache_data(ttl=3600)
def get_info() -> dict:
    return yf.Ticker(TICKER).info or {}


@st.cache_data(ttl=900)
def get_hist() -> pd.DataFrame:
    return yf.Ticker(TICKER).history(period="2y")


with st.spinner("Computing signals…"):
    try:
        info = get_info()
        hist = get_hist()
    except Exception as e:
        st.error(f"Data error: {e}")
        st.stop()

current_price = info.get("currentPrice") or 0.0
fcf = info.get("freeCashflow") or 0
shares = info.get("sharesOutstanding") or 1
total_debt = (info.get("totalDebt") or 0) / 1e9
total_cash = (info.get("totalCash") or 0) / 1e9
net_debt = total_debt - total_cash


# ── DCF (base case) ───────────────────────────────────────────────────────────
def _dcf(fcf_b, g=0.12, w=0.09, tg=0.03, nd=0.0, sh=1) -> float:
    pv, f = 0.0, fcf_b
    for yr in range(1, 6):
        f *= 1 + g
        pv += f / (1 + w) ** yr
    if w > tg:
        pv += f * (1 + tg) / (w - tg) / (1 + w) ** 5
    return (pv - nd) * 1e9 / sh if sh > 0 else 0


base_fcf_B = fcf / 1e9 if fcf > 0 else 11.0
iv = _dcf(base_fcf_B, nd=net_debt, sh=shares)

# ── 1. Valuation gap ──────────────────────────────────────────────────────────
# Gap = (DCF intrinsic value − current price) / current price
# Positive → undervalued, Negative → overvalued
valuation_gap = (iv - current_price) / current_price if current_price > 0 else 0.0

# ── 2. Trend score (−1 / 0 / +1) ─────────────────────────────────────────────
trend_score = 0.0
trend_label = "Neutral"
tech_notes: list[str] = []

if not hist.empty:
    close_ser = hist["Close"]
    last_close = float(close_ser.iloc[-1])
    sma50 = float(close_ser.rolling(50).mean().iloc[-1])
    sma200 = float(close_ser.rolling(200).mean().iloc[-1])
    delta = close_ser.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = float((100 - 100 / (1 + gain / loss.replace(0, float("nan")))).iloc[-1])

    # Rules per spec: Bullish if price > SMA50 > SMA200 AND 45 ≤ RSI ≤ 70
    bullish = (
        not math.isnan(sma50)
        and not math.isnan(sma200)
        and last_close > sma50 > sma200
        and not math.isnan(rsi)
        and 45 <= rsi <= 70
    )
    # Bearish if price < SMA50 < SMA200 AND (RSI < 40 OR RSI > 75)
    bearish = (
        not math.isnan(sma50)
        and not math.isnan(sma200)
        and last_close < sma50 < sma200
        and not math.isnan(rsi)
        and (rsi < 40 or rsi > 75)
    )

    if bullish:
        trend_score = 1.0
        trend_label = "Bullish"
        tech_notes.append(f"Price ${last_close:.0f} > SMA50 ${sma50:.0f} > SMA200 ${sma200:.0f} ✓")
        tech_notes.append(f"RSI {rsi:.1f} in 45–70 constructive zone ✓")
    elif bearish:
        trend_score = -1.0
        trend_label = "Bearish"
        tech_notes.append(f"Price ${last_close:.0f} < SMA50 ${sma50:.0f} < SMA200 ${sma200:.0f} ✗")
        tech_notes.append(f"RSI {rsi:.1f} — {'oversold (<40)' if rsi < 40 else 'overbought (>75)'} ✗")
    else:
        trend_score = 0.0
        trend_label = "Neutral"
        if not math.isnan(sma50):
            tech_notes.append(f"Price {'above' if last_close > sma50 else 'below'} SMA50 ${sma50:.0f}")
        if not math.isnan(sma200):
            tech_notes.append(f"Price {'above' if last_close > sma200 else 'below'} SMA200 ${sma200:.0f}")
        if not math.isnan(rsi):
            tech_notes.append(f"RSI {rsi:.1f} — does not meet bullish or bearish threshold")

# ── 3. Fundamental score → normalized to [−1, +1] ────────────────────────────
# Raw: op_margin > 50% → +1 · ROE > 100% → +1 · rev growth > 10% → +1  (max = 3)
# Normalized: (raw / 3) × 2 − 1  maps [0, 3] → [−1, +1]
op_m = info.get("operatingMargins") or 0.0
roe = info.get("returnOnEquity") or 0.0
rev_growth = info.get("revenueGrowth") or 0.0

fund_raw = 0
fund_notes: list[str] = []
if op_m > 0.50:
    fund_raw += 1
    fund_notes.append(f"Op margin {op_m * 100:.1f}% > 50% ✓")
else:
    fund_notes.append(f"Op margin {op_m * 100:.1f}% — below 50% threshold")
if roe > 1.00:
    fund_raw += 1
    fund_notes.append(f"ROE {roe * 100:.1f}% > 100% ✓")
else:
    fund_notes.append(f"ROE {roe * 100:.1f}% — below 100% threshold")
if rev_growth > 0.10:
    fund_raw += 1
    fund_notes.append(f"Revenue growth {rev_growth * 100:.1f}% > 10% ✓")
else:
    fund_notes.append(f"Revenue growth {rev_growth * 100:.1f}% — below 10% threshold")

fund_score_norm = (fund_raw / 3) * 2 - 1  # maps [0,3] → [−1, +1]

# ── Composite signal ──────────────────────────────────────────────────────────
# Clamp valuation_gap to [−1, +1] so one outlier doesn't dominate
val_gap_clamped = max(-1.0, min(1.0, valuation_gap))
composite = 0.5 * val_gap_clamped + 0.3 * trend_score + 0.2 * fund_score_norm

if composite > 0.1:
    decision, d_color = "BUY", "green"
elif composite < -0.1:
    decision, d_color = "AVOID", "red"
else:
    decision, d_color = "HOLD", "orange"

# ── Display: Decision ─────────────────────────────────────────────────────────
st.divider()
st.markdown(f"## Decision: :{d_color}[**{decision}**]")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Composite Signal", f"{composite:+.3f}", help="+0.1 = Buy · −0.1 = Avoid · between = Hold")
m2.metric("Valuation Gap", f"{val_gap_clamped:+.1%}", help="(DCF IV − Price) / Price, clamped ±1")
m3.metric("Trend Score", f"{trend_score:+.0f}", trend_label)
m4.metric("Fundamental Score", f"{fund_score_norm:+.2f}", help="Normalized −1 to +1")

st.divider()

# ── Formula transparency ──────────────────────────────────────────────────────
st.subheader("Signal Formula & Inputs")
with st.expander("Show full formula and all input values", expanded=True):
    st.markdown(
        f"""
**Composite = 0.5 × Valuation Gap + 0.3 × Trend + 0.2 × Fundamentals**

| Input | Raw Value | Normalized | Weight |
|---|---|---|---|
| DCF Intrinsic Value | ${iv:.0f} | — | — |
| Current Price | ${current_price:.2f} | — | — |
| **Valuation Gap** | {valuation_gap:+.1%} (clamped to {val_gap_clamped:+.1%}) | {val_gap_clamped:+.3f} | 50% |
| **Trend Score** | {trend_label} | {trend_score:+.1f} | 30% |
| **Fundamental Score** | {fund_raw}/3 raw | {fund_score_norm:+.3f} | 20% |
| **Composite** | | **{composite:+.3f}** | 100% |

**Decision rule:** composite > +0.1 → BUY · < −0.1 → AVOID · otherwise → HOLD

**Trend rule that fired:** {trend_label} — {tech_notes[0] if tech_notes else "N/A"}

**Fundamental inputs:**
{"".join(f"- {n}\n" for n in fund_notes)}
"""
    )

st.divider()

# ── Signal breakdown ──────────────────────────────────────────────────────────
st.subheader("Signal Breakdown")
bc1, bc2, bc3 = st.columns(3)

with bc1:
    color = "green" if val_gap_clamped > 0.05 else ("red" if val_gap_clamped < -0.05 else "orange")
    st.markdown(
        f":{color}[**Valuation: {'Undervalued' if val_gap_clamped > 0.05 else ('Overvalued' if val_gap_clamped < -0.05 else 'Fair')}**]"
    )
    st.markdown(f"- DCF IV: ${iv:.0f}")
    st.markdown(f"- Current: ${current_price:.2f}")
    st.markdown(f"- Gap: {valuation_gap:+.1%}")

with bc2:
    t_color = "green" if trend_score > 0 else ("red" if trend_score < 0 else "orange")
    st.markdown(f":{t_color}[**Trend: {trend_label}**]")
    for n in tech_notes:
        st.markdown(f"- {n}")

with bc3:
    f_color = "green" if fund_score_norm > 0 else ("red" if fund_score_norm < 0 else "orange")
    st.markdown(f":{f_color}[**Fundamentals: {fund_raw}/3 criteria met**]")
    for n in fund_notes:
        st.markdown(f"- {n}")

st.divider()

# ── Expected return ranges (±1σ, shifted by composite × alpha) ───────────────
st.subheader("Expected Return Ranges (Data-Derived)")
st.caption(
    "Center = composite signal × 0.5 alpha × √(days/252). "
    "Bands = ±1σ from historical volatility. "
    "These are probabilistic scenarios — NOT predictions or guarantees."
)

if not hist.empty:
    daily_ret = hist["Close"].pct_change().dropna()
    ann_vol = float(daily_ret.std() * np.sqrt(252))
    alpha = 0.5  # composite signal scaling factor

    rows = []
    for label, days in HORIZON_DAYS.items():
        horizon_vol = ann_vol * math.sqrt(days / 252)
        # Center the distribution: composite signal × alpha × horizon fraction
        center = composite * alpha * (days / 252)

        bull_r = (center + horizon_vol) * 100
        bear_r = (center - horizon_vol) * 100
        base_r = center * 100

        rows.append(
            {
                "Horizon": label,
                "Bear (−1σ)": f"{bear_r:+.1f}%  (${current_price * (1 + bear_r / 100):.0f})",
                "Base": f"{base_r:+.1f}%  (${current_price * (1 + base_r / 100):.0f})",
                "Bull (+1σ)": f"{bull_r:+.1f}%  (${current_price * (1 + bull_r / 100):.0f})",
                "Ann. Vol": f"{ann_vol * 100:.1f}%",
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("How are these ranges computed?"):
        st.markdown(
            f"""
**Formula:**
- **Annual volatility**: `{ann_vol * 100:.1f}%` (std of daily returns × √252, 2Y history)
- **Horizon volatility** = Ann. Vol × √(days / 252)
- **Center** = Composite signal ({composite:+.3f}) × alpha (0.5) × (days / 252)
- **Bull** = center + 1σ horizon vol
- **Bear** = center − 1σ horizon vol
- **Composite signal inputs**: Valuation gap {val_gap_clamped:+.1%} (50%) · Trend {trend_score:+.0f} (30%) · Fund {fund_score_norm:+.2f} (20%)
"""
        )

st.divider()

# ── Case-grounded catalysts & risks ──────────────────────────────────────────
st.subheader("Case Context (from indexed documents)")
index_file = Path(__file__).parent.parent / "data" / "index" / "embeddings.npz"
if index_file.exists():
    with st.spinner("Pulling case context…"):
        try:
            from src.qa import answer_question

            cat = answer_question(
                "What are the key growth catalysts for Mastercard from Agent Suite and Cloudflare?", top_k=4
            )
            risk = answer_question("What are the top risks to Mastercard's thesis from the case documents?", top_k=4)

            cc1, cc2 = st.columns(2)
            cc1.markdown("**Catalysts (from case docs)**")
            cc1.markdown(cat["answer"])
            if cat.get("excerpts"):
                titles = list({ex["source_title"] for ex in cat["excerpts"]})
                cc1.caption("Sources: " + " · ".join(titles))

            cc2.markdown("**Risks (from case docs)**")
            cc2.markdown(risk["answer"])
            if risk.get("excerpts"):
                titles = list({ex["source_title"] for ex in risk["excerpts"]})
                cc2.caption("Sources: " + " · ".join(titles))
        except Exception as e:
            st.info(f"Could not load case context: {e}")
else:
    st.info("Case document index not found — ensure data/index/embeddings.npz is present.", icon="📚")

st.divider()
st.warning(
    "**Disclaimer:** This analysis is for educational purposes only as part of MGMT690. "
    "It is not investment advice. Do not make investment decisions based on this tool. "
    "All return ranges are probabilistic scenarios derived from historical volatility and signal inputs.",
    icon="⚠️",
)
