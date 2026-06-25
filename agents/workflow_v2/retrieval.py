from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any

RERANK_MODEL_NAME = os.getenv("RERANK_MODEL_NAME", "dengcao/Qwen3-Reranker-4B:Q4_K_M")
RERANK_PROMPT = """<Instruct>: Đánh giá mức độ liên quan giữa Document và Query trên thang điểm từ 0.0 (không liên quan) đến 1.0 (rất liên quan).
<Query>: {query}
<Document>: {document}

Chỉ trả lời đúng một số thực từ 0.0 đến 1.0, không giải thích gì thêm.
Score:"""

_rerank_client = None


def _get_rerank_client():
    global _rerank_client
    if _rerank_client is None:
        import ollama

        _rerank_client = ollama.Client(host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    return _rerank_client


def _parse_score(text: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+", text or "")
    if not match:
        return None
    try:
        return max(0.0, min(1.0, float(match.group())))
    except ValueError:
        return None


def model_rerank_score(query: str, document: str) -> float | None:
    """Score relevance of a document to a query using the local Ollama reranker model."""
    try:
        client = _get_rerank_client()
        response = client.chat(
            model=RERANK_MODEL_NAME,
            messages=[{"role": "user", "content": RERANK_PROMPT.format(query=query, document=document)}],
            options={"temperature": 0.0, "num_predict": 8},
            think=False,
        )
        return _parse_score(response["message"]["content"])
    except Exception:
        return None


def parse_retrieval_input(text: str) -> tuple[str, str]:
    parts = (text or "").split("Câu hỏi:", 1)
    context = parts[0].replace("Đoạn thông tin:", "", 1).strip()
    question = parts[1].strip() if len(parts) > 1 else ""
    return context, question


def chunk_context(context: str, min_len: int = 20) -> list[str]:
    return [chunk.strip() for chunk in (context or "").split("\n\n") if len(chunk.strip()) >= min_len]


def _fallback_scores(question: str, chunks: list[str]) -> list[float]:
    q_tokens = Counter(question.lower().split())
    scores = []
    for chunk in chunks:
        c_tokens = Counter(chunk.lower().split())
        scores.append(float(sum(min(q_tokens[token], c_tokens[token]) for token in q_tokens)))
    return scores


def bm25_retrieve(question: str, chunks: list[str], top_k: int = 10) -> list[str]:
    if not chunks:
        return []
    top_k = min(top_k, len(chunks))
    try:
        from rank_bm25 import BM25Okapi

        tokenized = [chunk.split() for chunk in chunks]
        scores = BM25Okapi(tokenized).get_scores(question.split())
    except Exception:
        scores = _fallback_scores(question, chunks)
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    return [chunks[index] for index, _ in ranked[:top_k]]


def rerank(question: str, candidates: list[str], top_n: int = 3, score_fn=None) -> list[str]:
    """Rerank BM25 candidates with a cross-encoder reranker model.

    Skips the model call when there is nothing to reorder (<= top_n candidates),
    which keeps small-context callers (and unit tests) fast and deterministic.
    Falls back to BM25 order on score failure (stable sort + score=0.0 default).
    """
    if len(candidates) <= top_n:
        return candidates[:top_n]
    score_fn = score_fn or model_rerank_score
    scored = [(score_fn(question, candidate) or 0.0, candidate) for candidate in candidates]
    ranked = sorted(scored, key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in ranked[:top_n]]


def build_retrieval_context(top_chunks: list[str]) -> str:
    return "\n\n".join(f"[Chunk {index + 1}]\n{chunk}" for index, chunk in enumerate(top_chunks))


def row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def build_retrieval_prompt(context: str, question: str, options: dict[str, Any] | None = None) -> str:
    options = options or {}
    options_text = json.dumps(options, ensure_ascii=False) if options else ""
    options_block = f"\nCác lựa chọn:\n{options_text}\n" if options_text else ""
    answer_instruction = (
        "Chỉ trả lời bằng đúng một chữ cái đáp án (A, B, C hoặc D) dựa trên đoạn thông tin trên."
        if options_text
        else "Hãy trả lời câu hỏi dựa trên đoạn thông tin trên."
    )
    return f"""Dựa vào đoạn thông tin dưới đây, hãy trả lời câu hỏi.
Chỉ sử dụng thông tin trong đoạn văn, không thêm kiến thức bên ngoài.

Đoạn thông tin:
{context}

Câu hỏi:
{question}
{options_block}
{answer_instruction}
"""


def solve_retrieval(text: str, row: dict[str, Any], call_llm_fn) -> dict:
    context, question = parse_retrieval_input(text)
    chunks = chunk_context(context)
    top10 = bm25_retrieve(question, chunks, top_k=10)
    top3 = rerank(question, top10, top_n=3)
    prompt = build_retrieval_prompt(build_retrieval_context(top3), question, row_options(row))
    return {"answer": call_llm_fn(prompt), "confidence": 0.8}
