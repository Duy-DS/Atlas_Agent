# THUYẾT MINH PHƯƠNG PHÁP

## Cuộc thi Vietnamese Student HackAIthon 2026 — Bảng C: INNOVATOR

**Tên dự án:** Atlas Agent  
**Đội thi:** Atlas Agents  

| Thành viên | Vai trò | Công việc chính |
|---|---|---|
| Lê Phước Thành | Tech Lead & MLOps Engineer | Khởi tạo Project, Git Workflow, Docker, Entry-point I/O, Review PR |
| Trần Chí Vỹ | LangGraph Architect | State Machine, Tool Calling, Prompt Engineering |
| Nguyễn Tấn Duy | Data & RAG Engineer | Vector Database, Embedding Pipeline, Search Tool |
| Nguyễn Công Chí | Model Optimizer | Quantization, vLLM, Batching Optimization |
| Đường Minh Đức | QA, UI Tester & Technical Writer | Mock Data, Web UI Test, Thuyết minh phương pháp |

---

## 1. Tổng quan giải pháp

Atlas Agent là một hệ thống **AI Agent tự động trả lời câu hỏi trắc nghiệm** (A/B/C/D), được xây dựng trên kiến trúc **ReAct Agent** kết hợp **Retrieval-Augmented Generation (RAG)**. Hệ thống có khả năng:

- **Tự quyết định** gọi công cụ tra cứu (RAG) hay trả lời trực tiếp bằng kiến thức nội tại của LLM.
- **Suy luận logic** theo phương pháp Chain-of-Thought (CoT) trước khi chọn đáp án.
- **Đảm bảo 100% đầu ra hợp lệ** nhờ cơ chế parse và fallback 3 tầng.
- **Chạy hoàn toàn offline** trong Docker container, không phụ thuộc dịch vụ cloud.

---

## 2. Kiến trúc hệ thống

### 2.1. Sơ đồ tổng quan

```
Input CSV (/data/public_test.csv)
        │
        ▼
┌─────────────────┐
│  Preprocessing   │  Đọc CSV, chuyển mỗi dòng thành text
└────────┬────────┘
         ▼
┌─────────────────┐     ┌──────────────────┐
│   Agent Node     │────▶│  Tool Node (RAG)  │
│  (LLM Reasoning) │◀────│  ChromaDB Search  │
└────────┬────────┘     └──────────────────┘
         │
         ▼  (Nếu không cần RAG → trả lời trực tiếp)
┌─────────────────┐
│  Parse Answer    │  Trích xuất A/B/C/D từ JSON output
└────────┬────────┘
         ▼
Output CSV (/output/pred.csv)
```

### 2.2. Các thành phần chính

| Thành phần | Công nghệ | Mô tả |
|---|---|---|
| **Orchestrator** | LangGraph StateGraph | Điều phối luồng xử lý Agent theo đồ thị trạng thái |
| **LLM Inference** | Ollama (Qwen3.5) | Mô hình ngôn ngữ chạy local để suy luận |
| **RAG Engine** | ChromaDB + LangChain | Vector Database lưu trữ và truy xuất tri thức |
| **Embedding** | all-MiniLM-L6-v2 / BGE-m3 | Sinh vector biểu diễn ngữ nghĩa cho tài liệu |
| **Web UI** | Streamlit | Giao diện test, debug và đánh giá kết quả |
| **Container** | Docker + Docker Compose | Đóng gói toàn bộ môi trường chạy thống nhất |

---

## 3. Chi tiết phương pháp

### 3.1. ReAct Agent — Kiến trúc tự quyết định

Khác với pipeline RAG truyền thống (luôn gọi RAG cho mọi câu hỏi), Atlas Agent sử dụng kiến trúc **ReAct (Reasoning + Acting)** cho phép LLM tự đánh giá câu hỏi và quyết định hành động:

**4 quy tắc quyết định của Agent:**

| Quy tắc | Mô tả |
|---|---|
| **Rule 1 — EVALUATE BEFORE CALLING** | Nếu là kiến thức tổng quát, toán cơ bản → trả lời trực tiếp, không gọi RAG |
| **Rule 2 — CONTEXT ALREADY PROVIDED** | Nếu câu hỏi đã chứa đoạn văn/context → trả lời trực tiếp |
| **Rule 3 — ONLY USE RAG WHEN NECESSARY** | Chỉ gọi RAG khi cần thông tin từ tài liệu bên ngoài |
| **Rule 4 — DIRECT RESPONSE** | Khi không cần tool → trả JSON đáp án ngay lập tức |

**Lợi ích so với pipeline cứng:**

