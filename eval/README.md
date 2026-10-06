# Evalueringssett (utkast fra september 2026)

[questions.json](questions.json) er et **utkast** på 58 spørsmål med fasit, laget for et tidligere chatbot-forsøk. Det aktive testsettet er [tests/testsett.json](../tests/testsett.json), som kjøres med `tests/kjor_testsett.py`. Spørsmålene her er beholdt fordi de kan flettes inn der. Det skal brukes til å måle om hver endring i boten gjør den bedre eller dårligere. **Fasitene må leses og godkjennes av deg før vi stoler på dem.**

## Felter

| Felt | Betydning |
|---|---|
| `id` | Unik id. Bokstaven viser gruppen (D, P, K, O, E). |
| `category` | `dokument`, `produkt`, `beregning`, `ordre` eller `grense` |
| `question` | Spørsmålet slik kunden skriver det |
| `login_as` | E-post til innlogget demokunde, eller `null` for gjest |
| `today` | Dagens dato i testen. Boten skal få den i systemprompten, og svarene (returfrister) avhenger av den. |
| `expected` | Fasit i vanlig tekst |
| `key_facts` | Fakta som må være med i svaret. Dette er det som sjekkes. |
| `must_not` | Ting som ikke skal stå i svaret (feil tall, informasjon som ikke skal lekke) |
| `sources` | Hvor svaret finnes: dokument i `data/docs`, produktdata, ordredata eller rabattkodedata |
| `expect_handoff_offer` | `true` hvis boten skal tilby å sende saken til kundeservice |
| `notes` | Hvorfor spørsmålet er med, eller spesielle forhold |

## Hva settet dekker

| Gruppe | Antall | Hva den tester |
|---|---|---|
| D, dokument | 23 | Svar som ligger i policydokumentene. Mange har med vilje tall som ligner (14 og 30 dager), unntak som bare står ett sted og sesongregler. |
| P, produkt | 7 | Oppslag i produktdata: lager, tilbud, spesifikasjoner |
| K, beregning | 8 | Regler som avhenger av kategori eller tall: fri frakt etter rabatt, rabattkoder, reklamasjonsfrist per volum |
| O, ordre | 11 | Ordreoppslag, tilgangskontroll (ikke lekke andres ordrer) og returfrister mot dagens dato, også grensetilfellet siste dag (O07a) og dagen etter (O07b) |
| E, grense | 9 | Når boten skal tilby kundeservice, avslå, spørre tilbake, motstå prompt injection og svare på bokmål |

`expect_handoff_offer` er satt på 9 av spørsmålene.

## Viktig å vite

- **Kjør mot en fersk database.** Lagertall og ordrenummer gjelder rett etter `python seed.py`. Testbestillinger i nettbutikken endrer lager, og den neste ordren blir `VH-10016`.
- **Fasit er avledet fra `data/`.** Endres policydokumentene eller dataene, må de berørte fasitene oppdateres. Ordrespørsmålene (O) og beregningene (K) er mest følsomme.
- **Dagens dato er 2026-09-26** i utkastet, samme som seed-dataene er laget rundt. O06–O08 er regnet ut fra den datoen.
- **Fritekstsvar** kan ikke sjekkes med enkel strengsammenligning. `tests/kjor_testsett.py` løser det med faktasjekk pluss en modell som dømmer mot fasit og kunnskapsbase.
