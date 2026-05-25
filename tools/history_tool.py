from memory.health_memory import retrieve_relevant_history, get_all_sessions
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_relevant_history(user_id: str, current_symptoms: list[str]) -> str:
    """
    Fetch and format the most relevant past sessions for LLM context.
    Returns an empty string if there is no history.
    """
    history = retrieve_relevant_history(user_id, current_symptoms)
    if history:
        logger.debug(f"Injecting history context for user {user_id}")
    return history


def get_session_count(user_id: str) -> int:
    return len(get_all_sessions(user_id))
