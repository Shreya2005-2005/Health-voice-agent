import threading
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not available — TTS will print to console only (expected on server)")
except Exception as e:
    _PYTTSX3_AVAILABLE = False
    logger.warning(f"pyttsx3 import failed ({e}) — TTS unavailable")

try:
    from config import TTS_RATE, TTS_VOLUME
except Exception:
    TTS_RATE = 175
    TTS_VOLUME = 1.0


class TextToSpeech:
    def __init__(self):
        self._lock = threading.Lock()
        self._engine = None
        self._available = False
        self._init_engine()

    def _init_engine(self):
        if not _PYTTSX3_AVAILABLE:
            return
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", TTS_RATE)
            self._engine.setProperty("volume", TTS_VOLUME)
            voices = self._engine.getProperty("voices")
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    self._engine.setProperty("voice", v.id)
                    break
            self._available = True
            logger.info("TTS engine initialized")
        except Exception as e:
            logger.warning(f"TTS init failed ({e}) — voice output unavailable (expected on server)")
            self._engine = None

    def speak(self, text: str) -> None:
        """Speak text synchronously. Silently prints on server where TTS is unavailable."""
        if not text:
            return
        if not self._available or self._engine is None:
            logger.debug(f"[TTS] {text}")
            return
        try:
            with self._lock:
                self._engine.say(text)
                self._engine.runAndWait()
        except Exception as e:
            logger.warning(f"TTS speak error: {e}")

    def speak_async(self, text: str) -> threading.Thread:
        """Speak in a background thread; returns the thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    @property
    def available(self) -> bool:
        return self._available
