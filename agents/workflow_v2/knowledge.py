from __future__ import annotations

from collections import Counter
import json
import re
from typing import Any

KNOWLEDGE_PROMPT = """Bạn là một trợ lý thông minh. Hãy trả lời câu hỏi dưới đây.

Câu hỏi:
{question}

Các lựa chọn:
{options_text}

Hãy suy nghĩ từng bước, sau đó trả lời theo đúng format:
ANSWER: <chữ cái đáp án, ví dụ A hoặc B hoặc C hoặc D>
CONFIDENCE: <số từ 0.0 đến 1.0>
"""


def row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def build_knowledge_prompt(question: str, options: dict[str, Any]) -> str:
    options_text = json.dumps(options, ensure_ascii=False)
    return KNOWLEDGE_PROMPT.format(question=question, options_text=options_text)


def extract_answer(response: str) -> str | None:
    match = re.search(r"ANSWER:\s*([A-Ja-j])", response or "")
    return match.group(1).upper() if match else None


def extract_self_confidence(response: str) -> float:
    match = re.search(r"CONFIDENCE:\s*([\d.]+)", response or "")
    if not match:
        return 0.5
    try:
        return max(0.0, min(1.0, float(match.group(1))))
    except ValueError:
        return 0.5


def consistency_score(answers: list[str]) -> float:
    if not answers:
        return 0.0
    return Counter(answers).most_common(1)[0][1] / len(answers)


def majority_vote(answers: list[str]) -> str | None:
    if not answers:
        return None
    return Counter(answers).most_common(1)[0][0]


def solve_knowledge(text: str, row: dict[str, Any], call_llm_fn, n_samples: int = 3) -> dict:
    prompt = build_knowledge_prompt(text, row_options(row))
    answers = []
    self_confs = []
    for _ in range(n_samples):
        response = call_llm_fn(prompt, temperature=0.7)
        answer = extract_answer(response)
        if answer:
            answers.append(answer)
            self_confs.append(extract_self_confidence(response))
    best_answer = majority_vote(answers)
    avg_self_conf = sum(self_confs) / len(self_confs) if self_confs else 0.5
    final_conf = round(0.7 * consistency_score(answers) + 0.3 * avg_self_conf, 2)
    return {"answer": best_answer, "confidence": final_conf, "votes": dict(Counter(answers)), "n_samples": len(answers)}
