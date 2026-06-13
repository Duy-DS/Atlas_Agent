# Flow Agent

Tài liệu này mô tả flow hiện tại của agent trong repo, tính từ lúc đọc câu hỏi CSV đến lúc ghi đáp án và audit.

## 1. Đầu vào và đầu ra

Đầu vào mặc định trong `main.py` là:

```text
data/public_test_80.csv
```

Mỗi row cần có các cột:

```text
qid,question,A,B,C,D
```

Đầu ra gồm:

```text
output/pred.csv        # qid,answer
output/pred_audit.csv  # qid,answer,confidence,needs_search,search_used
```

`answer` hợp lệ chỉ gồm:

```text
A, B, C, D, N/A
```

## 2. Flow tổng quát

```text
read CSV
  -> normalize rows
  -> chia batch theo BATCH_SIZE, mặc định 20
  -> predict_batch_details()
       -> gọi model local một lần cho cả batch
       -> parse answer
       -> tính answer_quality cho từng qid
  -> retry_bad_rows()
       -> gọi model lại từng câu đang N/A
  -> retry_domain_rows()
       -> chỉ gọi model lại khi domain có risk signal hoặc batch parse yếu
  -> apply_web_search()
       -> search nếu answer N/A hoặc câu hỏi có thông tin volatile/current
  -> write pred.csv
  -> write pred_audit.csv
```

## 3. Gọi model

Mỗi lần cần hỏi model, code đi qua `agents.agent.agent()`.

`agent()` gọi Ollama với:

```text
model: MODEL_NAME, mặc định qwen3.5:0.8b
system prompt: prompts/system_prompt.md
think: false
temperature: 0
num_predict: OLLAMA_NUM_PREDICT, mặc định 512
```

Sau khi model trả về, `final_answer()` xóa block `<think>...</think>` nếu có. Pipeline chỉ xử lý phần output còn lại.

## 4. Parse answer và answer_quality

Sau batch call, `parse_model_answers()` cố gắng đọc output model thành map:

```python
{qid: answer}
```

Parser chấp nhận hai dạng chính:

```text
1,A
2: B
```

hoặc CSV có header:

```text
qid,answer
1,A
2,B
```

Sau khi parse, `predict_batch_details()` tính `answer_quality` cho từng row.

### 4.1. clean

`clean` khi output batch có đúng `qid` và đáp án là một trong `A/B/C/D`.

Ví dụ:

```text
qid,answer
1,A
```

Với row có `qid=1`, quality là `clean`.

### 4.2. weak_parse

`weak_parse` khi batch output không map sạch vào đúng `qid`, nhưng fallback vẫn lấy được một đáp án hợp lệ.

Ví dụ single row có `qid=1`, nhưng model trả:

```text
wrong_id,A
```

Với single-row batch, code có thể gán đáp án duy nhất đó về qid thật. Đáp án đúng format nhưng parse yếu, nên quality là `weak_parse`.

### 4.3. invalid

`invalid` khi model có trả row cho đúng qid nhưng answer không hợp lệ hoặc thành `N/A`.

Ví dụ:

```text
qid,answer
1,E
```

`E` không hợp lệ, nên answer thành `N/A`, quality là `invalid`.

### 4.4. missing

`missing` khi output batch không có đáp án cho qid đó và fallback không lấy được đáp án hợp lệ.

Ví dụ batch có qid `1`, `2`, nhưng model chỉ trả:

```text
qid,answer
1,A
```

Thì qid `2` có answer `N/A`, quality `missing`.

## 5. Single retry

`retry_bad_rows()` chạy sau parse batch.

Điều kiện:

```text
answer hiện tại == N/A
```

Nếu đúng điều kiện, pipeline gọi lại model từng câu bằng `predict_single_retry()` với prompt ép format:

```text
Chi tra ve dung 2 dong CSV: header qid,answer va mot dong dap an cho qid nay.
Khong phan tich. answer chi la A, B, C, D hoac N/A.
```

Nếu single retry ra `A/B/C/D`, `answer_source` của câu đó là:

```text
single_retry
```

Confidence tương ứng là `0.55` nếu câu không bị search router đánh dấu cần search.

## 6. Domain retry

`retry_domain_rows()` chạy sau single retry và trước web search.

