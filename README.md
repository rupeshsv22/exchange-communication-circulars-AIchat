# NSE Circulars RAG API

A production-ready Retrieval-Augmented Generation system for NSE (National Stock Exchange of India) circulars.

## Architecture

```
POST /ingest  →  NSE API → MongoDB (metadata) → PDF → Chunks → Embeddings → Qdrant
GET  /ask     →  Embed query → Qdrant search → Context → Ollama (llama3) → Answer
```

## Tech Stack

| Component | Library |
|---|---|
| API | FastAPI + Uvicorn |
| Vector DB | Qdrant |
| Document DB | MongoDB (pymongo) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Ollama (llama3, local) |
| PDF parsing | pypdf |
| HTTP client | httpx |
| Logging | structlog |

## Prerequisites

1. **MongoDB** running on `localhost:27017`
2. **Qdrant** running on `localhost:6333`
3. **Ollama** running on `localhost:11434` with `llama3` pulled:
   ```bash
   ollama pull llama3
   ollama serve
   ```

## Setup

```bash
# Clone and enter the repo
cd circulars-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and edit env file (defaults work for local dev)
cp .env.example .env

# Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health check
```bash
curl http://localhost:8000/health
```

### Ingest NSE circulars
```bash
curl -X POST http://localhost:8000/ingest
```

**Response:**
```json
{
  "status": "ok",
  "total_fetched": 50,
  "new_in_mongo": 48,
  "skipped_already_embedded": 2,
  "processed": 45,
  "failed": 3,
  "total_chunks": 1230
}
```

### Query (RAG)
```bash
curl "http://localhost:8000/ask?q=What+are+the+latest+margin+requirements?"
```

```bash
curl "http://localhost:8000/ask?q=Settlement+holiday+circular&top_k=3"
```

**Response:**
```json
{
  "answer": "Based on circular NSE/CLEARING/123, the settlement holiday...",
  "sources": ["NSE/CLEARING/123", "NSE/CLEARING/119"]
}
```

### Interactive docs
Open http://localhost:8000/docs in your browser.

## Project Structure

```
circulars-ai/
├── app/
│   ├── main.py              # FastAPI app, lifespan, router registration
│   ├── config.py            # Pydantic settings (env-driven)
│   ├── routes/
│   │   ├── ingest.py        # POST /ingest
│   │   └── query.py         # GET /ask
│   ├── services/
│   │   ├── nse.py           # NSE API fetch + deduplication
│   │   ├── pdf.py           # PDF download + text extraction
│   │   ├── chunker.py       # Text chunking (500 chars, 100 overlap)
│   │   ├── embedder.py      # sentence-transformers wrapper
│   │   ├── qdrant_service.py# Qdrant CRUD + search
│   │   ├── ollama.py        # Ollama HTTP client + prompt template
│   │   └── ingest.py        # Orchestration pipeline
│   ├── db/
│   │   └── mongo.py         # MongoDB upsert + state tracking
│   └── utils/
│       └── logger.py        # structlog configuration
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Configuration

All settings can be overridden via `.env` or environment variables:

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `nse_rag` | Database name |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `nse_circulars` | Collection name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Model to use |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model |

## Idempotency

- Re-running `/ingest` skips circulars already embedded (tracked in MongoDB via `embedded: true` flag).
- Qdrant uses `upsert` — re-uploading is safe.

## Docker (optional)

Start all dependencies with Docker:

```bash
# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# MongoDB
docker run -d -p 27017:27017 mongo:7
```
