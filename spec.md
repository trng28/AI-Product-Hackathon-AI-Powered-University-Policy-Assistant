# AI SPEC — University Policy Assistant · Nhóm PARIS · D303

## §1. User & Job

**User:** Sinh viên, giảng viên và nhân sự nhà trường.

**Workflow:**
Người dùng nhập câu hỏi → hệ thống xác định nhóm policy → truy xuất tài liệu liên quan → phân tích và kiểm chứng → trả lời kèm điều khoản, nguồn và phiên bản tài liệu.

**Core JTBD:**
Khi cần tra cứu chính sách của trường, tôi muốn nhanh chóng tìm được quy định chính xác và còn hiệu lực để biết mình cần làm gì.

**Problem statement:**
Các chính sách của trường nằm rải rác trong nhiều tài liệu, khó tìm kiếm, dễ nhầm phiên bản và dễ bỏ sót điều kiện hoặc ngoại lệ.

**Phạm vi policy dự kiến:**

* Quy chế đào tạo và đăng ký học phần
* Học phí, học bổng và hỗ trợ tài chính
* Thi cử, chấm điểm và phúc khảo
* Cảnh báo học tập, bảo lưu và thôi học
* Kỷ luật và quy tắc ứng xử
* Ký túc xá và đời sống sinh viên
* Thực tập, trao đổi và tốt nghiệp
* Chính sách dành cho giảng viên và nhân sự

---

## §2. Impact & quyết định chọn

| Ứng viên                      | Số người ảnh hưởng |   Tần suất |                       Chi phí mỗi lần |        Khả thi |
| ----------------------------- | -----------------: | ---------: | ------------------------------------: | -------------: |
| Tra cứu quy chế đào tạo       |                Cao |        Cao |                 Mất thời gian đọc PDF |            Cao |
| Tra cứu học phí, học bổng     |                Cao | Trung bình |                    Dễ bỏ lỡ quyền lợi |            Cao |
| Tra cứu toàn bộ policy trường |            Rất cao |        Cao | Sai thông tin có thể gây hậu quả thật | Trung bình–cao |

**Ứng viên đã loại:**
Chỉ làm chatbot FAQ cố định, vì khó cập nhật khi policy thay đổi và không xử lý tốt các câu hỏi có điều kiện.

**Ứng viên chọn:**
University Policy Assistant đa tài liệu, vì phục vụ nhiều nhóm người dùng, có tần suất sử dụng cao và dễ mở rộng theo từng domain policy.

---

## §4. Thiết kế

**Lát cắt một câu:**
Người dùng hỏi một vấn đề liên quan đến chính sách trường → hệ thống xác định đúng nhóm policy và phiên bản tài liệu → trả lời kèm điều khoản và hành động cần thực hiện.

### Kiến trúc mở rộng

```text
University Policy Documents
        ↓
Knowledge Processing
        ↓
Policy Classification & Metadata
        ↓
Knowledge Indexing
        ↓
Multi-Agent Retrieval
        ↓
Policy Analysis
        ↓
Citation & Version Validation
        ↓
Answer + Source + Effective Date
```

### Module 1 — Knowledge Processing

* PDF parsing
* Text cleaning
* Legal structure detection
* Chunking theo chương, điều, khoản
* Nhận diện ngày hiệu lực và phiên bản

### Module 2 — Policy Classification & Indexing

Phân loại tài liệu theo:

* Academic Policy
* Financial Policy
* Student Affairs
* Examination Policy
* Scholarship Policy
* Disciplinary Policy
* HR/Faculty Policy

Lưu metadata:

```text
policy_type
document_title
department
version
effective_date
expiry_date
chapter
article
clause
page
source_file
```

### Module 3 — Multi-Agent Workflow

* **Orchestrator Agent:** điều phối luồng xử lý
* **Query Understanding Agent:** xác định ý định và nhóm policy
* **Retrieval Agent:** tìm đúng tài liệu, điều khoản và phiên bản
* **Policy Analysis Agent:** phân tích điều kiện, ngoại lệ và đối tượng áp dụng
* **Citation Validation Agent:** kiểm tra trích dẫn, ngày hiệu lực và tính nhất quán
* **Response Agent:** sinh câu trả lời dễ hiểu

### Non-goals

* Không tự tạo chính sách mới.
* Không thay thế quyết định chính thức của phòng ban.
* Không chỉnh sửa hồ sơ cá nhân hoặc dữ liệu học vụ.
* Không trả lời khi không có tài liệu đủ căn cứ.

### Automation

☑ **Conditional**

Hệ thống chỉ trả lời khi tìm được nguồn đủ tin cậy. Khi có nhiều policy xung đột, hết hiệu lực hoặc thiếu ngữ cảnh, hệ thống phải yêu cầu làm rõ hoặc chuyển người dùng đến phòng ban phụ trách.

