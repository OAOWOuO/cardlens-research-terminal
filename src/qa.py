"""
Case-grounded Q&A with citations.
Answers use case document RAG + full model knowledge for financial analysis.
"""

from __future__ import annotations

import os

from openai import OpenAI

from src.retrieval import retrieve

SYSTEM_PROMPT = """You are an expert financial analyst and AI research assistant for Mastercard (NYSE: MA).
You are helping MBA students in MGMT690 analyze two landmark case events:
• Mastercard Agent Suite (Jan 2026) — AI-native agentic commerce infrastructure
• Cloudflare × Mastercard partnership (Feb 2026) — Comprehensive cyber-defense for agentic payments

You have access to case documents (excerpts provided below). You may also draw on your broad financial
knowledge to give thorough, analytical answers. Always cite case documents when you use them.
Be specific, data-driven, and insightful — this is for an MBA finance course.
"""


def answer_question(question: str, top_k: int = 5, model: str = "gpt-4o-mini") -> dict:
    """
    Answer a question using RAG + full model knowledge.

    Returns:
        {
            "answer": str,
            "citations": list[str],
            "excerpts": list[dict],
            "no_index": bool,
        }
    """
    chunks = retrieve(question, top_k=top_k)

    if chunks:
        excerpts_text = ""
        for i, c in enumerate(chunks, start=1):
            excerpts_text += f"\n--- Excerpt {i} [{c['citation']}] ---\n{c['text']}\n"
        citations = list({c["citation"] for c in chunks})
        no_index = False
    else:
        excerpts_text = "No case document excerpts available."
        citations = []
        no_index = True

    user_msg = f"""Question: {question}

Case document excerpts:
{excerpts_text}

Please provide a thorough answer. Cite case documents where relevant."""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "answer": "OpenAI API key not configured. Add OPENAI_API_KEY to your environment or Streamlit secrets.",
            "citations": citations,
            "excerpts": [{"citation": c["citation"], "text": c["text"], "score": c["score"]} for c in chunks],
            "no_index": no_index,
        }

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=1000,
    )

    answer = response.choices[0].message.content.strip()

    return {
        "answer": answer,
        "citations": citations,
        "excerpts": [{"citation": c["citation"], "text": c["text"], "score": c["score"]} for c in chunks],
        "no_index": no_index,
    }
