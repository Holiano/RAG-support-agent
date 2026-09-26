# Vindhamar Friluft – demo-nettbutikk

En oppdiktet norsk nettbutikk for friluftsutstyr. Butikken er en **testbenk for en AI-kundeserviceagent** som skal bygges senere, så datagrunnlaget (produkter, ordrer, policydokumenter) er viktigere enn designet.

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

**Chat:** knappen nede til høyre åpner et chatvindu som sender `POST /api/chat` med `{"message": "...", "history": [...]}`. Stubben ligger i [app/routes/api.py](app/routes/api.py) og returnerer `{"reply": "Kundeservice-agenten er ikkje kopla til enno."}`. Bytt ut funksjonen `chat()` med agenten.

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
data/              all data (eneste kilde til sannhet)
seed.py            bygger shop.db fra /data
tests/smoke_test.py
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

Sidene rendres **direkte fra markdown-filene** i `data/docs` (endringer vises uten omstart), slik at nettsiden og en senere RAG-løsning bruker nøyaktig samme tekst. `seed.py` legger samtidig en kopi av tekstene i tabellen `docs`.

`retur-og-bytte`, `frakt-og-levering`, `garanti-og-reklamasjon`, `betaling`, `storleiksguide`, `vedlikehald`, `personvern`, `om-oss`, `kontakt`, `faq`.

### Vanskelige detaljer for RAG-agenten (med vilje)

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
- Skjemaer har ikke CSRF-beskyttelse; dette er en lokal demobutikk.
- `DB_PATH` kan settes som miljøvariabel for å bruke en annen databasefil.
