from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import setup_logger

logger = setup_logger(__name__)

FOLLOWUP_SYSTEM = """You are an empathetic health assistant collecting information about a patient's symptoms.
Based on the symptoms provided, ask ONE clear, focused follow-up question to better understand the condition.
Prioritise asking about: duration, severity (1-10 scale), location, what makes it better/worse, associated symptoms.
Keep the question short and conversational. Do NOT give any diagnosis yet."""


def generate_followup(symptoms: list[str], conversation_history: list[dict], round_number: int) -> str:
    """Generate a targeted follow-up question for the given symptoms."""
    client = Groq(api_key=GROQ_API_KEY)

    symptom_summary = ", ".join(symptoms) if symptoms else "unspecified symptoms"
    user_msg = (
        f"Patient symptoms so far: {symptom_summary}. "
        f"This is follow-up question number {round_number}. "
        "Ask ONE concise follow-up question."
    )

    messages = [{"role": "system", "content": FOLLOWUP_SYSTEM}]
    # Include last 4 turns for context
    messages.extend(conversation_history[-4:])
    messages.append({"role": "user", "content": user_msg})

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Follow-up generation error: {e}")
        fallback_questions = [
            "How long have you been experiencing these symptoms?",
            "On a scale of 1 to 10, how severe would you say the discomfort is?",
            "Do you have any other symptoms along with this?",
        ]
        idx = min(round_number - 1, len(fallback_questions) - 1)
        return fallback_questions[idx]
