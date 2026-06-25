# Work Flow ver 2 #

## Phân tích câu hỏi## 

Câu hỏi từ đánh vào 3 khả năng chính : 
+ retrieval: khả năng đọc hiểu của Agent
+ calculation : khả năng tính toán của agent 
+ Confidence scoring: khả năng trả lời câu hỏi "knowledge" của agent 

Từ phân tích từ các câu hỏi đã được đưa ra ta sẽ thiết kế work flow pipeline riêng biệt xử lý cho 3 phần trên. 



## clasification type ##

Ở phase này ta cần phân loại các câu hỏi đầu vào là thuộc phần nào trong 3 phần đã phân tích ở câu hỏi để  có thể đưa vào pipeline chuyên biệt để  để xử lý. 

Dùng: 
+ regex  
+ heuristic scoring 

**Rule detect retrieval**

câu hỏi phần này thường sẽ có dạng sau: 

```
"Đoạn thông tin:..... Tổng quan(nội dung)/n....... câu hỏi/n" 
```
từ đây ta có thể thấy signal cực mạnh để phân loại vào phần 1. 

đó là khi thấy phần đầu của câu hỏi là `đoạn thông tin` thì sẽ đưa vào phần 1 (retrieval) 
```python
if "Đoạn thông tin" in text and "Câu hỏi" in text: 
    task = 'retrieval' 
```

**Rule detect calculation** 


dùng python calculator: 

ta sẽ chia làm 3 phần: 

```python
simple
medium
complex
```
phần 1 : simple 

câu solve bằng regex/ safe_eval được: 

ví dụ :
 
```
2 + 3 = ?
15 * 7 = ?
```

hoặc: 
```
2x + 4 = 10
```

signal: 
- expression rõ ràng
- linear equation
- ít text
- ít reasoning

Dectect: 
```python 
if has_math_expression:
    return "simple"
```
ví dụ: 
```python 
_EXPR_RE
_LINEAR_RE
```
match được -> simple 

phần 2: Medium 

Có word problem nhưng formula khá direct.

ví dụ: 

```
Một hình trụ bán kính 5 cm.
Nước dâng 3 cm/s.
Tính tốc độ thay đổi thể tích.
```

Không có expression sẵn. 

Nhưng có: 
+ nhiều số
+ units
+ toán ứng dụng

Signal: 
1. Number count cao: 

```python 
num_count >= 2
```

2. Có units 

```
cm, m, kg, lít, đồng, %, m/s
```
3. có calculation keyworks 
```python
[
  "tính",
  "bao nhiêu",
  "calculate",
  "find"
]
```

Phần 3: complex 

có thể là :

probability
combinatorics
calculus
finance
optimization 

ví dụ: 
```
Có 5 bi đỏ, 3 bi xanh...
Xác suất...
```

hoặc: 
```
Một khoản đầu tư tăng 7% mỗi năm...
```

signal keywords: 

```python
complex_keywords = [
    "xác suất",
    "probability",
    "log",
    "sin",
    "cos",
    "đạo hàm",
    "tích phân",
    "lãi suất",
]
```
Cách classify recommend

Đừng classify kiểu AI trước.

Dùng score.

Pseudo:
```python
def classify_calculation(question, row):
    if _EXPR_RE.search(question):
        return "simple"

    if _LINEAR_RE.search(question):
        return "simple"

    score = 0
```

Count numbers
```python
numbers = len(re.findall(r'\d+(\.\d+)?', question))
```
Units
```python
units = [
    "cm", "m", "kg", "km",
    "%", "đồng", "lít"
]
Complex keywords
complex_words = [
    "xác suất",
    "probability",
    "đạo hàm",
    "lãi suất"
]
```
Scoring:
```python
if numbers >= 2:
    score += 0.3

if has_units:
    score += 0.3

if numeric_options:
    score += 0.2

if has_complex_keyword:
    score += 0.4
```
Decision:
```python
if score >= 0.5:
    return "complex"

Else:

return "unknown
```

**Rule detect Confidence scoring**

sau khi đã detect 2 phần trên thì còn lại sẽ thuộc phần này. 

## Pipeline cho từng Phần 

### Pipeline Retrieval ###

Bước 1: 

parse question/context: 

đầu vào của phần này sẽ có dạng: 

```markdown
"Đoạn thông tin:..... Tổng quan(nội dung)/n....... câu hỏi/n" 
```
nên ta cần parse 

