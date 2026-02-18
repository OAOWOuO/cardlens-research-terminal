"""
Valuation — DCF with sensitivity table (WACC × terminal growth) + peer comps.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Valuation · CardLens", page_icon="💰", layout="wide")

st.title("💰 Valuation")
st.caption("DCF · Sensitivity analysis · Peer comps · Educational only — not investment advice")

TICKER = "MA"
PEERS = {"MA": "Mastercard", "V": "Visa", "AXP": "American Express", "PYPL": "PayPal", "FIS": "Fiserv"}


@st.cache_data(ttl=3600)
def get_info(sym: str) -> dict:
    return yf.Ticker(sym).info or {}


with st.spinner("Loading market data…"):
    try:
        info = get_info(TICKER)
    except Exception as e:
        st.error(f"Failed: {e}")
        st.stop()

current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
trailing_eps = info.get("trailingEps") or 0.0
fcf = info.get("freeCashflow") or 0
shares = info.get("sharesOutstanding") or 1
total_debt = info.get("totalDebt") or 0
total_cash = info.get("totalCash") or 0
net_debt = (total_debt - total_cash) / 1e9  # $B

# ── Section 1: PE multiples ───────────────────────────────────────────────────
st.subheader("1 · Multiples-Based Valuation")
st.caption("PE-band fair value using trailing EPS × scenario multiples.")

c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"${current_price:.2f}")
c2.metric("Trailing EPS", f"${trailing_eps:.2f}" if trailing_eps else "N/A")
c3.metric("Trailing P/E", f"{info.get('trailingPE', 0):.1f}x" if info.get("trailingPE") else "N/A")

if trailing_eps and trailing_eps > 0:
    pe_scenarios = {"Bear (22x)": 22, "Base (28x)": 28, "Bull (35x)": 35}
    rows = []
    for label, pe in pe_scenarios.items():
        implied = trailing_eps * pe
        rows.append(
            {
                "Scenario": label,
                "Applied P/E": f"{pe}x",
                "Implied Price": f"${implied:.0f}",
                "vs Current": f"{(implied / current_price - 1) * 100:+.1f}%" if current_price else "N/A",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.warning("EPS data unavailable — PE multiples cannot be computed.")

st.divider()

# ── Section 2: DCF ────────────────────────────────────────────────────────────
st.subheader("2 · DCF-Lite (Adjustable Assumptions)")

with st.form("dcf"):
    r1c1, r1c2, r1c3 = st.columns(3)
    base_fcf_B = r1c1.number_input("Base FCF ($B)", value=round(fcf / 1e9, 1) if fcf else 11.0, step=0.5)
    growth_rate = r1c2.slider("FCF Growth (Yrs 1–5)", 0.0, 0.30, 0.12, 0.01, format="%.0f%%")
    terminal_growth = r1c3.slider("Terminal Growth", 0.01, 0.05, 0.03, 0.005, format="%.1f%%")

    r2c1, r2c2 = st.columns(2)
    wacc = r2c1.slider("WACC (Discount Rate)", 0.06, 0.14, 0.09, 0.005, format="%.1f%%")
    net_debt_input = r2c2.number_input("Net Debt ($B, neg = net cash)", value=round(net_debt, 1), step=0.5)

    submitted = st.form_submit_button("Recalculate")


def _dcf(fcf_b, g, w, tg, nd_b, sh) -> float:
    """Return intrinsic value per share."""
    pv = 0.0
    f = fcf_b
    for yr in range(1, 6):
        f *= 1 + g
        pv += f / (1 + w) ** yr
    if w > tg:
        tv = f * (1 + tg) / (w - tg)
        pv += tv / (1 + w) ** 5
    equity = (pv - nd_b) * 1e9
    return equity / sh if sh > 0 else 0


iv = _dcf(base_fcf_B, growth_rate, wacc, terminal_growth, net_debt_input, shares)
mos = (iv - current_price) / iv * 100 if iv > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Intrinsic Value / Share", f"${iv:.0f}")
col2.metric("Current Price", f"${current_price:.2f}")
col3.metric(
    "Margin of Safety",
    f"{mos:.1f}%",
    delta="Undervalued" if mos > 0 else "Overvalued",
    delta_color="normal" if mos > 0 else "inverse",
)

if mos > 15:
    st.success(f"DCF suggests {mos:.1f}% margin of safety at current assumptions.")
elif mos > 0:
    st.warning(f"Small margin of safety ({mos:.1f}%). Stock close to fair value.")
else:
    st.error(f"Stock appears overvalued by {-mos:.1f}% vs DCF. Adjust assumptions or see Bull case.")

st.divider()

# ── Section 3: Sensitivity table ─────────────────────────────────────────────
st.subheader("3 · Sensitivity Table — Intrinsic Value / Share")
st.caption("Rows = Terminal Growth · Columns = WACC · Green = above current price · Red = below")

wacc_range = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
tg_range = [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]

sens_data = {}
for tg_v in tg_range:
    row = {}
    for w_v in wacc_range:
        row[f"WACC {w_v * 100:.0f}%"] = round(_dcf(base_fcf_B, growth_rate, w_v, tg_v, net_debt_input, shares), 0)
    sens_data[f"TG {tg_v * 100:.1f}%"] = row

df_sens = pd.DataFrame(sens_data).T


def _color(val):
    try:
        v = float(val)
    except Exception:
        return ""
    if v >= current_price * 1.15:
        return "background-color:#1a472a;color:#90EE90;font-weight:bold"
    elif v >= current_price:
        return "background-color:#2d5a27;color:#b7e4b7"
    elif v >= current_price * 0.85:
        return "background-color:#5a2d2d;color:#FFB6B6"
    return "background-color:#6b1a1a;color:#FF9999;font-weight:bold"


st.dataframe(df_sens.style.map(_color).format("${:.0f}"), use_container_width=True)
st.caption(
    f"Current price reference: ${current_price:.2f}. Base FCF = ${base_fcf_B:.1f}B, Growth = {growth_rate * 100:.0f}%."
)

st.divider()

# ── Section 4: Peer comps ─────────────────────────────────────────────────────
st.subheader("4 · Peer Comparables")
st.caption("P/E · EV/EBITDA · P/S · Net Margin — fetched live via yfinance")


@st.cache_data(ttl=3600)
def get_peer_data() -> pd.DataFrame:
    rows = []
    for sym, name in PEERS.items():
        try:
            i = get_info(sym)
            rows.append(
                {
                    "Ticker": sym,
                    "Company": name,
                    "Price": f"${i.get('currentPrice', 0):.2f}" if i.get("currentPrice") else "N/A",
                    "P/E (Trail.)": f"{i.get('trailingPE', 0):.1f}x" if i.get("trailingPE") else "N/A",
                    "P/E (Fwd)": f"{i.get('forwardPE', 0):.1f}x" if i.get("forwardPE") else "N/A",
                    "EV/EBITDA": f"{i.get('enterpriseToEbitda', 0):.1f}x" if i.get("enterpriseToEbitda") else "N/A",
                    "P/S": f"{i.get('priceToSalesTrailing12Months', 0):.1f}x"
                    if i.get("priceToSalesTrailing12Months")
                    else "N/A",
                    "Net Margin": f"{i.get('profitMargins', 0) * 100:.1f}%" if i.get("profitMargins") else "N/A",
                    "Op Margin": f"{i.get('operatingMargins', 0) * 100:.1f}%" if i.get("operatingMargins") else "N/A",
                }
            )
        except Exception:
            rows.append({"Ticker": sym, "Company": name, "Price": "Error"})
    return pd.DataFrame(rows)


with st.spinner("Loading peer data…"):
    df_peers = get_peer_data()

st.dataframe(df_peers, use_container_width=True, hide_index=True)
st.caption(
    "MA row is highlighted context; all peers fetched from Yahoo Finance. Multiples reflect market consensus, not CardLens estimates."
)
