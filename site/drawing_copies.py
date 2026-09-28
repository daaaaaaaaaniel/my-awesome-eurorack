#!/usr/bin/env python3
"""Readable copies of hairline panel drawings, for thumbnails only (d, 2026-09-28 05:30).

    pip3 install --user cairosvg lxml        # once
    python3 site/drawing_copies.py           # fetches the drawings, writes site/drawings/
    python3 site/drawing_copies.py --sheet /tmp/sheet.png   # ...and a before/after image of each copy

Laser-cutter panel files draw with hairline strokes (~0.01 mm): "cut here", not "show this". Shrunk to
the 400x360 thumbnail they come out a few hundredths of a pixel wide and all but vanish. For every panel
drawing the site shows as a thumbnail (modules without photos, see build.py fallback_thumb), this
fetches the SVG, works out how wide each stroke will be on screen, and when the thinnest one is under
MIN_BEFORE px it writes a copy with every thinner stroke raised to TARGET px on screen. Nothing else in
the drawing changes. Zero-width strokes (invisible on purpose) are left alone, and a copy is kept only when
it visibly helps (GAIN / MOSTLY_BLANK), so filled artwork with incidental hairlines keeps its original.
Copies are named <slug>-<content hash>.svg, so a changed copy gets a new URL and wsrv's cache can't serve
a stale thumbnail.

site/drawings/index.tsv maps each original to its copy. build.py copies site/drawings/*.svg into
docs/drawings/ and points the thumbnail (only) at the copy on GitHub Pages; links still open the
original. Re-run when a drawing changes upstream; an unchanged drawing gives a byte-identical copy.
Scale is measured the way wsrv shows it: content trimmed like trim=10, fitted into 400x360.
"""
import hashlib, io, math, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build                                    # module data and the drawing picker, same as the site
import cairosvg
from lxml import etree
from PIL import Image, ImageChops

OUT = os.path.join(build.ROOT, "site", "drawings")
BOX_W, BOX_H = 400, 360          # thumbnail box on the module pages (thumb_src)
MIN_BEFORE = 0.5                 # copy a drawing when its thinnest stroke would show thinner than this (px)
TARGET = 1.0                     # ...and raise every thinner stroke to this many screen px (2 device px on Retina)
GAIN = 1.25                      # keep a copy only if it shows at least 25% more of the drawing...
MOSTLY_BLANK = 0.005             # ...or the original shows next to nothing (under 0.5% of the thumbnail)
BG = (0xD6, 0xD2, 0xC8)          # the grey the thumbnails sit on (build.py, d 04:55)
UNIT = {"": 1, "px": 1, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96, "pt": 96 / 72, "pc": 16}
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}

def raw_url(blob):
    return re.sub(r"^https://github\.com/([^/]+)/([^/]+)/blob/", r"https://raw.githubusercontent.com/\1/\2/", blob)

def length(v):
    m = re.fullmatch(r"\s*([-+]?[0-9]*\.?[0-9]+(?:e[-+]?\d+)?)\s*([a-z]*)\s*", v or "", re.I)
    return float(m.group(1)) * UNIT[m.group(2).lower()] if m and m.group(2).lower() in UNIT else None

def render(svg_bytes, width):
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg_bytes, output_width=width, unsafe=False))).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,)); bg.alpha_composite(im)
    return bg.convert("RGB")

def trimmed_box(im):
    """Bounding box of pixels that differ from the top-left pixel by more than 10 (wsrv trim=10)."""
    d = ImageChops.difference(im, Image.new("RGB", im.size, im.getpixel((0, 0)))).split()
    return ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2]).point(lambda v: 255 if v > 10 else 0).getbbox()

def ink(im):
    """Share of pixels visibly different from the grey background: how much of the drawing shows."""
    d = ImageChops.difference(im, Image.new("RGB", im.size, BG)).split()
    m = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2]).point(lambda v: 255 if v > 40 else 0)
    return m.histogram()[255] / (im.width * im.height)

