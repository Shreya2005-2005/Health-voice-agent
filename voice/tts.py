import threading
import pyttsx3
from config import TTS_RATE, TTS_VOLUME
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TextToSpeech:
    def __init__(self):
        self._lock = threading.Lock()
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", TTS_RATE)
            self._engine.setProperty("volume", TTS_VOLUME)
            # Prefer a female voice if available
            voices = self._engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    self._engine.setProperty("voice", v.id)
                    break
            logger.info("TTS engine initialized")
        except Exception as e:
            logger.error(f"TTS init failed: {e}")
            self._engine = None

    def speak(self, text: str) -> None:
        """Speak text synchronously (blocks until done)."""
        if not text:
            return
        if self._engine is None:
            print(f"[TTS unavailable] {text}")
            return
        try:
            with self._lock:
                self._engine.say(text)
                self._engine.runAndWait()
        except Exception as e:
            logger.warning(f"TTS speak error: {e}")
            print(f"[TTS error] {text}")

    def speak_async(self, text: str) -> threading.Thread:
        """Speak in a background thread; returns the thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t
