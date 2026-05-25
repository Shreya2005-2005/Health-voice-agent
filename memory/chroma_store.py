from __future__ import annotations

import chromadb
from config import CHROMA_DB_DIR, CHROMA_COLLECTION_NAME
from utils.logger import setup_logger

logger = setup_logger(__name__)

_client = None
_collection = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        logger.info(f"ChromaDB client initialised at {CHROMA_DB_DIR}")
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' ready")
    return _collection
