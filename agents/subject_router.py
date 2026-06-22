from __future__ import annotations

import functools
from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectDecision:
    subject: str
    needs_domain_retry: bool
    reason: str


DOMAIN_RETRY_SUBJECTS = {"math", "physics", "logic"}
VALID_SUBJECTS = {"math", "physics", "it", "geography", "history", "english", "logic", "other"}

DOMAIN_RETRY_RISK_KEYWORDS = (
    "không đúng", "khong dung", "không phải", "khong phai", "sai", "ngoại trừ",
    "ngoai tru", "tất cả", "tat ca", "mâu thuẫn", "mau thuan", "kéo theo",
    "keo theo", "suy ra", "kết luận", "ket luan", "phương trình", "phuong trinh",
    "biểu thức", "bieu thuc", "xác suất", "xac suat", "đạo hàm", "dao ham",
    "tích phân", "tich phan", "bằng bao nhiêu", "bang bao nhieu", "%", "x =",
    "x=", "2x", "newton", "lực", "luc", "gia tốc", "gia toc", "vận tốc",
    "van toc", "điện trở", "dien tro", "rơi tự do", "roi tu do", "nếu", "neu",
    "mọi", "moi",
)


def has_domain_retry_risk(question: str) -> bool:
    normalized = (question or "").lower()
    return any(keyword in normalized for keyword in DOMAIN_RETRY_RISK_KEYWORDS)


def should_retry_domain(row: dict[str, str], answer_quality: str = "clean") -> bool:
    decision = classify_subject(row)
    if decision.subject not in DOMAIN_RETRY_SUBJECTS:
        return False
    return decision.needs_domain_retry or answer_quality != "clean"


@functools.lru_cache(maxsize=2048)
def _llm_classify(question_key: str) -> str:
    """Dùng LLM để phân loại môn học. Cache kết quả theo nội dung câu hỏi để tránh gọi 2 lần."""
    try:
        from agents.agent import agent
        prompt = (
            "Phân loại câu hỏi sau thuộc môn học nào. "
            "Chỉ trả về đúng 1 từ: math, physics, it, geography, history, english, logic, other.\n\n"
            f"Câu hỏi: {question_key[:500]}"
        )
        result = agent(prompt, think=False).strip().lower()
        # Lấy từ đầu tiên khớp với danh sách hợp lệ
        for word in result.split():
            clean = word.strip(".,;:\"'")
            if clean in VALID_SUBJECTS:
                return clean
    except Exception:
        pass
    return "other"


def classify_subject(row: dict[str, str]) -> SubjectDecision:
    question = (row.get("question") or "")
    # Dùng 300 ký tự đầu làm cache key để tránh key quá dài
    cache_key = question[:300]
    subject = _llm_classify(cache_key)
    needs_retry = subject in DOMAIN_RETRY_SUBJECTS and has_domain_retry_risk(question)
    reason = f"llm:{subject}"
    if needs_retry:
        reason += ";risk_signal"
    return SubjectDecision(subject, needs_retry, reason)
