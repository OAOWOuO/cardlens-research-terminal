"""
Case-grounded Q&A with strict RAG grounding, citations, and multi-turn memory.
"""

from __future__ import annotations

import os

from openai import OpenAI

from src.retrieval import retrieve

SYSTEM_PROMPT = """You are a financial analyst assistant for Mastercard (NYSE: MA) — MGMT690 MBA case study.

CRITICAL RULE: Answer ONLY using the case document excerpts provided in this message.
If the answer is not found in the excerpts, say exactly: "This information is not in the case documents I have access to."
Do not fabricate data, invent numbers, or draw on knowledge beyond the provided excerpts.

When you use information from an excerpt, cite it explicitly (e.g., "Per the Agent Suite PR, ...").
Be direct and concise — bullet points preferred. Maximum 150 words unless the question requires more detail.
"""


def answer_question(
    question: str,
    top_k: int = 5,
    model: str = "gpt-4o-mini",
    history: list[dict] | None = None,
) -> dict:
    """
    Answer a question using strict RAG grounding with optional multi-turn history.

    Args:
        question: The user's question.
        top_k: Number of chunks to retrieve.
        model: OpenAI model name.
        history: Prior conversation turns as [{"role": "user"/"assistant", "content": str}, ...].

    Returns:
        {
            "answer": str,
            "citations": list[str],
            "excerpts": list[dict],   # each has citation, source_title, source_url, text, score
            "no_index": bool,
        }
    """
    chunks = retrieve(question, top_k=top_k)

    if chunks:
        excerpts_text = ""
        for i, c in enumerate(chunks, start=1):
            excerpts_text += f"\n--- Excerpt {i} {c['citation']} ---\n{c['text']}\n"
        citations = list({c["citation"] for c in chunks})
        no_index = False
    else:
        excerpts_text = "No case document excerpts are available."
        citations = []
        no_index = True

    user_msg = (
        f"Case document excerpts for context:\n{excerpts_text}\n\n"
        f"Question: {question}\n\n"
        "Answer strictly from the excerpts above. Cite sources explicitly."
    )

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "answer": "⚠️ OpenAI API key not configured. Add OPENAI_API_KEY to Streamlit secrets or .env.",
            "citations": citations,
            "excerpts": [
                {
                    "citation": c["citation"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "text": c["text"],
                    "score": c["score"],
                }
                for c in chunks
            ],
            "no_index": no_index,
        }

    # Build message list: system → prior history → current question+context
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_msg})

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=500,
    )

    answer = response.choices[0].message.content.strip()

    return {
        "answer": answer,
        "citations": citations,
        "excerpts": [
            {
                "citation": c["citation"],
                "source_title": c["source_title"],
                "source_url": c["source_url"],
                "text": c["text"],
                "score": c["score"],
            }
            for c in chunks
        ],
        "no_index": no_index,
    }
