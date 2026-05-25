import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL, DISCLAIMER
from tools.remedy_finder import find_remedies
from utils.logger import setup_logger

logger = setup_logger(__name__)

REMEDY_SYSTEM = f"""You are a caring, concise health assistant named Medi.
Give a SHORT, conversational response — plain sentences only, NO markdown, NO headers, NO bullet points, NO bold text.

Structure (3 short paragraphs max):
1. One sentence naming 2-3 possible causes.
2. Two or three sentences describing the most helpful home remedies to try right now.
3. One sentence: when to see a doctor + the disclaimer: "{DISCLAIMER}"

Keep the whole response under 80 words. Speak like a knowledgeable friend, not a medical report.
NEVER diagnose definitively. NEVER use markdown formatting of any kind."""


def generate_diagnosis(
    symptoms: list[str],
    conversation_history: list[dict],
    history_context: str = "",
) -> tuple[str, list[str], list[str]]:
    """
    Generate causes + remedies using the LLM.
    Returns (full_response_text, causes_list, remedies_list).
    """
    client = Groq(api_key=GROQ_API_KEY)

    # Seed with KB data if available
    kb_data = find_remedies(symptoms)
    kb_hint = ""
    if kb_data:
        kb_hint = (
            f"\n\n[Reference data for {kb_data['matched_on']}]\n"
            f"Common causes: {', '.join(kb_data['causes'])}\n"
            f"Common remedies: {', '.join(kb_data['remedies'][:3])}"
        )

    system_with_kb = REMEDY_SYSTEM + kb_hint

    messages = [{"role": "system", "content": system_with_kb}]

    if history_context:
        messages.append({
            "role": "system",
            "content": f"Patient's past health history for context:\n{history_context}",
        })

    messages.extend(conversation_history)
    messages.append({
        "role": "user",
        "content": (
            f"I've told you all my symptoms. Symptoms summary: {', '.join(symptoms)}. "
            "Please give me your assessment with possible causes and home remedies."
        ),
    })

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.6,
        )
        response = completion.choices[0].message.content.strip()

        # Best-effort extraction of structured lists for storage
        causes = _extract_list(response, ["cause", "reason", "may be due"])
        remedies = _extract_list(response, ["remedy", "remedies", "try", "recommend"])
        return response, causes, remedies

    except Exception as e:
        logger.error(f"Remedy generation error: {e}")
        fallback = (
            "Based on what you've told me, here are some general suggestions.\n\n"
            "Please rest, stay hydrated, and monitor your symptoms.\n\n"
            f"{DISCLAIMER}"
        )
        return fallback, [], []


def _extract_list(text: str, keywords: list[str]) -> list[str]:
    """Very simple extraction: grab bullet/numbered lines near keywords."""
    import re
    lines = text.splitlines()
    results = []
    capture = False
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            capture = True
        if capture:
            # Grab lines that look like list items
            m = re.match(r"^\s*[-•*\d]+[.)]\s*(.+)", line)
            if m:
                results.append(m.group(1).strip())
            if len(results) >= 5:
                break
    return results
