"""
Technicals page — price chart + SMA/RSI/MACD with trend signal.
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

st.set_page_config(page_title="Technicals · CardLens", page_icon="📈", layout="wide")

st.title("📈 Technicals")

ticker_sym = st.session_state.get("ticker", "MA")
st.caption(f"Ticker: **{ticker_sym}**")

period_map = {"3M": "3mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y"}
period_label = st.selectbox("Chart Period", list(period_map.keys()), index=2)
period = period_map[period_label]


@st.cache_data(ttl=900)
def fetch_hist(sym: str, per: str) -> pd.DataFrame:
    return yf.Ticker(sym).history(period=per)


with st.spinner("Loading price data…"):
    try:
        df = fetch_hist(ticker_sym, period)
        if df.empty:
            st.error("No price data returned.")
            st.stop()
    except Exception as e:
        st.error(f"Failed to load: {e}")
        st.stop()

# ── Compute indicators ─────────────────────────────────────────────────────
df = df.copy()
df["SMA50"] = df["Close"].rolling(50).mean()
df["SMA200"] = df["Close"].rolling(200).mean()

# RSI (14)
delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss.replace(0, float("nan"))
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9).mean()
df["Hist"] = df["MACD"] - df["Signal"]

# ── Price Chart ────────────────────────────────────────────────────────────
st.subheader("Price + Moving Averages")

import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.55, 0.22, 0.23],
    vertical_spacing=0.04,
    subplot_titles=["Price & SMAs", "RSI (14)", "MACD"],
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        showlegend=True,
    ),
    row=1,
    col=1,
)

fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50", line=dict(color="#fb8c00", width=1.5)), row=1, col=1)
fig.add_trace(
    go.Scatter(x=df.index, y=df["SMA200"], name="SMA 200", line=dict(color="#ab47bc", width=1.5)), row=1, col=1
)

# RSI
fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="#42a5f5")), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

# MACD
fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#26c6da")), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal", line=dict(color="#ff7043")), row=3, col=1)
colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["Hist"].fillna(0)]
fig.add_trace(go.Bar(x=df.index, y=df["Hist"], name="Histogram", marker_color=colors, showlegend=False), row=3, col=1)

fig.update_layout(
    height=700,
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(color="#fafafa"),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.02),
)
fig.update_yaxes(gridcolor="#1f2937", zerolinecolor="#374151")
fig.update_xaxes(gridcolor="#1f2937")

st.plotly_chart(fig, use_container_width=True)

# ── Trend Signal ───────────────────────────────────────────────────────────
st.subheader("Trend Signal")

last = df.iloc[-1]
close = last["Close"]
sma50 = last["SMA50"]
sma200 = last["SMA200"]
rsi_val = last["RSI"]
macd_val = last["MACD"]
sig_val = last["Signal"]

signals = []
if not pd.isna(sma50):
    signals.append(1 if close > sma50 else -1)
if not pd.isna(sma200):
    signals.append(1 if close > sma200 else -1)
if not pd.isna(rsi_val):
    signals.append(1 if 40 < rsi_val < 70 else (-1 if rsi_val >= 70 else -1))
if not pd.isna(macd_val) and not pd.isna(sig_val):
    signals.append(1 if macd_val > sig_val else -1)

score = sum(signals)
if score >= 2:
    trend = "Bullish"
    color = "green"
elif score <= -2:
    trend = "Bearish"
    color = "red"
else:
    trend = "Neutral"
    color = "orange"

st.markdown(f"### Trend: :{color}[{trend}]")

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Price vs SMA50",
    f"{'Above' if close > sma50 else 'Below'}" if not pd.isna(sma50) else "N/A",
    delta=f"{(close / sma50 - 1) * 100:+.1f}%" if not pd.isna(sma50) else None,
)
col2.metric(
    "Price vs SMA200",
    f"{'Above' if close > sma200 else 'Below'}" if not pd.isna(sma200) else "N/A",
    delta=f"{(close / sma200 - 1) * 100:+.1f}%" if not pd.isna(sma200) else None,
)
col3.metric(
    "RSI (14)",
    f"{rsi_val:.1f}" if not pd.isna(rsi_val) else "N/A",
    delta="Overbought"
    if rsi_val >= 70
    else ("Oversold" if rsi_val <= 30 else "Neutral")
    if not pd.isna(rsi_val)
    else None,
    delta_color="inverse" if not pd.isna(rsi_val) and rsi_val >= 70 else "normal",
)
col4.metric(
    "MACD vs Signal",
    f"{'Bullish' if macd_val > sig_val else 'Bearish'}" if not (pd.isna(macd_val) or pd.isna(sig_val)) else "N/A",
)

st.caption("Trend signal is a simple heuristic combining 4 indicators. Not financial advice.")
