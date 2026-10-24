#!/usr/bin/env python3
"""Regenerate eurorack-open-source.csv and enrichment-audit.md from data/modules.tsv.

The curated prefix is taken verbatim from the baseline commit, so the original
rows cannot be altered by this script: append-only is enforced mechanically.
"""
import csv, io, re, subprocess, sys, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = "6ce3817:eurorack-open-source.csv"   # the hand-curated original
COLS = ["creator","module_name","type","license","schematic","layout","components","link","notes","prototype","panel","photos","build"]
# 10th column (user, 2026-09-26): "prototype" - X when the repo clearly labels the build a prototype /
# untested, ? when the wording is ambiguous, blank otherwise. The curated rows and the header get the
# column appended to their frozen bytes; the legend row reads "X | ?".
PROTO_LEGEND = "X | ?"
# 11th and 12th columns (d, 2026-09-26 16:52): "Panel" - HP and the panel's source files
# ("12HP · kicad + gerbers", "1U 12HP · kicad", "HP ? · svg"; blank = no panel files) and "photo" -
# space-separated /blob/ links to photos and renders. Filled by data/panel_photos.py for every row,
# the 26 curated rows included (their values: data/curated-panel-photos.tsv), appended like prototype.
EXTRA_HEAD = ["Panel", "photo", "build guide"]   # "build guide": d 2026-09-26 17:11
EXTRA_LEGEND = ["NHP · kicad | eagle | easyeda | gerbers | svg | dxf | ai | pdf | fpd | 3D", "links", "links"]
# bare "NHP": no panel files, HP stated in the module name/folder (0HP d 08:24; name d 09:06)
PANEL_RE = re.compile(r"^\d{1,3}HP$|^((1U )?\d{1,3}HP|HP \?) · (kicad|eagle|easyeda|gerbers|svg|dxf|ai|pdf|fpd|3D)( \+ (kicad|eagle|easyeda|gerbers|svg|dxf|ai|pdf|fpd|3D))*$")

# d's hand-picked photos that are full URLs (data/photo-includes.tsv: id, path, basis) - the only photo links
# allowed outside a row's repo
PHOTO_URLS = {}
if os.path.exists(os.path.join(REPO, "data", "photo-includes.tsv")):
    for _l in open(os.path.join(REPO, "data", "photo-includes.tsv"), encoding="utf-8").read().splitlines()[1:]:
        _f = _l.split("\t")
        if len(_f) >= 2 and re.match(r"https?://", _f[1]): PHOTO_URLS.setdefault(_f[0], set()).add(_f[1])

# Web-sourced rows (retirement step 3, d 2026-10-23): a module whose design lives on a web page, not GitHub.
# repo = the page's host, module_dir = its path, sha = 'sha256:' + 12 hex of the bytes read, date = the day
# fetched - all copied from data/web-sources.tsv, written by data/web_fetch.py. Every URL in schematic /
# photos / build must be a link found on the row's page (data/web-links.tsv) and fetched too.
def _tsv(name):
    path = os.path.join(REPO, "data", name)
    return list(csv.DictReader(open(path, newline="", encoding="utf-8"), delimiter="\t")) if os.path.exists(path) else []
WEB_SRC = {r["url"]: r for r in _tsv("web-sources.tsv")}
WEB_LINKS = {}
for _r in _tsv("web-links.tsv"): WEB_LINKS.setdefault(_r["page"], set()).add(_r["link"])
def is_web(m): return m["sha"].startswith("sha256:")

DETECTOR_VERSION = "26"
# Per-row stamps (d 2026-10-23): detector_version is the version a row was last actually run at, so an
# upgrade rewrites only the rows it re-ran. Each version names the detector paths it changed, as a regex on
# the start of comp_basis; a row is stale only when a version newer than its stamp changed its row's path.
# Versions up to 24 count as changing every path (v24 was a full re-run of every detector row).
CHANGED_PATHS = {
    # detector bases only - hand-written ones ("schematic PDF only", "BOMs in ...") are not detector output
    "25": r"BOM[ (]",                     # BOMs recorded in html-boms.tsv, any file type (MI <Module>.xlsx)
    "26": r"(BOM[ (]|easyeda|eagle|ibom|gerber paste\+drill|no \.kicad_pcb|fetch failed|\d+ \.kicad_pcb fetched)",
                                          # zipped EasyEDA precedes Eagle / iBOM / BOM / gerbers; pad-read packages
}
def stale_by(stamp, basis):
    """versions newer than stamp that changed the detector path this basis came from"""
    try: s = int(stamp)
    except ValueError: return ["(no stamp)"]
    return [str(v) for v in range(s + 1, int(DETECTOR_VERSION) + 1)
            if v <= 24 or re.match(CHANGED_PATHS.get(str(v), r""), basis or "")]
