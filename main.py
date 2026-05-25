#!/usr/bin/env python3
"""
Voice Health Assistant — Terminal entry point.
On servers without audio hardware the script exits cleanly with a helpful
message instead of crashing. Use app.py for the web interface.
"""

import sys
import signal

from config import GROQ_API_KEY
from utils.logger import setup_logger
from memory.session_manager import SessionManager
from agents.health_agent import HealthAgent

logger = setup_logger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════╗
║           VOICE HEALTH ASSISTANT  (Medi)                 ║
║   Powered by Groq · faster-whisper · ChromaDB            ║
╚══════════════════════════════════════════════════════════╝
"""


def check_config() -> None:
    if not GROQ_API_KEY:
        print(
            "\n[ERROR] GROQ_API_KEY is not set.\n"
            "1. Copy .env.example → .env\n"
            "2. Add your free key from https://console.groq.com\n"
        )
        sys.exit(1)


def init_components():
    print("Initialising components…")

    session_manager = SessionManager()

    # TTS — optional, gracefully unavailable on server
    tts = None
    try:
        from voice.tts import TextToSpeech
        tts = TextToSpeech()
        status = "ready" if tts.available else "unavailable (no audio hardware)"
        print(f"  {'✓' if tts.available else '⚠'} TTS {status}")
    except Exception as e:
        logger.warning(f"TTS could not be loaded: {e}")
        print("  ⚠ TTS unavailable")

    # STT — required for terminal voice mode
    stt = None
    try:
        from voice.stt import SpeechToText
        stt = SpeechToText()
        print("  ✓ STT (Whisper) ready")
    except Exception as e:
        logger.error(f"STT failed to load: {e}")
        print(f"  ✗ STT unavailable: {e}")

    # Recorder — optional, unavailable on server
    recorder = None
    try:
        from voice.recorder import AudioRecorder
        recorder = AudioRecorder()
        status = "ready" if recorder.available else "unavailable (no audio hardware)"
        print(f"  {'✓' if recorder.available else '⚠'} Recorder {status}")
    except Exception as e:
        logger.warning(f"Recorder could not be loaded: {e}")
        print("  ⚠ Recorder unavailable")

    agent = HealthAgent(session_manager, tts)
    print("  ✓ Health agent ready\n")

    return session_manager, tts, stt, recorder, agent


def main():
    print(BANNER)
    check_config()

    session_manager, tts, stt, recorder, agent = init_components()

    # If mic recording is unavailable, the terminal loop cannot function —
    # but the web server (app.py) will work fine.
    if recorder is None or not recorder.available:
        print(
            "┌─────────────────────────────────────────────────────┐\n"
            "│  No microphone detected — starting web server.      │\n"
            "│  Visit the URL shown below to use the app.          │\n"
            "└─────────────────────────────────────────────────────┘"
        )
        import subprocess
        subprocess.run([sys.executable, "app.py"])

    user = session_manager.get_or_create_user()
    agent.set_user(user)

    def _speak(text: str):
        if tts:
            tts.speak(text)

    def shutdown(sig=None, frame=None):
        print("\n\nShutting down…")
        agent.save_current_session()
        _speak("Goodbye! Take care of your health.")
        recorder.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    greeting = agent.start_conversation()
    print(f"\nMedi: {greeting}\n")
    _speak(greeting)

    while not agent.is_done():
        try:
            print("[Listening… speak now | Ctrl+C to exit]")
            audio = recorder.record()

            if audio is None or len(audio) == 0:
                print("[No audio captured — try again]")
                continue

            if stt is None:
                print("[STT unavailable — cannot transcribe]")
                continue

            user_text = stt.transcribe(audio)

            if not user_text or len(user_text.strip()) < 2:
                print("[Could not understand — please speak again]")
                _speak("Sorry, I didn't catch that. Could you say it again?")
                continue

            print(f"\nYou:  {user_text}")
            response = agent.process_input(user_text)
            print(f"Medi: {response}\n")
            _speak(response)

        except KeyboardInterrupt:
            shutdown()
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
            print(f"[Error] {e}")
            _speak("Something went wrong. Let's continue — what were you saying?")

    print("\nThank you for using Voice Health Assistant. Stay healthy!\n")


if __name__ == "__main__":
    main()
