import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.agent_graph import app_graph

CONCURRENCY_LIMIT = 5

def process_row(index_and_row):
    index, row = index_and_row
    
    question_text = row.get("question", "")
    opt_a = row.get("A", "")
    opt_b = row.get("B", "")
    opt_c = row.get("C", "")
    opt_d = row.get("D", "")

    full_question = (
        f"{question_text}\n"
        f"A. {opt_a}\n"
        f"B. {opt_b}\n"
        f"C. {opt_c}\n"
        f"D. {opt_d}"
    )

    state = {
        "question": full_question,
        "context": ""
    }

    try:
        # Gọi luồng chạy đồ thị LangGraph đã refactor
        result_state = app_graph.invoke(state)
        
        # Trích xuất trường reasoning và answer sạch
        reasoning = result_state.get("reasoning", "")
        answer = result_state.get("answer", "")
    except Exception as e:
        reasoning = f"Lỗi hệ thống: {e}"
        answer = "B" # Fallback an toàn

    # Đảm bảo output đáp án hợp lệ
    reasoning = str(reasoning).strip()
    answer = str(answer).strip().upper()
    if answer not in ["A", "B", "C", "D"]:
        answer = "B"

    # Hỗ trợ tên cột id hoặc qid
    qid = row.get("id") if pd.notna(row.get("id")) else row.get("qid")
    if pd.isna(qid):
        qid = index

    return index, qid, reasoning, answer

def main():
    # Cấu hình đường dẫn I/O chuẩn Thể lệ
    input_file = os.getenv("INPUT_CSV", "data/public_test.csv")
    output_file = os.getenv("OUTPUT_CSV", "output/pred.csv")

    if not os.path.exists(input_file):
        print(f"[!] LỖI TÍNH MẠNG: Không tìm thấy file dữ liệu tại {input_file}")
        return

    print(f"[*] Bắt đầu nạp dữ liệu từ: {input_file}")
    df = pd.read_csv(input_file)
    
    total_rows = len(df)
    print(f"[*] Tổng số câu hỏi cần xử lý: {total_rows}")
    print(f"[*] ⚡ Kích hoạt Đa luồng song song (ThreadPoolExecutor) với MAX_WORKERS = {CONCURRENCY_LIMIT}")

    results = []
    # Gán kèm chỉ số index gốc của từng dòng
    rows_data = list(df.iterrows())

    # Bắn đồng thời 5 requests suy luận vào LangGraph Agent
    with ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT) as executor:
        futures = {executor.submit(process_row, item): item for item in rows_data}
        
        # Hiển thị thanh tiến trình trực quan
        with tqdm(total=total_rows, desc="Đang suy luận", unit=" câu") as pbar:
            for future in as_completed(futures):
                index, qid, reasoning, answer = future.result()
                results.append({
                    "index": index,
                    "id": qid,
                    "reasoning": reasoning,
                    "answer": answer
                })
                pbar.update(1)

    # [CRITICAL] Sắp xếp lại (Sort) theo đúng index ban đầu để BẢO TOÀN THỨ TỰ
    print("\n[*] Sắp xếp lại kết quả theo thứ tự gốc (Row Order Preservation)...")
    results.sort(key=lambda x: x["index"])

    # Xuất đúng cấu trúc DataFrame
    output_df = pd.DataFrame(results)
    if "index" in output_df.columns:
        output_df.drop(columns=["index"], inplace=True)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    print(f"[*] Xuất file kết quả CSV cuối cùng: {output_file}")
    output_df.to_csv(output_file, index=False)
    
    print("[+] THÀNH CÔNG! Giai đoạn 4: Đa Luồng Tăng Tốc đã hoàn tất.")

if __name__ == "__main__":
    main()
