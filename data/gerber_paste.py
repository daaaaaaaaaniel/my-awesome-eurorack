#!/usr/bin/env python3
"""Count SMD pads on the solder-paste layers of a gerber set (Pass B, trial 2026-09-26).

  gerber_paste.py FILE...        files: gerber layers and/or .zip archives of them
  prints: paste_layers=N paste_pads=N copper_layers=N drill_files=N [layers: ...]

A paste layer carries stencil openings, and only SMD pads get them: a paste layer with no
flashes (D03) and no regions (G36) means the board has no SMD pads at all. Paste layers are
found by name/extension: .gtp .gbp .crm .tcream .bcream, *Paste* / *paste*. Missing paste
layers print paste_layers=0 - that is NOT evidence of anything (Eagle's default CAM job
never wrote them).
"""
import io, re, sys, zipfile
PASTE = re.compile(r"(\.gtp|\.gbp|\.crm|\.crs|\.tcream|\.bcream|\.stc|\.sts)$|paste", re.I)
COPPER = re.compile(r"(\.gtl|\.gbl|\.cmp|\.sol|_cu\.gbr|\.top|\.bot)$|copper", re.I)
DRILL = re.compile(r"\.(drl|xln|exc|drd)$|drill", re.I)
def pads(txt):
    # flashes: a D03 op (optionally after coordinates); regions: G36 blocks
    fl = len(re.findall(r"D0?3\*", txt)); rg = len(re.findall(r"G36\*", txt))
    return fl + rg
layers = []
for p in sys.argv[1:]:
    data = open(p, "rb").read()
    items = []
    if p.lower().endswith(".zip"):
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            items = [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
        except zipfile.BadZipFile:
            continue
    else:
        items = [(p, data)]
    for n, b in items:
        base = n.rsplit("/", 1)[-1]
        if PASTE.search(base) and not DRILL.search(base):
            layers.append(("paste", base, pads(b.decode("latin-1"))))
        elif COPPER.search(base): layers.append(("copper", base, pads(b.decode("latin-1"))))
        elif DRILL.search(base): layers.append(("drill", base, len(re.findall(rb"^X-?\d", b, re.M))))
pl = [l for l in layers if l[0] == "paste"]
print(f"paste_layers={len(pl)} paste_pads={sum(l[2] for l in pl)} copper_layers={sum(l[0]=='copper' for l in layers)} "
      f"drill_files={sum(l[0]=='drill' for l in layers)} [paste: " + ", ".join(f"{l[1]}={l[2]}" for l in pl) + "]")
