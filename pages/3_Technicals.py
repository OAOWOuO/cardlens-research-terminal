"""
Technicals — SMA 20/50/200, RSI, rolling volatility, max drawdown, trend signal.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

st.set_page_config(page_title="Technicals · CardLens", page_icon="📈", layout="wide")

st.title("📈 Technicals")
st.caption("Price chart · Moving averages · RSI · Rolling volatility · Max drawdown · Trend signal")

TICKER = "MA"
PERIOD_MAP = {"3M": "3mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y"}
period_label = st.selectbox("Chart period", list(PERIOD_MAP.keys()), index=2)
period = PERIOD_MAP[period_label]


@st.cache_data(ttl=900)
def get_hist(per: str) -> pd.DataFrame:
    return yf.Ticker(TICKER).history(period=per)


with st.spinner("Loading price data…"):
    try:
        df = get_hist(period)
        if df.empty:
            st.error("No price data returned.")
            st.stop()
    except Exception as e:
        st.error(f"Failed: {e}")
        st.stop()

df = df.copy()

# ── Indicators ────────────────────────────────────────────────────────────────
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()
df["SMA200"] = df["Close"].rolling(200).mean()

# RSI 14
delta = df["Close"].diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
df["RSI"] = 100 - 100 / (1 + gain / loss.replace(0, float("nan")))

# Rolling 30-day annualised volatility
df["DailyRet"] = df["Close"].pct_change()
df["RolVol30"] = df["DailyRet"].rolling(30).std() * np.sqrt(252) * 100  # in %

# MACD
ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["MACDSig"] = df["MACD"].ewm(span=9).mean()
df["MACDHist"] = df["MACD"] - df["MACDSig"]

# Max drawdown (running)
roll_max = df["Close"].cummax()
df["Drawdown"] = (df["Close"] - roll_max) / roll_max * 100

# ── Chart ─────────────────────────────────────────────────────────────────────
st.subheader("Price + Moving Averages")

fig = make_subplots(
    rows=4,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.48, 0.18, 0.17, 0.17],
    vertical_spacing=0.03,
    subplot_titles=["Price & SMAs", "RSI (14)", "MACD", "Rolling Vol 30D (Ann.)"],
)

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
    ),
    row=1,
    col=1,
)
for col_name, color, width in [("SMA20", "#ffeb3b", 1.2), ("SMA50", "#fb8c00", 1.5), ("SMA200", "#ab47bc", 1.5)]:
    fig.add_trace(
        go.Scatter(x=df.index, y=df[col_name], name=col_name, line=dict(color=color, width=width)), row=1, col=1
    )

fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="#42a5f5")), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#26c6da")), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["MACDSig"], name="Signal", line=dict(color="#ff7043")), row=3, col=1)
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["MACDHist"],
        name="Hist",
        marker_color=["#26a69a" if v >= 0 else "#ef5350" for v in df["MACDHist"].fillna(0)],
        showlegend=False,
    ),
    row=3,
    col=1,
)

fig.add_trace(
    go.Scatter(x=df.index, y=df["RolVol30"], name="Vol 30D", line=dict(color="#ce93d8"), fill="tozeroy"), row=4, col=1
)

fig.update_layout(
    height=800,
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    font=dict(color="#fafafa"),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", y=1.02),
)
fig.update_yaxes(gridcolor="#1f2937", zerolinecolor="#374151")
fig.update_xaxes(gridcolor="#1f2937")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Key stats ─────────────────────────────────────────────────────────────────
st.subheader("Key Statistics")
last = df.iloc[-1]
close = last["Close"]
sma20 = last["SMA20"]
sma50 = last["SMA50"]
sma200 = last["SMA200"]
rsi_val = last["RSI"]
vol_val = last["RolVol30"]

# 52W high/low
wk52_high = df["High"].max()
wk52_low = df["Low"].min()
pct_from_high = (close - wk52_high) / wk52_high * 100
pct_from_low = (close - wk52_low) / wk52_low * 100

# Max drawdown
max_dd = df["Drawdown"].min()

cols = st.columns(4)
cols[0].metric("Current Price", f"${close:.2f}")
cols[1].metric("52W High", f"${wk52_high:.2f}", delta=f"{pct_from_high:+.1f}% from high", delta_color="inverse")
cols[2].metric("52W Low", f"${wk52_low:.2f}", delta=f"{pct_from_low:+.1f}% from low")
cols[3].metric("Max Drawdown (period)", f"{max_dd:.1f}%")

cols2 = st.columns(4)
cols2[0].metric("RSI (14)", f"{rsi_val:.1f}" if not math.isnan(rsi_val) else "N/A")
cols2[1].metric("30D Ann. Vol", f"{vol_val:.1f}%" if not math.isnan(vol_val) else "N/A")
cols2[2].metric("vs SMA50", f"{(close / sma50 - 1) * 100:+.1f}%" if not math.isnan(sma50) else "N/A")
cols2[3].metric("vs SMA200", f"{(close / sma200 - 1) * 100:+.1f}%" if not math.isnan(sma200) else "N/A")

st.divider()

# ── Trend Signal ──────────────────────────────────────────────────────────────
st.subheader("Technical Signal")
st.caption("Rules-based signal — transparent logic, not financial advice.")

signals = []
rules = []

if not math.isnan(sma20):
    up = close > sma20
    signals.append(1 if up else -1)
    rules.append(("Price vs SMA20", "Above" if up else "Below", "✅" if up else "⚠️"))
if not math.isnan(sma50):
    up = close > sma50
    signals.append(1 if up else -1)
    rules.append(("Price vs SMA50", "Above" if up else "Below", "✅" if up else "⚠️"))
if not math.isnan(sma200):
    up = close > sma200
    signals.append(1 if up else -1)
    rules.append(("Price vs SMA200", "Above" if up else "Below", "✅" if up else "⚠️"))
if not math.isnan(rsi_val):
    if 40 < rsi_val < 65:
        signals.append(1)
        rules.append(("RSI", f"{rsi_val:.1f} — constructive zone (40–65)", "✅"))
    elif rsi_val >= 70:
        signals.append(-1)
        rules.append(("RSI", f"{rsi_val:.1f} — overbought (≥70)", "⚠️"))
    else:
        signals.append(0)
        rules.append(("RSI", f"{rsi_val:.1f} — oversold/neutral (≤40)", "🔵"))
if not math.isnan(last["MACD"]) and not math.isnan(last["MACDSig"]):
    up = last["MACD"] > last["MACDSig"]
    signals.append(1 if up else -1)
    rules.append(("MACD vs Signal", "Bullish crossover" if up else "Bearish crossover", "✅" if up else "⚠️"))

score = sum(signals)
if score >= 3:
    trend, color = "Bullish", "green"
elif score <= -3:
    trend, color = "Bearish", "red"
else:
    trend, color = "Neutral", "orange"

st.markdown(f"## Overall Trend: :{color}[**{trend}**]  (score {score:+d} / {len(signals)} signals)")

for name, detail, icon in rules:
    st.markdown(f"{icon} **{name}**: {detail}")

st.caption(
    "Signal logic: +1 for each bullish condition, -1 for bearish. "
    "≥3 → Bullish · ≤-3 → Bearish · otherwise Neutral. "
    "This is a heuristic summary, not a trading recommendation."
)
