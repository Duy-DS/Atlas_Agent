# 🤖 Atlas_Agent - Giải Pháp Trợ Lý Ảo Đa Tác Vụ
**Đội thi:** Ngũ Lão Tinh 
**Cuộc thi:** Vietnamese Student HackAIthon 2026 - Bảng C (Innovator)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker Supported](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-orange.svg)](https://python.langchain.com/)

---

## 📖 Giới thiệu dự án
**Atlas_Agent** là một hệ thống AI Agent thông minh được thiết kế đặc biệt để giải quyết các bài toán trắc nghiệm phức tạp. Thay vì áp dụng phương pháp đoán mò hay học vẹt (hard-code), Atlas_Agent sử dụng kiến trúc đồ thị trạng thái (State Graph) kết hợp với kỹ thuật suy luận chuỗi (Chain-of-Thought / ReAct) để tự động đọc hiểu, tìm kiếm ngữ cảnh, và đưa ra quyết định logic nhất.

### 🛠️ Tech Stack Cốt Lõi
* **Main LLM:** Qwen 8B (Đảm bảo tiêu chuẩn $\le 9B$ tham số).
* **Inference Engine:** vLLM (Tối ưu hóa tốc độ Reg/s bằng PagedAttention).
* **Orchestrator:** LangGraph & LangChain (Quản lý luồng suy luận Multi-Agent).
* **RAG Pipeline:** Chroma (Vector Store local) & BGE-m3 (HuggingFaceEmbeddings).

---

## ✨ Điểm Nhấn Công Nghệ (Tech Highlights)
> *[LƯU Ý DÀNH CHO TEAM: Hãy điền các tính năng đặc biệt của hệ thống vào đây sau khi chốt phương án. Dưới đây là khung gợi ý]*

* **Chèn điểm nhấn 1 vào đây** (Ví dụ: Cơ chế Tool Calling thông minh giúp Agent tự đánh giá độ khó câu hỏi trước khi gọi RAG...)
* **Chèn điểm nhấn 2 vào đây** (Ví dụ: Tối ưu hóa Inference với vLLM Batching giúp xử lý x câu hỏi/giây...)
* **Chèn điểm nhấn 3 vào đây** (Ví dụ: Xử lý Vector Store Local hoàn toàn không phụ thuộc Cloud...)

---

## 📁 Cấu Trúc Thư Mục
Hệ thống được thiết kế chuẩn mực, đáp ứng 100% yêu cầu I/O của Ban tổ chức:
```text
/atlas_agent_ngu_lao_tinh
├── /data               # Nơi chứa file input (public_test.csv hoặc private_test.csv)
├── /output             # Nơi lưu file kết quả tự động (pred.csv)
├── /chroma_db          # CSDL Vector lưu trữ cục bộ (Persistent)
├── /src
│   ├── rag_engine_v2.py # Module RAG (Langchain, BGE-m3, Tool Calling)
│   ├── agent_graph.py   # Module định nghĩa tư duy Agent (LangGraph)
│   └── main.py          # Entry-point kết nối I/O và khởi chạy hệ thống
├── Dockerfile          # Cấu hình đóng gói môi trường
├── requirements.txt    # Danh sách thư viện phụ thuộc
└── run_local.sh        # Script chạy test nhanh trên local

```

---

## 🚀 Hướng Dẫn Cài Đặt & Vận Hành (Reproduction Steps)

Hệ thống hỗ trợ chạy trên cả môi trường phát triển (Local) và môi trường đóng gói (Docker). 

Lưu ý: Yêu cầu bắt buộc phải có GPU (Card đồ họa rời) hỗ trợ CUDA.

### Cách 1: Chạy trực tiếp trên máy Local (Development Mode)

Phù hợp cho việc debug và kiểm thử trong quá trình phát triển (Khuyên dùng WSL2 trên Windows hoặc Ubuntu).

1. Cài đặt môi trường:

```Bash
# Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate  # Trên Linux/WSL2
# venv\Scripts\activate   # Trên Windows

# Cài đặt thư viện
pip install -r requirements.txt
```

2. Chuẩn bị dữ liệu:

Đảm bảo bạn đã đặt file đề thi public_test.csv (hoặc private_test.csv) vào thư mục /data.

3. Khởi chạy hệ thống:

Có thể chạy lệnh trực tiếp bằng Python hoặc sử dụng script đã chuẩn bị sẵn:

```Bash
bash run_local.sh
# Hoặc chạy lệnh: python src/main.py
```

Kết quả dự đoán sẽ tự động được ghi vào /output/pred.csv.

### Cách 2: Chạy qua Docker Container (Official Submission Mode)

Đây là phương pháp chuẩn để Ban Giám Khảo và hệ thống tự động chấm điểm nghiệm thu dự án.

1. Tải (Pull) Image từ Docker Hub:

(Đang cập nhật - Dev 1 sẽ điền link Docker Hub chính thức vào đây trước khi nộp bài)

```Bash
docker pull ngu_lao_tinh/atlas_agent:v1.0
```

(Hoặc tự Build Image trên máy của bạn):

```Bash
docker build -t ngu_lao_tinh/atlas_agent .
```
2. Chạy Container với Volume Mapping:

Lệnh dưới đây sẽ mount thư mục /data và /output trên máy tính của bạn vào đúng vị trí trong Container, đồng thời cấp quyền sử dụng GPU cho Docker:

```Bash
docker run --gpus all \
  -v $(pwd)/data:/data \
  -v $(pwd)/output:/output \
  ngu_lao_tinh/atlas_agent:v1.0
```

Sau khi tiến trình chạy xong, mở thư mục /output trên máy tính của mình để kiểm tra file pred.csv

---

## 👥 Nhóm Tác Giả (Ngũ Lão Tinh)

- Dev 1: MLOps & System Architecture - [🌿Lá🌿](https://github.com/thanhlek5)

- Dev 2: LangGraph Logic & Main LLM - [CHIVY2005](https://github.com/CHIVY2005)

- Dev 3: Data & RAG Engineering - [Duy-DS](https://github.com/Duy-DS)

- Dev 4: Model Optimization - [nguyen-cong-tri](https://github.com/nguyen-cong-tri)

- Dev 5: QA & Documentation - [mDuck](https://github.com/MinDuwcs)