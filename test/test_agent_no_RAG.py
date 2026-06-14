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

from src.agent_graph import app_graph

def test_agent_no_rag():
    print("\n=== BAT DAU KIEM THU AGENT KHONG CAN RAG ===")
    
    # Thiết lập câu hỏi trắc nghiệm không cần RAG
    test_question = (
        "Câu hỏi: 1 + 1 bằng bao nhiêu?\n"
        "A. 1\n"
        "B. 2\n"
        "C. 3\n"
        "D. 4"
    )
    
    print(f"\n[CAU HOI THU NGHIEM]:\n{test_question}\n")
    print(">> Dang chay luong Agent Graph (Truy van -> Lap luan)...")
    
    # Chạy Agent Graph
    agent_input = {"question": test_question}
    result = app_graph.invoke(agent_input)
    
    print("\n=== KET QUA TU AGENT ===")
    print(f"[SUY LUAN CO T]:\n{result.get('reasoning')}\n")
    print(f"[DAP AN DUOC CHON]: {result.get('answer')}")
    print("=========================")

if __name__ == "__main__":
    test_agent_no_rag()
