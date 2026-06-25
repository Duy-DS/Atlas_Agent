from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any

from agents.workflow_v2.classifier import EXPR_RE, LINEAR_RE

COMPLEX_KEYWORDS = ("xác suất", "probability", "log", "sin", "cos", "tan", "đạo hàm", "tích phân", "lãi suất", "tổ hợp", "chỉnh hợp")

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

WORD_PROBLEM_PROMPT = """You are a calculation engine. Solve the math problem step by step.

Output EXACTLY one line at the end:
result = <numeric expression using Python math>

Do not output anything after the result line.

Problem:
{question}
"""


def parse_number_vn(value: str) -> float | None:
    text = re.sub(r"[^\d,.]", "", str(value).strip())
    if not text:
        return None
    try:
        if text.count(".") == 1 and "," not in text and len(text.split(".")[1]) != 3:
            return float(text)
        return float(text.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def parse_options(raw_options: dict[str, Any]) -> dict[str, float]:
    parsed = {}
    for key, value in raw_options.items():
        number = parse_number_vn(str(value))
        if number is not None:
            parsed[key] = number
    return parsed


def row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def classify_calculation(question: str) -> str:
    if EXPR_RE.search(question or ""):
        return "arithmetic"
    if LINEAR_RE.search(question or ""):
        return "equation"
    lowered = (question or "").lower()
    if any(keyword in lowered for keyword in COMPLEX_KEYWORDS):
        return "complex"
    if re.search(r"\\[a-zA-Z]+\{", question or "") or "\\frac" in (question or ""):
        return "complex"
    return "word_problem"


def safe_eval(expr: str) -> float:
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
            return SAFE_OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPS:
            return SAFE_OPS[type(node.op)](evaluate(node.operand))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    tree = ast.parse(expr.replace("^", "**"), mode="eval")
    return float(evaluate(tree.body))


def solve_arithmetic(question: str) -> float | None:
    match = EXPR_RE.search(question or "")
    if not match:
        return None
    try:
        return safe_eval(match.group())
    except Exception:
        return None


def solve_linear(question: str) -> float | None:
    match = LINEAR_RE.search(question or "")
    if not match:
        return None
    expr = match.group().replace("X", "x")
    lhs, rhs = expr.split("=", 1)
    lhs = lhs.replace(" ", "")
    match_lhs = re.fullmatch(r"([+-]?\d*\.?\d*)x([+-]\d+\.?\d*)?", lhs)
    if not match_lhs:
        return None
    a_text, b_text = match_lhs.groups()
    if a_text in ("", "+"):
        a = 1.0
    elif a_text == "-":
        a = -1.0
    else:
        a = float(a_text)
    b = float(b_text) if b_text else 0.0
    return (float(rhs.strip()) - b) / a


def solve_word_problem(question: str, call_llm_fn) -> float | None:
    response = call_llm_fn(WORD_PROBLEM_PROMPT.format(question=question))
    match = re.search(r"result\s*=\s*(.+)", response or "")
    if not match:
        return None
    try:
        return safe_eval(match.group(1).strip())
    except Exception:
        return None


def solve_complex(question: str, call_llm_fn) -> float | None:
    return solve_word_problem(question, call_llm_fn)


def match_option(result: float, opts: dict[str, float]) -> tuple[str | None, float]:
    best_key = None
    best_diff = math.inf
    for key, value in opts.items():
        diff = abs(value - result)
        if diff < best_diff:
            best_key = key
            best_diff = diff
    return best_key, best_diff


def calc_confidence(calc_type: str, best_diff: float) -> float:
    base = {"arithmetic": 0.95, "equation": 0.9, "word_problem": 0.75, "complex": 0.7}.get(calc_type, 0.6)
    if best_diff > 10:
        base *= 0.7
    elif best_diff > 1:
        base *= 0.85
    return round(base, 2)


def solve_calculation(text: str, row: dict[str, Any], call_llm_fn) -> dict:
    options = parse_options(row_options(row))
    calc_type = classify_calculation(text)
    result = None
    if calc_type == "arithmetic":
        result = solve_arithmetic(text)
    if calc_type == "equation":
        result = solve_linear(text)
    if result is None and calc_type in ("word_problem", "complex", "equation"):
        result = solve_word_problem(text, call_llm_fn)
    if result is None or not options:
        return {"answer": None, "confidence": 0.0, "calc_type": calc_type}
    best_key, best_diff = match_option(result, options)
    return {"answer": best_key, "confidence": calc_confidence(calc_type, best_diff), "result": result, "calc_type": calc_type}
