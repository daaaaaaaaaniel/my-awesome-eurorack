#!/usr/bin/env python3
"""Regenerate eurorack-open-source.csv and enrichment-audit.md from data/modules.tsv.

The curated prefix is taken verbatim from the baseline commit, so the original
rows cannot be altered by this script: append-only is enforced mechanically.
"""
import csv, io, re, subprocess, sys, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = "6ce3817:eurorack-open-source.csv"   # the hand-curated original
COLS = ["creator","module_name","type","license","schematic","layout","components","link","notes"]

DETECTOR_VERSION = "12"
# components may only be non-blank at these confidences (CLAUDE.md)
OK_CONF = {"Stated", "Strong"}
# Type of Module must state a function; everything in this table is a eurorack module
GENERIC_TYPES = {"eurorack module", "module", "synth module", "synthesizer module",
                 "dev platform", "platform", "eurorack", "diy module"}


def validate(mods):
    """Fail loudly rather than shipping a row that breaks a hard rule."""
    # Pinned SHAs are evidence, so they must come from the harvest, never be typed.
    with open("data/inventory.tsv") as f:
        head_sha = {r["repo"]: r["head_sha"] for r in csv.DictReader(f, delimiter="\t")}
    errs = []
    for m in mods:
        i = m["id"]
        if not m["link"].startswith(f"https://github.com/{m['repo']}"):
            errs.append(f"{i}: link {m['link']!r} does not point into {m['repo']}")
        elif m["module_dir"] != "." and "/tree/" not in m["link"] and "/blob/" not in m["link"]:
            errs.append(f"{i}: link is the repo root but the module is in {m['module_dir']!r}")
        owner = m["repo"].split("/")[0]
        if "GitHub owner" in m["creator_basis"] and m["creator"].split(" + ")[-1] != owner:
            errs.append(f"{i}: creator falls back to the GitHub owner but reads "
                        f"{m['creator'].split(' + ')[-1]!r}, not {owner!r} - never prettify handles")
        if m["sha"] != head_sha.get(m["repo"]):
            errs.append(f"{i}: sha {m['sha']!r} != inventory head_sha "
                        f"{head_sha.get(m['repo'])!r} for {m['repo']}")
        # schematic?: a deep link to a standalone schematic file (PDF, else image) in the
        # row's repo; "x" only when the schematic is implicit (inside KiCad/Eagle/EasyEDA
        # sources or a zip) and has no path of its own; "n/a" or blank otherwise.
        s = m["schematic"]
        if s not in ("", "x", "n/a") and not s.startswith(f"https://github.com/{m['repo']}/blob/"):
            errs.append(f"{i}: schematic {s!r} is neither x / n/a / blank nor a /blob/ link into {m['repo']}")
        if m["components"] and m["comp_conf"] not in OK_CONF:
            errs.append(f"{i}: components={m['components']!r} at confidence "
                        f"{m['comp_conf']!r} - must be blank below {sorted(OK_CONF)}")
        t = (m["type"] or "").strip().lower()
        if t in GENERIC_TYPES:
            errs.append(f"{i}: Type of Module {m['type']!r} is generic - state a function")
        if m.get("detector_version", "") != DETECTOR_VERSION:
            errs.append(f"{i}: detector_version {m.get('detector_version')!r} != "
                        f"{DETECTOR_VERSION} - stale, re-run components.sh")
        for c in COLS:
            if "\t" in (m[c] or "") or "\n" in (m[c] or ""):
                errs.append(f"{i}: field {c} contains a tab or newline")
    if errs:
        raise SystemExit("generate.py: refusing to write\n  " + "\n  ".join(errs))

os.chdir(REPO)
frozen = subprocess.run(["git","show",BASELINE],capture_output=True,text=True,check=True).stdout
# User-authorised edits to curated rows - the ONLY exceptions to append-only. Each is an
# exact byte substring of the baseline that must occur exactly once, so an edit can never
# drift onto another row. Add entries only on an explicit user ruling, with its date.
CURATED_OVERRIDES = [
    # Crimps: THT -> SMD (user, 2026-09-26). Footprints: 58 SMD + 4 THT passives, no THT IC - SMD by the rule
    # (2 radial electrolytics, 2 DO-41 diodes) in crimps/k2.kicad_pcb.
    (",kicad,THT,https://github.com/kstammits/crimps,", ",kicad,SMD,https://github.com/kstammits/crimps,"),
]
for old_s, new_s in CURATED_OVERRIDES:
    if frozen.count(old_s) != 1:
        raise SystemExit(f"generate.py: curated override {old_s!r} matches {frozen.count(old_s)}x, not 1")
    frozen = frozen.replace(old_s, new_s)
n_frozen = len(list(csv.reader(io.StringIO(frozen))))

with open("data/modules.tsv") as f:
    mods = list(csv.DictReader(f, delimiter="\t"))
validate(mods)

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
    # Per-module review queue for the SMD/THT call (user, 2026-09-26): THT transistors are
    # counted toward the 5-passive limit, and a TO-92/TO-220 part without a Q reference is
    # taken as an IC. Flag every SMD-bearing module where either happened.
    mt = re.search(r"smd=(\d+) tht_passive=\d+ tht_transistor=(\d+) tht_ic=(\d+)", m["comp_basis"])
    if mt and int(mt.group(1)) > 0 and (int(mt.group(2)) > 0 or int(mt.group(3)) > 0):
        fu = (f"**review components**: {mt.group(2)} THT transistor(s) counted toward the "
              f"5-passive limit, {mt.group(3)} THT IC(s) (DIP/SIP/TO- without a Q ref). " + fu).strip()
    if "GitHub owner" in m["creator_basis"]:
        fu = ("creator is the GitHub owner - no brand name found in repo. " + fu).strip()
    # A schematic is the basis for a BOM, so a missing BOM only matters when there is
    # no schematic or EDA source either. "blocks a parts order" was simply untrue.
    has_source = bool(m["schematic"]) or bool(m["layout"])
    if m["bom"] != "y" and not has_source:
        fu = ("**no BOM and no schematic/EDA source** — nothing to derive a parts list from. " + fu).strip()
    lines.append("| {} | {} · {} | `{}` @ `{}` ({}) | {} | `{}` / sch={} | {} | **{}** · {} · **{}** | {} | {} |".format(
        i, cell(m["creator"]), cell(m["module_name"]), m["repo"], m["sha"], m["date"],
        cell(m["type_basis"]), cell(m["layout"] or "—"), m["schematic"] or "—",
        cell(m["license_basis"] or "—"), cell(m["components"] or "blank"), cell(m["comp_basis"]), m["comp_conf"],
        cell("; ".join(blanks) if blanks else "none"), cell(fu)))
open("enrichment-audit.md","w").write("\n".join(lines)+"\n")
print(f"frozen logical rows: {n_frozen}; generated: {len(mods)}")
