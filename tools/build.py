#!/usr/bin/env python3
"""Build pinkal.art: renders every page (EN and DE) from data/ into the repo root.

    python tools/build.py                 full build into the repo root
    python tools/build.py --no-images     skip the share cards (og.py) and QR codes (qr.py)
    python tools/build.py --deploy        refuse while legal data has TODOs or any check fails
    python tools/build.py --data-dir DIR  read the JSON files from another folder (fixtures)
    python tools/build.py --out DIR       write the site somewhere else (preview, tests)

Reads   data/works.json rooms.json site.json strings.en.json strings.de.json images.json
        src/templates/*.html  src/css/*.css  src/js/*.js  fonts/fonts.css
Writes  index.html 404.html works/ rooms/ de/ enquire/ show/ impressum/ datenschutz/ assets/
        sitemap.xml robots.txt manifest.webmanifest .nojekyll build/CHECKLIST.md build/REVIEW.csv
        build/manifest.json (every generated path; stale paths from the previous run are deleted)
Then    tools/og.py and tools/qr.py when present (non-fatal), and tools/check.py (budgets, links, copy).
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from markupsafe import Markup
except ImportError:  # pragma: no cover
    sys.exit("build.py: Jinja2 is missing. Run: python -m pip install -r tools/requirements.txt")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TPL_DIR = os.path.join(SRC, "templates")
CSS_DIR = os.path.join(SRC, "css")
JS_DIR = os.path.join(SRC, "js")
FONTS_DIR = os.path.join(ROOT, "fonts")

LANGS = ("en", "de")
SLUG = {
    "en": {"prefix": "", "works": "works", "rooms": "rooms", "enquire": "enquire", "thanks": "thanks", "show": "show"},
    "de": {"prefix": "/de", "works": "werke", "rooms": "raeume", "enquire": "anfrage", "thanks": "danke", "show": "show"},
}
OG_LOCALE = {"en": "en_GB", "de": "de_DE"}
PAPER = "#f5f0e8"
FORMSPREE = "https://formspree.io/f/"

# Grid algorithm reference values (brief section 6)
REF_W, GAP, TARGET = 1376, 32, 320
BAND_AR = 2.2          # 19 (2.30) and 18 (3.11) form single-work bands
TALL_AR = 0.5          # 20 (0.415) and 42 (0.476) never share a row
LOW_CAP = 500          # a row never holds two works with --maxw < 500
BAND_MAX_H = 400

STATUSES = ("available", "reserved", "sold", "private")
REQUIRED_WORK = ("id", "kind", "room", "order", "subject", "alt", "title_status", "zoom", "desc_approved")
OPTIONAL_WORK = {
    "duplicate_of": None, "title": None, "desc": None, "text_by": "studio", "medium": None, "width_cm": None,
    "height_cm": None, "year": None, "panels": None, "signed": None, "shape": "rect", "mask": None, "status": None,
    "price_eur": None, "price_mode": None, "instagram_url": None, "colour": None,
}


class BuildError(Exception):
    pass


def log(msg):
    print("build.py: " + msg)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text(out_root, rel, text, written):
    path = os.path.join(out_root, rel)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    written.append(rel.replace("\\", "/"))


def write_bytes(out_root, rel, data, written):
    path = os.path.join(out_root, rel)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    written.append(rel.replace("\\", "/"))


def hash8(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:8]


def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};>,])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    css = css.replace(";}", "}")
    return css.strip()


def compact_html(html):
    out = []
    for line in html.split("\n"):
        s = line.strip()
        if s:
            out.append(s)
    return "\n".join(out) + "\n"


def json_for_html(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def fmt_number(n, lang):
    s = f"{int(n):,}" if float(n).is_integer() else f"{n:,.2f}"
    return s.replace(",", ".") if lang == "de" else s


# ---------------------------------------------------------------- data loading and validation

def load_data(data_dir):
    files = {}
    for name in ("works", "rooms", "site", "strings.en", "strings.de", "images"):
        path = os.path.join(data_dir, name + ".json")
        if not os.path.exists(path):
            raise BuildError(f"missing {path} (run with --data-dir to use fixtures)")
        files[name] = read_json(path)
    return files


def validate(works, rooms, site, strings_en, strings_de, images, problems):
    room_slugs = [r["slug"] for r in rooms]
    if len(set(room_slugs)) != len(room_slugs):
        problems.append("rooms.json: duplicate slug")
    for r in rooms:
        for k in ("slug", "slug_de", "name", "text", "lead", "order"):
            if k not in r:
                problems.append(f"rooms.json: room {r.get('slug')} lacks '{k}'")
    seen = set()
    for w in works:
        wid = w.get("id")
        for k in REQUIRED_WORK:
            if k not in w:
                problems.append(f"works.json: work {wid} lacks required '{k}'")
        if not (isinstance(wid, str) and re.fullmatch(r"\d\d", wid)):
            problems.append(f"works.json: id {wid!r} is not a two-digit string")
        if wid in seen:
            problems.append(f"works.json: duplicate id {wid}")
        seen.add(wid)
        if w.get("kind") not in ("painting", "photo"):
            problems.append(f"works.json: {wid} kind {w.get('kind')!r} is not painting|photo")
        if w.get("kind") == "painting" and not w.get("duplicate_of") and w.get("room") not in room_slugs:
            problems.append(f"works.json: {wid} room {w.get('room')!r} is not in rooms.json")
        if w.get("title_status") not in ("none", "proposed", "confirmed"):
            problems.append(f"works.json: {wid} title_status {w.get('title_status')!r} invalid")
        if w.get("status") not in STATUSES + (None,):
            problems.append(f"works.json: {wid} status {w.get('status')!r} invalid")
        if w.get("price_mode") not in ("show", "request", None):
            problems.append(f"works.json: {wid} price_mode {w.get('price_mode')!r} invalid")
        if w.get("shape", "rect") not in ("rect", "round"):
            problems.append(f"works.json: {wid} shape {w.get('shape')!r} invalid")
        for fld in ("subject", "alt"):
            v = w.get(fld)
            if not (isinstance(v, dict) and v.get("en")):
                problems.append(f"works.json: {wid} {fld}.en missing")
        needs_image = w.get("kind") == "painting" and not w.get("duplicate_of")
        if wid not in images:
            if needs_image:
                problems.append(f"images.json: no entry for {wid} (run python tools/images.py)")
        elif not images[wid].get("variants"):
            problems.append(f"images.json: {wid} has no variants")
    missing = sorted(set(strings_en) ^ set(strings_de))
    if missing:
        problems.append("strings key parity: " + ", ".join(missing[:12]) + (" …" if len(missing) > 12 else ""))
    for k in ("name", "domain", "instagram", "hero", "proof", "location", "formspree", "legal"):
        if k not in site:
            problems.append(f"site.json lacks '{k}'")
    # room totals: every room has paintings, every lead is in its room, orders unique per room
    paintings = [w for w in works if w.get("kind") == "painting" and not w.get("duplicate_of")]
    by_room = {}
    for w in paintings:
        by_room.setdefault(w["room"], []).append(w)
    for r in rooms:
        members = by_room.get(r["slug"], [])
        if not members:
            problems.append(f"room {r['slug']} has no paintings")
        orders = [m.get("order") for m in members]
        if len(set(orders)) != len(orders):
            problems.append(f"room {r['slug']}: duplicate order values")
        if r.get("lead") not in [m["id"] for m in members]:
            problems.append(f"room {r['slug']}: lead {r.get('lead')} is not a painting of that room")
    if site.get("hero") not in [w["id"] for w in paintings]:
        problems.append(f"site.hero {site.get('hero')} is not a painting")
    return paintings


# ---------------------------------------------------------------- derivation

def srcset(variants, fmt):
    return ", ".join(f"{v[fmt]} {v['w']}w" for v in variants)


def pick(variants, min_w):
    for v in variants:
        if v["w"] >= min_w:
            return v
    return variants[-1]


def partition(items):
    """Greedy justified rows at REF_W (brief section 6). items: dicts with id, ar, maxw."""
    rows, cur = [], []

    def height(ws):
        return (REF_W - GAP * (len(ws) - 1)) / sum(w["ar"] for w in ws)

    def allowed(ws):
        return sum(1 for w in ws if w["ar"] < TALL_AR) <= 1 and sum(1 for w in ws if w["maxw"] < LOW_CAP) <= 1

    def close(ws, last=False, band=False):
        h = height(ws)
        filler = False
        if band:
            if h > BAND_MAX_H:
                h, filler = BAND_MAX_H, True
        elif (last and h > TARGET) or h > TARGET * 1.25:
            h, filler = TARGET, True
        ar_sum = sum(w["ar"] for w in ws)
        row = {"ids": [w["id"] for w in ws], "h": round(h, 1), "band": band, "filler": filler, "plates": []}
        for w in ws:
            if filler:
                px = round(h * w["ar"])
                vw = round(px / REF_W * 92)
            else:
                px = round(w["ar"] / ar_sum * REF_W)
                vw = round(w["ar"] / ar_sum * 92)
            slot = h * w["ar"]
            row["plates"].append({
                "id": w["id"],
                "sizes": f"(min-width: 1200px) {px}px, (min-width: 700px) {vw}vw, calc(100vw - 32px)",
                "capped": slot > w["maxw"],
                "slot_px": round(slot),
                "basis": round(slot / REF_W * 100, 3),
            })
        rows.append(row)

    for w in items:
        if w["ar"] >= BAND_AR:
            if cur:
                close(cur)
                cur = []
            close([w], band=True)
            continue
        cand = cur + [w]
        if cur and not allowed(cand):
            close(cur)
            cur = [w]
            continue
        if height(cand) >= TARGET:
            cur = cand
            continue
        if cur and abs(height(cur) - TARGET) < abs(height(cand) - TARGET):
            close(cur)
            cur = [w]
        else:
            close(cand)
            cur = []
    if cur:
        close(cur, last=True)
    return rows


class Site:
    """Everything derived from the data files, for both languages."""

    def __init__(self, data, problems):
        self.works_raw = data["works"]
        self.rooms_raw = sorted(data["rooms"], key=lambda r: r["order"])
        self.site = data["site"]
        self.strings = {"en": data["strings.en"], "de": data["strings.de"]}
        self.images = data["images"]
        self.problems = problems
        needed_path = os.path.join(TPL_DIR, "_strings_needed.json")
        self.needed = read_json(needed_path) if os.path.exists(needed_path) else {}
        self.fallback_keys = set()
        self.domain = self.site["domain"].rstrip("/")
        paintings = validate(self.works_raw, self.rooms_raw, self.site, self.strings["en"], self.strings["de"],
                             self.images, problems)
        if problems:
            raise BuildError("data validation failed:\n  " + "\n  ".join(problems))
        for w in self.works_raw:
            for k, v in OPTIONAL_WORK.items():
                w.setdefault(k, v)
        self.by_id = {w["id"]: w for w in self.works_raw}
        self.rooms = {}
        for r in self.rooms_raw:
            members = sorted([w for w in paintings if w["room"] == r["slug"]], key=lambda w: w["order"])
            self.rooms[r["slug"]] = {"raw": r, "ids": [m["id"] for m in members]}
        self.hang = [wid for r in self.rooms_raw for wid in self.rooms[r["slug"]]["ids"]]
        self.total = len(self.hang)
        self.photo = next((w["id"] for w in self.works_raw if w["kind"] == "photo" and w["id"] in self.images), None)
        self.excluded = [w["id"] for w in self.works_raw if w["kind"] != "painting" or w.get("duplicate_of")]
        self.rows = {slug: partition([self.geometry(wid) for wid in r["ids"]]) for slug, r in self.rooms.items()}
        self.views = {lang: {wid: self.view(wid, lang) for wid in self.by_id if wid in self.images} for lang in LANGS}
        self.room_views = {lang: [self.room_view(slug, lang) for slug in self.rooms] for lang in LANGS}
        self.notes = []  # CHECKLIST items collected while deriving

    # ---- strings
    def t(self, lang, key, **kw):
        s = self.strings[lang].get(key)
        if s is None:
            s = (self.needed.get(key) or {}).get(lang)
            if s is None:
                raise BuildError(f"missing string '{key}' for {lang} (add it to data/strings.{lang}.json)")
            self.fallback_keys.add(key)
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    def ts(self, lang, key, default, **kw):
        try:
            return self.t(lang, key, **kw)
        except BuildError:
            for k, v in kw.items():
                default = default.replace("{" + k + "}", str(v))
            return default

    def count_text(self, lang, n):
        return self.t(lang, "rooms.count_one" if n == 1 else "rooms.count_other", count=n)

    # ---- urls
    def url(self, lang, kind, **kw):
        s = SLUG[lang]
        p = s["prefix"]
        if kind == "home":
            return p + "/"
        if kind == "works":
            return f"{p}/{s['works']}/"
        if kind == "work":
            return f"{p}/{s['works']}/{kw['id']}/"
        if kind == "room":
            r = self.rooms[kw["slug"]]["raw"]
            return f"{p}/{s['rooms']}/{r['slug'] if lang == 'en' else r['slug_de']}/"
        if kind == "enquire":
            return f"{p}/{s['enquire']}/"
        if kind == "thanks":
            return f"{p}/{s['enquire']}/{s['thanks']}/"
        if kind == "show":
            return f"{p}/{s['show']}/"
        if kind == "impressum":
            return "/impressum/"
        if kind == "datenschutz":
            return "/datenschutz/"
        raise KeyError(kind)

    def abs_url(self, path):
        return self.domain + path

    # ---- works
    def geometry(self, wid):
        img = self.images[wid]
        w, h = img["w"], img["h"]
        return {"id": wid, "ar": round(img.get("ar") or w / h, 4), "maxw": img.get("maxw") or w * 2 // 3}

    def text(self, field, lang):
        """(text, lang_of_text) with English fallback for a missing German field."""
        if not isinstance(field, dict):
            return (field, lang) if field else (None, lang)
        if field.get(lang):
            return field[lang], lang
        if field.get("en"):
            return field["en"], "en"
        return None, lang

    def view(self, wid, lang):
        w = self.by_id[wid]
        img = self.images[wid]
        geo = self.geometry(wid)
        ar, maxw = geo["ar"], geo["maxw"]
        variants = sorted(img["variants"], key=lambda v: v["w"])
        plate_v = [v for v in variants if v["w"] <= 2000] or variants
        room_v = [v for v in plate_v if v["w"] >= 400] or plate_v
        jpg_small = [v for v in variants if v["w"] <= 1200]
        fallback = (jpg_small[-1] if jpg_small else variants[0])["jpg"]
        v2400 = next((v for v in variants if v["w"] >= 2400), None)
        colour = w.get("colour") or {}
        subject, subject_lang = self.text(w["subject"], lang)
        alt, _ = self.text(w["alt"], lang)
        title_txt, _ = self.text(w.get("title"), lang) if w.get("title") else (None, lang)
        show_title = bool(title_txt) and (w["title_status"] == "confirmed" or self.site.get("show_proposed_titles"))
        desc, desc_lang = self.text(w.get("desc"), lang) if w.get("desc_approved") and w.get("desc") else (None, lang)
        medium, medium_lang = self.text(w.get("medium"), lang) if w.get("medium") else (None, lang)
        no = f"{self.t(lang, 'label.no')} {wid}"
        label = self.ts(lang, "a11y.plate", f"{no} · {subject}", no=wid, subject=subject)
        room = self.rooms.get(w["room"])
        room_name = self.text(room["raw"]["name"], lang)[0] if room else None
        dims = None
        if w.get("width_cm") and w.get("height_cm"):
            dims = self.ts(lang, "label.dimensions_value", "{w} × {h} cm", w=fmt_number(w["width_cm"], lang), h=fmt_number(w["height_cm"], lang))
        price_text = None
        if w.get("price_mode") == "request":
            price_text = self.t(lang, "label.price.request")
        elif w.get("price_mode") == "show" and w.get("price_eur"):
            key = "label.price.kleinunternehmer" if self.site["legal"].get("vat_mode") == "kleinunternehmer" else "label.price.show"
            price_text = self.t(lang, key, price=fmt_number(w["price_eur"], lang))
        if w.get("status") == "sold":
            ask_text = self.t(lang, "actions.ask_sold")
        elif medium or dims or price_text:
            ask_text = self.t(lang, "actions.ask_known")
        else:
            ask_text = self.t(lang, "actions.ask_default")
        in_collection = wid in self.hang
        url = self.url(lang, "work", id=wid) if in_collection else None
        small = variants[0]
        src_v = pick(plate_v, 800)
        return {
            "id": wid, "no": no, "subject": subject, "subject_lang": subject_lang, "alt": alt or subject,
            "label": label, "title": title_txt if show_title else None, "title_raw": title_txt,
            "title_status": w["title_status"], "desc": desc, "desc_lang": desc_lang,
            "in_words": w.get("text_by") == "artist", "kind": w["kind"], "in_collection": in_collection,
            "url": url, "abs_url": self.abs_url(url) if url else None,
            "ask_url": f"{self.url(lang, 'enquire')}?work={wid}",
            "room": w["room"] if room else None, "room_name": room_name,
            "room_url": self.url(lang, "room", slug=w["room"]) if room else None,
            "ar": ar, "w": img["w"], "h": img["h"], "maxw": maxw, "long_edge": img.get("long_edge") or max(img["w"], img["h"]),
            "eligible": bool(img.get("eligible_lead", (img.get("long_edge") or max(img["w"], img["h"])) >= 2400)),
            "wall": colour.get("wall") or img["wall"], "deep": colour.get("deep") or img["deep"], "lqip": img.get("lqip", ""),
            "zoom": bool(w.get("zoom")), "zoom_src": v2400["avif"] if (w.get("zoom") and v2400) else None,
            "round": w.get("shape") == "round", "band": ar >= BAND_AR, "panels": w.get("panels"),
            "medium": medium, "medium_lang": medium_lang, "dims": dims, "year": w.get("year"), "signed": w.get("signed"),
            "status": w.get("status"),
            "status_text": self.t(lang, "label.status." + w["status"]) if w.get("status") else None,
            "price_text": price_text, "ask_text": ask_text, "instagram_url": w.get("instagram_url"),
            "has_meta": bool(medium or dims or w.get("year") or w.get("panels") or w.get("signed") is not None
                             or w.get("status") or price_text),
            "srcset_avif": srcset(plate_v, "avif"), "srcset_jpg": srcset(plate_v, "jpg"),
            "room_avif": srcset(room_v, "avif"), "room_jpg": srcset(room_v, "jpg"), "fallback": fallback,
            "src": src_v["jpg"], "src_w": src_v["w"], "src_h": src_v["h"],
            "small_avif": small["avif"], "small_jpg": small["jpg"], "small_w": small["w"], "small_h": small["h"],
            "og_image": f"/og/{wid}.jpg", "qr": f"/images/qr/{wid}.svg",
            "index": self.hang.index(wid) if in_collection else None,
        }

    def room_view(self, slug, lang):
        r = self.rooms[slug]
        raw = r["raw"]
        n = len(r["ids"])
        return {
            "slug": slug, "slug_lang": raw["slug"] if lang == "en" else raw["slug_de"],
            "name": self.text(raw["name"], lang)[0], "text": self.text(raw["text"], lang)[0],
            "lead": raw["lead"], "ids": r["ids"], "count": n, "count_text": self.count_text(lang, n),
            "enter_text": self.t(lang, "rooms.enter_one" if n == 1 else "rooms.enter", count=n),
            "url": self.url(lang, "room", slug=slug), "rows": self.rows[slug], "og_image": f"/og/room-{slug}.jpg",
        }

    def room_data(self, lang, ids, extra_qr=False):
        s = {k: self.t(lang, "room." + k) for k in ("counter", "close", "prev", "next", "zoom", "zoom_out", "play",
                                                      "pause", "ask", "share", "share_copied", "open_page",
                                                      "fullscreen", "painting")}
        works = []
        for wid in ids:
            v = self.views[lang][wid]
            e = {"id": wid, "no": v["no"], "subject": v["subject"], "title": v["title"], "url": v["url"], "ask": v["ask_url"],
                 "ar": v["ar"], "w": v["w"], "h": v["h"], "wall": v["wall"], "deep": v["deep"], "lqip": v["lqip"],
                 "zoom": v["zoom"], "avif": v["room_avif"], "jpg": v["room_jpg"], "fallback": v["fallback"],
                 "zoomSrc": v["zoom_src"], "alt": v["alt"]}
            if extra_qr:
                e["qr"] = v["qr"]
            works.append(e)
        return {"lang": lang, "total": self.total, "strings": s, "works": works}


# ---------------------------------------------------------------- page definitions

def page_list(site):
    """Every HTML page: dicts with lang, kind, path, counterpart path."""
    pages = []
    for lang in LANGS:
        other = "de" if lang == "en" else "en"
        add = lambda kind, path, alt, **kw: pages.append(dict(lang=lang, kind=kind, path=path, alt=alt, **kw))
        add("home", site.url(lang, "home"), site.url(other, "home"))
        add("works", site.url(lang, "works"), site.url(other, "works"))
        for slug in site.rooms:
            add("room", site.url(lang, "room", slug=slug), site.url(other, "room", slug=slug), slug=slug)
        for wid in site.hang:
            add("work", site.url(lang, "work", id=wid), site.url(other, "work", id=wid), id=wid)
        add("enquire", site.url(lang, "enquire"), site.url(other, "enquire"))
        add("thanks", site.url(lang, "thanks"), site.url(other, "thanks"), noindex=True)
        add("show", site.url(lang, "show"), site.url(other, "show"), noindex=True)
    pages.append(dict(lang="de", kind="impressum", path="/impressum/", alt=None))
    pages.append(dict(lang="de", kind="datenschutz", path="/datenschutz/", alt=None))
    return pages


def jsonld_home(site, lang, page_url):
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "Person", "@id": site.domain + "/#pinkal", "name": site.site["name"], "url": site.domain + "/",
         "jobTitle": "Painter" if lang == "en" else "Malerin/Maler", "sameAs": [site.site["instagram"]],
         "address": {"@type": "PostalAddress", "addressLocality": site.site["location"]["city"],
                     "addressRegion": site.site["location"]["region"], "addressCountry": "DE"}},
        {"@type": "WebSite", "@id": site.domain + "/#website", "url": page_url, "name": site.site["name"],
         "inLanguage": lang, "publisher": {"@id": site.domain + "/#pinkal"}},
    ]}


def jsonld_work(site, lang, v, room, page_url):
    largest_jpg = max((x for x in site.images[v["id"]]["variants"] if x["w"] <= 2400), key=lambda x: x["w"])["jpg"]
    art = {"@type": "VisualArtwork", "@id": page_url, "url": page_url, "name": v["title"] or f"{v['no']} — {v['subject']}",
           "description": v["subject"], "image": site.abs_url(largest_jpg), "inLanguage": lang, "artform": "Painting",
           "creator": {"@type": "Person", "name": site.site["name"], "url": site.domain + "/", "sameAs": [site.site["instagram"]]},
           "isPartOf": site.abs_url(room["url"])}
    raw = site.by_id[v["id"]]
    if v["medium"]:
        art["artMedium"] = v["medium"]
    if raw.get("width_cm") and raw.get("height_cm"):
        art["width"] = {"@type": "QuantitativeValue", "value": raw["width_cm"], "unitCode": "CMT"}
        art["height"] = {"@type": "QuantitativeValue", "value": raw["height_cm"], "unitCode": "CMT"}
    if raw.get("year"):
        art["dateCreated"] = str(raw["year"])
    if raw.get("price_mode") == "show" and raw.get("status") == "available" and raw.get("price_eur"):
        art["offers"] = {"@type": "Offer", "price": raw["price_eur"], "priceCurrency": "EUR",
                         "availability": "https://schema.org/InStock", "url": page_url}
    crumbs = [(site.site["name"], site.url(lang, "home")), (site.t(lang, "nav.works"), site.url(lang, "works")),
              (room["name"], room["url"]), (v["no"], v["url"])]
    bl = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": site.abs_url(u)} for i, (n, u) in enumerate(crumbs)]}
    return {"@context": "https://schema.org", "@graph": [art, bl]}


# ---------------------------------------------------------------- the build

def build(args):
    t0 = datetime.datetime.now()
    out_root = os.path.abspath(args.out)
    data_dir = os.path.abspath(args.data_dir)
    problems = []
    data = load_data(data_dir)
    site = Site(data, problems)
    written = []
    warnings = []

    # ---- assets: fonts css (inlined), critical css (inlined), external css + js (hashed)
    fonts_css, fonts_ext_css = "", ""
    fonts_path = os.path.join(FONTS_DIR, "fonts.css")
    if os.path.exists(fonts_path):
        with open(fonts_path, encoding="utf-8") as f:
            raw = re.sub(r"url\(['\"]?(?!/|https?:|data:)([^'\")]+)['\"]?\)", r"url(/fonts/\1)", f.read())
        # latin subsets are inlined (every English and German glyph lives there); latin-ext rules go to the external sheet
        rules = re.findall(r"@font-face\{[^}]*\}", minify_css(raw))
        fonts_css = "".join(r for r in rules if "latin-ext" not in r)
        fonts_ext_css = "".join(r for r in rules if "latin-ext" in r)
    else:
        warnings.append("fonts/fonts.css is missing (run python tools/fonts.py); pages fall back to system fonts")
    with open(os.path.join(CSS_DIR, "critical.css"), encoding="utf-8") as f:
        critical_css = minify_css(f.read())
    with open(os.path.join(CSS_DIR, "site.css"), encoding="utf-8") as f:
        site_css = fonts_ext_css + minify_css(f.read())
    css_name = f"assets/styles.{hash8(site_css)}.css"
    write_text(out_root, css_name, site_css, written)
    js = {}
    for name in ("site", "room", "show"):
        path = os.path.join(JS_DIR, name + ".js")
        if os.path.exists(path):
            with open(path, "rb") as f:
                code = f.read()
        else:
            code = f"// {name}.js is not written yet (src/js/{name}.js missing at build time)\n".encode()
            warnings.append(f"src/js/{name}.js missing; an empty module was emitted")
        rel = f"assets/{name}.{hash8(code)}.js"
        write_bytes(out_root, rel, code, written)
        js[name] = "/" + rel
    assets = {"css": "/" + css_name, "site_js": js["site"], "room_js": js["room"], "show_js": js["show"],
              "critical_css": Markup(critical_css), "fonts_css": Markup(fonts_css),
              "preload_fonts": ["/fonts/Fraunces-300-700-normal-latin.woff2", "/fonts/InstrumentSans-400-700-normal-latin.woff2"]}
    for p in assets["preload_fonts"]:
        if not os.path.exists(os.path.join(ROOT, p.lstrip("/"))):
            warnings.append(f"preloaded font {p} does not exist")

    # ---- jinja
    env = Environment(loader=FileSystemLoader(TPL_DIR), autoescape=True, undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["nl2br"] = lambda s: Markup("<br>".join(env.filters["e"](x) for x in str(s).split("\n")))
    env.filters["jsonhtml"] = lambda o: Markup(json_for_html(o))
    env.globals["slugs"] = SLUG

    build_date = datetime.date.today()
    date_text = {"en": build_date.strftime("%-d %B %Y") if os.name != "nt" else build_date.strftime("%#d %B %Y"),
                 "de": f"{build_date.day}. {['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'][build_date.month - 1]} {build_date.year}"}

    pages = page_list(site)
    sitemap_entries = []
    inline_sizes = {}
    for pg in pages:
        lang, kind = pg["lang"], pg["kind"]
        other = "de" if lang == "en" else "en"
        T = lambda key, **kw: site.t(lang, key, **kw)
        views = site.views[lang]
        rooms = site.room_views[lang]
        hero = views[site.site["hero"]]
        page = {
            "lang": lang, "other": other, "kind": kind, "path": pg["path"], "url": site.abs_url(pg["path"]),
            "alt_path": pg["alt"], "alt_url": site.abs_url(pg["alt"]) if pg["alt"] else None,
            "noindex": pg.get("noindex", False), "theme": PAPER, "og_type": "website", "og_image": "/og/home.jpg",
            "jsonld": None, "room_data": None, "has_plates": kind in ("home", "works", "room", "work"),
            "body_class": "page-" + kind, "preload": None, "title": "", "description": "", "speculation": None,
            "work": None, "room": None, "hreflang": None if kind in ("impressum", "datenschutz") else True,
        }
        if kind == "home":
            page.update(title=T("meta.home_title"), description=T("meta.home_desc"), theme=hero["wall"],
                        jsonld=jsonld_home(site, lang, page["url"]), room_data=site.room_data(lang, site.hang),
                        preload={"srcset": hero["srcset_avif"], "href": hero["fallback"], "sizes": "(min-width: 1024px) calc(58vw - 96px), calc(100vw - 32px)"})
        elif kind == "works":
            page.update(title=T("meta.works_title"), description=T("meta.works_desc"),
                        room_data=site.room_data(lang, site.hang))
        elif kind == "room":
            room = next(r for r in rooms if r["slug"] == pg["slug"])
            page.update(title=T("meta.room_title", room=room["name"]), description=TS("meta.room_desc", room["text"], text=room["text"]), room=room,
                        og_image=room["og_image"], room_data=site.room_data(lang, room["ids"]))
        elif kind == "work":
            v = views[pg["id"]]
            room = next(r for r in rooms if r["slug"] == v["room"])
            i = v["index"]
            prev_id, next_id = site.hang[i - 1], site.hang[(i + 1) % site.total]
            ri = room["ids"].index(v["id"])
            n = len(room["ids"])
            rel_ids = []
            for off in (-2, -1, 1, 2):
                rid = room["ids"][(ri + off) % n]
                if rid != v["id"] and rid not in rel_ids:
                    rel_ids.append(rid)
            page.update(title=T("meta.work_title", no=v["id"], subject=v["subject"]), description=T("meta.work_desc", subject=v["subject"]),
                        theme=v["wall"], og_type="article", og_image=v["og_image"], work=v, room=room,
                        jsonld=jsonld_work(site, lang, v, room, page["url"]), room_data=site.room_data(lang, site.hang),
                        prev=views[prev_id], next=views[next_id], related=[views[r] for r in rel_ids],
                        preload={"srcset": v["srcset_avif"], "href": v["fallback"], "sizes": f"(min-width: 1024px) min(62vw, {v['maxw']}px), calc(100vw - 32px)"},
                        speculation={"prerender": [{"urls": [views[prev_id]["url"], views[next_id]["url"]], "eagerness": "moderate"}]})
        elif kind == "enquire":
            page.update(title=T("meta.enquire_title"), description=T("meta.enquire_desc"))
        elif kind == "thanks":
            page.update(title=T("meta.thanks_title"), description=T("thanks.text"))
        elif kind == "show":
            leads = [wid for wid in site.hang if views[wid]["eligible"]]
            page.update(title=T("meta.show_title"), description=TS("meta.show_desc", T("show.intro")), theme=hero["deep"],
                        room_data=site.room_data(lang, leads, extra_qr=True), leads=[views[w] for w in leads])
        elif kind == "impressum":
            page.update(title=T("meta.legal_impressum_title"), description=T("meta.legal_impressum_desc"))
        elif kind == "datenschutz":
            page.update(title=T("meta.legal_datenschutz_title"), description=T("meta.legal_datenschutz_desc"))

        def TS(key, default, **kw):
            return site.ts(lang, key, default, **kw)

        ctx = {
            "page": page, "site": site.site, "domain": site.domain, "lang": lang, "other": other, "t": T, "ts": TS,
            "ig_handle": "@" + site.site["instagram"].rstrip("/").rsplit("/", 1)[-1],
            "works": [views[w] for w in site.hang], "views": views, "rooms": rooms, "total": site.total,
            "hero": hero, "proof": [views[p] for p in site.site.get("proof", []) if p in views],
            "photo": views[site.photo] if site.photo else None, "assets": assets, "url": lambda kind, **kw: site.url(lang, kind, **kw),
            "formspree": FORMSPREE + site.site["formspree"], "thanks_url": site.abs_url(site.url(lang, "thanks")),
            "legal": site.site["legal"], "date_text": date_text[lang], "build_date": build_date.isoformat(),
            "count_text": lambda n: site.count_text(lang, n), "og_locale": OG_LOCALE[lang], "og_locale_alt": OG_LOCALE[other],
            "year": str(build_date.year),
            "crops": None,
        }
        crops_path = os.path.join(data_dir, "crops.json")
        if os.path.exists(crops_path):
            ctx["crops"] = read_json(crops_path)
        template = {"impressum": "legal_impressum.html", "datenschutz": "legal_datenschutz.html"}.get(kind, kind + ".html")
        html = compact_html(env.get_template(template).render(**ctx))
        rel = pg["path"].strip("/") + ("/" if pg["path"].strip("/") else "") + "index.html"
        write_text(out_root, rel, html, written)
        inline_sizes[rel] = sum(len(m.encode("utf-8")) for m in re.findall(r"<style>(.*?)</style>", html, flags=re.S))
        if not page["noindex"] and kind not in ("impressum", "datenschutz"):
            sitemap_entries.append((pg["path"], pg["alt"] if lang == "de" else pg["path"], pg["path"] if lang == "en" else pg["alt"]))
        elif kind in ("impressum", "datenschutz"):
            sitemap_entries.append((pg["path"], pg["path"], pg["path"]))

    # ---- 404 (one bilingual file)
    ctx404 = {"page": {"lang": "en", "other": "de", "kind": "404", "path": "/404.html", "url": site.abs_url("/404.html"), "alt_path": None,
                       "alt_url": None, "noindex": True, "theme": PAPER, "og_type": "website", "og_image": "/og/home.jpg", "jsonld": None,
                       "room_data": None, "has_plates": False, "body_class": "page-404", "preload": None, "speculation": None,
                       "title": site.t("en", "meta.error404_title") + " · " + site.t("de", "meta.error404_title"), "description": "",
                       "work": None, "room": None, "hreflang": None},
              "site": site.site, "domain": site.domain, "lang": "en", "other": "de", "t": lambda k, **kw: site.t("en", k, **kw),
              "t_de": lambda k, **kw: site.t("de", k, **kw), "assets": assets, "url": lambda kind, **kw: site.url("en", kind, **kw),
              "url_de": lambda kind, **kw: site.url("de", kind, **kw), "legal": site.site["legal"], "total": site.total,
              "og_locale": "en_GB", "og_locale_alt": "de_DE", "works": [], "rooms": site.room_views["en"], "hero": site.views["en"][site.site["hero"]],
              "ts": lambda k, d, **kw: site.ts("en", k, d, **kw), "year": str(build_date.year)}
    write_text(out_root, "404.html", compact_html(env.get_template("404.html").render(**ctx404)), written)

    # ---- machine files
    lastmod = git_date(data_dir) or build_date.isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for path, en, de in sitemap_entries:
        sm.append(f"  <url><loc>{site.abs_url(path)}</loc><lastmod>{lastmod}</lastmod>"
                  f'<xhtml:link rel="alternate" hreflang="en" href="{site.abs_url(en)}"/>'
                  f'<xhtml:link rel="alternate" hreflang="de" href="{site.abs_url(de)}"/>'
                  f'<xhtml:link rel="alternate" hreflang="x-default" href="{site.abs_url(en)}"/></url>')
    sm.append("</urlset>\n")
    write_text(out_root, "sitemap.xml", "\n".join(sm), written)
    write_text(out_root, "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {site.domain}/sitemap.xml\n", written)
    manifest = {"name": site.site["name"], "short_name": site.site["name"], "start_url": "/", "display": "browser", "lang": "en",
                "background_color": PAPER, "theme_color": PAPER, "icons": [
                    {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                    {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                    {"src": "/icons/favicon.svg", "sizes": "any", "type": "image/svg+xml"}]}
    write_text(out_root, "manifest.webmanifest", json.dumps(manifest, indent=1) + "\n", written)
    write_text(out_root, ".nojekyll", "", written)

    # ---- review sheet and checklist
    write_review(site, out_root, data_dir, written)
    write_checklist(site, out_root, written, warnings)

    # ---- manifest with stale-file deletion
    man_path = os.path.join(out_root, "build", "manifest.json")
    previous = []
    if os.path.exists(man_path):
        try:
            previous = read_json(man_path).get("files", [])
        except (ValueError, OSError):
            previous = []
    written.append("build/manifest.json")
    new_set = set(written)
    removed = 0
    for rel in previous:
        if rel not in new_set:
            p = os.path.join(out_root, rel)
            if os.path.isfile(p):
                os.remove(p)
                removed += 1
                d = os.path.dirname(p)
                while d and d != out_root and os.path.isdir(d) and not os.listdir(d):
                    os.rmdir(d)
                    d = os.path.dirname(d)
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump({"built": datetime.datetime.now().isoformat(timespec="seconds"), "files": sorted(new_set)}, f, indent=1)

    # ---- share cards and QR codes (other tools; non-fatal)
    if not args.no_images:
        for tool in ("og.py", "qr.py"):
            tp = os.path.join(ROOT, "tools", tool)
            if not os.path.exists(tp):
                warnings.append(f"tools/{tool} not found; skipped")
                continue
            r = subprocess.run([sys.executable, tp], cwd=ROOT)
            if r.returncode != 0:
                warnings.append(f"tools/{tool} exited with {r.returncode}")

    html_pages = sum(1 for w in new_set if w.endswith(".html"))
    log(f"{html_pages} HTML pages, {len(new_set)} files, {removed} stale files removed, "
        f"{(datetime.datetime.now() - t0).total_seconds():.1f}s -> {out_root}")
    log(f"inline CSS per page: max {max(inline_sizes.values())} B ({max(inline_sizes, key=inline_sizes.get)}); "
        f"external CSS {len(site_css.encode())} B")
    if site.fallback_keys:
        log(f"{len(site.fallback_keys)} string keys came from src/templates/_strings_needed.json "
            f"(merge them into data/strings.*.json): {', '.join(sorted(site.fallback_keys)[:8])}"
            + (" …" if len(site.fallback_keys) > 8 else ""))
    for w in warnings:
        log("warning: " + w)

    # ---- checks
    code = 0
    check = os.path.join(ROOT, "tools", "check.py")
    if os.path.exists(check):
        cmd = [sys.executable, check, "--root", out_root, "--data-dir", data_dir]
        if args.deploy:
            cmd.append("--deploy")
        code = subprocess.run(cmd, cwd=ROOT).returncode
    else:
        log("warning: tools/check.py not found; checks skipped")
    if args.deploy:
        todo = legal_todos(site.site)
        if todo:
            log("DEPLOY REFUSED: site.legal still has TODO in " + ", ".join(todo))
            code = 1
        if code:
            log("DEPLOY REFUSED: fix the items above (see build/CHECKLIST.md) and run again")
    return code


def legal_todos(site_json):
    return [k for k, v in (site_json.get("legal") or {}).items() if isinstance(v, str) and "TODO" in v]


def git_date(data_dir):
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", data_dir], cwd=ROOT, capture_output=True, text=True, timeout=10)
        d = r.stdout.strip()
        return d if re.fullmatch(r"\d{4}-\d\d-\d\d", d) else None
    except (OSError, subprocess.SubprocessError):
        return None


def write_review(site, out_root, data_dir, written):
    catalog = {}
    for cand in (os.path.join(data_dir, "catalog.json"), os.path.join(ROOT, "data", "catalog.json")):
        if os.path.exists(cand):
            try:
                catalog = {c["id"]: c for c in read_json(cand)}
            except (ValueError, KeyError, TypeError):
                catalog = {}
            break
    rows = [["id", "thumbnail", "subject_en", "subject_de", "old_title", "title_fits", "title_status", "panels",
             "medium", "width_cm", "height_cm", "year", "status", "zoom_candidate", "note"]]
    for wid in site.hang:
        w = site.by_id[wid]
        v = site.views["en"][wid]
        fits = catalog.get(wid, {}).get("title_fits")
        rows.append([wid, site.abs_url(v["src"]), v["subject"], site.views["de"][wid]["subject"], v["title_raw"] or "",
                     "" if fits is None else ("yes" if fits else "no"), w["title_status"], w.get("panels") or "",
                     (w.get("medium") or {}).get("en", "") if isinstance(w.get("medium"), dict) else "",
                     w.get("width_cm") or "", w.get("height_cm") or "", w.get("year") or "", w.get("status") or "",
                     "yes" if v["eligible"] else "", ""])
    for wid in site.excluded:
        w = site.by_id[wid]
        note = f"duplicate of {w['duplicate_of']}: is there a second painting?" if w.get("duplicate_of") else "studio photograph, not a painting"
        rows.append([wid, "", w["subject"]["en"], w["subject"].get("de", ""), (w.get("title") or {}).get("en", "") if isinstance(w.get("title"), dict) else "",
                     "", w.get("title_status", ""), "", "", "", "", "", "", "", note])
    path = os.path.join(out_root, "build", "REVIEW.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    written.append("build/REVIEW.csv")


def write_checklist(site, out_root, written, warnings):
    L = ["# Checklist — generated by tools/build.py", "",
         f"Collection: {site.total} paintings in {len(site.rooms)} rooms; excluded ids: {', '.join(site.excluded) or 'none'}.", "",
         "## Site", ""]
    todo = legal_todos(site.site)
    L.append(f"- [{'x' if not todo else ' '}] Legal data complete (site.json → legal): " + (", ".join(todo) + " still TODO" if todo else "done"))
    for w in site.works_raw:
        if w.get("duplicate_of"):
            L.append(f"- [ ] No. {w['id']} is a duplicate photo of No. {w['duplicate_of']}: ask whether a second painting exists")
        if w["kind"] == "photo":
            L.append(f"- [x] No. {w['id']} is the studio photograph (kind photo); it never counts as a painting")
    hero = site.views["en"][site.site["hero"]]
    L.append(f"- [{'x' if hero['eligible'] else ' '}] Hero No. {hero['id']} source long edge {hero['long_edge']} px (needs ≥ 2400)")
    for r in site.room_views["en"]:
        lead = site.views["en"][r["lead"]]
        L.append(f"- [{'x' if lead['eligible'] else ' '}] Room {r['name']}: lead No. {lead['id']} long edge {lead['long_edge']} px")
    L.append(f"- [{'x' if site.site.get('facts', {}).get('medium', {}).get('en') else ' '}] Medium sentence (site.json → facts.medium)")
    L.append(f"- [{'x' if (site.site.get('bio') or {}).get('en') else ' '}] Biography (site.json → bio)")
    L.append(f"- [{'x' if site.site.get('whatsapp') else ' '}] WhatsApp number (site.json → whatsapp)")
    L.append(f"- [{'x' if not site.fallback_keys else ' '}] All string keys present in data/strings.*.json"
             + (f" ({len(site.fallback_keys)} still taken from src/templates/_strings_needed.json)" if site.fallback_keys else ""))
    for w in warnings:
        L.append(f"- [ ] Build warning: {w}")
    L += ["", "## Per painting", "", "| No. | title | medium | dimensions | year | status | zoom QA | German |", "|---|---|---|---|---|---|---|---|"]
    for wid in site.hang:
        w = site.by_id[wid]
        v = site.views["en"][wid]
        de = []
        if not (w["subject"].get("de")):
            de.append("subject")
        if not (w["alt"].get("de")):
            de.append("alt")
        if w.get("desc") and not w["desc"].get("de"):
            de.append("desc")
        zoom = "set" if w.get("zoom") else ("QA pending" if v["eligible"] else "source too small")
        L.append(f"| {wid} | {'confirmed' if w['title_status'] == 'confirmed' else 'to confirm'} | {'ok' if w.get('medium') else 'missing'} | "
                 f"{'ok' if (w.get('width_cm') and w.get('height_cm')) else 'missing'} | {'ok' if w.get('year') else 'missing'} | "
                 f"{w.get('status') or 'missing'} | {zoom} | {', '.join(de) + ' missing' if de else 'ok'} |")
    L += ["", f"Review sheet: build/REVIEW.csv ({site.total} rows plus excluded ids).", ""]
    write_text(out_root, "build/CHECKLIST.md", "\n".join(L), written)


def main():
    ap = argparse.ArgumentParser(description="Build pinkal.art from data/ and src/.")
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--out", default=ROOT)
    ap.add_argument("--no-images", action="store_true", help="skip og.py and qr.py")
    ap.add_argument("--deploy", action="store_true", help="refuse while legal TODOs remain or a check fails")
    args = ap.parse_args()
    try:
        sys.exit(build(args))
    except BuildError as e:
        sys.exit("build.py: " + str(e))


if __name__ == "__main__":
    main()
