"""
Cosine-similarity retrieval over the document index.
Each result includes source_title and source_url for citation display.
"""

from __future__ import annotations

import os

import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

from src.embeddings import EMBED_MODEL, load_index

DEFAULT_TOP_K = 5

# Maps committed raw-doc filenames → display metadata
SOURCE_META: dict[str, dict[str, str]] = {
    "01_mastercard_agent_suite.txt": {
        "title": "Mastercard Agent Suite Launch (Jan 2026)",
        "url": "https://newsroom.mastercard.com/press-releases/mastercard-launches-agent-suite-to-power-commerce-in-the-age-of-ai/",
    },
    "02_cloudflare_mastercard_cyber.txt": {
        "title": "Cloudflare × Mastercard Cyber Defense (Feb 2026)",
        "url": "https://www.cloudflare.com/press-releases/2026/cloudflare-and-mastercard-partner-to-extend-comprehensive-cyber-defense-to-businesses-worldwide/",
    },
    "03_cloudflare_mastercard_agentic.txt": {
        "title": "Cloudflare × Mastercard Agentic Commerce (2025)",
        "url": "https://www.cloudflare.com/press-releases/2025/cloudflare-collaborates-with-leading-payments-companies-to-secure-and-enable-agentic-commerce/",
    },
    "04_mastercard_10k_2024.txt": {
        "title": "Mastercard 10-K Annual Report FY2024",
        "url": "https://www.sec.gov/Archives/edgar/data/1141391/000114139125000007/ma-20241231.htm",
    },
}


def _embed_query(query: str) -> np.ndarray:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(model=EMBED_MODEL, input=[query])
    return np.array(response.data[0].embedding, dtype=np.float32).reshape(1, -1)


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Retrieve top_k relevant chunks. Each result dict contains:
      chunk_id, filename, page, text, score, citation, source_title, source_url
    """
    arr, meta = load_index()
    if arr is None or len(meta) == 0:
        return []

    q_vec = _embed_query(query)
    scores = cosine_similarity(q_vec, arr)[0]
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        m = meta[idx]
        page_str = f" p.{m['page']}" if m["page"] is not None else ""
        src = SOURCE_META.get(m["filename"], {})
        source_title = src.get("title", m["filename"])
        source_url = src.get("url", "")
        citation = f"[{source_title}{page_str}]"
        results.append(
            {
                "chunk_id": m["chunk_id"],
                "filename": m["filename"],
                "page": m["page"],
                "text": m["text"],
                "score": float(scores[idx]),
                "citation": citation,
                "source_title": source_title,
                "source_url": source_url,
            }
        )
    return results