| Tiêu chí | Pipeline RAG cứng | ReAct Agent (Atlas) |
|---|---|---|
| Tool calling | Luôn gọi RAG | Chỉ gọi khi cần |
| Tài nguyên | Lãng phí cho câu hỏi đơn giản | Tối ưu |
| Kết quả | Có thể nhiễu do context không liên quan | Chính xác hơn |
| Mở rộng | Khó thêm tool mới | Dễ dàng thêm tool |

### 3.2. Chain-of-Thought (CoT) Prompting

Hệ thống sử dụng kỹ thuật CoT để ép LLM thực hiện suy luận có cấu trúc trước khi đưa ra đáp án:

1. **Phân tích ngữ cảnh** — Đọc hiểu câu hỏi và tài liệu liên quan.
2. **Tranh luận từng phương án** — Giải thích logic tại sao mỗi đáp án A/B/C/D đúng hoặc sai.
3. **Kết luận** — Chọn đáp án cuối cùng dưới dạng JSON chuẩn hóa.

**Format đầu ra bắt buộc:**
```json
{
    "reasoning": "Phân tích chi tiết và loại bỏ phương án sai",
    "answer": "B"
}
```

### 3.3. RAG Pipeline — Truy xuất tri thức

#### Ingestion (Nạp dữ liệu):
- Đọc tài liệu nguồn (`.txt`) bằng LangChain `TextLoader`.
- Cắt văn bản thông minh bằng `RecursiveCharacterTextSplitter` với `chunk_size=100`, `chunk_overlap=50`.
- Sinh embedding vector cho mỗi chunk.
- Lưu vào ChromaDB (local persistent, không phụ thuộc cloud).

#### Retrieval (Truy xuất):
- Nhận query từ Agent → sinh embedding cho query.
- Tìm kiếm **top-3 chunks** có độ tương đồng cosine cao nhất từ ChromaDB.
- Ghép các chunks thành context trả về cho Agent.

#### Embedding Model:
- **Ưu tiên 1:** HuggingFace Inference API với model `BAAI/bge-m3` (nếu có HF_TOKEN).
- **Ưu tiên 2:** Local model `all-MiniLM-L6-v2` (~80MB, tải nhanh).
- **Fallback:** TF-IDF hash-based embedding khi không có model nào khả dụng.

### 3.4. Cơ chế đảm bảo đầu ra — 3 tầng bảo vệ

Đầu ra **luôn được đảm bảo** là một trong `A`, `B`, `C`, `D`:

| Tầng | Cơ chế | Mô tả |
|---|---|---|
| **Tầng 1** | System Prompt | Yêu cầu LLM trả về JSON chuẩn `{"reasoning": "...", "answer": "X"}` |
| **Tầng 2** | JSON Parser | Parse JSON → xử lý markdown wrapper → sửa JSON cắt cụt → regex fallback |
| **Tầng 3** | Answer Normalization | Trích xuất ký tự A-D đầu tiên; nếu không tìm thấy → mặc định `"A"` |

**Kết quả:** 100% câu hỏi luôn có đáp án hợp lệ, không bao giờ trả về giá trị rỗng hoặc lỗi.

### 3.5. Hỗ trợ chạy Local & Offline

Hệ thống hỗ trợ **2 chế độ LLM**:

| Chế độ | Model | Đặc điểm |
|---|---|---|
| **Cloud** | Groq API (Llama 3.1 8B Instant) | Nhanh, chính xác cao, hỗ trợ Tool Calling |
| **Local** | Ollama (Qwen3.5 0.8B) | Chạy offline hoàn toàn, nhẹ, pre-fetch RAG tự động |

Khi chạy local với model nhỏ (0.8B), hệ thống tự động **pre-fetch RAG context** và nhúng vào prompt vì model nhỏ không đủ khả năng tự quyết định gọi tool.

---

## 4. Triển khai Docker

### 4.1. Kiến trúc Docker Compose

```yaml
Services:
  ollama:        # Ollama server chạy LLM local
  ollama-pull:   # Tự động tải model Qwen3.5:0.8B
  app:           # Atlas Agent application
```

### 4.2. Entry-point

Hệ thống hỗ trợ 2 chế độ chạy:
- **Batch mode** (`main.py`): Đọc toàn bộ CSV → chạy Agent → xuất `pred.csv`.
- **Streamlit mode** (`app_ui.py`): Giao diện web tương tác, upload CSV, xem log suy luận.

### 4.3. Đường dẫn I/O theo yêu cầu BTC

| Mục | Đường dẫn |
|---|---|
| Input | `/data/public_test.csv` hoặc `/data/private_test.csv` |
| Output | `/output/pred.csv` |
| Format output | `qid,answer` (A/B/C/D) |

---

## 5. Công nghệ sử dụng

