#!/usr/bin/env python3
"""Share cards (Open Graph images) for pinkal.art, rendered with Playwright's Chromium.

Writes 1200 x 630 JPEG files (quality 80, at most 150 KB each):
  og/NN.jpg            one per painting: the painting whole on its wall colour with a 1 px rule,
                       "No. NN" and the subject bottom-left, "pinkal.art" bottom-right
  og/home.jpg          the hero painting (site.hero) with the hero line
  og/room-<slug>.jpg   each room's lead painting with the room name

Usage
  python tools/og.py                 all cards into og/
  python tools/og.py --out DIR --only 13,29
  python tools/og.py --demo 13,29,02 [--catalog PATH]
                                     before data/works.json exists: subjects from the vision catalog

Reads data/works.json, data/rooms.json, data/site.json, data/strings.en.json (hero.line, label.no)
and data/images.json; the fonts come from fonts/ (self-hosted woff2, embedded once as data URIs).
Skipped with a warning when Playwright or its Chromium is missing
(python -m pip install playwright; playwright install chromium).
"""
import argparse
import base64
import html
import io
import json
import os
import sys
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FONTS = os.path.join(ROOT, "fonts")
IMAGES = os.path.join(ROOT, "images", "r")
W, H = 1200, 630
JPEG_Q = 80
MAX_BYTES = 150 * 1024
INK, INK_2, INK_3 = "#141210", "#4a4440", "#6b625b"
DEFAULT_HERO_LINE = "The known world, painted brighter."
DEFAULT_DOMAIN = "https://pinkal.art"

