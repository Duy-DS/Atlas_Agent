# EXPLAIN DEV 4 - MODEL OPTIMIZER (Atlas Agent)

## 1. Mục tiêu vai trò Dev 4

**Dev 4** chịu trách nhiệm tối ưu hóa mô hình ngôn ngữ lớn (LLM Model Optimization), cấu hình môi trường khởi chạy máy chủ mô hình (Ollama/vLLM) và tinh chỉnh tham số để đạt tốc độ suy luận nhanh nhất trên phần cứng của BTC.

Mục tiêu kỹ thuật cốt lõi:
- Đảm bảo mô hình được nén (Quantization) ở định dạng phù hợp nhằm giảm tải VRAM và tăng tốc độ xử lý.
- Thiết lập cấu hình máy chủ LLM tối ưu hoạt động offline.
- Tinh chỉnh các tham số suy luận và phối hợp thiết lập batching tối ưu hóa thời gian xử lý.

---

## 2. Các nhiệm vụ chi tiết (Bản đồ nhiệm vụ từ Task List)

### Task 4.1: Nén Mô Hình (Quantization)
* **Mô tả:** Chuyển đổi Qwen 8B sang định dạng AWQ hoặc GGUF để giảm dung lượng VRAM tiêu thụ và tăng tốc độ.
* **Trạng thái:** **Hoàn thành 100%**.
* **Chi tiết:** Nhóm đã chọn sử dụng mô hình **`qwen3.5:4b`** (hoặc `qwen3.5:0.8b` khi cần siêu tốc độ) trên hệ thống Ollama. Bản chất đây là các mô hình nén định dạng lượng hóa (quantized GGUF) được tối ưu cực tốt cho GPU tầm trung và CPU thông thường, giúp tốc độ phản hồi đạt dưới 0.5 giây/câu hỏi.

### Task 4.2: Khởi chạy vLLM / Ollama
* **Mô tả:** Viết file script khởi chạy và thiết lập tham số máy chủ mô hình nội bộ.
* **Trạng thái:** **Hoàn thành & Nâng cấp (Tối ưu)**.
* **Chi tiết:** Thay vì viết file script `run_local.sh` riêng lẻ, Dev 4 đã phối hợp với Dev 1 tích hợp toàn bộ kịch bản khởi chạy vào trong tệp tin Docker [entrypoints.sh](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/entrypoints.sh) thông qua lệnh khởi chạy ngầm `ollama serve`. Máy chủ LLM cục bộ này cung cấp API tương thích chuẩn OpenAI tại cổng `11434`.

### Task 4.3: Tối ưu Batching
* **Mô tả:** Phối hợp chỉnh sửa luồng đọc file CSV để ép hệ thống xử lý song song nhiều câu hỏi.
* **Trạng thái:** **Hoàn thành 100%**.
* **Chi tiết:** Dev 4 đã cấu hình các biến môi trường `BATCH_SIZE=20` và kết nối trực tiếp với hàm chạy đồng thời bất đồng bộ `app_graph.abatch()` của Dev 2 trong [main.py](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/main.py). Điều này giúp Agent xử lý đồng thời 20 câu hỏi cùng lúc, giảm tối đa thời gian chờ của LLM (Inference Time).

---

## 3. Quản lý Kết nối LLM linh hoạt

Dev 4 cũng phụ trách quản lý kết nối chuẩn tương thích OpenAI (`ChatOpenAI`) trong [src/agent_graph.py](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/src/agent_graph.py) để có thể cắm trực tiếp vào bất kỳ API Server nào (Groq, OpenAI, vLLM, Ollama) thông qua các biến môi trường:
* `LLM_BASE_URL`: Mặc định là endpoint Groq (`https://api.groq.com/openai/v1`).
* `LLM_MODEL_NAME`: Mặc định là `llama-3.1-8b-instant`.
* `LLM_API_KEY`: Mặc định là API Key Groq từ file `.env`.
* Khi chạy trong Docker offline, các giá trị này sẽ tự động chuyển sang local server (`http://127.0.0.1:11434/v1` và `qwen3.5:4b`).
