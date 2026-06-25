# Workflow V2 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `docs/workflow_v2.md` as the primary question pipeline: priority classifier `retrieval -> calculation -> knowledge`, specialized solvers, confidence, and audit detail.

**Architecture:** Add focused pipeline modules under `agents/workflow_v2/` and keep the existing CSV runner in `main.py` as the orchestration boundary. The new pipeline returns `{task, answer, confidence, detail}` per row; `main.run` uses it per row first, then preserves existing web-search/domain retry behavior as fallback only when workflow-v2 returns `N/A` or very low confidence.

**Tech Stack:** Python 3.11+, `unittest`/`pytest`, Ollama client through existing `agents.agent.agent`, optional `rank_bm25` with a deterministic in-repo fallback to avoid hard runtime failure.

---

## File Structure

- Create: `agents/workflow_v2/__init__.py`
  - Public exports for `classify`, `run_pipeline`, and solver functions.
- Create: `agents/workflow_v2/classifier.py`
  - Priority classifier and heuristic calculation detection.
- Create: `agents/workflow_v2/retrieval.py`
  - Retrieval input parsing, context chunking, BM25-style ranking, prompt building, and solver.
- Create: `agents/workflow_v2/calculation.py`
  - VN number parsing, calculation type detection, safe arithmetic/equation solving, option matching, confidence scoring.
- Create: `agents/workflow_v2/knowledge.py`
  - Knowledge prompt, answer/confidence extraction, majority vote, sampled LLM solver.
- Create: `agents/workflow_v2/pipeline.py`
  - Entry point `run_pipeline(text, row, call_llm_fn)`.
- Modify: `main.py`
  - Add a row-level workflow-v2 prediction path and wire confidence/detail into audit.
- Modify: `requirements.txt`
  - Add `rank_bm25==0.2.2` only if the implementation chooses the package path. Keep fallback ranking in code either way.
- Test: `tests/test_workflow_v2_classifier.py`
- Test: `tests/test_workflow_v2_retrieval.py`
- Test: `tests/test_workflow_v2_calculation.py`
- Test: `tests/test_workflow_v2_knowledge.py`
- Test: `tests/test_workflow_v2_pipeline.py`
- Test: `tests/test_main_workflow_v2.py`

## Task 1: Classifier

**Files:**
- Create: `agents/workflow_v2/__init__.py`
- Create: `agents/workflow_v2/classifier.py`
- Test: `tests/test_workflow_v2_classifier.py`

- [ ] **Step 1: Write failing classifier tests**

```python
# tests/test_workflow_v2_classifier.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_workflow_v2_classifier.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'agents.workflow_v2'`.

- [ ] **Step 3: Implement classifier**

```python
# agents/workflow_v2/classifier.py
from __future__ import annotations

import re
from typing import Any

EXPR_RE = re.compile(r"\d+\s*[\+\-\*\/\^]\s*\d+")
LINEAR_RE = re.compile(r"\d*[xXyY]\s*[\+\-]?\s*\d*\s*=\s*\d+")

CALC_KEYWORDS = ("tính", "bao nhiêu", "calculate", "find", "xác suất", "đạo hàm")
UNITS = ("cm", "m", "kg", "km", "%", "đồng", "lít", "m/s")


def is_retrieval(text: str) -> bool:
    return "Đoạn thông tin" in (text or "") and "Câu hỏi" in (text or "")


def _row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def is_calculation(text: str, row: dict[str, Any]) -> bool:
    text = text or ""
    if EXPR_RE.search(text) or LINEAR_RE.search(text):
        return True

    score = 0.0
    numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
    lowered = text.lower()
    has_units = any(unit in lowered for unit in UNITS)
    has_keywords = any(keyword in lowered for keyword in CALC_KEYWORDS)
    numeric_options = sum(
        1
        for value in _row_options(row).values()
        if re.match(r"^[\d.,]+$", str(value).strip())
    )

    if len(numbers) >= 2:
        score += 0.3
    if has_units:
        score += 0.3
    if has_keywords:
        score += 0.3
    if numeric_options >= 2:
        score += 0.2
    return score >= 0.5


def classify(text: str, row: dict[str, Any]) -> str:
    if is_retrieval(text):
        return "retrieval"
    if is_calculation(text, row):
        return "calculation"
    return "knowledge"
```

