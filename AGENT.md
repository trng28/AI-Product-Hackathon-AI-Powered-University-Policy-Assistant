# Multi-Agent RAG MVP

## Setup

Use Python 3.11-3.13 because FAISS wheels may lag behind the newest Python
release.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure one provider in `.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
```

Supported providers are `openai`, `groq`, and `gemini`. Their keys are read
from `OPENAI_API_KEY`, `GROQ_API`, and `GEMINI_API_KEY`.

## Build the knowledge index

```powershell
python -m src.policy_assistant.cli index `
  "src/data/VU_HT03.VN_QC-dao-tao-dai-hoc-he-chinh-quy-theo-he-thong-tin-chi.pdf"
```

## Ask a question

```powershell
python -m src.policy_assistant.cli ask "Điều kiện bị cảnh báo học tập là gì?"
```

The output contains the grounded answer, validated article/page citations,
confidence score, evidence status, and interpreted query.

## Runtime workflow

```text
Question
  -> Query Understanding Agent
  -> Hybrid Retrieval Agent (FAISS semantic + keyword + article filter)
  -> Policy Analysis Agent
  -> Citation Validation Agent
  -> Response Agent
```

If analysis has no valid citation to a retrieved chunk, the response is
explicitly marked as insufficient evidence.

### Interactive CLI chat

```powershell
python -m src.policy_assistant.cli chat
```

Commands available in a chat session: `/help`, `/clear`, and `/exit`.

## Run the web application

Terminal 1 — FastAPI:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation is available at `http://127.0.0.1:8000/docs`.

Terminal 2 — React/Vite:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to FastAPI during local
development. For a separately deployed API, create `frontend/.env`:

```dotenv
VITE_API_BASE_URL=https://your-api.example.com
```

Available API endpoints:

- `GET /api/health`: provider, model, and index readiness.
- `POST /api/index`: build the FAISS index from the bundled PDF.
- `POST /api/ask`: execute the LangGraph agent workflow.

## Docker Compose

Create `.env` from the example and add the selected provider API key:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8080`. The frontend container serves the production
React build and proxies `/api` to FastAPI. Swagger remains available directly
at `http://localhost:8000/docs`.

The FAISS index and Hugging Face model cache use named volumes, so they survive
container recreation. To stop the application without deleting that data:

```powershell
docker compose down
```

To intentionally remove containers and both data volumes:

```powershell
docker compose down --volumes
```
