# Domain Retry Plan

Tài liệu này mô tả hướng cải thiện accuracy cho các câu hỏi theo domain, trước mắt tập trung vào toán/STEM, mà không làm tăng latency quá nhiều cho toàn bộ pipeline.

## 1. Mục tiêu

Hiện tại pipeline đã có batch prediction, retry khi model trả `N/A`, và web search cho câu cần thông tin cập nhật. Sau khi test thực tế, agent sai khá nhiều ở phần toán. Lý do chính:

- Toán thường cần suy luận nhiều bước, kiểm tra phép tính và thay đáp án ngược lại đề.
- Batch prompt chung dễ làm model trả lời nhanh nhưng thiếu kiểm chứng từng câu.
- Web search không phù hợp với toán thuần, vì lỗi nằm ở reasoning/tính toán chứ không phải thiếu dữ kiện cập nhật.

Mục tiêu của domain retry:

- Chỉ retry các câu có rủi ro cao, đặc biệt là toán/STEM.
- Không gọi thêm model cho mọi câu.
- Giữ `pred.csv` là đáp án cuối cùng tốt nhất.
- Giữ `pred_audit.csv` đủ thông tin để biết đáp án trước/sau các bước retry/search.

## 2. Nguyên tắc thiết kế

### 2.1. Dùng rule-based router trước

Không dùng model để classify domain ở bước đầu, vì nếu mỗi câu phải gọi model để phân loại rồi mới gọi model để trả lời thì latency có thể tăng gần gấp đôi.

Nên tạo `agents/subject_router.py` với rule-based classifier đơn giản:

- `math`: câu hỏi có dấu hiệu toán, số học, phương trình, phần trăm, xác suất, hình học, biểu thức.
- `stem`: vật lý, hóa học, sinh học, công thức, đơn vị đo.
- `current`: câu hỏi có yếu tố thời sự/cập nhật như “hiện nay”, “mới nhất”, CEO, giá, thống kê mới.
- `general`: còn lại.

Router này phải chạy local, không network, không model call.

### 2.2. Prompt bổ sung ngắn theo domain

Không viết lại toàn bộ system prompt cho từng domain. Chỉ thêm một prompt retry ngắn cho domain cần xử lý.

Với toán, retry prompt nên ép model:

- Giải lại câu hỏi độc lập.
- Tính toán cẩn thận.
- Thử thay từng đáp án A/B/C/D vào đề nếu có thể.
- Loại đáp án không thỏa mãn điều kiện.
- Chỉ xuất CSV `qid,answer`.

Ví dụ ý tưởng prompt:

```text
Đây là câu hỏi toán/STEM. Hãy giải lại cẩn thận, kiểm tra phép tính, và nếu có thể hãy thay từng đáp án A/B/C/D ngược vào đề để xác minh. Chỉ trả về đúng CSV qid,answer. Không giải thích.
```

### 2.3. Không retry toàn batch

Retry domain nên chạy từng câu. Nếu retry cả batch, model dễ bị nhiễu giữa các câu và thời gian tăng không cần thiết.

Chỉ retry câu thuộc domain có rủi ro cao hoặc câu có answer ban đầu là `N/A`.

### 2.4. Temperature hiện đã là 0

`agents/agent.py` hiện đã cấu hình:

```python
"temperature": 0
```

Vì vậy không cần thêm bước “set temperature=0 cho STEM” như một task riêng. Khi implement, chỉ cần đảm bảo retry domain vẫn đi qua `agent()` hoặc cấu hình tương đương để giữ temperature bằng 0.

## 3. Flow đề xuất

Flow mới nên là:

```text
Đọc input CSV
  ↓
Chia batch
  ↓
Predict batch bằng model local
  ↓
Retry các câu trả N/A bằng retry hiện tại
  ↓
Classify domain từng câu bằng subject_router.py
  ↓
Domain retry cho câu toán/STEM có rủi ro
  ↓
Lưu snapshot answer trước web_search để ghi audit
  ↓
Web search cho câu cần thông tin cập nhật
  ↓
Ghi pred.csv bằng answer cuối cùng
  ↓
Ghi pred_audit.csv bằng thông tin audit
```

Chi tiết từng bước:

### Bước 1. Batch prediction

Giữ nguyên `predict_batch()` hiện tại. Đây là bước nhanh nhất vì model xử lý nhiều câu trong một prompt.

Output tạm:

