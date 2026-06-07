# Agent Architecture: Before vs After Merge

Tài liệu giải thích sự khác biệt về cách hoạt động của hệ thống **trước** và **sau** khi merge branch `dev`, cùng cơ chế đảm bảo đầu ra.

---

## 1. Kiến trúc TRƯỚC khi merge (RAG Pipeline cứng)

```
Câu hỏi ──▶ RAG Search ──▶ LLM Reasoning ──▶ Đáp án
              (LUÔN gọi)
```

### Vấn đề:
| Hạn chế | Mô tả |
|---|---|
| **Luôn gọi RAG** | Mọi câu hỏi — kể cả `1+1=?` — đều bị đẩy qua RAG trước khi LLM trả lời |
| **Tốn tài nguyên** | Gọi vector search + embedding cho câu hỏi không cần context |
| **Kết quả nhiễu** | RAG trả về context không liên quan → LLM bị nhiễu, đáp án sai |
| **Không phải Agent** | Đây là một RAG pipeline cố định, không có khả năng tự quyết định |

### Luồng xử lý cũ:
1. Nhận câu hỏi
2. **Luôn luôn** gọi `search_rag_database()` để tìm context
3. Ghép context + câu hỏi → gửi cho LLM
4. LLM trả lời dựa trên context (dù context có thể không liên quan)

---

## 2. Kiến trúc SAU khi merge (ReAct Agent — Tự quyết định)

```
                    ┌──── Tool (RAG) ────┐
                    │                    │
Câu hỏi ──▶ Agent ─┤                    ├──▶ Parse ──▶ Đáp án
                    │                    │
                    └── Trả lời trực tiếp┘
```

### Cải tiến:
| Tính năng | Mô tả |
|---|---|
| **Agent tự quyết định** | LLM phân tích câu hỏi trước, tự chọn gọi tool hay trả lời trực tiếp |
| **Tiết kiệm tài nguyên** | Câu hỏi tổng quát (toán, kiến thức chung) → không gọi RAG |
| **Kết quả chính xác hơn** | Không bị nhiễu bởi context không liên quan |
| **Mở rộng được** | Có thể thêm tool mới (web search, calculator, ...) mà không thay đổi kiến trúc |

### Luồng xử lý mới:
1. Nhận câu hỏi
2. **Agent đánh giá** câu hỏi theo 4 quy tắc:
   - **Rule 1 — EVALUATE BEFORE CALLING**: Nếu là kiến thức tổng quát, toán cơ bản → trả lời trực tiếp
   - **Rule 2 — CONTEXT ALREADY PROVIDED**: Nếu câu hỏi đã chứa đoạn văn/context → trả lời trực tiếp
   - **Rule 3 — ONLY USE RAG WHEN NECESSARY**: Chỉ gọi RAG khi cần thông tin từ tài liệu bên ngoài
   - **Rule 4 — DIRECT RESPONSE**: Khi không gọi tool → trả JSON ngay lập tức
3. Nếu gọi tool → nhận kết quả → quay lại Agent để tổng hợp
4. Parse đáp án cuối cùng

---

## 3. So sánh trực tiếp

### Ví dụ 1: Câu hỏi toán cơ bản — `1+1 = ?`

| | Trước | Sau |
|---|---|---|
| Gọi RAG? | ✅ Có (lãng phí) | ❌ Không |
| Bước xử lý | Câu hỏi → RAG → LLM → Parse | Câu hỏi → Agent → Parse |
| Kết quả | Có thể sai do context nhiễu | ✅ Đúng (`B`) |

### Ví dụ 2: Câu hỏi về giải thưởng HackAIthon 2026

| | Trước | Sau |
|---|---|---|
| Gọi RAG? | ✅ Có | ✅ Có (đúng hành vi) |
| Bước xử lý | Câu hỏi → RAG → LLM → Parse | Câu hỏi → Agent → Tool (RAG) → Agent → Parse |
| Kết quả | Phụ thuộc context | ✅ Chính xác từ RAG context |

---

## 4. Cơ chế đảm bảo đầu ra (Output Guarantee)

Dù agent gọi tool hay trả lời trực tiếp, đầu ra **luôn được đảm bảo** là `A`, `B`, `C`, hoặc `D` nhờ 3 tầng bảo vệ:

### Tầng 1 — System Prompt (Hướng dẫn LLM)

LLM được yêu cầu trả lời dưới dạng JSON cố định:
```json
{
    "reasoning": "...",
    "answer": "A"
}
```

### Tầng 2 — JSON Parser (`parse_answer_node`)

Node `Parse` xử lý output của LLM qua nhiều bước:
1. **Parse JSON trực tiếp** — `json.loads(response)`
2. **Xử lý markdown** — Loại bỏ ` ```json ``` ` wrapper
3. **Sửa JSON cắt cụt** — Thử thêm `}` hoặc `"}` nếu bị cắt
4. **Regex fallback** — Nếu parse JSON lỗi hoàn toàn, dùng regex tìm `"answer": "X"`

### Tầng 3 — Answer Normalization

```python
match = re.search(r'([A-D])', clean_answer)
final_answer = match.group(1) if match else "A"
```

- Trích xuất ký tự `A-D` đầu tiên từ chuỗi đáp án
- Nếu không tìm thấy gì → fallback mặc định là `"A"`

### Kết quả: **100% đầu ra hợp lệ**

| Tình huống LLM output | Kết quả Parse |
|---|---|
| `{"reasoning": "...", "answer": "B"}` | ✅ `B` |
| ` ```json {"answer": "C"} ``` ` | ✅ `C` |
| `{"answer": "D"` (JSON cắt cụt) | ✅ `D` |
| Output bất thường hoàn toàn | ✅ `A` (fallback) |

---

## 5. Tóm tắt

| Tiêu chí | Trước (RAG Pipeline) | Sau (ReAct Agent) |
|---|---|---|
| Kiến trúc | Pipeline cứng | Agent tự quyết định |
| Tool calling | Luôn gọi RAG | Chỉ gọi khi cần |
| Mở rộng tool | Khó | Dễ (thêm tool mới) |
| Đầu ra | Không đảm bảo format | Luôn là A/B/C/D |
| Hiệu suất | Lãng phí cho câu hỏi đơn giản | Tối ưu |