# components may only be non-blank at these confidences (CLAUDE.md)
OK_CONF = {"Stated", "Strong"}
# Type of Module must state a function; everything in this table is a eurorack module
GENERIC_TYPES = {"eurorack module", "module", "synth module", "synthesizer module",
                 "dev platform", "platform", "eurorack", "diy module"}


def _month(updated):
    """'Jul 19, 2024' -> '2024-07' (inventory dates are GitHub's display format)."""
    mm = re.match(r"\s*([A-Za-z]{3})\w* +\d+, +(\d{4})", updated or "")
    if not mm:
        return None
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    return f"{mm.group(2)}-{months.index(mm.group(1).lower())+1:02d}"


def web_errs(m, errs):
    """a web row's link, sha and date are copied from web-sources.tsv; its file links were found on its page"""
    i, u = m["id"], m["link"]
    if u not in (f"https://{m['repo']}/{m['module_dir']}", f"http://{m['repo']}/{m['module_dir']}"):
        errs.append(f"{i}: web row link {u!r} is not https://<repo>/<module_dir>")
    src = WEB_SRC.get(u)
    if not src or src["status"] != "200" or src["found_on"]:
        errs.append(f"{i}: web row link {u!r} is not a fetched page in web-sources.tsv - run data/web_fetch.py"); return
    if m["sha"] != "sha256:" + src["sha256"][:12]:
        errs.append(f"{i}: sha {m['sha']!r} != web-sources.tsv sha256:{src['sha256'][:12]} for {u}")
    if m["date"] != src["fetched"]:
        errs.append(f"{i}: date {m['date']!r} != web-sources.tsv fetched {src['fetched']!r} for {u}")
    s = m["schematic"]
    for v in ([] if s in ("", "x", "n/a") else [s]) + (m.get("photos") or "").split() + (m.get("build") or "").split():
        if v != u and not (v in WEB_LINKS.get(u, ()) and WEB_SRC.get(v, {}).get("found_on") == u
                           and WEB_SRC[v]["status"] == "200"):
            errs.append(f"{i}: {v[:80]} is not a fetched link of {u} - run data/web_fetch.py --from")


