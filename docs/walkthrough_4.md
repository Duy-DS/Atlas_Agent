# 🚀 BÁO CÁO NGHIỆM THU: BƯỚC 4 - TỐI ƯU HÓA I/O & XỬ LÝ ĐỒNG THỜI (CONCURRENCY)

Quá trình tối ưu hóa luồng thực thi chính của hệ thống `Atlas_Agent` đã được hoàn tất thành công. Mục tiêu của bước này là tăng thông lượng xử lý khi chạy batch lớn, tận dụng đồng thời nhiều worker để ép xung GPU VRAM, đồng thời vẫn giữ đúng thứ tự câu hỏi đầu vào trong file kết quả cuối cùng.

Dưới đây là báo cáo chi tiết về các thay đổi đã áp dụng.

## 1. Đánh Giá Luồng Xử Lý Hiện Tại

Trước khi tối ưu, `main.py` đã đọc toàn bộ dữ liệu rồi xử lý batch theo kiểu tuần tự:
- Có chia lô dữ liệu theo `BATCH_SIZE`
- Nhưng các batch vẫn được xử lý lần lượt, chưa tận dụng concurrency ở tầng điều phối
- Kết quả được ghi ra CSV sau khi xử lý xong, nhưng chưa có cấu trúc rõ ràng để đảm bảo vừa song song vừa giữ thứ tự đầu vào

Điều này khiến GPU và backend inference chưa được khai thác đủ trong kịch bản 2000 câu hỏi.

## 2. Tối Ưu Hóa Batching & Concurrency

### [MODIFY] [main.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/main.py)
Luồng thực thi chính đã được tổ chức lại theo hướng batch + worker pool:

- Thêm hàm `chunk_items(...)` để chia danh sách câu hỏi thành các lô có thứ tự rõ ràng
- Thêm hàm `execute_batches_with_threadpool(...)` để đẩy các batch vào `ThreadPoolExecutor`
- Mỗi batch được xử lý song song bởi worker riêng
- Kết quả của từng batch được lưu lại theo `batch_index`, nên khi ghép lại vẫn giữ đúng thứ tự đầu vào

Đoạn xử lý chính hiện tại dùng:
- `BATCH_SIZE=10` mặc định
- `CONCURRENCY_LIMIT=5` mặc định, có thể điều chỉnh bằng biến môi trường

### Cơ chế an toàn ghi I/O
Để tránh race condition khi nhiều worker hoàn thành gần như cùng lúc:
- Không ghi trực tiếp từ worker thread
- Tất cả kết quả được gom về main thread
- Main thread mới thực hiện ghi `pred.csv`

Cách này vừa an toàn vừa đơn giản hơn so với việc dùng `threading.Lock()` cho từng lần ghi.

## 3. Trải Nghiệm Điều Khiển Tiến Độ

### [MODIFY] [main.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/main.py)
Đã tích hợp `tqdm` để hiển thị progress bar theo **từng batch**, thay vì từng câu hỏi:
- Mỗi batch hoàn tất sẽ cập nhật một bước tiến độ
- Phù hợp hơn với xử lý dữ liệu lớn
- Giúp quan sát trạng thái thực thi rõ ràng hơn khi chạy 2000 câu hỏi

## 4. Kiểm Tra Kỹ Thuật

Sau khi thay đổi, mình đã kiểm tra:
- `python -m py_compile main.py test/test_main_batching.py` chạy thành công
- Test mới `test/test_main_batching.py` pass
- Hành vi bảo toàn thứ tự đầu vào đã được xác nhận qua test

### [ADD] [test/test_main_batching.py](file:///f:/JOB/HACKAITHON/Atlas_Agent/test/test_main_batching.py)
Đã bổ sung test cho hai hành vi cốt lõi:
- `chunk_items(...)` chia batch đúng thứ tự
- `execute_batches_with_threadpool(...)` trả kết quả theo đúng thứ tự input dù worker hoàn thành không đồng thời

## 5. Lợi Ích Đạt Được

Sau bước tối ưu này, hệ thống có các lợi ích rõ rệt:
- Tận dụng tốt hơn khả năng xử lý đồng thời của backend inference
- Giảm thời gian chờ giữa các batch lớn
- Giữ nguyên thứ tự câu hỏi đầu vào trong file `pred.csv`
- Tránh race condition khi ghi kết quả
- Có progress bar theo batch giúp theo dõi tiến độ dễ hơn

> [!TIP]
> Nếu cần ép thêm hiệu năng, bước tiếp theo nên benchmark `BATCH_SIZE` và `CONCURRENCY_LIMIT` theo từng GPU cụ thể để tìm ngưỡng tối ưu giữa VRAM, độ ổn định và throughput.

Hệ thống `Atlas_Agent` đã hoàn tất bước tối ưu hóa I/O và concurrency, sẵn sàng cho các bài test tải lớn và benchmark thực tế trên GPU.