Domain retry vẫn dùng cùng model Ollama. Khác biệt là user prompt được ghép thêm prompt chuyên ngành trong `prompts/domain_*.md`.

Các domain có thể retry:

```text
math
physics
logic
```

Câu hỏi được classify trong `agents/subject_router.py` bằng keyword.

### 6.1. Khi nào retry domain

Sau tối ưu hiện tại, pipeline không retry mọi câu math/physics/logic nữa. Nó chỉ retry domain nếu:

```text
subject thuộc math/physics/logic
AND
(
  question có risk signal
  OR answer_quality != clean
)
```

Nghĩa là:

- câu domain đơn giản và batch answer `clean` thì giữ lại, không retry;
- câu domain có dấu hiệu khó/rủi ro thì retry;
- câu domain có batch parse yếu, invalid, missing thì retry, kể cả câu hỏi đơn giản.

### 6.2. Risk signal

Risk signal là các keyword trong câu hỏi cho thấy cần giải lại cẩn thận, ví dụ:

```text
không đúng, không phải, sai, ngoại trừ
tất cả, mâu thuẫn, kéo theo, suy ra, kết luận
phương trình, biểu thức, xác suất, đạo hàm, tích phân
bằng bao nhiêu, %, x=, 2x
newton, lực, gia tốc, vận tốc, điện trở, rơi tự do
nếu, mọi
```

Có cả biến thể tiếng Việt có dấu và không dấu cho nhiều keyword.

### 6.3. Domain retry confidence

Sau domain retry:

- Nếu đáp án sau retry khác đáp án trước retry: `answer_source = domain_retry_changed`, confidence `0.60`.
- Nếu retry có chạy và đáp án không đổi: `answer_source = domain_retry_same`, confidence `0.80`.

`0.60` không có nghĩa là bắt buộc search. Nó có nghĩa model chuyên ngành đã sửa đáp án batch, nên tin vừa phải và nên review nếu có thời gian.

`0.80` có nghĩa model chuyên ngành đồng thuận với batch, nên tin hơn batch thường.

## 7. Web search và review

Web search được quyết định bởi `should_search(row, answer)` trong `agents/search_router.py`, không dựa trực tiếp vào confidence.

Search khi:

```text
answer == N/A
```

hoặc câu hỏi có keyword volatile/current, ví dụ:

```text
hiện nay, mới nhất, hôm nay, năm nay
latest, current, today
ceo, chủ tịch, tổng thống
giá, cổ phiếu, chứng khoán
gdp, dân số, thống kê, sản lượng
phiên bản
```

Nếu search có context, LangGraph flow là:

```text
route -> search -> finalize
```

`finalize` gọi lại model với prompt có `Ngữ cảnh web`. Nếu search context rỗng, pipeline giữ đáp án cũ.

## 8. Confidence

`confidence_for()` tính confidence cho audit theo thứ tự ưu tiên sau:

```text
answer == N/A                         -> 0.00
should_search(row, answer)            -> 0.40
answer_source == single_retry         -> 0.55
answer_source == domain_retry_changed -> 0.60
answer_source == domain_retry_same    -> 0.80
mặc định batch clean/normal           -> 0.70
```

Ý nghĩa thực dụng:

```text
0.80  giữ: domain retry đã chạy và đồng thuận với batch
0.70  giữ: batch answer bình thường, không cần retry/search
0.60  giữ nhưng nên review: domain retry đã đổi đáp án
0.55  review: batch ban đầu N/A, single retry mới ra đáp án
0.40  search/review: câu có tính current/volatile hoặc router vẫn thấy cần search
0.00  không dùng: vẫn N/A
```

Lưu ý: nếu `should_search()` trả true, confidence sẽ là `0.40` kể cả đáp án đến từ batch, single retry hay domain retry. Điều này để ưu tiên search/review các câu cần thông tin mới.

## 9. Số lần gọi model

Số lần gọi model không cố định. Công thức gần đúng:

```text
model_calls =
  số batch
+ số câu N/A cần single retry
+ số câu domain retry theo risk/quality gate
+ số câu search có context
```

Với tối ưu quality gate, các câu math/physics/logic đơn giản có batch answer `clean` sẽ không còn bị domain retry nữa, nên giảm thời gian chạy so với flow cũ.
