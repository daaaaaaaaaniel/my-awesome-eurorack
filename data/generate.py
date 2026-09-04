#!/usr/bin/env python3
"""Regenerate eurorack-open-source.csv and enrichment-audit.md from data/modules.tsv.

The curated prefix is taken verbatim from the baseline commit, so the original
rows cannot be altered by this script: append-only is enforced mechanically.
"""
import csv, io, subprocess, sys, os

REPO = "/home/user/my-awesome-eurorack"
BASELINE = "6ce3817:eurorack-open-source.csv"   # the hand-curated original
COLS = ["creator","module_name","type","license","schematic","layout","components","link","notes"]

os.chdir(REPO)
frozen = subprocess.run(["git","show",BASELINE],capture_output=True,text=True,check=True).stdout
n_frozen = len(list(csv.reader(io.StringIO(frozen))))

with open("data/modules.tsv") as f:
    mods = list(csv.DictReader(f, delimiter="\t"))

# --- CSV: frozen bytes verbatim, then generated rows ---
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\n")
for m in mods:
    w.writerow([m[c] for c in COLS])
if not frozen.endswith("\n"): frozen += "\n"
open("eurorack-open-source.csv","w").write(frozen + buf.getvalue())

# --- audit table, same source ---
def cell(s): return (s or "").replace("|","\\|")
lines = [
 "# Enrichment audit","",
 "Generated from `data/modules.tsv` — the same source as the CSV rows, so the two cannot disagree.",
 "Row numbers continue the CSV's own numbering. Every non-blank cell traces to a file path or a quoted line.","",
 "`components` confidence: **Stated** (README/BOM says so) · **Strong** (unambiguous footprints) · **Weak** · **Deferred** (needs Pass B part lookup).","",
 "| # | Module | Repo @ commit (date) | Type — basis | Layout / schematic | License — basis | Components — call · basis · confidence | Blanks & why | Follow-up |",
 "|---|---|---|---|---|---|---|---|---|",
]
for i,m in enumerate(mods, start=n_frozen+1):
    blanks=[]
    if not m["license"]:    blanks.append(f'`License` — {m["license_basis"] or "not stated"}')
    if not m["components"]: blanks.append(f'`components` — {m["comp_conf"]}')
    if not m["layout"]:     blanks.append("`layout` — no EDA source identified")
    if not m["notes"]:      pass
    fu = m["followup"] or ""
    if m["bom"] != "y": fu = ("**no BOM** — blocks a parts order. " + fu).strip()
    lines.append("| {} | {} · {} | `{}` @ `{}` ({}) | {} | `{}` / sch={} | {} | **{}** · {} · **{}** | {} | {} |".format(
        i, cell(m["creator"]), cell(m["module_name"]), m["repo"], m["sha"], m["date"],
        cell(m["type_basis"]), cell(m["layout"] or "—"), m["schematic"] or "—",
        cell(m["license_basis"] or "—"), cell(m["components"] or "blank"), cell(m["comp_basis"]), m["comp_conf"],
        cell("; ".join(blanks) if blanks else "none"), cell(fu)))
open("enrichment-audit.md","w").write("\n".join(lines)+"\n")
print(f"frozen logical rows: {n_frozen}; generated: {len(mods)}")
