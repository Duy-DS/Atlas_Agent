• Hiện tại confidence trong repo không phải confidence thật từ model. Nó là
  heuristic tự đặt trong main.py, function confidence_for():

  def confidence_for(row, answer):
      if answer == "N/A":
          return "0.00"
      if should_search(row, answer):
          return "0.40"
      return "0.90"

  Nghĩa là:

  - N/A → 0.00
  - câu bị router đánh là cần web search → 0.40
  - còn lại → 0.90

  Cách này đơn giản, nhưng không đo được model chắc hay không. Nó chỉ phản ánh
  rule của pipeline.

  Các cách tốt hơn, theo mức độ thực tế:

  1. Heuristic theo pipeline
     Dễ nhất, nhanh nhất.
     Ví dụ:
      - batch trả hợp lệ ngay → 0.70
      - domain retry đổi đáp án → 0.60
      - domain retry giữ nguyên đáp án → 0.80
      - web search có source và đổi đáp án → 0.75
      - answer N/A → 0.00

  2. Self-consistency
     Gọi model 2-3 lần cùng câu, nếu cùng chọn một đáp án thì confidence cao.
     Chính xác hơn, nhưng chậm hơn nhiều.

  3. Ask model tự chấm confidence
     Prompt model trả thêm confidence.
     Không đáng tin lắm, vì model thường tự tin sai.

  4. Logprob/token probability
     Nếu backend model trả logprobs cho đáp án A/B/C/D thì đây là cách tốt hơn.
     Nhưng với ollama.chat hiện tại thường không có logprob chuẩn dễ dùng.

  5. Verifier pass
     Sau khi có đáp án, gọi một prompt verifier hỏi “đáp án này có thỏa đề
     không?”.
     Tốt cho toán/logic, nhưng thêm latency.

  Tôi khuyên với repo này dùng cách 1 trước: confidence theo pipeline events, vì
  nhanh và dễ debug. Muốn làm chính xác hơn cho toán thì thêm verifier riêng cho
  domain retry, không nên áp dụng toàn bộ câu hỏi ngay