import numpy as np
from utils.logger import setup_logger
from config import WHISPER_MODEL, WHISPER_LANGUAGE, SAMPLE_RATE

logger = setup_logger(__name__)


class SpeechToText:
    """
    Wraps faster-whisper for audio transcription.
    Requires no microphone hardware — works on any server.
    Raises on init if the model cannot be loaded.
    """

    def __init__(self):
        logger.info(f"Loading Whisper model '{WHISPER_MODEL}'...")
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded")
        except ImportError:
            logger.error("faster-whisper not installed — add it to requirements")
            raise
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe a float32 numpy audio array sampled at SAMPLE_RATE.
        Returns the transcribed string, or empty string on failure.
        """
        if audio is None or len(audio) == 0:
            return ""
        try:
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            if audio.max() > 1.0:
                audio = audio / 32768.0

            segments, _ = self._model.transcribe(
                audio,
                language=WHISPER_LANGUAGE,
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(seg.text for seg in segments).strip()
            logger.debug(f"Transcribed: {text!r}")
            return text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
