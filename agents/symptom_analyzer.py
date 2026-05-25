import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from utils.logger import setup_logger

logger = setup_logger(__name__)

EXTRACT_SYSTEM = """You are a medical symptom extractor.
Given user text, extract a clean JSON list of symptoms mentioned.
Normalise each symptom to a concise English phrase (e.g. "sore throat", "mild fever").
Respond ONLY with a valid JSON array of strings, nothing else.
Example: ["headache", "runny nose", "mild fever"]
If no symptoms are found, respond with an empty array: []"""

# Keyword fallback — used when the LLM call fails or returns nothing
_KEYWORD_MAP = {
    "headache":     ["headache", "head ache", "head pain", "migraine", "head hurts", "my head hurts", "head is pounding"],
    "fever":        ["fever", "high temperature", "feverish", "chills", "i'm burning", "burning up"],
    "sore throat":  ["sore throat", "throat pain", "throat hurts", "throat ache", "scratchy throat"],
    "cough":        ["cough", "coughing", "dry cough", "wet cough", "keep coughing"],
    "cold":         ["common cold", "runny nose", "stuffy nose", "congestion", "sneezing", "blocked nose"],
    "nausea":       ["nausea", "nauseous", "feel sick", "want to vomit", "going to throw up"],
    "vomiting":     ["vomit", "vomiting", "threw up", "throw up"],
    "stomach pain": ["stomach", "stomachache", "stomach pain", "abdominal", "belly pain", "tummy"],
    "back pain":    ["back pain", "backache", "back hurts", "lower back", "upper back"],
    "fatigue":      ["tired", "fatigue", "exhausted", "no energy", "weak", "weakness", "lethargic"],
    "dizziness":    ["dizzy", "dizziness", "lightheaded", "spinning", "vertigo"],
    "body ache":    ["body ache", "body pain", "muscle pain", "muscle ache", "aching all over"],
    "chest pain":   ["chest pain", "chest hurts", "chest tightness"],
    "shortness of breath": ["shortness of breath", "can't breathe", "hard to breathe", "difficulty breathing"],
    "rash":         ["rash", "itchy skin", "skin rash", "hives", "itching"],
    "eye pain":     ["eye pain", "eyes hurt", "red eyes", "eye strain"],
    "ear pain":     ["ear pain", "earache", "ear hurts"],
    "joint pain":   ["joint pain", "joint ache", "knee pain", "knee hurts", "hip pain"],
}


def _keyword_extract(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for symptom, keywords in _KEYWORD_MAP.items():
        if any(kw in lower for kw in keywords):
            found.append(symptom)
    return found


def extract_symptoms(text: str) -> list[str]:
    """Extract symptoms via LLM; fall back to keyword matching on any failure."""
    if not text or not text.strip():
        return []

    # Try LLM first
    if GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": EXTRACT_SYSTEM},
                    {"role": "user", "content": text},
                ],
                max_tokens=256,
                temperature=0.1,
            )
            raw = completion.choices[0].message.content.strip()
            # Strip markdown code fences if present
            raw = raw.strip("`").lstrip("json").strip()
            symptoms = json.loads(raw)
            if isinstance(symptoms, list) and symptoms:
                return [str(s).lower().strip() for s in symptoms if s]
        except json.JSONDecodeError as e:
            logger.warning(f"Symptom JSON parse failed: {e}")
        except Exception as e:
            logger.warning(f"LLM symptom extraction failed ({e}), using keyword fallback")

    # Keyword fallback
    found = _keyword_extract(text)
    if found:
        logger.info(f"Keyword fallback found: {found}")
    return found
