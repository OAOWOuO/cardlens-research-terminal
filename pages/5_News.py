"""
News page — latest headlines for the ticker via yfinance + RSS fallback.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import yfinance as yf

st.set_page_config(page_title="News · CardLens", page_icon="📰", layout="wide")

st.title("📰 Latest News")

ticker_sym = st.session_state.get("ticker", "MA")
st.caption(f"Ticker: **{ticker_sym}** · Top 10 headlines")


@st.cache_data(ttl=1800)
def fetch_news(sym: str) -> list[dict]:
    t = yf.Ticker(sym)
    try:
        news = t.news or []
        return news[:10]
    except Exception:
        return []


def _rss_fallback(sym: str) -> list[dict]:
    """Fetch news via Google Finance RSS as fallback."""
    import xml.etree.ElementTree as ET

    import requests

    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US"
    try:
        resp = requests.get(url, timeout=8)
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")
        results = []
        for item in items[:10]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            results.append({"title": title, "link": link, "pubDate": pub_date})
        return results
    except Exception:
        return []


with st.spinner("Fetching news…"):
    articles = fetch_news(ticker_sym)

if not articles:
    st.info("No news from yfinance — trying RSS fallback…")
    rss_items = _rss_fallback(ticker_sym)
    if rss_items:
        for item in rss_items:
            st.markdown(f"**[{item['title']}]({item['link']})**")
            if item.get("pubDate"):
                st.caption(item["pubDate"])
            st.divider()
    else:
        st.warning("No news articles found for this ticker. Check ticker symbol or try again later.")
else:
    for article in articles:
        # yfinance news item structure
        title = article.get("title", "No title")
        link = article.get("link") or article.get("url", "#")
        publisher = article.get("publisher", "")
        pub_time = article.get("providerPublishTime")
        thumbnail = None
        if isinstance(article.get("thumbnail"), dict):
            resolutions = article["thumbnail"].get("resolutions", [])
            if resolutions:
                thumbnail = resolutions[0].get("url")

        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"#### [{title}]({link})")
            meta = []
            if publisher:
                meta.append(publisher)
            if pub_time:
                from datetime import datetime, timezone
                try:
                    dt = datetime.fromtimestamp(pub_time, tz=timezone.utc)
                    meta.append(dt.strftime("%Y-%m-%d %H:%M UTC"))
                except Exception:
                    pass
            if meta:
                st.caption(" · ".join(meta))
        with col2:
            if thumbnail:
                st.image(thumbnail, width=100)

        st.divider()

st.caption("News sourced from yfinance (Yahoo Finance). Links open external sites.")
