#!/usr/bin/env python3
"""Quality gates for the generated site (run by tools/build.py; also standalone).

    python tools/check.py [--root DIR] [--data-dir DIR] [--deploy]

Checks: byte budgets, strings key parity, banned words, literal digits in strings, WCAG contrast of
the token pairs and of every painting's wall/deep tints, internal links, img width/height/alt,
canonical + hreflang on every page. Prints a compact table and exits non-zero on failure.
With --deploy, missing share cards, QR codes and icons count as failures too.
"""
import argparse
import gzip
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(ROOT, "src", "templates")

KB = 1024
BUDGETS = {"home_raw": 60 * KB, "work_raw": 25 * KB, "inline_css": 8 * KB, "ext_css": 32 * KB, "site_js_gz": 12 * KB, "room_js_gz": 10 * KB}
BANNED = re.compile(r"imagin|dream|never existed|soul|visionary|self-taught|\b(she|her|he|his)\b", re.I)
# Descriptions name the people in a painting ("a couple, he in a hat"), so pronouns are allowed there;
# the words that describe the artist's work ("imagined", "dream", ...) stay banned everywhere.
BANNED_DESC = re.compile(r"imagin|dream|never existed|soul|visionary|self-taught", re.I)
ALLOWED_DIGITS = [r"\{[a-z_]+\}", r"(§|Art\.|Abs\.|Nr\.)\s?\d+[a-z]?", r"\b1:1\b", r"\b\d{5}\b", r"\+?\d[\d /-]{6,}\d"]
TOKENS = {"paper": "#f5f0e8", "paper-2": "#ece6db", "ink": "#141210", "ink-2": "#4a4440", "ink-3": "#6b625b", "accent": "#b5472a",
          "accent-ink": "#8f3620", "focus": "#1f5fa8", "ok": "#2e6b45", "reserved": "#7a561b", "sold": "#8c2f2f", "room": "#0e0d0c",
          "room-ink": "#e9e2d6", "room-ink-2": "#a39b90", "focus-room": "#9cc2ff"}
PAIRS = [("ink", "paper", 4.5), ("ink-2", "paper", 4.5), ("ink-3", "paper", 4.5), ("accent", "paper", 3.0), ("accent-ink", "paper", 4.5),
         ("focus", "paper", 3.0), ("ok", "paper", 4.5), ("reserved", "paper", 4.5), ("sold", "paper", 4.5), ("ink", "paper-2", 4.5),
         ("ink-2", "paper-2", 4.5), ("ink-3", "paper-2", 4.5), ("accent-ink", "paper-2", 4.5), ("room-ink", "room", 4.5),
         ("room-ink-2", "room", 4.5), ("focus-room", "room", 3.0), ("paper", "accent-ink", 4.5)]
PENDING_PREFIXES = ("/og/", "/images/qr/", "/icons/")


def luminance(hexc):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.imgs, self.styles, self.canonical, self.hreflang, self.h1, self.lang, self.title, self.theme = [], [], [], None, [], 0, None, False, False
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "style":
            self._in_style = True
        if tag == "meta" and a.get("name") == "theme-color":
            self.theme = True
        if tag == "link":
            if a.get("rel") == "canonical":
                self.canonical = a.get("href")
            if a.get("rel") == "alternate" and a.get("hreflang"):
                self.hreflang.append(a["hreflang"])
            if a.get("href"):
                self.links.append(a["href"])
            if a.get("imagesrcset"):
                self.links += [p.strip().split()[0] for p in a["imagesrcset"].split(",") if p.strip()]
        if tag in ("a", "area") and a.get("href"):
            self.links.append(a["href"])
        if tag in ("script", "source", "iframe") and a.get("src"):
            self.links.append(a["src"])
        if tag in ("source", "img") and a.get("srcset"):
            self.links += [p.strip().split()[0] for p in a["srcset"].split(",") if p.strip()]
        if tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.links.append(a["src"])
        if tag == "meta" and a.get("property") in ("og:image",) and a.get("content"):
            self.links.append(a["content"])
        if tag == "form" and a.get("action"):
            self.links.append(a["action"])

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.styles.append(data)


def walk_html(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "sources", "src", "tools", "build", "docs")]
        for fn in filenames:
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def gz_size(path):
    with open(path, "rb") as f:
        return len(gzip.compress(f.read(), 9))


def strip_allowed(s):
    for pat in ALLOWED_DIGITS:
        s = re.sub(pat, " ", s)
    return s


