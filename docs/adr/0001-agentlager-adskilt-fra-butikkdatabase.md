---
status: accepted
date: 2026-10-01
---

# Agentens data lagres adskilt fra butikkens database

Kundeserviceagenten skal betjene flere butikker, og i produksjon eier vi ikke butikkenes systemer. Derfor lagres agentens egne data (tekstbiter med embeddinger, samtalelogg, butikkregister) i en egen Postgres-database med pgvector (Supabase), mens demobutikken forblir på SQLite i `shop.db`. Agenten når butikkdata utelukkende gjennom verktøy, aldri ved å lese butikkens tabeller direkte. To databaser er valgt bevisst for å gjøre den snarveien umulig, ikke fordi det er teknisk nødvendig.

## Vurderte alternativer

- **Alt i Supabase, med skjemaskille.** Mindre å drifte, men krever omskriving av butikkens databaselag fra sqlite3 til Postgres, gjør butikken avhengig av nett, og grensen mellom agent og butikk må da håndheves med disiplin i stedet for med arkitektur.
- **sqlite-vec lokalt for agenten.** Ingen ekstern avhengighet, men utsetter læringen om vektorsøk i Postgres, som er det produksjonsversjonen vil bruke.

## Konsekvenser

- Utvikling av agenten krever nett og en Supabase-nøkkel i `.env`. Butikken kan fortsatt kjøres uten.
- Alle agentens tabeller har `shop_id`. Demobutikken er butikk 1.
- En ny butikk med et annet system kobles til ved å skrive nye verktøy, ikke ved å endre agenten.
