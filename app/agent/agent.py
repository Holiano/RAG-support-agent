"""Kundeserviceagenten: henter tekstbiter, kaller Gemini med verktøy i en manuell løkke, og logger hver melding."""
import logging
import time
from dataclasses import dataclass, field
from datetime import date

from google import genai
from google.genai import types

from ..config import SHOP_NAME
from . import settings
from .gemini import client as gemini_client
from .prompt import build_user_message, system_instruction
from .retriever import Retriever
from .tools import DECLARATIONS, ToolContext, execute

log = logging.getLogger(__name__)

TECHNICAL_ERROR_REPLY = ("Beklager, jeg har tekniske problemer akkurat nå. Prøv igjen om litt, eller kontakt "
                         "kundeservice på kundeservice@vindhamar.example eller +47 555 01 234.")
NO_ANSWER_REPLY = "Beklager, jeg klarte ikke å fullføre svaret. Kan du prøve å stille spørsmålet på nytt?"


@dataclass
class AgentReply:
    reply: str
    retrieved: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0
    error: str | None = None


class Agent:
    def __init__(self, retriever: Retriever, *, model: str = settings.CHAT_MODEL, shop_id: int = settings.SHOP_ID,
                 shop_name: str = SHOP_NAME, log_turns: bool = True, client: genai.Client | None = None):
        self.retriever = retriever
        self.model = model
        self.shop_id = shop_id
        self.log_turns = log_turns
        self._client = client
        self.config = types.GenerateContentConfig(
            system_instruction=system_instruction(shop_name),
            tools=[types.Tool(function_declarations=DECLARATIONS)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = gemini_client()
        return self._client

    def answer(self, message: str, history: list[dict] | None, customer: dict | None,
               today: date | None = None) -> AgentReply:
        today = today or date.today()
        history = (history or [])[-settings.HISTORY_LIMIT:]
        started = time.perf_counter()
        result = AgentReply(reply=TECHNICAL_ERROR_REPLY)
        try:
            result.retrieved = self.retriever.search(message)
            result.reply = self._run(message, history, customer, today, result)
        except Exception as e:  # noqa: BLE001 - kunden skal få et svar, og feilen skal i loggen
            log.exception("Agenten feilet")
            result.error = f"{type(e).__name__}: {e}"
            result.reply = TECHNICAL_ERROR_REPLY
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        if self.log_turns:
            self._log(message, history, customer, result)
        return result

    def _run(self, message: str, history: list[dict], customer: dict | None, today: date, result: AgentReply) -> str:
        ctx = ToolContext(customer=customer, today=today)
        contents = [types.Content(role="user" if h.get("role") == "user" else "model",
                                  parts=[types.Part.from_text(text=str(h.get("content", "")))])
                    for h in history if h.get("content")]
        contents.append(types.Content(role="user", parts=[types.Part.from_text(
            text=build_user_message(message, result.retrieved, customer, today))]))

        for _ in range(settings.MAX_TOOL_ROUNDS + 1):
            response = self.client.models.generate_content(model=self.model, contents=contents, config=self.config)
            self._add_usage(result.usage, response)
            calls = response.function_calls or []
            if not calls:
                text = (response.text or "").strip()
                return text or NO_ANSWER_REPLY
            contents.append(response.candidates[0].content)
            parts = []
            for call in calls:
                args = dict(call.args or {})
                output = execute(call.name, args, ctx)
                result.tool_calls.append({"verktoy": call.name, "argumenter": args, "resultat": output})
                payload = {"result": output}
                extra = self._follow_up_chunks(message, output, result.retrieved)
                if extra:
                    result.retrieved.extend(extra)
                    payload["relevant_butikkinformasjon"] = [c["content"] for c in extra]
                parts.append(types.Part.from_function_response(name=call.name, response=payload))
            contents.append(types.Content(role="user", parts=parts))
        return NO_ANSWER_REPLY

    def _follow_up_chunks(self, message: str, output: dict, already: list[dict]) -> list[dict]:
        """Ordrestatus avgjør ofte hvilke regler som gjelder (retur, refusjon, kansellering), men kundens
        spørsmål nevner dem sjelden. Hent derfor tekstbiter på nytt når et verktøy har gitt en status."""
        status = output.get("status_tekst") if isinstance(output, dict) else None
        if not status:
            return []
        notes = " ".join(h.get("merknad", "") for h in output.get("historikk", [])[-2:])
        seen = {(c["doc_slug"], c["heading_path"]) for c in already}
        try:
            hits = self.retriever.search(f"{message} Ordrestatus: {status}. {notes}")
        except Exception:  # noqa: BLE001 - oppfølgingshenting er en bonus, ikke et krav
            log.exception("Oppfølgingshenting feilet")
            return []
        return [c for c in hits if (c["doc_slug"], c["heading_path"]) not in seen][:3]

    @staticmethod
    def _add_usage(usage: dict, response) -> None:
        meta = getattr(response, "usage_metadata", None)
        if not meta:
            return
        usage["input_tokens"] = usage.get("input_tokens", 0) + (meta.prompt_token_count or 0)
        usage["output_tokens"] = usage.get("output_tokens", 0) + (meta.candidates_token_count or 0)
        usage["cached_tokens"] = usage.get("cached_tokens", 0) + (getattr(meta, "cached_content_token_count", 0) or 0)
        usage["calls"] = usage.get("calls", 0) + 1

    def _log(self, message: str, history: list[dict], customer: dict | None, result: AgentReply) -> None:
        from . import store
        try:
            store.log_turn(self.shop_id, {
                "customer_id": customer["id"] if customer else None, "message": message, "history_length": len(history),
                "retrieved": [{k: c.get(k) for k in ("doc_slug", "heading_path", "score")} for c in result.retrieved],
                "tool_calls": result.tool_calls, "reply": result.reply, "model": self.model,
                "latency_ms": result.latency_ms, "input_tokens": result.usage.get("input_tokens"),
                "output_tokens": result.usage.get("output_tokens"), "cached_tokens": result.usage.get("cached_tokens"),
                "error": result.error,
            })
        except Exception:  # noqa: BLE001 - logging skal aldri velte svaret til kunden
            log.exception("Kunne ikke logge samtalen")
