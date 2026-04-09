# 📊 NSE Circular Intelligence API (RAG System)

A production-ready **Retrieval-Augmented Generation (RAG)** system that ingests NSE circulars, processes PDF content, and enables intelligent querying using a local LLM.

---

## 🚀 Features

* 📡 Fetch latest circulars from NSE API
* 📄 Download and process PDF circulars
* 🧠 Extract and chunk text intelligently
* 🔍 Semantic search using Qdrant (Vector DB)
* 🗄️ Metadata storage in MongoDB
* 🤖 LLM-powered answers using Ollama (LLaMA3)
* ⚡ FastAPI-based high-performance backend
* 🔁 Deduplication & efficient ingestion

---

## 🧠 Architecture

```
NSE API
   ↓
FastAPI Backend
   ↓
PDF Downloader + Text Extractor
   ↓
Chunking + Embeddings
   ↓
Qdrant (Vector DB) ←→ MongoDB (Metadata)
   ↓
Query API
   ↓
Ollama (LLM)
   ↓
Final Answer
```

---

## 🛠️ Tech Stack

| Layer            | Technology            |
| ---------------- | --------------------- |
| Backend          | FastAPI               |
| Language         | Python                |
| Vector Database  | Qdrant                |
| Metadata Storage | MongoDB               |
| Embeddings       | sentence-transformers |
| LLM              | Ollama (LLaMA3)       |
| PDF Processing   | pypdf                 |

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-username/nse-rag-api.git
cd nse-rag-api
```

---

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Run MongoDB

```bash
mongod
```

---

### 4. Run Qdrant (Local)

```bash
qdrant.exe
```

---

### 5. Start Ollama

```bash
ollama run llama3
```

---

## ▶️ Run Application

```bash
uvicorn app.main:app --reload
```

API will be available at:

```
http://localhost:8000
```

---

## 📡 API Endpoints

### 🔹 Ingest NSE Circulars

```http
POST /ingest
```

**Description:**

* Fetches NSE circulars
* Stores metadata in MongoDB
* Processes PDFs
* Stores embeddings in Qdrant

---

### 🔹 Ask Questions (RAG)

```http
GET /ask?q=your_query
```

**Example:**

```bash
curl "http://localhost:8000/ask?q=listing of securities"
```

**Response:**

```json
{
  "answer": "Circular NSE/CML/73685 discusses listing of further issues...",
  "sources": ["73685"]
}
```

---

## 🧩 Project Structure

```
app/
├── main.py
├── config.py
├── routes/
│   ├── ingest.py
│   └── query.py
├── services/
│   ├── nse_service.py
│   ├── pdf_service.py
│   ├── embedding_service.py
│   └── rag_service.py
├── db/
│   ├── mongo.py
│   └── qdrant.py
└── utils/
    └── chunking.py
```

---

## 🧠 How It Works

1. NSE API provides circular metadata
2. PDFs are downloaded and parsed
3. Text is split into chunks (500 chars + overlap)
4. Each chunk is converted into embeddings
5. Stored in Qdrant with metadata
6. Query → embedding → similarity search
7. Relevant chunks passed to LLM
8. LLM generates contextual answer

---

## ⚡ Optimizations

* Deduplication using `circNumber`
* Chunk overlap for better context retention
* Batch embedding for performance
* Error handling for failed PDFs
* Metadata filtering in vector search

---

## 🔐 Environment Variables

Create `.env` file:

```
MONGO_URI=mongodb://localhost:27017
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_URL=http://localhost:11434
```

---

## 📌 Future Improvements

* 🕒 Scheduled ingestion (cron jobs)
* 🌐 React-based UI
* ☁️ Deployment on AWS/GCP
* 🔍 Advanced filtering (date, category)
* 📊 Dashboard for analytics

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first.

---

## 👨‍💻 Author

Rupesh Verma
