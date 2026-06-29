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


def classify_subject_by_rules(question: str) -> str | None:
    q_lower = (question or "").lower()
    
    # 1. English detection (high-priority, handles grammar/vocabulary)
    english_words = {"the", "choose", "correct", "tense", "sentence", "pronunciation", "meaning", "synonym", "antonym", "underlined", "following passage"}
    if any(word in q_lower for word in english_words) or any(w in q_lower for w in ["tense for this", "correct answer"]):
        vietnamese_chars = set("áàảãạâấầẩẫậăắằẳẵặéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ")
        has_vn = any(c in q_lower for c in vietnamese_chars)
        # English questions usually don't have Vietnamese diacritics
        if not has_vn or any(word in q_lower for word in ["tense", "pronunciation", "synonym", "antonym"]):
            return "english"

    # 2. IT / Computing
    it_keywords = [
        "thuật toán", "thuat toan", "quicksort", "mergesort", "bubblesort", "binary search", 
        "tìm kiếm nhị phân", "mảng", "danh sách liên kết", "cấu trúc dữ liệu", "cơ sở dữ liệu",
        "sql", "python", "c++", "java", "lập trình", "mã nguồn", "ip address", "mạng máy tính",
        "router", "switch", "http", "tcp/ip", "giao thức"
    ]
    if any(keyword in q_lower for keyword in it_keywords):
        return "it"

    # 3. Physics
    physics_keywords = [
        "vật lý", "vật lí", "vật lý học", "vật lí học", "định luật", "dieu luat", "newton", "lực", "luc", "gia tốc", "gia toc", "vận tốc", "van toc", 
        "điện trở", "dien tro", "rơi tự do", "roi tu do", "thế năng", "động năng", "cơ năng", "âm thanh", "ánh sáng",
        "thấu kính", "khúc xạ", "tần số", "bước sóng", "dòng điện", "hiệu điện thế"
    ]
    if any(keyword in q_lower for keyword in physics_keywords):
        return "physics"

    # 4. Logic
    logic_keywords = [
        "kéo theo", "keo theo", "logic", "lô-gíc", "logic học", "mệnh đề", "menh de", "suy luận", "suy luan", 
        "mâu thuẫn", "mau thuan", "tam đoạn luận", "kết luận", "ket luan", "suy ra"
    ]
    if any(keyword in q_lower for keyword in logic_keywords) or ("nếu" in q_lower and "thì" in q_lower) or ("neu" in q_lower and "thi" in q_lower):
        return "logic"

    # 5. Math
    math_keywords = [
        "toán", "toán học", "tính ", "cộng", "trừ", "nhân", "chia", "phương trình", "phuong trinh", 
        "tích phân", "tich phan", "đạo hàm", "dao ham", "xác suất", "xac suat", 
        "biểu thức", "bieu thuc", "tính giá trị", "x =", "x=", "2x", "cạnh", "tam giác", "hình vuông", "hình chữ nhật"
    ]
    import re
    if any(keyword in q_lower for keyword in math_keywords) or re.search(r'\b\d*x\s*[=+\-*/]\s*\d+\b', q_lower) or re.search(r'\bx\s*=\s*\d+\b', q_lower):
        return "math"

    # 6. Geography
    geography_keywords = [
        "địa lý", "dia ly", "bản đồ", "vĩ độ", "kinh độ", "xích đạo", "khí hậu", "ôn đới", "nhiệt đới",
        "lục địa", "đại dương", "hoàng liên sơn", "đồng bằng", "sông", "núi", "tỉnh thành", "thủ đô",
        "đông nam á", "châu á", "châu âu", "châu phi", "châu mỹ"
    ]
    if any(keyword in q_lower for keyword in geography_keywords):
        return "geography"

    # 7. History
    history_keywords = [
        "lịch sử", "lich su", "chiến dịch", "chien dich", "chiến tranh", "chien tranh", "khởi nghĩa", "cách mạng", 
        "triều đại", "trieu dai", "vua", "hoàng đế", "nhà nguyễn", "nhà lê", "nhà lý", "nhà trần", "thế kỷ", 
        "hiệp định", "hiệp ước", "giải phóng", "kháng chiến"
    ]
    if any(keyword in q_lower for keyword in history_keywords):
        return "history"

    return None


def classify_subject(row: dict[str, str]) -> SubjectDecision:
    question = (row.get("question") or "")
    
    # Try classifying using local keyword/regex rules first (0ms)
    subject = classify_subject_by_rules(question)
    reason = "rules"
    
    # Fall back to LLM-based classification only if rules cannot determine the subject
    if not subject:
        cache_key = question[:300]
        subject = _llm_classify(cache_key)
        reason = "llm"
        
    needs_retry = subject in DOMAIN_RETRY_SUBJECTS and has_domain_retry_risk(question)
    reason = f"{reason}:{subject}"
    if needs_retry:
        reason += ";risk_signal"
    return SubjectDecision(subject, needs_retry, reason)

