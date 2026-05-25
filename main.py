#!/usr/bin/env python3
"""
Voice Health Assistant — Entry Point
"""

import sys
import signal

from config import GROQ_API_KEY
from utils.logger import setup_logger
from memory.session_manager import SessionManager
from agents.health_agent import HealthAgent
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.recorder import AudioRecorder

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
    tts = TextToSpeech()

    print("  ✓ TTS ready")
    stt = SpeechToText()
    print("  ✓ STT (Whisper) ready")
    recorder = AudioRecorder()
    print("  ✓ Audio recorder ready")
    agent = HealthAgent(session_manager, tts)
    print("  ✓ Health agent ready\n")
    return session_manager, tts, stt, recorder, agent


def main():
    print(BANNER)
    check_config()

    try:
        session_manager, tts, stt, recorder, agent = init_components()
    except Exception as e:
        logger.error(f"Init failed: {e}")
        print(f"\n[Init error] {e}")
        print("Make sure all dependencies are installed:  pip install -r requirements.txt")
        sys.exit(1)

    user = session_manager.get_or_create_user()
    agent.set_user(user)

    # ----- Graceful shutdown -----
    def shutdown(sig=None, frame=None):
        print("\n\nShutting down…")
        agent.save_current_session()
        tts.speak("Goodbye! Take care of your health.")
        recorder.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # ----- Start conversation -----
    greeting = agent.start_conversation()
    print(f"\nMedi: {greeting}\n")
    tts.speak(greeting)

    # ----- Main loop -----
    while not agent.is_done():
        try:
            print("[Listening… speak now | Ctrl+C to exit]")
            audio = recorder.record()

            if audio is None or len(audio) == 0:
                print("[No audio captured — try again]")
                continue

            user_text = stt.transcribe(audio)

            if not user_text or len(user_text.strip()) < 2:
                print("[Could not understand — please speak again]")
                tts.speak("Sorry, I didn't catch that. Could you say it again?")
                continue

            print(f"\nYou:  {user_text}")

            response = agent.process_input(user_text)

            print(f"Medi: {response}\n")
            tts.speak(response)

        except KeyboardInterrupt:
            shutdown()
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
            msg = "Something went wrong on my end. Let's continue — what were you saying?"
            print(f"[Error] {e}")
            tts.speak(msg)

    print("\nThank you for using Voice Health Assistant. Stay healthy!\n")


if __name__ == "__main__":
    main()
