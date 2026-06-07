# Tech Spec: LangGraph Agent Architecture

## 1. Tổng quan dự án
Tài liệu này mô tả kiến trúc của **LangGraph Agent Pipeline**, đóng vai trò là bộ não xử lý chính cho hệ thống trả lời câu hỏi trắc nghiệm tự động. Kiến trúc được thiết kế theo hướng **Modularity (Module hóa)**, cho phép phát triển song song giữa các thành viên (Dev 1, Dev 2, Dev 3) thông qua kỹ thuật "Mocking".



## 2. Kiến trúc Hệ thống (Workflow)
Hệ thống vận hành theo mô hình State Machine (đồ thị trạng thái), đảm bảo luồng dữ liệu chảy xuyên suốt từ khâu nhận diện câu hỏi đến khâu chốt đáp án.

### Các Node chính:
* **Retrieve Node (Input -> RAG):** Tiếp nhận câu hỏi, gọi module RAG để truy vấn ngữ cảnh liên quan.
* **Reason Node (RAG -> LLM -> Output):** Tiếp nhận ngữ cảnh + câu hỏi, sử dụng mô hình ngôn ngữ (vLLM) để thực hiện suy luận logic theo Chain-of-Thought (CoT).

| Thành phần | File chịu trách nhiệm | Trạng thái |
| :--- | :--- | :--- |
| **Orchestrator** | `src/agent_graph.py` | Hoàn thiện (Đã thông luồng) |
| **Logic Prompt** | `src/system_prompt.py` | Hoàn thiện |
| **Data Retrieval** | `src/rag_engine.py` | Đang Mock (Cần tích hợp DB thật) |
| **LLM Inference** | `vLLM Server (port 8000)` | Đang Mock (Chờ kết nối thật) |

## 3. Chi tiết các thành phần (Components)

### A. Agent Graph (`src/agent_graph.py`)
Đóng vai trò là trung tâm điều phối. Sử dụng `StateGraph` để quản lý `AgentState` xuyên suốt vòng đời của một câu hỏi.
* **Ưu điểm:** Cho phép kiểm soát chặt chẽ từng bước suy luận, dễ dàng debug tại từng điểm (checkpoint).

### B. Chain-of-Thought Prompt (`src/system_prompt.py`)
Thay vì để AI đoán mò, chúng ta ép mô hình thực hiện các bước:
1.  Phân tích ngữ cảnh.
2.  Tranh luận các phương án sai/đúng.
3.  Kết luận đáp án cuối cùng dưới dạng JSON để hệ thống dễ dàng bóc tách.

### C. RAG Engine (`src/rag_engine.py`)
Hiện tại đang sử dụng hàm giả lập (Mock) để phát triển đồ thị song song. Khi Dev 3 hoàn thiện module Vector Database, hàm này sẽ được cập nhật để trả về ngữ cảnh thực tế từ `chroma_db`.

## 4. Hướng dẫn Tích hợp & Chạy thử

### Quy tắc chạy code:
Để đảm bảo Python nhận diện đúng cấu trúc module của dự án, luôn chạy từ thư mục gốc của project:

```bash
python -m src.test_graph
```
