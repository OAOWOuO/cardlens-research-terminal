"""
Fundamentals page — yfinance data + quality checklist.
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

ticker_sym = st.session_state.get("ticker", "MA")
st.caption(f"Ticker: **{ticker_sym}**")


@st.cache_data(ttl=3600)
def fetch_info(sym: str) -> dict:
    t = yf.Ticker(sym)
    return t.info or {}


@st.cache_data(ttl=3600)
def fetch_financials(sym: str):
    t = yf.Ticker(sym)
    return t.financials, t.balance_sheet, t.cashflow


with st.spinner("Loading fundamentals…"):
    try:
        info = fetch_info(ticker_sym)
        financials, balance_sheet, cashflow = fetch_financials(ticker_sym)
        load_ok = True
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        load_ok = False

if load_ok:
    # ── Key metrics table ──────────────────────────────────────────────────
    st.subheader("Key Metrics")

    def safe(d, key, fmt=None):
        v = d.get(key)
        if v is None or str(v) in {"None", "nan", ""}:
            return "N/A"
        if fmt == "pct" and isinstance(v, (int, float)):
            return f"{v * 100:.1f}%"
        if fmt == "x" and isinstance(v, (int, float)):
            return f"{v:.1f}x"
        if fmt == "B" and isinstance(v, (int, float)):
            return f"${v / 1e9:.1f}B"
        if fmt == "M" and isinstance(v, (int, float)):
            return f"${v / 1e6:.0f}M"
        return str(v)

    metrics = {
        "Market Cap": safe(info, "marketCap", "B"),
        "Enterprise Value": safe(info, "enterpriseValue", "B"),
        "P/E (Trailing)": safe(info, "trailingPE", "x"),
        "P/E (Forward)": safe(info, "forwardPE", "x"),
        "EV/EBITDA": safe(info, "enterpriseToEbitda", "x"),
        "Price/Sales": safe(info, "priceToSalesTrailing12Months", "x"),
        "Price/Book": safe(info, "priceToBook", "x"),
        "Revenue (TTM)": safe(info, "totalRevenue", "B"),
        "Gross Margin": safe(info, "grossMargins", "pct"),
        "Operating Margin": safe(info, "operatingMargins", "pct"),
        "Net Margin": safe(info, "profitMargins", "pct"),
        "ROE": safe(info, "returnOnEquity", "pct"),
        "ROA": safe(info, "returnOnAssets", "pct"),
        "EPS (Trailing)": safe(info, "trailingEps"),
        "EPS (Forward)": safe(info, "forwardEps"),
        "Dividend Yield": safe(info, "dividendYield", "pct"),
        "Beta": safe(info, "beta"),
        "52W High": safe(info, "fiftyTwoWeekHigh"),
        "52W Low": safe(info, "fiftyTwoWeekLow"),
        "Current Price": safe(info, "currentPrice"),
    }

    df_metrics = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
    st.dataframe(df_metrics, use_container_width=True, hide_index=True)

    # ── Income statement snippet ───────────────────────────────────────────
    if financials is not None and not financials.empty:
        st.subheader("Income Statement (Annual)")
        rows_to_show = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income", "EBITDA"]
        available = [r for r in rows_to_show if r in financials.index]
        if available:
            df_fin = financials.loc[available].copy()
            df_fin = df_fin.apply(lambda col: col.map(lambda v: f"${v / 1e9:.2f}B" if pd.notna(v) else "N/A"))
            st.dataframe(df_fin, use_container_width=True)

    # ── Quality Checklist ──────────────────────────────────────────────────
    st.subheader("Quality Checklist")

    def check(cond: bool | None, label: str, good: str, warn: str):
        if cond is None:
            return f"❓ **{label}**: Data unavailable"
        return f"{'✅' if cond else '⚠️'} **{label}**: {'good' if cond else 'watch'} — {good if cond else warn}"

    op_margin = info.get("operatingMargins")
    net_margin = info.get("profitMargins")
    roe = info.get("returnOnEquity")
    fcf = info.get("freeCashflow")
    beta_val = info.get("beta")

    checks = [
        check(
            op_margin > 0.20 if op_margin else None,
            "Pricing Power / Operating Margin",
            f"Strong operating margin ({op_margin * 100:.1f}%)" if op_margin else "",
            f"Low operating margin ({op_margin * 100:.1f}%)" if op_margin else "N/A",
        ),
        check(
            net_margin > 0.15 if net_margin else None,
            "Net Margin Quality",
            f"Net margin {net_margin * 100:.1f}% — above 15% threshold",
            f"Net margin {net_margin * 100:.1f}% — below 15% threshold",
        ),
        check(
            roe > 0.15 if roe else None,
            "Return on Equity (Moat Proxy)",
            f"ROE {roe * 100:.1f}% — indicates durable competitive advantage",
            f"ROE {roe * 100:.1f}% — below 15% moat proxy",
        ),
        check(
            fcf > 0 if fcf else None,
            "Free Cash Flow Generation",
            f"Positive FCF (${fcf / 1e9:.1f}B)" if fcf else "",
            f"Negative or zero FCF (${fcf / 1e9:.1f}B)" if fcf else "N/A",
        ),
        check(
            beta_val < 1.2 if beta_val else None,
            "Stability (Beta)",
            f"Low beta ({beta_val:.2f}) — relatively stable" if beta_val else "",
            f"High beta ({beta_val:.2f}) — more volatile than market" if beta_val else "N/A",
        ),
    ]

    for c in checks:
        st.markdown(c)

    st.caption("Quality checklist uses yfinance data. Cross-reference with case documents for deeper insight.")
