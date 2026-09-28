#!/usr/bin/env python3
"""Run cpl_check.py over the boards of every KiCad-footprint row (d, 2026-09-28 04:52). READ-ONLY:
writes data/cpl-audit.tsv (one line per row x board) and prints a summary; modules.tsv and the
CSV are not touched.

Boards = the files a row's comp_basis counted (files=N: ...), found in the row's scope, else once
in the repo tree (pooled sibling-folder boards). Panel boards are skipped (d 04:37). Fetched at the
pinned inventory SHA. Row grade = the worst of its SMD boards (needs-cleanup < cpl-ready <
parts-identified); rows whose boards hold no SMD placements read no-smd / no-placements."""
import csv, os, re, subprocess, sys, urllib.parse, concurrent.futures as cf
from collections import Counter
csv.field_size_limit(10**9)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); import cpl_check as C
inv = {l.split("\t")[1]: l.rstrip("\r\n").split("\t") for l in open(os.path.join(HERE, "inventory.tsv"), encoding="utf-8").read().splitlines()[1:]}
rows = [m for m in csv.DictReader(open(os.path.join(HERE, "modules.tsv"), encoding="utf-8"), delimiter="\t")
        if m["comp_basis"].startswith("kicad footprints")]
at = lambda p, x: p == x or p.endswith("/" + x)
jobs = []   # (id, repo, sha, path)
unres = []
for m in rows:
    fm = re.search(r"\(files=\d+: (.*?)\): smd=", m["comp_basis"])
    names = [x.strip() for x in fm.group(1).split(", ")] if fm else []
    md = m["module_dir"] or "."
    scope = subprocess.run(["bash", os.path.join(HERE, "modulefiles.sh"), m["repo"], md], capture_output=True, text=True).stdout.splitlines()[1:]
    tree = open(os.path.join(HERE, "trees", m["repo"].replace("/", "_") + ".txt"), encoding="utf-8").read().splitlines()
    sha = inv[m["repo"]][5] or inv[m["repo"]][6]
    for x in dict.fromkeys(names):
        hit = [p for p in scope if at(p, x)] or [p for p in tree if at(p, x)]
        # the same file name counted more than once (Moduleur PSU: files=2: psu.kicad_pcb, psu.kicad_pcb)
        # = that many boards of that name: take them all when the numbers agree
        if len(hit) != 1 and len(hit) != names.count(x): unres.append((m["id"], x, len(hit))); continue
        for h_ in hit: jobs.append((m["id"], m["repo"], sha, h_))

BOARDREFS = {}   # (row id, board path) -> its placement references
BREFS = {}   # row id -> every placement reference on its (non-panel) boards, for the staleness check
def run(j):
    rid, repo, sha, path = j
    if C.PANEL_FILE.search(path): return j, "grade=skipped-panel", []
    if re.search(r"stencil", path.rsplit("/", 1)[-1], re.I): return j, "grade=skipped-stencil", []   # a copy for ordering a solder stencil (Addatone)
    u = f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}"
    r = subprocess.run(["curl", "-sS", "--fail", "-m", "120", u], capture_output=True)   # in memory: no disk cache
    if r.returncode: return j, "grade=fetch-failed", []
    refs = {}
    s, iss = C.grade(r.stdout.decode("utf-8", "replace"), refs)
    BREFS.setdefault(rid, set()).update(refs); BOARDREFS[(rid, path)] = refs
    return j, s, iss

out = []
with cf.ThreadPoolExecutor(16) as ex:
    for (rid, repo, sha, path), s, iss in ex.map(run, jobs):
        kv = dict(x.split("=", 1) for x in s.split() if "=" in x)
        libs = Counter(f["lib"] for k, f in iss)
        out.append([rid, repo, path, kv.get("grade", "?"), kv.get("smd_placements", ""), kv.get("smd_with_pn", ""),
                    kv.get("smd_with_lcsc", ""), kv.get("back_side", ""), kv.get("kicad_version", ""),
                    "; ".join(f"{k}={v}" for k, v in kv.items() if k.startswith("issue[")),
                    ", ".join(f"{l} x{n}" for l, n in libs.most_common(4))])