```python
# agents/workflow_v2/__init__.py
from agents.workflow_v2.classifier import classify, is_calculation, is_retrieval

__all__ = ["classify", "is_calculation", "is_retrieval"]
```

- [ ] **Step 4: Run classifier tests**

Run: `rtk pytest tests/test_workflow_v2_classifier.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add agents/workflow_v2/__init__.py agents/workflow_v2/classifier.py tests/test_workflow_v2_classifier.py
rtk git commit -m "feat: add workflow v2 classifier"
```

## Task 2: Retrieval Solver

**Files:**
- Create: `agents/workflow_v2/retrieval.py`
- Modify: `agents/workflow_v2/__init__.py`
- Test: `tests/test_workflow_v2_retrieval.py`

- [ ] **Step 1: Write failing retrieval tests**

```python
# tests/test_workflow_v2_retrieval.py
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


def test_solve_retrieval_calls_llm_with_ranked_context():
    calls = []

    def fake_llm(prompt, **kwargs):
        calls.append(prompt)
        return "Hà Nội"

    text = "Đoạn thông tin: Hà Nội là thủ đô Việt Nam và nằm ở miền Bắc.\n\nHuế từng là kinh đô.\n\nCâu hỏi: Thủ đô Việt Nam là gì?"
    result = solve_retrieval(text, fake_llm)
    assert result["answer"] == "Hà Nội"
    assert result["confidence"] == 0.8
    assert "Hà Nội là thủ đô" in calls[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_workflow_v2_retrieval.py -q`

Expected: FAIL with missing `agents.workflow_v2.retrieval`.

- [ ] **Step 3: Implement retrieval solver with package fallback**

Use `rank_bm25.BM25Okapi` when importable; otherwise compute a deterministic token-overlap score so tests and Docker runs do not crash if dependency is absent.

```python
# agents/workflow_v2/retrieval.py
from __future__ import annotations

from collections import Counter


def parse_retrieval_input(text: str) -> tuple[str, str]:
    parts = (text or "").split("Câu hỏi:", 1)
    context = parts[0].replace("Đoạn thông tin:", "", 1).strip()
    question = parts[1].strip() if len(parts) > 1 else ""
    return context, question


def chunk_context(context: str, min_len: int = 20) -> list[str]:
    return [chunk.strip() for chunk in (context or "").split("\n\n") if len(chunk.strip()) >= min_len]


def _fallback_scores(question: str, chunks: list[str]) -> list[float]:
    q_tokens = Counter(question.lower().split())
    scores = []
    for chunk in chunks:
        c_tokens = Counter(chunk.lower().split())
        scores.append(float(sum(min(q_tokens[token], c_tokens[token]) for token in q_tokens)))
    return scores


def bm25_retrieve(question: str, chunks: list[str], top_k: int = 10) -> list[str]:
    if not chunks:
        return []
    top_k = min(top_k, len(chunks))
    try:
        from rank_bm25 import BM25Okapi

        tokenized = [chunk.split() for chunk in chunks]
        scores = BM25Okapi(tokenized).get_scores(question.split())
    except Exception:
        scores = _fallback_scores(question, chunks)
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    return [chunks[index] for index, _ in ranked[:top_k]]


def rerank(question: str, candidates: list[str], top_n: int = 3) -> list[str]:
    return candidates[:top_n]


def build_retrieval_context(top_chunks: list[str]) -> str:
    return "\n\n".join(f"[Chunk {index + 1}]\n{chunk}" for index, chunk in enumerate(top_chunks))


def build_retrieval_prompt(context: str, question: str) -> str:
    return f"""Dựa vào đoạn thông tin dưới đây, hãy trả lời câu hỏi.
Chỉ sử dụng thông tin trong đoạn văn, không thêm kiến thức bên ngoài.

Đoạn thông tin:
{context}

Câu hỏi:
{question}
"""


def solve_retrieval(text: str, call_llm_fn) -> dict:
    context, question = parse_retrieval_input(text)
    chunks = chunk_context(context)
    top10 = bm25_retrieve(question, chunks, top_k=10)
    top3 = rerank(question, top10, top_n=3)
    prompt = build_retrieval_prompt(build_retrieval_context(top3), question)
    return {"answer": call_llm_fn(prompt), "confidence": 0.8}
```

