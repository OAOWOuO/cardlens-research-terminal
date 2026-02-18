"""
Generate and persist embeddings for chunked documents.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from openai import OpenAI

from src.ingest import CHUNKS_FILE, load_chunks

INDEX_DIR = Path(__file__).parent.parent / "data" / "index"
EMBEDDINGS_FILE = INDEX_DIR / "embeddings.npz"
META_FILE = INDEX_DIR / "meta.json"
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


def _client() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _embed_batch(texts: list[str], client: OpenAI) -> list[list[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in response.data]


def build_index(chunks_file: Path = CHUNKS_FILE) -> int:
    """Build embedding index from chunks. Returns number of embeddings."""
    chunks = load_chunks(chunks_file)
    if not chunks:
        return 0

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    client = _client()

    all_vectors: list[list[float]] = []
    meta: list[dict] = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        vectors = _embed_batch(texts, client)
        all_vectors.extend(vectors)
        for c in batch:
            meta.append(
                {
                    "chunk_id": c["chunk_id"],
                    "filename": c["filename"],
                    "page": c["page"],
                    "text": c["text"],
                }
            )

    arr = np.array(all_vectors, dtype=np.float32)
    np.savez_compressed(EMBEDDINGS_FILE, embeddings=arr)
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(meta)


def load_index() -> tuple[np.ndarray | None, list[dict]]:
    """Load existing index. Returns (embeddings_array, meta_list) or (None, [])."""
    if not EMBEDDINGS_FILE.exists() or not META_FILE.exists():
        return None, []
    data = np.load(EMBEDDINGS_FILE)
    arr = data["embeddings"]
    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    return arr, meta


if __name__ == "__main__":
    n = build_index()
    print(f"Built index with {n} embeddings -> {EMBEDDINGS_FILE}")
