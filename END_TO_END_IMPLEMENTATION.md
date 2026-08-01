# VinUni Policy Assistant — End-to-End Implementation

Tài liệu này mô tả đúng trạng thái đang được triển khai trong repository tại
thời điểm audit ngày 31/07/2026. Các số liệu được lấy trực tiếp từ raw manifest,
processed manifest, FAISS config và eval report hiện tại.

## 1. Tổng quan

Hệ thống là một ứng dụng Retrieval-Augmented Generation (RAG) đa agent dùng để
trả lời câu hỏi dựa trên các policy public của VinUniversity.

```text
VinUni Policy Website
        ↓
Playwright Raw HTML Crawler
        ↓
HTML Processing + Public/Internal Filter + Table Conversion
        ↓
RAG-ready JSONL Chunks
        ↓
Multilingual E5 Embeddings + FAISS
        ↓
LangGraph 6-agent Workflow
        ↓
FastAPI
        ↓
React/Vite Chat UI + Clickable Citations
```

## 2. Nguồn dữ liệu

### Nguồn online

- Website: `https://policy.vinuni.edu.vn`
- Phương thức lấy dữ liệu: Playwright Chromium chạy headless.
- Crawler bắt đầu từ trang chủ và `/all-policies/`, sau đó duyệt các liên kết
  HTML nội bộ.
- Sitemap của website hiện không sử dụng được; crawler tự động chuyển sang
  Playwright link crawling.
- Ảnh, media và font bị chặn khi crawl để giảm thời gian và băng thông.
- Crawler lưu HTML đã render, không xử lý nội dung ngay trong lúc crawl.
- Raw manifest hỗ trợ resume; trang đã lưu hợp lệ không bị tải lại.

Script:

```text
backend/crawl/crawl_vinuni_policies.py
```

### Raw data hiện tại

```text
backend/data/vinuni-policies/raw/
├── manifest.json
└── pages/*.html
```

Số liệu:

| Chỉ số | Giá trị |
|---|---:|
| HTML pages | 131 |
| Tổng dung lượng HTML | 6,699,388 bytes, khoảng 6.39 MiB |
| Crawl failures được ghi trong processed manifest | 0 |
| Thời điểm raw manifest | 30/07/2026 18:39 UTC |

Raw data là nguồn audit. Không dùng raw HTML trực tiếp để tạo câu trả lời.

## 3. Xử lý dữ liệu

Script:

```text
backend/crawl/process_vinuni_raw.py
```

Pipeline xử lý:

1. Đọc `raw/manifest.json`.
2. Parse HTML bằng BeautifulSoup.
3. Sửa lỗi encoding/mojibake bằng `ftfy`.
4. Loại script, style, navigation, footer, form và SVG.
5. Trích title, URL, category và nội dung policy.
6. Trích metadata:
   - Reference Number
   - Document Type
   - Issuing By
   - Issuing Date
   - Applying For
   - Security Classification
7. Trích document links và external links.
8. Xác định policy internal từ dấu `(*)` trên link ở trang danh sách.
9. Chỉ đưa policy public vào Markdown, chunks và FAISS.
10. Chuyển HTML table thành Markdown table và JSON có cấu trúc.
11. Xử lý `rowspan`, `colspan`, caption và header.
12. Chia nội dung thành chunks tối đa 1,600 ký tự, overlap mục tiêu 200 ký tự.
13. Với hàng bảng quá dài, lặp lại header khi chia để giữ ngữ cảnh cột.

### Processed data hiện tại

```text
backend/data/vinuni-policies/processed/
├── manifest.json
├── pages.jsonl
├── policies.jsonl
├── internal_policies.jsonl
├── chunks.jsonl
└── markdown/*.md
```

| Chỉ số | Giá trị |
|---|---:|
| Tổng trang đã xử lý | 131 |
| Policy detail được nhận diện | 115 |
| Policy public | 39 |
| Policy internal `(*)` bị loại | 76 |
| Markdown public | 39 |
| Policy public có structured table | 32 |
| Top-level tables | 116 |
| Table rows | 882 |
| RAG chunks | 527 |
| Processing failures | 0 |

`pages.jsonl` giữ toàn bộ trang để audit. `policies.jsonl`, `chunks.jsonl` và
`markdown/` chỉ chứa policy public. `internal_policies.jsonl` giữ danh sách bị
loại để kiểm tra leakage, nhưng không được index.

## 4. Embedding và vector index

Index hiện tại:

```text
data/policy-index/
├── config.json
├── chunks.json
└── vectors.faiss
```

### Embedding model

| Thuộc tính | Giá trị |
|---|---|
| Model | `intfloat/multilingual-e5-small` |
| Framework | Sentence Transformers |
| Input passage prefix | `passage:` |
| Input query prefix | `query:` |
| Vector normalization | Có |
| Vector database | FAISS |
| FAISS index | `IndexFlatIP` |
| Indexed chunks | 527 |

Nguồn đang được index:

```text
backend/data/vinuni-policies/processed/chunks.jsonl
```

Build/rebuild index:

```powershell
python -m backend.policy_assistant.cli index
```

