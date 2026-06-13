# Hướng dẫn di chuyển từ Groq API sang Local LLM (Docker Submission)

Tài liệu này hướng dẫn các thành viên trong team chuyển đổi cấu hình LLM từ sử dụng **Groq API** sang **Local LLM (Offline Model)** để chuẩn bị đóng gói Docker nộp bài.

> [!IMPORTANT]
> **Quy định của BTC:** Môi trường chấm thi chạy Offline hoàn toàn (không có kết nối Internet). Do đó, việc gọi các dịch vụ API bên ngoài (Groq, OpenAI, Gemini) sẽ bị chặn và gây lỗi crash hệ thống. Bắt buộc phải cấu hình Agent sử dụng mô hình chạy cục bộ.

---

## 1. Tổng quan cơ chế kết nối

Hiện tại, hệ thống sử dụng thư viện `langchain_openai` kết nối qua giao thức OpenAI-compatible. Điều này rất thuận tiện vì cả **vLLM** và **Ollama** đều hỗ trợ API format của OpenAI, chúng ta chỉ cần đổi `base_url`, `model` và `api_key` mà không cần sửa đổi bất kỳ logic cốt lõi nào của Agent.

```
+------------------+         giao thức OpenAI API         +---------------------+
|   Atlas Agent    |  ==================================> |  Local LLM Server   |
| (main.py/Graph)  |  (http://localhost:8000/v1)          |   (vLLM / Ollama)   |
+------------------+                                      +---------------------+
```

---

## 2. Các bước cấu hình chi tiết

### Bước 1: Điều chỉnh mã nguồn `src/agent_graph.py`

Thay vì hardcode endpoint của Groq, chúng ta nên viết code có tính linh hoạt cao, tự động đọc cấu hình từ biến môi trường (Environment Variables). 

Hãy cập nhật phần khởi tạo LLM trong [src/agent_graph.py](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/src/agent_graph.py) như sau:

```python
# Đọc cấu hình từ biến môi trường hoặc dùng fallback mặc định
llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
llm_model_name = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant")
llm_api_key = os.getenv("LLM_API_KEY", groq_api_key)

print(f"[*] Cấu hình LLM: Base URL={llm_base_url} | Model={llm_model_name}")

# Khởi tạo LLM tương thích chuẩn OpenAI
llm = ChatOpenAI(
    model=llm_model_name,
    api_key=llm_api_key, 
    base_url=llm_base_url,
    temperature=0.1
)
```

### Bước 2: Cấu hình biến môi trường trong `.env` (Khi chạy thử nghiệm local)

Khi muốn chạy thử với mô hình Local thay vì Groq trên máy cá nhân của bạn, hãy cập nhật file `.env`:

```env
# Cấu hình cho Local LLM Server (ví dụ vLLM đang chạy cổng 8000)
LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
LLM_API_KEY=sk-local-dev-key
```

### Bước 3: Cấu hình trong Dockerfile / docker-compose.yml (Khi nộp bài)

Khi đóng gói Docker nộp bài, BTC thường cung cấp thông tin Endpoint của LLM chạy trên máy chấm qua các biến môi trường của container. 

Đảm bảo trong tệp cấu hình container của bạn có định nghĩa các biến này:

```dockerfile
# Ví dụ cấu hình biến môi trường trong Dockerfile
ENV LLM_BASE_URL=http://11.11.11.11:8000/v1
ENV LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
ENV LLM_API_KEY=not-needed-for-local
```

---

## 3. Cách dựng Local LLM Server để kiểm thử

Để đảm bảo Agent chạy mượt mà trước khi nộp Docker, bạn nên tự chạy thử một Local LLM Server bằng một trong hai cách dưới đây:

### Cách 1: Sử dụng vLLM (Khuyên dùng nếu máy có GPU mạnh)
vLLM hỗ trợ throughput cực tốt và tương thích 100% với chuẩn OpenAI API.
```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-7B-Instruct \
    --port 8000 \
    --host 0.0.0.0
```

### Cách 2: Sử dụng Ollama (Dành cho máy cấu hình vừa phải)
Ollama rất nhẹ và dễ cài đặt trên mọi hệ điều hành.
1. Tải mô hình: `ollama pull qwen2.5:7b`
2. Chạy Server: Mặc định Ollama chạy tại `http://localhost:11434/v1`. Cấu hình biến môi trường:
   ```env
   LLM_BASE_URL=http://localhost:11434/v1
   LLM_MODEL_NAME=qwen2.5:7b
   ```

---

## 4. Kiểm tra trước khi nộp bài

> [!WARNING]
> Luôn chạy kiểm thử trước khi nộp Docker để tránh lỗi mất điểm đáng tiếc do cấu hình mạng.

1. Ngắt kết nối internet (nếu muốn giả lập môi trường BTC).
2. Chạy kiểm thử luồng async:
   ```bash
   python test/test_async.py
   ```
3. Chạy thử nghiệm end-to-end với file CSV:
   ```bash
   python main.py
   ```
4. Xác nhận file kết quả tại [output/pred.csv](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/output/pred.csv) được tạo ra đầy đủ và định dạng chính xác.
