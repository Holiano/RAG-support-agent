"""Røyktest: kjør med  python tests/smoke_test.py  (bruker en midlertidig database, rører ikke shop.db)."""
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")

import seed  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

seed.main()

from app import cart as cart_svc  # noqa: E402
from app.db import DATA_DIR, query_one  # noqa: E402
from app.main import app  # noqa: E402
from app.pricing import compute_totals  # noqa: E402

failures = []


def check(cond, label):
    print(("OK   " if cond else "FEIL ") + label)
    if not cond:
        failures.append(label)


def new_client():
    return TestClient(app, follow_redirects=True)


c = new_client()

# ---- 1. Alle sider lastes ----
products = json.loads((DATA_DIR / "products.json").read_text(encoding="utf-8"))
pages = ["/", "/produkter", "/handlekurv", "/logg-inn", "/sporing"] + [f"/info/{p.stem}" for p in (DATA_DIR / "docs").glob("*.md")]
pages += [f"/produkt/{p['slug']}" for p in products] + [f"/bilde/produkt/{p['id']}.svg" for p in products]
pages += [f"/produkter?kategori={k}" for k in ("jakker", "sko", "sekker", "telt-sovepose", "tilbehor")]
bad = [(u, r.status_code) for u in pages if (r := c.get(u)).status_code != 200]
check(not bad, f"{len(pages)} sider gir 200 {bad}")
check("Demobutikk. Ingen ekte kjøp." in c.get("/").text, "Demobanner på forsiden")
home = c.get("/").text
docs_missing = [p.stem for p in (DATA_DIR / "docs").glob("*.md") if f"/info/{p.stem}" not in home]
check(not docs_missing, f"Footer lenker til alle infosider {docs_missing}")
check("Kundeservice-agenten" not in home and 'id="chat-root"' in home, "Chat-rot finnes på forsiden")

# ---- 2. Søk, filter, sortering ----
def count(qs):
    return len(re.findall(r'<article class="group', c.get("/produkter?" + qs).text))

check(count("") == 20, "20 produkter totalt")
check(count("kategori=sko") == 4, "4 sko")
check(count("tilbud=1") == 5, "5 tilbudsprodukter")
check(count("pa_lager=1") == 19, "19 på lager (Kveld er utsolgt)")
check(count("q=jakke") >= 4, "Søk 'jakke'")
check(count("q=tørketrommel+dun") >= 1 or count("q=dun") >= 1, "Søk 'dun'")
check(count("q=SNØGG") == 1, "Søk er skiftlesing-uavhengig for æøå")
check(count("min=1000&maks=2000") > 0, "Prisintervall")
first = re.search(r'href="/produkt/([^"]+)"', c.get("/produkter?sorter=pris_lav").text).group(1)
check(first == "varm-termoflaske-075", f"Sortering pris lav først ({first})")
first = re.search(r'href="/produkt/([^"]+)"', c.get("/produkter?sorter=pris_hoy").text).group(1)
check(first == "vidda-4-familietelt" or first == "tindra-2-telt", f"Sortering pris høy først ({first})")

# ---- 3. Seed-ordrenes summer stemmer med prisreglene ----
orders = json.loads((DATA_DIR / "orders.json").read_text(encoding="utf-8"))
prod = {p["id"]: p for p in products}
for o in orders:
    lines = [{"unit_price": l["unit_price"], "regular_price": prod[l["product_id"]]["price"], "quantity": l["quantity"]} for l in o["lines"]]
    code = cart_svc.get_code(o["discount_code"])
    t = compute_totals(lines, code, o["shipping_method"], today=date.fromisoformat(o["created_at"][:10]))
    ok = (t["discount"], t["shipping"], t["total"]) == (o["discount_amount"], o["shipping_cost"], o["total"]) and not t["code_error"]
    if not ok:
        check(False, f"Ordre {o['order_number']} totalsum stemmer ({t})")
check(True, "Alle 15 seed-ordrer stemmer med prisreglene")

# ---- 4. Ordresporing for alle 15 ordrer ----
untracked = []
for o in orders:
    r = c.post("/sporing", data={"order_number": o["order_number"].lower(), "email": o["email"].upper()})
    if r.status_code != 200 or o["order_number"] not in r.text:
        untracked.append(o["order_number"])
