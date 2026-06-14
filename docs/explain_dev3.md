# EXPLAIN DEV 3 - DATA & RAG ENGINEER (Atlas Agent)

## 1. Mục tiêu vai trò Dev 3

**Dev 3** ban đầu chịu trách nhiệm xây dựng "bộ nhớ tri thức" và các công cụ RAG cho Agent. Trong tiến trình phát triển và kiểm thử thực tế, để tối ưu hóa hiệu năng, giảm dung lượng bộ cài Docker và tránh nhiễu ngữ cảnh cho LLM, vai trò của Dev 3 đã được tối ưu hóa.

Mục tiêu cốt lõi:
- Đảm bảo luồng dữ liệu CSV đầu vào (`/data/*.csv`) được đọc chính xác không lỗi font/BOM.
- Ghi kết quả dự đoán đúng định dạng yêu cầu của BTC (`/output/pred.csv`).
- Quản lý tệp dữ liệu tri thức cục bộ phục vụ tra cứu.

---

## 2. Các nhiệm vụ chi tiết (Bản đồ nhiệm vụ từ Task List)

### Task 3.1: Dựng Vector Database
* **Mô tả:** Cấu hình ChromaDB chạy ở chế độ local persistent tại `/chroma_db`.
* **Trạng thái:** **Đã thay đổi sang chế độ Tối ưu (Optimized/Pivoted)**.
* **Chi tiết:** Nhóm quyết định loại bỏ module ChromaDB cồng kềnh để giảm dung lượng Docker image nộp bài và tránh lỗi thiếu thư viện trên môi trường máy chấm thi chấm điểm. 

### Task 3.2: Xây dựng Pipeline Embedding
* **Mô tả:** Viết script làm sạch văn bản, cắt đoạn (chunking) và nhúng qua mô hình BGE-m3.
* **Trạng thái:** **Đã thay đổi sang chế độ Tối ưu (Optimized/Pivoted)**.
* **Chi tiết:** Để tối ưu hóa tốc độ suy luận (Inference Time), việc nhúng vector động được thay thế bằng việc truy cập trực tiếp tệp tri thức tĩnh cục bộ và tra cứu online thời gian thực bằng Wikipedia / Web Search.

### Task 3.3: Hoàn thiện Tool Tìm kiếm (RAG Tool)
* **Mô tả:** Code hàm `search_rag_database(query)` trong `src/rag_engine.py` kết hợp Qwen-Rerank.
* **Trạng thái:** **Đã thay đổi sang chế độ Tối ưu (Optimized/Pivoted)**.
* **Chi tiết:** File `src/rag_engine.py` đã được xóa bỏ hoàn toàn. Thay vào đó, Dev 3 đã xây dựng luồng nạp ngữ cảnh cục bộ từ file [data/mock_knowledge.txt](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/data/mock_knowledge.txt) thông qua `Retrieve Node` của Agent. Tệp tri thức tĩnh này được đọc thẳng vào RAM và truyền trực tiếp làm context nền cho LLM, mang lại tốc độ truy xuất cực nhanh và loại bỏ lỗi phân tích vector.

---

## 3. Quản lý Data Pipeline (`main.py`)

Do sự dịch chuyển trong kiến trúc, Dev 3 đã phối hợp cùng Dev 1 quản lý và kiểm soát toàn bộ luồng vào/ra của dữ liệu:
* **Đầu vào (Input):** Tự động nhận diện thư mục `/data` trong Docker hoặc thư mục local `./data` để nạp file kiểm thử.
* **Đầu ra (Output):** Xuất file kết quả đúng định dạng cột yêu cầu `qid,answer` tại `/output/pred.csv`.
* **Chạy song song (Batching):** Cấu hình Batch Size phù hợp cho mô hình để chạy song song thông qua hàm `abatch()` nhằm tăng điểm tốc độ suy luận.
