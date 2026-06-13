from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectDecision:
    subject: str
    needs_domain_retry: bool
    reason: str


DOMAIN_RETRY_SUBJECTS = {"math", "physics", "logic"}

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


KEYWORDS = {
    "it": (
        "công nghệ thông tin", "cong nghe thong tin", "thuật toán", "thuat toan",
        "lập trình", "lap trinh", "cơ sở dữ liệu", "co so du lieu", "database",
        "mạng máy tính", "mang may tinh", "hệ điều hành", "he dieu hanh",
        "bảo mật", "bao mat", "quicksort", "python", "java", "sql", "tcp/ip",
    ),
    "math": (
        "toán", "toan", "tính", "tinh", "bằng bao nhiêu", "bang bao nhieu",
        "phương trình", "phuong trinh", "biểu thức", "bieu thuc", "xác suất",
        "xac suat", "đạo hàm", "dao ham", "tích phân", "tich phan", "chu vi",
        "diện tích", "dien tich", "%", "2x", "x =", "x=",
    ),
    "physics": (
        "vật lý", "vat ly", "newton", "lực", "luc", "gia tốc", "gia toc",
        "vận tốc", "van toc", "khối lượng", "khoi luong", "năng lượng", "nang luong",
        "điện trở", "dien tro", "định luật", "dinh luat", "rơi tự do", "roi tu do",
    ),
    "geography": (
        "địa lý", "dia ly", "địa hình", "dia hinh", "khí hậu", "khi hau",
        "sông", "song", "núi", "nui", "vùng", "vung", "hoàng liên sơn",
        "kinh tuyến", "vi tuyến", "vi tuyen", "châu lục", "chau luc",
    ),
    "history": (
        "lịch sử", "lich su", "chiến dịch", "chien dich", "điện biên phủ",
        "dien bien phu", "cách mạng", "cach mang", "triều đại", "trieu dai",
        "nhà nguyễn", "nha nguyen", "năm nào", "nam nao", "thế chiến", "the chien",
    ),
    "english": (
        "tiếng anh", "tieng anh", "choose the", "correct tense", "grammar",
        "synonym", "antonym", "reading passage", "fill in the blank", "sentence",
        "collocation", "preposition", "verb form",
    ),
    "logic": (
        "logic", "tư duy", "tu duy", "suy luận", "suy luan", "nếu", "neu",
        "kéo theo", "keo theo", "mâu thuẫn", "mau thuan", "kết luận nào",
        "ket luan nao", "mọi", "moi", "tất cả", "tat ca",
    ),
}


def classify_subject(row: dict[str, str]) -> SubjectDecision:
    question = (row.get("question") or "").lower()
    for subject, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword in question:
                needs_retry = subject in DOMAIN_RETRY_SUBJECTS and has_domain_retry_risk(question)
                reason = f"keyword:{keyword}"
                if needs_retry:
                    reason += ";risk_signal"
                return SubjectDecision(subject, needs_retry, reason)
    return SubjectDecision("other", False, "no_domain_signal")
