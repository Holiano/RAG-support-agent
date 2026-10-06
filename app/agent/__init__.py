"""Kundeserviceagenten. Bruk `get_agent().answer(...)`. Se CONTEXT.md for begrepene og docs/adr for valgene."""
from functools import lru_cache

from .agent import Agent, AgentReply
from .retriever import VectorRetriever
from .settings import is_configured

__all__ = ["Agent", "AgentReply", "get_agent", "is_configured"]


@lru_cache(maxsize=1)
def get_agent() -> Agent:
    return Agent(VectorRetriever())
