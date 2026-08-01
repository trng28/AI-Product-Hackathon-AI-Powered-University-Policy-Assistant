# AI-Powered University Policy Assistant

## Workflow Modules

```text
                OFFLINE

Module 1
Knowledge Processing
        │
        ▼
Module 2
Knowledge Indexing
        │
        ▼
Vector Database (FAISS)

────────────────────────────────────

                ONLINE

Module 3
Multi-Agent Retrieval
        │
        ▼
Module 4
Response Generation
```

---

# Module 1. Knowledge Processing

### Mục tiêu

Chuẩn hóa tài liệu pháp lý thành dữ liệu có cấu trúc.

### Input

* University Policy PDF
* Academic Regulations
* Internal Guidelines

### Workflow

```text
PDF
    ↓
Document Parsing
    ↓
Text Cleaning
    ↓
Legal Structure Detection
    ↓
Chunking
```

### Output

* Structured Text
* Legal Chunks
* Metadata

Ví dụ metadata

```text
Document
Chapter
Article
Clause
Page
Version
Effective Date
```

---

# Module 2. Knowledge Indexing

### Mục tiêu

Xây dựng Knowledge Base phục vụ Retrieval.

### Input

* Legal Chunks

### Workflow

```text
Legal Chunks
      ↓
Embedding Model
      ↓
Vector Embedding
      ↓
FAISS Index
```

### Output

* Vector Database
* Metadata Index

---

# Module 3. Multi-Agent Retrieval

### Mục tiêu

Tìm kiếm chính xác các điều khoản liên quan.

### Input

User Question

### Workflow

```text
User Query
      ↓
Orchestrator Agent
      ↓
Query Understanding Agent
      ↓
Retrieval Agent
      ↓
Policy Analysis Agent
      ↓
Citation Validation Agent
```

### Vai trò các Agent

### Orchestrator Agent

* Điều phối workflow
* Quản lý các Agent
* Tổng hợp kết quả

Output

Execution Plan

---

### Query Understanding Agent

* Intent Detection
* Query Rewrite
* Keyword Extraction
* Topic Classification

Output

Structured Query

---

### Retrieval Agent

* Semantic Search
* Keyword Search
* Metadata Filter
* Hybrid Retrieval
* Top-k Retrieval

Output

Relevant Legal Chunks

---

### Policy Analysis Agent

* Đọc điều khoản
* Phân tích quy định
* Xác định điều kiện
* Phát hiện ngoại lệ
* Tổng hợp nội dung

Output

Policy Summary

---

### Citation Validation Agent

* Evidence Checking
* Citation Validation
* Hallucination Detection

Output

Validated Context

---

# Module 4. Response Generation

### Mục tiêu

Sinh câu trả lời cuối cùng.

### Workflow

```text
Validated Context
        ↓
LLM
        ↓
Response Agent
        ↓
Final Answer
```

### Output

* Answer
* Related Policy
* Relevant Articles
* Citation
* Confidence Score
* Suggested Actions

---

# Tổng quan Input / Output

| Module                    | Input                    | Output                                             |
| ------------------------- | ------------------------ | -------------------------------------------------- |
| **Knowledge Processing**  | PDF, Quy chế, Chính sách | Structured Text, Legal Chunks, Metadata            |
| **Knowledge Indexing**    | Legal Chunks             | Embeddings, FAISS Vector DB                        |
| **Multi-Agent Retrieval** | User Question            | Relevant Chunks, Policy Summary, Validated Context |
| **Response Generation**   | Validated Context        | Final Answer, Citation, Confidence Score           |

---

# Workflow End-to-End

```text
                OFFLINE

University Policy PDF
        │
        ▼
Knowledge Processing
(Document Parsing, Cleaning,
Legal Structure Detection,
Chunking)
        │
        ▼
Knowledge Indexing
(Embedding + FAISS)
        │
        ▼
Knowledge Base


                ONLINE

User Question
        │
        ▼
Orchestrator Agent
        │
        ▼
Query Understanding
        │
        ▼
Hybrid Retrieval
(FAISS + BM25 + Metadata)
        │
        ▼
Policy Analysis
        │
        ▼
Citation Validation
        │
        ▼
Response Generation
        │
        ▼
Answer + Citation + Confidence
```

