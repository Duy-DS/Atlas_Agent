import asyncio
import time
from src.agent_graph import app_graph

async def main():
    questions = [
        "Câu hỏi 1: AI Agent là gì?",
        "Câu hỏi 2: Giải thưởng bảng C là bao nhiêu?",
        "Câu hỏi 3: Data Lakehouse có mấy lớp?",
        "Câu hỏi 4: RAG hoạt động như thế nào?",
        "Câu hỏi 5: Llama 3.3 có bao nhiêu tham số?",
        "Câu hỏi 6: ChromaDB dùng để làm gì?",
        "Câu hỏi 7: Embedding là gì?",
        "Câu hỏi 8: LangChain khác LangGraph ở điểm nào?",
        "Câu hỏi 9: Asyncio trong Python dùng để làm gì?",
        "Câu hỏi 10: Docker có thể chạy GPU không?",
    ]

    print(f"Bắt đầu xử lý {len(questions)} câu hỏi...")
    start_time = time.time()

    # Tạo danh sách các state đầu vào
    inputs = [{"question": q} for q in questions]

    # Sử dụng abatch của LangGraph để xử lý đồng thời (parallel)
    # langgraph.abatch() trả về danh sách các kết quả tương ứng với inputs
    results = await app_graph.abatch(inputs)

    end_time = time.time()

    print("\nKết quả:")
    for i, res in enumerate(results):
        # res là output của node cuối cùng hoặc toàn bộ state tùy cấu hình
        # Với StateGraph mặc định, nó trả về state cuối cùng
        print(f"Q{i+1}: {res.get('question')}")
        print(f"A: {res.get('answer')} | Lập luận: {res.get('reasoning')}")
        print("-" * 50)

    print(f"\nTổng thời gian xử lý {len(questions)} câu: {end_time - start_time:.2f} giây")
    # Với 10 câu, mỗi câu sleep 0.5s. Nếu chạy tuần tự (như mây hiện tại), mất ~5s. 
    # Nhưng chạy abatch (async), tổng thời gian chỉ mất ~0.5s - 0.6s.

if __name__ == "__main__":
    asyncio.run(main())