def thumb(svg_bytes):
    """The drawing as the page shows it at 2x: trimmed, fitted into 400x360, on grey."""
    big = render(svg_bytes, 1600)
    bb = trimmed_box(big) or (0, 0, big.width, big.height)
    im = big.crop(bb); im.thumbnail((BOX_W * 2, BOX_H * 2), Image.LANCZOS)
    return im

def css_rules(root):
    """Simple rules from <style> blocks: '.a,.b{stroke-width:.1}' -> {'.a': {...}, '.b': {...}}."""
    rules = {}
    for st in root.iter("{http://www.w3.org/2000/svg}style"):
        for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", st.text or ""):
            decl = dict((k.strip(), v.strip()) for k, v in (d.split(":", 1) for d in body.split(";") if ":" in d))
            for s in sel.split(","):
                rules.setdefault(s.strip(), {}).update(decl)
    return rules

def style_of(el):
    return dict((k.strip(), v.strip()) for k, v in (d.split(":", 1) for d in (el.get("style") or "").split(";") if ":" in d))

def own_props(el, rules):
    """stroke / stroke-width set on this element: presentation attribute < CSS class/tag rule < style attribute."""
    tag = etree.QName(el).localname
    p = {k: el.get(k) for k in ("stroke", "stroke-width") if el.get(k) is not None}
    for sel in [tag] + ["." + c for c in (el.get("class") or "").split()] + (["#" + el.get("id")] if el.get("id") else []):
        p.update({k: v for k, v in rules.get(sel, {}).items() if k in ("stroke", "stroke-width")})
    p.update({k: v for k, v in style_of(el).items() if k in ("stroke", "stroke-width")})
    return p

def linear_scale(transform):
    """sqrt(|det|) of the linear part of an SVG transform list."""
    a, b, c, d = 1.0, 0.0, 0.0, 1.0
    for name, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", transform or ""):
        v = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:e[-+]?\d+)?", args)]
        if name == "matrix" and len(v) >= 4: m = v[:4]
        elif name == "scale" and v: m = [v[0], 0, 0, v[1] if len(v) > 1 else v[0]]
        elif name == "rotate" and v: r = math.radians(v[0]); m = [math.cos(r), math.sin(r), -math.sin(r), math.cos(r)]
        elif name == "skewX" and v: m = [1, 0, math.tan(math.radians(v[0])), 1]
        elif name == "skewY" and v: m = [1, math.tan(math.radians(v[0])), 0, 1]
        else: continue
        a, b, c, d = a * m[0] + c * m[1], b * m[0] + d * m[1], a * m[2] + c * m[3], b * m[2] + d * m[3]
    return math.sqrt(abs(a * d - b * c)) or 1.0

def thicken(svg_bytes):
    """-> (new bytes or None, thinnest stroke before in screen px, strokes raised)."""
    parser = etree.XMLParser(resolve_entities=True, huge_tree=True, remove_blank_text=False, no_network=True)
    root = etree.fromstring(svg_bytes, parser)
    vb = [float(x) for x in re.split(r"[\s,]+", (root.get("viewBox") or "").strip()) if x] if root.get("viewBox") else None
    doc_w = vb[2] if vb and len(vb) == 4 else (length(root.get("width")) or 0)
    if not doc_w:
        return None, None, 0
    big = render(svg_bytes, 1600)
    bb = trimmed_box(big)
    if not bb:
        return None, None, 0
    unit_px = 1600 / doc_w                                   # rendered px per user unit
    cw, ch = (bb[2] - bb[0]) / unit_px, (bb[3] - bb[1]) / unit_px
    screen = min(BOX_W / cw, BOX_H / ch)                     # screen px per user unit in the thumbnail
    rules, thinnest, raised = css_rules(root), None, 0
    def walk(el, scale, stroke, width):
        nonlocal thinnest, raised
        if not isinstance(el.tag, str):
            return
        tag = etree.QName(el).localname
        if tag in ("defs", "metadata", "namedview", "style", "title", "desc", "clipPath", "mask", "symbol", "marker", "pattern"):
            return
        scale *= linear_scale(el.get("transform"))
        p = own_props(el, rules)
        stroke = p.get("stroke", stroke)
        w = length(p["stroke-width"]) if "stroke-width" in p else width
        width = w if w is not None else width
        # a zero width is an invisible outline on purpose; never draw it
        if tag in SHAPES and stroke not in (None, "none", "transparent") and width:
            px = width * scale * screen
            thinnest = px if thinnest is None else min(thinnest, px)
            if px < TARGET:
                st = style_of(el); st["stroke-width"] = f"{TARGET / (scale * screen):.5g}"
                el.set("style", ";".join(f"{k}:{v}" for k, v in st.items())); raised += 1
        for c in el:
            walk(c, scale, stroke, width)
    walk(root, 1.0, None, 1.0)                               # SVG defaults: no stroke, width 1
    if thinnest is None or thinnest >= MIN_BEFORE:
        return None, thinnest, 0
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8"), thinnest, raised

