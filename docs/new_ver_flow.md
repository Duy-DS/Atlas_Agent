# Work Flow ver 2 #

## Phân tích câu hỏi## 

Câu hỏi từ đánh vào 3 khả năng chính : 
+ retrieval: khả năng đọc hiểu của Agent
+ calculation : khả năng tính toán của agent 
+ Confidence scoring: khả năng trả lời câu hỏi "knowledge" của agent 

Từ phân tích từ các câu hỏi đã được đưa ra ta sẽ thiết kế work flow pipeline riêng biệt xử lý cho 3 phần trên. 

## Phase ## 

### Phase 1: clasification type ###

Ở phase này ta cần phân loại các câu hỏi đầu vào là thuộc phần nào trong 3 phần đã phân tích ở câu hỏi để  có thể đưa vào pipeline chuyên biệt để  để xử lý. 

Dùng: 
+ regex  
+ heuristic scoring 

**Rule detect retrieval**

câu hỏi phần này thường sẽ có dạng sau: 

```
"Đoạn thông tin:..... Tổng quan(nội dung)/n....... câu hỏi/n" 
```
từ đây ta có thể thấy signal cực mạnh để phân loại vào phần 1. 

đó là khi thấy phần đầu của câu hỏi là `đoạn thông tin` thì sẽ đưa vào phần 1 (retrieval) 
```
if "Đoạn thông tin" in text and "Câu hỏi" in text: 
    task = 'retrieval' 
```

**Rule detect calculation** 

Dùng regex: 




