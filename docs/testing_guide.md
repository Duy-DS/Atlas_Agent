# Testing Guide — Atlas Agent (Kiến trúc Multi-Tool)

Tài liệu hướng dẫn chạy thử nghiệm và kiểm thử hệ thống Agent phiên bản Multi-Tool Async.

---

## 1. Yêu cầu trước khi chạy Test

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

## 2. Hướng dẫn chạy Test Script chính

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

**Kết quả mong đợi trên Console:**
- Nhìn thấy các dòng log điều phối từ Router:
  ```text
  [ROUTER] 'Câu hỏi 1: AI Agent là gì?...' -> ĐI THẲNG REASONING
  [ROUTER] 'Câu hỏi 2: Giải thưởng bảng C là bao nhiêu?...' -> GOI WIKIPEDIA
  [ROUTER] 'Câu hỏi 3: RAG hoạt động như thế nào?...' -> GOI WEB SEARCH
  ```
- Kết quả in ra dạng:
  ```text
  Q1: Câu hỏi 1: AI Agent là gì?
  A: B | Lập luận: AI Agent là một thực thể trí tuệ nhân tạo...
  --------------------------------------------------
  ```
- Tổng thời gian xử lý hiển thị ở cuối log (thông thường chỉ mất khoảng dưới 2-3 giây nhờ chạy song song `abatch`).

---

## 3. Cách thêm câu hỏi kiểm thử mới

Nếu bạn muốn bổ sung câu hỏi để test độ chính xác của các công cụ cụ thể:
1. Mở file [test/test_async.py](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/test/test_async.py).
2. Thêm câu hỏi trắc nghiệm của bạn vào danh sách `questions`.
3. Chạy lại test script để quan sát xem Router có định hướng đúng hay không.

Ví dụ câu hỏi định tuyến mong đợi:
* *Toán học / Logic* ➔ `PYTHON` (Ví dụ: `"Tính tổng 1234 + 5678"`)
* *Thông tin lịch sử / Định nghĩa học thuật* ➔ `WIKI` (Ví dụ: `"Chiến tranh thế giới thứ hai bắt đầu năm nào?"`)
* *Sự kiện mới / Thời tiết / EURO* ➔ `WEB` (Ví dụ: `"Đội nào vô địch Euro 2024?"`)
* *Câu hỏi phổ thông cơ bản* ➔ `NO` (Ví dụ: `"Quả táo có màu gì?"`)
