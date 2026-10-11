#!/usr/bin/env python3
"""Self-host Google Fonts (GDPR: no requests to Google from visitors) with metric-matched fallbacks.

Usage: python tools/fonts.py "Family Name:ital,wght@0,400;0,700;1,400" "Other:wght@300..700"
       python tools/fonts.py --metrics      only recompute the fallback faces in fonts/fonts.css

Downloads woff2 files (latin + latin-ext subsets only) into fonts/ and writes fonts/fonts.css with
@font-face rules pointing at the local files (font-display: swap). It then appends one
"<Family> Fallback" face per family (Georgia for Fraunces, Arial for Instrument Sans) whose
size-adjust, ascent-override, descent-override and line-gap-override are computed with fontTools,
so the swap from the fallback to the web font barely moves the layout. That step needs fontTools
and brotli (pip install fonttools brotli) and the system Georgia/Arial files; without them the
fallback faces already in fonts.css are kept. Re-run to change the set.
"""
import glob
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "fonts")
CSS = os.path.join(OUT, "fonts.css")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
KEEP_SUBSETS = {"latin", "latin-ext"}

# family -> (fallback family, candidate files, variable-font location the metrics are measured at)
FALLBACKS = {
    "Fraunces": ("Georgia", ("georgia.ttf", "Georgia.ttf"), {"wght": 400, "opsz": 72}),
    "Instrument Sans": ("Arial", ("arial.ttf", "Arial.ttf"), {"wght": 400}),
}
FONT_DIRS = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), "/Library/Fonts",
             "/System/Library/Fonts/Supplemental", os.path.expanduser("~/Library/Fonts"),
             "/usr/share/fonts/truetype/msttcorefonts"]
# English letter frequencies (percent) plus the space, for a text-weighted average advance width
FREQ = {" ": 18.3, "e": 10.2, "t": 7.5, "a": 6.5, "o": 6.2, "i": 5.7, "n": 5.7, "s": 5.3, "r": 5.0, "h": 5.0,
        "l": 3.3, "d": 3.3, "c": 2.3, "u": 2.3, "m": 2.0, "f": 1.9, "w": 1.7, "g": 1.6, "y": 1.6, "p": 1.5,
        "b": 1.3, "v": 0.9, "k": 0.7, "x": 0.15, "j": 0.1, "q": 0.1, "z": 0.07}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


# ----------------------------------------------------------------------------- fallback metrics

def _avg_width(font):
    cmap, hmtx, upem = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    total = weight = 0.0
    for ch, f in FREQ.items():
        g = cmap.get(ord(ch))
        if g:
            total += hmtx[g][0] * f
            weight += f
    return total / weight / upem


def _vertical(font):
    upem, os2, hh = font["head"].unitsPerEm, font["OS/2"], font["hhea"]
    if os2.fsSelection & (1 << 7):  # USE_TYPO_METRICS
        asc, desc, gap = os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap
    else:
        asc, desc, gap = hh.ascent, hh.descent, hh.lineGap
    return asc / upem, abs(desc) / upem, gap / upem


def _find_system_font(names):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


