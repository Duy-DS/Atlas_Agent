"""
Calculator tool: detect câu hỏi tính toán, eval expression, map kết quả vào A/B/C/D.
"""
from __future__ import annotations

import ast
import re

# Detect câu hỏi có chứa biểu thức toán học đơn giản
_CALC_RE = re.compile(
    r"[\d]+\s*[\+\-\*\/\^]\s*[\d]"  # số op số
    r"|=\s*\?|bằng bao nhiêu|bang bao nhieu|tính|tinh",
    re.IGNORECASE,
)

# Extract biểu thức toán (chỉ cho phép số và phép tính cơ bản, không eval code tùy ý)
_EXPR_RE = re.compile(r"([\d]+(?:\.\d+)?(?:\s*[\+\-\*\/\^]\s*[\d]+(?:\.\d+)?)+)")

_SAFE_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
)


def _safe_eval(expr: str) -> float | None:
    """Eval biểu thức toán, chỉ cho phép các node an toàn."""
    expr = expr.replace("^", "**")
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, _SAFE_NODES):
                return None
        return float(eval(compile(tree, "<calc>", "eval")))  # noqa: S307
    except Exception:
        return None


def is_calculation_question(row: dict[str, str]) -> bool:
    question = row.get("question", "")
    return bool(_CALC_RE.search(question))


def try_calculator(row: dict[str, str]) -> str | None:
    """
    Nếu câu hỏi có phép tính, tính kết quả và so với A/B/C/D.
    Trả về đáp án (A/B/C/D) nếu tìm được, None nếu không.
    """
    question = row.get("question", "")
    matches = _EXPR_RE.findall(question)
    if not matches:
        return None

    result = _safe_eval(matches[-1].strip())
    if result is None:
        return None

    for option in ("A", "B", "C", "D"):
        val = row.get(option, "").strip()
        try:
            if abs(float(val) - result) < 1e-9:
                return option
        except (ValueError, TypeError):
            # option là text, không phải số
            continue

    return None
