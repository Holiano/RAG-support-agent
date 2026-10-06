# Kundeserviceagent

Agenten svarer kunder i en nettbutikks chat ut fra butikkens egne dokumenter og data. Den bygges som pilot på demobutikken Vindhamar Friluft og skal kunne betjene flere butikker på samme plattform.

## Language

### Agenten

**Kundeserviceagent**:
Det vi bygger: en samtalepartner som svarer på kundespørsmål for én butikk, grunnet i butikkens kunnskapsbase og data.
_Unngå_: chatbot, support-agent, bot

**Butikk**:
Én leietaker i agenten, med egen kunnskapsbase, egne produkter og ordrer, og egen identitet.
_Unngå_: tenant, kunde (om butikken), shop

**Kunnskapsbase**:
En butikks policy- og infodokumenter, det eneste agenten får uttale seg om som fakta.
_Unngå_: docs, infosider, dokumentasjon

**Tekstbit**:
Én overskriftsseksjon fra et dokument i kunnskapsbasen, lagret med embedding slik at den kan hentes ved søk.
_Unngå_: chunk, passasje, segment

**Verktøy**:
En navngitt funksjon agenten kan be om å få kjørt mot butikkens system, for eksempel å hente en ordre. Verktøy er agentens eneste vei til butikkdata.
_Unngå_: function, tool, API-kall

**Verifisert kunde**:
En kunde som har bevist eierskap til en ordre, enten ved innlogging eller ved ordrenummer sammen med e-postadressen på ordren. Bare en verifisert kunde får se ordredata.
_Unngå_: autentisert bruker, innlogget (når ordrenummer og e-post er brukt)

**Samtale**:
Én chatøkt mellom en kunde og agenten, bestående av meldinger fra kunden og svar fra agenten.
_Unngå_: sesjon, tråd, chat

**Testsett**:
Spørsmål til agenten med forventede fakta i svaret, brukt til å måle om agenten svarer riktig.
_Unngå_: gullsett, eval, golden set

### Butikkdomene

Begreper fra kunnskapsbasen som agenten må holde fra hverandre.

**Returrett**:
Kundens rett til å returnere en vare uten begrunnelse innen en frist. Butikken gir 30 dager; loven gir 14.
_Unngå_: angrerett (bruk bare om den lovfestede 14-dagersretten)

**Bytte**:
En retur der kunden får en annen variant eller vare i stedet for penger tilbake.

**Reklamasjon**:
Kundens lovfestede rett til å klage på en feil eller mangel ved varen. Fristen er 2 eller 5 år avhengig av kategori.
_Unngå_: garanti, klage

**Garanti**:
Butikkens frivillige tillegg til reklamasjonsretten, med egen frist per kategori. Kommer i tillegg til, aldri i stedet for, reklamasjon.
_Unngå_: reklamasjon

**Ordre**:
Et kjøp med ordrenummer, linjer, fraktmetode og statushistorikk.
_Unngå_: bestilling, kjøp, handel
