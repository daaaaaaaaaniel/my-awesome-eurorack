#!/usr/bin/env python3
"""HTML BOM (a KiCad/Eagle BOM exported as an HTML table) on stdin -> TSV on stdout, one row
per <tr>, for bom_parts.py - the same role xl2tsv.py plays for spreadsheets. Only the first
table with a Ref/Reference/Designator/Part header is used. An iBOM builds its tables in
JavaScript and has no <tr> rows, so it prints nothing and the caller moves on."""
import html, re, sys
t = sys.stdin.read()
for tb in re.findall(r"<table[^>]*>(.*?)</table>", t, re.S | re.I) or [t]:
    rows = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S | re.I):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)]
        if any(cells): rows.append("\t".join(c.replace("\t", " ") for c in cells))
    if rows and re.search(r"(^|\t)(ref|reference|designator|parts?|qty|quantity)(\t|$)", rows[0], re.I):
        print("\n".join(rows)); break