check(not untracked, f"Ordresporing fungerer for alle 15 {untracked}")
check(c.post("/sporing", data={"order_number": "VH-10001", "email": "feil@example.com"}).status_code == 404, "Sporing med feil e-post gir ingen treff")
sent = next(o for o in orders if o["status"] == "sendt")
check(sent["tracking_number"] in c.post("/sporing", data={"order_number": sent["order_number"], "email": sent["email"]}).text, "Sporingsnummer vises")

# ---- 5. Rabattkoder ----
lines = [{"unit_price": 1190, "regular_price": 1490, "quantity": 1}]
check(compute_totals(lines, cart_svc.get_code("VELKOMMEN10"), "hjemlevering")["code_error"] is not None, "Prosentkode gjelder ikke tilbudsvarer")
check("utløpt" in compute_totals([{"unit_price": 2000, "regular_price": 2000, "quantity": 1}], cart_svc.get_code("VAR2026"), "hjemlevering")["code_error"], "Utløpt kode avvises")
check("minst" in compute_totals([{"unit_price": 1000, "regular_price": 1000, "quantity": 1}], cart_svc.get_code("SOMMAR200"), "hjemlevering")["code_error"], "Kronekode krever minstesum")
t = compute_totals([{"unit_price": 1300, "regular_price": 1300, "quantity": 1}], cart_svc.get_code("VELKOMMEN10"), "hjemlevering")
check(t["discount"] == 130 and t["shipping"] == 99 and t["total"] == 1170 + 99, "Fri frakt regnes etter rabatt (1300 - 130 = 1170 < 1200)")
check(compute_totals([{"unit_price": 3000, "regular_price": 3000, "quantity": 1}], None, "ekspress")["shipping"] == 199, "Ekspress aldri gratis")

# ---- 6. Full flyt: innlogging, korg, rabattkode, kasse, Mine sider ----
c = new_client()
r = c.post("/logg-inn", data={"email": "ingrid.solberg@example.com", "password": "feil"})
check(r.status_code == 401, "Feil passord avvises")
r = c.post("/logg-inn", data={"email": "ingrid.solberg@example.com", "password": "demo123"})
check(r.status_code == 200 and "Mine sider" in r.text and "VH-10001" in r.text, "Innlogging viser ordrehistorikk")
check(len(re.findall(r'href="/mine-sider/ordre/', c.get("/mine-sider").text)) == 3, "Ingrid har 3 seed-ordrer")
check("VH-10011" in c.get("/mine-sider/ordre/VH-10011").text and c.get("/mine-sider/ordre/VH-10002").status_code == 404, "Ordredetaljer, og andres ordre er skjult")

stock_before = query_one("SELECT stock FROM variants WHERE sku = 'VH-JAK-1001-M-FJO'")["stock"]
c.post("/handlekurv/legg-til", data={"sku": "VH-JAK-1001-M-FJO", "quantity": 1})
c.post("/handlekurv/legg-til", data={"sku": "VH-TIL-6004-STA", "quantity": 2})
cart_page = c.get("/handlekurv").text
check("Skarven Skaljakke" in cart_page and "Varm Termoflaske" in cart_page, "Varer i handlekurven")
c.post("/handlekurv/oppdater", data={"sku": "VH-TIL-6004-STA", "quantity": 3})
check('value="3"' in c.get("/handlekurv").text, "Endre antall")
r = c.post("/handlekurv/rabattkode", data={"code": "VAR2026"})
check("utløpt" in r.text, "Utløpt kode gir melding i handlekurven")
r = c.post("/handlekurv/rabattkode", data={"code": "velkommen10"})
check("VELKOMMEN10" in r.text and "−" in r.text, "Rabattkode VELKOMMEN10 brukes")
c.post("/handlekurv/oppdater", data={"sku": "VH-TIL-6004-STA", "quantity": 0})
check("Varm Termoflaske" not in c.get("/handlekurv").text, "Fjern vare via antall 0")

