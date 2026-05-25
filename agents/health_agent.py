"""
Main orchestrator agent.

Conversation states
-------------------
GREETING        → agent greets and asks for symptoms
COLLECTING      → user describes symptoms; extract them
FOLLOWING_UP    → agent asks follow-up questions (up to MAX_FOLLOW_UP_ROUNDS)
DIAGNOSING      → agent delivers assessment + remedies
SAVE_PROMPT     → ask if user wants to save the session
DONE            → conversation complete
"""

from groq import Groq
from config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE,
    MAX_FOLLOW_UP_ROUNDS, EMERGENCY_RESPONSE,
)
from agents.symptom_analyzer import extract_symptoms
from agents.followup_agent import generate_followup
from agents.remedy_agent import generate_diagnosis
from memory.health_memory import store_session
from tools.symptom_checker import check_emergency
from tools.history_tool import get_relevant_history
from memory.session_manager import SessionManager
from utils.logger import setup_logger

logger = setup_logger(__name__)

ORCHESTRATOR_SYSTEM = """You are Medi, a warm voice health assistant.
Rules:
- Keep every reply SHORT — 1 to 3 sentences maximum.
- Plain conversational text only. No markdown, no headers, no bullet points, no bold.
- Never diagnose. Never use lists or numbered points.
- If the user goes off-topic, briefly steer back to their health concern."""