```python
batch_answers = {qid: answer}
```

### Bước 2. Retry N/A hiện tại

Giữ `retry_bad_rows()` cho các câu model không trả được đáp án hợp lệ.

Mục đích bước này là sửa lỗi format hoặc trường hợp model bỏ sót qid.

### Bước 3. Subject routing

Thêm module mới:

```text
agents/subject_router.py
```

API đề xuất:

```python
def classify_subject(row: dict[str, str]) -> SubjectDecision:
    ...
```

Trong đó `SubjectDecision` có thể gồm:

```python
@dataclass(frozen=True)
class SubjectDecision:
    subject: str
    needs_domain_retry: bool
    reason: str
```

Ví dụ:

```python
SubjectDecision("math", True, "math_keyword:phương trình")
SubjectDecision("general", False, "no_domain_signal")
```

### Bước 4. Domain retry cho toán/STEM

Thêm function:

```python
def retry_domain_rows(rows, answers):
    ...
```

Logic đề xuất:

```text
for row in rows:
    qid = row["qid"]
    current_answer = answers.get(qid, "N/A")
    decision = classify_subject(row)

    if not decision.needs_domain_retry:
        continue

    retry_answer = predict_domain_retry(row, decision.subject)

    nếu retry_answer hợp lệ:
        answers[qid] = retry_answer
```

Ban đầu chỉ nên bật retry cho `math` và một phần `stem`. Không nên retry mọi domain ngay.

Cần lưu ý: retry toán không chỉ nên chạy khi answer là `N/A`. Nhiều lỗi toán là model chọn sai A/B/C/D nhưng vẫn rất tự tin. Vì vậy điều kiện nên là:

- retry nếu subject là `math`; hoặc
- retry nếu subject là `stem` và answer là `N/A`; hoặc
- retry nếu câu có dấu hiệu tính toán rõ như số, `%`, phương trình, biểu thức.

### Bước 5. Snapshot audit trước web search

Sau domain retry, lưu snapshot:

```python
audit_answers.update(batch_answers)
```

Snapshot này là đáp án trước web search.

Hiện repo đã có thay đổi theo hướng này: `pred_audit.csv` ghi answer trước web search, còn `pred.csv` ghi answer cuối cùng sau web search.

Khi thêm domain retry, cần quyết định audit ghi answer ở thời điểm nào. Đề xuất:

- `answer`: đáp án sau batch + N/A retry + domain retry, nhưng trước web search.
- `search_used`: web search có chạy thật không.
- Nếu cần debug domain retry sâu hơn, thêm cột mới ở bước sau.

### Bước 6. Web search

Giữ web search sau domain retry.

Lý do:

- Toán thuần không nên search.
- Câu current/current-events vẫn cần search sau khi có answer ban đầu.
- Web search nên dùng để sửa thiếu dữ kiện cập nhật, không dùng để sửa tính toán.

Cần chỉnh `search_router.py`: hiện đang có các keyword như `toán`, `hóa`, `lý`, `địa` trong `VOLATILE_KEYWORDS`, khiến nhiều câu học thuật bị đưa sang web search. Nên tách rõ:

- `search_router.py`: chỉ quyết định web search cho dữ kiện cập nhật/volatile.
- `subject_router.py`: quyết định domain retry cho toán/STEM.

Không nên dùng web search cho toán chỉ vì câu có chữ “toán”.

## 4. Audit đề xuất

Hiện audit có các cột:

```text
qid,answer,confidence,needs_search,search_used
```

Khi thêm domain retry, có hai lựa chọn.

### Lựa chọn A: Không thêm cột audit

Giữ audit như hiện tại. `answer` là answer trước web search, đã bao gồm domain retry nếu có.

Ưu điểm:

- Ít thay đổi file output.
- Không phá các script đang đọc audit hiện tại.

Nhược điểm:

- Khó biết câu nào được domain retry.
- Khó so sánh answer trước và sau domain retry.

### Lựa chọn B: Thêm cột audit cho domain retry

Thêm các cột:

```text
domain,domain_retry_used,answer_before_domain_retry
```

Ví dụ:

```text
qid,answer,confidence,needs_search,search_used,domain,domain_retry_used,answer_before_domain_retry
1,C,0.90,false,false,math,true,A
```

Ưu điểm:

- Dễ đo hiệu quả domain retry.
- Dễ biết retry có làm đúng hơn hay làm hỏng đáp án.