FONT_FILES = (
    ("Fraunces", "normal", "300 700", "Fraunces-300-700-normal-latin.woff2", "U+0000-00FF, U+2000-206F, U+20AC"),
    ("Fraunces", "normal", "300 700", "Fraunces-300-700-normal-latin-ext.woff2", "U+0100-024F, U+1E00-1EFF"),
    ("Fraunces", "italic", "300 700", "Fraunces-300-700-italic-latin.woff2", "U+0000-00FF, U+2000-206F, U+20AC"),
    ("Fraunces", "italic", "300 700", "Fraunces-300-700-italic-latin-ext.woff2", "U+0100-024F, U+1E00-1EFF"),
    ("Instrument Sans", "normal", "400 700", "InstrumentSans-400-700-normal-latin.woff2", "U+0000-00FF, U+2000-206F, U+20AC"),
    ("Instrument Sans", "normal", "400 700", "InstrumentSans-400-700-normal-latin-ext.woff2", "U+0100-024F, U+1E00-1EFF"),
)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(w)dpx;height:%(h)dpx;overflow:hidden;background:#ece6db}
body{color:%(ink)s;font-family:"Instrument Sans",Arial,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
.card{position:relative;width:%(w)dpx;height:%(h)dpx;padding:56px 60px 48px;display:grid;
  grid-template-rows:minmax(0,1fr) auto;row-gap:28px;background:var(--wall)}
.card--split{grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:56px}
.stage{display:flex;align-items:center;justify-content:center;min-height:0;min-width:0}
.card--split .stage{grid-row:1/3}
.stage img{display:block;width:auto;height:auto;max-width:100%%;max-height:100%%;
  outline:1px solid rgb(20 18 16 / .18);outline-offset:-1px;
  box-shadow:0 1px 2px rgb(20 18 16 / .14),0 14px 36px -16px rgb(20 18 16 / .34)}
.caption{display:grid;grid-template-columns:minmax(0,1fr) auto;column-gap:40px;align-items:end}
.caption p{font-family:"Fraunces",Georgia,serif;font-size:32px;line-height:1.2;color:%(ink2)s;
  font-style:italic;font-weight:400;font-variation-settings:"opsz" 32}
.caption .no{font-style:normal;font-weight:300;font-size:40px;color:%(ink)s;font-variant-numeric:tabular-nums;
  font-variation-settings:"opsz" 40;margin-right:14px}
.domain{font-weight:500;font-size:24px;letter-spacing:.02em;color:%(ink2)s;white-space:nowrap;padding-bottom:4px}
.text{display:flex;flex-direction:column;justify-content:center;min-width:0}
.text h1{font-family:"Fraunces",Georgia,serif;font-weight:300;font-size:var(--display,66px);line-height:.98;
  letter-spacing:-.015em;font-variation-settings:"opsz" 144;text-wrap:balance;color:%(ink)s}
.text .eyebrow{font-weight:500;font-size:20px;letter-spacing:.08em;text-transform:uppercase;color:%(ink3)s;margin-bottom:22px}
.card--split .caption{grid-column:2;grid-template-columns:auto;justify-content:end}
.warm{position:absolute;left:-9999px;top:0}
"""


def read_json(name, default=None):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def data_uri(path, mime):
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))


def font_css():
    rules = []
    for family, style, weight, name, urange in FONT_FILES:
        path = os.path.join(FONTS, name)
        if os.path.exists(path):
            rules.append('@font-face{font-family:"%s";font-style:%s;font-weight:%s;src:url(%s) format("woff2");unicode-range:%s}'
                         % (family, style, weight, data_uri(path, "font/woff2"), urange))
    return "\n".join(rules)


def base_document():
    """Loaded once: fonts, styles and a warm-up line in every face so later cards never wait for a font."""
    css = CSS % {"w": W, "h": H, "ink": INK, "ink2": INK_2, "ink3": INK_3}
    warm = ('<p class="warm"><span style="font:300 40px Fraunces">No. 0123456789</span>'
            '<span style="font:italic 400 32px Fraunces">Painting</span><span style="font:500 24px \'Instrument Sans\'">pinkal.art</span></p>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><style>%s\n%s</style></head><body>%s</body></html>'
            % (font_css(), css, warm))


def pick_variant(entry, min_w):
    """Smallest JPEG variant at least min_w wide, else the largest one."""
    for v in sorted(entry["variants"], key=lambda v: v["w"]):
        if v["w"] >= min_w:
            return v
    return max(entry["variants"], key=lambda v: v["w"])


def painting_img(entry, box_w, box_h):
    """<img> for a painting shown whole inside box_w x box_h, never above its source pixel size."""
    v = pick_variant(entry, min(box_w, entry["w"]))
    path = os.path.join(IMAGES, os.path.basename(v["jpg"]))
    return '<img src="%s" alt="" style="max-width:%dpx;max-height:%dpx">' % (
        data_uri(path, "image/jpeg"), min(box_w, entry["w"]), min(box_h, entry["h"]))


def card_work(entry, no, subject, domain):
    return ('<div class="card" style="--wall:%s"><div class="stage">%s</div>'
            '<div class="caption"><p><span class="no">%s</span>%s</p><div class="domain">%s</div></div></div>'
            % (entry["wall"], painting_img(entry, 1000, 420), html.escape(no), html.escape(subject), html.escape(domain)))


def card_split(entry, eyebrow, headline, domain, display):
    return ('<div class="card card--split" style="--wall:%s;--display:%dpx"><div class="stage">%s</div>'
            '<div class="text">%s<h1>%s</h1></div><div class="caption"><div class="domain">%s</div></div></div>'
            % (entry["wall"], display, painting_img(entry, 520, 526),
               '<div class="eyebrow">%s</div>' % html.escape(eyebrow) if eyebrow else "",
               html.escape(headline), html.escape(domain)))


def to_jpeg(png_bytes, path):
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    q = JPEG_Q
    while True:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAX_BYTES or q <= 50:
            break
        q -= 4
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return buf.tell(), q


def demo_subjects(catalog_path, ids):
    if not catalog_path or not os.path.exists(catalog_path):
        return {i: "Painting" for i in ids}
    with open(catalog_path, encoding="utf-8") as f:
        cat = json.load(f)
    out = {}
    for e in cat:
        if e.get("id") in ids:
            text = ", ".join(s.strip() for s in e.get("subjects", [])[:3] if s.strip()) or "Painting"
            out[e["id"]] = text[0].upper() + text[1:]
    return out


SWAP_JS = """async (markup) => {
  document.body.innerHTML = markup;
  void document.body.offsetHeight;
  await document.fonts.ready;
  await Promise.all([...document.images].map(i => i.decode().catch(() => null)));
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "og"))
    ap.add_argument("--only", default="", help="comma-separated ids; skips home and room cards")
    ap.add_argument("--demo", default="", help="comma-separated ids to render without data/works.json")
    ap.add_argument("--catalog", default="", help="vision catalog JSON for --demo subjects")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("og.py: warning: Playwright is not installed; share cards skipped "
              "(python -m pip install playwright; playwright install chromium)")
        return 0

    images = read_json("images.json")
    if not images:
        sys.exit("og.py: data/images.json is missing; run python tools/images.py first")
    site = read_json("site.json", {}) or {}
    rooms = read_json("rooms.json", []) or []
    strings = read_json("strings.en.json", {}) or {}
    domain = (site.get("domain") or DEFAULT_DOMAIN).rstrip("/").split("//")[-1]
    hero_line = strings.get("hero.line") or DEFAULT_HERO_LINE
    hero_id = str(site.get("hero") or "13")
    no_label = strings.get("label.no") or "No."

    works = read_json("works.json")
    if a.demo:
        ids = [i.strip() for i in a.demo.split(",") if i.strip()]
        subjects = demo_subjects(a.catalog, ids)
        paintings = [{"id": i, "subject": subjects.get(i, "Painting")} for i in ids]
        rooms = rooms if works else []
    elif works:
        paintings = [{"id": str(w["id"]), "subject": (w.get("subject") or {}).get("en") or ""}
                     for w in works if w.get("kind", "painting") == "painting" and not w.get("duplicate_of")]
    else:
        sys.exit("og.py: data/works.json is missing (use --demo 13,29,02 to test without it)")
    only = set(i.strip() for i in a.only.split(",") if i.strip())
    if only:
        paintings = [p for p in paintings if p["id"] in only]

    jobs, missing = [], []
    for p in paintings:
        e = images.get(p["id"])
        if not e:
            missing.append(p["id"])
            continue
        jobs.append(("%s.jpg" % p["id"], card_work(e, "%s %s" % (no_label, p["id"]), p["subject"], domain)))
    if not only:
        if hero_id in images:
            jobs.append(("home.jpg", card_split(images[hero_id], "", hero_line, domain, 66)))
        for r in rooms:
            lead = str(r.get("lead") or "")
            if lead in images:
                name = (r.get("name") or {}).get("en") or r.get("slug", "")
                jobs.append(("room-%s.jpg" % r["slug"], card_split(images[lead], "Room", name, domain, 72)))

    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    sizes, lowered = {}, []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as e:  # browser binary missing
            print("og.py: warning: Chromium could not start (%s); share cards skipped. Run: playwright install chromium"
                  % str(e).splitlines()[0][:120])
            return 0
        pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.set_content(base_document(), wait_until="load")
        pg.evaluate("() => document.fonts.ready")
        for name, markup in jobs:
            pg.evaluate(SWAP_JS, markup)
            png = pg.screenshot(type="png", clip={"x": 0, "y": 0, "width": W, "height": H})
            size, q = to_jpeg(png, os.path.join(a.out, name))
            sizes[name] = size
            if q != JPEG_Q:
                lowered.append("%s q%d" % (name, q))
            if a.verbose:
                print("  %s %d B%s" % (name, size, " (q%d)" % q if q != JPEG_Q else ""))
        browser.close()

    removed = 0
    if not only and not a.demo:
        for name in os.listdir(a.out):
            stem, ext = os.path.splitext(name)
            if ext == ".jpg" and name not in sizes and (stem.isdigit() or stem == "home" or stem.startswith("room-")):
                os.remove(os.path.join(a.out, name))
                removed += 1
    out_label = os.path.relpath(a.out, ROOT) if os.path.abspath(a.out).startswith(ROOT) else a.out
    if sizes:
        print("og.py: %d cards in %s, %d-%d KB (mean %d KB), %d above %d KB, %d stale removed, %.0f s"
              % (len(sizes), out_label, min(sizes.values()) // 1024, max(sizes.values()) // 1024,
                 sum(sizes.values()) // len(sizes) // 1024, sum(1 for s in sizes.values() if s > MAX_BYTES),
                 MAX_BYTES // 1024, removed, time.time() - t0))
    if lowered:
        print("  quality lowered to stay under %d KB: %s" % (MAX_BYTES // 1024, ", ".join(lowered)))
    if missing:
        print("  warning: no images.json entry for %s" % ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
