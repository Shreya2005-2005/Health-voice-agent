import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- API ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 1024
GROQ_TEMPERATURE = 0.7

# --- Whisper ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = "en"

# --- Paths ---
BASE_DIR = Path(__file__).parent
USER_DATA_DIR = Path(os.getenv("USER_DATA_DIR", "./user_data"))
CHROMA_DB_DIR = USER_DATA_DIR / "chroma_db"
PROFILES_DIR = USER_DATA_DIR / "profiles"

# Ensure directories exist
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

# --- Audio ---
SAMPLE_RATE = 16000
CHANNELS = 1
AUDIO_FORMAT_WIDTH = 2          # 16-bit PCM
CHUNK_DURATION_MS = 30          # VAD frame size in ms
SAMPLES_PER_FRAME = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 480 samples
SILENCE_FRAMES_THRESHOLD = 50   # ~1.5 s of silence triggers stop
SPEECH_FRAMES_THRESHOLD = 3     # frames of speech needed to start capture
VAD_AGGRESSIVENESS = 2          # 0-3; higher = stricter noise filtering
MAX_RECORDING_SECONDS = 30

# --- Memory ---
MAX_HISTORY_CONTEXT = 3         # past sessions to inject as context
CHROMA_COLLECTION_NAME = "health_sessions"

# --- Conversation ---
MAX_FOLLOW_UP_ROUNDS = 3

# --- Emergency / Safety ---
EMERGENCY_PHRASES = [
    "chest pain",
    "heart attack",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "shortness of breath",
    "trouble breathing",
    "stroke",
    "unconscious",
    "severe bleeding",
    "poisoning",
    "overdose",
    "suicidal",
    "want to die",
    "seizure",
    "loss of consciousness",
    "passed out",
    "paralysis",
    "severe chest",
    "crushing chest",
]

DISCLAIMER = (
    "These are general home remedies only. "
    "Please consult a doctor for proper medical advice, "
    "especially if symptoms persist or worsen."
)

EMERGENCY_RESPONSE = (
    "This sounds serious. Please call emergency services or visit a hospital immediately. "
    "Do not wait — your safety is the top priority."
)

# --- TTS ---
TTS_RATE = 175          # words per minute
TTS_VOLUME = 1.0
