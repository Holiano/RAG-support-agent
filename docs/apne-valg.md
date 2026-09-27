# Åpne valg

Valg som ikke er tatt ennå. Når et valg avgjøres, flyttes det til [chatbot-beslutninger.md](chatbot-beslutninger.md) med dato og begrunnelse. Sist oppdatert 2026-09-27.

Oversikt:

| # | Valg | Haster | Anbefaling |
|---|---|---|---|
| A1 | Embeddings: hvilken modell/API | Nei, etter BM25 | Utsett og mål |
| A2 | Skal agenten kunne utføre handlinger? | Nei | Bare lesing først |
| A3 | Hvilken Gemini-modell? | Ved steg 2 | `gemini-2.5-flash` er standard i v0; endelig valg med eval |
| A4 | Hvordan måles svarkvalitet? | Ved steg 1 | Fasit + LLM-vurdering |
| A5 | Samtalehistorikk: hvor lagres den? | Ved steg 3 | v0: klienten sender historikken (midlertidig). Bør bli server-side |
| A6 | Streaming av svar i vinduet | Ved steg 3 | SSE |
| A7 | Dagens dato til agenten | *Gjennomført i v0* | Sendes i systemprompten |
| A8 | Saksskjema for overlevering | Ved steg 4 | Se under |

---

## A1. Embeddings

Verken Anthropic eller Google Gemini har (per nå) et eget dedikert embedding-API vi har tatt i bruk. Alternativene:

| Alternativ | For | Mot |
|---|---|---|
| **Gemini embedding-API** (`text-embedding-004` e.l.) | Samme konto/nøkkel som resten av boten, gratis nivå | Må sjekke gratisgrensen når vi kommer dit |
| **Lokal modell** (f.eks. `multilingual-e5`) | Gratis, ingen ekstra konto, data forlater ikke maskinen | Tyngre installasjon, kan være tregere |

**Anbefaling:** Utsett valget. Bygg først nøkkelordsøk (BM25), som fungerer uten embeddings, og legg til embeddings som steg to. Da måler vi også hva de faktisk bidrar med. Det er et lite korpus (ca. 60 biter), så vi trenger ikke en vektordatabase; numpy eller sqlite holder.

**Avgjør når:** BM25-resultatene er målt mot evalueringssettet.

## A2. Skal agenten kunne utføre handlinger?

Eksempler: starte en retur, kansellere en ordre som ikke er sendt, bytte adresse.

**Anbefaling:** Bare lesing først. Handlinger krever autentisering, bekreftelsessteg og strengere testing (en feil betyr en feil ordre, ikke bare et feil svar). Kan komme etter at grunnmuren er testet. Med mindre noe annet blir bestemt, gjelder «bare lesing». v0 har bare `sok_produkter` og `hent_ordre`, begge lesing.

## A3. Hvilken Gemini-modell?

En sterkere modell gir bedre resonnering (returfrister, rabattregler), en mindre modell er raskere og har romsligere gratisgrenser. v0 bruker `gemini-2.5-flash` (satt i `CHATBOT_MODEL`-miljøvariabelen i `app/chatbot.py`) som et rimelig utgangspunkt. **Anbefaling:** Kjør evalueringssettet mot `gemini-2.5-flash` og `gemini-2.5-pro` og velg den billigste/raskeste som klarer seg godt nok.

## A4. Hvordan måles svarkvalitet?

Forslag: hvert spørsmål har en fasit og en liste med fakta som må med (`must_include`) og ting som ikke må med (`must_not_include`). Enkle tester sjekker det automatisk. For fritekstsvar kan en LLM vurdere mot fasiten (LLM som dommer). Det må vi teste mot noen håndvurderte svar først, så vi vet at dommeren er til å stole på.

## A5. Samtalehistorikk

Nettleseren sender hele historikken med hver melding (`history` i `POST /api/chat`, se `chat.js`), og v0 videresender den til Gemini uendret. Alternativ: server-side med en samtale-ID. Server-side er tryggere (klienten kan ikke forfalske tidligere svar fra boten) og trengs uansett for å lagre samtalelogg i overleveringssaken (A8).

## A6. Streaming

Uten streaming venter kunden på hele svaret. Med streaming (SSE) vises teksten mens den skrives. Nytt for `chat.js`, og litt mer å teste.

## A7. Dagens dato — gjennomført i v0

Agenten må vite hvilken dag det er for å svare på «kan jeg fortsatt returnere?». Løst: `date.today()` sendes inn i systemprompten fra `app/routes/api.py` ved hvert kall. Gjenstår: evalueringssettets `today`-felt (se `eval/questions.json`) må faktisk brukes når vi kjører v0 mot settet, ikke bare dagens ekte dato — ellers stemmer ikke grensetilfellene O07a/O07b.

## A8. Saksskjema for overlevering

Ikke bygget ennå. v0 har ikke noe `tilby_kundeservice`-verktøy eller sakslagring (se B5 i `chatbot-beslutninger.md`) — boten anbefaler bare kundeservice i teksten sin når den er usikker.

Forslag til tabell `support_tickets`: `id`, `created_at`, `email`, `customer_id` (kan være tom), `order_number` (valgfritt), `summary` (skrevet av boten), `transcript` (JSON), `status` (`ny`).

Åpent: skal kunden kunne legge til en egen melding i tillegg til samtalen? Skal vi vise en liste over egne saker på «Mine sider»?

---

## Andre ting å huske

- Loggføring av samtaler kan inneholde personopplysninger. `data/docs/personvern.md` sier at chatsamtaler lagres i 12 måneder, og sletting må samsvare med det. Gjelder også når A8 bygges.
- Beskyttelse mot misbruk (rate limiting på `/api/chat`) trengs før noe eksponeres utenfor lokal demo.
- v0 har ingen synlig kildehenvisning i selve chat-vinduet (bare i brødteksten når modellen velger å skrive den). Bør bli en strukturert del av svaret (`sources`) når vinduet finpusses (steg 4).
