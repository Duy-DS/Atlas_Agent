from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubjectDecision:
    subject: str
    needs_domain_retry: bool
    reason: str


DOMAIN_RETRY_SUBJECTS = {"math", "physics", "logic"}

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
                return SubjectDecision(subject, subject in DOMAIN_RETRY_SUBJECTS, f"keyword:{keyword}")
    return SubjectDecision("other", False, "no_domain_signal")
