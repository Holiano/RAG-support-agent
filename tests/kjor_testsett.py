"""Kjører testsettet (tests/testsett.json) mot kundeserviceagenten og skriver rapport til tests/rapporter/.

  python tests/kjor_testsett.py                            vektorsøk, standardmodell, med dommer
  python tests/kjor_testsett.py --retriever alt-lokalt     alle tekstbiter fra data/docs i kontekst (referanse, trenger ikke database)
  python tests/kjor_testsett.py --modell gemini-3.5-flash-lite --uten-dommer
  python tests/kjor_testsett.py --bare ordre-returfrist --bare gjest-feil-epost

Hvert tilfelle sjekkes på to måter: forventede fakta må finnes i svaret (sammenlignet uten mellomrom og store
bokstaver), og en modell dømmer svaret mot fasiten med 0 (feil eller finner på), 1 (delvis) eller 2 (riktig).
Bruker en midlertidig butikkdatabase og logger ikke til agentens samtalelogg med mindre --logg er satt.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "testsett.db")

import seed  # noqa: E402

from app.agent import settings  # noqa: E402
from app.agent.agent import Agent  # noqa: E402
from app.agent.retriever import FullContextRetriever, LocalFullContextRetriever, VectorRetriever  # noqa: E402
from app.db import DATA_DIR, query_one  # noqa: E402

RAPPORTER = ROOT / "tests" / "rapporter"

JUDGE_PROMPT = """Du vurderer svaret fra en kundeserviceagent for nettbutikken Vindhamar Friluft.

Agenten har lov til å bruke tre kilder som fakta: kunnskapsbasen under, resultatene fra verktøykallene under, og dagens dato ({dato}). Alt som stemmer med disse kildene er riktig, også om det ikke står i fasiten. Fasiten er minimum, ikke en fullstendig liste. Det som IKKE kan spores til kildene, regnes som oppdiktet.

Kundens spørsmål:
{sporsmal}

Fasit (det et riktig svar minst må få fram, og hva agenten ikke skal gjøre):
{fasit}

Verktøyresultater agenten fikk (tom hvis ingen verktøy ble brukt):
{verktoy}

Agentens svar:
{svar}

Gi poeng:
2 = Svaret dekker fasiten, alt i svaret kan spores til kildene, og det er forståelig for kunden.
1 = Svaret er i hovedsak riktig, men mangler et vesentlig punkt fra fasiten eller er upresist.
0 = Svaret er feil, villedende, inneholder påstander som ikke finnes i kildene, eller gjør noe fasiten sier agenten ikke skal gjøre.
Svar på bokmål med JSON: {{"poeng": <0|1|2>, "begrunnelse": "<én til to setninger>"}}