def main():
    os.makedirs(OUT, exist_ok=True)
    rows = build.load()
    drawings = [(r["slug"], build.fallback_thumb(r)) for r in rows if not (r.get("photos") or "").split() and build.fallback_thumb(r)]
    index, keep, pairs = [], set(), []
    sheet = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    for slug, blob in sorted(drawings):
        try:
            src = urllib.request.urlopen(raw_url(blob), timeout=30).read()
        except Exception as ex:
            print(f"{slug}: fetch failed ({ex}); skipped"); continue
        try:
            new, thinnest, raised = thicken(src)
        except Exception as ex:
            print(f"{slug}: could not process ({type(ex).__name__}: {ex}); skipped"); continue
        if new is None:
            print(f"{slug}: thinnest stroke {thinnest if thinnest is None else round(thinnest, 2)} px - no copy needed"); continue
        t_before, t_after = thumb(src), thumb(new)
        before, after = ink(t_before), ink(t_after)
        if before >= MOSTLY_BLANK and after < before * GAIN:
            print(f"{slug}: thinnest {thinnest:.3f} px, but raising {raised} strokes only moves visible ink {before:.1%} -> {after:.1%}; original kept"); continue
        name = f"{slug}-{hashlib.sha1(new).hexdigest()[:8]}.svg"
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(new)
        keep.add(name)
        pairs.append((slug, t_before, t_after))
        index.append((slug, blob, name, f"{thinnest:.3f}", str(raised), f"{before:.4f}", f"{after:.4f}"))
        print(f"{slug}: thinnest {thinnest:.3f} px, {raised} strokes raised, visible ink {before:.1%} -> {after:.1%}")
    for f in os.listdir(OUT):                               # copies of drawings that changed or no longer need one
        if f.endswith(".svg") and f not in keep:
            os.remove(os.path.join(OUT, f))
    with open(os.path.join(OUT, "index.tsv"), "w", encoding="utf-8") as f:
        f.write("# written by site/drawing_copies.py - thumbnails of these drawings use the copy; links open the original\n")
        f.write("slug\tsource\tcopy\tthinnest_px_before\tstrokes_raised\tink_before\tink_after\n")
        for row in index:
            f.write("\t".join(row) + "\n")
    print(f"{len(index)} copies of {len(drawings)} panel drawings in {os.path.relpath(OUT, build.ROOT)}/")
    if sheet and pairs:
        from PIL import ImageDraw
        cw, ch, cols = 2 * 210 + 20, 390, 4                 # each cell: before | after at 1x, slug on top
        img = Image.new("RGB", (cols * cw, ((len(pairs) + cols - 1) // cols) * ch), (255, 255, 255))
        dr = ImageDraw.Draw(img)
        for i, (slug, a, b) in enumerate(pairs):
            x, y = (i % cols) * cw + 10, (i // cols) * ch + 6
            dr.text((x, y), slug[:48], fill=(0, 0, 0))
            for k, t in enumerate((a, b)):
                t = t.copy(); t.thumbnail((200, 350), Image.LANCZOS)
                img.paste(t, (x + k * 210, y + 18))
        img.save(sheet); print("before | after sheet:", sheet)

if __name__ == "__main__":
    main()
