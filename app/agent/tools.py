"""Verktøyene agenten kan be om å få kjørt. Dette er agentens eneste vei til butikkens data.

Verifisering av kunde skjer her, ved hvert kall: en uinnlogget kunde får bare ut en ordre når ordrenummer og
e-post stemmer overens, og en innlogget kunde får bare ut egne ordrer. Modellen stoles aldri på for dette.
"""
from dataclasses import dataclass
from datetime import date

from .. import catalog, orders
from ..config import CATEGORY_LABELS, STATUS
from ..db import query_one

MAX_SEARCH_HITS = 8


@dataclass
class ToolContext:
    customer: dict | None  # innlogget kunde fra sesjonen, eller None
    today: date


DECLARATIONS = [
    {
        "name": "hent_ordre",
        "description": ("Henter én ordre med status, varelinjer, beløp, sporingsnummer og historikk. Innloggede kunder "
                        "kan hente egne ordrer med bare ordrenummer. Uinnloggede kunder må oppgi både ordrenummer og "
                        "e-postadressen ordren ble lagt inn med; be om begge før du kaller verktøyet."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ordrenummer": {"type": "STRING", "description": "Ordrenummer, for eksempel VH-10010."},
                "epost": {"type": "STRING", "description": "E-postadressen på ordren. Påkrevd når kunden ikke er innlogget."},
            },
            "required": ["ordrenummer"],
        },
    },
    {
        "name": "mine_ordrer",
        "description": ("Lister ordrene til den innloggede kunden, nyeste først, med ordrenummer, dato, status og sum. "
                        "Bruk når en innlogget kunde spør om «pakken min» eller «ordren min» uten ordrenummer. "
                        "Virker ikke for uinnloggede kunder."),
    },
    {
        "name": "sok_produkter",
        "description": "Søker i produktkatalogen og returnerer inntil 8 treff med pris, tilbudspris og lagerstatus.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "sokeord": {"type": "STRING", "description": "Ett eller flere ord fra produktnavn, kategori eller beskrivelse."},
                "kategori": {"type": "STRING", "description": "Begrens til kategori.", "enum": list(CATEGORY_LABELS)},
                "kun_pa_lager": {"type": "BOOLEAN", "description": "Bare produkter som har minst én variant på lager."},
            },
        },
    },
    {
        "name": "hent_produkt",
        "description": ("Henter alle detaljer om ett produkt: beskrivelse, spesifikasjoner, vaskeråd, garanti og alle "
                        "varianter med størrelse, farge og antall på lager."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "produkt": {"type": "STRING", "description": "Produktets slug fra sok_produkter, eller produktnavnet."},
            },
            "required": ["produkt"],
        },
    },
    {
        "name": "hent_rabattkode",
        "description": "Slår opp en rabattkode og sier om den er gyldig i dag, hva den gir og hvilke vilkår som gjelder.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"kode": {"type": "STRING", "description": "Rabattkoden slik kunden skrev den."}},
            "required": ["kode"],
        },
    },
]


# ---- Visninger: det modellen får se. Ingen interne id-er eller fulle adresser. ----

def _order_view(o: dict) -> dict:
    delivered = next((h["at"] for h in reversed(o["history"]) if h["status"] == "levert"), None)
    return {
        "ordrenummer": o["order_number"],
        "bestilt": o["created_at"],
        "status": o["status"],
        "status_tekst": STATUS.get(o["status"], (o["status"],))[0],
        "levert": delivered,
        "fraktmetode": o["shipping_method"],
        "frakt_kr": o["shipping_cost"],
        "rabattkode": o["discount_code"],
        "rabatt_kr": o["discount_amount"],
        "varesum_kr": o["subtotal"],
        "totalt_kr": o["total"],
        "refundert_kr": o["refund_amount"],
        "sporingsnummer": o["tracking_number"],
        "leveringssted": o["ship_city"],
        "varelinjer": [{"produkt": l["name"], "variant": l["variant_label"], "antall": l["quantity"],
                        "pris_kr": l["unit_price"]} for l in o["lines"]],
        "historikk": [{"status": h["status"], "tidspunkt": h["at"], "merknad": h["note"]} for h in o["history"]],
    }


def _product_summary(p: dict) -> dict:
    return {
        "produkt": p["slug"], "navn": p["name"], "kategori": p["category_label"], "pris_kr": p["price"],
        "tilbudspris_kr": p["sale_price"], "pa_tilbud": p["on_sale"], "lagerstatus": p["stock_text"],
        "garanti_ar": p["warranty_years"], "kort_beskrivelse": p["short_description"],
    }


