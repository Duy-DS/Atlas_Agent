# Báo Cáo Cập Nhật: Giai Đoạn 2 - Ép Xung Lò Phản Ứng Ollama

Dưới đây là báo cáo xác nhận việc cấu hình tối ưu hóa để ép xung Ollama xử lý song song, nhằm ép GPU hoạt động hết công suất.

## 1. Cập nhật `docker-compose.yml` và `docker-compose.gpu.yml`
Đã thêm/sửa block cấu hình service `ollama` để kích hoạt các giới hạn bộ nhớ và luồng xử lý:
- Khai báo 3 biến môi trường tối thượng giúp tối ưu thông lượng xử lý song song.
- Chuyển hoàn toàn khối tài nguyên vLLM sang Ollama trong file GPU.

## 2. Cập nhật `.env` và `.env.example`
Đã đồng bộ hóa 3 biến môi trường cốt lõi mới cho toàn đội:
- `OLLAMA_NUM_PARALLEL=5` (Ép Ollama cấp phát bộ nhớ xử lý đồng thời 5 luồng)
- `OLLAMA_MAX_VRAM=12G` (Bơm tối đa 12GB VRAM, chừa lại 4GB cho tiến trình khác)
- `OLLAMA_KEEP_ALIVE=-1` (Lệnh cưỡng chế giữ model vĩnh viễn trên VRAM, chặn tình trạng bị unload)

Các thao tác cấu hình môi trường đã hoàn tất và sẵn sàng cho các bài test stress test. Mọi cấu hình đều đã được đồng bộ để Dev 1, Dev 2, Dev 4 có thể tái tạo.
