#!/usr/bin/env python3
"""Does a gerber set prove "no SMD parts"? (detector v22, d 2026-09-26 16:15/16:23)

  gerber_nosmd.py FILE...   gerber layers, Excellon drill files and/or .zip archives of them
  prints one line: paste_layers=N paste_pads=N on_holes=N smd_pads=N comp_holes=N drill_files=N

Stencil (paste) openings exist only where solder paste is printed. SMD pads get them; a
through-hole pad gets one only in pin-in-paste designs, and then it sits on a drilled hole.
So every paste pad that is not on a hole is an SMD pad. smd_pads=0 with >=1 paste layer and
>=1 component hole (0.6-1.6 mm, i.e. not a via, not a mounting hole) means the board has no
SMD parts. A missing paste layer proves nothing (Eagle's default CAM job never wrote one).
Coordinates are compared in mm with 0.2 mm tolerance; if no paste pad lands on any hole the
pads all count as SMD - a format mismatch can only make the answer "unknown", never "THT".
"""
import io, math, re, sys, zipfile
PASTE = re.compile(r"(\.gtp|\.gbp|\.crm|\.crs|\.tcream|\.bcream|\.stc|\.sts)$|paste", re.I)
DRILL = re.compile(r"\.(drl|xln|exc|drd)$|drill|(^|[-_])n?pth\.(txt|drl)$", re.I)
GERB = re.compile(r"\.(g[tb][lospa]|gm\d*|gko|gbr|ger|pho|art|cmp|sol)$", re.I)

def gerber_pads(t):
    fs = re.search(r"%FS([LTD]?)([AI])X(\d)(\d)Y(\d)(\d)\*%", t)
    zs, xi, xd = (fs.group(1), int(fs.group(3)), int(fs.group(4))) if fs else ("L", 2, 4)
    scale = 25.4 if "%MOIN*%" in t else 1.0
    def val(s):
        neg = s.startswith("-"); s = s.lstrip("+-")
        if zs == "T": s = s.ljust(xi + xd, "0")
        v = int(s) / 10 ** xd
        return (-v if neg else v) * scale
    x = y = 0.0; pads = []; region = None
    for st in t.replace("\n", "").replace("\r", "").split("*"):
        if st.startswith("%"): st = st.lstrip("%")
        if st.startswith("G36"): region = []; continue
        if st.startswith("G37"):
            if region: pads.append((sum(p[0] for p in region) / len(region), sum(p[1] for p in region) / len(region)))
            region = None; continue
        m = re.match(r"^(?:G0?[123])?(?:X([+-]?\d+))?(?:Y([+-]?\d+))?(?:I[+-]?\d+)?(?:J[+-]?\d+)?(D0?[123])?$", st)
        if not m or not (m.group(1) or m.group(2) or m.group(3)): continue
        if m.group(1): x = val(m.group(1))
        if m.group(2): y = val(m.group(2))
        d = m.group(3)
        if region is not None and d: region.append((x, y))
        elif d and d.endswith("3"): pads.append((x, y))
    return pads

def drill_hits(t):
    metric = bool(re.search(r"^(METRIC|M71)", t, re.M))
    fmt = re.search(r"FORMAT=\{-?(\d):(\d)", t)
    zs = re.search(r"^(?:METRIC|INCH)\s*,\s*(LZ|TZ)", t, re.M)
    a, b = (int(fmt.group(1)), int(fmt.group(2))) if fmt else ((3, 3) if metric else (2, 4))
    scale = 1.0 if metric else 25.4
    tools = {}
    for m in re.finditer(r"^T0*(\d+)[^C\n]*C([\d.]+)", t, re.M): tools[m.group(1)] = float(m.group(2)) * scale
    def val(s):
        if "." in s: return float(s) * scale
        neg = s.startswith("-"); s = s.lstrip("+-")
        if zs and zs.group(1) == "LZ": s = s.ljust(a + b, "0")
        v = int(s) / 10 ** b
        return (-v if neg else v) * scale
    hits = []; cur = None; x = y = 0.0; body = t.split("%", 1)[-1] if "%" in t else t
    for line in body.splitlines():
        m = re.match(r"^T0*(\d+)\s*$", line)
        if m: cur = m.group(1); continue
        for part in re.split(r"G85", line):
            mx = re.search(r"X([+-]?[\d.]+)", part); my = re.search(r"Y([+-]?[\d.]+)", part)
            if not (mx or my) or not re.match(r"^(G0[01])?[XY]", part.strip() or "-"): continue
            if mx: x = val(mx.group(1))
            if my: y = val(my.group(1))
            hits.append((x, y, tools.get(cur, 0.0)))
    return hits

pads, holes, n_paste, n_drill = [], [], 0, 0
def take(name, data):
    global n_paste, n_drill
    base = name.rsplit("/", 1)[-1]
    txt = data.decode("latin-1")
    if DRILL.search(base) or (base.lower().endswith(".txt") and re.search(r"^M48", txt, re.M)):
        n_drill += 1; holes.extend(drill_hits(txt))
    elif PASTE.search(base) and "%FS" in txt:
        n_paste += 1; pads.extend(gerber_pads(txt))
for p in sys.argv[1:]:
    data = open(p, "rb").read()
    if p.lower().endswith(".zip"):
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            for n in z.namelist():
                if not n.endswith("/"): take(n, z.read(n))
        except zipfile.BadZipFile:
            pass
    else:
        take(p, data)
comp = [h for h in holes if 0.6 <= h[2] <= 1.6]
on = sum(1 for (px, py) in pads if any(math.hypot(px - hx, py - hy) < 0.2 for hx, hy, _ in holes))
smd = len(pads) - on if on else len(pads)
print(f"paste_layers={n_paste} paste_pads={len(pads)} on_holes={on} smd_pads={smd} comp_holes={len(comp)} drill_files={n_drill}")
