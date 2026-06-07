# EXPLAIN DEV 3 - DATA / RAG ENGINEER (Atlas Agent)

## 1. Mục tiêu vai trò Dev 3
Dev 3 chịu trách nhiệm xây dựng "bộ nhớ tri thức" cho toàn bộ hệ thống Agent. Kết quả đầu ra của Dev 3 phải giúp Dev 2 (LangGraph Architect) có thể gọi tool tra cứu một cách ổn định, chính xác và dễ tích hợp.

Mục tiêu kỹ thuật cốt lõi:
- Thiết kế Local Vector Database chạy bền vững trên cả Windows và Linux (Docker).
- Xây dựng pipeline nạp dữ liệu (ingestion) có thể chạy lặp lại, không gây hỏng dữ liệu.
- Cung cấp tool `search_rag_database(query: str) -> str` để Main Agent truy vấn ngữ cảnh.
- Đảm bảo module RAG có thể tự kiểm thử độc lập bằng command line.

## 2. Phạm vi công việc Dev 3
### 2.1 Trách nhiệm chính
- Quản lý dữ liệu nguồn dùng cho tra cứu tri thức.
- Thiết kế chunking, embedding, lưu vector và retrieval.
- Tối ưu chất lượng truy xuất (recall + precision) bằng retrieval và rerank.
- Bảo đảm module chạy được trong môi trường hạn chế (không cloud DB).

### 2.2 Trách nhiệm bàn giao cho Dev 2
- Hàm tool đã sẵn sàng để bind vào LLM (`bind_tools`).
- Contract đầu vào/đầu ra rõ ràng, docstring đầy đủ tiếng Việt.
- Hướng dẫn tích hợp ngắn gọn và ví dụ gọi tool.

## 3. Ràng buộc kiến trúc và môi trường
- Vector DB phải là local persistent (Chroma), không phụ thuộc cloud service.
- Đường dẫn bắt buộc tương thích đa nền tảng bằng `pathlib`.
- Ưu tiên thiết kế module có fallback khi model không tải được (mạng, policy, DLL).
- Không hard-code secret/API key trong mã nguồn.

## 4. Thiết kế kỹ thuật đề xuất
### Bước 1: Khởi tạo storage và model
- Tạo `BASE_DIR` từ `Path(__file__).resolve().parent.parent`.
- Tạo `CHROMA_PATH = BASE_DIR / "chroma_db"`.
- Khởi tạo `PersistentClient` hoặc `Chroma(... persist_directory=...)`.
- Chọn device tự động (`cuda` nếu có, ngược lại `cpu`).

### Bước 2: Ingestion pipeline
- Đọc dữ liệu đầu vào (`.txt` hoặc tài liệu text hóa).
- Chunking có overlap để giảm mất ngữ cảnh:
  - Gợi ý: `chunk_size=500`, `chunk_overlap=50`.
- Sinh embedding cho chunks.
- Ghi dữ liệu vào vector DB:
  - Nên dùng cơ chế idempotent (`upsert` hoặc deduplicate ID) để chạy lặp lại an toàn.

### Bước 3: Retrieval tool cho Agent
- Định nghĩa hàm tool:
  - `search_rag_database(query: str) -> str`
- Quy trình truy xuất đề xuất:
  1. Query embedding.
  2. Vector retrieval lấy top-k ứng viên thô (vd: top 10).
  3. Rerank để lọc top 3 tốt nhất.
  4. Ghép context trả về cho Agent theo format rõ ràng.

### Bước 4: Unit test độc lập
- Tạo dữ liệu mock.
- Chạy luồng ingest -> search.
- In kết quả để kiểm tra mức liên quan của ngữ cảnh trả về.
- Đảm bảo script chạy được bằng lệnh trực tiếp:
  - `python src/rag_engine.py`

## 5. Chuẩn chất lượng đầu ra của Dev 3
### 5.1 Đúng chức năng
- Tool nhận đúng query tiếng Việt tự nhiên.
- Trả về tối đa 3 đoạn ngữ cảnh liên quan nhất.
- Có thông báo rõ ràng khi không tìm thấy dữ liệu.

### 5.2 Ổn định vận hành
- Không crash khi thiếu model chính; có fallback hợp lý.
- Không vỡ khi chạy ingest lặp lại nhiều lần.
- Không phụ thuộc đường dẫn tuyệt đối theo máy cá nhân.

### 5.3 Dễ tích hợp
- Hàm tool có type hint đầy đủ.
- Docstring tiếng Việt đủ chi tiết để LLM hiểu khi nào cần gọi tool.
- Có snippet mẫu cho Dev 2 dùng `bind_tools`.

## 6. Contract bàn giao cho Dev 2
### Input contract
- `query: str`
- Là câu hỏi hoặc yêu cầu truy vấn tri thức từ Main Agent.

### Output contract
- `str` chứa các đoạn context đã lọc, ngăn cách bằng `---`.
- Nếu không có dữ liệu liên quan: trả thông báo tiếng Việt thống nhất.

### Hành vi kỳ vọng
- Tool chỉ trả tri thức truy xuất, không tự suy diễn đáp án cuối cùng.
- Main Agent sẽ dùng context này để lập luận và sinh câu trả lời.

## 7. Checklist trước khi merge
- [ ] Chạy local thành công module RAG.
- [ ] Ingestion chạy lặp lại không lỗi trùng ID.
- [ ] Search trả ra đúng domain context.
- [ ] Tool bind được vào LLM trong test tích hợp.
- [ ] Không lộ API key/secret trong source.
- [ ] Có hướng dẫn ngắn cho Dev 2.

## 8. Mẫu tích hợp cho Dev 2 (tham khảo)
```python
from rag_engine_v3 import search_rag_database

llm_with_tools = llm.bind_tools([search_rag_database])
response = llm_with_tools.invoke("Cơ cấu giải thưởng của bảng C HackAIthon là gì?")
```

## 9. Rủi ro thường gặp và cách xử lý
- Lỗi phụ thuộc model (`sentence_transformers`, `sklearn`, DLL policy):
  - Cần fallback embedding local để không block toàn hệ thống.
- Lỗi model LLM bị decommission:
  - Đọc model từ biến môi trường để đổi nhanh không sửa code.
- Lỗi nhiễu do dữ liệu cũ trong vector DB:
  - Tách collection theo phiên bản dữ liệu hoặc làm sạch định kỳ.

## 10. Lộ trình tối ưu tiếp theo
- Chuẩn hóa metadata cho mỗi chunk (nguồn, chủ đề, phiên bản tài liệu).
- Thêm reranker mạnh hơn khi môi trường cho phép.
- Thêm đánh giá tự động (retrieval metrics) trên bộ câu hỏi kiểm thử.
- Tách cấu hình model/chunking vào file config để dễ tinh chỉnh theo vòng thi.
