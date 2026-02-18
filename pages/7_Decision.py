"""
Decision — Buy / Hold / Avoid derived from data signals.
Return ranges computed from volatility + trend + valuation gap. No hardcoded numbers.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Decision · CardLens", page_icon="⭐", layout="wide")

st.title("⭐ Trade Decision")
st.caption(
    "Educational conclusion — Buy / Hold / Avoid. "
    "Return ranges derived from volatility + trend + valuation, not hardcoded."
)
st.warning(
    "**Disclaimer**: This is an academic exercise for MGMT690. Nothing here is investment advice. "
    "All return ranges are probabilistic scenarios, not predictions.",
    icon="⚠️",
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

# ── 1. Fundamentals signal ────────────────────────────────────────────────────
op_m = info.get("operatingMargins") or 0
net_m = info.get("profitMargins") or 0
roe = info.get("returnOnEquity") or 0
fcf_val = info.get("freeCashflow") or 0

fund_score = 0
fund_notes = []
if op_m > 0.30:
    fund_score += 1
    fund_notes.append(f"Op margin {op_m * 100:.1f}% — pricing power confirmed")
elif op_m > 0:
    fund_notes.append(f"Op margin {op_m * 100:.1f}% — below 30% threshold")
else:
    fund_score -= 1
    fund_notes.append("Negative operating margin — watch")

if roe > 0.30:
    fund_score += 1
    fund_notes.append(f"ROE {roe * 100:.1f}% — exceptional capital efficiency")
elif roe > 0:
    fund_notes.append(f"ROE {roe * 100:.1f}% — below 30% threshold")

if fcf_val > 0:
    fund_score += 1
    fund_notes.append(f"FCF positive (${fcf_val / 1e9:.1f}B) — self-funding")
else:
    fund_score -= 1
    fund_notes.append("Negative FCF — watch")


# ── 2. Valuation signal (DCF) ─────────────────────────────────────────────────
def _dcf(fcf_b, g=0.12, w=0.09, tg=0.03, nd=0.0, sh=1):
    pv = 0.0
    f = fcf_b
    for yr in range(1, 6):
        f *= 1 + g
        pv += f / (1 + w) ** yr
    if w > tg:
        tv = f * (1 + tg) / (w - tg)
        pv += tv / (1 + w) ** 5
    return (pv - nd) * 1e9 / sh if sh > 0 else 0


base_fcf_B = fcf / 1e9 if fcf > 0 else 11.0
iv = _dcf(base_fcf_B, nd=net_debt, sh=shares)
mos = (iv - current_price) / iv * 100 if iv > 0 and current_price > 0 else 0

val_score = 0
val_notes = []
if mos >= 15:
    val_score += 2
    val_notes.append(f"DCF suggests {mos:.1f}% margin of safety — materially undervalued")
elif mos >= 5:
    val_score += 1
    val_notes.append(f"DCF: modest {mos:.1f}% margin of safety")
elif mos >= -10:
    val_notes.append(f"DCF: near fair value ({mos:.1f}% MoS)")
else:
    val_score -= 1
    val_notes.append(f"DCF: overvalued by {-mos:.1f}% at base assumptions")

trailing_pe = info.get("trailingPE") or 0
if trailing_pe and trailing_pe < 30:
    val_score += 1
    val_notes.append(f"Trailing P/E {trailing_pe:.1f}x — reasonable for quality")
elif trailing_pe and trailing_pe > 45:
    val_score -= 1
    val_notes.append(f"Trailing P/E {trailing_pe:.1f}x — stretched valuation")
elif trailing_pe:
    val_notes.append(f"Trailing P/E {trailing_pe:.1f}x — moderate")

# ── 3. Technicals signal ──────────────────────────────────────────────────────
tech_score = 0
tech_notes = []

if not hist.empty:
    close_ser = hist["Close"]
    last_close = close_ser.iloc[-1]
    sma50 = close_ser.rolling(50).mean().iloc[-1]
    sma200 = close_ser.rolling(200).mean().iloc[-1]
    delta = close_ser.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = (100 - 100 / (1 + gain / loss.replace(0, float("nan")))).iloc[-1]

    for label, sma_val, sma_name in [(sma50, sma50, "SMA50"), (sma200, sma200, "SMA200")]:
        if not math.isnan(sma_val):
            up = last_close > sma_val
            tech_score += 1 if up else -1
            tech_notes.append(f"Price {'above' if up else 'below'} {sma_name} (${sma_val:.0f})")

    if not math.isnan(rsi):
        if 40 < rsi < 65:
            tech_score += 1
            tech_notes.append(f"RSI {rsi:.1f} — constructive zone")
        elif rsi >= 70:
            tech_score -= 1
            tech_notes.append(f"RSI {rsi:.1f} — overbought")
        else:
            tech_notes.append(f"RSI {rsi:.1f} — neutral/oversold")

# ── Decision ──────────────────────────────────────────────────────────────────
total = fund_score + val_score + tech_score
max_possible = 6

if total >= 4:
    decision, conf, d_color = "BUY", "High", "green"
elif total >= 2:
    decision, conf, d_color = "BUY", "Medium", "green"
elif total >= -1:
    decision, conf, d_color = "HOLD", "Medium", "orange"
elif total >= -3:
    decision, conf, d_color = "HOLD", "Low", "orange"
else:
    decision, conf, d_color = "AVOID", "Medium", "red"

st.divider()
st.markdown(f"## Decision: :{d_color}[**{decision}**]  ·  Confidence: **{conf}**")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Signal Score", f"{total:+d} / {max_possible}")
c2.metric("Fundamentals", f"{fund_score:+d}")
c3.metric("Valuation", f"{val_score:+d}")
c4.metric("Technicals", f"{tech_score:+d}")

st.divider()

# ── Signal breakdown ──────────────────────────────────────────────────────────
st.subheader("Signal Breakdown")
bc1, bc2, bc3 = st.columns(3)

fund_label = "Strong" if fund_score >= 2 else ("Moderate" if fund_score >= 0 else "Weak")
val_label = "Attractive" if val_score >= 2 else ("Fair" if val_score >= 0 else "Stretched")
tech_label = "Bullish" if tech_score >= 2 else ("Neutral" if tech_score >= 0 else "Bearish")

for col, label, score, notes in [
    (bc1, f"Fundamentals: **{fund_label}**", fund_score, fund_notes),
    (bc2, f"Valuation: **{val_label}**", val_score, val_notes),
    (bc3, f"Technicals: **{tech_label}**", tech_score, tech_notes),
]:
    color = "green" if score > 0 else ("orange" if score == 0 else "red")
    col.markdown(f":{color}[{label}]")
    for n in notes:
        col.markdown(f"- {n}")

st.divider()

# ── Horizon return ranges (data-derived) ──────────────────────────────────────
st.subheader("Horizon Scenario Ranges (Data-Derived)")
st.caption(
    "Ranges = historical volatility × horizon × 1.5σ, centered on trend + valuation adjustment. "
    "These are probabilistic scenarios, NOT predictions or guarantees."
)

if not hist.empty:
    daily_ret = hist["Close"].pct_change().dropna()
    ann_vol = daily_ret.std() * np.sqrt(252)
    mean_daily = daily_ret.mean()

    # Trend center adjustment: mean daily return × horizon trading days
    trend_mult = 1 if tech_score > 0 else (-1 if tech_score < 0 else 0)
    # Valuation gap contribution (blended at 20% weight)
    val_adj_ann = (mos / 100) * 0.20 if not math.isnan(mos) else 0

    rows = []
    for label, days in HORIZON_DAYS.items():
        horizon_vol = ann_vol * np.sqrt(days / 252)
        trend_adj = trend_mult * mean_daily * days
        val_adj = val_adj_ann * (days / 252)
        center = trend_adj + val_adj

        bull_r = (center + 1.5 * horizon_vol) * 100
        bear_r = (center - 1.5 * horizon_vol) * 100
        base_r = center * 100

        bull_p = current_price * (1 + bull_r / 100)
        bear_p = current_price * (1 + bear_r / 100)

        rows.append(
            {
                "Horizon": label,
                "Bear (−1.5σ)": f"{bear_r:+.1f}%  (${bear_p:.0f})",
                "Base": f"{base_r:+.1f}%  (${current_price * (1 + base_r / 100):.0f})",
                "Bull (+1.5σ)": f"{bull_r:+.1f}%  (${bull_p:.0f})",
                "Ann. Vol Used": f"{ann_vol * 100:.1f}%",
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("How are these ranges computed?"):
        st.markdown(
            f"""
