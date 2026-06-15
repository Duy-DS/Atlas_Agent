# Bệnh Án Hệ Thống - Atlas Agent

## 1. Triệu Chứng & Tiền Sử (Symptoms)
- **Môi trường:** Kaggle (GPU), xử lý Batch.
- **Mô hình:** Qwen2.5-7B-Instruct-AWQ chạy qua vLLM cục bộ (`http://127.0.0.1:8000/v1`).
- **Lỗi ghi nhận:** 
  ```text
  [*] LLM config: Base URL=http://127.0.0.1:8000/v1 | Model=Qwen/Qwen2.5-7B-Instruct-AWQ
  [*] Hardware mode: GPU | LLM concurrency hint: 8
  Router error (1/10): Connection error.
  Router error (2/10): Connection error.
  ```
- **Mô tả:** Pipeline LangChain gửi request tới Router và bị từ chối kết nối ngay lập tức, báo lỗi `Connection error` liên tục rồi thất bại.

## 2. Khám Cận Lâm Sàng (Deep Code Scan)

Qua rà soát mã nguồn (`.env`, `docker-compose.gpu.yml`, `entrypoints.sh`, `main.py`, `src/agent_graph.py`), tôi ghi nhận các vấn đề sau:

- **Server vLLM có thực sự được cấu hình để lắng nghe ở cổng 8000 không?**
  - **Có.** Trong `docker-compose.gpu.yml` đã chỉ định rõ `--port 8000`. Biến môi trường mặc định trong `src/agent_graph.py` cũng hướng đến `http://127.0.0.1:8000/v1`. Tuy nhiên, nếu chạy ngầm trên Kaggle, cổng này chưa chắc đã kịp mở lúc `main.py` bắt đầu gửi request.

- **Có cơ chế sleep (chờ đợi) nào giữa lệnh bật server vLLM ngầm và lệnh chạy main.py không?**
  - **Hoàn toàn KHÔNG.** Trong file khởi động (ví dụ `entrypoints.sh`), chỉ có cơ chế wait/health-check cho `Ollama` (`until curl -fsS "${OLLAMA_BASE_URL}/api/tags"...`). Đối với `vLLM`, hệ thống bỏ qua bước chờ và chạy thẳng lệnh thực thi python `main.py`. Trong khi đó, vLLM cần từ 1 đến 3 phút để load model 7B vào GPU memory.

- **Hàm khởi tạo mô hình LangChain (ChatOpenAI) có thiết lập cơ chế tự động Retry/Timeout hợp lý chưa?**
  - **Chưa hợp lý.** Trong `src/agent_graph.py`, đối tượng `ChatOpenAI` được khởi tạo thiếu tham số `max_retries` và `timeout` cho HTTP Client. 
  - Mặc dù hệ thống có vòng lặp retry 10 lần (custom retry trong `router_node` và `reasoning_node`), nhưng khi gặp lỗi kết nối (Connection error), nó chỉ gọi `await asyncio.sleep(1)`. Tổng thời gian chờ tối đa chỉ khoảng 10 giây. Thời gian này là quá ngắn so với thời gian khởi động vLLM.

## 3. Chẩn Đoán Xác Định (Root Cause)
Căn bệnh hệ thống đang mắc phải là **"Sốc phản vệ do khởi động nôn nóng" (Race Condition during Startup)**.
- Khi chạy script trên Kaggle, server vLLM được bật ngầm, nhưng quá trình nạp model Qwen2.5-7B-Instruct-AWQ lên VRAM tốn vài phút.
- Ngay lập tức, `main.py` khởi chạy, nã 8 luồng (concurrency) vào cổng 8000.
- Cổng 8000 chưa có dịch vụ nào lắng nghe vì vLLM đang bận khởi động model -> OS trả về Connection Refused/Connection Error.
- Vòng lặp retry 10 lần của LangChain Graph quá ngắn (chờ 1s mỗi lần ~ tổng 10s), nên hệ thống cạn kiệt attempt trước khi vLLM kịp "thức dậy", dẫn đến sụp đổ luồng Batch.

## 4. Phác Đồ Điều Trị (Treatment Plan)

Để trị dứt điểm, chúng ta cần can thiệp vào 2 vị trí: thêm cơ chế "chờ thuốc ngấm" (Health Check vLLM) và tăng cường đề kháng (Timeout/Retry cho ChatOpenAI).

### Bước 1: Sửa file Bash Script khởi động trên Kaggle (hoặc `entrypoints.sh`)
**Mục tiêu:** Ép luồng thực thi phải chờ vLLM server báo "sẵn sàng" trước khi gọi `main.py`.

Thêm đoạn script sau ngay trước khi gọi `python main.py` trong script bash trên Kaggle của bạn:
```bash
echo "Waiting for vLLM server to be ready at http://127.0.0.1:8000/v1/models..."
until curl -fsS http://127.0.0.1:8000/v1/models > /dev/null 2>&1; do
    echo "vLLM is not ready yet. Sleeping for 10 seconds..."
    sleep 10
done
echo "vLLM is UP and running!"
```

### Bước 2: Sửa `src/agent_graph.py` (Cấp thêm Retry và Timeout)
**Mục tiêu:** Tăng sức chịu đựng cho HTTP Client của LangChain khi server bị nghẽn.

Tìm dòng khởi tạo `llm = ChatOpenAI(...)` (khoảng dòng 30-35) trong file `src/agent_graph.py` và bổ sung thêm `max_retries` cùng `timeout`:
```python
llm = ChatOpenAI(
    model=llm_model_name,
    api_key=llm_api_key,
    base_url=llm_base_url,
    temperature=0.1,
    max_retries=5,       # Thêm: Tự động retry tối đa 5 lần ở tầng HTTP
    timeout=120.0,       # Thêm: Tăng timeout lên 120s phòng khi model sinh text dài bị chậm
)
```

### Bước 3: Tăng thời gian chờ trong Custom Retry Loop của `src/agent_graph.py`
**Mục tiêu:** Nếu vẫn rớt mạng (hoặc bị quá tải do concurrent lớn), hãy chờ lâu hơn một chút (exponential backoff) thay vì chỉ chờ 1s.

Tìm khối code bắt lỗi trong các hàm `router_node` và `reasoning_node` (đoạn `print(f"Router error ({attempt + 1}/{max_retries}): {e}")`):
```python
# Sửa dòng:
await asyncio.sleep(1)

# Thành đoạn này:
wait_time = 2 * (attempt + 1)
print(f"Connection/Other error. Waiting {wait_time}s before retry...")
await asyncio.sleep(wait_time)
```

**Lời dặn của Bác sĩ:** Hãy áp dụng đúng 3 bước trong phác đồ điều trị này, hệ thống sẽ tự động chờ vLLM load xong model và mượt mà "nhai" hết các question trong Kaggle với 8 luồng mà không gặp bất kỳ lỗi `Connection error` nào nữa! Chúc ca mổ thành công!
