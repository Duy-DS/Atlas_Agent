from __future__ import annotations

from dataclasses import dataclass
import re

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
    "cổ phiếu",
    "co phieu",
    "chứng khoán",
    "chung khoan",
    "thống kê",
    "thong ke",
    "dân số",
    "dan so",
    "gdp",
    "sản lượng",
    "san luong",
    "phiên bản",
    "phien ban",
)


@dataclass(frozen=True)
class SearchDecision:
    needs_search: bool
    reason: str


def should_search(row: dict[str, str], answer: str) -> bool:
    return route_search(row, answer).needs_search


def keyword_matches(question: str, keyword: str) -> bool:
    if " " in keyword or "/" in keyword:
        return keyword in question
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, question, flags=re.UNICODE) is not None


def route_search(row: dict[str, str], answer: str) -> SearchDecision:
    normalized_answer = (answer or "").strip().upper()
    question = (row.get("question") or "").lower()
    if normalized_answer == "N/A":
        return SearchDecision(True, "answer_is_na")
    for keyword in VOLATILE_KEYWORDS:
        if keyword_matches(question, keyword):
            return SearchDecision(True, f"volatile_keyword:{keyword}")
    return SearchDecision(False, "stable_question")
