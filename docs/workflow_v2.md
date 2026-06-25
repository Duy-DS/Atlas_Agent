# Work Flow ver 2 (Revised) #

## Tổng quan kiến trúc ##

Pipeline xử lý câu hỏi được chia thành 3 nhánh chuyên biệt:

- **Retrieval** — đọc hiểu đoạn văn bản, tìm thông tin
- **Calculation** — tính toán số học, giải phương trình
- **Knowledge** — câu hỏi kiến thức tổng quát, cần reasoning

---

## Phase 1: Classifier ##

### Nguyên tắc quan trọng: Priority Order ###

Classifier chạy theo thứ tự ưu tiên cố định. Khi câu hỏi thỏa mãn điều kiện đầu tiên thì dừng, không check tiếp.

```
retrieval → calculation → knowledge (fallback)
```

```python
def classify(text: str, row: dict) -> str:
    if is_retrieval(text):
        return "retrieval"
    if is_calculation(text, row):
        return "calculation"
    return "knowledge"
```

---

### Rule detect Retrieval ###

Câu hỏi phần này có dạng:

```
"Đoạn thông tin:..... Tổng quan(nội dung)\n....... câu hỏi\n"
```

Signal cực mạnh: cả hai từ khóa `Đoạn thông tin` và `Câu hỏi` xuất hiện trong cùng một câu.

```python
def is_retrieval(text: str) -> bool:
    return "Đoạn thông tin" in text and "Câu hỏi" in text
```

---

### Rule detect Calculation ###

Dùng heuristic scoring, không dùng LLM ở bước này.

```python
_EXPR_RE    = re.compile(r'\d+\s*[\+\-\*\/\^]\s*\d+')
_LINEAR_RE  = re.compile(r'\d*[xXyY]\s*[\+\-]?\s*\d*\s*=\s*\d+')

CALC_KEYWORDS = ["tính", "bao nhiêu", "calculate", "find", "xác suất", "đạo hàm"]
UNITS         = ["cm", "m", "kg", "km", "%", "đồng", "lít", "m/s"]

def is_calculation(text: str, row: dict) -> bool:
    # Fast-path: có expression rõ ràng
    if _EXPR_RE.search(text) or _LINEAR_RE.search(text):
        return True

    score = 0.0
    numbers      = re.findall(r'\d+(?:[.,]\d+)?', text)
    has_units    = any(u in text for u in UNITS)
    has_keywords = any(k in text.lower() for k in CALC_KEYWORDS)

    # Numeric options trong đáp án (A/B/C/D đều là số)
    options = row.get("options", {})
    numeric_options = sum(
        1 for v in options.values()
        if re.match(r'^[\d.,]+$', str(v).strip())
    )
    has_numeric_opts = numeric_options >= 2

    if len(numbers) >= 2:    score += 0.3
    if has_units:            score += 0.3
    if has_keywords:         score += 0.3
    if has_numeric_opts:     score += 0.2

    return score >= 0.5
```

---

### Rule detect Knowledge (fallback) ###

Sau khi đã loại 2 phần trên, phần còn lại là Knowledge — câu hỏi kiến thức tổng quát, không cần parsing đặc biệt.

---

## Phase 2: Pipeline cho từng Phần ##

---

### Pipeline Retrieval ###

```
input
↓
parse context / question
↓
chunk by \n\n
↓
BM25 retrieve top-K
↓
rerank top 3
↓
build context
↓
LLM answer
```

**Bước 1 — Parse input**

```python
def parse_retrieval_input(text: str) -> tuple[str, str]:
    """
    Tách context và câu hỏi từ input.
    Returns: (context, question)
    """
    parts = text.split("Câu hỏi:")
    context  = parts[0].replace("Đoạn thông tin:", "").strip()
    question = parts[1].strip() if len(parts) > 1 else ""
    return context, question
```

**Bước 2 — Chunk context**

Chunk theo `\n\n`, loại bỏ chunk quá ngắn (< 20 ký tự).

```python
def chunk_context(context: str, min_len: int = 20) -> list[str]:
    chunks = context.split("\n\n")
    return [c.strip() for c in chunks if len(c.strip()) >= min_len]
```

**Bước 3 — BM25 + Rerank**

