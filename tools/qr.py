#!/usr/bin/env python3
"""QR codes for the exhibition mode (/show/) of pinkal.art.

Writes images/qr/NN.svg for every painting whose source long edge is at least 2400 px
("eligible_lead" in data/images.json), each pointing at https://pinkal.art/works/NN/.
Error level M, 4-module quiet zone, dark modules #141210, light modules transparent, scalable
(viewBox, no fixed size). Stale codes of works that are no longer eligible are removed.

Usage
  python tools/qr.py            default output images/qr/
  python tools/qr.py --out DIR
  python tools/qr.py --all      one code per painting regardless of source size

Reads data/works.json (ids; 09 and 99 excluded), data/images.json (eligibility) and data/site.json (domain).
"""
import argparse
import json
import os
import sys

import segno

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DARK = "#141210"
DEFAULT_DOMAIN = "https://pinkal.art"


def load_json(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def painting_ids(works, images):
    if works:
        return [str(w["id"]) for w in works
                if w.get("kind", "painting") == "painting" and not w.get("duplicate_of")]
    return [i for i in images if i != "99"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "images", "qr"))
    ap.add_argument("--all", action="store_true", help="ignore the 2400 px eligibility rule")
    a = ap.parse_args()

    images = load_json("images.json", None)
    if images is None:
        sys.exit("qr.py: data/images.json is missing; run python tools/images.py first")
    works = load_json("works.json", None)
    site = load_json("site.json", {})
    domain = (site.get("domain") or DEFAULT_DOMAIN).rstrip("/")

    ids = [i for i in painting_ids(works, images) if i in images]
    eligible = [i for i in ids if a.all or images[i].get("eligible_lead")]
    os.makedirs(a.out, exist_ok=True)
    sizes = {}
    for wid in eligible:
        url = "%s/works/%s/" % (domain, wid)
        qr = segno.make_qr(url, error="m", boost_error=False)
        path = os.path.join(a.out, wid + ".svg")
        qr.save(path, kind="svg", border=4, dark=DARK, light=None, omitsize=True, xmldecl=False,
                svgclass=None, lineclass=None, nl=False)
        sizes[wid] = (os.path.getsize(path), qr.designator)
    removed = 0
    for name in os.listdir(a.out):
        stem, ext = os.path.splitext(name)
        if ext == ".svg" and stem not in sizes and stem.isdigit():
            os.remove(os.path.join(a.out, name))
            removed += 1
    if sizes:
        big = max(sizes.values())
        print("qr.py: %d codes in %s (%s), %d stale removed, largest %d B (version %s), total %d B"
              % (len(sizes), os.path.relpath(a.out, ROOT), ", ".join(sizes), removed, big[0], big[1],
                 sum(s for s, _ in sizes.values())))
    else:
        print("qr.py: no eligible works (source long edge >= 2400 px); nothing written")


if __name__ == "__main__":
    main()
