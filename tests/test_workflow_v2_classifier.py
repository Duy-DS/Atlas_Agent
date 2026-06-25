from agents.workflow_v2.classifier import classify, is_calculation, is_retrieval


def test_retrieval_has_highest_priority_even_with_numbers():
    text = "Đoạn thông tin: Giá trị 2 + 2 là 4.\n\nCâu hỏi: Kết quả là gì?"
    assert is_retrieval(text)
    assert classify(text, {"options": {"A": "4", "B": "5"}}) == "retrieval"


def test_calculation_detects_expression_and_numeric_options():
    assert classify("Tính 12 + 30 bằng bao nhiêu?", {"options": {"A": "42", "B": "12"}}) == "calculation"
    row = {"options": {"A": "10", "B": "20", "C": "30", "D": "40"}}
    assert is_calculation("Một vật đi 10 km trong 2 giờ, vận tốc là bao nhiêu?", row)


def test_knowledge_is_fallback():
    assert classify("Thủ đô của Việt Nam là gì?", {"options": {"A": "Hà Nội"}}) == "knowledge"
