# Hướng dẫn sử dụng Docker Compose

Hướng dẫn này giải thích cách chạy Atlas Agent với Docker Compose. Stack bao gồm ba service:

- `ollama`: phục vụ API model local trên mạng Compose
- `ollama-pull`: đợi Ollama khởi động và tải model `MODEL_NAME` trước khi app chạy
- `app`: chạy `python /app/main.py`, đọc CSV từ `/app/data` và ghi kết quả vào `/app/output`

## Yêu cầu cài đặt

Cài đặt các thành phần sau trên máy host:

- Docker Engine
- Docker Compose v2
- NVIDIA Container Toolkit (chỉ khi dùng GPU)

Kiểm tra Docker Compose:

```bash
docker compose version
```

## Cấu trúc Input và Output

Tạo các thư mục runtime từ root repository:

```bash
mkdir -p data output ollama-data chroma-data
```

Đặt file CSV input tại đây:

```text
data/public_test.csv        # CSV format với cột choices
```

**CSV Format:**
```csv
qid,question,choices
test_0001,"Câu hỏi của bạn?","[""Đáp án A"", ""Đáp án B"", ""Đáp án C"", ""Đáp án D""]"
```

Hoặc vẫn hỗ trợ format cũ:
```csv
qid,question,A,B,C,D
test_0001,"Câu hỏi của bạn?","Đáp án A","Đáp án B","Đáp án C","Đáp án D"
```

App sẽ ghi các file:

```text
output/pred.csv
output/pred_audit.csv
```

`pred.csv` chứa output theo format submission `qid,answer`. `pred_audit.csv` chứa thêm các cột audit cho confidence/search behavior để bạn có thể kiểm tra tại sao một câu trả lời được tạo ra.

## Cấu hình Environment

Copy file example nếu muốn override local:

```bash
cp .env.example .env
```

Các giá trị mặc định:

```dotenv
MODEL_NAME=qwen3.5:4b
BATCH_SIZE=20
OLLAMA_NUM_PREDICT=512
INPUT_CSV=/app/data/public_test.csv
OUTPUT_CSV=/app/output/pred.csv
AUDIT_CSV=/app/output/pred_audit.csv
WEB_SEARCH_ENABLED=false
WEB_SEARCH_PROVIDER=duckduckgo
WEB_SEARCH_ENDPOINT=
OLLAMA_HOST_PORT=11435
```

Lưu ý quan trọng:

- `INPUT_CSV`, `OUTPUT_CSV`, và `AUDIT_CSV` là đường dẫn trong container, không phải host
- Compose mount `./data:/app/data:ro`, nên file host `data/public_test.csv` xuất hiện trong container tại `/app/data/public_test.csv`
- Compose mount `./output:/app/output`, nên output container `/app/output/pred.csv` xuất hiện trên host tại `output/pred.csv`
- `OLLAMA_HOST_PORT=11435` expose Ollama tại `http://localhost:11435` từ host. Bên trong Compose, app dùng `http://ollama:11434`

## Chạy với CPU

Từ thư mục gốc repository:

```bash
docker compose up --build
```

Để force chạy mới hoàn toàn sau khi thay đổi code hoặc dependencies:

```bash
docker compose build --no-cache app
docker compose up
```

Để dừng services:

```bash
docker compose down
```

## Chạy với GPU

GPU mode sử dụng file Compose cơ bản cộng với `docker-compose.gpu.yml`:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

GPU override chỉ thay đổi service `ollama`. App vẫn kết nối tới Ollama qua `OLLAMA_BASE_URL=http://ollama:11434`.

Nếu GPU không được phát hiện, verify NVIDIA runtime trên host:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Chạy với Input khác

Nếu file host là `data/private_test.csv`, chạy:

```bash
INPUT_CSV=/app/data/private_test.csv OUTPUT_CSV=/app/output/private_pred.csv AUDIT_CSV=/app/output/private_pred_audit.csv docker compose up --build
```

File vẫn phải nằm trong `data/` vì đó là thư mục input được mount.

## Tuning Model và Tốc độ

Dùng batch nhỏ hơn cho CPU hoặc model yếu:

```bash
BATCH_SIZE=10 docker compose up --build
```

Dùng model Ollama khác:

```bash
MODEL_NAME=qwen3.5:0.8b docker compose up --build
```

Nếu output bị cắt ngắn, tăng độ dài prediction:

```bash
OLLAMA_NUM_PREDICT=768 docker compose up --build
```

## Web Search

Web search mặc định bị tắt trong Compose:

```dotenv
WEB_SEARCH_ENABLED=false
```

Bật search với DuckDuckGo:

```bash
WEB_SEARCH_ENABLED=true WEB_SEARCH_PROVIDER=duckduckgo docker compose up --build
```

Dùng custom HTTP search service:

```bash
WEB_SEARCH_ENABLED=true WEB_SEARCH_ENDPOINT=http://your-search-service/search docker compose up --build
```

## Kiểm tra

Validate cú pháp Compose mà không khởi động containers:

```bash
docker compose config
```

Validate cú pháp GPU Compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config
```

Sau khi chạy xong, kiểm tra files được tạo:

```bash
ls -l output/pred.csv output/pred_audit.csv
```

## Xử lý lỗi

Nếu app exit với `input CSV not found`, xác nhận file host tồn tại:

```bash
ls data/public_test.csv
```

Nếu app đợi Ollama lâu, kiểm tra logs của Ollama:

```bash
docker compose logs -f ollama
```

Nếu việc tải model thất bại, chạy lại chỉ pull service sau khi Ollama healthy:

```bash
docker compose up ollama-pull
```

Nếu muốn xóa containers nhưng giữ lại models đã tải và outputs:

```bash
docker compose down
```

Nếu muốn xóa cả Ollama models đã tải, xóa thủ công `ollama-data/` sau khi dừng containers.

## Cải tiến Model Loading

**Tự động chờ model sẵn sàng:** App giờ tự động verify model đã được tải hoàn toàn trước khi bắt đầu xử lý. Không còn tình trạng timeout khi model chưa sẵn sàng.

**Tăng timeout:** Health check và model pulling đã được tăng timeout phù hợp cho việc tải model lớn (tối đa 30 phút).

**Improved logging:** Entrypoint giờ hiển thị rõ ràng trạng thái model loading và các paths được sử dụng.
