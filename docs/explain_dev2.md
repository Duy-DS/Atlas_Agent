# Tech Spec: Multi-Tool LangGraph Agent (Bảng C - HackAIthon)

## 1. Tổng quan dự án
Tài liệu này mô tả kiến trúc của **Multi-Tool LangGraph Agent**, bộ não xử lý chính cho hệ thống trả lời câu hỏi trắc nghiệm tự động, nhắm tới việc tối đa hóa điểm **Accuracy** và **Inference Time** trong Bảng C cuộc thi Vietnamese Student HackAIthon 2026.
Hệ thống sử dụng **Conditional Routing** để định tuyến câu hỏi tới đúng công cụ (Tool) phù hợp thay vì gọi Tool mù quáng.

## 2. Kiến trúc Hệ thống (Workflow)
Hệ thống vận hành theo mô hình State Machine (Đồ thị trạng thái) bất đồng bộ (Async Batching). 

### Các Node chính (4 Ngã rẽ):
* **Retrieve Node:** Nạp câu hỏi và ngữ cảnh ban đầu.
* **Router Node:** Là bộ não điều phối. Gọi LLM để đọc nhanh câu hỏi và quyết định rẽ 1 trong 4 nhánh:
  - `PYTHON`: Các câu hỏi Toán học, phương trình, logic ➔ Chuyển qua **PythonREPL Node**.
  - `WIKI`: Các câu hỏi lịch sử, địa lý, định nghĩa ➔ Chuyển qua **WikiSearch Node**.
  - `WEB`: Các câu hỏi thời sự, kết quả thể thao, tỷ giá ➔ Chuyển qua **WebSearch Node** (DuckDuckGo).
  - `NO`: Mọi kiến thức phổ thông cơ bản ➔ Đi thẳng vào **Reason Node**.
* **Reason Node (Reasoning):** Nhận ngữ cảnh đã được bổ sung bởi các Tool (nếu có), gọi LLM suy luận theo chuỗi logic (Chain-of-Thought) để xuất ra đáp án cuối cùng dạng JSON chứa `answer` (A/B/C/D).

| Thành phần | File chịu trách nhiệm | Trạng thái hiện tại |
| :--- | :--- | :--- |
| **Orchestrator** | `src/agent_graph.py` | Hoàn thiện (Chạy Async + Conditional Routing) |
| **Tools** | `wikipedia`, `DuckDuckGo`, `PythonREPL` | Đã tích hợp (Local/Free API) |
| **Logic Prompt** | `src/system_prompt.py` | Hoàn thiện (CoT Prompt) |
| **Pipeline Runner** | `main.py` | Hoàn thiện (Đọc/Ghi file CSV) |

## 3. Điểm nhấn Kiến trúc Mới
1. **Zero API Key Tools:** Toàn bộ công cụ sử dụng (Wiki, DuckDuckGo, Python) đều miễn phí và không cần cấu hình API Key, rất thuận tiện khi nộp bài qua Docker.
2. **Speed Optimization (Inference Time):** Bằng cách phân loại qua Router, những câu hỏi cơ bản sẽ đi thẳng vào nhánh Reasoning mà không phải chờ phản hồi chậm chạp từ Internet, giúp tăng đáng kể điểm tốc độ.
3. **Accuracy Optimization:** Thay vì để LLM tự làm toán (thường xuyên bị sai), hệ thống sinh code Python và bắt máy tính chạy để đảm bảo tỷ lệ đúng tuyệt đối 100% cho mảng Khoa học tự nhiên.

## 4. Hướng dẫn Chạy thử

Đảm bảo bạn đã cài đặt đủ thư viện trong `requirements.txt` và đã thiết lập biến môi trường `GROQ_API_KEY` trong file `.env`.

Chạy hệ thống (cần cấu hình encoding UTF-8 trên Windows):
```bash
$env:PYTHONUTF8=1; python main.py
```