---

## §5. Kiểu lỗi cần kiểm thử

* Truy xuất nhầm loại policy.
* Trả lời theo tài liệu đã hết hiệu lực.
* Nhầm policy dành cho sinh viên với giảng viên.
* Bỏ sót ngoại lệ hoặc điều kiện áp dụng.
* Trích dẫn đúng nội dung nhưng sai phiên bản.
* Câu hỏi thuộc nhiều policy cùng lúc.
* Không có thông tin nhưng hệ thống tự suy đoán.
* Câu hỏi mơ hồ về đối tượng, chương trình hoặc năm học.

---

## §6. Các đường đi trải nghiệm

**Happy path:**
Tìm đúng policy → đúng phiên bản → trả lời kèm nguồn.

**Low-confidence:**
Có nhiều tài liệu gần giống nhau → hỏi thêm chương trình, đối tượng hoặc năm học.

**Failure/không căn cứ:**
Không có thông tin → thông báo không tìm thấy và chỉ dẫn đơn vị phụ trách.

**Correction:**
Người dùng sửa đối tượng hoặc năm học → hệ thống truy xuất lại.

**Ngoài phạm vi:**
Yêu cầu sửa điểm, miễn học phí hoặc thay đổi hồ sơ → từ chối và hướng dẫn quy trình chính thức.

**Case đặc thù domain:**
Hai policy có nội dung khác nhau → ưu tiên tài liệu còn hiệu lực và cảnh báo người dùng về sự khác biệt.

---

## §7. Kiểm thử

**Golden set:** 20–30 câu, trải đều nhiều domain policy.

**Cơ cấu đề xuất:**

* 30% quy chế đào tạo
* 20% học phí và học bổng
* 15% thi cử và phúc khảo
* 15% kỷ luật và đời sống sinh viên
* 10% bảo lưu, thôi học và tốt nghiệp
* 10% câu đa policy hoặc sai phiên bản

**Quality bar:**

> **Đạt khi ≥85% câu thử đúng, và không được bịa thông tin, trích dẫn sai hoặc dùng policy hết hiệu lực dù chỉ một lần.**

Như vậy, project không còn giới hạn ở một PDF quy chế đào tạo mà trở thành **nền tảng tra cứu toàn bộ chính sách của trường**, trong khi vẫn giữ nguyên kiến trúc **Knowledge Processing → Policy Indexing → Multi-Agent Retrieval → Citation Validation → Response Generation**.

## §8. Trách nhiệm từng thành viên
| Thành viên | Phụ trách                              | Công việc                                                                                                                                                                                                              |
| ---------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ly**     | **Quality Assurance & Evaluation**     | Thực hiện Quality Check cho dữ liệu, xây dựng bộ Golden Set/Test Case, đánh giá Accuracy, Hallucination và Citation Accuracy của hệ thống.                                                                             |
| **Mai**    | **Data Collection & User Analysis**    | Xác định và thu thập nguồn dữ liệu (quy chế, policy của trường), phân tích User Story, xác định các tình huống sử dụng và phạm vi bài toán.                                                                            |
| **Truc**   | **AI System Development & Deployment** | Đề xuất kiến trúc **Multi-Agent RAG**, triển khai pipeline (Knowledge Processing, Knowledge Indexing, Multi-Agent Retrieval, Response Generation), tích hợp LLM & FAISS, xây dựng backend/frontend và triển khai demo. |


## §9. Changelog

| Sprint       | Thay đổi                                                                                                                                                                                                              | Mục tiêu                                                                 |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Sprint 1** | Xác định bài toán, đối tượng người dùng, phạm vi hệ thống; khảo sát và thu thập nguồn dữ liệu (quy chế, policy của trường); đề xuất kiến trúc và hướng tiếp cận **Multi-Agent RAG**.                                  | Xác định rõ bài toán, dữ liệu đầu vào và kiến trúc tổng thể cho MVP.     |
| **Sprint 2** | Triển khai phiên bản demo đầu tiên với phương pháp hiện tại; xây dựng pipeline **Knowledge Processing → Indexing → Retrieval → Response**; indexing **01 PDF** làm dữ liệu mẫu; thực hiện kiểm thử và đánh giá lần 1. | Chứng minh tính khả thi của giải pháp và đánh giá chất lượng ban đầu.    |
| **Sprint 3** | Mở rộng Knowledge Base sang toàn bộ quy chế và policy của trường; tối ưu Retrieval và Multi-Agent Workflow; bổ sung Citation Validation, Quality Check và Golden Set để nâng cao độ chính xác và giảm Hallucination.  | Hoàn thiện MVP, mở rộng phạm vi dữ liệu và tăng độ tin cậy của hệ thống. |
