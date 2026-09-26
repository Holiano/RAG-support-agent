"""JSON-API. /api/chat er en stubb som skal byttes ut med kundeservice-agenten."""
from fastapi import APIRouter
from pydantic import BaseModel

from ..config import CHAT_STUB_REPLY

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] | None = None  # tidligere meldinger: [{"role": "user"|"assistant", "content": "..."}]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    # TODO: bytt ut med kundeservice-agenten (RAG over data/docs + ordre-/produktdata).
    return ChatResponse(reply=CHAT_STUB_REPLY)
