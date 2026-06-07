from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent

import sys
import io

# Cấu hình encoding UTF-8 cho Windows console để tránh UnicodeEncodeError
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


# Thêm thư mục gốc của project vào sys.path để Python tìm thấy package 'src'
sys.path.append(str(BASE_DIR))

from src.rag_engine import ingest_document, search_rag_database
from src.agent_graph import app_graph


def test_rag_and_agent():
    print("\n=== BAT DAU KIEM THU TICH HOP: RAG + AGENT ===")
    
    # 1. Tạo mock data sạch sẽ
    mock_file = BASE_DIR / "data" / "mock_knowledge.txt"
    mock_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(mock_file, "w", encoding="utf-8") as f:
        f.write(
            "Thông tin cuộc thi HackAIthon 2026: Cuộc thi có 3 bảng đấu. "
            "Đối với Bảng C (Innovator), các đội sẽ xây dựng AI Agent có khả năng tự luận logic. "
            "Cơ cấu giải thưởng của Bảng C vô cùng hấp dẫn. Giải thưởng Bảng C HackAIthon gồm 20 triệu VNĐ cho đội xuất sắc đạt giải Nhất. "
            "Giải Nhì nhận được 15 triệu VNĐ và Giải Ba là 10 triệu VNĐ."
        )
            
    # 2. Nạp dữ liệu vào ChromaDB
    print("\n>> 1. Dang nap du lieu vao RAG...")
    ingest_document(str(mock_file))
    
    # 3. Chạy thử nghiệm truy vấn trực tiếp từ RAG (RAG Search test)
    print("\n>> 2. Dang test truy van truc tiep tu RAG...")
    test_query = "Giải thưởng cho đội đạt giải Nhất bảng C là bao nhiêu?"
    rag_result = search_rag_database.invoke({"query": test_query})
    print(f"[CAU HOI RAG]: {test_query}")
    print(f"[KET QUA RAG]:\n{rag_result}")
    
    # 4. Chạy thử nghiệm toàn bộ Agent Graph (kết nối Agent + RAG + LLM)
    print("\n>> 3. Dang test luong Agent Graph (Agent goi RAG -> LLM)...")
    agent_input = {"question": "Giải thưởng giải Nhất bảng C cuộc thi HackAIthon 2026 là bao nhiêu?"}
    agent_result = app_graph.invoke(agent_input)
    print(f"[CAU HOI AGENT]: {agent_result.get('question')}")
    print(f"[SUY LUAN CO T]: {agent_result.get('reasoning')}")
    print(f"[DAP AN CHOT]: {agent_result.get('answer')}")
    
    print("\n=== KIEM THU HOAN TAT ===")

if __name__ == "__main__":
    test_rag_and_agent()
