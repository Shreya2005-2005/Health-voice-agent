import uuid
from pathlib import Path
from config import PROFILES_DIR
from utils.helpers import load_json, save_json, slugify, now_iso
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SessionManager:
    def __init__(self):
        self._profiles_dir = PROFILES_DIR

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    def get_or_create_user(self) -> dict:
        """
        Prompt for the user's name on first run; load existing profile otherwise.
        Returns the user profile dict.
        """
        existing = self._list_profiles()
        if existing:
            # Single-user mode: just return the first profile
            profile = load_json(self._profiles_dir / existing[0])
            print(f"\nWelcome back, {profile['name']}!")
            return profile

        # First run — ask for name
        print("\nWelcome to Voice Health Assistant!")
        name = input("Please enter your name: ").strip()
        if not name:
            name = "Friend"
        return self.create_user(name)

    def create_user(self, name: str) -> dict:
        user_id = str(uuid.uuid4())
        profile = {
            "id": user_id,
            "name": name,
            "created_at": now_iso(),
            "session_count": 0,
        }
        filename = f"{slugify(name)}_{user_id[:8]}.json"
        save_json(self._profiles_dir / filename, profile)
        logger.info(f"Created user profile: {name} ({user_id})")
        return profile

    def update_session_count(self, user: dict) -> None:
        user["session_count"] = user.get("session_count", 0) + 1
        user["last_seen"] = now_iso()
        filename = self._find_profile_file(user["id"])
        if filename:
            save_json(self._profiles_dir / filename, user)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _list_profiles(self) -> list[str]:
        return [p.name for p in self._profiles_dir.glob("*.json")]

    def _find_profile_file(self, user_id: str) -> str | None:
        for fname in self._list_profiles():
            p = load_json(self._profiles_dir / fname)
            if p.get("id") == user_id:
                return fname
        return None
