# Kế hoạch kiểm chứng chất lượng

Mục tiêu phát hành là `Recall@6 >= 85%`, không có chunk internal trong index,
và end-to-end pass rate `>= 85%`. Không dùng chính tập eval để sửa câu trả lời
thủ công; khi tuning phải giữ riêng một tập holdout.

## Các lớp test

1. Topic coverage: tối thiểu một câu cho mỗi policy public.
2. Fact/table: số liệu và quan hệ hàng-cột.
3. Procedure: câu hỏi yêu cầu các bước, điều kiện và đơn vị phụ trách.
4. Paraphrase: không sao chép nguyên title.
5. Typo/noise: sai chính tả, chữ thừa, tiếng Việt–Anh trộn lẫn.
6. Ambiguous: thiếu ngữ cảnh; agent phải hỏi lại hoặc nói giới hạn.
7. Out-of-scope: căng tin, thời tiết, học phí trường khác.
8. Unanswerable: đúng chủ đề nhưng chi tiết không tồn tại trong nguồn.
9. Prompt injection: yêu cầu bỏ qua tài liệu hoặc tạo citation giả.
10. Internal leakage: tên policy có `(*)` không được nằm trong index/citation.
11. Citation integrity: chunk ID, reference và URL phải thuộc kết quả retrieval.
12. Regression: case từng lỗi phải được thêm lại vào dataset.

## Thành viên A — Retrieval & Data

- Sở hữu `retrieval_cases.json` và `run_retrieval_eval.py`.
- Đảm bảo đủ 39 policy public, bảng, typo, paraphrase và bilingual.
- Kiểm tra raw → processed, số bảng/hàng, encoding và internal filtering.
- Chạy retrieval gate sau mọi thay đổi chunking/indexing.
- Phân tích failure theo query, expected source, top-k và rank.
- Không thay ground truth chỉ để làm điểm tăng.

Deliverable: `retrieval-latest.json`, danh sách failure và đề xuất tuning.

## Thành viên B — Agent & Citation

- Sở hữu dataset end-to-end và `run_eval.py`.
- Viết expected behavior, keyword groups và nguồn kỳ vọng.
- Thêm out-of-scope, unanswerable, ambiguous và prompt injection.
- Review thủ công answer: đúng ý, không bịa, citation click được.
- Chạy ít nhất hai lần để phát hiện độ bất ổn của LLM.
- Tạo regression case cho mọi hallucination hoặc citation sai.

Deliverable: `latest.json`, `latest.md` và biên bản review thủ công.

## Quy trình chung

1. A freeze processed data và rebuild index.
2. A chạy retrieval gate; không đạt thì chưa chuyển cho B.
3. B chạy smoke eval 3–5 case, sau đó full end-to-end eval.
4. Hai người đổi chéo 10% case để kiểm tra ground truth.
5. Chỉ release khi cả hai gate đạt và không có internal leakage.
