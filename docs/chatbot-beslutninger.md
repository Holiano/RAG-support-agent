# Chatbot: beslutninger

Valg som er tatt for kundeservice-chatboten. Sist oppdatert 2026-09-26.

## Utgangspunktet

Demobutikken Vindhamar Friluft er en testbenk for en AI-kundeserviceagent. Chatknappen i nettbutikken sender allerede meldinger til `POST /api/chat`, som foreløpig returnerer en stubb (`chat()` i `app/routes/api.py`). Agenten skal erstatte den funksjonen.

Butikken har tre typer kunnskap som krever ulik håndtering:

| Type | Eksempel | Kilde | Løses med |
|---|---|---|---|
| Policy og info | «Kan jeg returnere brukte sko?» | `data/docs/*.md` | Søk i tekst (RAG) |
| Produkt | «Er Storhaugen på lager i 43?» | produkt- og variantdata | Oppslag (verktøy) |
| Ordre | «Hvor er ordren min?» | ordredata, personlig | Oppslag med tilgangskontroll |

## Besluttet

### B1. Arkitektur: agent med verktøy
Ikke ren RAG. Claude får verktøy og velger selv hvilke som trengs: `søk_dokumenter`, `hent_produkt`, `hent_ordre` og `tilby_kundeservice`.

**Hvorfor:** Ren RAG kan ikke svare på ordrestatus eller lagerstatus, og den regner dårlig (er 30 dager gått? blir summen over 1 200 kr etter rabatt?). Et rammeverk som LangGraph er for tungt for et problem i denne størrelsen.

Å legge alle dokumentene i prompten (de er bare ca. 5 000 ord) er ikke en sluttløsning, men brukes som **referanse** for å måle om RAG faktisk gjør boten bedre.

### B2. LLM: Anthropic API
Claude med verktøybruk. API-nøkkelen ligger bare på serveren, aldri i nettleseren.

### B3. RAG bygges selv med små byggeklosser
Egen oppdeling (på markdown-overskrift, dokumenttittel med i hver bit, tabeller holdes hele), hybridsøk (nøkkelord + embeddings) og en enkel indeks. Ikke LangChain eller LlamaIndex.

**Hvorfor:** Målet er å forstå og kunne måle hvert steg. Tall som 14 og 30 dager fanges dårlig av embeddings alene, så nøkkelordsøk må med.

### B4. Språk: bokmål
Boten svarer alltid på bokmål, uansett hvilket språk kunden skriver på. Systemprompten må si det eksplisitt.

### B5. Usikker bot: kunden velger selv om saken sendes videre
Boten sender aldri en sak av seg selv. Den **tilbyr** det, og kunden bekrefter.

- Boten bruker verktøyet `tilby_kundeservice` når søket ikke gir noe relevant, når spørsmålet ligger utenfor butikken, eller når saken krever et menneske (for eksempel en reklamasjon som må vurderes).
- Harde regler ved siden av: ber kunden om en person, tilbys det med én gang. To mislykte svar på rad gir samme tilbud.
- En knapp for å kontakte kundeservice ligger alltid i chatvinduet.
- Overleveringen **lagrer en sak i databasen** med samtalelogg og kort sammendrag. Kunden fyller inn e-post (forhåndsutfylt hvis innlogget).
- Bekreftelsen viser åpningstider og svartid fra `data/docs/kontakt.md`, slik at kunden vet når de får svar (for eksempel «neste virkedag» på julaften).

### B6. Personvern og trygghet
- En innlogget kunde ser bare sine egne ordrer. Gjester må oppgi ordrenummer og e-post, som i ordresporingen.
- Tekst som hentes inn (anmeldelser, produktbeskrivelser, dokumenter) behandles som **data**, aldri som instruksjoner.
- Boten skal ikke finne på policy. Er svaret ikke i kildene, sier den det og tilbyr kundeservice.

## Planlagt rekkefølge

1. **Evalueringssett:** spørsmål med fasit, hentet fra de bevisste fallgruvene i README. Se [eval/](../eval/).
2. **RAG over dokumentene** med kilder, målt mot alt-i-prompten-referansen.
3. **Verktøy for ordre og produkt**, deretter finpuss av vinduet (streaming, kilder, overleveringsknapp).