- [ ] **Step 4: Export retrieval functions**

```python
# agents/workflow_v2/__init__.py
from agents.workflow_v2.classifier import classify, is_calculation, is_retrieval
from agents.workflow_v2.retrieval import solve_retrieval

__all__ = ["classify", "is_calculation", "is_retrieval", "solve_retrieval"]
```

- [ ] **Step 5: Run retrieval tests**

Run: `rtk pytest tests/test_workflow_v2_retrieval.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add agents/workflow_v2/__init__.py agents/workflow_v2/retrieval.py tests/test_workflow_v2_retrieval.py
rtk git commit -m "feat: add workflow v2 retrieval solver"
```

## Task 3: Calculation Solver

**Files:**
- Create: `agents/workflow_v2/calculation.py`
- Modify: `agents/workflow_v2/__init__.py`
- Test: `tests/test_workflow_v2_calculation.py`

- [ ] **Step 1: Write failing calculation tests**

```python
# tests/test_workflow_v2_calculation.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_workflow_v2_calculation.py -q`

Expected: FAIL with missing `agents.workflow_v2.calculation`.

- [ ] **Step 3: Implement calculation solver**

```python
# agents/workflow_v2/calculation.py
from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any

from agents.workflow_v2.classifier import EXPR_RE, LINEAR_RE

COMPLEX_KEYWORDS = ("xác suất", "probability", "log", "sin", "cos", "tan", "đạo hàm", "tích phân", "lãi suất", "tổ hợp", "chỉnh hợp")

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

WORD_PROBLEM_PROMPT = """You are a calculation engine. Solve the math problem step by step.

Output EXACTLY one line at the end:
result = <numeric expression using Python math>

Do not output anything after the result line.

Problem:
{question}
"""


def parse_number_vn(value: str) -> float | None:
    text = re.sub(r"[^\d,.]", "", str(value).strip())
    if not text:
        return None
    try:
        if text.count(".") == 1 and "," not in text and len(text.split(".")[1]) != 3:
            return float(text)
        return float(text.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def parse_options(raw_options: dict[str, Any]) -> dict[str, float]:
    parsed = {}
    for key, value in raw_options.items():
        number = parse_number_vn(str(value))
        if number is not None:
            parsed[key] = number
    return parsed


def row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def classify_calculation(question: str) -> str:
    if EXPR_RE.search(question or ""):
        return "arithmetic"
    if LINEAR_RE.search(question or ""):
        return "equation"
    lowered = (question or "").lower()
    if any(keyword in lowered for keyword in COMPLEX_KEYWORDS):
        return "complex"
    if re.search(r"\\[a-zA-Z]+\{", question or "") or "\\frac" in (question or ""):
        return "complex"
    return "word_problem"


def safe_eval(expr: str) -> float:
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
            return SAFE_OPS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPS:
            return SAFE_OPS[type(node.op)](evaluate(node.operand))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    tree = ast.parse(expr.replace("^", "**"), mode="eval")
    return float(evaluate(tree.body))


def solve_arithmetic(question: str) -> float | None:
    match = EXPR_RE.search(question or "")
    if not match:
        return None
    try:
        return safe_eval(match.group())
    except Exception:
        return None


def solve_linear(question: str) -> float | None:
    match = LINEAR_RE.search(question or "")
    if not match:
        return None
    expr = match.group().replace("X", "x")
    lhs, rhs = expr.split("=", 1)
    lhs = lhs.replace(" ", "")
    match_lhs = re.fullmatch(r"([+-]?\d*\.?\d*)x([+-]\d+\.?\d*)?", lhs)
    if not match_lhs:
        return None
    a_text, b_text = match_lhs.groups()
    if a_text in ("", "+"):
        a = 1.0
    elif a_text == "-":
        a = -1.0
    else:
        a = float(a_text)
    b = float(b_text) if b_text else 0.0
    return (float(rhs.strip()) - b) / a


def solve_word_problem(question: str, call_llm_fn) -> float | None:
    response = call_llm_fn(WORD_PROBLEM_PROMPT.format(question=question))
    match = re.search(r"result\s*=\s*(.+)", response or "")
    if not match:
        return None
    try:
        return safe_eval(match.group(1).strip())
    except Exception:
        return None


def solve_complex(question: str, call_llm_fn) -> float | None:
    return solve_word_problem(question, call_llm_fn)


def match_option(result: float, opts: dict[str, float]) -> tuple[str | None, float]:
    best_key = None
    best_diff = math.inf
    for key, value in opts.items():
        diff = abs(value - result)
        if diff < best_diff:
            best_key = key
            best_diff = diff
    return best_key, best_diff


def calc_confidence(calc_type: str, best_diff: float) -> float:
    base = {"arithmetic": 0.95, "equation": 0.9, "word_problem": 0.75, "complex": 0.7}.get(calc_type, 0.6)
    if best_diff > 10:
        base *= 0.7
    elif best_diff > 1:
        base *= 0.85
    return round(base, 2)


def solve_calculation(text: str, row: dict[str, Any], call_llm_fn) -> dict:
    options = parse_options(row_options(row))
    calc_type = classify_calculation(text)
    result = None
    if calc_type == "arithmetic":
        result = solve_arithmetic(text)
    if calc_type == "equation":
        result = solve_linear(text)
    if result is None and calc_type in ("word_problem", "complex", "equation"):
        result = solve_word_problem(text, call_llm_fn)
    if result is None or not options:
        return {"answer": None, "confidence": 0.0, "calc_type": calc_type}
    best_key, best_diff = match_option(result, options)
    return {"answer": best_key, "confidence": calc_confidence(calc_type, best_diff), "result": result, "calc_type": calc_type}
```

