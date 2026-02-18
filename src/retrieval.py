"""
Cosine-similarity retrieval over the document index.
"""

from __future__ import annotations

import os

import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

from src.embeddings import EMBED_MODEL, load_index

DEFAULT_TOP_K = 5


def _embed_query(query: str) -> np.ndarray:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(model=EMBED_MODEL, input=[query])
    return np.array(response.data[0].embedding, dtype=np.float32).reshape(1, -1)


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Retrieve top_k relevant chunks. Returns list of dicts with keys:
    chunk_id, filename, page, text, score, citation
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
        citation = f"[Source: {m['filename']}{page_str}]"
        results.append(
            {
                "chunk_id": m["chunk_id"],
                "filename": m["filename"],
                "page": m["page"],
                "text": m["text"],
                "score": float(scores[idx]),
                "citation": citation,
            }
        )
    return results
