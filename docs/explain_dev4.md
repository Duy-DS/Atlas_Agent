# EXPLAIN DEV 4 - LLM CONFIGURATION & API KEY (Atlas Agent)

## 1. Mục tiêu vai trò Dev 4

**Dev 4** chịu trách nhiệm quản lý cấu hình kết nối LLM, thiết lập biến môi trường, bảo mật API Key và đảm bảo cơ chế chuyển đổi linh hoạt giữa các LLM Providers (ví dụ: Groq API trực tuyến khi phát triển và Local LLM offline khi nộp bài).

Mục tiêu kỹ thuật cốt lõi:
- Đọc động cấu hình LLM từ tệp môi trường `.env` hoặc hệ thống Docker mà không cần chỉnh sửa mã nguồn.
- Thiết lập kết nối chuẩn tương thích OpenAI (`ChatOpenAI`) để có thể cắm trực tiếp vào bất kỳ API Server nào (Groq, OpenAI, vLLM, Ollama).
- Quản lý nhiệt độ mô hình (`temperature`), số lượng tokens đầu ra (`max_tokens`) để suy luận ổn định và tối ưu chi phí/tốc độ.

---

## 2. Thiết kế kết nối LLM linh hoạt

Trong mã nguồn [src/agent_graph.py](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/src/agent_graph.py), Dev 4 đã triển khai cấu hình động thông qua việc đọc biến môi trường:

```python
# Đọc cấu hình từ biến môi trường hoặc dùng fallback mặc định sang Groq API
llm_base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
llm_model_name = os.getenv("LLM_MODEL_NAME", "llama-3.1-8b-instant")
llm_api_key = os.getenv("LLM_API_KEY", groq_api_key)

# Khởi tạo mô hình tương thích chuẩn OpenAI
llm = ChatOpenAI(
    model=llm_model_name,
    api_key=llm_api_key, 
    base_url=llm_base_url,
    temperature=0.1
)
```

### Phân tích các chế độ hoạt động:

| Chế độ | Môi trường hoạt động | Biến môi trường cần thiết |
| :--- | :--- | :--- |
| **Online Mode (Groq)** | Phát triển, test local nhanh bằng API đám mây | `GROQ_API_KEY=gsk_...` trong file `.env` |
| **Offline Mode (Ollama)** | Chạy thử nghiệm offline cục bộ hoặc đóng gói Docker nộp bài | `LLM_BASE_URL=http://localhost:11434/v1` và `LLM_MODEL_NAME=qwen3.5:4b` |
| **vLLM Mode** | Khi team tự host vLLM Server hiệu năng cao | `LLM_BASE_URL=http://<ip-server>:8000/v1` và `LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct` |

---

## 3. Cấu hình tệp môi trường cục bộ `.env`

Tệp `.env` được sử dụng để lưu trữ các thông tin bảo mật và cấu hình riêng biệt của từng máy lập trình viên. 

> [!CAUTION]
> Tệp `.env` chứa API Key bảo mật (như `GROQ_API_KEY`). **Bắt buộc** phải khai báo tệp `.env` trong `.gitignore` để không vô tình đẩy thông tin nhạy cảm lên GitHub công khai.

Ví dụ tệp cấu hình mẫu `.env.example`:
```env
# Chế độ Groq API (Development)
GROQ_API_KEY=gsk_your_groq_api_key_here

# Hoặc chế độ Local LLM (Testing / Production)
# LLM_BASE_URL=http://localhost:11434/v1
# LLM_MODEL_NAME=qwen3.5:4b
```

---

## 4. Checklist bàn giao của Dev 4

- [ ] Tạo file mẫu cấu hình `.env.example` hướng dẫn cho team.
- [ ] Xác minh tệp `.env` nằm trong danh sách bỏ qua của `.gitignore`.
- [ ] Test thử kết nối Groq API thành công khi khai báo API Key.
- [ ] Test thử kết nối local server (Ollama/vLLM) thành công khi khai báo biến `LLM_BASE_URL`.
- [ ] Đặt cấu hình `temperature=0.1` hoặc thấp hơn để đảm bảo đáp án trắc nghiệm đầu ra mang tính nhất quán, không bị sinh ngẫu nhiên.
