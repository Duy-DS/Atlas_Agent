# Giải thích công việc Dev 5 - QA & Technical Writer

## 1. Bối cảnh dự án

Dự án của nhóm có tên là **Atlas Agent**, tham gia cuộc thi **Vietnamese Student HackAIthon 2026**.

Mô tả ngắn gọn của dự án:

> Atlas Agent là AI Agent được thiết kế từ mô hình ngôn ngữ lớn để xử lý đa tác vụ.

Trong nhóm, vai trò của Dev 5 không tập trung chính vào xây dựng model lõi hay pipeline AI phức tạp ngay từ đầu, mà đảm nhận phần **QA & Technical Writer**. Đây là vai trò hỗ trợ kỹ thuật, kiểm thử, tài liệu hóa và giúp sản phẩm của nhóm rõ ràng, dễ chạy, dễ kiểm tra, dễ trình bày hơn.

Nói ngắn gọn: nếu dev khác xây hệ thống, Dev 5 là người đảm bảo hệ thống đó **chạy được, test được, hiểu được, trình bày được**. Một vai trò nghe có vẻ phụ, nhưng thiếu nó thì repo sẽ biến thành cái hang động có code, và ban giám khảo không phải nhà khảo cổ.

---

## 2. Vai trò chính của Dev 5

Dev 5 đảm nhận vai trò:

**QA & Technical Writer**

Vai trò này gồm hai mảng lớn:

1. **QA - Quality Assurance**  
   Kiểm thử, rà soát, tạo dữ liệu test, kiểm tra output, phát hiện lỗi, đảm bảo sản phẩm chạy đúng yêu cầu.

2. **Technical Writer**  
   Viết tài liệu kỹ thuật, README, hướng dẫn setup, hướng dẫn chạy project, giải thích luồng hoạt động, mô tả công việc các thành viên và tài liệu phục vụ demo.

---

## 3. Mục tiêu công việc của Dev 5

Công việc của Dev 5 hướng tới các mục tiêu sau:

- Giúp project có tài liệu rõ ràng, người khác đọc vào hiểu ngay dự án làm gì.
- Giúp thành viên nhóm biết cách setup và chạy project local.
- Giúp ban giám khảo hoặc người review repo hiểu được kiến trúc, cách dùng và kết quả đầu ra.
- Tạo dữ liệu test để kiểm tra pipeline AI trước khi có dữ liệu thật từ ban tổ chức.
- Kiểm tra định dạng input/output có đúng yêu cầu cuộc thi hay không.
- Làm UI test local để nhóm dễ quan sát quá trình chạy thay vì chỉ nhìn terminal.
- Hỗ trợ chuẩn hóa repo để sản phẩm nhìn chuyên nghiệp hơn.

---

## 4. Các nhóm công việc cụ thể

## 4.1. Viết README cho toàn bộ dự án

Một trong các nhiệm vụ quan trọng là tạo README cho repo GitHub của dự án **Atlas Agent**.

README cần giải thích được:

- Tên dự án.
- Mô tả ngắn gọn dự án.
- Cuộc thi tham gia.
- Thành viên nhóm.
- Vai trò từng thành viên.
- Công nghệ sử dụng.
- Cấu trúc thư mục.
- Cách setup môi trường.
- Cách chạy project.
- Cách chạy bằng Docker nếu có.
- Cách input dữ liệu.
- Cách output kết quả.
- Cách đánh giá kết quả.

README không chỉ là file trang trí cho GitHub. Nó là tài liệu đầu tiên người khác nhìn vào để đánh giá nhóm có làm việc nghiêm túc hay chỉ ném code lên repo rồi cầu nguyện.

### Thành viên nhóm

| Vị trí | Thành viên |
|---|---|
| Dev 1 | Thành |
| Dev 2 | Vỹ |
| Dev 3 | Duy |
| Dev 4 | Trí |
| Dev 5 | Đức |

Dev 5 cần viết phần mô tả công việc của các thành viên theo dạng sườn, để sau đó nhóm có thể điền chi tiết.

---

## 4.2. Làm tài liệu setup môi trường

Dev 5 cần viết hướng dẫn để người khác có thể chạy project local.

Các phần cần có trong tài liệu setup:

- Yêu cầu hệ thống.
- Phiên bản Python nếu có.
- Cách clone repo.
- Cách tạo môi trường ảo.
- Cách cài dependencies.
- Cách cấu hình file `.env` nếu project cần.
- Cách chạy từng service.
- Cách chạy bằng Docker.
- Cách kiểm tra project đã chạy thành công.

