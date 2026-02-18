"""
AI Research Chat — strictly grounded in case documents with citations and source URLs.
Multi-turn conversational memory: follow-up questions understand prior context.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import os

import streamlit as st

try:
    for _k in ["OPENAI_API_KEY"]:
        if _k in st.secrets:
            os.environ[_k] = st.secrets[_k]
except Exception:
    pass

st.set_page_config(page_title="AI Chat · CardLens", page_icon="💬", layout="wide")

st.title("💬 AI Research Chat")
st.caption(
    "Strictly grounded in case documents (Agent Suite PR · Cloudflare PR · Mastercard 10-K). "
    "Every answer cites its source. Follow-up questions remember prior context."
)

st.success(
    "Ask anything about the Mastercard case — Agent Suite, Cloudflare partnership, 10-K financials, risks.",
    icon="✅",
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
        if msg["role"] == "assistant" and msg.get("excerpts"):
            with st.expander("📄 Sources used"):
                seen = set()
                for ex in msg["excerpts"]:
                    title = ex.get("source_title", ex.get("citation", "Source"))
                    url = ex.get("source_url", "")
                    key = title
                    if key not in seen:
                        seen.add(key)
                        if url:
                            st.markdown(f"**[{title}]({url})**")
                        else:
                            st.markdown(f"**{title}**")
                    if show_excerpts:
                        snippet = ex["text"][:400] + ("…" if len(ex["text"]) > 400 else "")
                        st.caption(f"Relevance: {ex['score']:.3f}")
                        st.text(snippet)
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

                # Pass prior conversation history for multi-turn context
                prior = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history[:-1]  # exclude current user msg
                ]
                result = answer_question(prompt, top_k=top_k, model=model, history=prior or None)
            except Exception as e:
                result = {
                    "answer": f"Error running Q&A: {e}",
                    "citations": [],
                    "excerpts": [],
                    "no_index": True,
                }

        st.markdown(result["answer"])

        # Sources expander — always shown when excerpts exist
        if result.get("excerpts"):
            with st.expander("📄 Sources used"):
                seen: set[str] = set()
                for ex in result["excerpts"]:
                    title = ex.get("source_title", ex.get("citation", "Source"))
                    url = ex.get("source_url", "")
                    key = title
                    if key not in seen:
                        seen.add(key)
                        if url:
                            st.markdown(f"**[{title}]({url})**")
                        else:
                            st.markdown(f"**{title}**")
                    if show_excerpts:
                        snippet = ex["text"][:400] + ("…" if len(ex["text"]) > 400 else "")
                        st.caption(f"Relevance: {ex['score']:.3f}")
                        st.text(snippet)
                        st.divider()

        if result.get("no_index"):
            st.warning("Could not load document index. Ensure data/index/embeddings.npz is present.")

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
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
    "Answers are generated strictly from the indexed case documents. "
    "If a question cannot be answered from the documents, the model will say so. "
    "Follow-up questions retain context from the full conversation. "
    "This is not financial advice."
)