Indexer vẫn hỗ trợ PDF và JSONL để tương thích pipeline cũ, nhưng nguồn mặc định
hiện tại là public `chunks.jsonl`.

## 5. Retrieval

Implementation:

```text
backend/policy_assistant/retrieval.py
```

Retriever là hybrid retrieval:

```text
final score =
    0.75 × semantic similarity
  + 0.25 × keyword match
  + 0.15 article bonus (nếu có target article)
```

Runtime hiện tại:

- `TOP_K=6`.
- FAISS lấy tối thiểu 20 candidates; với `TOP_K=6`, hệ thống lấy 24 candidates.
- Candidates được rerank bằng semantic score, keyword score và article bonus.
- Sáu chunks cao nhất được chuyển cho Policy Analysis Agent.

## 6. LLM runtime

### Cấu hình đang chạy

Được đọc từ `backend/.env`:

| Thuộc tính | Giá trị |
|---|---|
| Provider | OpenAI |
| Chat model | `gpt-4o-mini` |
| Temperature | `0` |
| OpenAI mode | Responses API |
| Embedding model | `intfloat/multilingual-e5-small` |
| Top K | `6` mặc định |

API key không được ghi trong tài liệu hoặc source control.

### Provider có thể cấu hình

Code hỗ trợ:

| Provider | Default nếu không override |
|---|---|
| OpenAI | `gpt-5.6` |
| Groq | `llama-3.3-70b-versatile` |
| Gemini | `gemini-2.5-flash` |

Các giá trị trên là khả năng cấu hình trong code. Runtime hiện tại thực tế là
OpenAI `gpt-4o-mini`.

## 7. Multi-agent workflow

Implementation:

```text
backend/policy_assistant/agents.py
```

LangGraph có **6 agent/node chức năng**, chạy tuần tự:

```text
START
  ↓
1. Query Understanding Agent
  ↓
2. Question Decomposition Agent
  ↓
3. Retrieval Agent
  ↓
4. Policy Analysis Agent
  ↓
5. Citation Validation Agent
  ↓
6. Response Agent
  ↓
END
```

### 1. Query Understanding Agent

- Có gọi LLM.
- Chuyển câu hỏi thành structured output:
  - intent
  - topic
  - keywords
  - target articles
  - rewritten query
- Không được tự bịa số Điều.

### 2. Question Decomposition Agent

- Có gọi LLM.
- Phân rã câu hỏi nhiều ý thành các sub-query độc lập.
- Giúp retrieval bao phủ từng phần và cho phép trả lời partial evidence.

### 3. Retrieval Agent

- Không gọi chat LLM.
- Dùng multilingual E5, FAISS và keyword reranking.
- Trả về top 6 evidence chunks.

### 4. Policy Analysis Agent

- Có gọi LLM.
- Chỉ được sử dụng evidence đã retrieve.
- Trả structured output gồm answer, evidence decision, citations và confidence.
- Citation do LLM đề xuất phải dùng chunk ID có trong evidence.

### 5. Citation Validation Agent

- Deterministic, không gọi LLM.
- Loại mọi citation có chunk ID không tồn tại trong retrieved results.
- Giảm confidence nếu có citation không hợp lệ.
- Tạo `source_url` khi document là URL public.
- Không cho LLM tự xác nhận citation của chính nó.

### 6. Response Agent

- Deterministic, không gọi LLM.
- Trả response cuối cùng.
- Nếu thiếu evidence hoặc không có citation hợp lệ, thay answer bằng thông báo
  không đủ căn cứ.

### Số lần gọi LLM

Mỗi câu hỏi thông thường gọi chat LLM **3 lần**:

1. Query understanding.
2. Question decomposition.
3. Policy analysis.

Ba node còn lại không gọi chat LLM. Embedding query là một model call local
riêng, không phải chat LLM API.

### Conversation memory

- Frontend gửi tối đa 6 lượt hoàn chỉnh gần nhất (12 messages) trong mỗi request.
- History chỉ dùng để giải quyết câu hỏi nối tiếp như "ngành đó" hoặc "mức này".
- Backend không lưu memory dùng chung giữa người dùng hoặc phụ thuộc RAM của Render.
- Policy chunks được retrieve vẫn là nguồn evidence duy nhất cho câu trả lời.

## 8. Citation

Mỗi citation API gồm:

```text
chunk_id
article/title
reference number
page
document
source_url
support
```

Với HTML policy:

- `article` là policy title.
- `clause` là reference number.
- `page=0` và không hiển thị “Trang 0”.
- `source_url` là URL policy public.
- Frontend render title thành link mở tab mới.

Với PDF cũ, citation vẫn có document name và page number.

## 9. Backend API

Framework: FastAPI.

Implementation:

```text
backend/api/main.py
```

Endpoints:

| Method | Endpoint | Chức năng |
|---|---|---|
| GET | `/api/health` | Provider, model và index readiness |
| POST | `/api/index` | Build/rebuild FAISS từ JSONL, PDF hoặc processed directory |
| POST | `/api/ask` | Chạy toàn bộ LangGraph workflow |

Agent runtime được cache trong process. Sau khi rebuild index, runtime được
reset để lần hỏi tiếp theo đọc index mới.

