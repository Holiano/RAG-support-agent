# Åpne valg

Valg som ikke er tatt ennå. Når et valg avgjøres, flyttes det til [chatbot-beslutninger.md](chatbot-beslutninger.md) med dato og begrunnelse. Sist oppdatert 2026-09-26.

Oversikt:

| # | Valg | Haster | Anbefaling |
|---|---|---|---|
| A1 | Embeddings: Voyage API eller lokal modell | Nei, etter BM25 | Utsett og mål |
| A2 | Skal agenten kunne utføre handlinger? | Nei | Bare lesing først |
| A3 | Hvilken Claude-modell? | Ved steg 2 | Velg med eval |
| A4 | Hvordan måles svarkvalitet? | Ved steg 1 | Fasit + LLM-vurdering |
| A5 | Samtalehistorikk: hvor lagres den? | Ved steg 3 | Server-side |
| A6 | Streaming av svar i vinduet | Ved steg 3 | SSE |
| A7 | Dagens dato til agenten | Ved steg 3 | Sendes i systemprompten |
| A8 | Saksskjema for overlevering | Ved steg 3 | Se under |

---

## A1. Embeddings

Anthropic har ikke noe eget embedding-API, så vi må velge en annen vei.

| Alternativ | For | Mot |
|---|---|---|
| **Voyage API** | God flerspråklig kvalitet, enkelt å bruke | Ekstra konto, nøkkel og kostnad |
| **Lokal modell** (f.eks. `multilingual-e5`) | Gratis, ingen ekstra konto, data forlater ikke maskinen | Tyngre installasjon, kan være tregere |

**Anbefaling:** Utsett valget. Bygg først nøkkelordsøk (BM25), som fungerer uten embeddings, og legg til embeddings som steg to. Da måler vi også hva de faktisk bidrar med. Det er et lite korpus (ca. 60 biter), så vi trenger ikke en vektordatabase; numpy eller sqlite holder.

**Avgjør når:** BM25-resultatene er målt mot evalueringssettet.

## A2. Skal agenten kunne utføre handlinger?

Eksempler: starte en retur, kansellere en ordre som ikke er sendt, bytte adresse.

**Anbefaling:** Bare lesing først. Handlinger krever autentisering, bekreftelsessteg og strengere testing (en feil betyr en feil ordre, ikke bare et feil svar). Kan komme etter at grunnmuren er testet. Med mindre noe annet blir bestemt, gjelder «bare lesing».

## A3. Hvilken Claude-modell?

En sterkere modell gir bedre resonnering (returfrister, rabattregler), en mindre modell er raskere og billigere. **Anbefaling:** Bygg modellen som en innstilling, og kjør evalueringssettet mot flere. Velg den billigste som klarer seg.

## A4. Hvordan måles svarkvalitet?

Forslag: hvert spørsmål har en fasit og en liste med fakta som må med (`must_include`) og ting som ikke må med (`must_not_include`). Enkle tester sjekker det automatisk. For fritekstsvar kan en LLM vurdere mot fasiten (LLM som dommer). Det må vi teste mot noen håndvurderte svar først, så vi vet at dommeren er til å stole på.

## A5. Samtalehistorikk

Nå sender nettleseren hele historikken med hver melding (`history` i `POST /api/chat`). Alternativ: server-side med en samtale-ID. Server-side er tryggere og trengs uansett for å lagre samtalelogg i overleveringssaken.

## A6. Streaming

Uten streaming venter kunden på hele svaret. Med streaming (SSE) vises teksten mens den skrives. Nytt for `chat.js`, og litt mer å teste.

## A7. Dagens dato

Agenten må vite hvilken dag det er for å svare på «kan jeg fortsatt returnere?». **Anbefaling:** Send datoen inn i systemprompten fra serveren, og la evalueringssettet fastsette datoen per spørsmål (`today`). Ikke la modellen gjette.

## A8. Saksskjema for overlevering

Forslag til tabell `support_tickets`: `id`, `created_at`, `email`, `customer_id` (kan være tom), `order_number` (valgfritt), `summary` (skrevet av boten), `transcript` (JSON), `status` (`ny`).

Åpent: skal kunden kunne legge til en egen melding i tillegg til samtalen? Skal vi vise en liste over egne saker på «Mine sider»?

---

## Andre ting å huske

- Loggføring av samtaler kan inneholde personopplysninger. `data/docs/personvern.md` sier at chatsamtaler lagres i 12 måneder, og sletting må samsvare med det.
- Beskyttelse mot misbruk (rate limiting på `/api/chat`) trengs før noe eksponeres utenfor lokal demo.
- Chat-stubben i `app/config.py` er skrevet på nynorsk og byttes ut.
