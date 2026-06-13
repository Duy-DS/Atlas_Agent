# Testing Guide — Atlas Agent (Kiến trúc Multi-Tool)

Tài liệu hướng dẫn chạy thử nghiệm, kiểm thử hệ thống Agent phiên bản Multi-Tool Async trên môi trường Local và Docker.

---

## 1. Yêu cầu trước khi chạy Test Local

1. **Kích hoạt Virtual Environment:**
   ```bash
   # Windows PowerShell/CMD
   .venv\Scripts\activate

   # Linux / macOS
   source .venv/bin/activate
   ```

2. **Cài đặt thư viện:** Đảm bảo bạn đã cài đặt đầy đủ các thư viện mới nhất:
   ```bash
   pip install -r requirements.txt
   ```

3. **Biến môi trường:** Đảm bảo tệp `.env` ở thư mục gốc có cấu hình `GROQ_API_KEY`:
   ```env
   GROQ_API_KEY=gsk_...
   ```

---

## 2. Hướng dẫn chạy Test Script chính (Local)

Tất cả các lệnh chạy kiểm thử phải được thực hiện từ **thư mục gốc** của dự án (`Atlas_Agent/`).

### Test Script: `test/test_async.py`

**Mục đích:**
- Kiểm tra luồng chạy của Multi-Tool Agent trên 10 câu hỏi mẫu khác nhau.
- Xác thực hoạt động của **Router Node** trong việc phân loại câu hỏi (định tuyến đến Python, Wikipedia, Web Search hoặc Đi thẳng).
- Kiểm tra cơ chế chạy song song bất đồng bộ (`abatch()`) để đo thời gian phản hồi thực tế.

**Lệnh thực thi:**
* **Trên Windows (Tránh lỗi mã hóa tiếng Việt):**
  ```powershell
  $env:PYTHONUTF8=1; python test/test_async.py
  ```
* **Trên Linux / macOS:**
  ```bash
  python test/test_async.py
  ```

---

## 3. Hướng dẫn chạy kiểm thử trên Docker (Giả lập môi trường BTC)

Nhóm đã đóng gói toàn bộ mô hình và môi trường chạy offline vào một container Standalone. Bạn có thể kiểm thử Docker trực tiếp tại máy cục bộ bằng Docker Compose:

### 3.1 Chuẩn bị thư mục dữ liệu kiểm thử
Tạo thư mục lưu dữ liệu đầu vào và đầu ra trên máy của bạn:
```bash
mkdir -p data output
```
Đảm bảo bạn có tệp tin câu hỏi mẫu tại đầu vào: `data/public_test.csv` (Có thể copy từ [data/mock_public_test.csv](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/data/mock_public_test.csv) sang).

### 3.2 Khởi chạy với Docker Compose (CPU Mode)
Build và chạy toàn bộ luồng xử lý tự động trong container:
```bash
docker compose up --build
```
*Hệ thống sẽ tự động khởi động Ollama bên trong container, nạp mô hình Qwen 3.5, gọi script `main.py` để xử lý và ghi kết quả.*

### 3.3 Khởi chạy với Docker Compose (GPU Mode)
Nếu máy của bạn có GPU NVIDIA và đã cài đặt NVIDIA Container Toolkit, hãy chạy lệnh sau để tăng tốc phần cứng:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

### 3.4 Kiểm tra kết quả đầu ra
Sau khi container chạy hoàn tất và tự tắt, hãy kiểm tra tệp tin kết quả được xuất ra tại thư mục trên máy thật của bạn:
* `output/pred.csv` (Chứa 2 cột `qid` và `answer` chuẩn theo quy chế BTC).

---

## 4. Các điểm Tối ưu hóa hiệu năng (Performance Tuning)

Để tối ưu hóa thời gian xử lý (Inference Time) và tránh lỗi sập tài nguyên (Out of Memory) phù hợp với phần cứng máy chấm thi, Dev 4 đã cấu hình các tham số động qua biến môi trường. Bạn có thể cấu hình chúng trong file `.env` hoặc Dockerfile:

### 4.1 Cấu hình Giới hạn chạy thử (`TEST_LIMIT`)
* **Mặc định:** `TEST_LIMIT=0` (Xử lý toàn bộ các câu hỏi trong file CSV đầu vào).
* **Khi muốn chạy test nhanh:** Bạn có thể đặt `TEST_LIMIT=5` để chỉ xử lý 5 câu hỏi đầu tiên rồi xuất file kết quả ngay lập tức, tránh bị dính giới hạn API của Groq hoặc tiết kiệm thời gian test local.
  ```bash
  TEST_LIMIT=5 docker compose up
  ```

### 4.2 Cấu hình Giới hạn luồng chạy song song (`LLM_CONCURRENCY_LIMIT`)
* **Mặc định:** `LLM_CONCURRENCY_LIMIT=5` (Cho phép tối đa 5 luồng gọi LLM suy luận đồng thời qua Semaphore).
* **Tối ưu hóa:** 
  * Nếu phần cứng máy chấm thi của BTC có GPU mạnh (như A100, T4, RTX 4090), bạn có thể nâng giới hạn này lên **`10` hoặc `15`** để xử lý batch cực nhanh, rút ngắn tối đa thời gian chấm bài.
  * Nếu chạy trên CPU yếu và bị lỗi sập hoặc tràn bộ nhớ (Out of Memory), hãy hạ giới hạn này xuống **`2` hoặc `3`** để đảm bảo hệ thống chạy bền bỉ tới câu hỏi cuối cùng.
  ```bash
  LLM_CONCURRENCY_LIMIT=12 docker compose up
  ```