def fallback_rules():
    """One metric-matched @font-face per family in FALLBACKS, or [] with a printed reason."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        print("fonts.py: fontTools not installed; fallback metrics skipped (pip install fonttools brotli)")
        return []
    rules = []
    for family, (fb_family, fb_files, loc) in FALLBACKS.items():
        web = sorted(glob.glob(os.path.join(OUT, family.replace(" ", "") + "-*-normal-latin.woff2")))
        if not web:
            continue
        fb_path = _find_system_font(fb_files)
        if not fb_path:
            print("fonts.py: %s not found on this system; fallback face for %s skipped" % (fb_family, family))
            continue
        try:
            wf = TTFont(web[0])
            if "fvar" in wf:
                axes = {a.axisTag: a for a in wf["fvar"].axes}
                at = {k: min(max(v, axes[k].minValue), axes[k].maxValue) for k, v in loc.items() if k in axes}
                wf = instancer.instantiateVariableFont(wf, at)
            ff = TTFont(fb_path)
        except ImportError as e:  # woff2 needs brotli
            print("fonts.py: cannot read %s (%s); fallback metrics skipped (pip install brotli)" % (os.path.basename(web[0]), e))
            return []
        adjust = _avg_width(wf) / _avg_width(ff)
        asc, desc, gap = _vertical(wf)
        rules.append("@font-face{font-family:'%s Fallback';src:local('%s');size-adjust:%.2f%%;ascent-override:%.2f%%;"
                     "descent-override:%.2f%%;line-gap-override:%.2f%%}"
                     % (family, fb_family, adjust * 100, asc / adjust * 100, desc / adjust * 100, gap / adjust * 100))
        print("  %s Fallback = %s: size-adjust %.1f%% (avg width %.3f vs %.3f em), ascent %.1f%%, descent %.1f%%"
              % (family, fb_family, adjust * 100, _avg_width(wf), _avg_width(ff), asc / adjust * 100, desc / adjust * 100))
    return rules


def write_css(header, rules, fallbacks):
    with open(CSS, "w", encoding="utf-8") as f:
        f.write(header.rstrip("\n") + "\n" + "\n".join(rules + fallbacks) + "\n")


# ----------------------------------------------------------------------------- download

def main(specs):
    os.makedirs(OUT, exist_ok=True)
    url = "https://fonts.googleapis.com/css2?" + "&".join("family=" + urllib.parse.quote(s, safe=":,;@.") for s in specs) + "&display=swap"
    css = fetch(url).decode("utf-8")
    blocks = re.findall(r"/\* (\w[\w-]*) \*/\s*@font-face \{(.*?)\}", css, re.S)
    rules, n = [], 0
    for subset, body in blocks:
        if subset not in KEEP_SUBSETS:
            continue
        fam = re.search(r"font-family: '([^']+)'", body).group(1)
        style = re.search(r"font-style: (\w+)", body).group(1)
        weight = re.search(r"font-weight: ([\d ]+)", body).group(1).strip().replace(" ", "-")
        src = re.search(r"url\((https://[^)]+\.woff2)\)", body).group(1)
        extra = re.search(r"font-stretch: [^;]+;", body)
        fname = f"{fam.replace(' ', '')}-{weight}-{style}-{subset}.woff2"
        path = os.path.join(OUT, fname)
        if not os.path.exists(path):
            open(path, "wb").write(fetch(src))
            n += 1
        urange = re.search(r"unicode-range: ([^;]+);", body).group(1)
        rules.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;%sfont-display:swap;src:url('%s') format('woff2');unicode-range:%s}"
            % (fam, style, weight.replace("-", " "), (extra.group(0) if extra else ""), fname, urange))
    write_css("/* generated by tools/fonts.py from: " + " | ".join(specs) + " */", rules, fallback_rules())
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".woff2"))
    print(f"{len(rules)} @font-face rules, {n} new files, {total/1024:.0f} KB of woff2 in fonts/")


def metrics_only():
    if not os.path.exists(CSS):
        sys.exit("fonts.py --metrics: fonts/fonts.css does not exist yet; download the fonts first")
    with open(CSS, encoding="utf-8") as f:
        lines = f.read().splitlines()
    header = lines[0] if lines and lines[0].startswith("/*") else "/* generated by tools/fonts.py */"
    rules = [l for l in lines if l.startswith("@font-face") and " Fallback'" not in l]
    fallbacks = fallback_rules()
    if not fallbacks:
        fallbacks = [l for l in lines if l.startswith("@font-face") and " Fallback'" in l]
    write_css(header, rules, fallbacks)
    print(f"{len(rules)} @font-face rules kept, {len(fallbacks)} fallback faces written to fonts/fonts.css")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--metrics":
        metrics_only()
    else:
        main(sys.argv[1:])
