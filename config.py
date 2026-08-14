import os
from dotenv import load_dotenv

load_dotenv()


def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

API_ID = int(require("API_ID"))
API_HASH = require("API_HASH")
GEMINI_API_KEY = require("GEMINI_API_KEY")
OWNER_ID = int(require("OWNER_ID"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()
DB_PATH = os.getenv("DB_PATH", "data/ubot.sqlite3")
AI_PREFIX = os.getenv("AI_PREFIX", ".pai")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "16"))
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "4000"))
AI_COOLDOWN_SECONDS = float(os.getenv("AI_COOLDOWN_SECONDS", "1.5"))

PERSONALITY = os.getenv(
    "AI_PERSONALITY",
    "Jawab singkat, natural, santai, dan tidak kaku. Gunakan bahasa yang mengikuti gaya pengguna. Jangan bertele-tele kecuali pengguna meminta penjelasan detail."
)
