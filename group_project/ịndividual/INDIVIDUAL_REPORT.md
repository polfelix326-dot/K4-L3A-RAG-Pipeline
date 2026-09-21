# Individual contribution report

## Thông tin

- Họ và tên: Dương Minh Hiếu
- Mã học viên: 2A202602488
- Nhóm: [Tên nhóm]
- Repository/branch: K4-L3A-RAG-Pipeline / duongminhhieu

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Data collection & ingestion | Tham gia chuẩn bị và kiểm tra luồng thu thập tài liệu pháp lý và bài viết tin tức từ archive/dữ liệu landing; xác nhận cấu trúc dữ liệu đầu vào đủ điều kiện cho pipeline. | src/task1_collect_legal_docs.py, src/task2_crawl_news.py | Done |
| Standardization | Rà soát và hỗ trợ chuẩn hóa dữ liệu đầu vào thành Markdown có front matter, bảo toàn metadata và nguồn gốc tài liệu để phục vụ indexing. | src/task3_convert_markdown.py | Done |
| Chunking & embedding | Tham gia xây dựng quy trình chia văn bản thành chunk, giữ metadata và tạo embedding cho từng đoạn để chuẩn bị cho retrieval. | src/task4_chunking_indexing.py | Done |
| Dense search | Hỗ trợ triển khai semantic search dựa trên Chroma cosine similarity, đảm bảo query và passage cùng được embedding theo schema chuẩn. | src/task5_semantic_search.py | Done |
| Sparse search | Phụ trách kiểm tra luồng lexical/BM25 trên corpus chunk để đảm bảo cùng schema output với dense retrieval. | src/task6_lexical_search.py | Done |
| Reranking / fusion | Tham gia kiểm tra logic gộp thứ hạng giữa dense và sparse theo RRF để tăng độ chính xác kết quả trả về. | src/task7_reranking.py | Done |
| Fallback & retrieval pipeline | Kết nối logic tìm kiếm, threshold và fallback để pipeline có thể trả về hybrid result ổn định khi dense score thấp. | src/task8_pageindex_vectorless.py, src/task9_retrieval_pipeline.py | Done |
| Generation / answer synthesis | Không tham gia phần generation, citation map và final answer synthesis. Phần này nằm ngoài phạm vi công việc tôi thực hiện. | - | Not assigned |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chọn lưu trữ index bằng Chroma PersistentClient với khoảng cách cosine và embedding chuẩn hóa.
   **Lý do/evidence:** Logic trong src/task4_chunking_indexing.py và src/task5_semantic_search.py cố định schema metadata, khởi tạo collection với cấu hình cosine, đồng thời sử dụng normalize_embeddings=True để search và ranking có cùng thang đo.
   **Trade-off:** Tăng tính nhất quán và dễ kiểm tra giữa dense retrieval và các module sau, nhưng cần rebuild index đúng cấu hình để tránh mismatch giữa metadata và embedding.

2. **Quyết định:** Một lần chạy RRF trên dense + sparse rồi mới dùng fallback theo dense score gốc.
   **Lý do/evidence:** src/task9_retrieval_pipeline.py đi logic: dense và sparse được lấy trước, sau đó fuse bằng rerank_rrf, và chỉ khi best_dense_score < threshold mới chuyển sang fallback. Điều này giúp tránh so sánh nhầm giữa thang điểm hồi quy và RRF.
   **Trade-off:** Tăng độ ổn định cho pipeline nhưng cũng làm logic phụ thuộc nhiều vào threshold và chất lượng dense retrieval ban đầu.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - python -m src.task3_convert_markdown
  - python -m src.task4_chunking_indexing
  - python -m src.task5_semantic_search
  - python -m src.task6_lexical_search
  - python -m src.task9_retrieval_pipeline
  - pytest tests/test_contracts.py -q (nếu đã chạy trong nhóm)
- Kết quả trước/sau nếu có:
  - Dữ liệu landing được chuẩn hóa thành Markdown có metadata đầy đủ.
  - Chunks được tạo và index vào Chroma với metadata rõ ràng.
  - Retrieval pipeline chạy được theo luồng dense → sparse → fusion → fallback.
- Lỗi đã phát hiện và cách xử lý:
  - Mismatch cấu hình embedding hoặc index cần rebuild đúng version model/dimension.
  - Metadata của document/chunk cần tuân schema; khi thiếu dữ liệu hoặc cấu trúc sai, pipeline bị reject ở validate_document/validate_search_results.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tôi chưa trực tiếp đảm nhận task generation và UI cuối cùng, vì vậy phần answer synthesis, citation rendering và chat UI chưa nằm trong phạm vi tôi chủ động triển khai.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tôi sẽ tập trung hoàn thiện phần generation/citation để pipeline end-to-end chạy trọn vẹn từ query đến kết quả có nguồn tham khảo.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: [Ngày viết báo cáo]
- Tên thành viên: Dương Minh Hiếu
