# EXPLAIN DEV 3 - DATA PIPELINE & DOCKER DEPLOYMENT (Atlas Agent)

## 1. Mục tiêu vai trò Dev 3

Trong kiến trúc mới, module RAG cồng kềnh đã được lược bỏ để tối ưu hóa thời gian chạy và dung lượng Docker image. Vai trò của **Dev 3** chuyển trọng tâm sang **Quản lý dữ liệu đầu vào/đầu ra (Data Pipeline)** và **Đảm bảo tính tương thích môi trường (Docker & OS)** để nộp bài thành công lên hệ thống chấm thi tự động.

Mục tiêu cốt lõi:
- Đảm bảo luồng dữ liệu CSV đầu vào (`/data/*.csv`) được đọc chính xác không lỗi font/BOM.
- Ghi kết quả dự đoán đúng định dạng yêu cầu của BTC (`/output/pred.csv`).
- Thiết lập cơ chế chạy bất đồng bộ (Async Batching) để đạt tốc độ xử lý tối đa.
- Quản lý tệp tri thức tĩnh phục vụ tra cứu cục bộ (`data/mock_knowledge.txt`).

---

## 2. Phạm vi công việc Dev 3

### 2.1 Quản lý Data Pipeline (`main.py`)
* **Đầu vào (Input):**
  - Quét tự động thư mục `/data` (trong Docker) hoặc thư mục local `./data` để tìm file kiểm thử (`public_test.csv` hoặc `private_test.csv`).
  - Định dạng bảng đầu vào chứa: `qid`, `question`, `A`, `B`, `C`, `D`.
  - Kết hợp câu hỏi và các phương án thành một chuỗi text có cấu trúc gửi cho Agent.
* **Xử lý Batching:**
  - Sử dụng hàm `abatch()` từ đồ thị LangGraph (`app_graph`) của Dev 2 để chạy song song nhiều câu hỏi cùng một lúc.
* **Đầu ra (Output):**
  - Ghi tệp `pred.csv` tại `/output/` (Docker) hoặc `./output/` (Local).
  - Định dạng cột bắt buộc: `qid`, `answer` (A/B/C/D).

### 2.2 Quản lý Tri thức tĩnh (Local Knowledge Context)
- Do RAG Engine đã được gỡ bỏ, tri thức tĩnh cố định về cuộc thi hoặc tài liệu hướng dẫn được Dev 3 lưu trữ tại [data/mock_knowledge.txt](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/data/mock_knowledge.txt) (nếu cần).
- Đồ thị Agent sẽ nạp toàn bộ file này vào bộ nhớ trong bước `Retrieve Node` để cung cấp context cho LLM mà không cần thông qua bước tìm kiếm vector chậm chạp.

---

## 3. Ràng buộc Kỹ thuật & Docker

### 3.1 Đường dẫn tương thích Docker
Tất cả đường dẫn file đầu vào/đầu ra phải tuân thủ nghiêm ngặt cấu trúc thư mục Docker của BTC:
* **Input Path:** `/data/public_test.csv` hoặc `/data/private_test.csv`
* **Output Path:** `/output/pred.csv`

Hệ thống hỗ trợ cơ chế tự động nhận diện môi trường (Docker vs Local) trong `main.py`:
```python
def find_input_csv():
    if os.path.exists("/data"):
        # Chạy trong Docker
        ...
    return local_data_path # Chạy local
```

### 3.2 Khắc phục lỗi Encode trên Windows
Khi dev trên Windows, hệ thống rất dễ gặp lỗi `UnicodeEncodeError` khi in các câu hỏi tiếng Việt ra Console. Dev 3 đã tích hợp giải pháp cấu hình UTF-8 tự động tại đầu file `src/agent_graph.py` và chạy lệnh với biến môi trường:
```bash
# Windows PowerShell
$env:PYTHONUTF8=1; python main.py
```

---

## 4. Checklist bàn giao trước khi nộp bài

- [ ] File dữ liệu tri thức tĩnh [data/mock_knowledge.txt](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/data/mock_knowledge.txt) được cập nhật đầy đủ thông tin hỗ trợ thi cử.
- [ ] Hàm quét file CSV tự động nhận diện đúng file test của BTC.
- [ ] Thư mục `/output` được tạo tự động nếu chưa tồn tại.
- [ ] File `pred.csv` xuất ra có đúng 2 cột `qid` và `answer` (viết hoa A/B/C/D).
- [ ] Dockerfile cấu hình cài đặt tất cả thư viện trong `requirements.txt` và thiết lập biến môi trường `PYTHONUTF8=1`.
