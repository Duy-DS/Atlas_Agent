"""
Calculator tool: detect câu hỏi tính toán, eval expression, map kết quả vào A/B/C/D.
Hỗ trợ: biểu thức số học + phương trình tuyến tính một ẩn (ax + b = c).
"""
from __future__ import annotations

import ast
import re

# Detect câu hỏi có chứa biểu thức toán học đơn giản
_CALC_RE = re.compile(
    r"[\d]+\s*[\+\-\*\/\^]\s*[\d]"         # số op số: 3+4, 2^10
    r"|\d*x\s*[\+\-\=]"                      # phương trình ẩn x: 2x+, x-, x=
    r"|=\s*\?|bằng bao nhiêu|bang bao nhieu|tính|tinh",
    re.IGNORECASE,
)

# Extract biểu thức toán (chỉ cho phép số và phép tính cơ bản, không eval code tùy ý)
_EXPR_RE = re.compile(r"([\d]+(?:\.\d+)?(?:\s*[\+\-\*\/\^]\s*[\d]+(?:\.\d+)?)+)")

# Phương trình tuyến tính: ax + b = c hoặc x + b = c hoặc ax = c
# Nhóm: (hệ số x)(b)(c) với dấu
_LINEAR_RE = re.compile(
    r"([\-\+]?\s*\d*\.?\d*)\s*x\s*([\+\-]\s*\d+\.?\d*)?\s*=\s*([\-\+]?\s*\d+\.?\d*)",
    re.IGNORECASE,
)

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


def _solve_linear(question: str) -> float | None:
    """Giải phương trình tuyến tính ax + b = c, trả về x."""
    m = _LINEAR_RE.search(question)
    if not m:
        return None
    a_str, b_str, c_str = m.group(1), m.group(2), m.group(3)
    try:
        a = float(a_str.replace(" ", "") or "1")
        if a == 0:
            a = 1.0
        b = float(b_str.replace(" ", "")) if b_str else 0.0
        c = float(c_str.replace(" ", ""))
        return (c - b) / a
    except (ValueError, ZeroDivisionError):
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

    # Thử phương trình tuyến tính trước (có ẩn x)
    result = _solve_linear(question)

    # Nếu không phải phương trình, thử biểu thức số học
    if result is None:
        matches = _EXPR_RE.findall(question)
        if matches:
            result = _safe_eval(matches[-1].strip())

    if result is None:
        return None

    for option in ("A", "B", "C", "D"):
        val = row.get(option, "").strip()
        try:
            if abs(float(val) - result) < 1e-9:
                return option
        except (ValueError, TypeError):
            continue

    return None
