#!/usr/bin/env python3
"""Site icons for pinkal.art: an italic Fraunces "P" in ink #141210 on paper #f5f0e8.

Writes icons/favicon.svg (the glyph outline traced from the self-hosted woff2 with fontTools),
icons/icon-192.png, icons/icon-512.png and icons/apple-touch-icon.png (180 px), all rendered
from that SVG with Playwright's Chromium at 1024 px and downsampled with Pillow.

Usage: python tools/icons.py [--out DIR]
Needs fonttools and brotli (pip install fonttools brotli) besides Pillow and Playwright; the icons
are generated once and committed, so a normal build never runs this.
"""
import argparse
import io
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "Fraunces-300-700-italic-latin.woff2")
PAPER, INK = "#f5f0e8", "#141210"
BOX = 64          # viewBox size
GLYPH_H = 40      # glyph height inside the box (62 %)
LOCATION = {"wght": 500, "opsz": 144}


def glyph_path():
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen

    font = TTFont(FONT)
    if "fvar" in font:
        axes = {a.axisTag: a for a in font["fvar"].axes}
        loc = {k: min(max(v, axes[k].minValue), axes[k].maxValue) for k, v in LOCATION.items() if k in axes}
        font = instancer.instantiateVariableFont(font, loc)
    gs = font.getGlyphSet()
    name = font.getBestCmap()[ord("P")]
    bp = BoundsPen(gs)
    gs[name].draw(bp)
    x0, y0, x1, y1 = bp.bounds
    s = GLYPH_H / (y1 - y0)
    tx = BOX / 2 - s * (x0 + x1) / 2
    ty = BOX / 2 + s * (y0 + y1) / 2
    sp = SVGPathPen(gs, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip("."))
    gs[name].draw(TransformPen(sp, (s, 0, 0, -s, tx, ty)))
    return sp.getCommands()


def svg(path_d):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">'
            '<rect width="%d" height="%d" fill="%s"/><path fill="%s" d="%s"/></svg>'
            % (BOX, BOX, BOX, BOX, PAPER, INK, path_d))


def render_png(svg_text, size):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
        pg.set_content('<!doctype html><html><body style="margin:0;background:%s">%s</body></html>'
                       % (PAPER, svg_text.replace("<svg ", '<svg width="%d" height="%d" ' % (size, size))))
        png = pg.screenshot(type="png", clip={"x": 0, "y": 0, "width": size, "height": size})
        b.close()
    return Image.open(io.BytesIO(png)).convert("RGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "icons"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    text = svg(glyph_path())
    with open(os.path.join(a.out, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(text)
    big = render_png(text, 1024)
    sizes = {"icon-512.png": 512, "icon-192.png": 192, "apple-touch-icon.png": 180}
    for name, px in sizes.items():
        big.resize((px, px), Image.Resampling.LANCZOS).save(os.path.join(a.out, name), "PNG", optimize=True)
    out = {n: os.path.getsize(os.path.join(a.out, n)) for n in ["favicon.svg"] + list(sizes)}
    print("icons.py: " + ", ".join("%s %d B" % kv for kv in out.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
