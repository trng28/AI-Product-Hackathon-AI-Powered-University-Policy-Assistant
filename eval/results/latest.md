# Báo cáo Eval – VinUni Policy Assistant

- Thời gian: 2026-07-30T08:57:11.753442+00:00
- Provider/model: `openai` / `gpt-4o-mini`
- Tổng số câu: **20**
- Chạy thành công: **20**
- Passed: **18** (90.0%)
- Điểm trung bình: **95.5%**
- Citation accuracy: **90.0%**
- Evidence decision accuracy: **100.0%**
- Thời gian trung bình/câu: **10.88s**

## Kết quả chi tiết

| ID | Category | Score | Pass | Citation | Evidence | Latency |
|---|---|---:|:---:|:---:|:---:|---:|
| E01 | course_registration | 100% | ✅ | ✅ | ✅ | 11.36s |
| E02 | course_registration | 100% | ✅ | ✅ | ✅ | 12.54s |
| E03 | add_drop | 100% | ✅ | ✅ | ✅ | 9.35s |
| E04 | credit_transfer | 100% | ✅ | ✅ | ✅ | 12.60s |
| E05 | retake | 100% | ✅ | ✅ | ✅ | 4.74s |
| E06 | leave | 100% | ✅ | ✅ | ✅ | 11.64s |
| E07 | classification | 100% | ✅ | ✅ | ✅ | 11.64s |
| E08 | academic_warning | 100% | ✅ | ✅ | ✅ | 16.57s |
| E09 | academic_warning | 100% | ✅ | ✅ | ✅ | 7.99s |
| E10 | dismissal | 100% | ✅ | ✅ | ✅ | 18.38s |
| E11 | dual_program | 100% | ✅ | ✅ | ✅ | 8.58s |
| E12 | transfer | 85% | ✅ | ✅ | ✅ | 15.71s |
| E13 | assessment | 100% | ✅ | ✅ | ✅ | 8.33s |
| E14 | exam | 100% | ✅ | ✅ | ✅ | 10.01s |
| E15 | exam | 100% | ✅ | ✅ | ✅ | 5.66s |
| E16 | grading | 70% | ❌ | ❌ | ✅ | 13.91s |
| E17 | appeal | 55% | ❌ | ❌ | ✅ | 17.29s |
| E18 | graduation | 100% | ✅ | ✅ | ✅ | 7.66s |
| E19 | graduation | 100% | ✅ | ✅ | ✅ | 9.64s |
| E20 | out_of_scope | 100% | ✅ | ✅ | ✅ | 3.99s |

## Các trường hợp chưa đạt

### E16 – Hệ thống điểm chữ và điểm số của VinUni được quy định ra sao?

- Expected: Trình bày hệ thống điểm theo Điều 25, citation trang 27-30.
- Error: Không có
- Answer: Hệ thống điểm chữ và điểm số của VinUni được quy định như sau:

1. **Điểm học phần**: Là tổng điểm của tất cả các điểm đánh giá bộ phận của học phần nhân với trọng số tương ứng. Điểm học phần sẽ được làm tròn đến một chữ số thập phân và sau đó được chuyển thành điểm chữ. Mức điểm chữ của mỗi học phần phải được quy đổi qua điểm số thang điểm 4. Giảng viên dạy học phần có trách nhiệm chuyển đổi đánh giá định lượng sang điểm chữ cuối cùng. Chính sách chấm điểm cần được mô tả rõ ràng trong đề cương chi tiết môn học (chunk_id: [26]).

2. **Chuyển đổi điểm**: Điểm chữ cuối cùng sẽ được thể hiện trong bảng điểm của sinh viên. Các Viện có thể xây dựng quy trình chấm điểm cụ thể hơn dựa trên hướng dẫn này và do Viện trưởng phê duyệt (chunk_id: [26]).

3. **Liêm chính trong học thuật**: Sinh viên phải tuân theo các quy định liên quan đến điểm số và không vi phạm các quy định này. Mọi hành vi sai trái sẽ bị xử phạt (chunk_id: [5f09eb65ef31]).

Tóm lại, hệ thống điểm chữ và điểm số tại VinUni được xây dựng dựa trên việc tính toán điểm học phần và quy đổi sang điểm chữ, đồng thời yêu cầu sinh viên tuân thủ các quy định về liêm chính trong học thuật.

### E17 – Sinh viên muốn phúc tra điểm thì thực hiện theo quy định nào?

- Expected: Nêu quy trình hoặc nguyên tắc phúc tra theo Điều 27, citation trang 31.
- Error: Không có
- Answer: Sinh viên muốn phúc tra điểm cần thực hiện theo quy định tại Điều 14 của Quy chế Đào tạo, trong đó quy định rằng sinh viên có quyền đăng ký học lại để cải thiện điểm trung bình tích lũy. Tuy nhiên, sinh viên phải tự chịu trách nhiệm nếu phải học lại/học cải thiện và nhà trường không có nghĩa vụ tổ chức các học phần riêng cho các trường hợp này. Nếu sinh viên có học phần bắt buộc bị điểm F, họ sẽ phải học lại học phần đó hoặc tham gia một học phần tương đương theo quy định trong chương trình giảng dạy cho đến khi đạt điểm đạt. Điều này cho thấy rằng việc phúc tra điểm có thể liên quan đến việc học lại các học phần mà sinh viên không đạt yêu cầu.
