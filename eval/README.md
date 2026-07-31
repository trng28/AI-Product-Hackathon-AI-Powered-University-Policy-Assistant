# Evaluation

Quy ước đặt tên, version, thêm/sửa testcase và regression được mô tả chi tiết
tại [`README_TESTCASES.md`](README_TESTCASES.md).

`questions.json` chứa 20 câu hỏi do nhóm tự thiết kế. Mỗi case có:

- `input`: câu hỏi đưa vào sản phẩm.
- `expected_behavior`: sản phẩm phải trả lời như thế nào.
- `expected_article` và `expected_pages`: citation ground truth.
- `keyword_groups`: các ý bắt buộc, hỗ trợ nhiều cách diễn đạt.
- `expect_evidence`: hệ thống phải trả lời có căn cứ hay từ chối.

Chạy retrieval gate trước (không gọi LLM):

```powershell
python eval/run_retrieval_eval.py --min-recall 0.85
```

Chạy end-to-end toàn bộ:

```powershell
python eval/run_eval.py `
  --dataset eval/agent_cases.json `
  --min-pass-rate 0.85
```

Chạy smoke test:

```powershell
python eval/run_eval.py --dataset eval/agent_cases.json --limit 3
```

Kết quả được lưu trong `eval/results/`:

- `latest.json`: toàn bộ output và grading dạng máy đọc.
- `latest.md`: báo cáo tóm tắt cho proposal/demo.
- Các file có timestamp để theo dõi nhiều lần chạy.

Một case đạt khi điểm tổng ít nhất 75%, citation đúng và quyết định
đủ/không đủ bằng chứng chính xác. Quality gate tổng đạt khi pass rate ít nhất
85% và không có case `critical` thất bại. Xem `QUALITY_PLAN.md` để phân công và
quy trình review.
