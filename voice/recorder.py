import numpy as np
from utils.logger import setup_logger
from config import (
    SAMPLE_RATE, CHANNELS, AUDIO_FORMAT_WIDTH,
    SAMPLES_PER_FRAME, SILENCE_FRAMES_THRESHOLD,
    SPEECH_FRAMES_THRESHOLD, VAD_AGGRESSIVENESS,
    MAX_RECORDING_SECONDS,
)

logger = setup_logger(__name__)


class AudioRecorder:
    """
    Records audio using PyAudio with WebRTC VAD for silence detection.
    On servers with no audio hardware (Render, Railway, etc.) this class
    initialises without crashing — record() simply returns None.
    """

    def __init__(self):
        self._pa = None
        self._pyaudio = None
        self._vad = None
        self._use_webrtcvad = False
        self._available = False
        self._init_pyaudio()
        self._init_vad()

    # ------------------------------------------------------------------
    def _init_pyaudio(self):
        try:
            import pyaudio
            self._pyaudio = pyaudio
            self._pa = pyaudio.PyAudio()
            self._available = True
            logger.info("PyAudio initialized")
        except ImportError:
            logger.warning("pyaudio not installed — microphone recording unavailable (expected on server)")
        except Exception as e:
            logger.warning(f"PyAudio init failed ({e}) — microphone recording unavailable")

    def _init_vad(self):
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
            self._use_webrtcvad = True
            logger.info("WebRTC VAD initialized")
        except ImportError:
            logger.warning("webrtcvad not available — using energy-based VAD")
        except Exception as e:
            logger.warning(f"webrtcvad init error ({e}) — using energy-based VAD")

    # ------------------------------------------------------------------
    def _is_speech(self, frame_bytes: bytes) -> bool:
        if self._use_webrtcvad:
            try:
                return self._vad.is_speech(frame_bytes, SAMPLE_RATE)
            except Exception:
                pass
        arr = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(arr ** 2)))
        return rms > 300

    # ------------------------------------------------------------------
    def record(self) -> np.ndarray | None:
        """
        Block until the user speaks, then capture until silence.
        Returns a float32 numpy array at SAMPLE_RATE, or None if
        audio hardware is unavailable.
        """
        if not self._available or self._pa is None:
            logger.warning("Audio recording unavailable on this server")
            return None

        stream = self._pa.open(
            format=self._pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=SAMPLES_PER_FRAME,
        )

        frames: list[bytes] = []
        speech_frames = 0
        silence_frames = 0
        recording = False
        max_frames = int(MAX_RECORDING_SECONDS * 1000 / 30)

        logger.debug("Waiting for speech...")
        try:
            for _ in range(max_frames):
                frame = stream.read(SAMPLES_PER_FRAME, exception_on_overflow=False)
                is_speech = self._is_speech(frame)

                if is_speech:
                    speech_frames += 1
                    silence_frames = 0
                    if not recording and speech_frames >= SPEECH_FRAMES_THRESHOLD:
                        recording = True
                        logger.debug("Speech detected — recording started")
                else:
                    if recording:
                        silence_frames += 1
                        if silence_frames >= SILENCE_FRAMES_THRESHOLD:
                            logger.debug("Silence detected — recording stopped")
                            break
                    else:
                        speech_frames = 0

                if recording:
                    frames.append(frame)
        finally:
            stream.stop_stream()
            stream.close()

        if not frames:
            return None

        raw = b"".join(frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    @property
    def available(self) -> bool:
        return self._available

    def close(self):
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        self._available = False
