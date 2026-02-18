"""
Fetch public Mastercard case documents from web and save to data/raw/.
Sources: Mastercard Newsroom, Cloudflare, SEC EDGAR 10-K.
"""

from __future__ import annotations

import re
import time
import warnings
from pathlib import Path

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

HEADERS = {
    "User-Agent": ("CardLens-Research-Terminal/1.0 (MGMT690 Academic Research; educational use only)"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SOURCES = [
    {
        "filename": "01_mastercard_agent_suite.txt",
        "url": "https://www.mastercard.com/us/en/news-and-trends/press/2026/january/mastercard-launches-agent-suite-to-ready-enterprises-for-a-new-e.html",
        "title": "Mastercard Agent Suite Launch — Official Press Release (January 2026)",
        "selectors": ["article", ".press-detail", ".content-body", "main", "body"],
        "max_chars": None,
    },
    {
        "filename": "02_cloudflare_mastercard_cyber.txt",
        "url": "https://www.cloudflare.com/press/press-releases/2026/cloudflare-and-mastercard-partner-to-extend-comprehensive-cyber-defense/",
        "title": "Cloudflare × Mastercard Cyber Defense Partnership — Press Release (2026)",
        "selectors": ["article", ".press-release-body", "main", ".content", "body"],
        "max_chars": None,
    },
    {
        "filename": "03_cloudflare_mastercard_agentic.txt",
        "url": "https://www.cloudflare.com/press/press-releases/2025/cloudflare-collaborates-with-leading-payments-companies-to-secure-and-enable-agentic-commerce/",
        "title": "Cloudflare × Mastercard Agentic Commerce Collaboration — Press Release (2025)",
        "selectors": ["article", ".press-release-body", "main", ".content", "body"],
        "max_chars": None,
    },
    {
        "filename": "04_mastercard_10k_2024.txt",
        "url": "https://www.sec.gov/Archives/edgar/data/1141391/000114139125000011/ma-20241231.htm",
        "title": "Mastercard 10-K Annual Report FY2024 (SEC EDGAR)",
        "selectors": ["body"],
        "max_chars": 250_000,  # First 250k chars covers Business + Risk Factors + MD&A
    },
]


def _clean_text(raw: str) -> str:
    """Normalize whitespace in extracted text."""
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]{2,}", " ", raw)
    return raw.strip()


def _extract_text(html: str, selectors: list[str]) -> str:
    """Extract main body text from HTML, removing boilerplate."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    for sel in selectors:
        el = soup.select_one(sel)
        if el and len(el.get_text(strip=True)) > 200:
            return _clean_text(el.get_text(separator="\n", strip=True))

    return _clean_text(soup.get_text(separator="\n", strip=True))


def fetch_one(source: dict, timeout: int = 20) -> tuple[bool, str]:
    """Fetch one source. Returns (success, message)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / source["filename"]
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        text = _extract_text(resp.text, source["selectors"])
        if source["max_chars"]:
            text = text[: source["max_chars"]]
        # Prepend metadata header for RAG citation
        header = (
            f"TITLE: {source['title']}\n"
            f"SOURCE URL: {source['url']}\n"
            f"FETCHED: {time.strftime('%Y-%m-%d')}\n"
            f"{'=' * 60}\n\n"
        )
        out_path.write_text(header + text, encoding="utf-8")
        return True, f"Saved {source['filename']} ({len(text):,} chars)"
    except Exception as e:
        return False, f"Failed {source['filename']}: {e}"


def fetch_all() -> list[dict]:
    """Fetch all sources. Returns list of {filename, success, message}."""
    results = []
    for src in SOURCES:
        ok, msg = fetch_one(src)
        results.append({"filename": src["filename"], "title": src["title"], "success": ok, "message": msg})
        time.sleep(1)  # Polite delay between requests
    return results


if __name__ == "__main__":
    for r in fetch_all():
        status = "✓" if r["success"] else "✗"
        print(f"{status} {r['message']}")