context sẽ là `Đoạn thông tin: ...` 
câu hỏi sẽ là `câu hỏi/n ...` 

Bước 2: 

Chunk context 

vì context sẽ rất dài và lớn nên ta cần chia nhỏ ra nhiều đoạn để  tìm được keyword cho câu trả lời. 

ta sẽ chunk context theo kiểu `\n\n` 

tức là 
```
"Đoạn thông tin: \n chunk_1 \n\n chunk_2 \n\n chunk_3"
```

ví dụ: 

```
Đoạn thông tin:

[Chunk 1 | score = ...]
Tiêu đề: Friedrich Wilhelm I của Phổ

[Chunk 2 | score = ...]
I. Thân thế
...

[Chunk 3 | score = ...]
II. Nhà vua nước Phổ
Friedrich Wilhelm I được xem là người cha của chủ nghĩa quân phiệt Phổ...
Nhà vua chú tâm vào việc xây dựng quân đội...

Câu hỏi:
Tại sao Friedrich Wilhelm I được gọi là vua chiến sĩ?
```

Bước 3: 

và ta sẽ dùng BM25 để  chọn ra chunk nào có điểm cao nhất với câu hỏi và score ở trên là BM25 score.   

dùng bm25 để  retrieval top 10 chunks 

```python 
top10 = bm25(question,chunks)
```
sau đó ta sẽ dùng model để rerank lại lấy top 3 

```python
top3 = rerank(question,top10)
```

Bước 4 

ta sẽ build context: 

```
Đoạn thông tin:

[Chunk 1]
...

[Chunk 2]
...

[Chunk 3]
...

Câu hỏi:
...
```

hàm ví dụ: 

```python
context = "\n\n".join(
    f"[Chunk {i+1}]\n{chunk}"
    for i, chunk in enumerate(top_chunks)
)
```
prompt ví dụ : 

```python 
prompt = f"""
Dựa vào đoạn thông tin dưới đây, hãy trả lời câu hỏi.

Đoạn thông tin:
{context}

Câu hỏi:
{question}
"""
```
rồi đưa vào LLM để ra đáp á 

pipeline 
```
input
↓
clasifier 
↓
chunk by \n\n 
↓
BM25 retrieve 
↓
rerank
↓
build context 
↓
LLM answer
```

### pipeline calculation ###


pipeline: 

```
Input
↓
1. Detect calculation question
↓
2. Parse options A/B/C/D/...
↓
3. Classify calculation type
↓
4. Solve
↓
5. Match option
↓
6. Confidence scoring
```

bước 1: 

xác định 

```
Có phải là câu toán hay không?
```

Signals:

+ nhiều số
+ units
+ latex
+ calc keywords
+ numeric options

Ví dụ: 

```python 
calc_keywords = [
    "tính",
    "bao nhiêu",
    "calculate",
    "find",
    "xác suất",
    "đạo hàm",
]
```

ví dụ hàm : 

```python

def is_calculation(row):
    score = 0

    if many_numbers:
        score += 0.3

    if numeric_options:
        score += 0.3

    if has_math_keywords:
        score += 0.4
    return score > 0.5
```

bước 2: 
parse answer 

có thể  lên tới 10 đáp án để chọn
ví dụ: 
```
A. 3.14
B. 3.15
C. 3.16
D. 3.17
...
```
convert thành: 

```python
{
    "A": 3.14,
    "B": 3.15,
    "C": 3.16,
    "D": 3.17,
    "E": 3.18,
    ...
}
```
Handle:
+ VN format 400.000
+ decimal 3,14
+ units

ví dụ: 

```
400.000 đồng
```

parse: 
```python
400000
```
Bước 3 : 

phân loại dạng toán

dạng 1: Simple arithmetic

là các loại dạng toán đơn giản

ví dụ
```
2 + 3 = ?

7 * 9
```
Regex detect: 
```
_EXPR_RE
```

route:
```
safe eval
```

 dạng 2: Equation

 ví dụ: 

 ```
 2x + 7 = 6
 ```
 route: 
 ```
 equation solver
 ```


 dạng 3: word problem

 ví dụ: 
 ```
 Một hình trụ bán kính 5 cm...
 ``` 

 route:
 ```
 LLM code generation
 ```

 dạng 4: Complex math / LaTeX

 ví dụ :

 ```latex
\int_0^1 x^2 dx
 ```
 route: 
+ code generation
+ symbolic solver

hàm ví dụ: 

