---
title: Health Voice Agent
emoji: 🩺
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Medi — AI Voice Health Assistant

🔴 **Live Demo:** [health-voice-agent on Hugging Face](https://huggingface.co/spaces/Shreya2005-2005/health-voice-agent)

Medi is an AI-powered health assistant. Tell it your symptoms by voice or text, and it asks smart follow-up questions, then gives you possible causes and home remedies. It remembers your past sessions too.

**100% free — no paid APIs needed.**

---

## What It Does

- 🎤 Speak or type your symptoms
- 🤔 AI asks follow-up questions (how long? how severe?)
- 💊 Get possible causes + home remedies
- 🧠 Remembers your past health sessions
- 🚨 Detects emergencies (chest pain etc.) and tells you to call help

---

## Tech Used

| What | How |
|------|-----|
| AI Brain | Groq — LLaMA 3.3 70B (free) |
| Speech to Text | faster-whisper (runs locally) |
| Memory | ChromaDB (vector database) |
| Web Server | FastAPI + Uvicorn |
| Frontend | HTML, CSS, JavaScript |

---

## Run Locally

**1. Get a free Groq API key** at [console.groq.com](https://console.groq.com)

**2. Clone and install:**
```bash
git clone https://github.com/Shreya2005-2005/Health-voice-agent.git
cd Health-voice-agent
pip install -r requirements.txt
```

**3. Set up your key:**
```bash
copy .env.example .env
# Open .env and paste your GROQ_API_KEY
```

**4. Run:**
```bash
python app.py
# Open http://localhost:8000 in your browser
```

---

## Safety

- Emergency symptoms always get "call emergency services" — no remedies
- Never diagnoses — only suggests possible causes
- Every response includes a medical disclaimer

---

## Future Plans

- [ ] PDF export of health history
- [ ] Multilingual support
- [ ] Medication reminders
- [ ] Symptom trend charts