- [ ] **Step 4: Export calculation solver**

```python
# agents/workflow_v2/__init__.py
from agents.workflow_v2.calculation import solve_calculation
from agents.workflow_v2.classifier import classify, is_calculation, is_retrieval
from agents.workflow_v2.retrieval import solve_retrieval

__all__ = ["classify", "is_calculation", "is_retrieval", "solve_calculation", "solve_retrieval"]
```

- [ ] **Step 5: Run calculation tests**

Run: `rtk pytest tests/test_workflow_v2_calculation.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add agents/workflow_v2/__init__.py agents/workflow_v2/calculation.py tests/test_workflow_v2_calculation.py
rtk git commit -m "feat: add workflow v2 calculation solver"
```

## Task 4: Knowledge Solver

**Files:**
- Create: `agents/workflow_v2/knowledge.py`
- Modify: `agents/workflow_v2/__init__.py`
- Test: `tests/test_workflow_v2_knowledge.py`

- [ ] **Step 1: Write failing knowledge tests**

```python
# tests/test_workflow_v2_knowledge.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_workflow_v2_knowledge.py -q`

Expected: FAIL with missing `agents.workflow_v2.knowledge`.

- [ ] **Step 3: Implement knowledge solver**

```python
# agents/workflow_v2/knowledge.py
from __future__ import annotations

from collections import Counter
import re
from typing import Any

KNOWLEDGE_PROMPT = """Bạn là một trợ lý thông minh. Hãy trả lời câu hỏi dưới đây.

Câu hỏi:
{question}

Các lựa chọn:
{options_text}

Hãy suy nghĩ từng bước, sau đó trả lời theo đúng format:
ANSWER: <chữ cái đáp án, ví dụ A hoặc B hoặc C hoặc D>
CONFIDENCE: <số từ 0.0 đến 1.0>
"""


def row_options(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance(row.get("options"), dict):
        return row["options"]
    return {key: row.get(key, "") for key in ("A", "B", "C", "D") if key in row}


def build_knowledge_prompt(question: str, options: dict[str, Any]) -> str:
    options_text = "\n".join(f"{key}. {value}" for key, value in options.items())
    return KNOWLEDGE_PROMPT.format(question=question, options_text=options_text)


def extract_answer(response: str) -> str | None:
    match = re.search(r"ANSWER:\s*([A-Ja-j])", response or "")
    return match.group(1).upper() if match else None


def extract_self_confidence(response: str) -> float:
    match = re.search(r"CONFIDENCE:\s*([\d.]+)", response or "")
    if not match:
        return 0.5
    try:
        return max(0.0, min(1.0, float(match.group(1))))
    except ValueError:
        return 0.5


def consistency_score(answers: list[str]) -> float:
    if not answers:
        return 0.0
    return Counter(answers).most_common(1)[0][1] / len(answers)


def majority_vote(answers: list[str]) -> str | None:
    if not answers:
        return None
    return Counter(answers).most_common(1)[0][0]


def solve_knowledge(text: str, row: dict[str, Any], call_llm_fn, n_samples: int = 3) -> dict:
    prompt = build_knowledge_prompt(text, row_options(row))
    answers = []
    self_confs = []
    for _ in range(n_samples):
        response = call_llm_fn(prompt, temperature=0.7)
        answer = extract_answer(response)
        if answer:
            answers.append(answer)
            self_confs.append(extract_self_confidence(response))
    best_answer = majority_vote(answers)
    avg_self_conf = sum(self_confs) / len(self_confs) if self_confs else 0.5
    final_conf = round(0.7 * consistency_score(answers) + 0.3 * avg_self_conf, 2)
    return {"answer": best_answer, "confidence": final_conf, "votes": dict(Counter(answers)), "n_samples": len(answers)}
```

