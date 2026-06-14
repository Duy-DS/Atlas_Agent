# 🐛 BÁO CÁO FIX BUG: XUNG ĐỘT EVENT LOOP (ASYNCIO LỘN XỘN)

Tài liệu này mô tả chi tiết lỗi xảy ra liên quan đến bất đồng bộ (asyncio) trong quá trình batch processing và cách khắc phục để báo cáo cho team.

## 1. Mô tả Bug (Vấn đề gặp phải) 🚨

**Lỗi hiển thị:**
`RuntimeError: <asyncio.locks.Semaphore object at ...> is bound to a different event loop`

**Nguyên nhân gốc rễ (Root Cause):**
Lỗi này xảy ra trong file `main.py` do sự xung đột giữa môi trường đa luồng (multi-threading) và môi trường bất đồng bộ (asyncio) của LangChain/LangGraph:
- Mã nguồn cũ sử dụng `concurrent.futures.ThreadPoolExecutor` để chạy đa luồng cho các lô câu hỏi (batch processing).
- Bên trong mỗi worker thread, hệ thống lại gọi các hàm bất đồng bộ của LangGraph (vốn yêu cầu một event loop riêng biệt cho mỗi thread hoặc chung một event loop thống nhất).
- Khi LangGraph cố gắng khởi tạo hoặc sử dụng các khóa (như `asyncio.Semaphore`) để giới hạn tài nguyên kết nối đến vLLM, Semaphore này bị gán (bound) vào một event loop khác với event loop đang thực thi luồng hiện tại, dẫn đến lỗi crash toàn bộ worker.

## 2. Giải pháp khắc phục (How to fix) 🛠️

Để giải quyết triệt để lỗi này, chúng ta cần thống nhất toàn bộ luồng chạy về **Pure Async** (thuần bất đồng bộ trên một event loop duy nhất), từ bỏ hoàn toàn `ThreadPoolExecutor`.

### Các thay đổi chi tiết trong [main.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/main.py):

#### a) Loại bỏ ThreadPoolExecutor
- Đã xóa import `from concurrent.futures import ThreadPoolExecutor, as_completed`.
- Gỡ bỏ hoàn toàn hàm `execute_batches_with_threadpool`.

#### b) Chuyển đổi sang Pure Asyncio (`asyncio.gather`)
- Viết lại hàm xử lý lô bằng `process_dataset_async`.
- Thay vì đẩy task vào các Thread, mã nguồn mới tạo ra một danh sách các coroutines và sử dụng `await asyncio.gather(*tasks)` để chạy song song toàn bộ các câu hỏi trong một batch cực kì mượt mà.

#### c) Giới hạn Concurrency bằng `asyncio.Semaphore`
- Khởi tạo `semaphore = asyncio.Semaphore(5)` ở bên trong hàm async chính (`process_dataset_async`) trên cùng một event loop.
- Truyền biến `semaphore` này vào từng task con `_process_single_question`.
- Sử dụng context manager `async with semaphore:` trước khi gọi request LLM để đảm bảo không vượt quá 5 kết nối đồng thời tới server vLLM, chống quá tải.

#### d) Gọi LangGraph đúng chuẩn Async
- Cập nhật phương thức gọi LangGraph từ đồng bộ sang bất đồng bộ hoàn toàn thông qua phương thức `ainvoke`:
  ```python
  return await app_graph.ainvoke({"question": item["question"]})
  ```

## 3. Kết quả (Verification) ✅
- **Hiệu năng:** Code chạy nhanh hơn và ổn định hơn do loại bỏ được chi phí overhead (context switching) của ThreadPool.
- **Tính ổn định:** Hoàn toàn chấm dứt tình trạng crash do "different event loop". Hệ thống an toàn để hoạt động trong môi trường containerized và pipeline đánh giá quy mô lớn.

> [!TIP]
> Việc sử dụng pure asyncio (`asyncio.gather`) kết hợp Semaphore là Best Practice khi làm việc với các hệ thống AI/LLM gọi API bất đồng bộ. Nó giúp tiết kiệm tài nguyên CPU và dễ dàng theo dõi (trace) luồng request hơn so với Multithreading.
