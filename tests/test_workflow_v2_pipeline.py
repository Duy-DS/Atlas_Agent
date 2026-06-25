from agents.workflow_v2.pipeline import run_pipeline


def test_pipeline_routes_retrieval_before_calculation():
    text = "Đoạn thông tin: 2 + 2 = 4 trong đoạn này.\n\nCâu hỏi: Kết quả là gì?"
    result = run_pipeline(text, {"A": "4", "B": "5"}, lambda prompt, **kwargs: "A")
    assert result["task"] == "retrieval"
    assert result["answer"] == "A"
    assert result["confidence"] == 0.8


def test_pipeline_routes_calculation():
    result = run_pipeline("Tính 2 + 2", {"A": "3", "B": "4"}, lambda prompt, **kwargs: "")
    assert result["task"] == "calculation"
    assert result["answer"] == "B"


def test_pipeline_routes_knowledge():
    result = run_pipeline("Thủ đô Việt Nam?", {"A": "Hà Nội", "B": "Huế"}, lambda prompt, **kwargs: "ANSWER: A\nCONFIDENCE: 0.8")
    assert result["task"] == "knowledge"
    assert result["answer"] == "A"