H = ["id", "repo", "board", "grade", "smd", "smd_with_pn", "smd_with_lcsc", "back_side_smd", "kicad_version", "issues", "issue_footprints"]
with open(os.path.join(HERE, "cpl-audit.tsv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n"); w.writerow(H); w.writerows(sorted(out, key=lambda x: (int(re.sub(r"\D", "", x[0]) or 0), x[2])))
RANK = ["needs-cleanup", "cpl-ready", "parts-identified"]
def pnsrc(nl, n):   # which kind of part numbers: recorded beside the grade, never ranked (d 05:48)
    return "" if not n else "LCSC" if nl == n else "MPN/SKU" if nl == 0 else "mixed"
byrow = {}
for o in out: byrow.setdefault(o[0], []).append(o[3])
rg = Counter()
for rid, gs in byrow.items():
    smd = [g for g in gs if g in RANK]
    rg[min(smd, key=RANK.index) if smd else ("fetch-failed" if "fetch-failed" in gs else "no-smd" if "no-smd" in gs else "no-placements" if "no-placements" in gs else "only-panels")] += 1
print(f"rows {len(rows)} | boards {len(jobs)} | unresolved names {len(unres)}")
print("boards:", dict(Counter(o[3] for o in out).most_common()))
print("rows:  ", dict(rg.most_common()))
print("back-side SMD boards:", sum(1 for o in out if o[7] not in ("", "0")))
for u in unres[:5]: print("  unresolved:", *u)

# --- shipped placement files (d 05:17) ---------------------------------------------------------
import cpl_shipped as S
allrows = list(csv.DictReader(open(os.path.join(HERE, "modules.tsv"), encoding="utf-8"), delimiter="\t"))
NROWS = Counter(m["repo"] for m in allrows)
SHARED = Counter((m["repo"], m["module_dir"] or ".") for m in allrows)
def fetch(repo, sha, path):
    r = subprocess.run(["curl", "-sS", "--fail", "-m", "90", f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}"], capture_output=True)
    return None if r.returncode else r.stdout
def shipped(m):
    tree = open(os.path.join(HERE, "trees", m["repo"].replace("/", "_") + ".txt"), encoding="utf-8").read().splitlines()
    if not any(S.is_place(p) for p in tree): return None
    scope = subprocess.run(["bash", os.path.join(HERE, "modulefiles.sh"), m["repo"], m["module_dir"] or "."], capture_output=True, text=True).stdout.splitlines()[1:]
    if NROWS[m["repo"]] == 1: scope = tree   # one row per repo: plugin folders (jlcpcb/) can be detected as a module dir of their own (Spectralist)
    pf = [p for p in scope if S.is_place(p)]
    if not pf: return None
    # archive / old / backup copies only when nothing current exists (d 2026-09-28 06:55 backup rule;
    # Super Synthesis jlcpcb/_archive/ holds REV3/REV4 beside the current REV5)
    cur_pf = [p for p in pf if not S.OLD.search(p)]
    if cur_pf: pf = cur_pf
    # a folder shared with other rows (TiNRS "Eurorack Set 2021": Ardabil, Switch, Ducktape ...): a file counts
    # only when its path below the folder names this module or one of its counted board files (2026-09-28)
    md = m["module_dir"] or "."
    if SHARED[(m["repo"], md)] > 1:
        norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
        fm = re.search(r"\(files=\d+: (.*?)\)", m["comp_basis"])
        stems = {norm(re.sub(r"\.[A-Za-z0-9]+$", "", x.strip())) for x in (fm.group(1).split(", ") if fm else [])}
        stems |= {norm(w) for w in re.split(r"[\s(/)+-]+", m["module_name"]) if len(norm(w)) >= 4}
        stems = {t for t in stems if len(t) >= 4}
        below = lambda p: norm(p[len(md) + 1:] if md != "." else p)
        keep = [p for p in pf if any(t in below(p) for t in stems)]
        othr = [p for p in pf if p not in keep]
        pf = keep
        if not pf: return [m["id"], m["repo"], "; ".join(f"(not this row's board: {p})" for p in othr), 0, "", "", "", "", "", "shipped-other-board", ""]
    dirs = {p.rsplit("/", 1)[0] if "/" in p else "" for p in pf}
    bf = [p for p in scope if re.search(r"\.(csv|tsv|txt|xlsx?)$", p, re.I) and (
          ((p.rsplit("/", 1)[0] if "/" in p else "") in dirs and S.BOMF.search(p.rsplit("/", 1)[-1])) or S.BOMDIR.search(p))]
    cur_bf = [p for p in bf if not S.OLD.search(p)]
    if cur_bf: bf = cur_bf
    sha = inv[m["repo"]][5] or inv[m["repo"]][6]
    refs, sides, bom, bad = set(), {}, {}, []
    boards = {b: r for (rid, b), r in BOARDREFS.items() if rid == m["id"] and r}
    stale, judged, unpaired = 0, False, []
    pkgs = {}; bomfp = {}
    for p in pf:
        d = fetch(m["repo"], sha, p)
        if d is None: bad.append(p); continue
        try: r, sd = S.placements(p, d, pkgs)
        except Exception as e: bad.append(p); continue
        b = S.pair(p, boards)
        if not b and r and not re.search(r"experiment|variant", p, re.I):
            # names/folders do not pair it (StudioKAT Gerber_for_JLCPCB/ vs KiCAD/, CATs Gerber/): take the board
            # that already holds >= 90% of its references; a file for another board (moduleur ui/) will not reach it
            ov = max(((len(r & set(v)) / len(r), k) for k, v in boards.items()), default=(0, None))
            if ov[0] >= 0.9: b = ov[1]
        if boards and not b: unpaired.append(p); continue   # a variant / other board the row does not count (moduleur experimental/)
        refs |= r
        if b and r: judged = True; stale += len(r - set(boards[b]))
        for x in r:   # a part number on the board counts too: shipped files add evidence, never remove it
            bp = (boards[b].get(x) if b else None) or next((v[x] for v in boards.values() if x in v), (False, False, True))
            if bp[0] or bp[1]:
                o = bom.get(x, (False, False)); bom[x] = (o[0] or bp[0], o[1] or bp[1])
        for k, v in sd.items(): sides[k] = sides.get(k, 0) + v
    for p in bf:
        d = fetch(m["repo"], sha, p)
        if d is None: continue
        try: bm = S.bom_parts(p, d, bomfp)
        except Exception: continue
        for k, (a, b) in bm.items():
            x, y = bom.get(k, (False, False)); bom[k] = (x or a, y or b)
    pf = [p for p in pf if p not in unpaired] + [f"(not this row's board: {p})" for p in unpaired]
    if not refs: return [m["id"], m["repo"], "; ".join(pf), 0, "", "; ".join(bf), "", "", "", "shipped-unreadable" if bad else "shipped-other-board" if unpaired else "shipped-empty", ""]
    # judge the SMD parts only: "all parts" position exports also list the hand-soldered THT jacks and pots.
    # A reference no board knows (EasyEDA / Eagle rows, stale files) is kept in.
    info = lambda x: next((v[x] for v in boards.values() if x in v), None)
    # a placement file without a package column (JLCPCB XY/CPL): the paired BOM's footprint column describes its
    # parts instead - 2OPFM's XY lists the Thonkiconn jacks, LED and pots too, which are not SMD (d 07:16)
    for x in refs:
        if x not in pkgs and x in bomfp: pkgs[x] = bomfp[x]
    # no board describes a reference: its package column decides; neither THT nor SMD -> left out, counted
    # the row's board decides; else the file's package column; a file with NO package column is a
    # pick list (JLCPCB CPL: Designator, Mid X, Mid Y, Layer, Rotation) - its parts are the SMD placements
    # last resort, nothing describes it: panel-hardware designators (jacks, switches, pots, LEDs, test points,
    # holes, fiducials - the iBOM reader's rule) are not SMD; anything else in a pick list is (2OPFM J3: in the XY
    # file, missing from the BOM)
    PANELREF = re.compile(r"^(J|JP|SW|S|RV|VR|LED|TP|MH|H|FID|BT|KNOB)\d", re.I)
    kind = lambda x: (("smd" if info(x)[2] else "tht") if info(x) is not None else S.pkg_kind(pkgs[x]) if x in pkgs
                      else "panel" if PANELREF.match(x) else "smd")
    smdrefs = {x for x in refs if kind(x) == "smd"}
    uncl = sum(1 for x in refs if kind(x) == "")
    nl = sum(bom.get(x, (False, False))[0] for x in smdrefs); npn = sum(bom.get(x, (False, False))[1] for x in smdrefs)
    stale = stale if judged else ""
    g = ("unclassified" if uncl else "no-smd") if not smdrefs else "parts-identified" if bom and npn == len(smdrefs) else "cpl-ready"
    return [m["id"], m["repo"], "; ".join(pf), f"{len(refs)} ({len(smdrefs)} SMD" + (f", {uncl} unclassified" if uncl else "") + ")", " ".join(f"{k}={v}" for k, v in sorted(sides.items())),
            "; ".join(bf), nl if bom else "", npn if bom else "", stale, g, pnsrc(nl, len(smdrefs)) if g == "parts-identified" else ""]
with cf.ThreadPoolExecutor(12) as ex:
    sh = [x for x in ex.map(shipped, allrows) if x]
SH = ["id", "repo", "placement_files", "placed_refs", "sides", "bom_files", "smd_with_lcsc", "smd_with_pn", "refs_not_on_board", "grade", "part_numbers"]
with open(os.path.join(HERE, "cpl-shipped.tsv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n"); w.writerow(SH); w.writerows(sorted(sh, key=lambda x: int(re.sub(r"\D", "", x[0]) or 0)))
# per-row result: shipped files decide where present, else the board grade
bgrade = {}
for rid, gs in byrow.items():
    smd = [g for g in gs if g in RANK]
    bgrade[rid] = min(smd, key=RANK.index) if smd else ("no-smd" if "no-smd" in gs else "no-placements" if "no-placements" in gs else "only-panels")
shd = {x[0]: x for x in sh}
bsrc = {}
for o in out:
    if o[3] == "parts-identified": a = bsrc.setdefault(o[0], [0, 0]); a[0] += int(o[6] or 0); a[1] += int(o[4] or 0)
with open(os.path.join(HERE, "cpl-rows.tsv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n")
    w.writerow(["id", "repo", "module_name", "grade", "source", "part_numbers", "board_grade", "shipped_grade", "shipped_refs_not_on_board"])
    for m in allrows:
        b, x = bgrade.get(m["id"], ""), shd.get(m["id"])
        if not b and (not x or x[9] in ("shipped-empty", "shipped-other-board")): continue   # not checked
        use_x = bool(x) and (not x[9].startswith("shipped-") or not b)   # shipped files decide unless empty / unreadable / another board's
        g = x[9] if use_x else b
        src = x[10] if use_x else (pnsrc(*bsrc[m["id"]]) if g == "parts-identified" and m["id"] in bsrc else "")
        w.writerow([m["id"], m["repo"], m["module_name"], g, "shipped files" if use_x else "board", src, b, x[9] if x else "", x[8] if x else ""])
fin = Counter(l.split("\t")[3] for l in open(os.path.join(HERE, "cpl-rows.tsv"), encoding="utf-8").read().splitlines()[1:])
print("shipped placement files: rows", len(sh), dict(Counter(x[9] for x in sh).most_common()))
print("stale (refs not on the board):", sum(1 for x in sh if isinstance(x[8], int) and x[8] > 0), "of", sum(1 for x in sh if isinstance(x[8], int)), "checkable")
print("final rows:", dict(fin.most_common()))
print("parts-identified by part-number source:", dict(Counter((l.split("\t")[5]) for l in open(os.path.join(HERE, "cpl-rows.tsv"), encoding="utf-8").read().splitlines()[1:] if l.split("\t")[3] == "parts-identified").most_common()))
