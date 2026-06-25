from agents.workflow_v2.retrieval import (
    build_retrieval_context,
    build_retrieval_prompt,
    chunk_context,
    parse_retrieval_input,
    solve_retrieval,
)


def test_parse_and_chunk_retrieval_input():
    text = "Đoạn thông tin: Một đoạn đủ dài về Hà Nội.\n\nĐoạn ngắn.\n\nMột đoạn đủ dài về Huế.\nCâu hỏi: Thành phố nào là thủ đô?"
    context, question = parse_retrieval_input(text)
    assert "Hà Nội" in context
    assert question == "Thành phố nào là thủ đô?"
    assert chunk_context(context) == ["Một đoạn đủ dài về Hà Nội.", "Một đoạn đủ dài về Huế."]


def test_build_retrieval_context_and_prompt():
    context = build_retrieval_context(["A", "B"])
    assert "[Chunk 1]\nA" in context
    assert "[Chunk 2]\nB" in context
    prompt = build_retrieval_prompt(context, "Q?")
    assert "Chỉ sử dụng thông tin" in prompt
    assert "Q?" in prompt


def test_build_retrieval_prompt_includes_options_as_json_and_asks_for_a_letter():
    prompt = build_retrieval_prompt("ctx", "Q?", {"A": "Huế", "B": "Hà Nội"})
    assert "Các lựa chọn:" in prompt
    assert '"A": "Huế"' in prompt
    assert '"B": "Hà Nội"' in prompt
    assert "một chữ cái đáp án" in prompt


def test_solve_retrieval_calls_llm_with_ranked_context_and_options():
    calls = []

    def fake_llm(prompt, **kwargs):
        calls.append(prompt)
        return "B"

    text = "Đoạn thông tin: Hà Nội là thủ đô Việt Nam và nằm ở miền Bắc.\n\nHuế từng là kinh đô.\n\nCâu hỏi: Thủ đô Việt Nam là gì?"
    row = {"A": "Huế", "B": "Hà Nội"}
    result = solve_retrieval(text, row, fake_llm)
    assert result["answer"] == "B"
    assert result["confidence"] == 0.8
    assert "Hà Nội là thủ đô" in calls[0]
    assert '"B": "Hà Nội"' in calls[0]
