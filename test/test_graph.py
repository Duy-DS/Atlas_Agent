from src.agent_graph import app_graph

def test_graph():
    print("--- BẮT ĐẦU TEST ---")
    test_input = {"question": "Quy trình xử lý data lakehouse gồm những bước nào?"}
    result = app_graph.invoke(test_input)
    print(f"Đáp án: {result.get('answer')}")
    print(f"Lý do: {result.get('reasoning')}")

if __name__ == "__main__":
    test_graph()