- [ ] **Step 4: Export knowledge solver**

```python
# agents/workflow_v2/__init__.py
from agents.workflow_v2.calculation import solve_calculation
from agents.workflow_v2.classifier import classify, is_calculation, is_retrieval
from agents.workflow_v2.knowledge import solve_knowledge
from agents.workflow_v2.retrieval import solve_retrieval

__all__ = ["classify", "is_calculation", "is_retrieval", "solve_calculation", "solve_knowledge", "solve_retrieval"]
```

- [ ] **Step 5: Run knowledge tests**

Run: `rtk pytest tests/test_workflow_v2_knowledge.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add agents/workflow_v2/__init__.py agents/workflow_v2/knowledge.py tests/test_workflow_v2_knowledge.py
rtk git commit -m "feat: add workflow v2 knowledge solver"
```

## Task 5: Pipeline Entry Point

**Files:**
- Create: `agents/workflow_v2/pipeline.py`
- Modify: `agents/workflow_v2/__init__.py`
- Test: `tests/test_workflow_v2_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

```python
# tests/test_workflow_v2_pipeline.py
from agents.workflow_v2.pipeline import run_pipeline


def test_pipeline_routes_retrieval_before_calculation():
    text = "Đoạn thông tin: 2 + 2 = 4 trong đoạn này.\n\nCâu hỏi: Kết quả là gì?"
    result = run_pipeline(text, {"A": "4", "B": "5"}, lambda prompt, **kwargs: "4")
    assert result["task"] == "retrieval"
    assert result["answer"] == "4"
    assert result["confidence"] == 0.8


def test_pipeline_routes_calculation():
    result = run_pipeline("Tính 2 + 2", {"A": "3", "B": "4"}, lambda prompt, **kwargs: "")
    assert result["task"] == "calculation"
    assert result["answer"] == "B"


def test_pipeline_routes_knowledge():
    result = run_pipeline("Thủ đô Việt Nam?", {"A": "Hà Nội", "B": "Huế"}, lambda prompt, **kwargs: "ANSWER: A\nCONFIDENCE: 0.8")
    assert result["task"] == "knowledge"
    assert result["answer"] == "A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_workflow_v2_pipeline.py -q`

Expected: FAIL with missing `agents.workflow_v2.pipeline`.

- [ ] **Step 3: Implement pipeline**