class HealthAgent:
    STATE_GREETING = "GREETING"
    STATE_COLLECTING = "COLLECTING"
    STATE_FOLLOWING_UP = "FOLLOWING_UP"
    STATE_DIAGNOSING = "DIAGNOSING"
    STATE_SAVE_PROMPT = "SAVE_PROMPT"
    STATE_DONE = "DONE"

    def __init__(self, session_manager: SessionManager, tts=None):
        self._sm = session_manager
        self._tts = tts
        self._client = Groq(api_key=GROQ_API_KEY)
        self._user: dict = {}
        self._state = self.STATE_GREETING
        self._conversation: list[dict] = []  # {role, content}
        self._symptoms: list[str] = []
        self._followup_round = 0
        self._causes: list[str] = []
        self._remedies: list[str] = []
        self._diagnosis_text: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_user(self, user: dict) -> None:
        self._user = user
        logger.info(f"Agent set for user: {user.get('name')} ({user.get('id')})")

    def start_conversation(self) -> str:
        name = self._user.get("name", "there")
        session_count = self._user.get("session_count", 0)
        if session_count > 0:
            greeting = (
                f"Hello {name}! Welcome back to your health assistant. "
                "What symptoms are you experiencing today?"
            )
        else:
            greeting = (
                f"Hello {name}! I'm Medi, your personal voice health assistant. "
                "I'm here to help you understand your symptoms and find relief. "
                "What symptoms are you experiencing today?"
            )
        self._state = self.STATE_COLLECTING
        self._add_message("assistant", greeting)
        return greeting

    def process_input(self, user_text: str) -> str:
        self._add_message("user", user_text)

        # Emergency check on every input
        if check_emergency(user_text):
            response = EMERGENCY_RESPONSE
            self._add_message("assistant", response)
            self._state = self.STATE_DONE
            return response

        if self._state == self.STATE_COLLECTING:
            return self._handle_collecting(user_text)
        elif self._state == self.STATE_FOLLOWING_UP:
            return self._handle_followup(user_text)
        elif self._state == self.STATE_DIAGNOSING:
            return self._handle_diagnosing()
        elif self._state == self.STATE_SAVE_PROMPT:
            return self._handle_save_prompt(user_text)
        elif self._state == self.STATE_DONE:
            return self._handle_done(user_text)
        else:
            return self._fallback_response(user_text)

    def is_done(self) -> bool:
        return self._state == self.STATE_DONE

    def save_current_session(self) -> None:
        """Force-save if there are symptoms (called on Ctrl+C)."""
        if self._symptoms and self._user.get("id"):
            self._do_save()

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _handle_collecting(self, user_text: str) -> str:
        new_symptoms = extract_symptoms(user_text)
        if new_symptoms:
            # Merge, deduplicate
            for s in new_symptoms:
                if s not in self._symptoms:
                    self._symptoms.append(s)
            logger.info(f"Symptoms so far: {self._symptoms}")

        if not self._symptoms:
            response = (
                "I didn't quite catch any symptoms. "
                "Could you describe what you're feeling? For example, do you have a headache, fever, or sore throat?"
            )
            self._add_message("assistant", response)
            return response

        # Move to follow-up phase
        self._state = self.STATE_FOLLOWING_UP
        self._followup_round = 0
        return self._ask_followup()

    def _handle_followup(self, user_text: str) -> str:
        # Absorb any additional symptoms mentioned in follow-up answers
        extra = extract_symptoms(user_text)
        for s in extra:
            if s not in self._symptoms:
                self._symptoms.append(s)

        self._followup_round += 1
        if self._followup_round < MAX_FOLLOW_UP_ROUNDS:
            return self._ask_followup()
        else:
            # Enough info — diagnose
            self._state = self.STATE_DIAGNOSING
            return self._handle_diagnosing()

    def _handle_diagnosing(self) -> str:
        history_ctx = get_relevant_history(self._user.get("id", ""), self._symptoms)
        response, causes, remedies = generate_diagnosis(
            self._symptoms,
            self._conversation[:-1],  # exclude the trigger message
            history_ctx,
        )
        self._causes = causes
        self._remedies = remedies
        self._diagnosis_text = response

        # Append save prompt
        save_prompt = "\n\nWould you like me to remember this session for future reference? Please say yes or no."
        full_response = response + save_prompt

        self._add_message("assistant", full_response)
        self._state = self.STATE_SAVE_PROMPT
        return full_response

    def _handle_save_prompt(self, user_text: str) -> str:
        lowered = user_text.lower()
        if any(w in lowered for w in ("yes", "yeah", "sure", "please", "ok", "okay", "yep", "y")):
            self._do_save()
            response = (
                "I've saved your health session for future reference. "
                "Is there anything else you'd like to discuss, or shall we wrap up?"
            )
        else:
            response = (
                "No problem, I won't save this session. "
                "Is there anything else you'd like to discuss, or shall we wrap up?"
            )
        self._add_message("assistant", response)
        self._state = self.STATE_DONE
        return response

    def _handle_done(self, user_text: str) -> str:
        lowered = user_text.lower()
        if any(w in lowered for w in ("no", "bye", "goodbye", "exit", "quit", "done", "nothing", "nope")):
            response = (
                "Take care and feel better soon! "
                "Remember to consult a doctor if your symptoms persist or worsen. Goodbye!"
            )
            self._add_message("assistant", response)
            return response

        # User wants to continue — restart
        self._reset_session()
        response = (
            "Of course! What other symptoms or health questions would you like to discuss?"
        )
        self._add_message("assistant", response)
        self._state = self.STATE_COLLECTING
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ask_followup(self) -> str:
        question = generate_followup(
            self._symptoms,
            self._conversation,
            self._followup_round + 1,
        )
        self._add_message("assistant", question)
        return question

    def _fallback_response(self, user_text: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": ORCHESTRATOR_SYSTEM}] + self._conversation,
                max_tokens=GROQ_MAX_TOKENS,
                temperature=GROQ_TEMPERATURE,
            )
            response = completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Fallback LLM error: {e}")
            response = "I'm sorry, I encountered an issue. Could you please repeat that?"
        self._add_message("assistant", response)
        return response

    def _add_message(self, role: str, content: str) -> None:
        self._conversation.append({"role": role, "content": content})

    def _do_save(self) -> None:
        if not self._user.get("id"):
            return
        summary = self._diagnosis_text[:300] if self._diagnosis_text else "Session with symptoms: " + ", ".join(self._symptoms)
        store_session(
            user_id=self._user["id"],
            symptoms=self._symptoms,
            causes=self._causes,
            remedies=self._remedies,
            conversation_summary=summary,
        )
        self._sm.update_session_count(self._user)
        logger.info("Session saved successfully")

    def _reset_session(self) -> None:
        self._symptoms = []
        self._followup_round = 0
        self._causes = []
        self._remedies = []
        self._diagnosis_text = ""