def validate(mods):
    """Fail loudly rather than shipping a row that breaks a hard rule."""
    # Pinned SHAs are evidence, so they must come from the harvest, never be typed.
    with open("data/inventory.tsv") as f:
        head_sha = {r["repo"]: r["head_sha"] for r in csv.DictReader(f, delimiter="\t")}
    with open("data/inventory.tsv") as f:
        inv_month = {r["repo"]: _month(r["updated"]) for r in csv.DictReader(f, delimiter="\t")}
    errs = []
    seen_id, seen_key = {}, {}
    for m in mods:
        i = m["id"]
        # a row is one buildable variant: the same id, or the same module twice, is a bug
        if i in seen_id: errs.append(f"{i}: duplicate id")
        seen_id[i] = 1
        k = (m["repo"], m["module_dir"], m["module_name"])
        if k in seen_key: errs.append(f"{i}: duplicates {seen_key[k]} ({k})")
        seen_key[k] = i
        if m["components"] not in ("", "THT", "SMD", "both"):
            errs.append(f"{i}: components {m['components']!r} not in THT / SMD / both / blank")
        # the verdict must follow the rule from the tally the detector recorded, so a
        # hand-edited call and its evidence can never disagree
        mt = re.search(r"smd=(\d+) tht_passive=(\d+) tht_to=(\d+) tht_ic=(\d+)", m["comp_basis"])
        if mt and m["comp_conf"] in OK_CONF:
            smd, tp, tq, ic = map(int, mt.groups())   # tq (TO-92/TO-220) never decides
            want = ("both" if smd and (ic or tp > 5) else "SMD" if smd else "THT" if (tp or tq or ic) else "")
            # v22 (d 2026-09-26 16:23): verified no SMD parts -> THT, even with panel hardware only
            if not want and re.search(r"\[panel hardware only: \d+ through-hole parts, no SMD\]|^gerber paste\+drill \[no SMD pads", m["comp_basis"]):
                want = "THT"
            if want != m["components"]:
                errs.append(f"{i}: components {m['components']!r} but the recorded tally "
                            f"(smd={smd} tht={tp} tht_ic={ic}) gives {want!r}")
        if m["date"] and inv_month.get(m["repo"]) and m["date"][:7] != inv_month[m["repo"]]:
            errs.append(f"{i}: date {m['date']!r} disagrees with inventory 'updated' "
                        f"({inv_month[m['repo']]}) for {m['repo']}")
        if is_web(m):
            web_errs(m, errs)
        elif not m["link"].startswith(f"https://github.com/{m['repo']}"):
            errs.append(f"{i}: link {m['link']!r} does not point into {m['repo']}")
        elif m["module_dir"] != "." and "/tree/" not in m["link"] and "/blob/" not in m["link"]:
            errs.append(f"{i}: link is the repo root but the module is in {m['module_dir']!r}")
        owner = m["repo"].split("/")[0]
        if "GitHub owner" in m["creator_basis"] and m["creator"].split(" + ")[-1] != owner:
            errs.append(f"{i}: creator falls back to the GitHub owner but reads "
                        f"{m['creator'].split(' + ')[-1]!r}, not {owner!r} - never prettify handles")
        if not is_web(m) and m["sha"] != head_sha.get(m["repo"]):
            errs.append(f"{i}: sha {m['sha']!r} != inventory head_sha "
                        f"{head_sha.get(m['repo'])!r} for {m['repo']}")
        # schematic?: a deep link to a standalone schematic file (PDF, else image) in the
        # row's repo; "x" only when the schematic is implicit (inside KiCad/Eagle/EasyEDA
        # sources or a zip) and has no path of its own; "n/a" or blank otherwise.
        s = m["schematic"]
        if s not in ("", "x", "n/a") and not is_web(m) and not s.startswith(f"https://github.com/{m['repo']}/blob/"):
            errs.append(f"{i}: schematic {s!r} is neither x / n/a / blank nor a /blob/ link into {m['repo']}")
        if m["components"] and m["comp_conf"] not in OK_CONF:
            errs.append(f"{i}: components={m['components']!r} at confidence "
                        f"{m['comp_conf']!r} - must be blank below {sorted(OK_CONF)}")
        t = (m["type"] or "").strip().lower()
        if t in GENERIC_TYPES:
            errs.append(f"{i}: Type of Module {m['type']!r} is generic - state a function")
        _st = stale_by(m.get("detector_version", ""), m.get("comp_basis", ""))
        if _st:
            errs.append(f"{i}: detector_version {m.get('detector_version')!r} is stale - v{', v'.join(_st)} "
                        f"changed this row's detector path; re-run components.sh")
        pr = m.get("prototype") or ""
        if pr not in ("", "X", "?"):
            errs.append(f"{i}: prototype {pr!r} not in X / ? / blank")
        if pr and not (m.get("prototype_basis") or "").strip():
            errs.append(f"{i}: prototype={pr!r} without a prototype_basis quote")
        pn = m.get("panel") or ""
        if pn and not PANEL_RE.match(pn): errs.append(f"{i}: panel {pn!r} does not read 'NHP · source + source' (or bare '0HP')")
        if pn and not (m.get("panel_basis") or "").strip(): errs.append(f"{i}: panel without panel_basis")
        for u in (m.get("photos") or "").split():
            # an external URL is allowed only when d listed it for this row in data/photo-includes.tsv (d 2026-09-28)
            if not is_web(m) and not u.startswith(f"https://github.com/{m['repo']}/blob/") and u not in PHOTO_URLS.get(m["id"], ()):
                errs.append(f"{i}: photo link outside the row's repo: {u[:80]}")
        for u in (m.get("build") or "").split():
            if not is_web(m) and not re.match(rf"https://github\.com/{re.escape(m['repo'])}/(blob|tree)/", u): errs.append(f"{i}: build-guide link outside the row's repo: {u[:80]}")
        for c in COLS:
            if "\t" in (m.get(c) or "") or "\n" in (m.get(c) or ""):
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
# Append the "prototype" column to the frozen rows without re-serialising them: csv.reader's
# line_num gives the physical line each logical row ends on (one curated creator field holds a
# newline), so the extra cell is added to that line only - every other byte stays as committed.
_lines = frozen.split("\n")
_rd = csv.reader(io.StringIO(frozen)); _ends = []
for _row in _rd: _ends.append(_rd.line_num - 1)
_cur = {int(r["k"]): r for r in csv.DictReader(open("data/curated-panel-photos.tsv"), delimiter="\t")}
def _cells(vals):
    b = io.StringIO(); csv.writer(b, lineterminator="").writerow(vals); return b.getvalue()