```python
# agents/workflow_v2/pipeline.py
from __future__ import annotations

from typing import Any

from agents.workflow_v2.calculation import solve_calculation
from agents.workflow_v2.classifier import classify
from agents.workflow_v2.knowledge import solve_knowledge
from agents.workflow_v2.retrieval import solve_retrieval


def run_pipeline(text: str, row: dict[str, Any], call_llm_fn) -> dict:
    task = classify(text, row)
    if task == "retrieval":
        result = solve_retrieval(text, call_llm_fn)
    elif task == "calculation":
        result = solve_calculation(text, row, call_llm_fn)
    else:
        result = solve_knowledge(text, row, call_llm_fn)
    return {"task": task, "answer": result.get("answer"), "confidence": result.get("confidence", 0.0), "detail": result}
```

- [ ] **Step 4: Export pipeline**

```python
# agents/workflow_v2/__init__.py
from agents.workflow_v2.calculation import solve_calculation
from agents.workflow_v2.classifier import classify, is_calculation, is_retrieval
from agents.workflow_v2.knowledge import solve_knowledge
from agents.workflow_v2.pipeline import run_pipeline
from agents.workflow_v2.retrieval import solve_retrieval

__all__ = [
    "classify",
    "is_calculation",
    "is_retrieval",
    "run_pipeline",
    "solve_calculation",
    "solve_knowledge",
    "solve_retrieval",
]
```

- [ ] **Step 5: Run pipeline tests**

Run: `rtk pytest tests/test_workflow_v2_pipeline.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add agents/workflow_v2/__init__.py agents/workflow_v2/pipeline.py tests/test_workflow_v2_pipeline.py
rtk git commit -m "feat: add workflow v2 pipeline entrypoint"
```

## Task 6: Integrate Workflow V2 Into CSV Runner

**Files:**
- Modify: `main.py`
- Test: `tests/test_main_workflow_v2.py`

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_main_workflow_v2.py
import csv
import tempfile
from pathlib import Path
from unittest.mock import patch

import main
from agents.web_search import StaticWebSearch