Nhược điểm:

- Thay đổi schema audit.
- Cần update test và tooling đọc audit.

Khuyến nghị: nếu đang trong giai đoạn thử nghiệm accuracy, chọn B. Nếu đã có tool downstream phụ thuộc audit schema, chọn A trước rồi thêm cột sau.

## 5. Thứ tự implement đề xuất

### Phase 1. Subject router

Tạo `agents/subject_router.py` và test riêng.

Test nên cover:

- Phương trình → `math`, retry true.
- Phần trăm/xác suất → `math`, retry true.
- CEO hiện nay → `current`, retry false.
- Câu kiến thức thường → `general`, retry false.

### Phase 2. Math retry prompt

Thêm:

```python
def domain_retry_prompt(row, subject):
    ...

def predict_domain_retry(row, subject):
    ...
```

Test bằng mock `agent()`:

- Batch trả `A`.
- Math retry trả `C`.
- Final answer phải là `C`.

### Phase 3. Tích hợp vào `run()`

Flow trong `run()` nên thành:

```python
batch_answers = predict_batch(batch)
batch_answers = retry_bad_rows(batch, batch_answers)
batch_answers = retry_domain_rows(batch, batch_answers)
audit_answers.update(batch_answers)
answers.update(apply_web_search(batch, batch_answers, search_client, search_used_qids))
```

Điểm quan trọng: domain retry phải chạy trước `audit_answers.update(...)` nếu muốn audit answer phản ánh kết quả retry domain trước web search.

### Phase 4. Tách web search router khỏi subject router

Xóa các keyword học thuật khỏi `VOLATILE_KEYWORDS` nếu chúng không đại diện cho dữ kiện cập nhật.

Ví dụ nên bỏ khỏi web search router:

```text
toán, toán học, hóa, hóa học, lý, vật lý, địa, địa lý, diện tích
```

Những từ này không nhất thiết cần web search. Chúng nên thuộc subject routing hoặc rule riêng.

### Phase 5. Đo accuracy và latency

Chạy cùng một tập test với 2 mode:

- baseline: batch + N/A retry + web search hiện tại.
- domain retry: batch + N/A retry + math retry + web search.

Cần đo:

- Accuracy tổng.
- Accuracy riêng câu toán/STEM.
- Số câu bị retry domain.
- Số câu bị web search.
- Runtime tổng.

Chỉ giữ domain retry nếu accuracy tăng đủ đáng kể so với runtime tăng thêm.

## 6. Rủi ro

### 6.1. Retry làm sai câu vốn đúng

Math retry có thể sửa sai nhưng cũng có thể đổi đáp án đúng thành sai. Vì vậy audit nên lưu `answer_before_domain_retry` trong giai đoạn thử nghiệm.

### 6.2. Router bắt nhầm domain

Rule-based router có thể bắt nhầm câu có số nhưng không phải toán. Ví dụ câu lịch sử có năm 1945 không nên bị math retry.

Cần viết rule cẩn thận:

- Có số thôi chưa đủ để classify math.
- Cần kết hợp với keyword như `tính`, `bằng bao nhiêu`, `phương trình`, `%`, `x`, `diện tích`, `chu vi`, `xác suất`, `trung bình`.

### 6.3. Web search bị dùng sai cho câu học thuật

Nếu `search_router.py` vẫn coi `toán/hóa/lý/địa` là volatile keyword, pipeline sẽ search quá nhiều và chậm hơn. Cần tách domain routing khỏi search routing.

### 6.4. Python executor/tool calling

Python executor có thể tăng accuracy cho arithmetic nhưng không nên làm ngay. Nếu để model sinh code tự do, rủi ro parse sai và tăng complexity. Nếu làm, nên bắt đầu bằng solver hẹp cho biểu thức số học rõ ràng.

## 7. Kết luận

Plan hợp lý nếu triển khai theo hướng incremental:

1. Rule-based `subject_router.py`.
2. Retry prompt ngắn cho toán/STEM.
3. Tích hợp retry trước web search.
4. Audit đủ thông tin để đo retry có giúp thật không.
5. Sau khi đo kết quả mới cân nhắc solver/tool calling.

Không nên viết prompt dài riêng cho mọi domain ngay từ đầu. Cách đó dễ tăng token, khó kiểm soát behavior, và chưa chắc cải thiện accuracy. Nên bắt đầu với toán/STEM vì đây là pain point đã thấy qua test.
