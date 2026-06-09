# Tech Spec: LangGraph Agent Architecture (Updated)

## 1. Tổng quan dự án
Tài liệu này mô tả kiến trúc của **LangGraph Agent Pipeline**, đóng vai trò là bộ não xử lý chính cho hệ thống trả lời câu hỏi trắc nghiệm tự động. Kiến trúc đã được tái cấu trúc (Refactored) để đạt hiệu năng xử lý hàng loạt song song (Async Batching), loại bỏ hoàn toàn các thành phần dư thừa như RAG/VectorDB nhằm tối đa hóa tốc độ.

## 2. Kiến trúc Hệ thống (Workflow)
Hệ thống vận hành theo mô hình State Machine (đồ thị trạng thái) bất đồng bộ, đảm bảo luồng dữ liệu chảy xuyên suốt từ khâu nạp câu hỏi đến khâu xuất đáp án.

### Các Node chính:
* **Retrieve Node (Input -> Local File):** Tiếp nhận câu hỏi, tự động đọc trực tiếp file `mock_knowledge.txt` để lấy toàn bộ ngữ cảnh (Không còn dùng RAG).
* **Reason Node (Context -> LLM -> Output):** Tiếp nhận ngữ cảnh + câu hỏi, gọi API tới mô hình ngôn ngữ (hiện là Groq, sau này là vLLM tự host) để suy luận logic theo Chain-of-Thought (CoT). Node này được trang bị **Concurrency Limit (Semaphore)** và **Retry Loop (Exponential Backoff)** để bảo vệ server.

| Thành phần | File chịu trách nhiệm | Trạng thái hiện tại |
| :--- | :--- | :--- |
| **Orchestrator** | `src/agent_graph.py` | Hoàn thiện (Chạy Async + Batching) |
| **Logic Prompt** | `src/system_prompt.py` | Hoàn thiện |
| **Data Retrieval** | N/A | Đã loại bỏ RAG. Đọc thẳng từ txt. |
| **LLM Inference** | `Groq API` (Tạm thời) | Hoàn thiện (Đã tích hợp API thật + Retry) |
| **Pipeline Runner** | `main.py` | Hoàn thiện (Xử lý file CSV ra CSV) |

## 3. Chi tiết các thành phần (Components)

### A. Agent Graph (`src/agent_graph.py`)
Đóng vai trò là trung tâm điều phối. Sử dụng `StateGraph` để quản lý `AgentState` xuyên suốt vòng đời của một câu hỏi.
* **Điểm nhấn Kiến trúc mới:** Sử dụng `async def` và gọi xử lý song song bằng `.abatch()`. Cùng với đó là hệ thống giới hạn luồng (`asyncio.Semaphore`) để tránh nghẽn/Sập LLM khi xử lý hàng trăm câu hỏi.

### B. Chain-of-Thought Prompt (`src/system_prompt.py`)
Thay vì để AI đoán mò, chúng ta ép mô hình thực hiện các bước:
1.  Phân tích ngữ cảnh.
2.  Tranh luận các phương án sai/đúng.
3.  Kết luận đáp án cuối cùng dưới dạng JSON để hệ thống dễ dàng bóc tách thông qua Regex.

### C. Pipeline Xử Lý File (`main.py`)
Là cổng giao tiếp chính (Entry Point). Đọc dữ liệu từ `data/mock_public_test.csv`, đóng gói hàng loạt các câu hỏi thành Input State và gọi Graph xử lý đồng thời, cuối cùng xuất ra kết quả dự đoán tại `output/pred.csv`.

## 4. Hướng dẫn Tích hợp & Chạy thử

### Cấu hình môi trường:
Hãy đảm bảo bạn đã tạo file `.env` chứa `GROQ_API_KEY` (hoặc cấu hình url cho vLLM tương ứng trong `agent_graph.py`).

### Lệnh chạy chính thức:
Chạy luồng xử lý toàn bộ data (đang được limit 5 câu trong source code để test API free):

```bash
python main.py
```
