from config import EMERGENCY_PHRASES
from utils.logger import setup_logger

logger = setup_logger(__name__)

SEVERITY_KEYWORDS = {
    "severe": ["severe", "extreme", "unbearable", "worst", "excruciating", "crushing", "intense"],
    "moderate": ["moderate", "significant", "bad", "strong", "constant", "persistent"],
    "mild": ["mild", "slight", "little", "bit", "minor", "occasional"],
}


def check_emergency(text: str) -> bool:
    """Return True if the text contains any emergency phrase."""
    lowered = text.lower()
    for phrase in EMERGENCY_PHRASES:
        if phrase in lowered:
            logger.warning(f"Emergency phrase detected: '{phrase}'")
            return True
    return False


def estimate_severity(text: str) -> str:
    """Return 'severe', 'moderate', or 'mild' based on keywords."""
    lowered = text.lower()
    for level in ("severe", "moderate", "mild"):
        for kw in SEVERITY_KEYWORDS[level]:
            if kw in lowered:
                return level
    return "mild"


def extract_duration_hint(text: str) -> str | None:
    """Extract simple duration mentions from text."""
    import re
    patterns = [
        r"\b(\d+)\s*(day|days|week|weeks|month|months|hour|hours|minute|minutes)\b",
        r"\b(yesterday|today|this morning|last night|a few days|a week)\b",
        r"\b(since\s+\w+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None
