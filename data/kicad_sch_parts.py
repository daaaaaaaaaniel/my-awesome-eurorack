#!/usr/bin/env python3
"""KiCad 6+ schematic (.kicad_sch) on stdin -> one line per placed symbol:
<footprint><TAB><reference>   (footprint "" when the symbol has none assigned)

Only placed symbols (top-level "(symbol (lib_id ...") count; library definitions inside
lib_symbols are skipped. Power symbols, flags and references starting with '#' are skipped.
Multi-unit parts (U1A/U1B share reference U1) are printed once per reference."""
import re, sys
t = sys.stdin.read()
ls = t.find("(lib_symbols")
if ls >= 0:                                   # cut out the library block by paren matching
    d = 0
    for i in range(ls, len(t)):
        if t[i] == "(": d += 1
        elif t[i] == ")":
            d -= 1
            if d == 0: t = t[:ls] + t[i + 1:]; break
seen = set()
for m in re.finditer(r'\(symbol\s+\(lib_id\s+"([^"]*)"', t):
    body = t[m.start(): m.start() + 6000]
    ref = re.search(r'\(property\s+"Reference"\s+"([^"]*)"', body)
    fp = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', body)
    ref = ref.group(1) if ref else ""
    if not ref or ref.startswith("#") or m.group(1).startswith("power:"): continue
    if ref in seen: continue
    seen.add(ref); print(f"{fp.group(1) if fp else ''}\t{ref}")