**Formula:**
- **Annual volatility**: `{ann_vol * 100:.1f}%` (std of daily returns × √252, from 2Y price history)
- **Horizon volatility** = Ann. Vol × √(days / 252)
- **Center (base case)** = mean_daily_return × horizon_days + valuation_gap × 20% weight × (days/252)
- **Bull** = center + 1.5 × horizon_vol  (87th percentile)
- **Bear** = center − 1.5 × horizon_vol  (13th percentile)
- Trend adjustment: `{"+1 (bullish)" if tech_score > 0 else ("-1 (bearish)" if tech_score < 0 else "0 (neutral)")}` × mean daily return
- Valuation adjustment: `{mos:+.1f}%` DCF margin of safety × 20% weight
"""
        )

st.divider()

# ── Case-grounded context ─────────────────────────────────────────────────────
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
            if cat.get("citations"):
                cc1.caption("Sources: " + " · ".join(set(cat["citations"])))

            cc2.markdown("**Risks (from case docs)**")
            cc2.markdown(risk["answer"])
            if risk.get("citations"):
                cc2.caption("Sources: " + " · ".join(set(risk["citations"])))
        except Exception as e:
            st.info(f"Could not load case context: {e}")
else:
    st.info("Build document index (Home → Fetch & Index) to show case-grounded catalysts and risks.", icon="📚")

st.divider()
st.caption(
    "Signal scoring: fundamentals (max +3), valuation (max +3), technicals (max +3). "
    "Total ≥4 → BUY (High) · 2–3 → BUY (Med) · -1 to 1 → HOLD · ≤-3 → AVOID. "
    "Educational only. Not investment advice."
)
