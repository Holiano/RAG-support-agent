"""JSON-API. /api/chat går til kundeserviceagenten når den er konfigurert, ellers til en stubb."""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from .. import agent, auth
from ..config import CHAT_STUB_REPLY

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None  # tidligere meldinger: [{"role": "user"|"assistant", "content": "..."}]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    if not agent.is_configured():
        return ChatResponse(reply=CHAT_STUB_REPLY)
    result = agent.get_agent().answer(payload.message, payload.history, auth.current_user(request))
    return ChatResponse(reply=result.reply)
