#!/usr/bin/env python3
"""Read a BOM (CSV, TSV or Markdown table) on stdin; print one line per BOM line:
<qty>\t<designators>\t<whole line text, tabs flattened>.

qty is the Quantity/Qty column when present, else the number of designators, else 1 -
so the detector counts PARTS, not BOM lines. Lines without a header match are passed
through with qty 1 (the old behaviour), so nothing is silently dropped.
"""
import csv, io, re, sys
raw = sys.stdin.read().lstrip("\ufeff")   # UTF-8 BOM would hide the header
lines = [l for l in raw.splitlines() if l.strip()]
if not lines:
    sys.exit()
if lines[0].lstrip().startswith("|"):                       # markdown table
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines
            if not re.fullmatch(r"[\s|:-]+", l)]
else:
    delim = "\t" if lines[0].count("\t") > lines[0].count(",") else ("," if "," in lines[0] else ";")
    rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
hdr, qi, di = None, None, None
for i, r in enumerate(rows[:10]):
    low = [c.strip().lower() for c in r]
    q = [j for j, c in enumerate(low) if c in ("qty", "quantity", "qnty", "count", "amount", "anzahl")]
    d = [j for j, c in enumerate(low) if c in ("designator", "designators", "reference", "references", "ref", "refs", "reference(s)", "part", "parts")]
    if q or d:
        hdr, qi, di = i, (q[0] if q else None), (d[0] if d else None)
        break
for i, r in enumerate(rows):
    if hdr is not None and i <= hdr:
        continue
    text = " ".join(c.replace("\t", " ") for c in r)
    refs = r[di] if di is not None and di < len(r) else ""
    n = None
    if qi is not None and qi < len(r):
        m = re.match(r"\s*(\d+)", r[qi])
        n = int(m.group(1)) if m else None
    if n is None and refs:
        n = len([x for x in re.split(r"[,\s;]+", refs) if x])
    print(f"{n or 1}\t{refs}\t{text}")
