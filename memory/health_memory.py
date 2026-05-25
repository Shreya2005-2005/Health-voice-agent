import uuid
from datetime import datetime
from typing import Optional
from memory.chroma_store import get_collection
from utils.helpers import now_iso, format_session_summary
from utils.logger import setup_logger
from config import MAX_HISTORY_CONTEXT

logger = setup_logger(__name__)


def store_session(
    user_id: str,
    symptoms: list[str],
    causes: list[str],
    remedies: list[str],
    conversation_summary: str,
) -> str:
    """Persist a health session; returns the session ID."""
    collection = get_collection()
    session_id = str(uuid.uuid4())
    date_str = datetime.now().strftime("%B %d, %Y")

    doc_text = (
        f"Date: {date_str}\n"
        f"Symptoms: {', '.join(symptoms)}\n"
        f"Possible causes: {', '.join(causes)}\n"
        f"Remedies: {', '.join(remedies)}\n"
        f"Summary: {conversation_summary}"
    )

    collection.add(
        documents=[doc_text],
        ids=[session_id],
        metadatas=[{
            "user_id": user_id,
            "date": now_iso(),
            "symptoms": "|".join(symptoms),
            "causes": "|".join(causes),
            "remedies": "|".join(remedies),
        }],
    )
    logger.info(f"Session {session_id} stored for user {user_id}")
    return session_id


def retrieve_relevant_history(user_id: str, current_symptoms: list[str]) -> str:
    """
    Query ChromaDB for sessions that are semantically similar to the current
    symptoms. Returns a formatted string ready for LLM context injection.
    """
    if not current_symptoms:
        return ""

    collection = get_collection()
    query_text = "Symptoms: " + ", ".join(current_symptoms)

    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=MAX_HISTORY_CONTEXT,
            where={"user_id": user_id},
        )
    except Exception as e:
        logger.warning(f"History query failed: {e}")
        return ""

    docs = results.get("documents", [[]])[0]
    if not docs:
        return ""

    lines = ["=== Relevant Past Health Sessions ==="]
    for i, doc in enumerate(docs, 1):
        lines.append(f"\n[Session {i}]\n{doc}")
    lines.append("=== End of Past Sessions ===")
    return "\n".join(lines)


def get_all_sessions(user_id: str) -> list[dict]:
    """Return all sessions for a user, sorted newest-first."""
    collection = get_collection()
    try:
        result = collection.get(where={"user_id": user_id})
        sessions = []
        for doc, meta in zip(result["documents"], result["metadatas"]):
            sessions.append({"document": doc, **meta})
        sessions.sort(key=lambda s: s.get("date", ""), reverse=True)
        return sessions
    except Exception as e:
        logger.warning(f"Failed to fetch sessions: {e}")
        return []
