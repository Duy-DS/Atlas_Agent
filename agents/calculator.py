"""
Calculator tool: detect câu hỏi tính toán, eval expression, map kết quả vào A/B/C/D.
Hỗ trợ: biểu thức số học + phương trình tuyến tính một ẩn (ax + b = c)
         + code generation cho các dạng toán phức tạp hơn.
"""
from __future__ import annotations

import ast
import math
import re
from pathlib import Path

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

# Format số kiểu VN dùng dấu chấm làm phân cách nghìn: chỉ coi là phân cách
# nghìn khi đúng dạng nhóm-3-chữ-số (vd 400.000), tránh nuốt nhầm số thập
# phân thường viết bằng dấu chấm (vd 3.14).
_VN_THOUSANDS_RE = re.compile(r"\d{1,3}(\.\d{3})+")

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
        a_clean = (a_str or "").replace(" ", "")
        if a_clean in ("", "+"):
            a = 1.0
        elif a_clean == "-":
            a = -1.0
        else:
            a = float(a_clean)
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


_CALC_CODE_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "calc_code.md").read_text(encoding="utf-8").strip()
_RESULT_RE = re.compile(r"result\s*=\s*(.+)")
_SAFE_ASSIGN_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Call, ast.Attribute,
    ast.Name, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.Mod,
    ast.FloorDiv, ast.Load, ast.List, ast.Tuple,
)


_SAFE_BUILTINS = {"int", "float", "round", "abs", "sum", "len", "max", "min", "range", "list"}
_ALLOWED_NAMES = _SAFE_BUILTINS | {"math", "None", "True", "False"}


def _safe_exec_result(expr: str) -> float | None:
    """Exec biểu thức trong sandbox giới hạn, chỉ cho phép math + builtins an toàn."""
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in _ALLOWED_NAMES:
                return None
            if not isinstance(node, _SAFE_ASSIGN_NODES):
                return None
        import builtins
        safe_builtins = {k: getattr(builtins, k) for k in _SAFE_BUILTINS if hasattr(builtins, k)}
        ns = {"math": math, "__builtins__": safe_builtins}
        result = eval(compile(tree, "<calc>", "eval"), ns)  # noqa: S307
        return float(result) if result is not None else None
    except Exception:
        return None


def _parse_options(row: dict[str, str]) -> dict[str, float]:
    """Parse A/B/C/D thành số nếu có thể. Xử lý cả format VN: 400.000 hay 9,42."""
    opts = {}
    for opt in ("A", "B", "C", "D"):
        parts = row.get(opt, "").strip().split()
        if not parts:
            continue  # field rỗng, bỏ qua thay vì crash
        raw = parts[0]  # bỏ đơn vị như "đồng", "cm"

        if _VN_THOUSANDS_RE.fullmatch(raw):
            # Đúng dạng nhóm-3-chữ-số (400.000) → dấu chấm là phân cách nghìn
            raw = raw.replace(".", "")
        elif "," in raw:
            # Có dấu phẩy → dấu chấm (nếu có) là phân cách nghìn, phẩy là thập phân
            raw = raw.replace(".", "").replace(",", ".")
        # else: giữ nguyên, coi là số thập phân chuẩn (vd "3.14")

        try:
            opts[opt] = float(raw)
        except ValueError:
            pass
    return opts


def try_code_calculator(row: dict[str, str], call_agent_fn) -> str | None:
    """
    Dùng LLM sinh 1 dòng Python, exec an toàn, so kết quả với A/B/C/D.
    call_agent_fn: hàm nhận prompt string, trả về string response.
    """
    opts = _parse_options(row)
    if not opts:
        return None  # options không phải số, skip

    prompt = (
        f"{_CALC_CODE_PROMPT}\n\n"
        f"Bài toán: {row.get('question', '')}\n"
        f"Đáp án: " + ", ".join(f"{k}={row[k]}" for k in ("A", "B", "C", "D") if k in row)
    )

    raw = call_agent_fn(prompt)
    m = _RESULT_RE.search(raw or "")
    if not m:
        return None

    result = _safe_exec_result(m.group(1).strip())
    if result is None:
        return None

    for opt, val in opts.items():
        if abs(val - result) < 1e-6:
            return opt

    return None