Một điểm đã được làm rõ trong các đoạn chat trước: nếu project dùng Docker đúng cách, về lý thuyết chỉ cần chạy Docker Compose là các service chính sẽ được khởi động cùng nhau. Tuy nhiên, README vẫn cần giải thích rõ:

- Docker chạy những service nào.
- Service nào phụ thuộc service nào.
- Port nào được mở.
- Output nằm ở đâu.
- Khi lỗi thì kiểm tra log thế nào.

Không thể chỉ ghi “chạy Docker là được”. Câu đó đúng kiểu kỹ thuật viên mệt mỏi viết tài liệu lúc 3 giờ sáng, nhưng không đủ cho repo thi hackathon.

---

## 4.3. Kiểm tra định dạng input/output của cuộc thi

Dev 5 cần nắm rõ yêu cầu định dạng dữ liệu của ban tổ chức.

Theo thông tin đã tổng hợp:

- Ban tổ chức cung cấp file `public_test.csv` hoặc `private_test.csv` tại thư mục `/data`.
- Hệ thống cần đọc file input từ `/data`.
- Hệ thống cần ghi file kết quả `pred.csv` vào thư mục `/output`.
- File output bắt buộc có hai cột:
  - `qid`
  - `answer`
- Giá trị `answer` là một trong bốn lựa chọn:
  - `A`
  - `B`
  - `C`
  - `D`

Định dạng output chuẩn:

```csv
qid,answer
1,A
2,C
3,B
```

Đây là phần cực kỳ quan trọng. Model có thể thông minh đến mức biết pha cà phê bằng đạo hàm, nhưng nếu file output sai tên cột thì vẫn có thể bị chấm sai.

---

## 4.4. Tạo dữ liệu test giả lập

Dev 5 đã làm việc với yêu cầu tạo dữ liệu test giả lập để nhóm kiểm tra pipeline trước khi dùng test thật.

Các file/ý tưởng đã được nhắc tới:

- File mock test ban đầu khoảng **80 câu hỏi**.
- Chuyển file `mock_public_test.csv` thành file `.txt` nếu cần.
- Mở rộng lên khoảng **1500 câu hỏi đa lĩnh vực**.
- Các lĩnh vực mở rộng gồm:
  - Tài chính.
  - Y tế.
  - Công nghệ.
  - Giáo dục.
  - Khoa học.
  - Đời sống.
  - Xã hội.
  - Các lĩnh vực tổng quát khác.

Các nhóm câu hỏi nên có:

| Nhóm câu | Mục đích |
|---|---|
| Câu dễ, trả lời trực tiếp | Kiểm tra hệ thống xử lý câu đơn giản |
| Câu cần đọc hiểu/ngữ cảnh | Kiểm tra khả năng hiểu nội dung |
| Câu cần RAG | Kiểm tra khả năng truy xuất tri thức ngoài |
| Câu nhiễu/bẫy | Kiểm tra khả năng tránh chọn đáp án sai do nhiễu |
| Câu dài/edge case | Kiểm tra độ ổn định với input phức tạp |

Tuy nhiên, cần phân biệt rõ:

- File nộp cho ban tổ chức phải theo đúng format BTC yêu cầu.
- File metadata chỉ dùng nội bộ để phân tích, test, chia nhóm câu hỏi.

Metadata không cần giống format BTC nếu nó không phải file nộp. Nó dùng để nhóm hiểu câu nào khó, câu nào dễ, câu nào cần RAG, câu nào là edge case. Nói cách khác, metadata là bản đồ nội bộ, không phải hộ chiếu để đi qua cổng chấm điểm.

---

## 4.5. Task 5.2 - Dựng Web UI Test Local

Một nhiệm vụ cụ thể của Dev 5 là:

**Task 5.2: Dựng Web UI Test Local**

Yêu cầu:

> Viết file `src/app_ui.py` bằng Gradio hoặc Streamlit. Tạo UI hiển thị trực tiếp luồng log suy luận của AI để test trực quan thay vì nhìn terminal.

Thông tin đã thống nhất:

| Hạng mục | Quyết định hiện tại |
|---|---|
| Pipeline AI hiện tại | Chưa có |
| Input UI | Upload file |
| Format input | CSV |
| Log hiển thị | Basic log |
| Output | Xuất file `pred.csv` vào `/output` |
| Cột output | `qid`, `answer` |
| Giá trị answer | A/B/C/D |
| Model hiện tại | Mock trước |

