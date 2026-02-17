"""
Case-grounded Q&A with citations. Answers ONLY from retrieved chunks.
"""
from __future__ import annotations

import os

from openai import OpenAI

from src.retrieval import retrieve

SYSTEM_PROMPT = """You are a financial research assistant for the Mastercard case (MGMT690).
Your role is to answer questions using ONLY the provided case document excerpts below.

Rules:
1. Answer ONLY using information from the provided excerpts.
2. If the excerpts do not contain enough information, say exactly: "Not found in provided case materials."
3. Always cite the source(s) you used, using the citation tag provided per excerpt.
4. Be concise and factual. Do not hallucinate or add external knowledge.
"""


def answer_question(question: str, top_k: int = 5, model: str = "gpt-4o-mini") -> dict:
    """
    Answer a question using RAG.

    Returns:
        {
            "answer": str,
            "citations": list[str],
            "excerpts": list[dict],   # chunk text + citation
            "no_index": bool,         # True if index doesn't exist
        }
    """
    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return {
            "answer": "No document index found. Please rebuild the index from the Sources page.",
            "citations": [],
            "excerpts": [],
            "no_index": True,
        }

    excerpts_text = ""
    for i, c in enumerate(chunks, start=1):
        excerpts_text += f"\n--- Excerpt {i} {c['citation']} ---\n{c['text']}\n"

    user_msg = f"""Question: {question}

Provided excerpts:
{excerpts_text}

Answer (cite sources inline):"""

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=800,
    )

    answer = response.choices[0].message.content.strip()
    citations = [c["citation"] for c in chunks]

    return {
        "answer": answer,
        "citations": citations,
        "excerpts": [{"citation": c["citation"], "text": c["text"], "score": c["score"]} for c in chunks],
        "no_index": False,
    }
