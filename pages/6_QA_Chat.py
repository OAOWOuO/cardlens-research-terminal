"""
AI Research Chat — grounded in case documents with citations.
Ask anything about Mastercard, Agent Suite, Cloudflare partnership, 10-K.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

st.set_page_config(page_title="AI Chat · CardLens", page_icon="💬", layout="wide")

st.title("💬 AI Research Chat")
st.caption(
    "Answers grounded in case documents (Agent Suite PR · Cloudflare PR · Mastercard 10-K). "
    "Every answer cites its source."
)

# ── Index status indicator ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
index_file = PROJECT_ROOT / "data" / "index" / "embeddings.npz"
raw_dir = PROJECT_ROOT / "data" / "raw"
n_docs = len([f for f in raw_dir.iterdir() if f.suffix in {".txt", ".pdf", ".md"}]) if raw_dir.exists() else 0

if index_file.exists():
    st.success(f"Document index ready — {n_docs} documents indexed. Ask anything below.", icon="✅")
else:
    st.warning(
        "No document index found. Go to **Home** → click **Fetch & Index Documents** first.",
        icon="⚠️",
    )

st.divider()

# ── Suggested question chips ──────────────────────────────────────────────────
st.markdown("**Quick questions — click to ask:**")
suggested = [
    "What is Mastercard Agent Suite and why does it matter?",
    "What are the key terms of the Cloudflare partnership?",
    "What are Mastercard's main revenue drivers from the 10-K?",
    "What are the top risks facing Mastercard?",
    "How does Agent Suite create a new monetization model?",
    "What does the 10-K say about Mastercard's competitive position?",
    "What is Mastercard's strategy for value-added services?",
    "How significant is cross-border volume to Mastercard's revenue?",
]

cols = st.columns(4)
for i, q in enumerate(suggested):
    if cols[i % 4].button(q, use_container_width=True, key=f"chip_{i}"):
        st.session_state["pending_question"] = q

st.divider()

# ── Settings ──────────────────────────────────────────────────────────────────
with st.expander("⚙️ Chat settings", expanded=False):
    show_excerpts = st.toggle("Show retrieved document excerpts", value=False)
    top_k = st.slider("Documents retrieved per answer", 3, 8, 5)
    model = st.selectbox("LLM model", ["gpt-4o-mini", "gpt-4o"], index=0)

# ── Chat history init ─────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Display chat history ──────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            st.markdown("**Sources used:** " + " · ".join(set(msg["citations"])))
        if show_excerpts and msg["role"] == "assistant" and msg.get("excerpts"):
            with st.expander("📄 Retrieved excerpts"):
                for ex in msg["excerpts"]:
                    st.markdown(f"**{ex['citation']}** — relevance score: `{ex['score']:.3f}`")
                    st.text(ex["text"][:500] + ("…" if len(ex["text"]) > 500 else ""))
                    st.divider()

# ── Handle pending chip question ──────────────────────────────────────────────
prompt = st.chat_input("Ask about the Mastercard case, Agent Suite, Cloudflare partnership, 10-K…")
if not prompt and "pending_question" in st.session_state:
    prompt = st.session_state.pop("pending_question")

# ── Process question ──────────────────────────────────────────────────────────
if prompt:
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching case documents…"):
            try:
                from src.qa import answer_question

                result = answer_question(prompt, top_k=top_k, model=model)
            except Exception as e:
                result = {
                    "answer": f"Error running QA: {e}",
                    "citations": [],
                    "excerpts": [],
                    "no_index": True,
                }

        st.markdown(result["answer"])

        if result.get("citations"):
            st.markdown("**Sources used:** " + " · ".join(set(result["citations"])))

        if show_excerpts and result.get("excerpts"):
            with st.expander("📄 Retrieved excerpts"):
                for ex in result["excerpts"]:
                    st.markdown(f"**{ex['citation']}** — score: `{ex['score']:.3f}`")
                    st.text(ex["text"][:500] + ("…" if len(ex["text"]) > 500 else ""))
                    st.divider()

        if result.get("no_index"):
            st.error("No document index. Go to **Home** → **Fetch & Index Documents**.")

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "citations": result.get("citations", []),
            "excerpts": result.get("excerpts", []),
        }
    )

# ── Clear button ──────────────────────────────────────────────────────────────
if st.session_state.chat_history:
    if st.button("🗑 Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()

st.divider()
st.caption(
    "Answers are generated by GPT-4o-mini using ONLY the indexed case documents. "
    "If a question cannot be answered from the documents, the model says so. "
    "This is not financial advice."
)
