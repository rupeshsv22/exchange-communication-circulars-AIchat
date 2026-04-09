# NSE Circulars RAG API

A production-ready Retrieval-Augmented Generation (RAG) system that fetches NSE (National Stock Exchange of India) circulars, processes their PDFs, stores embeddings in a vector database, and answers natural-language queries using a local LLM.

---

## How It Works

```
                        ┌─────────────┐
                        │  NSE API    │
                        └──────┬──────┘
                               │ fetch circulars (JSON)
                               ▼
                        ┌─────────────┐
              upsert    │   MongoDB   │  metadata store
            ──────────► │  circulars  │  (circNumber, subject, date, file link)
                        └─────────────┘
                               │ download PDF / ZIP
                               ▼
                   ┌───────────────────────┐
                   │  pypdf  text extract  │
                   │  + 500-char chunking  │
                   └───────────┬───────────┘
                               │ embed (all-MiniLM-L6-v2)
                               ▼
                        ┌─────────────┐
                        │   Qdrant    │  vector store
                        │nse_circulars│  384-dim cosine
                        └─────────────┘

  Query Flow
  ──────────
  GET /ask?q=...
       │
       ├─ circular number in query? ──► Qdrant payload filter ──► DETAIL prompt
       │
       └─ topic query? ──────────────► vector search (top-k) ──► BRIEF prompt
                                               │
                                               ▼
                                       Ollama (llama3)
                                               │
                                               ▼
                                    { answer, sources }
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| Vector database | Qdrant |
| Document database | MongoDB (pymongo) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (384-dim) |
| LLM | Ollama `llama3` (local, no internet) |
| PDF / ZIP parsing | pypdf + zipfile |
| HTTP client | httpx (with retry + backoff) |
| Settings | pydantic-settings (`.env` driven) |
| Logging | structlog (structured JSON-style) |

---

## Prerequisites

Before running the API, make sure these three services are up:

### 1. MongoDB
```bash
# Docker (recommended)
docker run -d --name mongodb -p 27017:27017 mongo:7
```

### 2. Qdrant
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### 3. Ollama + llama3
```bash
# Install Ollama from https://ollama.com/download
ollama pull llama3      # downloads ~4.7 GB model
ollama serve            # starts API on localhost:11434
```

---

## Setup & Run

```bash
# 1. Clone the repo
git clone <repo-url>
cd circulars-ai

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / Mac
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment config (defaults work for local dev)
cp .env.example .env

# 5. Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API is now live at: http://localhost:8000
Interactive docs at: http://localhost:8000/docs

---

## API Reference

### Health Check

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok" }
```

---

### POST /ingest — Ingest NSE Circulars

Fetches the latest circulars from NSE, stores metadata in MongoDB, downloads PDFs, extracts text, chunks, embeds, and stores in Qdrant.

- Skips circulars already embedded (idempotent — safe to re-run)
- If a PDF fails to download, a metadata-only chunk is stored so the circular is still searchable

```bash
curl -X POST http://localhost:8000/ingest
```

**Response:**
```json
{
  "status": "ok",
  "total_fetched": 80,
  "new_in_mongo": 78,
  "skipped_already_embedded": 2,
  "processed": 65,
  "failed": 15,
  "total_chunks": 473
}
```

| Field | Description |
|---|---|
| `total_fetched` | Circulars received from NSE API |
| `new_in_mongo` | Newly inserted into MongoDB |
| `skipped_already_embedded` | Already in Qdrant, skipped |
| `processed` | Successfully chunked and embedded |
| `failed` | PDF download/parse failed (metadata chunk stored instead) |
| `total_chunks` | Total Qdrant points created |

---

### GET /ask — Query Circulars (RAG)

Ask a natural-language question. The system automatically detects whether the query is:
- A **topic search** → semantic vector search, brief bullet-point answer
- A **specific circular lookup** (contains a number like `73669`) → exact Qdrant filter, full structured answer

**Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `q` | string | required | Your question |
| `top_k` | integer | 5 | Number of chunks to retrieve (1–20) |

#### Topic queries

```bash
curl "http://localhost:8000/ask?q=What+are+the+latest+surveillance+measures?"
```

```bash
curl "http://localhost:8000/ask?q=Settlement+holiday+circular&top_k=3"
```

```bash
curl "http://localhost:8000/ask?q=Which+stocks+moved+from+BE+to+EQ+series?"
```

**Response:**
```json
{
  "answer": "• ST-ASM surveillance applied to XYZ Ltd shares [NSE(73679)]\n• ABC Ltd transferred from BE to EQ series [NSE(73635)]",
  "sources": [
    "NSE/CIRCULAR/73679",
    "NSE/CIRCULAR/73635"
  ]
}
```

#### Circular number lookup

```bash
curl "http://localhost:8000/ask?q=give+complete+details+of+73669"
```

```bash
curl "http://localhost:8000/ask?q=what+is+circular+73645+about?"
```

**Response:**
```json
{
  "answer": "Circular No   : 73669\nRef No        : NSE/NMFTM/73669 / 1319/2026\nDate          : April 09, 2026\nDepartment    : NMF TM Segment\nSubject       : Launch of Sapphire Equity Long-Short SIF NFO on NSE MF Invest Platform\nDetails       : Sapphire Equity Long-Short SIF NFO available April 10–24, 2026. Six schemes listed with ISINs. Clear funds deadline: April 29, 2026 10:00 AM.\nIssued By     : Milton Dias (AVP), Sagar Vaidya (Senior Manager)\nSource        : NSE(73669)",
  "sources": [
    "NSE/CIRCULAR/73669"
  ]
}
```

---

### DELETE /admin/clean — Wipe All Data

Deletes all documents from MongoDB and drops + recreates the Qdrant collection. **Irreversible.**

```bash
curl -X DELETE http://localhost:8000/admin/clean
```

**Response:**
```json
{
  "status": "ok",
  "mongo_deleted": 80,
  "qdrant_collection_recreated": true
}
```

---

## Typical Workflow

```bash
# Step 1 — start all services (MongoDB, Qdrant, Ollama)

