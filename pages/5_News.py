"""
News — Mastercard headlines from newsroom RSS + Google News RSS + pinned case PRs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from datetime import datetime, timezone

import feedparser
import streamlit as st

st.set_page_config(page_title="News · CardLens", page_icon="📰", layout="wide")

st.title("📰 Latest News")
st.caption("Mastercard (MA) headlines — official newsroom RSS + Google News · cached 30 min")

NEWS_SOURCES = [
    {"label": "Mastercard Newsroom", "url": "https://newsroom.mastercard.com/feed/"},
    {
        "label": "Google News — Mastercard",
        "url": "https://news.google.com/rss/search?q=Mastercard+MA+stock&hl=en-US&gl=US&ceid=US:en",
    },
]


@st.cache_data(ttl=1800)
def fetch_feed(url: str) -> list[dict]:
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:8]:
            pub = entry.get("published", "") or entry.get("updated", "")
            try:
                ts = entry.get("published_parsed") or entry.get("updated_parsed")
                if ts:
                    pub = datetime(*ts[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                pass
            items.append(
                {
                    "title": entry.get("title", "No title"),
                    "link": entry.get("link", "#"),
                    "published": pub,
                }
            )
        return items
    except Exception as e:
        return [{"title": f"Feed error: {e}", "link": "#", "published": ""}]


# ── Pinned case press releases ────────────────────────────────────────────────
st.subheader("📌 Case Press Releases (Pinned)")
pinned = [
    (
        "Mastercard Launches Agent Suite — Ready Enterprises for a New Era (Jan 2026)",
        "https://www.mastercard.com/us/en/news-and-trends/press/2026/january/mastercard-launches-agent-suite-to-ready-enterprises-for-a-new-e.html",
        "Mastercard.com · January 2026",
    ),
    (
        "Cloudflare × Mastercard — Comprehensive Cyber Defense Partnership (Feb 2026)",
        "https://www.cloudflare.com/press/press-releases/2026/cloudflare-and-mastercard-partner-to-extend-comprehensive-cyber-defense/",
        "Cloudflare · February 2026",
    ),
    (
        "Cloudflare × Mastercard — Agentic Commerce Collaboration (2025)",
        "https://www.cloudflare.com/press/press-releases/2025/cloudflare-collaborates-with-leading-payments-companies-to-secure-and-enable-agentic-commerce/",
        "Cloudflare · 2025",
    ),
]
for title, link, meta in pinned:
    st.markdown(f"**[{title}]({link})**")
    st.caption(meta)
    st.divider()

# ── Live feeds ────────────────────────────────────────────────────────────────
for src in NEWS_SOURCES:
    st.subheader(f"🔗 {src['label']}")
    articles = fetch_feed(src["url"])
    if not articles or (len(articles) == 1 and "error" in articles[0]["title"].lower()):
        st.info(f"No articles from {src['label']} right now — feed may be temporarily unavailable.")
    else:
        for art in articles:
            st.markdown(f"**[{art['title']}]({art['link']})**")
            if art["published"]:
                st.caption(art["published"])
            st.divider()

st.caption("Feeds cached 30 min · Links open external sites · Not financial advice.")
