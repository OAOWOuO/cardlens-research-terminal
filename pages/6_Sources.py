"""
Sources / Document Library page.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import json
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="Sources · CardLens", page_icon="📚", layout="wide")

st.title("📚 Document Library")
st.caption("Case materials used for Q&A grounding (RAG). Files must be in `data/raw/`.")

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
META_FILE = INDEX_DIR / "meta.json"
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"

# ── Document list ──────────────────────────────────────────────────────────
st.subheader("Files in data/raw/")

if not RAW_DIR.exists():
    st.error("`data/raw/` directory not found.")
else:
    raw_files = sorted([
        f for f in RAW_DIR.iterdir()
        if f.suffix.lower() in {".pdf", ".txt", ".md"}
    ])
    if not raw_files:
        st.warning("No PDF/TXT/MD files found in `data/raw/`. Add your case materials there.")
    else:
        rows = []
        for f in raw_files:
            stat = f.stat()
            rows.append({
                "Filename": f.name,
                "Type": f.suffix.upper().lstrip("."),
                "Size": f"{stat.st_size / 1024:.1f} KB",
                "Modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Index status ───────────────────────────────────────────────────────────
st.subheader("Index Status")

col1, col2, col3 = st.columns(3)

if META_FILE.exists():
    meta = json.loads(META_FILE.read_text())
    n_chunks = len(meta)
    mtime = datetime.fromtimestamp(META_FILE.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    col1.metric("Indexed Chunks", n_chunks)
    col2.metric("Last Indexed", mtime)
    unique_files = len(set(m["filename"] for m in meta))
    col3.metric("Unique Files Indexed", unique_files)
else:
    st.info("No index built yet. Click **Rebuild Index** below.")

# ── Rebuild ────────────────────────────────────────────────────────────────
st.divider()
if st.button("🔄 Rebuild Index", use_container_width=False):
    with st.spinner("Ingesting documents…"):
        from src.ingest import ingest_all
        n_c = ingest_all()
    with st.spinner("Building embeddings (this may take a minute for large files)…"):
        from src.embeddings import build_index
        n_e = build_index()
    if n_e == 0:
        st.warning("No chunks to embed. Ensure documents exist in `data/raw/`.")
    else:
        st.success(f"Done — {n_c} chunks ingested, {n_e} embeddings built.")
    st.rerun()

# ── Chunk preview ──────────────────────────────────────────────────────────
if META_FILE.exists():
    st.subheader("Chunk Preview")
    meta = json.loads(META_FILE.read_text())
    if meta:
        filenames = sorted(set(m["filename"] for m in meta))
        selected_file = st.selectbox("Filter by file", ["All"] + filenames)
        filtered = meta if selected_file == "All" else [m for m in meta if m["filename"] == selected_file]

        st.caption(f"Showing first 5 of {len(filtered)} chunks")
        for chunk in filtered[:5]:
            with st.expander(f"{chunk['chunk_id']}"):
                st.text(chunk["text"][:800] + ("…" if len(chunk["text"]) > 800 else ""))
