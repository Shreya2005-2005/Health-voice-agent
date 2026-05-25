"""
FastAPI web server — serves the browser UI at http://localhost:8000
and exposes a JSON API for the health agent.
"""

from __future__ import annotations

import asyncio
import io
import os
import subprocess
import uuid
import wave
from pathlib import Path

import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from agents.health_agent import HealthAgent
from memory.session_manager import SessionManager
from utils.logger import setup_logger
from voice.stt import SpeechToText

logger = setup_logger(__name__)

app = FastAPI(title="Voice Health Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------------------------------------------------------------------
# Globals — initialised on startup
# ---------------------------------------------------------------------------
_stt: SpeechToText | None = None
_session_manager: SessionManager | None = None
_agent_sessions: dict[str, HealthAgent] = {}


@app.on_event("startup")
async def startup() -> None:
    global _stt, _session_manager
    logger.info("Starting up…")
    _session_manager = SessionManager()
    _stt = await asyncio.to_thread(SpeechToText)
    logger.info("Server ready")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/api/session/start")
async def start_session(name: str = Form(...)) -> dict:
    user = _session_manager.create_user(name.strip() or "Friend")
    session_id = str(uuid.uuid4())

    agent = HealthAgent(_session_manager)
    agent.set_user(user)
    _agent_sessions[session_id] = agent

    greeting = agent.start_conversation()
    logger.info(f"Session {session_id} started for {user['name']}")
    return {"session_id": session_id, "message": greeting, "user": user["name"]}


@app.post("/api/chat/audio")
async def chat_audio(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    agent = _get_agent(session_id)
    audio_bytes = await audio.read()

    audio_array = await asyncio.to_thread(_convert_audio, audio_bytes)
    if audio_array is None or len(audio_array) == 0:
        return {"transcription": "", "message": "Sorry, I couldn't process that audio. Please try again.", "is_done": False}

    transcription = await asyncio.to_thread(_stt.transcribe, audio_array)
    if not transcription or len(transcription.strip()) < 2:
        return {"transcription": "", "message": "I didn't catch that. Could you speak again?", "is_done": False}

    response = await asyncio.to_thread(agent.process_input, transcription)
    return {"transcription": transcription, "message": response, "is_done": agent.is_done()}


@app.post("/api/chat/text")
async def chat_text(
    session_id: str = Form(...),
    text: str = Form(...),
) -> dict:
    agent = _get_agent(session_id)
    response = await asyncio.to_thread(agent.process_input, text.strip())
    return {"transcription": text, "message": response, "is_done": agent.is_done()}


@app.post("/api/session/restart")
async def restart_session(session_id: str = Form(...)) -> dict:
    agent = _get_agent(session_id)
    agent._reset_session()
    agent._state = agent.STATE_COLLECTING
    msg = "Sure! What new symptoms or health concerns would you like to discuss?"
    agent._add_message("assistant", msg)
    return {"message": msg, "is_done": False}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_agent(session_id: str) -> HealthAgent:
    agent = _agent_sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found. Please refresh the page.")
    return agent


def _convert_audio(audio_bytes: bytes) -> np.ndarray | None:
    """
    Convert uploaded audio to a float32 numpy array at 16 kHz mono.

    Strategy (in order):
      1. Python's built-in `wave` module — works for WAV sent by the browser
         recorder (our preferred path; no FFmpeg needed).
      2. FFmpeg subprocess fallback — for WebM/Ogg/MP4 if FFmpeg is installed.
    """
    if not audio_bytes:
        logger.warning("Received empty audio bytes")
        return None

    # --- Path 1: native WAV (sent by our JS recorder) ---
    try:
        with wave.open(io.BytesIO(audio_bytes), "r") as wf:
            n_channels = wf.getnchannels()
            sampwidth  = wf.getsampwidth()
            frames     = wf.readframes(wf.getnframes())

        if sampwidth == 2:
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

        # Mix down to mono if needed
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

        logger.debug(f"WAV parsed: {len(audio)} samples")
        return audio
    except Exception as e:
        logger.debug(f"WAV parse failed ({e}), trying FFmpeg…")

    # --- Path 2: FFmpeg fallback for WebM / Ogg / MP4 ---
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-ar", "16000", "-ac", "1",
             "-f", "wav", "pipe:1", "-loglevel", "quiet"],
            input=audio_bytes,
            capture_output=True,
            timeout=30,
        )
        wav = result.stdout
        if len(wav) >= 44:
            audio = np.frombuffer(wav[44:], dtype=np.int16).astype(np.float32) / 32768.0
            logger.debug(f"FFmpeg converted: {len(audio)} samples")
            return audio
        logger.error(f"FFmpeg produced no output. stderr: {result.stderr[:200]}")
    except FileNotFoundError:
        logger.warning("FFmpeg not found — install it or use the browser WAV recorder")
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")

    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
