import os
import csv
import asyncio
import time
from src.agent_graph import app_graph

async def process_dataset(input_file: str, output_file: str):
    print(f"Đang đọc dữ liệu từ: {input_file}")
    
    inputs = []
    qids = []
    
    # Đọc file csv, chú ý encoding utf-8-sig để bỏ BOM nếu có
    with open(input_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row.get("qid")
            q_text = row.get("question")
            opt_a = row.get("A", "")
            opt_b = row.get("B", "")
            opt_c = row.get("C", "")
            opt_d = row.get("D", "")
            
            # Đóng gói câu hỏi và các lựa chọn thành một đoạn text hoàn chỉnh
            full_question = (
                f"{q_text}\n"
                f"A. {opt_a}\n"
                f"B. {opt_b}\n"
                f"C. {opt_c}\n"
                f"D. {opt_d}"
            )
            qids.append(qid)
            inputs.append({"question": full_question})
            
    # Cấu hình giới hạn chạy thử nghiệm qua biến môi trường (Mặc định 0 = Chạy toàn bộ file)
    test_limit = int(os.getenv("TEST_LIMIT", "0"))
    if test_limit > 0:
        print(f"[TEST MODE] Chỉ chạy giới hạn {test_limit} câu hỏi đầu tiên.")
        inputs = inputs[:test_limit]
        qids = qids[:test_limit]
            
    # Đọc BATCH_SIZE từ biến môi trường (mặc định 20) để chia nhỏ tải chạy song song
    batch_size = int(os.getenv("BATCH_SIZE", "20"))
    if batch_size <= 0:
        batch_size = 20
        
    print(f"Tổng số câu hỏi sẽ xử lý (Test mode): {len(inputs)}")
    print(f"Đang xử lý bất đồng bộ theo từng batch (kích thước {batch_size}) qua LangGraph...")
    
    start_time = time.time()
    
    results = []
    for idx in range(0, len(inputs), batch_size):
        chunk_inputs = inputs[idx : idx + batch_size]
        print(f"[BATCH RUN] Đang xử lý câu hỏi từ {idx + 1} đến {min(idx + batch_size, len(inputs))}...")
        chunk_results = await app_graph.abatch(chunk_inputs)
        results.extend(chunk_results)
    
    end_time = time.time()
    print(f"Xử lý xong {len(inputs)} câu hỏi trong {end_time - start_time:.2f} giây.")
    
    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    # Ghi kết quả ra pred.csv
    print(f"Đang ghi kết quả ra: {output_file}")
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["qid", "answer"]) # Header theo format thông thường của các cuộc thi
        
        for qid, res in zip(qids, results):
            # Lấy đáp án dự đoán (mặc định hiện tại là B từ mock logic)
            ans = res.get("answer", "")
            writer.writerow([qid, ans])
            
    print("Hoàn tất luồng dữ liệu của Agent!")

import glob

def find_input_csv():
    # Quy định BTC: Đọc public_test.csv hoặc private_test.csv tại /data (khi chạy trong Docker)
    if os.path.exists("/data"):
        csv_files = glob.glob("/data/*.csv")
        if csv_files:
            # Ưu tiên lấy đúng tên file chuẩn của BTC nếu có
            for f in csv_files:
                if "private_test" in f or "public_test" in f:
                    return f
            return csv_files[0]
            
    # Fallback cho môi trường test local của Dev
    local_data = os.path.join(os.getcwd(), "data")
    if os.path.exists(local_data):
        csv_files = glob.glob(os.path.join(local_data, "*.csv"))
        if csv_files:
            return csv_files[0]
            
    return None

def get_output_csv():
    # Quy định BTC: Ghi pred.csv vào /output với hai cột qid, answer (A/B/C/D)
    if os.path.exists("/output"):
        return "/output/pred.csv"
    
    # Fallback cho local
    return os.path.join(os.getcwd(), "output", "pred.csv")

if __name__ == "__main__":
    INPUT_CSV = find_input_csv()
    OUTPUT_CSV = get_output_csv()
    
    if not INPUT_CSV:
        print("Lỗi: Không tìm thấy file CSV nào trong thư mục /data hoặc ./data")
    else:
        print(f"[CẤU HÌNH BẢNG C] - Input: {INPUT_CSV} | Output: {OUTPUT_CSV}")
        asyncio.run(process_dataset(INPUT_CSV, OUTPUT_CSV))
