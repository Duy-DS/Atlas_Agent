# EXPLAIN DEV 1 - DOCKER INTEGRATION & SUBMISSION (Atlas Agent)

## 1. Mục tiêu vai trò Dev 1

**Dev 1** chịu trách nhiệm thiết lập môi trường đóng gói **Docker**, đảm bảo hệ thống Agent chạy cô lập và ổn định khi nộp bài cho Ban tổ chức (BTC).

Mục tiêu kỹ thuật cốt lõi:
- Đóng gói toàn bộ mã nguồn, các thư viện phụ thuộc và **trọng số mô hình (model weights)** vào một Docker Image duy nhất để chạy Offline 100%.
- Thiết lập kịch bản khởi động tự động (`entrypoints.sh`) quản lý cả LLM Server (Ollama) và ứng dụng Python.
- Tương thích tốt trên cả hai chế độ CPU (máy local của dev) và GPU (máy chấm thi của BTC).
- Đảm bảo cơ chế đọc dữ liệu từ `/data` và ghi kết quả ra `/output` đúng chuẩn quy định.

---

## 2. Các thành phần chính do Dev 1 quản lý

### 2.1 Standalone Dockerfile
Tệp [Dockerfile](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/Dockerfile) sử dụng base image `ollama/ollama` để có sẵn driver GPU và cấu hình:
* **Tách biệt môi trường Python:** Sử dụng Python Virtual Environment (`/opt/venv`) để tránh xung đột hệ thống.
* **Pre-bake Model:** Tải trước mô hình `qwen3.5:4b` trong quá trình build để không phụ thuộc vào internet khi container chạy trên máy chấm.

### 2.2 Entrypoint Script (`entrypoints.sh`)
Tệp [entrypoints.sh](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/entrypoints.sh) là bộ khởi động chính của container:
1. Chạy dịch vụ Ollama Server ở chế độ nền (`ollama serve &`).
2. Chờ cho tới khi Ollama Server sẵn sàng nhận request.
3. Cấu hình biến môi trường kết nối nội bộ cho Agent (`LLM_BASE_URL=http://127.0.0.1:11434/v1`).
4. Khởi chạy script chạy chính (`python main.py`).

### 2.3 Docker Compose (Dành cho Dev local)
* [docker-compose.yml](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/docker-compose.yml): Cấu hình chạy thử nghiệm chế độ CPU nhanh chóng, mount thư mục `./data` và `./output` cục bộ.
* [docker-compose.gpu.yml](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/docker-compose.gpu.yml): Cấu hình cấp phát thiết bị GPU Nvidia (`deploy.resources.reservations.devices`) để chạy thử nghiệm tăng tốc phần cứng.

---

## 3. Quy trình nộp bài & Chạy thử của BTC

Khi nộp bài, BTC sẽ build Image từ mã nguồn và khởi chạy container bằng lệnh tiêu chuẩn:

```bash
# Lệnh chạy Container đơn lẻ có cấp phát GPU và mount thư mục dữ liệu
docker run --gpus all \
  -v /path/to/btc/data:/data \
  -v /path/to/btc/output:/output \
  <ten_image_cua_doi_thi>
```

* **Dữ liệu đầu vào:** Nạp tại `/data/public_test.csv` hoặc `/data/private_test.csv`.
* **Dữ liệu đầu ra:** Container phải xuất file dự đoán tại `/output/pred.csv`.

---

## 4. Checklist bàn giao của Dev 1

- [ ] Thực hiện build thử Docker image cục bộ thành công: `docker compose build`.
- [ ] Chạy thử nghiệm offline (ngắt mạng internet) kiểm tra xem container có tự khởi động Ollama và chạy suy luận được không.
- [ ] Xác minh thư mục `/output` sinh ra tệp `pred.csv` với cấu trúc chuẩn.
- [ ] Kiểm tra tài nguyên GPU có được sử dụng khi chạy lệnh GPU Compose.