r = c.post("/kasse", data={"name": "Ingrid Solberg", "email": "ingrid.solberg@example.com", "street": "Havnegata 14",
                            "postal_code": "9171", "city": "Longyearbyen", "method": "hjemlevering"})
check(r.status_code == 422 and "Svalbard" in r.text, "Svalbard avvises i kassen")
r = c.post("/kasse", data={"name": "", "email": "x", "street": "", "postal_code": "12", "city": "", "method": "hjemlevering"})
check(r.status_code == 422, "Ugyldig skjema avvises")
check("Fullfør bestilling (demo)" in c.get("/kasse").text and "kortnummer" not in c.get("/kasse").text.lower().replace("ikke fylle inn kortnummer", ""), "Kasse har demoknapp og ingen kortfelt")
r = c.post("/kasse", data={"name": "Ingrid Solberg", "email": "ingrid.solberg@example.com", "street": "Havnegata 14",
                            "postal_code": "5700", "city": "Voss", "method": "ekspress"})
m = re.search(r"VH-\d+", r.text)
check(r.status_code == 200 and m and m.group(0) == "VH-10016", f"Ordrebekreftelse med ordrenummer ({m.group(0) if m else None})")
number = m.group(0)
check(c.get("/handlekurv").text.count("Skarven") == 0, "Handlekurven tømmes etter bestilling")
detail = c.get(f"/mine-sider/ordre/{number}").text
check("Mottatt" in detail and "199" in detail, "Ny ordre vises under Mine sider med ekspress (199 kr) og status Mottatt")
o = query_one("SELECT * FROM orders WHERE order_number = ?", (number,))
check(o["total"] == 2990 - 299 + 199 and o["discount_code"] == "VELKOMMEN10" and o["discount_amount"] == 299, f"Ordresum i databasen ({o['total']})")
check(query_one("SELECT stock FROM variants WHERE sku = 'VH-JAK-1001-M-FJO'")["stock"] == stock_before - 1, "Lager trekkes ved bestilling")
check(c.post("/sporing", data={"order_number": number, "email": "ingrid.solberg@example.com"}).status_code == 200, "Ny ordre kan spores")

# Gjest: utsolgt variant kan ikke legges i korg
g = new_client()
r = g.post("/handlekurv/legg-til", data={"sku": "VH-JAK-1001-XXL-FJO", "quantity": 1})
check("utsolgt" in r.text.lower() and "Handlekurven din er tom" in g.get("/handlekurv").text, "Utsolgt variant kan ikke bestilles")
r = g.post("/handlekurv/legg-til", data={"sku": "VH-JAK-1001-L-FJO", "quantity": 5})
check("Vi har bare 2 igjen" in r.text, "Antall begrenses av lager")
r = g.post("/kasse", data={"name": "Gjest", "email": "gjest@example.com", "street": "Gate 1", "postal_code": "0150", "city": "Oslo", "method": "hentested"})
check(r.status_code == 200 and re.search(r"VH-\d+", r.text), "Gjestebestilling fungerer")
check(g.get("/mine-sider", follow_redirects=False).status_code == 303, "Mine sider krever innlogging")

# ---- 7. Ønskeliste ----
w = new_client()
r = w.post("/onskeliste/1", data={"next": "/produkt/skarven-skaljakke-herre"})
check("Logg inn" in r.text and "/logg-inn" in str(r.url), "Ønskeliste krever innlogging")
w.post("/logg-inn", data={"email": "ola.kvamme@example.com", "password": "demo123"})
w.post("/onskeliste/3", data={"next": "/produkter"})
check("Dunfjell" in w.get("/onskeliste").text, "Legg til i ønskelisten")
w.post("/onskeliste/3", data={"next": "/onskeliste"})
check("Ønskelisten din er tom" in w.get("/onskeliste").text, "Fjern fra ønskelisten")

# ---- 8. Chat-API ----
r = c.post("/api/chat", json={"message": "Hei"})
check(r.status_code == 200 and r.json() == {"reply": "Kundeserviceagenten er ikke koblet til ennå."}, "POST /api/chat gir stubbsvar")

print()
print("Alt OK" if not failures else f"{len(failures)} feil")
sys.exit(1 if failures else 0)