BM25 lấy top-K (tối đa là số chunk thực tế), sau đó rerank lấy top 3.

```python
from rank_bm25 import BM25Okapi

def bm25_retrieve(question: str, chunks: list[str], top_k: int = 10) -> list[str]:
    top_k = min(top_k, len(chunks))          # Guard: không vượt số chunk thực tế
    tokenized = [c.split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(question.split())
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [chunks[i] for i, _ in ranked[:top_k]]

def rerank(question: str, candidates: list[str], top_n: int = 3) -> list[str]:
    """
    Rerank bằng cross-encoder hoặc LLM scoring.
    Dùng cross-encoder (sentence-transformers) nếu có để tiết kiệm token.
    Fallback: giữ nguyên thứ tự BM25 nếu không có reranker.
    """
    # Option A — cross-encoder (khuyến nghị)
    # from sentence_transformers import CrossEncoder
    # model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    # scores = model.predict([(question, c) for c in candidates])
    # return [candidates[i] for i in sorted(range(len(scores)),
    #         key=lambda x: scores[x], reverse=True)][:top_n]

    # Option B — fallback (giữ BM25 order)
    return candidates[:top_n]
```

> **Lưu ý:** Chọn một trong hai option và nhất quán. Cross-encoder tốt hơn nhiều nhưng cần thêm dependency.

**Bước 4 — Build context + Prompt**

```python
def build_retrieval_context(top_chunks: list[str]) -> str:
    return "\n\n".join(
        f"[Chunk {i+1}]\n{chunk}"
        for i, chunk in enumerate(top_chunks)
    )

def build_retrieval_prompt(context: str, question: str) -> str:
    return f"""Dựa vào đoạn thông tin dưới đây, hãy trả lời câu hỏi.
Chỉ sử dụng thông tin trong đoạn văn, không thêm kiến thức bên ngoài.

Đoạn thông tin:
{context}

Câu hỏi:
{question}
"""
```

**Full function**

```python
def solve_retrieval(text: str, call_llm_fn) -> dict:
    context, question = parse_retrieval_input(text)
    chunks   = chunk_context(context)
    top10    = bm25_retrieve(question, chunks, top_k=10)
    top3     = rerank(question, top10, top_n=3)
    ctx      = build_retrieval_context(top3)
    prompt   = build_retrieval_prompt(ctx, question)
    answer   = call_llm_fn(prompt)
    return {"answer": answer, "confidence": 0.80}
```

---

### Pipeline Calculation ###

```
input
↓
parse options A/B/C/D
↓
classify calculation type
↓
solve (arithmetic / equation / word problem / complex)
↓
match nearest option
↓
confidence scoring
↓
output
```

**Bước 1 — Parse options**

```python
import re

# Format VN: "400.000 đồng" → 400000
# Decimal VN: "3,14" → 3.14
def parse_number_vn(s: str) -> float | None:
    s = s.strip()
    s = re.sub(r'[^\d,.]', '', s)   # bỏ units
    if not s:
        return None
    # Phân biệt: "400.000" (VN thousands) vs "3.14" (decimal)
    if s.count('.') == 1 and len(s.split('.')[1]) != 3:
        return float(s.replace(',', '.'))
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None

def parse_options(raw_options: dict) -> dict:
    """
    raw_options: {"A": "3,14", "B": "400.000 đồng", ...}
    returns:     {"A": 3.14,   "B": 400000.0, ...}
    """
    parsed = {}
    for key, val in raw_options.items():
        num = parse_number_vn(str(val))
        if num is not None:
            parsed[key] = num
    return parsed
```

**Bước 2 — Classify calculation type**

```python
COMPLEX_KEYWORDS = [
    "xác suất", "probability", "log", "sin", "cos", "tan",
    "đạo hàm", "tích phân", "lãi suất", "tổ hợp", "chỉnh hợp"
]

def classify_calculation(question: str) -> str:
    # Simple: có expression trực tiếp
    if _EXPR_RE.search(question):
        return "arithmetic"

    # Simple: linear equation
    if _LINEAR_RE.search(question):
        return "equation"

    # Complex: có từ khóa phức tạp
    if any(kw in question.lower() for kw in COMPLEX_KEYWORDS):
        return "complex"

    # Có LaTeX
    if re.search(r'\\[a-zA-Z]+\{', question) or '\\frac' in question:
        return "complex"

    # Còn lại: word problem (medium)
    return "word_problem"
```