Do pipeline AI thật chưa có, UI sẽ dùng **mock model** trước.

### Mục tiêu của Web UI Test Local

UI này giúp nhóm:

- Upload file CSV test.
- Xem dữ liệu đầu vào.
- Chạy mock inference.
- Hiển thị log quá trình xử lý.
- Tạo file `pred.csv` đúng format.
- Tải hoặc kiểm tra output sau khi chạy.
- Test giao diện và flow trước khi tích hợp pipeline AI thật.

### Vì sao cần Web UI Test Local?

Nếu chỉ nhìn terminal, việc demo và debug sẽ khó hơn. Web UI giúp nhóm nhìn trực quan hơn:

- Input đã đọc đúng chưa.
- Bao nhiêu câu đã được xử lý.
- Có lỗi dòng nào không.
- File output đã tạo chưa.
- Format có đúng không.

Đây là công việc có ảnh hưởng trực tiếp đến trải nghiệm test nội bộ và demo sản phẩm.

---

## 5. Ảnh hưởng của công việc Dev 5 tới sản phẩm

Công việc của Dev 5 ảnh hưởng đến sản phẩm ở nhiều lớp.

## 5.1. Ảnh hưởng tới chất lượng sản phẩm

Dev 5 giúp phát hiện lỗi trước khi nộp hoặc demo:

- Sai format file input.
- Sai tên cột output.
- Sai thư mục lưu kết quả.
- Thiếu file cần thiết.
- Hướng dẫn chạy không đúng.
- Docker chạy lỗi.
- UI không đọc được file.
- Pipeline không tạo được `pred.csv`.

Đây là các lỗi nhỏ nhưng có thể làm sản phẩm mất điểm nặng. Lỗi kiểu này không hào nhoáng, nhưng lại rất thực tế, đúng kiểu nhân loại hay thua vì quên dấu phẩy.

## 5.2. Ảnh hưởng tới khả năng demo

Một sản phẩm hackathon không chỉ cần chạy được, mà còn phải trình bày được.

Dev 5 hỗ trợ demo bằng cách:

- Viết README rõ ràng.
- Tạo UI test local.
- Chuẩn hóa dữ liệu test.
- Viết mô tả luồng xử lý.
- Giúp người chấm hiểu sản phẩm nhanh hơn.

Nếu demo tốt, sản phẩm dễ tạo ấn tượng hơn. Nếu demo rối, dù core tốt cũng có thể bị đánh giá thấp.

## 5.3. Ảnh hưởng tới làm việc nhóm

Tài liệu tốt giúp các thành viên khác:

- Biết chạy project thế nào.
- Biết input/output đang theo chuẩn nào.
- Biết mình cần đặt file ở đâu.
- Biết lỗi xảy ra ở bước nào.
- Giảm thời gian hỏi qua lại.

Technical Writer không chỉ viết chữ. Người này biến tri thức rải rác trong đầu từng dev thành tài liệu chung mà cả nhóm dùng được.

---

## 6. Công việc Dev 5 cần làm theo giai đoạn

## Giai đoạn 1 - Chuẩn hóa thông tin dự án

Cần hoàn thành:

- Ghi rõ tên dự án: **Atlas Agent**.
- Ghi rõ mô tả dự án.
- Ghi rõ tên cuộc thi.
- Ghi rõ thành viên nhóm.
- Ghi rõ vai trò từng thành viên.
- Tạo sườn README để nhóm bổ sung.

## Giai đoạn 2 - Chuẩn hóa dữ liệu test

Cần hoàn thành:

- Tạo file mock test nhỏ để kiểm thử nhanh.
- Mở rộng bộ câu hỏi test nếu cần.
- Đảm bảo test file có cột `qid`.
- Đảm bảo output sinh ra đúng `qid,answer`.
- Tách rõ file input chính và file metadata nội bộ.

## Giai đoạn 3 - Viết Web UI Test Local

Cần hoàn thành:

- Tạo file `src/app_ui.py`.
- Dùng Streamlit hoặc Gradio.
- Cho phép upload file CSV.
- Đọc danh sách câu hỏi.
- Chạy mock model.
- Hiển thị log cơ bản.
- Xuất file `/output/pred.csv`.
- Hiển thị bảng kết quả.

## Giai đoạn 4 - Viết tài liệu chạy project

Cần hoàn thành:

