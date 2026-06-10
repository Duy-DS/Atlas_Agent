from __future__ import annotations

from dataclasses import dataclass

VOLATILE_KEYWORDS = (
    "hiện nay",
    "hien nay",
    "mới nhất",
    "moi nhat",
    "hôm nay",
    "hom nay",
    "năm nay",
    "nam nay",
    "latest",
    "current",
    "today",
    "ceo",
    "chủ tịch",
    "chu tich",
    "tổng thống",
    "tong thong",
    "giá",
    "gia",
    "phiên bản",
    "phien ban",
)


@dataclass(frozen=True)
class SearchDecision:
    needs_search: bool
    reason: str


def should_search(row: dict[str, str], answer: str) -> bool:
    return route_search(row, answer).needs_search


def route_search(row: dict[str, str], answer: str) -> SearchDecision:
    normalized_answer = (answer or "").strip().upper()
    question = (row.get("question") or "").lower()
    if normalized_answer == "N/A":
        return SearchDecision(True, "answer_is_na")
    for keyword in VOLATILE_KEYWORDS:
        if keyword in question:
            return SearchDecision(True, f"volatile_keyword:{keyword}")
    return SearchDecision(False, "stable_question")