for k, ln in enumerate(_ends):
    extra = EXTRA_HEAD if k == 0 else EXTRA_LEGEND if k == 1 else [(_cur.get(k - 2) or {}).get(c, "") for c in ("panel", "photos", "build")]
    _lines[ln] += "," + ("prototype" if k == 0 else PROTO_LEGEND if k == 1 else "") + "," + _cells(extra)
frozen = "\n".join(_lines)
n_frozen = len(_ends)

with open("data/modules.tsv") as f:
    mods = list(csv.DictReader(f, delimiter="\t"))
validate(mods)
# Stand-ins for the handwritten rows (d, 2026-10-22: retire the frozen rows once each is covered once by a
# generated row). Until the switch they live in modules.tsv (so the site sees them) but stay out of the CSV,
# which still carries the handwritten originals - no module appears twice. data/handwritten-map.tsv: one
# line per stand-in, hrow = the handwritten row's logical CSV row (3 = first module row).
_hw = {r["id"]: r for r in csv.DictReader(open("data/handwritten-map.tsv"), delimiter="\t")} \
      if os.path.exists("data/handwritten-map.tsv") else {}
_unknown = set(_hw) - {m["id"] for m in mods}
if _unknown: raise SystemExit(f"generate.py: handwritten-map.tsv names ids not in modules.tsv: {sorted(_unknown)}")
standins = [m for m in mods if m["id"] in _hw]
mods = [m for m in mods if m["id"] not in _hw]

# --- CSV: frozen bytes verbatim, then generated rows ---
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\n")
for m in mods:
    w.writerow([m.get(c) or "" for c in COLS])
if not frozen.endswith("\n"): frozen += "\n"
open("eurorack-open-source.csv","w").write(frozen + buf.getvalue())