def _product_detail(p: dict) -> dict:
    d = _product_summary(p)
    d.update({
        "beskrivelse": p["description"], "spesifikasjoner": p["specs"], "vaskerad": p["care"],
        "vurdering": {"snitt": p["avg_rating"], "antall": p["review_count"]},
        "varianter": [{"storrelse": v["size"], "farge": v["color"], "pa_lager": v["stock"], "lagerstatus": v["stock_text"]}
                      for v in p["variants"]],
    })
    return d


# ---- Utførere ----

def hent_ordre(ctx: ToolContext, ordrenummer: str = "", epost: str | None = None) -> dict:
    number = (ordrenummer or "").strip().upper()
    if not number:
        return {"feil": "Ordrenummer mangler."}
    if ctx.customer:
        order = orders.get_order(number)
        if order and order["customer_id"] == ctx.customer["id"]:
            return _order_view(order)
    if epost and epost.strip():
        order = orders.find_for_tracking(number, epost)
        if order:
            return _order_view(order)
        return {"feil": "Fant ingen ordre med denne kombinasjonen av ordrenummer og e-postadresse. "
                        "Be kunden sjekke begge, og ikke oppgi noe om ordren."}
    if ctx.customer:
        return {"feil": "Ordren finnes ikke på kundens konto. Ble den lagt inn som gjest, må kunden oppgi "
                        "e-postadressen ordren ble lagt inn med."}
    return {"feil": "Kunden er ikke innlogget. Be om e-postadressen ordren ble lagt inn med før ordren kan hentes."}


def mine_ordrer(ctx: ToolContext) -> dict:
    if not ctx.customer:
        return {"feil": "Kunden er ikke innlogget. Be om ordrenummer og e-postadresse, og bruk hent_ordre."}
    rows = orders.orders_for_customer(ctx.customer["id"])
    return {"kunde": ctx.customer["name"], "ordrer": [
        {"ordrenummer": o["order_number"], "bestilt": o["created_at"], "status": o["status"],
         "status_tekst": STATUS.get(o["status"], (o["status"],))[0], "totalt_kr": o["total"],
         "varer": [l["name"] for l in o["lines"]]} for o in rows]}


def sok_produkter(ctx: ToolContext, sokeord: str = "", kategori: str | None = None, kun_pa_lager: bool = False) -> dict:
    hits = catalog.filter_products(catalog.list_products(), q=sokeord or "", category=kategori or "",
                                   in_stock=bool(kun_pa_lager))
    tokens = (sokeord or "").lower().split()
    hits.sort(key=lambda p: not all(t in p["name"].lower() for t in tokens))  # treff i navnet først
    return {"antall_treff": len(hits), "produkter": [_product_summary(p) for p in hits[:MAX_SEARCH_HITS]]}


def hent_produkt(ctx: ToolContext, produkt: str = "") -> dict:
    needle = (produkt or "").strip().lower()
    if not needle:
        return {"feil": "Produkt mangler."}
    products = catalog.list_products()
    match = next((p for p in products if p["slug"] == needle), None) \
        or next((p for p in products if p["name"].lower() == needle), None) \
        or next((p for p in products if needle in p["name"].lower()), None)
    if not match:
        return {"feil": f"Fant ikke noe produkt som matcher «{produkt}». Prøv sok_produkter."}
    return _product_detail(match)


def hent_rabattkode(ctx: ToolContext, kode: str = "") -> dict:
    row = query_one("SELECT * FROM discount_codes WHERE upper(code) = ?", ((kode or "").strip().upper(),))
    if row is None:
        return {"feil": f"Rabattkoden «{kode}» finnes ikke."}
    valid_from, valid_to = date.fromisoformat(row["valid_from"]), date.fromisoformat(row["valid_to"])
    return {
        "kode": row["code"], "type": "prosent" if row["type"] == "percent" else "kroner", "verdi": row["value"],
        "minste_varesum_kr": row["min_subtotal"], "gyldig_fra": row["valid_from"], "gyldig_til": row["valid_to"],
        "gjelder_ikke_tilbudsvarer": bool(row["excludes_sale_items"]), "beskrivelse": row["description"],
        "gyldig_i_dag": valid_from <= ctx.today <= valid_to,
    }


EXECUTORS = {
    "hent_ordre": hent_ordre, "mine_ordrer": mine_ordrer, "sok_produkter": sok_produkter,
    "hent_produkt": hent_produkt, "hent_rabattkode": hent_rabattkode,
}


def execute(name: str, args: dict, ctx: ToolContext) -> dict:
    fn = EXECUTORS.get(name)
    if fn is None:
        return {"feil": f"Ukjent verktøy: {name}"}
    try:
        return fn(ctx, **args)
    except TypeError as e:
        return {"feil": f"Ugyldige argumenter til {name}: {e}"}
    except Exception as e:  # noqa: BLE001 - feilen skal tilbake til modellen, ikke velte svaret
        return {"feil": f"{name} feilet: {type(e).__name__}: {e}"}
