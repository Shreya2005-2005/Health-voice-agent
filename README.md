# Voice Health Assistant (Medi)

An agentic AI voice assistant where you speak your symptoms and receive intelligent follow-up questions, possible causes, and home remedies — with health history that persists across sessions.

**100% free to run — no paid APIs required.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│             (conversation loop + signals)               │
└──────────┬──────────────────────────────┬───────────────┘
           │                              │
    ┌──────▼──────┐               ┌───────▼──────┐
    │  Voice I/O  │               │  HealthAgent │  ◄── orchestrator
    │─────────────│               │──────────────│
    │ recorder.py │               │  state:      │
    │   stt.py    │               │  COLLECTING  │
    │   tts.py    │               │  FOLLOW_UP   │
    └─────────────┘               │  DIAGNOSING  │
          ▲                       │  SAVE_PROMPT │
          │ audio/text            └──────┬───────┘
          │                             │ calls
     ┌────┴────┐          ┌─────────────┼─────────────┐
     │  User   │          │             │             │
     └─────────┘   ┌──────▼──────┐ ┌───▼──────┐ ┌───▼──────────┐
                   │  symptom_   │ │ followup_│ │ remedy_agent │
                   │  analyzer   │ │  agent   │ │              │
                   └──────┬──────┘ └───┬──────┘ └──────┬───────┘
                          │            │               │
                          └────────────┼───────────────┘
                                       │ Groq API (llama-3.3-70b)
                    ┌──────────────────▼──────────────────┐
                    │            Memory Layer              │
                    │  ChromaDB  ·  JSON profiles          │
                    │  health_memory · session_manager     │
                    └──────────────────────────────────────┘
```

---

## Tech Stack

| Component | Library | Cost |
|-----------|---------|------|
| LLM | [Groq](https://console.groq.com) — `llama-3.3-70b-versatile` | Free tier |
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (local) | Free |
| Text-to-Speech | [pyttsx3](https://pyttsx3.readthedocs.io) (local) | Free |
| Vector Memory | [ChromaDB](https://www.trychroma.com) (local) | Free |
| Voice Activity Detection | [webrtcvad](https://github.com/wiseman/py-webrtcvad) (local) | Free |
| Audio Recording | [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) (local) | Free |

---

## Setup

### 1. Prerequisites

- Python 3.10 or newer
- [FFmpeg](https://ffmpeg.org/download.html) on your PATH (required by faster-whisper)
- A microphone

#### Windows — install FFmpeg
```powershell
winget install ffmpeg
```
Or download from https://www.gyan.dev/ffmpeg/builds/ and add `bin/` to PATH.

#### Windows — install PyAudio
```powershell
pip install pipwin
pipwin install pyaudio
```
Or download the matching wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

### 2. Clone / open the project

```bash
cd "Health Voice Agent"
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get a free Groq API key

1. Go to **https://console.groq.com**
2. Sign up (no credit card needed)
3. Click **API Keys → Create API Key**
4. Copy the key

### 5. Configure environment

```bash
copy .env.example .env
```

Open `.env` and paste your key:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
WHISPER_MODEL=base
USER_DATA_DIR=./user_data
```

### 6. Run

```bash
python main.py
```

---

## Example Conversation

```
Medi: Hello Alex! I'm Medi, your personal voice health assistant.
      What symptoms are you experiencing today?

You:  I have a really bad headache and my throat feels sore.

Medi: How long have you been experiencing these symptoms?

You:  Since yesterday evening, maybe about 18 hours.

Medi: On a scale of 1 to 10, how severe would you say the headache is?

You:  About a 6. It gets worse when I look at screens.

Medi: Do you have any other symptoms, such as fever, runny nose, or fatigue?

You:  Yes, I feel a bit tired and my nose is a little runny.

Medi: Based on what you've told me, here are some possible causes and suggestions:

      POSSIBLE CAUSES
      1. Viral upper respiratory infection (common cold or flu)
      2. Tension headache worsened by screen use
      3. Mild dehydration combined with a viral infection

      HOME REMEDIES
      1. Rest in a quiet, dark room and limit screen time for today
      2. Drink plenty of warm fluids — herbal tea with honey is especially soothing
      3. Gargle warm salt water (½ tsp salt in 8 oz water) 3 times today
      4. Apply a cool cloth to your forehead for headache relief
      5. Take paracetamol or ibuprofen as directed if needed

      These are general home remedies only. Please consult a doctor for proper
      medical advice, especially if symptoms persist or worsen.

      Would you like me to remember this session for future reference?

You:  Yes please.

Medi: I've saved your health session. Is there anything else you'd like to discuss?

You:  No, that's all.

Medi: Take care and feel better soon! Goodbye!
```

---

## Project Structure

```
voice-health-assistant/
├── main.py                  # Entry point & conversation loop
├── config.py                # All configs and constants
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── agents/
│   ├── health_agent.py      # Orchestrator — state machine + Groq
│   ├── symptom_analyzer.py  # Extracts symptoms via LLM
│   ├── followup_agent.py    # Generates follow-up questions
│   └── remedy_agent.py      # Generates causes + home remedies
├── voice/
│   ├── stt.py               # faster-whisper speech-to-text
│   ├── tts.py               # pyttsx3 text-to-speech
│   └── recorder.py          # PyAudio + VAD audio recording
├── memory/
│   ├── chroma_store.py      # ChromaDB client setup
│   ├── health_memory.py     # Store and retrieve sessions
│   └── session_manager.py  # User profile management
├── tools/
│   ├── symptom_checker.py   # Emergency detection + severity
│   ├── remedy_finder.py     # Offline remedy knowledge base
│   └── history_tool.py      # History retrieval wrapper
└── utils/
    ├── logger.py            # Logging (console + file)
    └── helpers.py           # Utility functions
```

---

## Safety Notes

- **Emergency symptoms** (chest pain, difficulty breathing, stroke signs, etc.) trigger an immediate "call emergency services" message — no remedies are given.
- The assistant **never diagnoses** — it only suggests *possible causes*.
- Every remedy response ends with a medical disclaimer.

---

## Future Improvements

- [ ] Web UI with waveform visualiser (React + FastAPI)
- [ ] Multi-user support with login
- [ ] Export health history to PDF
- [ ] Medication reminder scheduling
- [ ] Integration with health wearables (Fitbit, Apple Health)
- [ ] Multilingual support (Whisper supports 99 languages)
- [ ] Faster TTS using Edge-TTS (Microsoft Azure, still free)
- [ ] Symptom trend charts over time
