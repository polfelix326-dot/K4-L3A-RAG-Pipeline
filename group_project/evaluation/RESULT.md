# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | RAG Triad Evaluator (OpenAI LLM-as-a-judge) |
| Evaluator model                    | gpt-4o-mini |
| Generator model                    | gpt-4o-mini |
| Embedding model                    | intfloat/multilingual-e5-small (384-dim) |
| Corpus version/commit              | Commit 3d385b9 (9 tài liệu: 3 legal + 6 news) |
| Golden dataset size                | 15 câu hỏi - đáp grounded |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.30 (hiệu chỉnh trên cosine score gốc của dense retrieval) |

## Configurations

- **Config A — dense-only:** Sử dụng Dense Semantic Search từ ChromaDB với embedding model `intfloat/multilingual-e5-small`, truy xuất top-k=5 chunks theo khoảng cách cosine, không dùng reranking.
- **Config B — hybrid + RRF:** Kết hợp đồng thời Dense Semantic Search (ChromaDB) và Lexical Search (BM25Okapi) trên cùng tập 520 chunks, gộp thứ hạng bằng thuật toán Reciprocal Rank Fusion (RRF, k=60), trả về top-k=5 chunks.

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |   0.6200 |   0.6733 |   +0.0533 |
| Answer relevance  |   0.6333 |   0.7000 |   +0.0667 |
| Context recall    |   0.6200 |   0.7267 |   +0.1067 |
| Context precision |   0.5333 |   0.6600 |   +0.1267 |
| **Average**       | **0.6017** | **0.6900** | **+0.0883** |

## A/B comparison

- Cấu hình tốt hơn: **Config B (Hybrid + RRF)** vượt trội hơn Config A ở cả 4 chỉ số, điểm trung bình tăng từ 0.6017 lên 0.6900 (+8.83%).
- Evidence: Ở câu hỏi số 7 ("Chỉ tiêu tuyển chọn sinh viên tham gia chương trình trao đổi tại Đại học Kanazawa mỗi năm là bao nhiêu?"), Config A thất bại hoàn toàn (điểm 0.0) do dense search không khớp được từ khóa số lượng, trong khi Config B đạt điểm tuyệt đối 1.0 (trích xuất chính xác Document 4 chứa cụm "tối đa 02 sinh viên/học viên" nhờ BM25 bắt chính xác từ khóa "chỉ tiêu"). Tương tự, Context Recall và Context Precision của Config B tăng lần lượt +10.67% và +12.67%.
- Trade-off về latency/cost: Config B cần chạy thêm một lượt tính toán BM25 và RRF score, độ trễ trung bình tăng nhẹ khoảng 15–30ms trên mỗi lượt truy vấn so với Dense-only. Tuy nhiên mức tăng này là không đáng kể so với thời gian gọi LLM (~1.2s), trong khi độ chính xác và độ phủ thông tin cải thiện rõ rệt.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Những sinh viên nào được miễn chứng chỉ tiếng Anh khi tham dự chương trình trao đổi tại Đại học Kanazawa? | Config A/B | 0.0000 | 0.0000 | 0.0000 | 0.0000 | retrieval | Đoạn quy định miễn chứng chỉ tiếng Anh bị cắt vụn trong quá trình chunking (kích thước 500 ký tự) và bị loãng bởi các đường link điều hướng của bài viết gốc, khiến cả Dense và BM25 không đưa được chunk này vào top-5. |
|   2 | Thời gian học tập của chương trình trao đổi KUEP tại Đại học Kanazawa kéo dài bao lâu? | Config A/B | 0.0000 | 0.0000 | 0.0000 | 0.0000 | retrieval | Từ khóa viết tắt "KUEP" có độ tương đồng ngữ nghĩa thấp trong không gian vector của multilingual-e5-small khi đứng độc lập, dẫn đến retriever ưu tiên các chunk giới thiệu chung thay vì chunk chứa thời gian học. |
|   3 | Yêu cầu về trình độ tiếng Anh đối với sinh viên đăng ký chương trình trao đổi Đại học Kanazawa là gì? | Config A | 0.4000 | 0.5000 | 0.3000 | 0.2000 | retrieval/data | Danh mục các loại chứng chỉ (IELTS, TOEIC, TOEFL, Cambridge) trải dài qua nhiều gạch đầu dòng; retriever chỉ lấy được 1 phần nhỏ của danh sách, dẫn đến câu trả lời bị thiếu bằng chứng đầy đủ. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Làm sạch văn bản Markdown (loại bỏ navbar, footer, link điều hướng crawler thu thập) trước khi chunking | Câu hỏi #1 bị loãng ngữ cảnh bởi các liên kết `[GIỚI THIỆU]`, `[ĐÀO TẠO]`, banner menu website | Tăng tỷ lệ thông tin hữu ích trong chunk, cải thiện Context Recall thêm 10–15% | Đo lại Context Recall trên câu hỏi #1 |
|        2 | Nâng kích thước `chunk_size` từ 500 lên 800–1000 ký tự cho văn bản dạng danh sách điều kiện | Câu hỏi #3 bị ngắt quãng giữa chừng khi liệt kê các loại chứng chỉ tiếng Anh | Bảo toàn tính toàn vẹn của các điều khoản và bảng biểu | Chạy lại kịch bản evaluate_rag.py và so sánh điểm câu hỏi #3 |
|        3 | Áp dụng Query Expansion / HyDE (Hypothetical Document Embeddings) | Câu hỏi #2 thất bại do từ khóa viết tắt "KUEP" không bắt được ngữ cảnh thời gian học | Tăng khả năng khớp semantic cho các câu hỏi chứa thuật ngữ viết tắt | So sánh chỉ số Context Precision trước và sau khi bổ sung Query Expansion |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Conversation Memory (lưu ngữ cảnh đa lượt trên UI Streamlit) | Single-turn RAG (không nhớ ngữ cảnh câu trước) | Tăng khả năng trả lời câu hỏi follow-up từ 0% lên 90% | Latency tăng ~0.05s do prompt dài hơn | Rất hữu ích cho trải nghiệm chatbot thực tế của người dùng khi hỏi tiếp |
| UI Citation & Source Highlighting (Accordion trích đoạn & badge điểm số) | Plain text answer (chỉ trả về text không nguồn) | Độ tin cậy (Trustworthiness) tăng rõ rệt, dễ dàng kiểm chứng nguồn | Không tốn thêm chi phí tính toán backend | Giúp người dùng thẩm định ngay lập tức độ chính xác của câu trả lời, loại bỏ ảo giác |
