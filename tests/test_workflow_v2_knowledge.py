from agents.workflow_v2.knowledge import extract_answer, extract_self_confidence, solve_knowledge


def test_extract_answer_and_confidence():
    response = "Lý do...\nANSWER: c\nCONFIDENCE: 0.82"
    assert extract_answer(response) == "C"
    assert extract_self_confidence(response) == 0.82


def test_solve_knowledge_majority_votes_three_samples():
    responses = iter([
        "ANSWER: A\nCONFIDENCE: 0.9",
        "ANSWER: B\nCONFIDENCE: 0.6",
        "ANSWER: A\nCONFIDENCE: 0.8",
    ])

    def fake_llm(prompt, **kwargs):
        assert kwargs["temperature"] == 0.7
        assert "Các lựa chọn:" in prompt
        return next(responses)

    result = solve_knowledge("Thủ đô Việt Nam?", {"A": "Hà Nội", "B": "Huế"}, fake_llm)
    assert result["answer"] == "A"
    assert result["votes"] == {"A": 2, "B": 1}
    assert result["n_samples"] == 3
    assert result["confidence"] == 0.7
