FROM ollama/ollama:latest

# Thiết lập các biến môi trường cho Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

# Cài đặt Python, pip, venv và curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Tạo và sử dụng Python Virtual Environment để cô lập thư viện
RUN python3 -m venv /opt/venv

# Sao chép và cài đặt các thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Đóng gói trước (pre-bake) trọng số mô hình LLM vào trong Docker Image
# Điều này đảm bảo container chạy offline 100% không cần tải lại model từ internet
RUN ollama serve > /var/log/ollama_build.log 2>&1 & \
    until curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do sleep 1; done && \
    ollama pull qwen3.5:4b

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Phân quyền cho file chạy chính
RUN chmod +x /app/entrypoints.sh

ENTRYPOINT ["/app/entrypoints.sh"]
