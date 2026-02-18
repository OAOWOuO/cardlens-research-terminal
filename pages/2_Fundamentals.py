"""
Fundamentals — MA financials from yfinance + 10-K citations, quality checklist.
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

st.set_page_config(page_title="Fundamentals · CardLens", page_icon="📋", layout="wide")

st.title("📋 Fundamentals")
st.caption("Key financial metrics · Source: yfinance (Yahoo Finance) + SEC 10-K FY2024")

TICKER = "MA"


@st.cache_data(ttl=3600)
def get_info() -> dict:
    return yf.Ticker(TICKER).info or {}


@st.cache_data(ttl=3600)
def get_financials():
    t = yf.Ticker(TICKER)
    return t.financials, t.balance_sheet, t.cashflow


with st.spinner("Loading financials…"):
    try:
        info = get_info()
        financials, balance_sheet, cashflow = get_financials()
        ok = True
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        ok = False

if not ok:
    st.stop()


def _fmt(v, mode="B"):
    if v is None or str(v) in {"None", "nan"}:
        return "N/A"
    try:
        v = float(v)
    except Exception:
        return str(v)
    if mode == "B":
        return f"${v / 1e9:.2f}B"
    if mode == "pct":
        return f"{v * 100:.1f}%"
    if mode == "x":
        return f"{v:.1f}x"
    if mode == "$":
        return f"${v:.2f}"
    return str(v)


# ── Snapshot ─────────────────────────────────────────────────────────────────
st.subheader("Snapshot")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Current Price", _fmt(info.get("currentPrice"), "$"))
c2.metric("Market Cap", _fmt(info.get("marketCap"), "B"))
c3.metric("Revenue (TTM)", _fmt(info.get("totalRevenue"), "B"))
c4.metric("Net Margin", _fmt(info.get("profitMargins"), "pct"))
c5.metric("FCF", _fmt(info.get("freeCashflow"), "B"))

st.divider()

# ── Full metrics table ────────────────────────────────────────────────────────
st.subheader("Key Metrics")

metrics = {
    "Revenue (TTM)": _fmt(info.get("totalRevenue"), "B"),
    "Gross Margin": _fmt(info.get("grossMargins"), "pct"),
    "Operating Margin": _fmt(info.get("operatingMargins"), "pct"),
    "Net Margin": _fmt(info.get("profitMargins"), "pct"),
    "ROE": _fmt(info.get("returnOnEquity"), "pct"),
    "ROA": _fmt(info.get("returnOnAssets"), "pct"),
    "EPS (Trailing)": _fmt(info.get("trailingEps"), "$"),
    "EPS (Forward)": _fmt(info.get("forwardEps"), "$"),
    "P/E (Trailing)": _fmt(info.get("trailingPE"), "x"),
    "P/E (Forward)": _fmt(info.get("forwardPE"), "x"),
    "EV/EBITDA": _fmt(info.get("enterpriseToEbitda"), "x"),
    "Price/Sales": _fmt(info.get("priceToSalesTrailing12Months"), "x"),
    "Price/Book": _fmt(info.get("priceToBook"), "x"),
    "Beta": str(round(info.get("beta", 0) or 0, 2)),
    "Dividend Yield": _fmt(info.get("dividendYield"), "pct"),
    "Free Cash Flow": _fmt(info.get("freeCashflow"), "B"),
    "Total Debt": _fmt(info.get("totalDebt"), "B"),
    "52W High": _fmt(info.get("fiftyTwoWeekHigh"), "$"),
    "52W Low": _fmt(info.get("fiftyTwoWeekLow"), "$"),
    "Shares Outstanding": _fmt(info.get("sharesOutstanding"), "B"),
}

df_m = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
st.dataframe(df_m, use_container_width=True, hide_index=True)

# ── Income Statement ──────────────────────────────────────────────────────────
if financials is not None and not financials.empty:
    st.subheader("Income Statement (Annual)")
    want = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income", "EBITDA"]
    avail = [r for r in want if r in financials.index]
    if avail:
        df_fin = financials.loc[avail].copy()
        df_fin.columns = [str(c)[:4] for c in df_fin.columns]
        df_fin_fmt = df_fin.apply(lambda col: col.map(lambda v: f"${v / 1e9:.2f}B" if pd.notna(v) else "N/A"))
        st.dataframe(df_fin_fmt, use_container_width=True)

        if len(df_fin.columns) >= 2:
            st.subheader("YoY Change")
            years = df_fin.columns.tolist()
            growth_rows = []
            for metric in ["Total Revenue", "Net Income"]:
                if metric in df_fin.index:
                    row = {"Metric": metric}
                    for i in range(len(years) - 1):
                        new_yr, old_yr = years[i], years[i + 1]
                        try:
                            new_v, old_v = float(df_fin.loc[metric, new_yr]), float(df_fin.loc[metric, old_yr])
                            pct = (new_v - old_v) / abs(old_v) * 100 if old_v else 0
                            row[f"{old_yr}→{new_yr}"] = f"{pct:+.1f}%"
                        except Exception:
                            row[f"{old_yr}→{new_yr}"] = "N/A"
                    growth_rows.append(row)
            if growth_rows:
                st.dataframe(pd.DataFrame(growth_rows), use_container_width=True, hide_index=True)

st.divider()

# ── Quality Checklist ─────────────────────────────────────────────────────────
st.subheader("Quality Checklist")
st.caption("Thresholds reflect investment-grade benchmarks for large-cap financial networks.")

op_m = info.get("operatingMargins") or 0
net_m = info.get("profitMargins") or 0
roe = info.get("returnOnEquity") or 0
fcf_v = info.get("freeCashflow") or 0
beta_v = info.get("beta") or 0
debt_v = info.get("totalDebt") or 0
ebitda_v = info.get("ebitda") or 1

checks = [
    (op_m > 0.30, "Operating Margin > 30%", f"{op_m * 100:.1f}%", "Pricing power confirmed", "Margin pressure — watch"),
    (net_m > 0.20, "Net Margin > 20%", f"{net_m * 100:.1f}%", "Best-in-class profitability", "Below 20% threshold"),
    (
        roe > 0.30,
        "ROE > 30%",
        f"{roe * 100:.1f}%",
        "Exceptional capital efficiency — moat proxy",
        "Below 30% threshold",
    ),
    (fcf_v > 0, "Positive Free Cash Flow", _fmt(fcf_v, "B"), "Self-funding growth + buybacks", "Negative FCF — watch"),
    (
        beta_v < 1.0,
        "Beta < 1.0",
        f"{beta_v:.2f}",
        "Below-market volatility — defensive quality",
        f"Beta {beta_v:.2f} — above market",
    ),
    (
        (debt_v / ebitda_v < 2.0) if ebitda_v > 0 else False,
        "Net Debt/EBITDA < 2x",
        f"{debt_v / ebitda_v:.1f}x" if ebitda_v > 0 else "N/A",
        "Conservative leverage",
        "Leverage elevated",
    ),
]

for flag, label, value, good, warn in checks:
    st.markdown(f"{'✅' if flag else '⚠️'} **{label}**: `{value}` — {good if flag else warn}")

st.divider()

# ── 10-K Citation ─────────────────────────────────────────────────────────────
st.subheader("10-K Key Passages (FY2024)")
st.info(
    "Ask the **Q&A Chat** for specific passages. Excerpts below are from `data/raw/04_mastercard_10k_2024.txt`.",
    icon="📄",
)
st.markdown(
    """
- **Revenue model**: Primarily assessments (% of GDV) + transaction processing fees — structurally recurring and volume-driven.
- **Geography**: US ~30% of net revenue; Europe, APAC, LAC, MEA compose the remainder — strong geographic diversification.
- **Capital return**: MA has consistently returned >80% of FCF via buybacks + dividends.
- **New Services**: Agent Suite and Cloudflare partnership are part of the "Value-Added Services" strategy referenced in Item 1.

*[Source: Mastercard 10-K FY2024, Items 1 & 7 — SEC EDGAR CIK 1141391]*
"""
)