**Bước 3 — Safe eval**

```python
import ast
import operator

_SAFE_OPS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.USub: operator.neg,
}

def safe_eval(expr: str) -> float:
    """Eval biểu thức số học thuần — KHÔNG dùng eval() gốc."""
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            return _SAFE_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return _SAFE_OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported: {node}")
    tree = ast.parse(expr, mode='eval')
    return _eval(tree.body)
```

**Bước 4 — Solvers**

```python
import re

def solve_arithmetic(question: str) -> float | None:
    match = _EXPR_RE.search(question)
    if match:
        try:
            return safe_eval(match.group())
        except Exception:
            return None
    return None

def solve_linear(question: str) -> float | None:
    """Giải phương trình bậc 1 dạng ax + b = c."""
    match = _LINEAR_RE.search(question)
    if not match:
        return None
    expr = match.group()
    # Parse a, b, c từ regex rồi giải
    # Ví dụ đơn giản: "2x + 4 = 10" → x = 3
    try:
        from sympy import symbols, Eq, solve
        x = symbols('x')
        lhs, rhs = expr.split('=')
        lhs = lhs.replace('x', '*x')
        result = solve(Eq(eval(lhs), float(rhs)), x)
        return float(result[0]) if result else None
    except Exception:
        return None

WORD_PROBLEM_PROMPT = """You are a calculation engine. Solve the math problem step by step.

Output EXACTLY one line at the end:
result = <numeric expression using Python math>

Do not output anything after the result line.

Problem:
{question}
"""

def solve_word_problem(question: str, call_llm_fn) -> float | None:
    prompt = WORD_PROBLEM_PROMPT.format(question=question)
    response = call_llm_fn(prompt)
    match = re.search(r'result\s*=\s*(.+)', response)
    if not match:
        return None
    try:
        import math
        return float(safe_eval(match.group(1).strip()))
    except Exception:
        return None

def solve_complex(question: str, call_llm_fn) -> float | None:
    """Dùng LLM codegen cho toán phức tạp / LaTeX."""
    return solve_word_problem(question, call_llm_fn)   # Same flow, khác prompt có thể tùy chỉnh thêm
```

**Bước 5 — Match nearest option**

Không dùng exact match. Luôn lấy option gần nhất.

```python
from math import inf

def match_option(result: float, opts: dict) -> tuple[str, float]:
    """
    Trả về (key, diff) của option gần result nhất.
    """
    best_key  = None
    best_diff = inf
    for key, val in opts.items():
        diff = abs(val - result)
        if diff < best_diff:
            best_diff = diff
            best_key  = key
    return best_key, best_diff
```

**Bước 6 — Confidence scoring**

```python
def calc_confidence(calc_type: str, best_diff: float) -> float:
    base = {
        "arithmetic":   0.95,
        "equation":     0.90,
        "word_problem": 0.75,
        "complex":      0.70,
    }.get(calc_type, 0.60)

    # Penalize nếu khoảng cách với option quá lớn
    if best_diff > 10:
        base *= 0.7
    elif best_diff > 1:
        base *= 0.85

    return round(base, 2)
```

**Full function**

```python
def solve_calculation(text: str, row: dict, call_llm_fn) -> dict:
    options = parse_options(row.get("options", {}))
    calc_type = classify_calculation(text)

    result = None

    if calc_type == "arithmetic":
        result = solve_arithmetic(text)

    if calc_type == "equation":
        result = solve_linear(text)

    if result is None and calc_type in ("word_problem", "complex", "equation"):
        # Fallback sang LLM nếu rule-based thất bại
        result = solve_word_problem(text, call_llm_fn)

    if result is None or not options:
        return {"answer": None, "confidence": 0.0}

    best_key, best_diff = match_option(result, options)
    confidence = calc_confidence(calc_type, best_diff)

    return {
        "answer":     best_key,
        "confidence": confidence,
        "result":     result,
        "calc_type":  calc_type,
    }
```

---

### Pipeline Knowledge ###

```
input
↓
build prompt
↓
LLM x3 (temp=0.7)
↓
parse answers
↓
majority vote
↓
confidence scoring
↓
output
```