```python
def classify_calc(question):
    if expr_match:
        return "arithmetic"

    if equation_match:
        return "equation"

    if has_latex:
        return "complex"

    return "word_problem"
```

Bước 4: 

giải quyết bài toán: 

Nhánh A: Arithmetic

```python
result = safe_eval(expr)
```
ví dụ: 
```
3 + 4 * 2
```

Nhánh B: Equation 

```python
result = solve_linear(question)
```
ví dụ: 
```
2x + 4 = 10
```

Nhánh C: Words problem

prompt:
```
You are a calculation engine.

Solve the problem.
Output EXACTLY one line:
result = <expression>
```
input: 
```
Một hình trụ bán kính 5 cm...
```
output model: 
```python
result = math.pi * (5**2) * 3
```

eval: 
```
safe_eval(result)
```

Nhánh D: Complex / LaTeX

ví dụ: 
```latex
\frac{3}{4}+\frac{1}{2}
```

Nếu simple latex:

+ normalize rồi eval

Nếu hard:

+ route sang LLM codegen

Bước 5 : math answer

không match exact

sai lầm phổ biến 
bad

```python
if abs(val - result) < 1e-6
```

good: 

Nearest option.

```python
best = min(opts.items(), key=lambda x: abs(x[1] - result))
```
ví dụ: 

resutl: 
```
3.1415926 
```

answer:
```
A=3.14
B=3.15
```
-> chọn A

hàm: 
```python
def match_option(result, opts):
    best_opt = None
    best_diff = inf
```

Bước 6: Confidence

Rất nên có.

Arithmetic exact:
```
confidence = 0.95
```
Equation:
```
confidence = 0.9
```
Code generation:
```
confidence = 0.75
```
Rounded nearest option:
```
confidence = 0.5
```

```
return {
   "answer": answer,
   "confidence": confidence
}
```
toàn bộ kiến trúc: 

```
Question
↓
Calculation detector
↓
Calculation classifier
├─ Arithmetic
│   └─ safe eval
│
├─ Equation
│   └─ solver
│
├─ Word problem
│   └─ LLM codegen
│
└─ Complex math
    └─ codegen / symbolic
↓
Option matching
↓
Confidence
```

+ branch đơn giản trước: 
+ fail thì mới LLM

```
ans = try_calculator(row)

if ans:
    return ans

return try_code_calculator(row)
```

### Pipeline reasoning/knowledge

Cái này quan trọng hơn nhiều người nghĩ.

Vì model confidence tự report thường khá… ảo tưởng.

Một trait rất con người.

Signal 1: self confidence

model output: 

```
CONFIDENCE: 0.82

```
Signal 2: logprob 

Nếu lấy được:

+ best token prob
+ answer prob

→ rất useful.

đã có hàm để lấy logprob rồi 

Signal 3: Multi-sample consistency

Cực mạnh.

Run model 3 lần:
```
Run 1 → B
Run 2 → B
Run 3 → C
```
Confidence medium.

ví dụ: 

```python
answers = ["B", "B", "C"]
```
vote: 
```python
B = 2/3
```
Confidence:
```python
0.66
```
Nếu :
```python
answers = ["B", "B", "B"]
```
Confidence rất cao

hàm ví dụ: 
```python
def consistency_score(answers):
    counter = Counter(answers)
    return max(counter.values()) / len(answers)
```

strong ver: 
pipeline:
```
Question
↓
LLM sample x3 (temp=0.7)
↓
Majority vote
↓
Final answer
```

full knowledge pipeline:
```
Question
↓
LLM x3
↓
Parse answers
↓
Majority vote
↓
Confidence score
```

```python
def solve_knowledge(question, options, call_agent_fn):
    answers = []

    for _ in range(3):
        response = call_agent_fn(build_prompt(question, options))
        ans = extract_answer(response)

        if ans:
            answers.append(ans)
```

vote:
```
best = Counter(answers).most_common(1)[0]
```

return: 
```python
return {
   "answer": best_answer,
   "confidence": freq / len(answers)
}
```

Full architecture
```
Question
↓
Phase 1 Classifier
├─ Retrieval
│   ├─ BM25
│   ├─ Rerank
│   └─ LLM
│
├─ Calculation
│   ├─ Rule-based
│   ├─ Solver
│   └─ Codegen
│
└─ Knowledge
    ├─ Direct LLM
    ├─ Self consistency
    └─ Voting
```
```python
final_confidence = max(
    retrieval_conf,
    calc_conf,
    knowledge_conf
)
```
