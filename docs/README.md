# Prosjektdokumentasjon

Dette er dokumentasjon **om prosjektet**: beslutninger, åpne valg og planer for kundeservice-chatboten.

> Ikke forveksle med [data/docs/](../data/docs/). Der ligger butikkens policy- og infosider (retur, frakt, garanti osv.). De vises på nettsiden og er kunnskapsgrunnlaget til chatboten. Filene her i `docs/` skal **ikke** indekseres av chatboten.

| Fil | Innhold |
|---|---|
| [chatbot-beslutninger.md](chatbot-beslutninger.md) | Valg som er tatt, med begrunnelse |
| [apne-valg.md](apne-valg.md) | Valg som ikke er tatt ennå, med alternativer og anbefaling |

Slik holder vi oversikten:

- Når et åpent valg avgjøres, flyttes det fra `apne-valg.md` til `chatbot-beslutninger.md` med dato og begrunnelse.
- Nye spørsmål som dukker opp underveis, legges inn i `apne-valg.md` med en gang, også når de ikke haster.
- Evalueringssettet ligger i [eval/](../eval/).
