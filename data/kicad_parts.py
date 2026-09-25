#!/usr/bin/env python3
"""Read a .kicad_pcb on stdin; print one line per footprint: <footprint>\t<reference>.

Handles KiCad v5 `(module …)` and v6+ `(footprint "…")`, with the reference in
`(fp_text reference "Q1" …)` (v5/v6) or `(property "Reference" "Q1" …)` (v7+).
The reference is what tells a TO-92 transistor (Q…) from a TO-92 regulator (U…).
"""
import re, sys
txt = sys.stdin.read()
starts = [m for m in re.finditer(r'\((?:footprint|module) "?([^" )]+)', txt)]
for i, m in enumerate(starts):
    body = txt[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(txt)]
    r = re.search(r'\(fp_text reference "?([^" )]+)|\(property "Reference" "([^"]*)"', body)
    ref = (r.group(1) or r.group(2)) if r else ""
    print(f"{m.group(1)}\t{ref}")
