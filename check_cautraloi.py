import csv
import os

def evaluate_predictions(key_file, pred_file):
    if not os.path.exists(key_file):
        print(f"Không tìm thấy file đáp án: {key_file}")
        return
    if not os.path.exists(pred_file):
        print(f"Không tìm thấy file dự đoán: {pred_file}")
        return

    key_dict = {}
    with open(key_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key_dict[row['qid']] = row['answer']

    correct = 0
    total = 0
    
    with open(pred_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = row['qid']
            pred_ans = row['answer']
            if qid in key_dict:
                total += 1
                if key_dict[qid] == pred_ans:
                    correct += 1

    if total > 0:
        accuracy = correct / total
        print(f"Tổng số câu đã chấm: {total}")
        print(f"Số câu trả lời đúng: {correct}")
        print(f"Độ chính xác (Accuracy): {accuracy:.2%}")
    else:
        print("Không có câu hỏi nào được tìm thấy hoặc không khớp qid.")

if __name__ == "__main__":
    key_path = 'data/mock_answer_key.csv'
    pred_path = 'output/pred.csv'
    evaluate_predictions(key_path, pred_path)