def json_values(obj, skip_keys=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip_keys:
                continue
            yield from json_values(v, skip_keys)
    elif isinstance(obj, list):
        for v in obj:
            yield from json_values(v, skip_keys)
    elif isinstance(obj, str):
        yield obj


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--deploy", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    data_dir = os.path.abspath(a.data_dir)
    rows = []  # (name, ok, detail)
    warn = []

    def row(name, ok, detail):
        rows.append((name, bool(ok), detail))

    # ---- budgets
    home = os.path.join(root, "index.html")
    if os.path.exists(home):
        sz = os.path.getsize(home)
        row("home HTML <= 60 KB raw", sz <= BUDGETS["home_raw"], f"{sz} B raw, {gz_size(home)} B gz")
    else:
        row("home HTML", False, "index.html missing")
    works = sorted(p for p in walk_html(os.path.join(root, "works")) if os.path.basename(os.path.dirname(p)) != "works")
    if works:
        big = max(works, key=os.path.getsize)
        row("artwork page <= 25 KB raw", os.path.getsize(big) <= BUDGETS["work_raw"], f"max {os.path.getsize(big)} B ({os.path.relpath(big, root)}), {len(works)} EN pages")
    else:
        row("artwork pages", False, "no works/NN/index.html found")
    css = sorted(os.listdir(os.path.join(root, "assets"))) if os.path.isdir(os.path.join(root, "assets")) else []
    ext = [c for c in css if c.startswith("styles.") and c.endswith(".css")]
    if ext:
        sz = os.path.getsize(os.path.join(root, "assets", ext[-1]))
        row("external CSS <= 32 KB", sz <= BUDGETS["ext_css"], f"{sz} B ({ext[-1]})")
    else:
        row("external CSS", False, "assets/styles.*.css missing")
    for name, key in (("site", "site_js_gz"), ("room", "room_js_gz")):
        files = [c for c in css if c.startswith(name + ".") and c.endswith(".js")]
        if files:
            gz = gz_size(os.path.join(root, "assets", files[-1]))
            row(f"{name}.js <= {BUDGETS[key] // KB} KB gz", gz <= BUDGETS[key], f"{gz} B gz ({files[-1]})")
        else:
            row(f"{name}.js", False, f"assets/{name}.*.js missing")

    # ---- strings parity, banned words, digits
    strings = {}
    for lang in ("en", "de"):
        p = os.path.join(data_dir, f"strings.{lang}.json")
        if os.path.exists(p):
            strings[lang] = json.load(open(p, encoding="utf-8"))
    if len(strings) == 2:
        diff = sorted(set(strings["en"]) ^ set(strings["de"]))
        row("strings key parity", not diff, f"{len(strings['en'])} keys" if not diff else "only in one file: " + ", ".join(diff[:10]))
    else:
        row("strings key parity", False, "strings.en.json / strings.de.json missing")
    hits = []
    for lang, table in strings.items():
        for k, v in table.items():
            m = BANNED.search(v)
            if m:
                hits.append(f"strings.{lang}:{k} '{m.group(0)}'")
    for fn in sorted(os.listdir(TPL_DIR)) + [os.path.join("partials", f) for f in sorted(os.listdir(os.path.join(TPL_DIR, "partials")))]:
        p = os.path.join(TPL_DIR, fn)
        if fn.endswith(".html") and os.path.isfile(p):
            for i, line in enumerate(read(p).splitlines(), 1):
                m = BANNED.search(line)
                if m:
                    hits.append(f"templates/{fn}:{i} '{m.group(0)}'")
    for name in ("works", "rooms", "site"):
        p = os.path.join(data_dir, name + ".json")
        if os.path.exists(p):
            obj = json.load(open(p, encoding="utf-8"))
            for v in json_values(obj, skip_keys=("title", "title_de", "old_title", "old_desc", "desc", "alt")):
                m = BANNED.search(v)
                if m:
                    hits.append(f"{name}.json '{m.group(0)}' in '{v[:40]}'")
            if name == "works":
                for w in obj:
                    for fld in ("desc", "alt"):
                        for v in json_values(w.get(fld)):
                            m = BANNED_DESC.search(v)
                            if m:
                                hits.append(f"works.json {w.get('id')} {fld} '{m.group(0)}'")
    row("banned words", not hits, f"{len(hits)} hits: " + "; ".join(hits[:6]) if hits else "none in strings, templates, rendered data")
    digits = []
    for lang, table in strings.items():
        for k, v in table.items():
            if re.search(r"\d", strip_allowed(v)):
                digits.append(f"{lang}:{k}")
    row("no literal digits in strings", not digits, ", ".join(digits[:8]) if digits else "only placeholders, § / Art. references, postcodes, phone numbers")

    # ---- contrast
    bad = [f"{f}/{b} {contrast(TOKENS[f], TOKENS[b]):.2f}<{m}" for f, b, m in PAIRS if contrast(TOKENS[f], TOKENS[b]) < m]
    row("token contrast", not bad, ", ".join(bad) if bad else f"{len(PAIRS)} pairs pass (min {min(contrast(TOKENS[f], TOKENS[b]) for f, b, _ in PAIRS):.2f})")
    img_path = os.path.join(data_dir, "images.json")
    works_path = os.path.join(data_dir, "works.json")
    if os.path.exists(img_path) and os.path.exists(works_path):
        images = json.load(open(img_path, encoding="utf-8"))
        wl = json.load(open(works_path, encoding="utf-8"))
        overrides = {w["id"]: (w.get("colour") or {}) for w in wl}
        worst_wall, worst_deep, worst_deep2, fails = 99, 99, 99, []
        for wid, e in images.items():
            wall = overrides.get(wid, {}).get("wall") or e.get("wall")
            deep = overrides.get(wid, {}).get("deep") or e.get("deep")
            if not (wall and deep):
                fails.append(f"{wid} no tints")
                continue
            cw, cd, cd2 = contrast(TOKENS["ink"], wall), contrast(TOKENS["room-ink"], deep), contrast(TOKENS["room-ink-2"], deep)
            worst_wall, worst_deep, worst_deep2 = min(worst_wall, cw), min(worst_deep, cd), min(worst_deep2, cd2)
            if cw < 12 or cd < 10 or cd2 < 4.5:
                fails.append(f"{wid} wall {cw:.1f} deep {cd:.1f}/{cd2:.1f}")
        row("per-work tint contrast", not fails, f"{len(images)} works; min ink/wall {worst_wall:.2f}, room-ink/deep {worst_deep:.2f}, room-ink-2/deep {worst_deep2:.2f}"
            + ("; fails: " + ", ".join(fails[:6]) if fails else ""))
    else:
        row("per-work tint contrast", False, "images.json or works.json missing")

    # ---- pages: links, imgs, canonical, hreflang, inline css
    pages = list(walk_html(root))
    missing, pending, img_bad, head_bad, inline_max, inline_page = [], [], [], [], 0, ""
    site_json = os.path.join(data_dir, "site.json")
    domain = json.load(open(site_json, encoding="utf-8")).get("domain", "https://pinkal.art").rstrip("/") if os.path.exists(site_json) else "https://pinkal.art"
    seen = set()
    for p in pages:
        pg = Page()
        pg.feed(read(p))
        rel = os.path.relpath(p, root).replace("\\", "/")
        inline = sum(len(s.encode("utf-8")) for s in pg.styles)
        if inline > inline_max:
            inline_max, inline_page = inline, rel
        if not pg.lang or not pg.title or not pg.theme or pg.h1 != 1:
            head_bad.append(f"{rel} (lang {pg.lang}, title {pg.title}, theme {pg.theme}, h1 x{pg.h1})")
        if not pg.canonical:
            head_bad.append(f"{rel} no canonical")
        if rel != "404.html" and not ({"de", "x-default"} <= set(pg.hreflang) and (rel.startswith(("impressum", "datenschutz")) or "en" in pg.hreflang)):
            head_bad.append(f"{rel} hreflang {pg.hreflang}")
        for im in pg.imgs:
            if im.get("src") and (not im.get("width") or not im.get("height") or "alt" not in im):
                img_bad.append(f"{rel}: {im.get('src')}")
        for href in pg.links:
            if href.startswith(domain):
                href = href[len(domain):] or "/"
            u = urlsplit(href)
            if u.scheme or href.startswith(("#", "mailto:", "tel:", "data:")) or not u.path:
                continue
            path = unquote(u.path)
            target = path if path.startswith("/") else "/" + os.path.relpath(os.path.join(os.path.dirname(rel), path), ".").replace("\\", "/")
            if (target, ) in seen:
                continue
            seen.add((target, ))
            cands = [os.path.join(root, target.lstrip("/")), os.path.join(ROOT, target.lstrip("/"))]
            ok = any(os.path.isfile(c) or os.path.isfile(os.path.join(c, "index.html")) for c in cands)
            if not ok:
                (pending if target.startswith(PENDING_PREFIXES) else missing).append(f"{target} (from {rel})")
    row("pages parsed", bool(pages), f"{len(pages)} HTML files")
    row("inline CSS <= 8 KB", inline_max <= BUDGETS["inline_css"], f"max {inline_max} B ({inline_page})")
    row("internal links", not missing, f"{len(seen)} distinct targets; broken: " + ", ".join(missing[:6]) if missing else f"{len(seen)} distinct targets, 0 broken")
    if pending:
        row("share cards / QR / icons present", not a.deploy, f"{len(pending)} not generated yet: " + ", ".join(sorted(set(x.split(' (')[0] for x in pending))[:5]))
    else:
        row("share cards / QR / icons present", True, "all referenced files exist")
    row("img width/height/alt", not img_bad, ", ".join(img_bad[:5]) if img_bad else "every <img> with a src has all three")
    row("lang/title/theme-color/h1/canonical/hreflang", not head_bad, "; ".join(head_bad[:5]) if head_bad else "every page")

    # ---- report
    width = max(len(r[0]) for r in rows)
    failed = [r for r in rows if not r[1]]
    print("check.py")
    for name, ok, detail in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    print(f"check.py: {len(rows) - len(failed)} passed, {len(failed)} failed" + (" (deploy mode)" if a.deploy else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
