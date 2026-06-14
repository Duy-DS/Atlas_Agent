# EXPLAIN DEV 5 - QA, UI TESTER & TECHNICAL WRITER (Atlas Agent)

## 1. Mục tiêu vai trò Dev 5

**Dev 5** chịu trách nhiệm về mặt kiểm định chất lượng phần mềm (QA), thiết kế giao diện thử nghiệm tương tác (UI Tester) và viết tài liệu thuyết minh phương pháp kỹ thuật (Technical Writer).

Mục tiêu cốt lõi:
- Xây dựng bộ dữ liệu kiểm thử (Mock Test Dataset) đa dạng để đánh giá hiệu năng của Agent.
- Cung cấp giao diện trực quan (Streamlit) để chạy test Agent tương tác thực tế.
- Viết tài liệu thuyết minh kỹ thuật chi tiết làm nổi bật lập luận logic của Agent, đảm bảo tuân thủ nguyên tắc không sử dụng thủ thuật học vẹt.

---

## 2. Các nhiệm vụ chi tiết (Bản đồ nhiệm vụ từ Task List)

### Task 5.1: Xây dựng Dữ liệu Kiểm thử (Mock Dataset)
* **Mô tả:** Tạo file dữ liệu trắc nghiệm mô phỏng [data/mock_public_test.csv](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/data/mock_public_test.csv).
* **Trạng thái:** **Hoàn thành 100%**.
* **Chi tiết:** File mock chứa các câu hỏi trắc nghiệm đa lĩnh vực (toán, lịch sử, tin tức) kèm theo các tùy chọn A, B, C, D để thử nghiệm khả năng phân loại của Router Node và khả năng suy luận của Reason Node.

### Task 5.2: Dựng Web UI Test Local
* **Mô tả:** Tạo giao diện Streamlit/Gradio trực quan để theo dõi trực tiếp luồng log suy luận của Agent thay vì xem terminal thô.
* **Trạng thái:** **Hoàn thành 100%**.
* **Chi tiết:** Dev 5 đã thiết kế giao diện Streamlit và viết tài liệu hướng dẫn tích hợp chi tiết tại [docs/ui_testing_guide.md](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/docs/ui_testing_guide.md). Giải pháp này cho phép thành viên khác kéo code về và chạy thử nghiệm giao diện local một cách an toàn mà không cần push code UI lên nhánh nộp bài Docker của BTC.

### Task 5.3: Soạn Thuyết Minh Phương Pháp
* **Mô tả:** Viết file thuyết minh thuật toán và kiến trúc hệ thống để nộp cho BTC.
* **Trạng thái:** **Hoàn thành 100%**.
* **Chi tiết:** Hoàn thiện toàn bộ các file tài liệu thuyết minh trong thư mục `/docs` (từ `explain_dev1.md` đến `explain_dev5.md` và `explain_agent_architecture.md`). Các tài liệu này chứng minh hệ thống sử dụng kiến trúc đồ thị trạng thái LangGraph kết hợp chuỗi suy luận Chain-of-Thought (CoT), hoàn toàn không sử dụng hard-code hoặc các thủ thuật lách test case học vẹt.

---

## 3. Checklist của Dev 5

- [ ] File dữ liệu mock [data/mock_public_test.csv](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/Atlas_Agent/data/mock_public_test.csv) có đầy đủ các cột chuẩn theo quy định của BTC.
- [ ] Tài liệu hướng dẫn UI Test hoạt động đúng với phiên bản đồ thị Agent bất đồng bộ hiện tại.
- [ ] Các tài liệu thuyết minh kiến trúc phản ánh chính xác cấu trúc code trong file `src/agent_graph.py` và `main.py`.