def test_run_uses_workflow_v2_for_calculation_rows():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "public_test.csv"
        output_path = tmp_path / "pred.csv"
        input_path.write_text(
            "qid,question,A,B,C,D\n"
            "1,Tính 2 + 2,3,4,5,6\n",
            encoding="utf-8",
        )

        with patch.object(main, "agent", return_value="qid,answer\n1,A\n"):
            main.run(input_path=input_path, output_path=output_path, batch_size=10, search_client=StaticWebSearch({}))

        with output_path.open(newline="", encoding="utf-8") as f:
            assert list(csv.DictReader(f)) == [{"qid": "1", "answer": "B"}]

        with output_path.with_name("pred_audit.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["confidence"] == "0.95"
        assert rows[0]["answer_source"] == "workflow_v2:calculation"


def test_run_preserves_batch_for_non_workflow_fallback_when_pipeline_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "public_test.csv"
        output_path = tmp_path / "pred.csv"
        input_path.write_text(
            "qid,question,A,B,C,D\n"
            "1,one,a,b,c,d\n",
            encoding="utf-8",
        )

        with patch.object(main, "agent", return_value="qid,answer\n1,C\n"):
            main.run(input_path=input_path, output_path=output_path, batch_size=10, search_client=StaticWebSearch({}))

        with output_path.open(newline="", encoding="utf-8") as f:
            assert list(csv.DictReader(f)) == [{"qid": "1", "answer": "C"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_main_workflow_v2.py -q`

Expected: FAIL because `main.run` does not call workflow-v2 and audit lacks `answer_source`.

- [ ] **Step 3: Modify `main.py` imports and audit schema**

Add import:

```python
from agents.workflow_v2.pipeline import run_pipeline as run_workflow_v2
```

Change `write_audit` fieldnames:

```python
writer = csv.DictWriter(
    f,
    fieldnames=["qid", "answer", "confidence", "needs_search", "search_used", "answer_source"],
)
```

Change each `build_audit_rows` item:

```python
"answer_source": answer_sources.get(qid, "batch"),
```

- [ ] **Step 4: Add row-level workflow helper in `main.py`**

```python
def workflow_v2_answer(row: dict[str, str]) -> tuple[str, float, str] | None:
    result = run_workflow_v2(row.get("question", ""), row, agent)
    answer = (result.get("answer") or "N/A").strip().upper()
    if answer not in VALID_ANSWERS:
        return None
    confidence = float(result.get("confidence") or 0.0)
    if answer == "N/A" or confidence <= 0.0:
        return None
    return answer, confidence, f"workflow_v2:{result.get('task', 'unknown')}"
```

- [ ] **Step 5: Wire helper into the per-row loop before old calculator/domain/search branching**

Inside `for row in batch:` after `qid`, `conf`, and `ans` are assigned:

```python
workflow_answer = workflow_v2_answer(row)
if workflow_answer is not None:
    wf_answer, wf_confidence, wf_source = workflow_answer
    batch_answers[qid] = wf_answer
    answer_logprobs[qid] = wf_confidence
    answer_sources[qid] = wf_source
    continue
```

Keep the existing calculator block below this as compatibility fallback for any workflow-v2 miss.

- [ ] **Step 6: Update existing audit tests for new column**

In `tests/test_main.py`, every expected audit dict must include `"answer_source": "<expected source>"`. For current tests:

```python
{"qid": "1", "answer": "A", "confidence": "0.70", "needs_search": "false", "search_used": "false", "answer_source": "batch"}
```

Use `"single_retry"` for rows recovered by `retry_bad_rows`, `"calculator"` for legacy calculator fallback, and existing domain retry source names where applicable.

- [ ] **Step 7: Run main integration tests**

Run: `rtk pytest tests/test_main.py tests/test_main_workflow_v2.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
rtk git add main.py tests/test_main.py tests/test_main_workflow_v2.py
rtk git commit -m "feat: route csv rows through workflow v2"
```

## Task 7: Dependency And Full Verification

**Files:**
- Modify: `requirements.txt`
- Optional modify: `docs/workflow_v2.md` only if documenting implementation status is requested separately.

- [ ] **Step 1: Decide dependency mode**

Use fallback-only mode if avoiding dependency churn. Use package mode if retrieval quality matters more than image size.

Package mode change:

```text
rank_bm25==0.2.2
```

- [ ] **Step 2: Run focused workflow tests**

Run:

```bash
rtk pytest tests/test_workflow_v2_classifier.py tests/test_workflow_v2_retrieval.py tests/test_workflow_v2_calculation.py tests/test_workflow_v2_knowledge.py tests/test_workflow_v2_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
rtk pytest -q
```

Expected: PASS.

- [ ] **Step 4: Check git status**

Run:

```bash
rtk git status --short
```

Expected: only planned files changed, plus pre-existing user changes remain untouched:

```text
 M docs/new_ver_flow.md
?? docs/workflow_v2.md
```

If those two entries still appear, do not revert them.

- [ ] **Step 5: Commit dependency decision**

If `requirements.txt` changed:

```bash
rtk git add requirements.txt
rtk git commit -m "chore: add workflow v2 retrieval dependency"
```

If no dependency changed, skip this commit.

## Self-Review

- Spec coverage:
  - Priority classifier is covered in Task 1 and Task 5.
  - Retrieval parse/chunk/BM25/rerank/prompt/solve is covered in Task 2.
  - Calculation option parsing/type detection/safe eval/LLM fallback/nearest option/confidence is covered in Task 3.
  - Knowledge prompt/three samples/majority vote/confidence blend is covered in Task 4.
  - Entry point output `{task, answer, confidence, detail}` is covered in Task 5.
  - CSV runner integration and audit visibility are covered in Task 6.
- Placeholder scan:
  - No task uses placeholder markers or vague "add tests" language.
  - Each code-changing task includes concrete test and implementation snippets.
- Type consistency:
  - `call_llm_fn(prompt, **kwargs)` is used consistently so existing `agent(prompt)` still works through Python's normal callable path only where no kwargs are passed; knowledge tests require a fake that accepts `temperature`.
  - `row` supports both existing CSV shape (`A`, `B`, `C`, `D`) and spec shape (`options`).
  - `answer_source` values are strings and fit the existing `answer_sources` map.
