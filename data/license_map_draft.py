#!/usr/bin/env python3
"""Draft data/license-map.tsv from the distinct `license` strings in data/modules.tsv.

    python3 data/license_map_draft.py            # prints the table, writes nothing
    python3 data/license_map_draft.py --write    # writes data/license-map.tsv (OVERWRITES)

One row per *grant*: a raw string like
    CC BY-SA 3.0 (hardware) / MIT (STM32 code) / GPL v3 (AVR code)
becomes three rows (seq 1..3). Rules (data/licenses.md):
  - split on " / "; a trailing "(...)" is the scope when it names one, otherwise a qualifier
  - family is version-free; version only when the string states it (never inferred)
  - terms is a property of the family, never of the module
  - blank license -> family none-found (not "no licence": nothing was found in the files checked)
Every row is written with status=draft. Re-running overwrites reviewed rows, so once rows are
marked ok, edit the TSV by hand instead.
"""
import csv, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "modules.tsv")
OUT = os.path.join(ROOT, "data", "license-map.tsv")

# family -> terms. Terms vocabulary: permissive, copyleft, non-commercial, public-domain,
# custom, none-named, none-found, not-open, unclear.
FAMILIES = [  # (regex on the licence token, family, terms)
    (r"^MIT$",                        "MIT",          "permissive"),
    (r"^Apache ?2(\.0)?$",            "Apache",       "permissive"),
    (r"^BSD( 3-Clause)?$",            "BSD",          "permissive"),
    (r"^CC BY( \d\.\d)?$",            "CC-BY",        "permissive"),
    (r"^CC BY-SA( \d\.\d)?$",         "CC-BY-SA",     "copyleft"),
    (r"^CC BY-NC-SA( \d\.\d)?$",      "CC-BY-NC-SA",  "non-commercial"),
    (r"^CC BY-NC( \d\.\d)?$",         "CC-BY-NC",     "non-commercial"),
    (r"^CC0(-\d\.\d)?$",              "CC0",          "public-domain"),
    (r"^GPL( v\d)?$",                 "GPL",          "copyleft"),
    (r"^CERN-OHL-W(-\d\.\d| v\d)?$",  "CERN-OHL-W",   "copyleft"),
    (r"^CERN-OHL-S(-\d\.\d| v\d)?$",  "CERN-OHL-S",   "copyleft"),
    (r"^CERN-OHL-P(-\d\.\d| v\d)?$",  "CERN-OHL-P",   "permissive"),
    (r"^open source, no licen[cs]e named$", "none-named", "none-named"),
    (r"^custom$",                     "custom",       "custom"),
    (r"^(proprietary|closed source|not open source|none granted)$", "not-open", "not-open"),
    (r"^Creative Commons or MIT$",    "unclear",      "unclear"),
]
VERSION = re.compile(r"(?:^|[ -])(?:v)?(\d(?:\.\d)?)$")

HW = re.compile(r"\b(hardware|pcb|pcbs|board|board files|bom|schematic|dsp mcu board)\b", re.I)
SW = re.compile(r"\b(software|firmware|code)\b", re.I)
PANEL = re.compile(r"\bpanel\b", re.I)

def parse_scope(q):
    """qualifier text inside (...) -> (scope, is_scope). Not-a-scope qualifiers go to the note."""
    hw, sw, pn = bool(HW.search(q)), bool(SW.search(q)), bool(PANEL.search(q))
    if hw and sw: return "hardware+software", True
    if hw and pn: return "hardware", True          # "PCB/panel", "PCBs, panel"
    if hw: return "hardware", True
    if sw: return "software", True
    if pn: return "panel", True
    return "unstated", False

def parse_grant(part):
    part = part.strip()
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", part)
    token, qual = (m.group(1).strip(), m.group(2).strip()) if m else (part, "")
    scope, is_scope = parse_scope(qual) if qual else ("unstated", False)
    note = "" if is_scope or not qual else f"qualifier: {qual}"
    if is_scope and not re.fullmatch(r"(hardware|software|firmware|code|panel|PCB/panel|PCBs, panel|BOM, schematic|STM32 code|AVR code)", qual, re.I):
        note = f"scope text: {qual}"
    fam = terms = "unclear"
    for rx, f, t in FAMILIES:
        if re.match(rx, token, re.I):
            fam, terms = f, t; break
    ver = ""
    vm = VERSION.search(token)
    if vm and fam not in ("none-named", "custom", "not-open", "unclear"):
        ver = vm.group(1)
    return dict(family=fam, version=ver, scope_raw=qual if is_scope else "", scope=scope, terms=terms, note=note, token=token)

def parse(raw):
    if not raw.strip():
        return [dict(family="none-found", version="", scope_raw="", scope="unstated", terms="none-found",
                     note="blank cell: no LICENSE file or README statement found in the files checked", token="")]
    return [parse_grant(p) for p in raw.split(" / ")]

def main():
    with open(SRC, newline="", encoding="utf-8") as f:
        counts = Counter((r["license"] or "").strip() for r in csv.DictReader(f, delimiter="\t"))
    rows = []
    for raw, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        for i, g in enumerate(parse(raw), 1):
            rows.append([raw, n, i, g["family"], g["version"], g["scope_raw"], g["scope"], g["terms"],
                         "UNMAPPED" if g["family"] == "unclear" and g["token"] != "Creative Commons or MIT" else "draft", g["note"]])
    hdr = ["license", "rows", "seq", "family", "version", "scope_raw", "scope", "terms", "status", "note"]
    if "--write" in sys.argv:
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n"); w.writerow(hdr); w.writerows(rows)
        print(f"wrote {len(rows)} grant rows for {len(counts)} distinct strings -> {os.path.relpath(OUT, ROOT)}")
    else:
        print("\t".join(hdr))
        for r in rows: print("\t".join(str(x) for x in r))

if __name__ == "__main__":
    main()
