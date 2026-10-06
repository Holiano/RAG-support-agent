# Vindhamar Friluft – demo-nettbutikk med kundeserviceagent

En oppdiktet norsk nettbutikk for friluftsutstyr, og en **kundeserviceagent** som svarer i chatten ut fra butikkens dokumenter og data. Butikken er testbenk for agenten, så datagrunnlaget (produkter, ordrer, policydokumenter) er viktigere enn designet. Begrepene står i [CONTEXT.md](CONTEXT.md), arkitekturvalgene i [docs/adr](docs/adr).

> Demobutikk. Ingen ekte kjøp. Ingen ekte betaling, ingen eksterne bilder, og navn og merker er oppdiktet.

## Kom i gang

Krever Python 3.11+.

```bash
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

Åpne <http://127.0.0.1:8000>. Tailwind lastes fra CDN, så du må ha nettilgang for at styling skal vises.

`python seed.py` bygger databasen (`shop.db`) på nytt fra `/data`, og sletter alle endringer gjort i appen (nye ordrer, ønskelister, lagerbeholdning). Kjør den når du vil nullstille.

Røyktest (bruker en midlertidig database): `python tests/smoke_test.py`

### Demobrukere

Passord for alle: `demo123`

| Navn | E-post | Sted |
|---|---|---|
| Ingrid Solberg | ingrid.solberg@example.com | Voss |
| Ola Kvamme | ola.kvamme@example.com | Oslo |
| Marte Haugland | marte.haugland@example.com | Trondheim |
| Sindre Nilsen | sindre.nilsen@example.com | Tromsø |
| Hilde Berge | hilde.berge@example.com | Kristiansand |

### Rabattkoder

| Kode | Regel |
|---|---|
| `VELKOMMEN10` | 10 % på varer til ordinær pris (ikke tilbudsvarer). Gyldig ut 2026. |
| `SOMMAR200` | 200 kr rabatt ved varesum på minst 1 500 kr. Gyldig til 31.10.2026. |
| `VAR2026` | 15 %, **utløpt** 31.05.2026. |

## Funksjoner

Forside, produktliste med søk/filter/sortering, produktside (varianter, lager, spesifikasjoner, vaskeråd, anmeldelser, relaterte produkter), handlekurv (antall, rabattkode, frakt, framdrift mot fri frakt), kasse uten betaling, ordrebekreftelse, innlogging og Mine sider, ordresporing uten innlogging (`/sporing`, ordrenummer + e-post), ønskeliste, infosider fra markdown, og en chatknapp.

**Chat:** knappen nede til høyre åpner et chatvindu som sender `POST /api/chat` med `{"message": "...", "history": [...]}`. Er agenten konfigurert (se under), svarer den. Ellers svarer stubben `{"reply": "Kundeserviceagenten er ikke koblet til ennå."}`.

## Kundeserviceagenten

Agenten ligger i `app/agent/` og kalles fra `chat()` i [app/routes/api.py](app/routes/api.py). Den henter de mest relevante tekstbitene fra kunnskapsbasen (`data/docs`), kaller Gemini med verktøy for ordre- og produktoppslag, og logger hver melding. Butikkens database røres bare gjennom verktøyene, aldri direkte (se [ADR 0001](docs/adr/0001-agentlager-adskilt-fra-butikkdatabase.md)).

### Oppsett

1. **Gemini-nøkkel:** lag en nøkkel i Google AI Studio.
2. **Database for agenten:** lag et Supabase-prosjekt (gratis holder) og kopier Postgres-URI-en fra *Connect* i prosjektet. Skjemaet (`agent.shops`, `agent.chunks`, `agent.chat_log`) og pgvector-utvidelsen opprettes automatisk av indekseringen. Merk om nett: direktetilkoblingen (`db.<ref>.supabase.co`) finnes bare på IPv6. Har nettet ditt ikke IPv6, bruk *Session pooler*-URI-en (vert `aws-0-<region>.pooler.supabase.com`, port 5432, bruker `postgres.<ref>`). Noen bedriftsnett blokkerer port 5432 og 6543 helt; da må du bytte nett.
3. Kopier `example.env` til `.env` og fyll inn `GEMINI_API_KEY` og `AGENT_DB_URL`.
4. Indekser kunnskapsbasen:

```bash
python index_docs.py --dry-run   # vis tekstbitene uten nett
python index_docs.py             # embed og lagre (bare nye og endrede tekstbiter embeddes)
```

Kjør `index_docs.py` på nytt når et dokument i `data/docs` endres. Start deretter appen som vanlig; chatten bruker agenten så snart begge miljøvariablene er satt.

Innstillinger (miljøvariabler, standard i parentes): `AGENT_CHAT_MODEL` (`gemini-3.8-flash`), `AGENT_EMBEDDING_MODEL` (`gemini-embedding-2`), `AGENT_EMBEDDING_DIM` (768), `AGENT_SHOP_ID` (1), `AGENT_TOP_K` (6), `AGENT_REQUEST_TIMEOUT_MS` (90000).

### Slik svarer den

- Svarer på bokmål og bare om butikken. Fakta kommer fra tekstbitene eller verktøyene; finner den ikke svaret, sier den det og henviser til kundeservice.
- **Verktøy:** `hent_ordre`, `mine_ordrer`, `sok_produkter`, `hent_produkt`, `hent_rabattkode`. Verifisering skjer i verktøyet ved hvert kall: innloggede kunder får bare egne ordrer, uinnloggede må oppgi ordrenummer og e-post som stemmer overens (samme regel som `/sporing`).
- **Flere butikker:** alle agentens tabeller har `shop_id`. Demobutikken er butikk 1.
- **Logg:** `agent.chat_log` får spørsmål, hentede tekstbiter, verktøykall, svar, latens og tokenforbruk per melding.

### Testsett

[tests/testsett.json](tests/testsett.json) har 39 spørsmål som dekker fellene under, med forventede fakta og en fasit. [tests/kjor_testsett.py](tests/kjor_testsett.py) kjører dem mot agenten, sjekker fakta maskinelt, lar en modell dømme svaret mot fasiten (0, 1 eller 2 poeng) og skriver rapport til `tests/rapporter/`.

```bash
python tests/kjor_testsett.py                              # vektorsøk, standardmodell
python tests/kjor_testsett.py --modell gemini-3.5-flash-lite
python tests/kjor_testsett.py --retriever alt-lokalt       # alle tekstbiter i kontekst, referanse uten database
python tests/kjor_testsett.py --bare ordre-returfrist --uten-dommer
```

## Kodestruktur

```
app/
  main.py          FastAPI-app, sesjon (cookie), ruter, feilsider
  db.py            sqlite3-tilgang og databaseskjema
  catalog.py       produkter, søk, filter, sortering
  pricing.py       rabattkoder, frakt, fri frakt, leveringstid per landsdel
  cart.py          handlekurv i sesjon
  orders.py        opprette og hente ordrer
  docs.py          rendrer data/docs/*.md til HTML
  auth.py          innlogging (PBKDF2)
  images.py        genererte SVG-plasshaldarer (farge + kategoriikon)
  routes/          pages, cart, checkout, account, api
  templates/       Jinja2
  static/          css og js (chat.js, app.js)
  agent/           kundeserviceagenten
    agent.py       verktøyløkke mot Gemini, logging
    prompt.py      systeminstruksjon og oppbygging av meldingen
    tools.py       verktøy mot butikkens data (med verifisering)
    retriever.py   vektorsøk / alt-i-kontekst bak samme grensesnitt
    chunking.py    markdown -> tekstbiter per overskrift
    embeddings.py  Gemini-embeddinger
    gemini.py      delt Gemini-klient med tidsfrist per kall
    store.py       agentens Postgres-lager (tekstbiter, logg, butikker)
    schema.sql     tabellene i skjemaet agent
    settings.py    miljøvariabler
data/              all data (eneste kilde til sannhet)
seed.py            bygger shop.db fra /data
index_docs.py      indekserer kunnskapsbasen i agentens database
tests/smoke_test.py
tests/testsett.json, tests/kjor_testsett.py
```

## Datastruktur

All data ligger i `/data` og lastes inn i SQLite av `seed.py`.

| Fil | Innhold |
|---|---|
| `products.json` | 20 produkter i 5 kategorier (`jakker`, `sko`, `sekker`, `telt-sovepose`, `tilbehor`): `id`, `slug`, `name`, `category`, `price`, `sale_price` (eller `null`), `sku`, `description` (150–300 ord), `specs`, `care`, `warranty_years`, `added`, `featured`, `image_color` og `variants` (`sku`, `size`, `color`, `stock`). |
| `reviews.json` | 2–4 anmeldelser per produkt. Alle har `"is_demo_data": true`. |
| `customers.json` | 5 kunder med adresse og passord `demo123` (hashes i databasen). |
| `orders.json` | 15 ordrer (juni–sept. 2026) med `lines`, `shipping_method`, `shipping_cost`, `discount_code`, `discount_amount`, `subtotal`, `total`, `tracking_number`, `refund_amount` og `status_history`. |
| `discount_codes.json` | 3 rabattkoder (prosent, kroner med minstesum, utløpt). |
| `docs/*.md` | Policy- og infosider. |

**Ordrestatuser:** `mottatt`, `under_pakking`, `sendt`, `levert`, `kansellert`, `retur_under_behandling`, `refundert`.
**Fraktmetoder:** `hentested` (49 kr), `hjemlevering` (99 kr), `ekspress` (199 kr).
**Lagerstatus** utledes av `stock`: 0 = utsolgt, 1–3 = få igjen, ellers på lager.

Databasetabeller: `products`, `variants`, `reviews`, `customers`, `orders`, `order_lines`, `order_status_history`, `discount_codes`, `wishlist` og `docs`. Skjemaet ligger i [app/db.py](app/db.py).

### Infosidene (`/info/<navn>`)

Sidene rendres **direkte fra markdown-filene** i `data/docs` (endringer vises uten omstart), slik at nettsiden og agenten bruker nøyaktig samme tekst. `seed.py` legger samtidig en kopi av tekstene i tabellen `docs`.

`retur-og-bytte`, `frakt-og-levering`, `garanti-og-reklamasjon`, `betaling`, `storrelsesguide`, `vedlikehold`, `personvern`, `om-oss`, `kontakt`, `faq`.

### Vanskelige detaljer for agenten (med vilje)

Dokumentene skal ikke motsi hverandre, men noen svar krever nøye lesing:

- **14 vs. 30 dager:** 30 dagers returrett (utvidet angrerett, lovfestet er 14), 14 dager til å sende varen etter meldt retur, 14 dager hentefrist på hentested, 14 dager fakturafrist, refusjon senest 14 dager etter mottatt retur.
- **Julereturen:** kjøp 1. nov.–24. des. kan returneres til 31. jan.
- **Unntak bare i ett dokument:** hygieneprodukter (uåpnet ullsokk), telt satt opp utendørs, «Sluttsalg» kan ikke byttes, Svalbard/Jan Mayen (postnummer blokkert i kassen), sesong- og helligdagsåpningstider.
- **Kategoriavhengige regler:** garanti (1/2/3/5 år) er noe annet enn reklamasjonsfrist (2 eller 5 år, sekker deles på 40 liter). Hodelykt har 2 års garanti mens resten av tilbehør har 1 år.
- **Fri frakt:** 1 200 kr regnet *etter* rabatt, gjelder ikke ekspress.
- **Rabattkoder:** prosentkoder gjelder ikke tilbudsvarer, kronekoder har minstesum, én kode per ordre.
- **Størrelser:** Snøgg faller små (gå opp én), Storhaugen normalt (opp én ved tykke sokker), Frost har romslig lest (ikke gå opp), unisex-jakker følger herretabellen.
- **Ordredata:** blant annet en ordre der returfristen utløper 26.09.2026 (`VH-10010`), en retur under behandling (`VH-10011`), en refusjon med fratrukket returfrakt (`VH-10005`) og en kansellert ordre (`VH-10006`).

## Merknader

- Sesjonscookien er signert. Sett `SECRET_KEY` som miljøvariabel utenfor lokal demo.
- `.env` (Gemini-nøkkel og database-URI) er ignorert av git. Del aldri nøklene.
- Skjemaer har ikke CSRF-beskyttelse; dette er en lokal demobutikk.
- `DB_PATH` kan settes som miljøvariabel for å bruke en annen databasefil.