## 10. Frontend

Stack:

- React 19
- TypeScript
- Vite
- React Markdown
- Lucide icons

Frontend gọi:

```text
GET  /api/health
POST /api/index
POST /api/ask
```

Kết quả hiển thị:

- Markdown answer.
- Evidence status.
- Confidence.
- Danh sách citation.
- Policy title và reference number.
- Clickable source URL mở trong tab mới.

## 11. Evaluation

### Retrieval eval đã chạy

Dataset:

- 39 topic coverage cases, một case cho mỗi policy public.
- 18 robustness cases.
- Tổng cộng 57 cases.

Kết quả thực tế:

| Metric | Kết quả |
|---|---:|
| Recall@6 | 96.49% |
| MRR | 92.11% |
| Internal chunks leaked | 0 |
| Quality gate | PASS |

Hai retrieval cases hiện chưa đạt:

- `R04`: paraphrase về công nhận môn học.
- `R09`: noisy query về vi phạm ký túc xá.

Các case này được giữ làm regression tests.

### End-to-end eval

Đã triển khai và chạy ngày 31/07/2026:

- 13 agent cases.
- Positive, table, procedure, bilingual.
- Out-of-scope.
- Unanswerable detail.
- Prompt injection.
- Internal leakage.
- Pass-rate gate `>=85%`.
- Critical case gate.

Kết quả thực tế:

| Metric | Kết quả |
|---|---:|
| Cases | 13 |
| Passed | 9 |
| Pass rate | 69.23% |
| Average score | 85.00% |
| Citation accuracy | 84.62% |
| Evidence decision accuracy | 100% |
| Critical failures | Có |
| Quality gate | FAIL |

Hai failure thực chất thuộc grader keyword rubric (`N02`, `N03`). Nếu adjudicate
hai case này là pass thì tỷ lệ là 11/13 = 84.62%, vẫn thấp hơn gate và còn hai
critical system failures `A04`, `S01`.

Chạy:

```powershell
python eval/run_eval.py `
  --dataset eval/agent_cases.json `
  --min-pass-rate 0.85
```

## 12. Chạy end-to-end local

### 1. Crawl

Từ thư mục `src`:

```powershell
python crawl/crawl_vinuni_policies.py
```

### 2. Process

```powershell
python crawl/process_vinuni_raw.py
```

### 3. Build index

Từ project root:

```powershell
python -m backend.policy_assistant.cli index
```

### 4. Start backend

```powershell
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Start frontend

```powershell
cd frontend
npm run dev
```

### 6. Test

```powershell
$env:HF_HUB_OFFLINE = "1"
python eval/run_retrieval_eval.py --min-recall 0.85

python eval/run_eval.py `
  --dataset eval/agent_cases.json `
  --min-pass-rate 0.85
```

## 13. Docker deployment

Docker Compose có hai services:

- `backend`: FastAPI, port mặc định `8000`.
- `frontend`: static React app qua web server, port mặc định `8080`.

Persistent volumes:

- `policy_index`
- `huggingface_cache`

Lưu ý: named volume Docker tách biệt với `data/policy-index` trên host. Khi
volume mới chưa có index, cần gọi `/api/index` hoặc có bước seed index phù hợp.

## 14. Giới hạn và việc còn lại

1. Full end-to-end eval đạt 69.23%, chưa qua quality gate 85%.
2. Hai retrieval robustness cases chưa đạt nhưng tổng Recall@6 đã qua gate.
3. Crawler là link crawler, nên độ phủ phụ thuộc graph liên kết public tại thời
   điểm crawl.
4. Dữ liệu cần được recrawl và rebuild index khi website cập nhật.
5. `gpt-4o-mini` là model runtime do `backend/.env` override; môi trường khác có thể
   chạy model khác.
6. FAISS `IndexFlatIP` phù hợp quy mô 527 chunks hiện tại; nếu dữ liệu tăng lớn,
   cần đánh giá index khác hoặc vector database.
7. Cần theo dõi latency CPU của multilingual E5 khi deploy.

## 15. File map

| Thành phần | File/thư mục |
|---|---|
| Raw crawler | `backend/crawl/crawl_vinuni_policies.py` |
| Data processor | `backend/crawl/process_vinuni_raw.py` |
| Raw data | `backend/data/vinuni-policies/raw/` |
| Processed public data | `backend/data/vinuni-policies/processed/` |
| Index builder | `backend/policy_assistant/indexing.py` |
| Hybrid retriever | `backend/policy_assistant/retrieval.py` |
| Agents/LangGraph | `backend/policy_assistant/agents.py` |
| LLM provider factory | `backend/policy_assistant/llm.py` |
| Service | `backend/policy_assistant/service.py` |
| FastAPI | `backend/api/main.py` |
| Frontend | `frontend/src/` |
| FAISS index | `data/policy-index/` |
| Retrieval eval | `eval/run_retrieval_eval.py` |
| Agent eval | `eval/run_eval.py` |
| Eval process | `eval/QUALITY_PLAN.md` |
| Testcase guide | `eval/README_TESTCASES.md` |