- Hướng dẫn chạy local.
- Hướng dẫn chạy Docker.
- Hướng dẫn cấu trúc thư mục.
- Hướng dẫn kiểm tra output.
- Hướng dẫn debug lỗi thường gặp.

## Giai đoạn 5 - Hỗ trợ kiểm thử và review trước khi nộp

Cần hoàn thành:

- Chạy thử project từ đầu theo README.
- Kiểm tra file output.
- Kiểm tra lỗi Docker.
- Kiểm tra UI.
- Kiểm tra đường dẫn `/data` và `/output`.
- Ghi lại lỗi và báo cho dev phụ trách sửa.

---

## 7. Checklist công việc Dev 5

## Checklist tài liệu

- [ ] Viết README tổng quan dự án.
- [ ] Viết mô tả thành viên và vai trò.
- [ ] Viết hướng dẫn setup môi trường.
- [ ] Viết hướng dẫn chạy project local.
- [ ] Viết hướng dẫn chạy bằng Docker.
- [ ] Viết hướng dẫn input/output.
- [ ] Viết phần troubleshooting lỗi thường gặp.

## Checklist QA

- [ ] Kiểm tra project có chạy theo README không.
- [ ] Kiểm tra Docker có chạy đủ service không.
- [ ] Kiểm tra file input CSV có đọc được không.
- [ ] Kiểm tra output có tên `pred.csv` không.
- [ ] Kiểm tra output có đúng hai cột `qid,answer` không.
- [ ] Kiểm tra answer chỉ gồm A/B/C/D.
- [ ] Kiểm tra đường dẫn `/data` và `/output`.
- [ ] Ghi nhận lỗi để nhóm sửa.

## Checklist Web UI Test Local

- [ ] Tạo file `src/app_ui.py`.
- [ ] Cho upload file CSV.
- [ ] Hiển thị preview dữ liệu.
- [ ] Chạy mock model.
- [ ] Hiển thị log xử lý.
- [ ] Xuất file `/output/pred.csv`.
- [ ] Hiển thị bảng kết quả.
- [ ] Kiểm tra UI hoạt động local.

## Checklist dữ liệu test

- [ ] Tạo mock dataset nhỏ.
- [ ] Tạo bộ câu hỏi mở rộng nếu cần.
- [ ] Phân loại câu hỏi theo nhóm khó/dễ/RAG/bẫy/edge case.
- [ ] Không dùng metadata làm file nộp chính.
- [ ] Đảm bảo file nộp giả lập giống format BTC.

---

## 8. Kết quả đầu ra Dev 5 cần bàn giao

Các file hoặc nội dung Dev 5 nên bàn giao gồm:

| File/Nội dung | Mục đích |
|---|---|
| `README.md` | Tài liệu chính của dự án |
| `src/app_ui.py` | Web UI test local |
| `mock_public_test.csv` | File test giả lập dạng CSV |
| `pred.csv` | File output mẫu |
| `question_metadata.csv` | Metadata nội bộ để phân loại câu hỏi |
| `explain_dev5.md` | Giải thích công việc Dev 5 |
| Tài liệu setup Docker | Hướng dẫn chạy toàn bộ project |
| Checklist QA | Danh sách kiểm thử trước khi nộp |

---

## 9. Tóm tắt ngắn gọn vai trò Dev 5

Dev 5 không chỉ “viết tài liệu”. Công việc thực tế gồm:

- Hiểu yêu cầu cuộc thi.
- Chuẩn hóa input/output.
- Tạo dữ liệu test.
- Kiểm thử flow chạy project.
- Viết README.
- Viết hướng dẫn setup.
- Làm UI test local.
- Ghi nhận lỗi.
- Giúp sản phẩm dễ demo và dễ review hơn.

Nếu ví project như một cỗ máy, các dev khác xây động cơ, còn Dev 5 kiểm tra xem người khác có biết bật máy không, máy có phun khói vào mặt ban giám khảo không, và tài liệu hướng dẫn có phải được viết bằng ngôn ngữ loài người không.

---

## 10. Mô tả một câu cho CV hoặc báo cáo nhóm

> Đảm nhận vai trò QA & Technical Writer cho dự án Atlas Agent, phụ trách chuẩn hóa tài liệu kỹ thuật, hướng dẫn setup/chạy project, kiểm thử định dạng input-output, xây dựng mock test data và phát triển Web UI test local để hỗ trợ nhóm kiểm tra pipeline AI trước khi tích hợp hệ thống chính thức.
