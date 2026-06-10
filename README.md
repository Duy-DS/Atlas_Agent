# Atlas_Agent - Giải Pháp Trợ Lý Ảo Đa Tác Vụ

**Atlas Agent** là một AI Agent được thiết kế từ mô hình ngôn ngữ lớn để xử lý đa tác vụ trong khuôn khổ cuộc thi Vietnamese Student HackAIthon 2026.  


## 📖 Giới thiệu dự án  
**Atlas_Agent** là một hệ thống AI Agent thông minh được thiết kế đặc biệt để giải quyết các bài toán trắc nghiệm phức tạp. Thay vì áp dụng phương pháp đoán mò hay học vẹt (hard-code), Atlas_Agent sử dụng kiến trúc đồ thị trạng thái (State Graph) kết hợp với kỹ thuật suy luận chuỗi (Chain-of-Thought / ReAct) để tự động đọc hiểu, tìm kiếm ngữ cảnh, và đưa ra quyết định logic nhất.
Dự án hướng đến việc xây dựng một hệ thống AI Agent có khả năng:  
- Đọc và phân tích câu hỏi đầu vào.
- Suy luận để chọn đáp án phù hợp.
- Gọi công cụ hỗ trợ khi cần thiết.
- Kết hợp RAG để truy xuất thông tin liên quan.
- Xuất kết quả theo đúng định dạng yêu cầu của cuộc thi.
- Đóng gói và chạy được trong môi trường local hoặc Docker.

## 🎯 Mục Tiêu Dự Án:

Dự án được xây dựng với các mục tiêu chính:

1. Xây dựng AI Agent có khả năng reasoning thay vì trả lời theo hard-code.
2. Tích hợp cơ chế tool calling để Agent có thể sử dụng công cụ hỗ trợ.
3. Sử dụng RAG pipeline để tăng khả năng truy xuất và xử lý thông tin.
4. Tối ưu tốc độ inference bằng vLLM và các kỹ thuật tối ưu model.
5. Đảm bảo hệ thống đọc input và ghi output đúng chuẩn.
6. Cung cấp tài liệu kỹ thuật rõ ràng để giải thích kiến trúc và phương pháp triển khai.

## 🌐 Bối Cảnh Đề Bài:  
Tên cuộc thi: Vietnamese Student HackAIthon 2026  
Bảng: C - INNOVATOR  
Đội thi: Ngũ Lão Tinh  
Vòng: Vòng 1  
Yêu cầu chính: Cá nhân/đội thi tập trung vào việc sử dụng các mô hình ngôn ngữ lớn để thiết kế AI Agent xử lý đa tác vụ.  
Định dạng đầu vào: Đọc public_test.csv hoặc private_test.csv tại /data  
Định dạng đầu ra:  
- Docker Container: Docker hub.  
- Ghi file pred.csv vào /output với hai cột: qid,answer (A/B/C/D).  
- Github chứa code và các chạy reproduce kết quả trong container.  
- Tài liệu thuyết minh phương pháp: Định dạng tuỳ chọn với mục tiêu thể hiện.  
  được rõ nhất tính sáng tạo, hiệu quả của chiến lược tối ưu mô hình đã lựa chọn.  
  Thời hạn nộp bài: 02/6/2026 - 23/6/2026.  

## 📐 Kiến Trúc Tổng Quan  
Hệ thống dự kiến bao gồm các thành phần chính:

Input CSV
    ↓
Preprocessing
    ↓
LangGraph Agent
    ↓
Main LLM
    ↓
Tool Calling / RAG Search
    ↓
Reasoning & Answer Selection
    ↓
Output pred.csv  
### Các Thành Phần Chính  
|Thành Phần|Vai Trò|  
|---|---|  
|Main LLM|Mô hình ngôn ngữ lớn dùng để suy luận và chọn đáp án|  
|LangGraph|Điều phối luồng xử lý Agent theo dạng state machine|  
|Tool Calling|Cho phép Agent gọi công cụ khi cần thêm thông tin|  
|RAG Pipeline|Truy xuất dữ liệu liên quan để hỗ trợ suy luận|  
|Vector Database|Lưu trữ embedding phục vụ truy xuất|  
|Reranker|Sắp xếp lại kết quả truy xuất để giảm nhiễu|  
|vLLM|Tăng tốc inference cho mô hình|  
|Docker|Đóng gói môi trường chạy thống nhất|  


