"""
Case Overview — Mastercard strategic thesis: Agent Suite + Cloudflare partnership.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import streamlit as st

st.set_page_config(page_title="Case Overview · CardLens", page_icon="📌", layout="wide")

st.title("📌 Case Overview")
st.caption("Mastercard (NYSE: MA) · MGMT690 Project 2 · Strategic Platform Evolution")

# ── Thesis ─────────────────────────────────────────────────────────────────
st.markdown(
    """
### Investment Thesis

**Mastercard is transitioning from a pure transaction-fee network to a multi-layered financial
intelligence platform.** Two concurrent strategic developments in 2025–2026 underscore this shift:

1. **Agent Suite** (January 2026) — Mastercard's AI/agentic commerce product that embeds payment
   intelligence directly into autonomous AI agents, positioning MA to capture value as commerce moves
   from human-initiated to AI-initiated transactions.

2. **Cloudflare × Mastercard Cyber Defense Partnership** (February 2026) — A joint offering that
   extends Mastercard's risk and security services to businesses globally via Cloudflare's network,
   diversifying revenue beyond transaction fees into recurring B2B security services.

Together, these moves indicate deliberate **platform diversification**: expanding total addressable
market beyond core payment rails while leveraging MA's existing network effects and data moat.
"""
)

st.divider()

# ── Two case angles ─────────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("🤖 Angle A — Agent Suite")
    st.markdown(
        """
**What it is**: A suite of AI tools that lets enterprises integrate Mastercard's payment and
identity infrastructure into autonomous AI agents — enabling AI to search, decide, and transact
on behalf of users.

**Why it matters**:
- Agentic commerce is projected to be a multi-trillion dollar shift (AI agents making purchases
  autonomously)
- MA's network becomes the *trusted rails* for AI transactions — a structural position competitors
  cannot easily replicate
- New revenue model: per-agent or subscription fees on top of traditional interchange

**Key questions**:
- What share of AI-initiated commerce can MA capture?
- How does Agent Suite pricing compare to core interchange revenue?
- Does this accelerate or cannibalize Visa's similar initiatives?

**Source**: [Mastercard Press Release — January 2026](https://www.mastercard.com/us/en/news-and-trends/press/2026/january/mastercard-launches-agent-suite-to-ready-enterprises-for-a-new-e.html)
"""
    )

with col2:
    st.subheader("🔒 Angle B — Cloudflare Partnership")
    st.markdown(
        """
**What it is**: Mastercard's cyber defense capabilities (via its RiskRecon and threat intelligence
assets) are being distributed through Cloudflare's global network to SMBs and enterprises worldwide.

**Why it matters**:
- Extends MA's security revenue stream to a massive new addressable market (Cloudflare reaches
  millions of businesses)
- Recurring B2B SaaS-like revenue that is counter-cyclical to payment volume
- Reinforces MA's positioning as a *trust infrastructure* company, not just a payment network

**Key questions**:
- What is the revenue split between MA and Cloudflare?
- How material can security services become relative to MA's $25B+ revenue base?
- Does this create a defensible moat or is it easily replicated by Visa/Amex?

**Source**: [Cloudflare Press Release — February 2026](https://www.cloudflare.com/press/press-releases/2026/cloudflare-and-mastercard-partner-to-extend-comprehensive-cyber-defense/)
"""
    )

st.divider()

# ── Timeline ────────────────────────────────────────────────────────────────
st.subheader("📅 Key Event Timeline")

events = [
    ("FY2024 Full Year", "MA reports record net revenue of ~$28.2B (+12% YoY), operating margin ~58%"),
    ("Q4 2024 Earnings", "Gross dollar volume +11% YoY, cross-border volume +20% YoY; strong FCF"),
    ("January 2026", "**Agent Suite launched** — AI/agentic commerce product for enterprises"),
    ("February 2026", "**Cloudflare × MA partnership announced** — cyber defense expansion"),
    (
        "Current",
        "Stock trading near 52-week highs; analysts debate whether platform evolution is priced in",
    ),
]

for date, desc in events:
    st.markdown(f"**{date}** — {desc}")

st.divider()

# ── Key questions ────────────────────────────────────────────────────────────
st.subheader("🔍 Key Analytical Questions")

qs = [
    "What is Mastercard's core revenue model and how are Agent Suite / Cloudflare diversifying it?",
    "How does MA's valuation compare to Visa — does the platform story justify a premium?",
    "What are the primary regulatory and competitive risks to the agentic commerce thesis?",
    "How sustainable is MA's ~58% operating margin as it invests in new platforms?",
    "What does historical price/volume data tell us about market confidence in the thesis?",
]
for i, q in enumerate(qs, 1):
    st.markdown(f"{i}. {q}")

st.divider()

# ── Document status ─────────────────────────────────────────────────────────
st.subheader("📚 Case Document Library")

PROJECT_ROOT = Path(__file__).parent.parent
raw_dir = PROJECT_ROOT / "data" / "raw"
index_file = PROJECT_ROOT / "data" / "index" / "embeddings.npz"

doc_sources = {
    "01_mastercard_agent_suite.txt": "Mastercard Agent Suite Press Release (Jan 2026)",
    "02_cloudflare_mastercard_cyber.txt": "Cloudflare × MA Cyber Defense Press Release (Feb 2026)",
    "03_cloudflare_mastercard_agentic.txt": "Cloudflare × MA Agentic Commerce PR (2025)",
    "04_mastercard_10k_2024.txt": "Mastercard 10-K FY2024 — First 250k chars (Business + MD&A)",
}

rows = []
for fname, label in doc_sources.items():
    fpath = raw_dir / fname
    rows.append(
        {
            "Document": label,
            "Status": "✅ Downloaded" if fpath.exists() else "❌ Not fetched",
            "Size": f"{fpath.stat().st_size / 1024:.0f} KB" if fpath.exists() else "—",
        }
    )

import pandas as pd

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

indexed = "✅ Built" if index_file.exists() else "⚠️ Not built yet"
st.caption(f"Vector index: {indexed} — use **Home → Fetch & Index Documents** to build.")

st.divider()
st.caption(
    "**Disclaimer**: CardLens is an educational research tool for MGMT690. "
    "Nothing on this platform constitutes investment advice. All analysis is for academic purposes only."
)