Kunnskapsbase:
{kunnskapsbase}"""


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text.lower()).replace("–", "-").replace("—", "-")


def check_facts(reply: str, expected: list[str], forbidden: list[str]) -> tuple[list[str], list[str]]:
    """Returnerer (manglende fakta, forbudte treff)."""
    n = norm(reply)
    missing = [fact for fact in expected if not any(norm(alt) in n for alt in fact.split(" | "))]
    hits = [word for word in forbidden if norm(word) in n]
    return missing, hits


def knowledge_base() -> str:
    return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((DATA_DIR / "docs").glob("*.md")))


def judge(client, model: str, case: dict, reply, today: date, kunnskapsbase: str) -> dict:
    from google.genai import types
    verktoy = json.dumps(reply.tool_calls, ensure_ascii=False, default=str)[:6000] if reply.tool_calls else "(ingen)"
    prompt = JUDGE_PROMPT.format(sporsmal=case["sporsmal"], fasit=case["fasit"], svar=reply.reply, dato=today.isoformat(),
                                 verktoy=verktoy, kunnskapsbase=kunnskapsbase)
    response = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            response_mime_type="application/json",
            response_schema={"type": "OBJECT", "properties": {"poeng": {"type": "INTEGER"}, "begrunnelse": {"type": "STRING"}},
                             "required": ["poeng", "begrunnelse"]}))
    try:
        return json.loads(response.text)
    except (TypeError, ValueError):
        return {"poeng": None, "begrunnelse": f"Uleselig dommersvar: {response.text!r}"}


def customer_for(email: str | None) -> dict | None:
    if not email:
        return None
    row = query_one("SELECT id, name, email FROM customers WHERE lower(email) = ?", (email.lower(),))
    if row is None:
        raise SystemExit(f"Testsettet viser til ukjent kunde: {email}")
    return dict(row)


def make_retriever(kind: str):
    if kind == "vektor":
        return VectorRetriever()
    if kind == "alt-db":
        return FullContextRetriever()
    return LocalFullContextRetriever(DATA_DIR / "docs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modell", default=settings.CHAT_MODEL)
    parser.add_argument("--retriever", choices=["vektor", "alt-db", "alt-lokalt"], default="vektor")
    parser.add_argument("--uten-dommer", action="store_true")
    parser.add_argument("--dommer-modell", default="gemini-3.8-flash")
    parser.add_argument("--bare", action="append", default=[], help="Kjør bare tilfellet med denne id-en (kan gjentas).")
    parser.add_argument("--dato", type=date.fromisoformat, default=None, help="Dagens dato for agenten, YYYY-MM-DD.")
    parser.add_argument("--logg", action="store_true", help="Logg også til agentens samtalelogg.")
    args = parser.parse_args()

    if not settings.GEMINI_API_KEY:
        print("GEMINI_API_KEY mangler (se example.env).", file=sys.stderr)
        return 2
    if args.retriever != "alt-lokalt" and not settings.AGENT_DB_URL:
        print("AGENT_DB_URL mangler. Bruk --retriever alt-lokalt for å kjøre uten database.", file=sys.stderr)
        return 2

    seed.main()
    cases = json.loads((ROOT / "tests" / "testsett.json").read_text(encoding="utf-8"))["tilfeller"]
    if args.bare:
        cases = [c for c in cases if c["id"] in set(args.bare)]
    agent = Agent(make_retriever(args.retriever), model=args.modell, log_turns=args.logg)
    today = args.dato or date.today()
    kb = knowledge_base()

    results = []
    print(f"\nModell {args.modell}, retriever {args.retriever}, dato {today}, {len(cases)} tilfeller\n")
    for case in cases:
        reply = agent.answer(case["sporsmal"], case.get("historikk"), customer_for(case.get("innlogget")), today)
        missing, hits = check_facts(reply.reply, case.get("forventet", []), case.get("forbudt", []))
        verdict = None if args.uten_dommer else judge(agent.client, args.dommer_modell, case, reply, today, kb)
        facts_ok = not missing and not hits and reply.error is None
        results.append({
            "id": case["id"], "sporsmal": case["sporsmal"], "innlogget": case.get("innlogget"), "svar": reply.reply,
            "fakta_ok": facts_ok, "mangler": missing, "forbudt_treff": hits, "dommer": verdict, "feil": reply.error,
            "verktoy": [t["verktoy"] for t in reply.tool_calls], "tekstbiter": [c["heading_path"] for c in reply.retrieved],
            "latens_ms": reply.latency_ms, "tokens": reply.usage,
        })
        score = "-" if verdict is None else str(verdict.get("poeng"))
        tools = ",".join(t["verktoy"] for t in reply.tool_calls) or "-"
        print(f"{'OK  ' if facts_ok else 'FEIL'} {case['id']:<24} dommer {score}  {reply.latency_ms:>5} ms  verktøy {tools}")
        for m in missing:
            print(f"       mangler: {m}")
        for h in hits:
            print(f"       forbudt: {h}")
        if reply.error:
            print(f"       feil: {reply.error}")
        time.sleep(0.5)  # skånsomt mot ratebegrensning

    passed = sum(r["fakta_ok"] for r in results)
    scores = [r["dommer"]["poeng"] for r in results if r["dommer"] and r["dommer"].get("poeng") is not None]
    tokens_in = sum(r["tokens"].get("input_tokens", 0) for r in results)
    tokens_out = sum(r["tokens"].get("output_tokens", 0) for r in results)
    print(f"\nFakta bestått: {passed}/{len(results)}")
    if scores:
        print(f"Dommer: snitt {sum(scores) / len(scores):.2f} av 2, {scores.count(2)} fulle, {scores.count(0)} nuller")
    print(f"Tokens: {tokens_in} inn, {tokens_out} ut. Snittlatens {sum(r['latens_ms'] for r in results) // max(1, len(results))} ms")

    RAPPORTER.mkdir(exist_ok=True)
    path = RAPPORTER / f"{datetime.now():%Y%m%d-%H%M%S}-{args.modell}-{args.retriever}.json"
    path.write_text(json.dumps({"modell": args.modell, "retriever": args.retriever, "dato": today.isoformat(),
                                "fakta_bestatt": passed, "antall": len(results), "dommer_snitt": (sum(scores) / len(scores)) if scores else None,
                                "resultater": results}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Rapport: {path.relative_to(ROOT)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
