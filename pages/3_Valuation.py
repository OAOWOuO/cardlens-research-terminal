"""
Valuation page — DCF-lite + multiples with editable assumptions.
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

st.set_page_config(page_title="Valuation · CardLens", page_icon="💰", layout="wide")

st.title("💰 Valuation")

ticker_sym = st.session_state.get("ticker", "MA")
st.caption(f"Ticker: **{ticker_sym}** · Scenarios are illustrative, not investment advice.")

@st.cache_data(ttl=3600)
def fetch_info(sym: str) -> dict:
    return yf.Ticker(sym).info or {}

with st.spinner("Loading market data…"):
    try:
        info = fetch_info(ticker_sym)
    except Exception as e:
        st.error(f"Failed to load: {e}")
        st.stop()

current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0.0)
trailing_eps = info.get("trailingEps", 0.0) or 0.0
forward_eps = info.get("forwardEps", 0.0) or 0.0
trailing_pe = info.get("trailingPE", 0.0) or 0.0
ev_ebitda = info.get("enterpriseToEbitda", 0.0) or 0.0
shares = info.get("sharesOutstanding", 1) or 1
revenue = info.get("totalRevenue", 0) or 0
fcf = info.get("freeCashflow", 0) or 0

# ── Section 1: Multiples ───────────────────────────────────────────────────
st.subheader("Multiples-Based Valuation")
col1, col2, col3 = st.columns(3)
col1.metric("Current Price", f"${current_price:.2f}")
col2.metric("Trailing P/E", f"{trailing_pe:.1f}x" if trailing_pe else "N/A")
col3.metric("EV/EBITDA", f"{ev_ebitda:.1f}x" if ev_ebitda else "N/A")

st.markdown("**PE-based fair value range** (using consensus PE bands):")
if trailing_eps and trailing_eps > 0:
    bear_pe, base_pe, bull_pe = 22, 28, 35
    bear_val = trailing_eps * bear_pe
    base_val = trailing_eps * base_pe
    bull_val = trailing_eps * bull_pe
    df_pe = pd.DataFrame({
        "Scenario": ["Bear", "Base", "Bull"],
        "Applied P/E": [f"{bear_pe}x", f"{base_pe}x", f"{bull_pe}x"],
        "Implied Price": [f"${bear_val:.0f}", f"${base_val:.0f}", f"${bull_val:.0f}"],
        "vs Current": [
            f"{(bear_val/current_price-1)*100:+.1f}%" if current_price else "N/A",
            f"{(base_val/current_price-1)*100:+.1f}%" if current_price else "N/A",
            f"{(bull_val/current_price-1)*100:+.1f}%" if current_price else "N/A",
        ],
    })
    st.dataframe(df_pe, use_container_width=True, hide_index=True)
else:
    st.warning("EPS data unavailable from yfinance for this ticker.")

# ── Section 2: DCF-lite ────────────────────────────────────────────────────
st.subheader("DCF-Lite (Transparent Assumptions)")
st.markdown(
    "Adjust the assumptions below. This is a simplified two-stage DCF using Free Cash Flow as the base."
)

with st.form("dcf_form"):
    c1, c2, c3 = st.columns(3)
    base_fcf_B = c1.number_input(
        "Base FCF ($B)",
        value=round(fcf / 1e9, 2) if fcf else 11.0,
        step=0.5,
        help="Starting Free Cash Flow in billions.",
    )
    growth_rate = c2.slider(
        "Growth Rate (Years 1–5)",
        min_value=0.0, max_value=0.30, value=0.12, step=0.01,
        format="%.0f%%",
    )
    terminal_growth = c3.slider(
        "Terminal Growth Rate",
        min_value=0.01, max_value=0.06, value=0.03, step=0.005,
        format="%.1f%%",
    )
    c4, c5 = st.columns(2)
    discount_rate = c4.slider(
        "Discount Rate (WACC)",
        min_value=0.06, max_value=0.15, value=0.09, step=0.005,
        format="%.1f%%",
    )
    net_debt_B = c5.number_input(
        "Net Debt ($B, negative = net cash)",
        value=round((info.get("totalDebt", 0) - info.get("totalCash", 0)) / 1e9, 1),
        step=0.5,
    )
    submitted = st.form_submit_button("Calculate")

if submitted or True:
    fcf_b = base_fcf_B
    pv_total = 0.0
    for yr in range(1, 6):
        fcf_yr = fcf_b * (1 + growth_rate) ** yr
        pv_total += fcf_yr / (1 + discount_rate) ** yr

    # Terminal value (Gordon growth)
    fcf_term = fcf_b * (1 + growth_rate) ** 5 * (1 + terminal_growth)
    tv = fcf_term / (discount_rate - terminal_growth)
    pv_tv = tv / (1 + discount_rate) ** 5

    enterprise_val = pv_total + pv_tv
    equity_val = enterprise_val - net_debt_B * 1e9
    intrinsic_per_share = equity_val / shares if shares > 0 else 0
    margin_of_safety = (intrinsic_per_share - current_price) / intrinsic_per_share * 100 if intrinsic_per_share > 0 else 0

    st.divider()
    cols = st.columns(4)
    cols[0].metric("Intrinsic Value / Share", f"${intrinsic_per_share:.0f}")
    cols[1].metric("Current Price", f"${current_price:.2f}")
    cols[2].metric(
        "Margin of Safety",
        f"{margin_of_safety:.1f}%",
        delta=f"{'Undervalued' if margin_of_safety > 0 else 'Overvalued'}",
        delta_color="normal" if margin_of_safety > 0 else "inverse",
    )
    cols[3].metric("PV of Terminal Value", f"${pv_tv/1e9:.1f}B")

    risk_profile = st.session_state.get("risk_profile", "Balanced")
    mos_thresholds = {"Conservative": 20, "Balanced": 10, "Aggressive": 5}
    threshold = mos_thresholds[risk_profile]

    if margin_of_safety >= threshold:
        st.success(
            f"Margin of safety ({margin_of_safety:.1f}%) exceeds {risk_profile} threshold ({threshold}%). "
            "Suggests potential upside at current assumptions."
        )
    elif margin_of_safety >= 0:
        st.warning(
            f"Margin of safety ({margin_of_safety:.1f}%) is positive but below {risk_profile} threshold ({threshold}%)."
        )
    else:
        st.error(
            f"Stock appears overvalued vs DCF ({margin_of_safety:.1f}% margin). "
            "Adjust assumptions or see Bull scenario."
        )

    st.caption(
        "DCF is illustrative only. Assumptions drive outcomes significantly. "
        "Terminal value represents the majority of intrinsic value — treat with appropriate skepticism."
    )
