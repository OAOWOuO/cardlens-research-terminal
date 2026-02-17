"""
Ingest PDF/TXT/MD files from data/raw into chunked JSONL for RAG.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import pdfplumber
import tiktoken

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
CHUNKS_FILE = PROCESSED_DIR / "chunks.jsonl"

CHUNK_TOKENS = 900
OVERLAP_TOKENS = 150
ENCODING = "cl100k_base"


def _tokenizer() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING)


def _chunk_text(text: str, filename: str, page: int | None) -> Iterator[dict]:
    enc = _tokenizer()
    tokens = enc.encode(text)
    chunk_id = 0
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        yield {
            "chunk_id": f"{filename}::p{page}::c{chunk_id}" if page is not None else f"{filename}::c{chunk_id}",
            "filename": filename,
            "page": page,
            "text": chunk_text,
        }
        chunk_id += 1
        start += CHUNK_TOKENS - OVERLAP_TOKENS
        if end == len(tokens):
            break


def _load_pdf(path: Path) -> Iterator[dict]:
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue
            yield from _chunk_text(text, path.name, page_num)


def _load_text(path: Path) -> Iterator[dict]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if text:
        yield from _chunk_text(text, path.name, None)


def ingest_all(raw_dir: Path = RAW_DIR, out_file: Path = CHUNKS_FILE) -> int:
    """Ingest all documents; return number of chunks written."""
    out_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_file.open("w", encoding="utf-8") as fout:
        for fpath in sorted(raw_dir.iterdir()):
            if fpath.suffix.lower() == ".pdf":
                chunks = list(_load_pdf(fpath))
            elif fpath.suffix.lower() in {".txt", ".md"}:
                chunks = list(_load_text(fpath))
            else:
                continue
            for chunk in chunks:
                fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                count += 1
    return count


def load_chunks(chunks_file: Path = CHUNKS_FILE) -> list[dict]:
    """Load existing chunks from JSONL."""
    if not chunks_file.exists():
        return []
    chunks = []
    with chunks_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


if __name__ == "__main__":
    n = ingest_all()
    print(f"Ingested {n} chunks -> {CHUNKS_FILE}")
