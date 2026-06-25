from __future__ import annotations

from typing import Any

from agents.workflow_v2.calculation import solve_calculation
from agents.workflow_v2.classifier import classify
from agents.workflow_v2.knowledge import solve_knowledge
from agents.workflow_v2.retrieval import solve_retrieval


def run_pipeline(text: str, row: dict[str, Any], call_llm_fn) -> dict:
    task = classify(text, row)
    if task == "retrieval":
        result = solve_retrieval(text, row, call_llm_fn)
    elif task == "calculation":
        result = solve_calculation(text, row, call_llm_fn)
    else:
        result = solve_knowledge(text, row, call_llm_fn)
    return {"task": task, "answer": result.get("answer"), "confidence": result.get("confidence", 0.0), "detail": result}