# Step 2 — start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Step 3 — ingest circulars (run once; re-run any time to fetch new ones)
curl -X POST http://localhost:8000/ingest

# Step 4 — query
curl "http://localhost:8000/ask?q=What+are+the+margin+requirements+for+derivatives?"
curl "http://localhost:8000/ask?q=details+of+circular+73669"

# Step 5 — if you want a clean slate
curl -X DELETE http://localhost:8000/admin/clean
curl -X POST http://localhost:8000/ingest
```

---

## Project Structure

```
circulars-ai/
├── app/
│   ├── main.py                  # FastAPI app entry, lifespan hooks
│   ├── config.py                # All settings via pydantic-settings + .env
│   ├── routes/
│   │   ├── ingest.py            # POST /ingest
│   │   ├── query.py             # GET /ask  (topic search + circular lookup)
│   │   └── admin.py             # DELETE /admin/clean
│   ├── services/
│   │   ├── nse.py               # NSE API fetch, browser headers, deduplication
│   │   ├── pdf.py               # Download PDF/ZIP, extract text, retry logic
│   │   ├── chunker.py           # 500-char chunks with 100-char overlap
│   │   ├── embedder.py          # all-MiniLM-L6-v2, model cached via lru_cache
│   │   ├── qdrant_service.py    # Store chunks, vector search, circular filter lookup
│   │   ├── ollama.py            # Ollama API, BRIEF + DETAIL prompt templates
│   │   └── ingest.py            # Full pipeline orchestration
│   ├── db/
│   │   └── mongo.py             # Upsert, exists check, mark embedded
│   └── utils/
│       └── logger.py            # structlog setup
├── .env.example                 # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Configuration

All values can be set in `.env` or as environment variables:

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `nse_rag` | Database name |
| `MONGO_COLLECTION` | `circulars` | Collection name |
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `nse_circulars` | Qdrant collection name |
| `VECTOR_SIZE` | `384` | Embedding dimension (must match model) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Model name |
| `NSE_CIRCULARS_URL` | `https://www.nseindia.com/api/circulars` | NSE API endpoint |
| `CHUNK_SIZE` | `500` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between consecutive chunks |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace sentence-transformer model |

---

## Key Design Decisions

**Idempotent ingestion** — MongoDB stores an `embedded: true` flag once a circular is fully processed. Re-running `/ingest` skips it automatically.

**ZIP support** — NSE serves many circulars as `.zip` archives. The PDF service detects the `PK\x03\x04` magic header and unwraps the PDF transparently.

**Retry on download failures** — 3 attempts with 2s → 5s → 10s backoff for transient DNS/connection errors. Only retries on network errors, not HTTP 4xx/5xx.

**Metadata fallback chunk** — When a PDF cannot be downloaded, a plain-text chunk is built from the circular's metadata (subject, date, department, file link) and stored in Qdrant anyway. Every circular is always searchable.

**Dual query modes** — Queries containing a 4–6 digit number trigger an exact Qdrant payload filter and a structured DETAIL prompt. Topic queries use semantic vector search and a brief bullet-point prompt.

**Embedding cache** — The sentence-transformer model is loaded once via `@lru_cache` and reused across all requests.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `502 Vector search error` | Qdrant not running | `docker start qdrant` |
| `502 Ollama unavailable` | Ollama not running | `ollama serve` |
| `llama runner process terminated` | OOM — context too large | Reduce `top_k` or restart Ollama |
| `No relevant circular found` | Circular not yet ingested | Run `POST /ingest` |
| PDF `invalid header` warning | File is a ZIP, not PDF | Handled automatically (ZIP unwrap) |
| `getaddrinfo failed` on download | Transient DNS failure | Auto-retried 3 times |
