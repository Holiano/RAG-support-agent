"""Felles konstanter for butikken."""

SHOP_NAME = "Vindhamar Friluft"

CATEGORIES = [
    ("jakker", "Jakker", "Skall, dun og fleece for alt slags vær"),
    ("sko", "Sko", "Fra lette terrengsko til varme vintersko"),
    ("sekker", "Sekker", "Dagstur, helgetur og ekspedisjon"),
    ("telt-sovepose", "Telt og sovepose", "Overnatting ute, hele sesongen"),
    ("tilbehor", "Tilbehør", "Det lille som gjør turen bedre"),
]
CATEGORY_LABELS = {slug: label for slug, label, _ in CATEGORIES}

STATUS = {
    "mottatt": ("Mottatt", "bg-sky-100 text-sky-800"),
    "under_pakking": ("Under pakking", "bg-amber-100 text-amber-800"),
    "sendt": ("Sendt", "bg-indigo-100 text-indigo-800"),
    "levert": ("Levert", "bg-emerald-100 text-emerald-800"),
    "kansellert": ("Kansellert", "bg-stone-200 text-stone-700"),
    "retur_under_behandling": ("Retur under behandling", "bg-orange-100 text-orange-800"),
    "refundert": ("Refundert", "bg-purple-100 text-purple-800"),
}

# Rekkefølge og titler for infosidene i footer. Filer i data/docs som ikke står her, blir lagt til til slutt.
DOC_ORDER = [
    "retur-og-bytte", "frakt-og-levering", "garanti-og-reklamasjon", "betaling", "storrelsesguide",
    "vedlikehold", "faq", "kontakt", "om-oss", "personvern",
]

CHAT_STUB_REPLY = "Kundeserviceagenten er ikke koblet til ennå."
