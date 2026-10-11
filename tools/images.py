#!/usr/bin/env python3
"""Responsive image pipeline for pinkal.art.

Reads the originals in sources/NN.jpg (never modified, never published) and writes

  images/r/NN-<width>.avif and NN-<width>.jpg   responsive variants
  data/images.json                              one entry per work, read by tools/build.py

Usage
  python tools/images.py              incremental: only new or changed sources are rendered
  python tools/images.py --force      render everything again
  python tools/images.py --only 13,29 limit the run to some ids (no stale cleanup for the others)
  python tools/images.py --check      verify the existing output and exit 1 on a failure, write nothing
  python tools/images.py -v           one line per work

Rules (build contract, section 3; brief, sections 8 and 11)
  Works are the ids of data/works.json (09, the duplicate, is skipped); without that file every
  sources/*.jpg is processed. Widths 200 400 800 1200 1600 2000, each only when it is at most the
  source width, plus the source width itself when it lies between two steps or below 200; 2400 only
  for works with "zoom": true. Portrait images are also capped at 2400 px height. Never upscaled.
  AVIF quality 58 speed 6; progressive JPEG quality 78 optimised; EXIF orientation applied; metadata
  stripped; sRGB. LQIP: 24 px JPEG data URI of at most 650 bytes. maxw = floor(width / 1.5).
  eligible_lead = long edge >= 2400. Colours: wall (OKLCH L .925, C <= .02) and deep (L .19,
  C <= .04) from an 8-cluster median-cut palette of the 400 px variant, contrast-verified
  (ink on wall >= 12:1, room ink on deep >= 10:1, muted room ink on deep >= 4.5:1; chroma is
  lowered in 0.005 steps until the gates pass). A manual "colour": {"wall", "deep"} in works.json wins.
"""
import argparse
import base64
import io
import json
import math
import os
import sys
import time

from PIL import Image, ImageCms, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")
OUT = os.path.join(ROOT, "images", "r")
DATA = os.path.join(ROOT, "data", "images.json")
WORKS = os.path.join(ROOT, "data", "works.json")
URL_PREFIX = "/images/r/"

STEPS = (200, 400, 800, 1200, 1600, 2000)
ZOOM_W = 2400
MAX_H = 2400
AVIF_OPTS = {"quality": 58, "speed": 6}
JPEG_OPTS = {"quality": 78, "optimize": True, "progressive": True}
LQIP_PX = 24
LQIP_MAX = 650
PALETTE_PX = 400

INK = "#141210"
ROOM_INK = "#e9e2d6"
ROOM_INK_2 = "#a39b90"
WALL_L, WALL_CMAX, WALL_FACTOR = 0.925, 0.02, 0.25
DEEP_L, DEEP_CMAX, DEEP_FACTOR = 0.19, 0.04, 0.6
WALL_GATES = ((INK, 12.0),)
DEEP_GATES = ((ROOM_INK, 10.0), (ROOM_INK_2, 4.5))
CHROMA_STEP = 0.005


# ----------------------------------------------------------------------------- colour maths
# sRGB <-> linear <-> OKLab <-> OKLCH, Bjorn Ottosson's matrices (2020, revised M1).

def _to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c):
    c = min(1.0, max(0.0, c))
    v = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return int(round(v * 255))


def rgb_to_oklab(r, g, b):
    r, g, b = _to_linear(r), _to_linear(g), _to_linear(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = l ** (1 / 3) if l > 0 else 0.0, m ** (1 / 3) if m > 0 else 0.0, s ** (1 / 3) if s > 0 else 0.0
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_to_rgb(L, a, b):
    l = L + 0.3963377774 * a + 0.2158037573 * b
    m = L - 0.1055613458 * a - 0.0638541728 * b
    s = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l ** 3, m ** 3, s ** 3
    return (_to_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            _to_srgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            _to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))


def rgb_to_oklch(r, g, b):
    L, a, bb = rgb_to_oklab(r, g, b)
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def oklch_to_hex(L, C, h):
    rad = math.radians(h)
    return hexc(oklab_to_rgb(L, C * math.cos(rad), C * math.sin(rad)))


