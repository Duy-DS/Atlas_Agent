# 🏗️ SYSTEM ARCHITECTURE & REFACTOR PLAN: PIVOT TO PURE REASONING

## 1. PHÂN TÍCH & VẼ LẠI CẤU TRÚC LOGIC

Dựa trên việc quét toàn bộ nhánh `feature/docker`, dưới đây là bức tranh tổng thể về kiến trúc hệ thống.

### 1.1 Vai trò của từng thành phần
- **Infrastructure (Hạ tầng):**
  - `Dockerfile`, `docker-compose.yml`, `docker-compose.gpu.yml`: Chịu trách nhiệm đóng gói ứng dụng. Đặc biệt `Dockerfile` có bước pre-bake trọng số mô hình `qwen3.5:4b` từ Ollama vào thẳng image để có thể chạy offline 100%.
  - `entrypoints.sh`: Kịch bản khởi động, đảm bảo Ollama server chạy nền trước khi kích hoạt Python app.

- **Configuration (Cấu hình):**
  - `.env` & `.env.example`: Lưu trữ các biến môi trường cấu hình luồng như `MODEL_NAME`, `BATCH_SIZE`, `LLM_CONCURRENCY_LIMIT` và đường dẫn file CSV.
  - `requirements.txt`: Chứa các thư viện phụ thuộc (cần được dọn dẹp các thư viện RAG thừa).

- **Data I/O (Luồng dữ liệu Vào/Ra):**
  - `main.py`: Đóng vai trò là Orchestrator ở lớp ngoài. Chịu trách nhiệm định vị file `public_test.csv` trong thư mục `/data`, đọc file, ghép câu hỏi và 4 đáp án (A, B, C, D) thành chuỗi văn bản.
  - Xử lý chia lô (batching) theo cấu hình `BATCH_SIZE`, gọi LangGraph qua `app_graph.abatch` (bất đồng bộ) và ghi kết quả ra `/output/pred.csv`. Xử lý lỗi an toàn (fallback thành "B" nếu có Exception).

- **Core Agent (Lõi suy luận AI):**
  - `src/agent_graph.py`: Chứa LangGraph workflow. Thiết lập các node (Retrieve, Router, WebSearch, WikiSearch, PythonREPL, Reason) và quản lý luồng điều hướng (Conditional Edges). Quản lý Semaphore để giới hạn luồng gọi API LLM (`concurrency_limit`).
  - `src/system_prompt.py`: Chứa System Prompt định hình tư duy Chain-of-Thought (CoT) và ép định dạng JSON.

### 1.2 Luồng xử lý dữ liệu (End-to-End Data Flow)
1. **Khởi chạy:** Môi trường Docker kích hoạt `main.py`.
2. **Nạp dữ liệu:** `main.py` đọc `/data/public_test.csv` và chuyển đổi mỗi hàng thành biến `question` chứa toàn bộ nội dung.
3. **Phân lô (Batching):** Các câu hỏi được nhóm lại theo `BATCH_SIZE` và đẩy vào LangGraph (`agent_graph.py`).
4. **LangGraph Execution:**
   - **Node Retrieve:** Đọc nội dung file `mock_knowledge.txt` để làm ngữ cảnh (Đang là placeholder).
   - **Node Router:** LLM phân tích câu hỏi để quyết định đi theo nhánh nào (`PYTHON`, `WIKI`, `WEB`, `NO`).
   - **Tool Nodes (Optional):** Nếu nhánh không phải `NO`, gọi công cụ tương ứng để lấy thêm thông tin ghép vào `context`.
   - **Node Reason:** Nhận `question` và `context` kết hợp với `SYSTEM_COT_PROMPT`. Trả về đối tượng JSON gồm `reasoning` và `answer`.
5. **Trích xuất JSON:** Hệ thống dùng Regex trong `agent_graph.py` để bóc tách JSON text từ LLM.
6. **Lưu trữ:** `main.py` nhận kết quả, thu thập đáp án và ghi ra `/output/pred.csv`.

---

## 2. KẾ HOẠCH TÁI CẤU TRÚC (ACTION PLAN TO PURE REASONING)

