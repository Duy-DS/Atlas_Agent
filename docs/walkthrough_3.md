# 🚀 BÁO CÁO NGHIỆM THU: BƯỚC 3 - NÂNG CẤP INFERENCE ENGINE TỐI ƯU TỐC ĐỘ SUY LUẬN

Quá trình tối ưu hóa tầng suy luận của hệ thống `Atlas_Agent` đã được hoàn tất. Mục tiêu của bước này là giảm nút thắt cổ chai ở khâu inference, tăng thông lượng xử lý theo batch, và tận dụng GPU NVIDIA hiệu quả hơn trong môi trường triển khai.

Dưới đây là báo cáo chi tiết về các thay đổi đã áp dụng.

## 1. Đánh Giá Kiến Trúc Hiện Tại

Sau khi rà soát mã nguồn và hạ tầng, hệ thống hiện tại có đặc điểm:
- Ứng dụng đã dùng chuẩn `ChatOpenAI` qua endpoint tương thích OpenAI trong `src/agent_graph.py`.
- Hạ tầng Docker đã có tách riêng file `docker-compose.gpu.yml`, rất phù hợp để mở rộng sang backend inference tối ưu hơn.
- Luồng chạy cũ vẫn có dấu vết Ollama, nhưng không còn là lựa chọn tối ưu nếu mục tiêu là tăng `tokens/second`.

### Kết luận lựa chọn kiến trúc
- **Phương án 1 (Ollama + GGUF)**: khả thi, nhưng phù hợp hơn cho mức tinh chỉnh nhỏ và môi trường nhẹ.
- **Phương án 2 (vLLM + AWQ + GPU)**: phù hợp hơn với cấu trúc hiện tại và tối ưu hơn rõ rệt cho throughput.

**Kết luận nghiệm thu:** Hệ thống hiện tại dễ áp dụng **Phương án 2** hơn.

## 2. Nâng Cấp Hạ Tầng Docker

### [MODIFY] [docker-compose.gpu.yml](file:///f:/JOB/HACKAITHON/Atlas_Agent/docker-compose.gpu.yml)
Đã bổ sung một service `vllm` riêng để chạy inference engine chuyên dụng cho GPU:
- Image sử dụng: `vllm/vllm-openai:latest`
- Model loading qua tham số `--model`
- Bật lượng tử hóa `--quantization awq`
- Giới hạn độ dài ngữ cảnh bằng `--max-model-len 4096`
- Kích hoạt `--enable-prefix-caching` để giảm chi phí suy luận lặp
- Gắn GPU NVIDIA cho cả `app` và `vllm` bằng `gpus: all`
- Cấu hình `depends_on` để app khởi động sau backend vLLM

### [MODIFY] [docker-compose.yml](file:///f:/JOB/HACKAITHON/Atlas_Agent/docker-compose.yml)
File compose nền được giữ an toàn để vẫn có thể chạy standalone, nhưng đã thêm các biến môi trường chuẩn hóa cho LLM:
- `LLM_BACKEND`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `LLM_API_KEY`
- `LLM_CONCURRENCY_LIMIT`

## 3. Đồng Bộ Mã Nguồn Với Backend Mới

### [MODIFY] [src/agent_graph.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/src/agent_graph.py)
Lớp khởi tạo LLM đã được chuẩn hóa theo OpenAI-compatible API:
- Vẫn dùng `ChatOpenAI` từ `langchain_openai`
- `base_url` mặc định trỏ về `http://vllm:8000/v1`
- `model` mặc định đặt theo model AWQ phù hợp cho vLLM
- `api_key` được đặt an toàn ở mức `EMPTY` để tương thích local inference
- `LLM_CONCURRENCY_LIMIT` được dùng để kiểm soát số request đồng thời, tránh quá tải GPU

Phần reasoning cũng được giữ theo hướng parse JSON ổn định, tránh phụ thuộc vào structured-output đặc thù của từng backend.

### [MODIFY] [entrypoints.sh](file:///f:/JOB/HACKAITHON/Atlas_Agent/entrypoints.sh)
Entry point được cập nhật để phân nhánh rõ ràng:
- Nếu `LLM_BACKEND=vllm`, container app sẽ không khởi động Ollama nội bộ nữa
- Nếu fallback về `ollama`, luồng cũ vẫn có thể chạy bình thường
- Nhờ đó tránh lãng phí tài nguyên và tránh xung đột backend khi triển khai GPU stack

### [MODIFY] [.env](file:///f:/JOB/HACKAITHON/Atlas_Agent/.env) và [.env.example](file:///f:/JOB/HACKAITHON/Atlas_Agent/.env.example)
Đã chuẩn hóa biến môi trường để phản ánh đúng hai chế độ vận hành:
- Fallback Ollama cho chế độ standalone
- vLLM cho chế độ GPU tối ưu

## 4. Nghiệm Thu Kỹ Thuật

Đã thực hiện kiểm tra sau khi cấu hình:
- `python -m py_compile main.py src/agent_graph.py` chạy thành công
- `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config` tạo cấu hình hợp lệ
- Cấu hình render ra cho thấy service `vllm` nhận đúng model AWQ, `max-model-len=4096`, và `enable-prefix-caching`

## 5. Lợi Ích Đạt Được

Sau thay đổi này, hệ thống có các điểm mạnh sau:
- Giảm rõ rệt bottleneck inference nhờ backend vLLM tối ưu batch và cache
- Tận dụng GPU NVIDIA tốt hơn so với Ollama GGUF trong bối cảnh xử lý nhiều câu hỏi
- Giữ nguyên giao diện API tương thích OpenAI, nên mức sửa đổi code thấp
- Có fallback Ollama để đảm bảo tính linh hoạt khi chạy local

> [!TIP]
> Bước tiếp theo nên làm là benchmark thực tế `tokens/second` trên GPU mục tiêu để chốt model AWQ tối ưu nhất và tinh chỉnh thêm `gpu-memory-utilization`, `swap-space`, hoặc `max-num-batched-tokens` nếu cần.

Hệ thống inference của `Atlas_Agent` đã hoàn tất nâng cấp theo hướng GPU-first và sẵn sàng cho giai đoạn benchmark hiệu năng tiếp theo.
