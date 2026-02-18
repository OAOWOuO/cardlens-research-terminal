"""
Smoke tests for CardLens Research Terminal.
Tests that modules import and work gracefully when no data/index exists.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Module import tests ────────────────────────────────────────────────────


def test_import_ingest():
    import src.ingest  # noqa: F401


def test_import_embeddings():
    import src.embeddings  # noqa: F401


def test_import_retrieval():
    import src.retrieval  # noqa: F401


def test_import_qa():
    import src.qa  # noqa: F401


# ── Graceful empty-state tests ─────────────────────────────────────────────


def test_load_chunks_empty(tmp_path):
    """load_chunks returns empty list when no chunks file exists."""
    from src.ingest import load_chunks

    result = load_chunks(tmp_path / "nonexistent.jsonl")
    assert result == []


def test_ingest_empty_dir(tmp_path):
    """ingest_all on empty directory creates 0 chunks, does not crash."""
    from src.ingest import ingest_all

    out = tmp_path / "chunks.jsonl"
    n = ingest_all(raw_dir=tmp_path, out_file=out)
    assert n == 0


def test_load_index_empty(tmp_path, monkeypatch):
    """load_index returns (None, []) when no index files exist."""
    from src import embeddings

    monkeypatch.setattr(embeddings, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
    monkeypatch.setattr(embeddings, "META_FILE", tmp_path / "meta.json")
    arr, meta = embeddings.load_index()
    assert arr is None
    assert meta == []


def test_retrieve_no_index(tmp_path, monkeypatch):
    """retrieve returns empty list when no index is built."""
    from src import embeddings, retrieval

    monkeypatch.setattr(embeddings, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
    monkeypatch.setattr(embeddings, "META_FILE", tmp_path / "meta.json")
    results = retrieval.retrieve("test query")
    assert results == []


def test_qa_no_index(tmp_path, monkeypatch):
    """answer_question returns graceful no_index response when no index exists."""
    from src import embeddings

    monkeypatch.setattr(embeddings, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
    monkeypatch.setattr(embeddings, "META_FILE", tmp_path / "meta.json")
    from src import retrieval

    # Patch retrieval to return empty (simulates missing index)
    monkeypatch.setattr(retrieval, "retrieve", lambda query, top_k=5: [])

    # Patch OpenAI so no real API call is made in CI
    import types

    fake_msg = types.SimpleNamespace(content="Mock answer for testing.")
    fake_choice = types.SimpleNamespace(message=fake_msg)
    fake_response = types.SimpleNamespace(choices=[fake_choice])

    class FakeCompletions:
        def create(self, **kwargs):
            return fake_response

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    import src.qa as qa_mod

    monkeypatch.setattr(qa_mod, "OpenAI", lambda **kwargs: FakeClient())

    from src.qa import answer_question

    result = answer_question("What is Mastercard's moat?")
    assert "no_index" in result
    assert result["no_index"] is True
    assert "answer" in result
    assert result["answer"]  # Should have a message


# ── Chunking sanity test ───────────────────────────────────────────────────


def test_chunk_text_basic():
    """Chunking produces correct structure."""
    from src.ingest import _chunk_text

    text = "Hello world. " * 200  # Short text
    chunks = list(_chunk_text(text, "test.txt", None))
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "filename" in chunk
        assert "text" in chunk
        assert chunk["filename"] == "test.txt"
        assert chunk["page"] is None


def test_chunk_text_with_page():
    """Chunking with page number sets page in metadata."""
    from src.ingest import _chunk_text

    text = "Mastercard operates a global payment network. " * 50
    chunks = list(_chunk_text(text, "case.pdf", 3))
    assert all(c["page"] == 3 for c in chunks)
    assert all("p3" in c["chunk_id"] for c in chunks)