# --- audit table, same source ---
def cell(s): return (s or "").replace("|","\\|")
lines = [
 "# Enrichment audit","",
 "Generated from `data/modules.tsv` — the same source as the CSV rows, so the two cannot disagree.",
 "Row numbers continue the CSV's own numbering. Every non-blank cell traces to a file path or a quoted line.","",
 "`components` confidence: **Stated** (README/BOM says so) · **Strong** (unambiguous footprints) · **Weak** · **Deferred** (needs Pass B part lookup).","",
 "| # | Module | Repo @ commit (date) | Type — basis | Layout / schematic | License — basis | Components — call · basis · confidence | Blanks & why | Follow-up | Panel — basis |",
 "|---|---|---|---|---|---|---|---|---|---|",
]
for i,m in enumerate(mods, start=n_frozen+1):
    blanks=[]
    if not m["license"]:    blanks.append(f'`License` — {m["license_basis"] or "not stated"}')
    if not m["components"]: blanks.append(f'`components` — {m["comp_conf"]}')
    if not m["layout"]:     blanks.append("`layout` — no EDA source identified")
    if not m["notes"]:      pass
    fu = m["followup"] or ""
    # Files set aside as older revisions (latest_files.py) are a guess from names: a "v2" can be a
    # different circuit (bummbummgarage vca-0.1 / vca-0.2). Always queue them for review.
    ms = re.search(r"\[superseded, not counted: ([^\]]*)\]", m["comp_basis"])
    if ms:
        fu = (f"**review components**: set aside as older revisions of the same board - confirm they are "
              f"not different modules: {ms.group(1)}. " + fu).strip()
    # Multi-board rule (d via Fable 0130, applied 2026-09-26 pending d's yes; board + panel PCB is
    # exempt): 2+ non-panel board files pooled into one row are always queued for review - the
    # names cannot tell sub-boards from variants or different modules.
    mf = re.search(r"\(files=\d+: (.*?)\): smd=", m["comp_basis"])
    if mf:
        boards = [f for f in mf.group(1).split(", ") if f.strip()
                  and not re.search(r"panel|face ?plate|front ?plate|frontpanel|autosave", f, re.I)]
        if len(boards) >= 2:
            fu = (f"**review components**: {len(boards)} board files pooled into one row ({', '.join(boards)}) - "
                  f"confirm they are sub-boards of one module, not variants or different modules. " + fu).strip()
    # Per-module review queue for the SMD/THT call: a DIP/SIP part beside SMD parts makes
    # the build "both" on package name alone, so name it for a check. TO-92/TO-220 parts
    # never decide (user, 2026-09-26); from 10 of them on an SMD row a note is added so the
    # THT effort gets a look (user, 03:51) - informational, the verdict stays SMD.
    mt = re.search(r"smd=(\d+) tht_passive=\d+ tht_to=(\d+) tht_ic=(\d+)", m["comp_basis"])
    if mt and int(mt.group(1)) > 0 and int(mt.group(3)) > 0:
        fu = (f"**review components**: {mt.group(3)} THT IC(s) (DIP/SIP) beside SMD parts -> both. " + fu).strip()
    if mt and m["components"] == "SMD" and int(mt.group(2)) >= 10:
        fu = (f"**review components**: {mt.group(2)} TO-92/TO-220 parts on an SMD row (they never "
              f"decide the call; check the THT effort). " + fu).strip()
    if mt and m["components"]:
        nparts = sum(int(x) for x in re.findall(r"(?:smd|tht_passive|tht_to|tht_ic)=(\d+)", m["comp_basis"]))
        if nparts < 5:
            fu = (f"**review components**: verdict rests on {nparts} classified part(s) - footprints may be unrecognised. " + fu).strip()
    # Stacked / multi-board modules whose schematic is split over several files (user, 2026-09-26
    # 05:51): the column keeps one link (or x); the complication and every file go in the audit.
    if (m["schematic"].startswith("http") or m["schematic"] == "x") and \
            sum(1 for o in mods if o["repo"] == m["repo"] and o["module_dir"] == m["module_dir"]) == 1:
        tf = os.path.join("data", "trees", m["repo"].replace("/", "_") + ".txt")
        if os.path.exists(tf):
            d = m["module_dir"]
            sch = [x for x in open(tf, encoding="utf-8").read().splitlines()
                   if (d == "." or x.startswith(d + "/")) and re.search(r"\.(pdf|png|jpe?g|svg)$", x, re.I)
                   and (re.search(r"(sch|schem|circuit)", os.path.basename(x), re.I) or re.search(r"schem", os.path.dirname(x), re.I))]
            if len(sch) > 1 and (m["components"] or m["layout"]):
                fu = (f"**schematic split over {len(sch)} files** (stacked/sub-boards or revisions; column links one): "
                      f"{', '.join(os.path.basename(x) for x in sch[:8])}{' ...' if len(sch) > 8 else ''}. " + fu).strip()
    if m.get("prototype"):
        fu = (f"**prototype {m['prototype']}**: {m.get('prototype_basis') or ''}. " + fu).strip()
    if "GitHub owner" in m["creator_basis"]:
        fu = ("creator is the GitHub owner - no brand name found in repo. " + fu).strip()
    # A schematic is the basis for a BOM, so a missing BOM only matters when there is
    # no schematic or EDA source either. "blocks a parts order" was simply untrue.
    has_source = bool(m["schematic"]) or bool(m["layout"])
    if m["bom"] != "y" and not has_source:
        fu = ("**no BOM and no schematic/EDA source** — nothing to derive a parts list from. " + fu).strip()
    lines.append("| {} | {} · {} | `{}` @ `{}` ({}) | {} | `{}` / sch={} | {} | **{}** · {} · **{}** | {} | {} | {} |".format(
        i, cell(m["creator"]), cell(m["module_name"]), m["repo"], m["sha"], m["date"],
        cell(m["type_basis"]), cell(m["layout"] or "—"), m["schematic"] or "—",
        cell(m["license_basis"] or "—"), cell(m["components"] or "blank"), cell(m["comp_basis"]), m["comp_conf"],
        cell("; ".join(blanks) if blanks else "none"), cell(fu),
        cell(((m.get("panel") or "") + " — " + (m.get("panel_basis") or "")) if m.get("panel") else "—")))
if standins:
    lines += ["", "## Stand-ins for handwritten rows (in modules.tsv, not in the CSV yet)", "",
              "Each will replace the handwritten row it names when the frozen rows are retired (d, 2026-10-22).", "",
              "| id | replaces CSV row | Module | Repo @ commit | Type | Layout / schematic | License | Components · confidence | Prototype | Panel |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for m in standins:
        h = _hw[m["id"]]
        lines.append("| {} | {} ({}) | {} · {} | `{}` @ `{}` | {} | `{}` / sch={} | {} | **{}** · {} | {} | {} |".format(
            m["id"], h["hrow"], cell(h["handwritten"]), cell(m["creator"]), cell(m["module_name"]), m["repo"], m["sha"],
            cell(m["type"]), cell(m["layout"] or "—"), m["schematic"] or "—", cell(m["license"] or "—"),
            cell(m["components"] or "blank"), m["comp_conf"], m.get("prototype") or "—", cell(m.get("panel") or "—")))
open("enrichment-audit.md","w").write("\n".join(lines)+"\n")
print(f"frozen logical rows: {n_frozen}; generated: {len(mods)}; stand-ins kept out of the CSV: {len(standins)}")
