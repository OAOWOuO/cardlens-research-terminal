"""
Case-grounded Q&A Chat with citations.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

st.set_page_config(page_title="Q&A Chat · CardLens", page_icon="💬", layout="wide")

st.title("💬 Case Q&A Chat")
st.caption("Answers grounded in your case documents with citations. No hallucination — sources only.")

show_excerpts = st.toggle("Show retrieved excerpts", value=False)

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display existing messages
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("citations"):
            st.markdown("**Sources:** " + " · ".join(msg["citations"]))
        if show_excerpts and msg["role"] == "assistant" and msg.get("excerpts"):
            with st.expander("Retrieved excerpts"):
                for ex in msg["excerpts"]:
                    st.markdown(f"**{ex['citation']}** (score: {ex['score']:.3f})")
                    st.text(ex["text"][:600] + ("…" if len(ex["text"]) > 600 else ""))

# Chat input
if prompt := st.chat_input("Ask about the Mastercard case…"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents…"):
            try:
                from src.qa import answer_question

                result = answer_question(prompt)
            except Exception as e:
                result = {
                    "answer": f"Error: {e}",
                    "citations": [],
                    "excerpts": [],
                    "no_index": True,
                }

        st.markdown(result["answer"])

        if result["citations"]:
            st.markdown("**Sources:** " + " · ".join(result["citations"]))

        if show_excerpts and result.get("excerpts"):
            with st.expander("Retrieved excerpts"):
                for ex in result["excerpts"]:
                    st.markdown(f"**{ex['citation']}** (score: {ex['score']:.3f})")
                    st.text(ex["text"][:600] + ("…" if len(ex["text"]) > 600 else ""))

        if result.get("no_index"):
            st.warning(
                "No document index found. Go to **Home** and click **Rebuild Document Index** after placing files in `data/raw/`."
            )

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "citations": result.get("citations", []),
            "excerpts": result.get("excerpts", []),
        }
    )

if st.session_state.chat_history:
    if st.button("Clear chat history"):
        st.session_state.chat_history = []
        st.rerun()
