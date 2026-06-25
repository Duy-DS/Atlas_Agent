from __future__ import annotations

import re
from typing import Any

EXPR_RE = re.compile(r"\d+\s*[\+\-\*\/\^]\s*\d+")
LINEAR_RE = re.compile(r"\d*[xXyY]\s*[\+\-]?\s*\d*\s*=\s*\d+")

CALC_KEYWORDS = ("tính", "bao nhiêu", "calculate", "find", "xác suất", "đạo hàm")
UNITS = ("cm", "m", "kg", "km", "%", "đồng", "lít", "m/s")


def is_retrieval(text: str) -> bool:
    return "Đoạn thông tin" in (text or "") and "Câu hỏi" in (text or "")


def _row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def is_calculation(text: str, row: dict[str, Any]) -> bool:
    text = text or ""
    if EXPR_RE.search(text) or LINEAR_RE.search(text):
        return True

    score = 0.0
    numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
    lowered = text.lower()
    has_units = any(unit in lowered for unit in UNITS)
    has_keywords = any(keyword in lowered for keyword in CALC_KEYWORDS)
    numeric_options = sum(
        1
        for value in _row_options(row).values()
        if re.match(r"^[\d.,]+$", str(value).strip())
    )

    if len(numbers) >= 2:
        score += 0.3
    if has_units:
        score += 0.3
    if has_keywords:
        score += 0.3
    if numeric_options >= 2:
        score += 0.2
    return score >= 0.5


def classify(text: str, row: dict[str, Any]) -> str:
    if is_retrieval(text):
        return "retrieval"
    if is_calculation(text, row):
        return "calculation"
    return "knowledge"
