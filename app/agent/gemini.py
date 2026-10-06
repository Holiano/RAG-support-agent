"""Én delt Gemini-klient med tidsfrist per kall, slik at et kall som aldri får svar ikke henger agenten."""
from google import genai
from google.genai import types

from . import settings

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY,
                               http_options=types.HttpOptions(timeout=settings.REQUEST_TIMEOUT_MS))
    return _client