## 🛠️ Công Nghệ Sử Dụng

## 👥 Phân Công Thành Viên

|Thành Viên|Vai trò|Công việc|
|---|---|---|
|Lê Phước Thành|Tech Lead & MLOps Engineer|Khởi tạo Project & Git Workflow, Đóng gói môi trường (Docker), Xây dựng luồng I/O (Entry-point), Review Pull Request (Core Quality Control)|
|Trần Chí Vỹ|LangGraph Architect|Dựng State Machine, Tích hợp Tool Calling, Kỹ sư Prompt (Prompt Engineering)|
|Nguyễn Tấn Duy|Data & RAG Engineer|Dựng Vector Database, Xây dựng Pipeline Embedding, Hoàn thiện Tool Tìm kiếm|
|Nguyễn Công Chí|Model Optimizer|Nén Mô Hình (Quantization), Khởi chạy vLLM, Tối ưu Batching|
|Đường Minh Đức|QA, UI Tester & Technical Writer|Xây dựng Dữ liệu Kiểm thử, Dựng Web UI Test Local, Soạn Thuyết Minh Phương Pháp|

## ⚙️ Cài Đặt Môi Trường  
### Clone Repo  
```
git clone https://github.com/Duy-DS/Atlas_Agent.git cd Atlas_Agent

```  
### Tạo Virtual Environment  
```
python -m venv .venv 
source .venv/bin/activate

```  
Trên Windows:  
```
python -m venv .venv
.venv\Scripts\activate
```  

### Cài Đặt Thư Viện  
```
pip install -r requirements.txt  
```  
### Cấu Hình Biến Môi Trường

## 📈 Chuẩn Dữ Liệu Đầu Vào và Đầu Ra

### Định Dạng Dữ Liệu Đầu Vào

File input dự kiến đặt tại:

**/data/public_test.csv**

Format dự kiến:  
qid,question,A,B,C,D  
Ví Dụ:  
qid,question,A,B,C,D  
1,"Việt Nam thuộc khu vực nào?",Đông Á,Đông Nam Á,Nam Á,Tây Á  
2,"Việt Nam gia nhập ASEAN năm nào?",1995,1997,1999,2001  

### Định Dạng Dữ Liệu Đầu Ra

File output cần được ghi tại:

**/output/pred.csv**

Format dự kiến:  
qid,answer
1,A
2,C
3,D  
Quy định:  
Cột qid phải giữ nguyên từ file input.  
Cột answer chỉ nhận một trong bốn giá trị: A, B, C, D.  
Không được để trống đáp án.  
Không ghi thêm reasoning hoặc log vào file output.  

## 🏃 Cách Chạy Project

### Build Docker image

```
docker build -t atlas-agent .
```

### Run Docker container

```
docker run \
  -v $(pwd)/local_data:/data \
  -v $(pwd)/local_out:/output \
  atlas-agent
```

## 🔄 Quy trình xử lý của Agent

1. Đọc câu hỏi từ file input.
2. Phân tích độ khó của câu hỏi.
3. Quyết định trả lời trực tiếp hoặc gọi RAG.
4. Nếu cần RAG:
   - Trích xuất keyword.
   - Gọi công cụ search.
   - Nhận top-k chunks.
   - Rerank kết quả.
5. Tổng hợp thông tin.
6. Suy luận và chọn đáp án A/B/C/D.
7. Ghi kết quả vào pred.csv.

## ✉️ Liên Hệ

Nếu có bất kỳ thắc mắc nào, vui lòng liên hệ:

| Thành Viên      | Email                             | Github                                       |
| --------------- | --------------------------------- | -------------------------------------------- |
| Lê Phước Thành  | [thanhlephuoc0202@gmail.com]      | [GIthub](https://github.com/thanhlek5)       |
| Trần Chí Vỹ     | [tanduy.work@gmail.com]           | [Github](https://github.com/CHIVY2005)       |
| Nguyễn Tấn Duy  | [tranchivy2005official@gmail.com] | [Github](https://github.com/Duy-DS)          |
| Nguyễn Công Chí | [congtri.studies@gmail.com]       | [Github](https://github.com/nguyen-cong-tri) |
| Đường Minh Đức  | [duongmd.work@gmail.com]          | [Github](https://github.com/MinDuwcs)        |
