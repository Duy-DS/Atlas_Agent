# 🚀 BÁO CÁO NGHIỆM THU: BƯỚC 5 - HOÀN THIỆN BENCHMARKING & ÉP XUNG PHẦN CỨNG

Quá trình hoàn thiện cấu hình benchmark cho hệ thống `Atlas_Agent` đã được triển khai thành công. Mục tiêu của bước này là chốt backend inference theo hướng GPU-first, chuẩn hóa tham số chạy để dễ stress test, và bổ sung logging real-time phục vụ đo throughput trong các lần chạy tải lớn.

Dưới đây là báo cáo chi tiết về các thay đổi đã áp dụng.

## 1. Chốt Cấu Hình vLLM & Model AWQ

### [MODIFY] [docker-compose.gpu.yml](file:///f:/JOB/HACKAITHON/Atlas_Agent/docker-compose.gpu.yml)
Hạ tầng Docker GPU đã được tinh chỉnh để phù hợp cho benchmark và ép xung:
- Model mặc định chuyển sang AWQ 4-bit: `Qwen/Qwen1.5-4B-Chat-AWQ`
- Bổ sung `--gpu-memory-utilization 0.9`
- Bổ sung `--swap-space 4`
- Bổ sung `--served-model-name qwen-hackathon`
- Giữ nguyên `--quantization awq`
- Giữ nguyên `--enable-prefix-caching`
- Backend `app` và `vllm` đều được gắn GPU NVIDIA để đảm bảo chạy đúng chế độ benchmark

### Command khởi chạy vLLM hiện tại
```yaml
command:
  - --model
  - ${VLLM_MODEL:-Qwen/Qwen1.5-4B-Chat-AWQ}
  - --quantization
  - awq
  - --gpu-memory-utilization
  - ${VLLM_GPU_MEMORY_UTILIZATION:-0.9}
  - --swap-space
  - ${VLLM_SWAP_SPACE:-4}
  - --max-model-len
  - "4096"
  - --enable-prefix-caching
  - --served-model-name
  - ${VLLM_SERVED_MODEL_NAME:-qwen-hackathon}
  - --host
  - 0.0.0.0
  - --port
  - "8000"
```

## 2. Tham Số Hóa Batch & Concurrency

### [MODIFY] [.env](file:///f:/JOB/HACKAITHON/Atlas_Agent/.env) và [.env.example](file:///f:/JOB/HACKAITHON/Atlas_Agent/.env.example)
Các hằng số phục vụ stress test đã được khai báo rõ ràng:
- `BATCH_SIZE=10`
- `CONCURRENCY_LIMIT=5`
- `VLLM_MODEL=Qwen/Qwen1.5-4B-Chat-AWQ`
- `VLLM_SERVED_MODEL_NAME=qwen-hackathon`
- `VLLM_GPU_MEMORY_UTILIZATION=0.9`
- `VLLM_SWAP_SPACE=4`

Mục tiêu là giúp dễ dàng thay đổi tham số khi cần tìm “điểm bão hòa” của GPU và backend inference.

### [MODIFY] [src/config.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/src/config.py)
Đã bổ sung lớp cấu hình benchmark dùng chung:
- `BenchmarkConfig`
- `load_benchmark_config()`

Module này chịu trách nhiệm đọc env và cung cấp giá trị mặc định an toàn cho:
- batch size
- concurrency limit
- model AWQ
- served model name
- GPU memory utilization
- swap space

## 3. Logging Real-time Cho Benchmark

### [MODIFY] [main.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/main.py)
Luồng xử lý batch đã được bổ sung logging real-time để đo throughput ngay trong lúc chạy:
- Dùng `time.time()` để đo thời gian
- Cứ sau mỗi batch hoàn thành sẽ in log chuẩn ra terminal
- Log hiển thị:
  - batch hiện tại / tổng batch
  - tốc độ xử lý `qs/sec`
  - ước lượng độ chính xác theo định dạng đáp án `A/B/C/D`

### Hàm logging đo qs/sec
```python
def format_batch_log(
    current_batch: int,
    total_batches: int,
    questions_processed: int,
    elapsed_seconds: float,
    accuracy_hits: int,
) -> str:
    safe_elapsed = max(elapsed_seconds, 0.0)
    qs_per_sec = questions_processed / safe_elapsed if safe_elapsed > 0 else float(questions_processed)
    current_acc = (accuracy_hits / questions_processed * 100.0) if questions_processed > 0 else 0.0
    return (
        f"[INFO] Processed Batch {current_batch}/{total_batches} | "
        f"Speed: {qs_per_sec:.2f} qs/sec | Acc_Estimate: {current_acc:.2f}%"
    )
```

Cơ chế này có xử lý an toàn trường hợp thời gian bằng 0 để tránh crash do chia cho 0.

## 4. Nghiệm Thu Kỹ Thuật

Sau khi thay đổi, mình đã kiểm tra:
- `python -m py_compile main.py src/config.py` chạy thành công
- `test/test_benchmark_config.py` pass
- `docker compose -f docker-compose.gpu.yml config` render đúng command vLLM mới và nhận GPU NVIDIA

### [ADD] [test/test_benchmark_config.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/test/test_benchmark_config.py)
Đã bổ sung test cho hai hành vi quan trọng:
- Cấu hình benchmark mặc định đọc đúng `BATCH_SIZE=10` và `CONCURRENCY_LIMIT=5`
- Hàm log throughput không lỗi khi `elapsed_seconds = 0`

## 5. Lợi Ích Đạt Được

Sau bước tối ưu này, hệ thống có các lợi ích rõ rệt:
- Dễ benchmark tốc độ thực tế của vLLM trên GPU NVIDIA
- Dễ tinh chỉnh batch size và concurrency để tìm điểm bão hòa
- Có logging real-time để theo dõi throughput ngay trong terminal
- Giữ cấu hình rõ ràng, tách biệt giữa hạ tầng chạy và tham số benchmark
- Hạn chế rủi ro crash khi đo đạc nhờ xử lý an toàn các cạnh biên

> [!TIP]
> Nếu muốn benchmark sâu hơn, bước tiếp theo nên thêm export log ra file CSV hoặc JSON để so sánh throughput theo từng cấu hình GPU/batch/concurrency qua nhiều lần chạy.

Hệ thống `Atlas_Agent` đã hoàn tất giai đoạn chuẩn hóa benchmark và sẵn sàng cho các bài đo hiệu năng thực chiến trên GPU.
