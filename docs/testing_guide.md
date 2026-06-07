# Testing Guide — Atlas Agent

Hướng dẫn chạy các bài kiểm thử cho hệ thống Agent. Tất cả lệnh chạy từ **thư mục gốc** của project (`Atlas_Agent/`).

---

## Yêu cầu trước khi chạy test

1. Kích hoạt virtual environment:
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux / macOS
   source .venv/bin/activate
   ```

2. Đảm bảo file `.env` có chứa `GROQ_API_KEY` (bắt buộc) và `HF_TOKEN` (tùy chọn):
   ```
   GROQ_API_KEY=gsk_...
   HF_TOKEN=hf_...        # Nếu không có sẽ dùng local embedding
   ```

---

## Danh sách các Test Script

### 1. `test/test_agent_no_RAG.py` — Agent trả lời trực tiếp (không gọi tool)

**Mục đích**: Kiểm tra agent có thể trả lời câu hỏi kiến thức tổng quát / toán cơ bản **mà không gọi bất kỳ tool nào**.

```bash
.venv\Scripts\python test/test_agent_no_RAG.py
```

**Kết quả mong đợi**:
- Log **KHÔNG** xuất hiện dòng `[Tool] LLM yeu cau goi tool RAG Database...`
- Agent trả lời trực tiếp, đáp án đúng là `B` (1+1=2)

---

### 2. `test/test_agent_to_RAG.py` — Agent gọi RAG tool khi cần

**Mục đích**: Kiểm tra agent **tự động gọi tool `search_rag_database`** khi câu hỏi yêu cầu thông tin từ tài liệu bên ngoài (ví dụ: quy định cuộc thi).

```bash
.venv\Scripts\python test/test_agent_to_RAG.py
```

**Kết quả mong đợi**:
- Log xuất hiện dòng `[Tool] LLM yeu cau goi tool RAG Database...`
- Agent truy vấn RAG, lấy context, rồi mới trả lời

---

### 3. `test/test_graph.py` — Test cơ bản luồng đồ thị

**Mục đích**: Smoke test kiểm tra luồng chạy xuyên suốt từ đầu vào đến đầu ra.

```bash
.venv\Scripts\python test/test_graph.py
```

---

## Hướng dẫn tạo Test cho Tool mới

Khi thêm một tool mới vào agent (ví dụ: `search_web`, `calculate`, ...), hãy tạo file test theo mẫu sau:

### Bước 1: Tạo file `test/test_<tên_tool>.py`

```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

import sys
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.append(str(BASE_DIR))

from src.agent_graph import app_graph

def test_new_tool():
    # Câu hỏi BẮT BUỘC phải ở dạng trắc nghiệm ABCD
    test_question = (
        "Câu hỏi: ...?\n"
        "A. ...\n"
        "B. ...\n"
        "C. ...\n"
        "D. ..."
    )

    result = app_graph.invoke({"question": test_question})
    print(f"Reasoning: {result.get('reasoning')}")
    print(f"Answer: {result.get('answer')}")

if __name__ == "__main__":
    test_new_tool()
```

### Bước 2: Chạy test

```bash
.venv\Scripts\python test/test_<tên_tool>.py
```

### Bước 3: Kiểm tra kết quả

| Điều cần xác nhận | Cách kiểm tra |
|---|---|
| Tool có được gọi khi cần? | Log xuất hiện `[Tool]...` |
| Tool **không** được gọi khi không cần? | Log **không** xuất hiện `[Tool]...` |
| Đáp án đầu ra hợp lệ? | Kết quả là `A`, `B`, `C`, hoặc `D` |

---

## Lưu ý quan trọng

- **Luôn chạy từ thư mục gốc** của project (không `cd` vào `test/`).
- **Đầu ra luôn là A/B/C/D**: Dù agent gọi tool hay trả lời trực tiếp, `parse_answer_node` sẽ trích xuất đúng 1 ký tự `A`, `B`, `C`, hoặc `D`.
- **Câu hỏi phải là trắc nghiệm**: Agent được thiết kế cho multiple-choice, câu hỏi phải có 4 lựa chọn.
