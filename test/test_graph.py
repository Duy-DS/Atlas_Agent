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


def test_graph():
    print("--- BẮT ĐẦU TEST ---")
    test_input = {"question": "Quy trình xử lý data lakehouse gồm những bước nào?"}
    result = app_graph.invoke(test_input)
    print(f"Đáp án: {result.get('answer')}")
    print(f"Lý do: {result.get('reasoning')}")

if __name__ == "__main__":
    test_graph()