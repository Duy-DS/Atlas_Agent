# Confidence Score Plan

Tài liệu này mô tả cách tính `confidence` trong `pred_audit.csv`.

## 1. Trạng thái hiện tại

Confidence hiện đã được tính theo pipeline events thay vì chỉ dựa vào `should_search()`.

Các event đang được theo dõi trong `main.py`:

- `batch`: đáp án đến trực tiếp từ batch prediction.
- `single_retry`: đáp án được sửa từ bước retry riêng cho câu `N/A` hoặc thiếu qid.
- `domain_retry_changed`: domain retry đã chạy và đổi đáp án.
- `domain_retry_same`: domain retry đã chạy nhưng giữ nguyên đáp án.
- `missing`: batch không trả được đáp án hợp lệ.

Audit vẫn giữ schema hiện tại:

```text
qid,answer,confidence,needs_search,search_used
```

Trong đó `answer` là đáp án trước web search, còn `pred.csv` là đáp án cuối cùng sau web search nếu có.

## 2. Rule confidence hiện dùng

Rule trong `confidence_for()`:

```text
answer == N/A                         -> 0.00
needs_search == true                  -> 0.40
answer_source == single_retry          -> 0.55
answer_source == domain_retry_changed  -> 0.60
answer_source == domain_retry_same     -> 0.80
mặc định batch hợp lệ                  -> 0.70
```

Ý nghĩa:

- `0.70`: batch trả hợp lệ nhưng chưa có bước kiểm chứng bổ sung.
- `0.55`: câu ban đầu lỗi/thiếu, được single retry sửa lại nên độ tin cậy thấp hơn batch sạch.
- `0.60`: domain retry đổi đáp án, hữu ích nhưng có rủi ro sửa sai câu vốn đúng.
- `0.80`: domain retry kiểm tra lại và giữ nguyên đáp án, đáng tin hơn batch thường.
- `0.40`: câu cần web search, audit đang ghi đáp án trước search nên confidence thấp.
- `0.00`: không có đáp án hợp lệ.

## 3. Vì sao cách này sát hơn

Cách cũ chỉ có 3 mức:

```text
N/A -> 0.00
needs_search -> 0.40
còn lại -> 0.90
```

Cách đó không phân biệt được:

- câu batch trả ngay với câu phải retry;
- câu domain retry đổi đáp án với câu domain retry giữ nguyên;
- câu toán/logic đã được kiểm tra lại với câu thường.

Cách mới không phải confidence thật của model, nhưng phản ánh tốt hơn đường đi của đáp án trong pipeline.

## 4. Giới hạn

Confidence này vẫn là heuristic, không phải xác suất đúng thật sự.

Nó chưa dùng:

- self-consistency nhiều lần gọi model;
- model tự chấm confidence;
- logprob/token probability;
- verifier pass độc lập.

Các cách trên có thể sát hơn trong một số trường hợp nhưng sẽ tăng latency hoặc phức tạp hơn. Với pipeline hiện tại, confidence theo event là lựa chọn cân bằng giữa tốc độ và khả năng debug.

## 5. Hướng mở rộng sau

Nếu cần đánh giá sát hơn nữa, nên làm theo thứ tự:

1. Thêm cột audit `answer_source` để debug trực tiếp nguồn đáp án.
2. Thêm `answer_before_domain_retry` và `domain_retry_used` nếu muốn đo domain retry có giúp thật không.
3. Chỉ thêm verifier pass cho domain rủi ro cao như toán và logic.
4. Cân nhắc self-consistency cho một tập nhỏ câu khó, không áp dụng toàn bộ dataset.

Bổi sung thêm: 

1. Logprob qua /api/generate:
pythonimport requests, math

def get_confidence_from_logprob(prompt: str) -> float:
    res = requests.post("http://localhost:11434/api/generate", json={
        "model": "qwen3.5:4b",
        "prompt": prompt,
        "logprobs": True,
        "stream": False
    }).json()

    # Tìm token A/B/C/D trong logprobs và lấy xác suất
    for lp in res.get("logprobs", []):
        if lp["token"].strip() in ("A", "B", "C", "D"):
            return round(math.exp(lp["logprob"]), 2)  # logprob → probability
    return 0.5  # fallback
2. Thinking mode — tắt cho batch thường, bật cho câu khó:
python# Tắt thinking (nhanh hơn, dùng cho batch bình thường)
{"role": "system", "content": "/no_think " + system_prompt}

# Bật thinking (chậm hơn nhưng chính xác hơn, dùng cho retry)
{"role": "system", "content": "/think " + system_prompt}

Chiến lược kết hợp cho qwen3.5:4b:
Lần 1: /no_think + heuristic confidence
        ↓
confidence < 0.6 hoặc N/A?
        ↓ có
Lần 2: /think + logprob để lấy confidence thật
        ↓
Vẫn thấp? → web search hoặc domain retry