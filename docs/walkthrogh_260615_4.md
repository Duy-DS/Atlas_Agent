# Báo Cáo Nghiệm Thu: Giai Đoạn 4 - Đa Luồng Tăng Tốc (Concurrency Pipeline)

Dưới đây là báo cáo xác nhận việc viết lại toàn bộ tầng điều phối I/O tại tệp `src/main.py` để đạt tốc độ xử lý tối đa cho 2000 câu hỏi, đồng thời bảo toàn tính toàn vẹn của dữ liệu đầu ra.

## 1. Tích hợp Đa luồng song song (ThreadPoolExecutor)
- Đã kích hoạt hằng số `CONCURRENCY_LIMIT = 5` đồng bộ tuyệt đối với `OLLAMA_NUM_PARALLEL` hạ tầng.
- Thay thế hoàn toàn cơ chế xử lý tuần tự/cồng kềnh cũ bằng `ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT)`, bắn 5 request đồng thời vào đồ thị LangGraph.
- Đã bọc luồng hoàn thành `as_completed` bằng thư viện `tqdm` để hiển thị thanh tiến trình trực quan theo thời gian thực (Real-time Progress Bar).

## 2. Bảo toàn tuyệt đối thứ tự đầu vào (Row Order Preservation) - [CRITICAL]
- Để giải quyết vấn đề bất đồng bộ khi luồng nào xong trước trả kết quả trước, mã nguồn mới đã đính kèm `index` (từ `df.iterrows()`) vào từng tác vụ (task).
- Kết quả trả về chứa dictionary kèm `index` gốc.
- **[QUAN TRỌNG]**: Trước khi tạo DataFrame đầu ra, hệ thống tự động gọi hàm `results.sort(key=lambda x: x["index"])`, đảm bảo 100% kết quả xuất ra không bị lệch hàng so với file đề bài, ngăn chặn triệt để nguy cơ sập hệ thống chấm điểm tự động.

## 3. Quản lý Đọc/Ghi chuẩn Thể lệ
- Đọc dữ liệu mặc định từ `data/public_test.csv`.
- Sau khi có kết quả đã sort, xuất ra `pandas.DataFrame` gồm các cột `id`, `reasoning` và `answer`.
- Ghi chuẩn xác vào thư mục và file `output/pred.csv`.

## 4. Tương thích lõi LangGraph
- Đã import chính xác `app_graph` từ `src.agent_graph`.
- Sử dụng hàm `app_graph.invoke(state)` để chạy suy luận (Tự động thích ứng đồng bộ với các node bất đồng bộ trong graph).
- Tách `reasoning` và `answer` một cách sạch sẽ từ Object Dict trả về bởi Pydantic Structured Output.

Hệ thống đã đạt giới hạn tốc độ thiết kế với Ollama 5-luồng và sẵn sàng cho bài Test chính thức với 2000 câu!
