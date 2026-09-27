"""JSON-API. /api/chat kjører kundeserviceagenten (app/chatbot.py)."""
from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .. import chatbot
from ..auth import current_user

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None  # tidligere meldinger: [{"role": "user"|"assistant", "content": "..."}]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    user = current_user(request)
    reply = chatbot.get_reply(payload.message, payload.history, user, date.today().isoformat())
    return ChatResponse(reply=reply)