| Hạng mục | Công nghệ | Phiên bản |
|---|---|---|
| Ngôn ngữ | Python | 3.11 |
| Agent Framework | LangGraph + LangChain | ≥ 0.2.0 |
| LLM (local) | Ollama + Qwen3.5 | 0.8B |
| Vector Database | ChromaDB | ≥ 0.5.0 |
| Embedding | Sentence-Transformers / BGE-m3 | ≥ 3.0.0 |
| Web UI | Streamlit | 1.35.0 |
| Container | Docker + Docker Compose | Latest |
| Data Processing | Pandas | 2.2.2 |

---

## 6. Chiến lược tối ưu

### 6.1. Tối ưu tốc độ inference
- Sử dụng model nhẹ (Qwen3.5 0.8B) phù hợp triển khai trên phần cứng hạn chế.
- Agent tự bỏ qua RAG cho câu hỏi đơn giản → giảm latency đáng kể.
- Hỗ trợ GPU acceleration (NVIDIA Container Toolkit) khi có GPU.

### 6.2. Tối ưu chất lượng
- CoT Prompting buộc LLM suy luận từng bước thay vì đoán mò.
- RAG cung cấp context chính xác từ tài liệu nguồn cho câu hỏi chuyên biệt.
- Embedding đa ngôn ngữ (BGE-m3) hỗ trợ tốt tiếng Việt.

### 6.3. Tối ưu độ ổn định
- Fallback 3 tầng cho embedding model (Online → Local → Hash-based).
- Parse đáp án 3 tầng đảm bảo 100% output hợp lệ.
- Thiết kế cross-platform (Windows/Linux) bằng `pathlib`.
- Không hard-code API key, đọc từ biến môi trường `.env`.

---

## 7. Quy trình xử lý từng câu hỏi

```
1. Đọc câu hỏi từ CSV
       ↓
2. Agent đánh giá câu hỏi (4 quy tắc)
       ↓
   ┌───────────────────────┐
   │ Cần tra cứu tài liệu? │
   └───────┬───────┬───────┘
        Có ↓       ↓ Không
   ┌────────┐  ┌──────────────┐
   │  RAG    │  │ Trả lời      │
   │  Search │  │ trực tiếp    │
   └────┬───┘  └──────┬───────┘
        ↓              ↓
3. LLM suy luận CoT (phân tích A/B/C/D)
       ↓
4. Parse JSON → trích xuất đáp án
       ↓
5. Ghi vào pred.csv
```

---

## 8. Cách reproduce kết quả

### 8.1. Chạy bằng Docker (khuyến nghị)

```bash
# Clone repo
git clone https://github.com/Duy-DS/Atlas_Agent.git
cd Atlas_Agent

# Đặt file test vào thư mục data/
cp public_test.csv data/

# Build và chạy
docker compose up --build

# Kết quả tại output/pred.csv
```

### 8.2. Chạy local

```bash
# Tạo môi trường
python -m venv .venv
source .venv/bin/activate   # Linux
pip install -r requirements.txt

# Cấu hình .env
echo "OLLAMA_BASE_URL=http://localhost:11434" > .env
echo "MODEL_NAME=qwen3.5:0.8b" >> .env

# Chạy batch mode
python main.py

# Hoặc chạy Streamlit UI
streamlit run src/app_ui.py
```

---

## 9. Đánh giá và kiểm thử

Hệ thống cung cấp nhiều phương thức kiểm thử:

- **Unit test Agent** (`test/test_agent_no_RAG.py`): Kiểm tra Agent trả lời trực tiếp.
- **Unit test RAG** (`test/test_agent_to_RAG.py`): Kiểm tra Agent gọi tool RAG.
- **Smoke test** (`test/test_graph.py`): Kiểm tra luồng đồ thị xuyên suốt.
- **Batch evaluation** (`check_cautraloi.py`): So sánh pred.csv với answer key, tính accuracy.
- **Web UI** (`src/app_ui.py`): Upload CSV → chạy Agent → xem suy luận → đánh giá accuracy.

---

## 10. Tính sáng tạo và điểm nổi bật

1. **ReAct Agent thay vì RAG Pipeline cứng** — Agent tự quyết định khi nào cần tra cứu, tiết kiệm tài nguyên và giảm nhiễu.
2. **Thiết kế Module hóa** — Cho phép 5 thành viên phát triển song song nhờ kỹ thuật Mocking, tăng tốc độ phát triển.
3. **3 tầng bảo vệ đầu ra** — Đảm bảo 100% câu hỏi luôn có đáp án hợp lệ, không bao giờ lỗi format.
4. **3 tầng fallback embedding** — Hệ thống vẫn hoạt động ngay cả khi thiếu model chính.
5. **Dual-mode LLM** — Linh hoạt chuyển đổi giữa Cloud API và Local Ollama chỉ bằng biến môi trường.
6. **Web UI tích hợp** — Giao diện Streamlit trực quan để test, debug, và demo sản phẩm.

---

*Tài liệu thuyết minh phương pháp — Đội Atlas Agents — Vietnamese Student HackAIthon 2026*
