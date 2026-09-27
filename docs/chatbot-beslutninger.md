# Chatbot: beslutninger

Valg som er tatt for kundeservice-chatboten. Sist oppdatert 2026-09-27.

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
Ikke ren RAG. Modellen får verktøy og velger selv hvilke som trengs. Opprinnelig plan: `søk_dokumenter`, `hent_produkt`, `hent_ordre` og `tilby_kundeservice`. I v0 (se «Gjennomført» under) er det forenklet til `sok_produkter` og `hent_ordre` — dokumentene sendes hele i systemprompten i stedet for et eget søkeverktøy (jf. B1s andre avsnitt), og `tilby_kundeservice` er utsatt til B5 er fullt implementert.

**Hvorfor:** Ren RAG kan ikke svare på ordrestatus eller lagerstatus, og den regner dårlig (er 30 dager gått? blir summen over 1 200 kr etter rabatt?). Et rammeverk som LangGraph er for tungt for et problem i denne størrelsen.

Å legge alle dokumentene i prompten (de er bare ca. 5 000 ord) er ikke en sluttløsning, men brukes som **referanse** for å måle om RAG faktisk gjør boten bedre.

### B2. LLM: Google Gemini API (endret fra Anthropic)
**Opprinnelig valgt:** Anthropic API (Claude). **Endret 2026-09-27:** Anthropic krever betalingskort og kreditt selv for testbruk («credit balance too low» ved første ekte kall); Gemini har et ekte gratis nivå uten kort. Byttet til Google Gemini (`gemini-2.5-flash` som standard, se `CHATBOT_MODEL`-miljøvariabelen for å overstyre).

API-nøkkelen (`GEMINI_API_KEY`) ligger bare på serveren, i en lokal `.env`-fil (gitignored), aldri i nettleseren eller i git.

**Konsekvens for B1/B3:** verktøyoppsettet og systemprompten er uavhengig av hvilken modell som brukes bak `app/chatbot.py`. Skulle vi bytte LLM igjen, er det denne modulen som endres.

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

## Gjennomført (v0, 2026-09-27)

En første fungerende versjon er koblet til `POST /api/chat` (`app/chatbot.py`):

- **Modell:** Google Gemini (`gemini-2.5-flash`), med verktøybruk.
- **Kunnskap:** alle dokumentene i `data/docs` sendes hele i systemprompten (B1s alt-i-prompten-variant), ikke et eget søk ennå.
- **Verktøy:** `sok_produkter` (søk/filter i produktkatalogen) og `hent_ordre` (med samme tilgangsregel som ordresporingen: innlogget kunde ser bare egne ordrer via kundeforholdet, gjest må oppgi ordrenummer **og** e-post).
- **Ikke gjennomført ennå:** `tilby_kundeservice` som eget verktøy og sakslagring (B5, avhenger av A8 i `apne-valg.md`). Boten er foreløpig bedt om å *anbefale* kundeservice i tekst når den er usikker, ikke tilby en egen knapp/handling. Ingen streaming, ingen synlige kildehenvisninger i selve UI-et (kilder nevnes bare i brødteksten når modellen velger å ta dem med).
- **Uten API-nøkkel** viser chatten en forklarende feilmelding i stedet for å krasje eller vise stubb-tekst.

## Planlagt rekkefølge videre

1. **Evalueringssett:** spørsmål med fasit, hentet fra de bevisste fallgruvene i README. Se [eval/](../eval/) (laget, ikke kjørt mot v0 ennå).
2. **Kjør v0 mot evalueringssettet** og noter resultatet, som ny referanse (i praksis nå Gemini + alt-i-prompten, ikke bare et tankeeksperiment).
3. **RAG over dokumentene** med kilder, målt mot v0-referansen over.
4. **`tilby_kundeservice`-verktøy og sakslagring** (B5/A8), deretter finpuss av vinduet (streaming, synlige kilder i UI).
