import re
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().isoformat()


def now_display() -> str:
    return datetime.now().strftime("%B %d, %Y at %I:%M %p")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", text.lower().strip())[:50]


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def truncate(text: str, max_chars: int = 300) -> str:
    return text if len(text) <= max_chars else text[:max_chars] + "…"


def format_session_summary(session: dict) -> str:
    date = session.get("date", "Unknown date")
    symptoms = ", ".join(session.get("symptoms", []))
    remedies = "; ".join(session.get("remedies", [])[:2])
    return f"[{date}] Symptoms: {symptoms}. Remedies: {remedies}."
