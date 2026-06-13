# Hướng dẫn tích hợp và thử nghiệm Agent bằng Giao diện Streamlit (Local UI Testing)

Tài liệu này hướng dẫn cách kết nối và chạy thử nghiệm **Multi-Tool Agent** hiện tại với giao diện **Streamlit UI** có sẵn trên máy của bạn để test tương tác trực quan (không dùng để nộp bài chấm điểm).

> [!WARNING]
> **Quy tắc làm việc của Team:** Hướng dẫn này chỉ phục vụ mục đích test giao diện cục bộ (Local UI Test). Không commit phần code giao diện (Streamlit) hoặc đẩy các thay đổi này lên nhánh `dev` để tránh làm nặng Docker image nộp bài của BTC.

---

## 1. Chuẩn bị môi trường

1. **Cập nhật mã nguồn mới nhất:**
   Kéo code mới nhất từ nhánh `dev` về máy của bạn:
   ```bash
   git checkout dev
   git pull origin dev
   ```

2. **Cài đặt thư viện Streamlit:**
   Đảm bảo môi trường ảo của bạn đã được cài đặt thêm `streamlit`:
   ```bash
   pip install streamlit
   ```

3. **Cấu hình API Key:**
   Đảm bảo tệp `.env` ở thư mục gốc đã cấu hình đúng `GROQ_API_KEY` hoặc endpoint Local LLM của bạn để Agent có thể gọi mô hình suy luận.

---

## 2. Hướng dẫn tích hợp Agent vào Streamlit

Do đồ thị Agent hiện tại (`app_graph`) sử dụng các Node bất đồng bộ (**Async**), trong khi luồng chạy của Streamlit là đồng bộ (**Sync**), bạn cần sử dụng một hàm bọc (wrapper) để chạy Agent bằng `asyncio`.

Dưới đây là đoạn code mẫu tích hợp Agent vào file giao diện Streamlit (ví dụ: `app.py` hoặc `ui.py` của bạn):

```python
import streamlit as st
import asyncio
import sys
from pathlib import Path

# Đảm bảo Python nhận diện đúng thư mục src
sys.path.append(str(Path(__file__).resolve().parent))

# Import đồ thị Agent từ thư mục src
from src.agent_graph import app_graph

# Thiết lập tiêu đề giao diện
st.title("🤖 Atlas Multi-Tool Agent - Demo UI")
st.write("Giao diện kiểm thử cục bộ các công cụ: PythonREPL, Wikipedia, Web Search.")

# Hàm helper chạy luồng async trong môi trường sync của Streamlit
def run_agent_sync(question_text: str):
    try:
        # Khởi tạo event loop mới để tránh xung đột với Streamlit thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Gọi ainvoke để chạy đồ thị Agent bất đồng bộ
        result = loop.run_until_complete(
            app_graph.ainvoke({"question": question_text})
        )
        loop.close()
        return result
    except Exception as e:
        st.error(f"Lỗi khi chạy Agent: {e}")
        return None

# Giao diện người dùng
user_query = st.text_area("Nhập câu hỏi trắc nghiệm của bạn ở đây:", height=150, placeholder="Ví dụ:\nĐội tuyển nào vô địch Euro 2024?\nA. Pháp\nB. Anh\nC. Tây Ban Nha\nD. Ý")

if st.button("Gửi Agent xử lý"):
    if user_query.strip() == "":
        st.warning("Vui lòng nhập câu hỏi trước khi gửi.")
    else:
        with st.spinner("Agent đang suy luận và gọi công cụ hỗ trợ..."):
            # Chạy agent và nhận kết quả state
            state_result = run_agent_sync(user_query)
            
            if state_result:
                st.success("Xử lý hoàn tất!")
                
                # Hiển thị đáp án trắc nghiệm dự đoán (A/B/C/D)
                answer = state_result.get("answer", "N/A")
                st.metric(label="Đáp án dự đoán của Agent", value=answer)
                
                # Hiển thị chi tiết lập luận Chain-of-Thought
                st.subheader("🧠 Chuỗi suy luận (Reasoning Log):")
                st.info(state_result.get("reasoning", "Không có log suy luận."))
                
                # Hiển thị context đã tích lũy (nếu có từ Web/Wiki/Python)
                st.subheader("📚 Ngữ cảnh tích lũy từ công cụ:")
                st.code(state_result.get("context", "Trống"))
```

---

## 3. Khởi chạy thử nghiệm

Chạy ứng dụng Streamlit từ thư mục gốc của dự án:

```bash
# Windows (Tránh lỗi unicode font tiếng Việt)
$env:PYTHONUTF8=1; streamlit run app.py

# Linux / macOS
streamlit run app.py
```

Trình duyệt sẽ tự động mở trang thử nghiệm tại `http://localhost:8501`. Tại đây bạn có thể nhập các câu hỏi trắc nghiệm thực tế để kiểm tra khả năng Router phân loại sang các nhánh công cụ và bóc tách đáp án của mô hình.

---

## 4. Lưu ý khi làm việc nhóm

- **Không commit file giao diện Streamlit** (ví dụ `app.py`) lên nhánh `dev` nếu nó không thuộc file cần nộp cho BTC.
- Bạn nên thêm file UI test của mình vào `.gitignore` của local nếu muốn giữ lại chạy lâu dài mà không sợ vô tình commit lên Git:
  ```text
  # Thêm vào cuối file .gitignore (nếu cần)
  app.py
  ui.py
  ```
