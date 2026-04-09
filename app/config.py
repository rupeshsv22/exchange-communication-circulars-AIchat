from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "nse_rag"
    mongo_collection: str = "circulars"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "nse_circulars"
    vector_size: int = 384

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # NSE
    nse_circulars_url: str = "https://www.nseindia.com/api/circulars"
    nse_base_url: str = "https://www.nseindia.com"

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 100

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
