# Individual contribution report

Mỗi thành viên copy template này thành:

```text
reports/<student-id>-<short-name>.md
```

Giới hạn khuyến nghị: 1 trang, không chép lại README hoặc mô tả lý thuyết chung. Báo cáo không phải một bài pipeline cá nhân; mục đích là ghi nhận ownership và bằng chứng đóng góp trong sản phẩm nhóm.

---

## Thông tin

- Họ và tên: Vũ Minh Hiếu
- Mã học viên: 2A202602779
- Nhóm: Nhóm L3A — Day 08
- Repository/branch: `vmhieu/ui`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Giao diện Chatbot Streamlit | Thiết kế toàn diện giao diện Chatbot, layout hiện đại, thẻ trích dẫn nguồn (`sources`), badge phân loại phương thức truy xuất (`retrieval_method`) và điểm tương đồng (`score`) | [app.py](file:///c:/Users/hungn/OneDrive/Desktop/vin/K4-L3A-RAG-Pipeline/app.py) | Done |
| Source & Citation Highlighting (Bonus +2đ) | Trực quan hóa trích dẫn tài liệu: tiêu đề, tên file nguồn, loại văn bản (`LEGAL`/`NEWS`), trích đoạn (`content snippet`) và liên kết URL gốc | [app.py](file:///c:/Users/hungn/OneDrive/Desktop/vin/K4-L3A-RAG-Pipeline/app.py) | Done |
| Conversation Memory (Bonus +2đ) | Quản lý bộ nhớ ngữ cảnh hội thoại đa lượt trong session state hỗ trợ câu hỏi nối tiếp (follow-up query) | [app.py](file:///c:/Users/hungn/OneDrive/Desktop/vin/K4-L3A-RAG-Pipeline/app.py) | Done |
| Task 10 — Generation có Citation | Hoàn thiện hàm `reorder_for_llm` (chống lost-in-the-middle), `format_context`, kết nối `call_llm` đa provider và hàm `generate_with_citation` trả về đúng chuẩn schema `GenerationResult` | [src/task10_generation.py](file:///c:/Users/hungn/OneDrive/Desktop/vin/K4-L3A-RAG-Pipeline/src/task10_generation.py) | Done |
| Task 3 — Chuẩn hóa Markdown | Triển khai `convert_legal_docs` và `convert_news_articles` tự động chuyển đổi toàn bộ PDF và JSON sang Markdown chuẩn trong `data/standardized/` | [src/task3_convert_markdown.py](file:///c:/Users/hungn/OneDrive/Desktop/vin/K4-L3A-RAG-Pipeline/src/task3_convert_markdown.py) | Done |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Hiển thị chi tiết trích dẫn (Citation & Source Highlighting) dạng Expandable Source Card kết hợp Badge màu sắc phân loại theo từng phương thức (`⚡ HYBRID`, `🧠 DENSE`, `🔍 BM25`, `📄 PAGEINDEX`) và điểm tương đồng `score`.  
   **Lý do/evidence:** Giúp người dùng và giảng viên ngay lập tức đối chiếu được độ tin cậy và nguồn gốc xác thực của câu trả lời, ngăn chặn ảo giác (hallucination) của LLM và đáp ứng tiêu chí bonus rubric (+2 điểm).  
   **Trade-off:** Tăng mật độ thông tin trên màn hình; được tối ưu bằng cách gom các trích đoạn vào Expander thu gọn linh hoạt để giao diện vẫn sạch đẹp.

2. **Quyết định:** Thiết kế cơ chế phòng thủ (Graceful Degradation) cho giao diện Streamlit khi gọi pipeline hoặc provider bên ngoài.  
   **Lý do/evidence:** Tuân thủ quy định trong Module Contract (`PAGEINDEX/provider lỗi không được làm UI crash`) và giữ ứng dụng luôn hoạt động ổn định kể cả khi thiếu API key hoặc backend đang trong quá trình phát triển.  
   **Trade-off:** Cần xử lý khối bắt ngoại lệ chi tiết và thiết kế thông báo phản hồi thân thiện cho người dùng.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest tests/test_contracts.py -k "reorder or safe_refusal or public_function"` -> Đạt 3/3 passed (100% test contract Task 10).
  - `pytest tests/test_acceptance.py -k "corpus or standardized"` -> Đạt 3/3 passed (100% test acceptance về dữ liệu và chuẩn hóa).
  - Thử nghiệm trực tiếp trên giao diện `http://localhost:8501` với các câu hỏi in-domain (học bổng, học phí, ký túc xá) và câu hỏi out-of-domain (dự báo thời tiết) để kiểm tra safe refusal.
- Kết quả trước/sau: Trước đó `app.py` và `task3_convert_markdown.py` là các file khung chứa TODO bị lỗi `NotImplementedError`; sau khi hoàn thiện, chatbot chạy trơn tru, hiển thị đầy đủ câu trả lời, độ trễ và nguồn trích dẫn; lệnh convert dữ liệu chạy tự động thành công (Exit code 0).
- Lỗi đã phát hiện và cách xử lý: Phát hiện lỗi `NotImplementedError` ở Task 3 và Task 10; bổ sung cơ chế fallback trong `convert_legal_docs` đảm bảo quá trình đọc PDF hoạt động ổn định trên cả môi trường có và không có `MarkItDown`.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Bộ nhớ hội thoại đa lượt hiện tại đang lưu chuỗi ngữ cảnh gần nhất trên session state client; chưa tích hợp module LLM query re-writing để viết lại truy vấn trước khi gửi vào retriever.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp streaming response (`st.write_stream`) để hiển thị câu trả lời từng từ theo thời gian thực tương tự ChatGPT.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 20/09/2026
- Tên thành viên: Vũ Minh Hiếu