**Prompt template (đã thiếu ở bản gốc — bổ sung đầy đủ)**

```python
KNOWLEDGE_PROMPT = """Bạn là một trợ lý thông minh. Hãy trả lời câu hỏi dưới đây.

Câu hỏi:
{question}

Các lựa chọn:
{options_text}

Hãy suy nghĩ từng bước, sau đó trả lời theo đúng format:
ANSWER: <chữ cái đáp án, ví dụ A hoặc B hoặc C hoặc D>
CONFIDENCE: <số từ 0.0 đến 1.0>
"""

def build_knowledge_prompt(question: str, options: dict) -> str:
    options_text = "\n".join(f"{k}. {v}" for k, v in options.items())
    return KNOWLEDGE_PROMPT.format(question=question, options_text=options_text)
```

**Parse answer từ LLM output**

```python
def extract_answer(response: str) -> str | None:
    match = re.search(r'ANSWER:\s*([A-Ja-j])', response)
    return match.group(1).upper() if match else None

def extract_self_confidence(response: str) -> float:
    match = re.search(r'CONFIDENCE:\s*([\d.]+)', response)
    return float(match.group(1)) if match else 0.5
```

**Consistency scoring + majority vote**

```python
from collections import Counter

def consistency_score(answers: list[str]) -> float:
    if not answers:
        return 0.0
    counter = Counter(answers)
    return counter.most_common(1)[0][1] / len(answers)

def majority_vote(answers: list[str]) -> str | None:
    if not answers:
        return None
    return Counter(answers).most_common(1)[0][0]
```

**Full function**

```python
def solve_knowledge(text: str, row: dict, call_llm_fn, n_samples: int = 3) -> dict:
    options  = row.get("options", {})
    prompt   = build_knowledge_prompt(text, options)
    answers  = []
    self_confs = []

    for _ in range(n_samples):
        response = call_llm_fn(prompt, temperature=0.7)
        ans  = extract_answer(response)
        conf = extract_self_confidence(response)
        if ans:
            answers.append(ans)
            self_confs.append(conf)

    best_answer  = majority_vote(answers)
    consist_conf = consistency_score(answers)
    avg_self_conf = sum(self_confs) / len(self_confs) if self_confs else 0.5

    # Blend consistency + self-reported confidence
    # Consistency quan trọng hơn (0.7) vì self-confidence của LLM thường bị inflate
    final_conf = round(0.7 * consist_conf + 0.3 * avg_self_conf, 2)

    return {
        "answer":     best_answer,
        "confidence": final_conf,
        "votes":      dict(Counter(answers)),
        "n_samples":  len(answers),
    }
```

---

## Phase 3: Entry Point ##

```python
def run_pipeline(text: str, row: dict, call_llm_fn) -> dict:
    task = classify(text, row)

    if task == "retrieval":
        result = solve_retrieval(text, call_llm_fn)

    elif task == "calculation":
        result = solve_calculation(text, row, call_llm_fn)

    else:  # knowledge
        result = solve_knowledge(text, row, call_llm_fn)

    # Confidence cuối lấy từ nhánh đã chạy — KHÔNG dùng max()
    return {
        "task":       task,
        "answer":     result.get("answer"),
        "confidence": result.get("confidence", 0.0),
        "detail":     result,
    }
```

---

## Full Architecture ##

```
Question
↓
Phase 1 — Classifier (priority: retrieval → calc → knowledge)
│
├─ Retrieval
│   ├─ parse context / question
│   ├─ chunk by \n\n  (guard min_len)
│   ├─ BM25 top-K  (guard ≤ len(chunks))
│   ├─ rerank top 3  (cross-encoder hoặc fallback)
│   └─ LLM answer
│
├─ Calculation
│   ├─ parse options  (handle VN number format)
│   ├─ classify type  (arithmetic / equation / word_problem / complex)
│   ├─ solve (rule-based trước, LLM fallback sau)
│   ├─ match nearest option
│   └─ confidence scoring
│
└─ Knowledge
    ├─ build prompt  (có template đầy đủ)
    ├─ LLM x3 (temp=0.7)
    ├─ majority vote
    └─ blend confidence (0.7 consistency + 0.3 self-report)
↓
Output: { task, answer, confidence, detail }
```



