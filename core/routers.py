import re

# Domain keyword regex maps for fast routing (0ms)
SUBJECT_PATTERNS = {
    "math": re.compile(r"\b(toán|tích phân|đạo hàm|số học|phương trình|đại số|hình học|logarit|sin|cos|tan)\b", re.I),
    "it": re.compile(r"\b(mạng|lập trình|python|java|html|database|cơ sở dữ liệu|sql|thuật toán|git|docker)\b", re.I),
    "physics": re.compile(r"\b(vật lý|vận tốc|gia tốc|lực|điện tích|thấu kính|quang học|nhiệt động|hạt nhân)\b", re.I),
    "english": re.compile(r"\b(english|grammar|pronoun|verb|noun|adjective|vocabulary|translate|tiếng anh)\b", re.I),
    "geography": re.compile(r"\b(địa lý|bản đồ|kinh độ|vĩ độ|quốc gia|thành phố|sông|núi|dân số|khí hậu)\b", re.I),
    "history": re.compile(r"\b(lịch sử|chiến tranh|triều đại|vua|hiệp định|cách mạng|thế kỷ|năm \d{3,4})\b", re.I)
}

def classify_subject_fast(question_text: str) -> str:
    """Classifies the domain using fast regex rules without calling an LLM."""
    for subject, pattern in SUBJECT_PATTERNS.items():
        if pattern.search(question_text):
            return subject
    return "general"

def should_trigger_search(question_text: str, current_answer: str) -> bool:
    """Determines if the agent should fetch web search context.
    E.g. if the answer is invalid (N/A) or context is highly time-sensitive.
    """
    if current_answer == "N/A":
        return True
    
    # Time sensitivity check
    time_keywords = re.compile(r"\b(mới nhất|gần đây|năm nay|năm \b202[4-9]\b|hiện tại|ai đang là)\b", re.I)
    if time_keywords.search(question_text):
        return True
        
    return False
