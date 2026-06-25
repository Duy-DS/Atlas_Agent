from agents.workflow_v2.calculation import (
    classify_calculation,
    parse_number_vn,
    parse_options,
    solve_calculation,
)


def test_parse_number_vn_handles_thousands_and_decimal():
    assert parse_number_vn("400.000 đồng") == 400000.0
    assert parse_number_vn("3,14") == 3.14
    assert parse_number_vn("3.14") == 3.14


def test_classifies_arithmetic_equation_and_complex():
    assert classify_calculation("Tính 2 + 3") == "arithmetic"
    assert classify_calculation("Giải 2x + 4 = 10") == "equation"
    assert classify_calculation("Tính xác suất chọn được bi đỏ") == "complex"


def test_solve_arithmetic_matches_nearest_option():
    row = {"A": "4", "B": "5", "C": "6", "D": "7"}
    result = solve_calculation("Tính 2 + 3", row, lambda prompt, **kwargs: "")
    assert result["answer"] == "B"
    assert result["confidence"] == 0.95
    assert result["result"] == 5.0


def test_solve_word_problem_uses_llm_result_line():
    row = {"A": "10", "B": "20", "C": "30", "D": "40"}
    result = solve_calculation("Một xe đi 10 km rồi 20 km. Tổng là bao nhiêu?", row, lambda prompt, **kwargs: "result = 30")
    assert result["answer"] == "C"
    assert result["calc_type"] == "word_problem"
