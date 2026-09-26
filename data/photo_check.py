#!/usr/bin/env python3
"""Is an image a photo / render, or a schematic, layout plot, diagram, screenshot or artwork?
(d, 2026-09-26 19:55: schematics and wrong images were showing as module photos.)

check(data: bytes, name: str) -> (keep: bool, reason: str)

Measured on a 256/400 px copy:
  n95    colours (4 bits/channel) needed to cover 95% of the opaque pixels - photos need 100s,
         flat graphics a handful
  white  share of near-white pixels;  transp  share of transparent pixels
  soft / strong  share of pixels on gradual / sharp edges - JPEG line art rings, so a schematic
         or PCB plot saved as JPEG has many soft edges despite few colours
Rules, tuned on 138 images labelled by eye (data/photo-check-labels.tsv):
  transparent >= 50%                                          -> artwork / icon
  PNG/GIF/WEBP with n95 <= 60, or white >= 40% and n95 <= 150 -> flat graphic
  JPEG with n95 <= 30, soft >= 0.06 and strong/soft <= 1.2    -> line art saved as JPEG
  JPEG named panel/faceplate with n95 <= 30                   -> flat panel artwork / render
Files d flags by hand go in data/photo-excludes.tsv (panel_photos.py honours it).
Known misses (kept): colourful flat PNGs with many anti-aliased shades (pinout cards, some 2D
layout plots); art cards and illustrations. Name/folder rules in panel_photos.py catch most.
"""
import io, re
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None

def measure(data):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    t = im.copy(); t.thumbnail((256, 256))
    px = list(t.getdata()); n = len(px)
    transp = sum(1 for p in px if p[3] < 30) / n
    op = [p for p in px if p[3] >= 30] or [(255, 255, 255, 255)]
    white = sum(1 for p in op if min(p[:3]) > 225) / len(op)
    q = {}
    for p in op: k = (p[0] >> 4, p[1] >> 4, p[2] >> 4); q[k] = q.get(k, 0) + 1
    acc = n95 = 0
    for c in sorted(q.values(), reverse=True):
        acc += c; n95 += 1
        if acc >= 0.95 * len(op): break
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    g = bg.convert("L"); g.thumbnail((400, 400)); e = list(g.filter(ImageFilter.FIND_EDGES).getdata()); m = len(e)
    strong = sum(1 for p in e if p > 80) / m; soft = sum(1 for p in e if 15 < p <= 80) / m
    return dict(n95=n95, white=white, transp=transp, soft=soft, strong=strong)

def check(data, name):
    try: f = measure(data)
    except Exception as ex: return True, f"not measured ({str(ex)[:40]})"
    jpg = name.lower().endswith((".jpg", ".jpeg"))
    tag = f"n95={f['n95']} white={f['white']:.2f} soft={f['soft']:.3f} strong={f['strong']:.3f}"
    if f["transp"] >= 0.5: return False, "mostly transparent (artwork/icon) " + tag
    if not jpg and (f["n95"] <= 60 or (f["white"] >= 0.4 and f["n95"] <= 150)): return False, "flat graphic " + tag
    if jpg and f["n95"] <= 30 and re.search(r"panel|face[_ -]?plate|front[_ -]?plate", name.rsplit("/", 1)[-1], re.I):
        return False, "flat panel artwork (JPEG named panel) " + tag
    if jpg and f["n95"] <= 30 and f["soft"] >= 0.06 and f["strong"] / (f["soft"] + 1e-3) <= 1.2: return False, "line art (JPEG) " + tag
    return True, tag