def hexc(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    r, g, b = (_to_linear(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def gates_pass(bg, gates):
    return all(contrast(bg, fg) >= need for fg, need in gates)


def fit_contrast(L, C, h, gates):
    """Return (hex, final C, number of chroma steps taken). Lowers chroma 0.005 at a time."""
    steps = 0
    while True:
        hx = oklch_to_hex(L, C, h)
        if gates_pass(hx, gates) or C <= 0:
            return hx, C, steps
        C = max(0.0, round(C - CHROMA_STEP, 4))
        steps += 1


# ----------------------------------------------------------------------------- palette, wall, deep

def extract_palette(im):
    """8 median-cut clusters of an RGB image, largest first, each with hex, share and OKLCH."""
    q = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:8 * 3]
    counts = sorted(q.getcolors() or [], reverse=True)
    total = float(sum(c for c, _ in counts)) or 1.0
    out = []
    for n, idx in counts:
        rgb = tuple(pal[idx * 3: idx * 3 + 3])
        L, C, h = rgb_to_oklch(*rgb)
        out.append({"hex": hexc(rgb), "share": n / total, "L": L, "C": C, "h": h})
    return out


def derive_colours(clusters):
    """wall and deep per brief section 8, contrast-verified. Returns (wall, deep, notes)."""
    notes = []
    cand = [c for c in clusters if c["share"] >= 0.04] or clusters[:1]
    coloured = [c for c in cand if c["C"] >= 0.04 and 0.35 <= c["L"] <= 0.85]
    base = coloured[0] if coloured else cand[0]
    wall, c_final, steps = fit_contrast(WALL_L, min(WALL_CMAX, base["C"] * WALL_FACTOR), base["h"], WALL_GATES)
    if steps:
        notes.append("wall chroma lowered %d step(s) to %.3f" % (steps, c_final))
    dark = [c for c in cand if c["share"] >= 0.08] or cand
    base = min(dark, key=lambda c: c["L"])
    deep, c_final, steps = fit_contrast(DEEP_L, min(DEEP_CMAX, base["C"] * DEEP_FACTOR), base["h"], DEEP_GATES)
    if steps:
        notes.append("deep chroma lowered %d step(s) to %.3f" % (steps, c_final))
    return wall, deep, notes


def make_lqip(im):
    """24 px long-edge JPEG data URI of at most LQIP_MAX bytes (quality, then size, stepped down)."""
    for px in (LQIP_PX, 20, 16):
        t = im.copy()
        t.thumbnail((px, px), Image.Resampling.LANCZOS)
        t.info = {}
        for q in range(40, 5, -5):
            buf = io.BytesIO()
            t.save(buf, "JPEG", quality=q, optimize=True)
            uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
            if len(uri) <= LQIP_MAX:
                return uri
    return uri


# ----------------------------------------------------------------------------- variant planning

def plan_widths(w, h, zoom):
    """Variant widths for a w x h source: the ladder up to the source width, the source width when
    it lies between steps or below 200, a 2400 step only with zoom, portrait height capped at 2400,
    near-duplicate widths (< 4 % apart) dropped. Never wider than the source."""
    ladder = list(STEPS) + ([ZOOM_W] if zoom else [])
    cands = [s for s in ladder if s <= w]
    if w < ladder[-1] and w not in ladder:
        cands.append(w)
    capped = set()
    for s in cands:
        if round(h * s / w) > MAX_H:
            s = int(math.floor(MAX_H * w / h))
        capped.add(min(s, w))
    out = []
    for s in sorted(capped):
        if out and s < out[-1] * 1.04:
            continue
        out.append(s)
    return out


def variant_h(w, h, s):
    return max(1, min(MAX_H, int(round(h * s / w))))


def variant_files(wid, widths):
    for s in widths:
        yield s, "%s-%d.avif" % (wid, s), "%s-%d.jpg" % (wid, s)


# ----------------------------------------------------------------------------- source handling

def load_works():
    """(ids, zoom-by-id, colour-override-by-id, skipped) from data/works.json, or every source."""
    if os.path.exists(WORKS):
        with open(WORKS, encoding="utf-8") as f:
            works = json.load(f)
        if isinstance(works, dict):
            works = works.get("works", [])
        ids, zoom, colour, skipped = [], {}, {}, []
        for wk in works:
            wid = str(wk.get("id", "")).strip()
            if not wid:
                continue
            if wk.get("duplicate_of"):
                skipped.append("%s (duplicate_of %s)" % (wid, wk["duplicate_of"]))
                continue
            ids.append(wid)
            zoom[wid] = bool(wk.get("zoom"))
            if isinstance(wk.get("colour"), dict):
                colour[wid] = wk["colour"]
        return sorted(set(ids)), zoom, colour, skipped, "data/works.json"
    ids = sorted(os.path.splitext(n)[0] for n in os.listdir(SRC) if n.lower().endswith(".jpg"))
    return ids, {}, {}, [], "sources/*.jpg (data/works.json not found)"


def source_header(path):
    """(w, h, needs_full_transpose) without decoding the pixels."""
    with Image.open(path) as im:
        w, h = im.size
        orientation = im.getexif().get(274, 1)
    if orientation in (5, 6, 7, 8):
        w, h = h, w
    return w, h


def open_srgb(path):
    """Decode a source: EXIF orientation applied, ICC profile converted to sRGB, metadata dropped."""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    icc = im.info.get("icc_profile")
    if icc:
        try:
            im = ImageCms.profileToProfile(im.convert("RGB"), ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                           ImageCms.createProfile("sRGB"), outputMode="RGB")
        except Exception as e:  # keep going with the untagged pixels rather than fail the build
            print("  warning: %s: ICC conversion failed (%s); assuming sRGB" % (os.path.basename(path), e))
    im = im.convert("RGB")
    im.info = {}
    return im


def render_variants(im, wid, needed):
    """needed: list of (width, height, fmt, path)."""
    cache = {}
    for s, vh, fmt, path in needed:
        if (s, vh) not in cache:
            cache[(s, vh)] = im if (s, vh) == im.size else im.resize((s, vh), Image.Resampling.LANCZOS, reducing_gap=3.0)
        v = cache[(s, vh)]
        v.info = {}
        if fmt == "avif":
            v.save(path, "AVIF", **AVIF_OPTS)
        else:
            v.save(path, "JPEG", **JPEG_OPTS)


# ----------------------------------------------------------------------------- main run

def process(wid, zoom, override, prev, force, verbose):
    src = os.path.join(SRC, wid + ".jpg")
    if not os.path.exists(src):
        return None, "source missing: sources/%s.jpg" % wid, 0, 0
    st = os.stat(src)
    sig = {"src_size": st.st_size, "src_mtime": int(st.st_mtime)}
    w, h = source_header(src)
    widths = plan_widths(w, h, zoom)
    unchanged = (not force and prev is not None and prev.get("src_size") == sig["src_size"]
                 and prev.get("src_mtime") == sig["src_mtime"])
    needed = []
    for s, fa, fj in variant_files(wid, widths):
        vh = variant_h(w, h, s)
        for fmt, name in (("avif", fa), ("jpg", fj)):
            path = os.path.join(OUT, name)
            if force or not unchanged or not os.path.exists(path):
                needed.append((s, vh, fmt, path))
    if needed:
        render_variants(open_srgb(src), wid, needed)
    variants = []
    for s, fa, fj in variant_files(wid, widths):
        variants.append({"w": s, "h": variant_h(w, h, s), "avif": URL_PREFIX + fa, "jpg": URL_PREFIX + fj,
                         "bytes_avif": os.path.getsize(os.path.join(OUT, fa)),
                         "bytes_jpg": os.path.getsize(os.path.join(OUT, fj))})
    # palette and placeholder from the 400 px variant (the largest one at or below 400 px)
    thumb = max((v for v in variants if v["w"] <= PALETTE_PX), key=lambda v: v["w"], default=variants[0])
    with Image.open(os.path.join(OUT, os.path.basename(thumb["jpg"]))) as t:
        t = t.convert("RGB")
        clusters = extract_palette(t)
        wall, deep, notes = derive_colours(clusters)
        lqip = make_lqip(t)
    colour_source = "auto"
    if override:
        o_wall, o_deep = override.get("wall"), override.get("deep")
        if o_wall:
            wall, colour_source = o_wall.lower(), "manual"
            if not gates_pass(wall, WALL_GATES):
                notes.append("manual wall %s fails the %.0f:1 ink gate (kept, override wins)" % (wall, WALL_GATES[0][1]))
        if o_deep:
            deep, colour_source = o_deep.lower(), "manual"
            if not gates_pass(deep, DEEP_GATES):
                notes.append("manual deep %s fails a room-ink gate (kept, override wins)" % deep)
    entry = {
        "src": "sources/%s.jpg" % wid, "w": w, "h": h, "ar": round(w / h, 4), "long_edge": max(w, h),
        "maxw": int(math.floor(w / 1.5)), "eligible_lead": max(w, h) >= 2400,
        "variants": variants, "lqip": lqip, "wall": wall, "deep": deep, "colour_source": colour_source,
        "palette": [{"hex": c["hex"], "share": round(c["share"], 3)} for c in clusters],
        **sig,
    }
    if verbose:
        print("%s: %dx%d -> %s%s wall=%s deep=%s lqip=%dB%s" % (
            wid, w, h, [v["w"] for v in variants], " zoom" if zoom else "", wall, deep, len(lqip),
            (" rendered %d" % len(needed)) if needed else " (unchanged)"))
    return entry, notes, len(needed), len(widths) * 2 - len(needed)


def verify(data, zoom_by_id, works_source):
    """Gate G2 checks over an images.json dict. Returns a list of failure strings."""
    fails = []
    adjust = 0
    for wid, e in data.items():
        for k in ("variants", "lqip", "wall", "deep", "maxw", "w", "h", "ar", "long_edge", "eligible_lead"):
            if k not in e:
                fails.append("%s: missing key %s" % (wid, k))
        if not e.get("variants"):
            fails.append("%s: no variants" % wid)
            continue
        for v in e["variants"]:
            if v["w"] > e["w"] or v["h"] > e["h"]:
                fails.append("%s: variant %dx%d wider than source %dx%d" % (wid, v["w"], v["h"], e["w"], e["h"]))
            if v["h"] > MAX_H:
                fails.append("%s: variant height %d > %d" % (wid, v["h"], MAX_H))
            if v["w"] >= ZOOM_W and not zoom_by_id.get(wid):
                fails.append("%s: 2400 variant without zoom: true" % wid)
            for key in ("avif", "jpg"):
                if not os.path.exists(os.path.join(OUT, os.path.basename(v[key]))):
                    fails.append("%s: missing file %s" % (wid, v[key]))
        if len(e.get("lqip", "")) > LQIP_MAX:
            fails.append("%s: lqip %d B > %d" % (wid, len(e["lqip"]), LQIP_MAX))
        if e.get("maxw") != int(math.floor(e["w"] / 1.5)):
            fails.append("%s: maxw %s != floor(w/1.5)" % (wid, e.get("maxw")))
        if e.get("colour_source") == "auto":
            if not gates_pass(e["wall"], WALL_GATES):
                fails.append("%s: ink on wall %s = %.2f:1 < 12" % (wid, e["wall"], contrast(e["wall"], INK)))
            if not gates_pass(e["deep"], DEEP_GATES):
                fails.append("%s: room ink on deep %s = %.2f / %.2f" % (
                    wid, e["deep"], contrast(e["deep"], ROOM_INK), contrast(e["deep"], ROOM_INK_2)))
    return fails


def summarize(data, zoom_by_id):
    n_files = sum(len(e["variants"]) * 2 for e in data.values())
    n_bytes = sum(v["bytes_avif"] + v["bytes_jpg"] for e in data.values() for v in e["variants"])
    lq = [len(e["lqip"]) for e in data.values()]
    walls = [contrast(e["wall"], INK) for e in data.values()]
    deeps = [min(contrast(e["deep"], ROOM_INK) / 10.0, contrast(e["deep"], ROOM_INK_2) / 4.5) for e in data.values()]
    deep_min = min((contrast(e["deep"], ROOM_INK) for e in data.values()), default=0)
    deep2_min = min((contrast(e["deep"], ROOM_INK_2) for e in data.values()), default=0)
    n2400 = sum(1 for e in data.values() for v in e["variants"] if v["w"] >= ZOOM_W)
    leads = sum(1 for e in data.values() if e["eligible_lead"])
    print("  %d works, %d variant files, %.1f MB in images/r, %d eligible leads (long edge >= 2400), "
          "%d zoom works, %d 2400-px variants" % (len(data), n_files, n_bytes / 1e6, leads,
                                                  sum(1 for z in zoom_by_id.values() if z), n2400))
    if lq:
        print("  lqip: max %d B, mean %d B (limit %d); contrast: ink on wall min %.2f:1 (>= 12), "
              "room ink on deep min %.2f:1 (>= 10), muted room ink on deep min %.2f:1 (>= 4.5)"
              % (max(lq), sum(lq) / len(lq), LQIP_MAX, min(walls), deep_min, deep2_min))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="render every variant again")
    ap.add_argument("--only", default="", help="comma-separated ids to process")
    ap.add_argument("--check", action="store_true", help="verify data/images.json and images/r, write nothing")
    ap.add_argument("-v", "--verbose", action="store_true", help="one line per work")
    a = ap.parse_args()

    ids, zoom_by_id, colour_by_id, skipped, works_source = load_works()
    if a.check:
        if not os.path.exists(DATA):
            sys.exit("images.py --check: data/images.json is missing; run python tools/images.py first")
        with open(DATA, encoding="utf-8") as f:
            data = json.load(f)
        missing = [i for i in ids if i not in data]
        fails = verify(data, zoom_by_id, works_source) + ["%s: not in images.json" % i for i in missing]
        summarize(data, zoom_by_id)
        for fl in fails:
            print("  FAIL " + fl)
        print("images.py --check: %s" % ("OK" if not fails else "%d failure(s)" % len(fails)))
        sys.exit(1 if fails else 0)

    only = set(x.strip() for x in a.only.split(",") if x.strip())
    todo = [i for i in ids if not only or i in only]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    prev = {}
    if os.path.exists(DATA):
        try:
            with open(DATA, encoding="utf-8") as f:
                prev = json.load(f)
        except (OSError, ValueError):
            prev = {}

    t0 = time.time()
    data = {}
    rendered = reused = 0
    warnings, notes = [], []
    for wid in todo:
        entry, msg, n_new, n_old = process(wid, zoom_by_id.get(wid, False), colour_by_id.get(wid), prev.get(wid),
                                           a.force, a.verbose)
        if entry is None:
            warnings.append(msg)
            continue
        data[wid] = entry
        rendered += n_new
        reused += n_old
        for n in msg:
            notes.append("%s: %s" % (wid, n))
    if only:  # keep the untouched entries of a partial run
        for wid, e in prev.items():
            if wid not in data and wid in ids:
                data[wid] = e
    data = dict(sorted(data.items()))

    # stale cleanup: anything in images/r that no current entry references
    keep = {os.path.basename(v[k]) for e in data.values() for v in e["variants"] for k in ("avif", "jpg")}
    removed = 0
    for name in os.listdir(OUT):
        if name not in keep:
            os.remove(os.path.join(OUT, name))
            removed += 1

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")

    fails = verify(data, zoom_by_id, works_source)
    print("images.py: works from %s; %d rendered, %d reused, %d stale files removed, %.0f s"
          % (works_source, rendered, reused, removed, time.time() - t0))
    summarize(data, zoom_by_id)
    for s in skipped:
        print("  skipped %s" % s)
    for n in notes:
        print("  note: " + n)
    for wmsg in warnings:
        print("  warning: " + wmsg)
    for fl in fails:
        print("  FAIL " + fl)
    print("  checks: %s" % ("all gates pass" if not fails else "%d failure(s)" % len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
