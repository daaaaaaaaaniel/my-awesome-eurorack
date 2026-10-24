#!/usr/bin/env python3
"""Read a .kicad_pcb on stdin; print one line per footprint: <footprint>\t<reference>\t<smd|tht|none>\t<pads>\t<value>.

Handles KiCad v5 `(module …)` and v6+ `(footprint "…")`, with the reference in
`(fp_text reference "Q1" …)` (v5/v6) or `(property "Reference" "Q1" …)` (v7+).
Mounting (v27) comes from the footprint's own pads, as eagle_parts.py and ibom_parts.py do: any `smd` pad -> smd;
else any `thru_hole` pad -> tht; else (only np_thru_hole / connect pads, or none) -> none. <pads> counts smd and
thru_hole pads. Before v27 only the footprint name was read, and names that matched no package pattern were dropped.
"""
import re, sys
txt = sys.stdin.read()
starts = [m for m in re.finditer(r'\((?:footprint|module) "?([^" )]+)', txt)]
for i, m in enumerate(starts):
    body = txt[m.end(): starts[i + 1].start() if i + 1 < len(starts) else len(txt)]
    r = re.search(r'\(fp_text reference "?([^" )]+)|\(property "Reference" "([^"]*)"', body)
    ref = (r.group(1) or r.group(2)) if r else ""
    v = re.search(r'\(fp_text value "?([^")]*)"?|\(property "Value" "([^"]*)"', body)
    val = ((v.group(1) or v.group(2) or "") if v else "").strip().replace("\t", " ")
    kinds = re.findall(r'\(pad +(?:"[^"]*"|\S+) +(smd|thru_hole|np_thru_hole|connect)\b', body)
    mt = "smd" if "smd" in kinds else ("tht" if "thru_hole" in kinds else "none")
    print(f"{m.group(1)}\t{ref}\t{mt}\t{len([k for k in kinds if k in ('smd', 'thru_hole')])}\t{val}")
