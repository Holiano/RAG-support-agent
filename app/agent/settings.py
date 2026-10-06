"""Innstillinger for kundeserviceagenten. Leses fra miljøvariabler; en .env i prosjektroten støttes."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AGENT_DB_URL = os.environ.get("AGENT_DB_URL", "")  # Postgres-URI (Supabase) for agentens eget lager

CHAT_MODEL = os.environ.get("AGENT_CHAT_MODEL", "gemini-3.8-flash")
EMBEDDING_MODEL = os.environ.get("AGENT_EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIM = int(os.environ.get("AGENT_EMBEDDING_DIM", "768"))

SHOP_ID = int(os.environ.get("AGENT_SHOP_ID", "1"))
TOP_K = int(os.environ.get("AGENT_TOP_K", "6"))
MAX_TOOL_ROUNDS = 5
REQUEST_TIMEOUT_MS = int(os.environ.get("AGENT_REQUEST_TIMEOUT_MS", "90000"))  # per Gemini-kall
HISTORY_LIMIT = 12  # antall tidligere meldinger som sendes med


def is_configured() -> bool:
    """Agenten kobles til bare når både Gemini-nøkkel og database er satt. Ellers svarer /api/chat med stubben."""
    return bool(GEMINI_API_KEY and AGENT_DB_URL)
