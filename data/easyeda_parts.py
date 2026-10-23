#!/usr/bin/env python3
"""Read an EasyEDA (std) schematic or PCB JSON on stdin; print one line per component:
<package>\t<designator>\t<mount>\t<pads>. Multi-unit parts (U1.1, U1.2, ...) are counted once, by designator.

Each part is one record (a JSON string starting "LIB~" in shape arrays): its attributes are a
backtick key`value` string (package`SOIC-8`...), and its designator is a text label inside
the same record ("...#@$T~P~...~U1.2~..."). Parts in newer exports whose attributes are a JSON
object {"package":..., "pre":...} are read too.
<mount> (v26, PCB JSON only): "th" when every PAD is on layer 11 (all copper) with a drill hole,
"smd" when any PAD is on layer 1 or 2 (top/bottom only) without a hole, else blank; <pads> = PAD count.
"""
import json, re, sys
raw = sys.stdin.read()
seen = {}; anon = []
def add(pkg, ref, mount=""):
    pkg = (pkg or "").strip(); ref = re.sub(r"\.\d+$", "", (ref or "").strip())
    if not pkg: return
    if ref and "?" not in ref: seen.setdefault(ref, (pkg, mount))
    else: anon.append((pkg, mount))
def mount_of(rec):
    pads = [p.split("~") for p in rec.split("#@$") if p.startswith("PAD~")]
    pads = [p for p in pads if len(p) > 9]
    if not pads: return ""
    def hole(p):
        try: return float(p[9] or 0) > 0
        except ValueError: return False
    if any(p[6] in ("1", "2") and not hole(p) for p in pads): return f"smd\t{len(pads)}"
    if all(p[6] == "11" and hole(p) for p in pads): return f"th\t{len(pads)}"
    return f"\t{len(pads)}"
def strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        if isinstance(o.get("package"), str): add(o["package"], o.get("pre") or o.get("Designator"))
        for v in o.values(): yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)
try:
    recs = [s for s in strings(json.loads(raw)) if "package`" in s]
except Exception:
    recs = re.findall(r'"(LIB~[^"]*package`[^"]*)"', raw)
for rec in recs:
    m = re.search(r"package`([^`]*)`", rec)
    kv = re.search(r"[^~]*package`[^~]*", rec).group(0).split("`"); d = dict(zip(kv[0::2], kv[1::2]))
    ref = d.get("pre") or d.get("Designator")
    if not ref or "?" in ref:                                        # label text inside the record
        t = re.search(r"T~P~(?:[^~]*~){9}([A-Za-z]{1,4}\d+(?:\.\d+)?)~", rec) or \
            re.search(r"~([A-Za-z]{1,4}\d+\.\d+)~", rec) or re.search(r"T~P~[^#]*?~([A-Za-z]{1,4}\d+)~", rec)
        ref = t.group(1) if t else ""
    add(m.group(1) if m else "", ref, mount_of(rec))
for ref, (pkg, mt) in seen.items(): print(f"{pkg}\t{ref}\t{mt}")
for pkg, mt in anon: print(f"{pkg}\t\t{mt}")