### Cảnh báo & Đánh giá rủi ro
> [!WARNING]
> Việc chuyển sang Pure Reasoning phụ thuộc hoàn toàn vào độ thông minh của LLM và Prompt. Do đó, Few-shot Prompting là **bắt buộc** để mô hình nhỏ (như Qwen 4B) không bị ảo giác và tuân thủ định dạng. 
> Việc bóc tách bằng Regex như hiện nay rủi ro rất cao nếu LLM sinh ra text không lường trước.

### 2.1 Xóa bỏ tàn dư RAG (Code Cleanup)
Mặc dù file `src/rag_engine_v1.py` đã không còn trong nhánh, nhưng cấu trúc của nó vẫn nằm rải rác:
- **`requirements.txt`:** 
  - [DELETE] Xóa bỏ `chromadb`, `sentence-transformers`, `transformers`, `tokenizers`.
- **`src/agent_graph.py`:** 
  - [DELETE] Xóa đoạn code đọc file `mock_knowledge.txt` (dòng 98-104).
  - [DELETE] Xóa hàm `retrieve_node` (dòng 192-194).
  - [MODIFY] Thay đổi Entry Point của workflow: 
    - Xóa `workflow.add_node("Retrieve", retrieve_node)`
    - Đổi `workflow.set_entry_point("Retrieve")` thành `workflow.set_entry_point("Router")`.
    - Xóa `workflow.add_edge("Retrieve", "Router")`.

### 2.2 Cập nhật Prompting (Few-Shot Injection)
- **`src/system_prompt.py`:**
  - [MODIFY] Chèn thêm khối ví dụ (Few-shot) để hướng dẫn LLM cách suy luận step-by-step. Cấu trúc đề xuất:
    ```python
    SYSTEM_COT_PROMPT = """...
    [Giữ nguyên quy tắc hiện tại]...

    ### VÍ DỤ MINH HOẠ (FEW-SHOT EXAMPLES) ###
    User: Thủ đô của Pháp là gì?
    A. London
    B. Paris
    C. Berlin
    D. Rome
    
    Assistant:
    {
        "reasoning": "Thủ đô của nước Pháp là Paris. London là của Anh, Berlin của Đức, Rome của Ý.",
        "answer": "B"
    }
    """
    ```

### 2.3 Nâng cấp Cơ chế Structured Output
Thay vì dùng `re.search` bất ổn định, ta sẽ chuyển sang tính năng Structured Output chuẩn của Langchain cùng với Pydantic.
- **`requirements.txt`:**
  - [NEW] Bổ sung thư viện `pydantic`.
- **`src/agent_graph.py`:**
  - [MODIFY] Định nghĩa Pydantic models ở đầu file:
    ```python
    from pydantic import BaseModel, Field
    
    class RouterOutput(BaseModel):
        route: str = Field(description="PYTHON, WIKI, WEB, or NO")
        search_query: str = Field(description="Search keyword")
        
    class ReasoningOutput(BaseModel):
        reasoning: str = Field(description="Detailed analysis")
        dap_an: str = Field(description="Must be A, B, C, or D")
    ```
  - [MODIFY] Trong `router_node` và `reasoning_node`, sử dụng `.with_structured_output()` thay cho `re.search`:
    ```python
    # Thay thế cho reasoning_node
    structured_llm = llm.with_structured_output(ReasoningOutput)
    response = await structured_llm.ainvoke([system_msg, human_msg])
    # Tự động parse thành response.reasoning và response.dap_an
    ```
  - Lưu ý: Cần cập nhật cả `main.py` nếu thay đổi key dictionary trả về (vd: từ `answer` sang `dap_an`).

## Open Questions cho User
> [!IMPORTANT]
> 1. Bạn muốn tôi tiến hành thực thi toàn bộ Kế hoạch Tái cấu trúc này ngay bây giờ hay muốn điều chỉnh/bỏ qua phần nào không?
> 2. Có cần chuyển trường `answer` thành `dap_an` như trong yêu cầu ở báo cáo trước không? Nếu đổi thì tôi sẽ cập nhật luôn cả `main.py` để tương thích.

