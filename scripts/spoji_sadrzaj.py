"""Spaja sadržaj iz admina u fajlove koje sajt čita.

Pokreće ga Netlify pri svakom objavljivanju (vidi netlify.toml):
  content/proizvodi/*.json  ->  content/proizvodi.json
  content/brendovi/*.json   ->  content/highlights.json
  + osvežava rezervne podatke u index.html i pravi ponuda.html
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts):
    return os.path.join(ROOT, *parts)


def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # a broken file must not take the whole site down
        print("PRESKAČEM %s: %s" % (p, e), file=sys.stderr)
        return None


def text(v):
    return v.strip() if isinstance(v, str) else ""


def write_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# Products: newest first, hidden ones left out
products = []
for p in glob.glob(path("content", "proizvodi", "*.json")):
    d = load(p)
    if not isinstance(d, dict) or d.get("prikazi") is False or not text(d.get("naziv")):
        continue
    products.append({
        "naziv": text(d.get("naziv")),
        "brend": text(d.get("brend")),
        "kategorija": text(d.get("kategorija")),
        "velicine": text(d.get("velicine")),
        "slika": text(d.get("image")) or text(d.get("slika")),
        "belaPozadina": bool(d.get("belaPozadina")),
        "instagram": text(d.get("instagram")),
        "_datum": text(d.get("datum")),
    })
products.sort(key=lambda x: (x["_datum"], x["naziv"]), reverse=True)
for x in products:
    del x["_datum"]

# Brands -> highlight circles, ordered by "redosled"
brands = []
for p in glob.glob(path("content", "brendovi", "*.json")):
    d = load(p)
    if not isinstance(d, dict) or d.get("prikazi") is False or not text(d.get("naziv")):
        continue
    try:
        order = int(d.get("redosled") or 99)
    except (TypeError, ValueError):
        order = 99
    brands.append((order, text(d.get("naziv")), {
        "naziv": text(d.get("oznaka")) or text(d.get("naziv")),
        "slika": text(d.get("image")),
        "ikona": "",
        "filter": text(d.get("naziv")),
        "cilj": "izdvojeno" if d.get("istaknuto") else "",
    }))
brands.sort(key=lambda x: (x[0], x[1].lower()))
highlights = [b[2] for b in brands]

write_json(path("content", "proizvodi.json"), {"proizvodi": products})
write_json(path("content", "highlights.json"), {"highlights": highlights})

# Refresh the embedded fallback in index.html and rebuild ponuda.html from it
izdvojeno = load(path("content", "izdvojeno.json")) or {}
fallback = {"proizvodi": products, "izdvojeno": izdvojeno, "highlights": highlights}
blob = json.dumps(fallback, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
with open(path("index.html"), encoding="utf-8") as f:
    html = f.read()
html = re.sub(r'<script id="fallback">.*?</script>',
              lambda m: '<script id="fallback">window.FALLBACK=' + blob + ';</script>',
              html, count=1, flags=re.S)
with open(path("index.html"), "w", encoding="utf-8") as f:
    f.write(html)

ponuda = html.replace(
    "<title>Outcast Shopper</title>",
    '<title>Ponuda · Outcast Shopper</title><script>window.PAGE="ponuda";'
    'document.documentElement.classList.add("page-ponuda");</script>', 1)
with open(path("ponuda.html"), "w", encoding="utf-8") as f:
    f.write(ponuda)

print("Spojeno: %d proizvoda, %d brendova" % (len(products), len(highlights)))
