#!/usr/bin/env python3
"""Panel folders set aside in skips.tsv that belong to a row (d, 2026-09-28 09:49: "yes" to the website session's
proposal: "when a folder that skips.tsv sets aside says it belongs to a module's row ('part of / covered by /
pooled into the X row'), count its panel files for that row").

Resolves each such skips.tsv line to ONE row id and writes data/skip-panels.tsv (repo, skip_dir, id, how, reason).
panel_photos.py reads it and adds the panel files under skip_dir (panel-named paths only) to that row.
Resolution, first that works: a row id in the reason ("row p03"); a module_dir of the repo quoted or named in the
reason; a module name of the repo named in the reason ("the Miasma row"); "repo-root" / "module_dir '.'" -> the '.' row;
the nearest row whose module_dir is an ancestor or sibling-prefix of skip_dir; the repo's only row. Else unresolved.
Never: superseded / older / backup copies (they are not the current panel)."""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BELONGS = re.compile(r"part of|covered by|pooled into", re.I)
NOT_CURRENT = re.compile(r"supersed|older|\bold\b|backup|\bbu\b|previous|obsolete|earlier|exclud|not a eurorack", re.I)
rows = {}
for r in csv.DictReader(open(os.path.join(HERE, "modules.tsv"), newline=""), delimiter="\t"):
    rows.setdefault(r["repo"], []).append(r)
def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
out, unres = [], []
for s in csv.DictReader(open(os.path.join(HERE, "skips.tsv"), newline=""), delimiter="\t"):
    repo, d, why = s["repo"], s["module_dir"].strip("/"), s["reason"]
    if not BELONGS.search(why) or NOT_CURRENT.search(why) or repo not in rows: continue
    rs = rows[repo]; hit = how = None
    m = re.search(r"\brow (p\d+)\b", why)
    if m and any(r["id"] == m.group(1) for r in rs): hit, how = m.group(1), "row id in reason"
    if not hit:   # a module_dir named in the reason (longest first)
        c = [r for r in rs if r["module_dir"] not in (".", "") and (r["module_dir"] in why or r["module_dir"].rsplit("/", 1)[-1] in why)]
        c.sort(key=lambda r: -len(r["module_dir"]))
        if c: hit, how = c[0]["id"], f"module_dir '{c[0]['module_dir']}' named in reason"
    if not hit:   # a module name named in the reason ("the Speak to Me row"); longest name wins
        tail = norm(why.split(" - ", 1)[-1])
        c = [r for r in rs if len(norm(r["module_name"])) >= 3 and norm(r["module_name"]) in tail]
        c.sort(key=lambda r: -len(norm(r["module_name"])))
        if c: hit, how = c[0]["id"], f"module name '{c[0]['module_name']}' named in reason"
    if not hit and re.search(r"repo-root|module_dir '\.'", why):
        c = [r for r in rs if r["module_dir"] in (".", "")]
        if len(c) == 1: hit, how = c[0]["id"], "repo-root row"
    if not hit:   # nearest row folder that contains the skipped folder
        c = [r for r in rs if r["module_dir"] not in (".", "") and d.startswith(r["module_dir"].strip("/") + "/")]
        c.sort(key=lambda r: -len(r["module_dir"]))
        if c: hit, how = c[0]["id"], f"inside row folder '{c[0]['module_dir']}'"
    if not hit:   # "part of its module row": the row folder beside it (same parent folder), when only one
        par = d.rsplit("/", 1)[0] if "/" in d else ""
        c = [r for r in rs if r["module_dir"] not in (".", "") and (r["module_dir"].strip("/").rsplit("/", 1)[0] if "/" in r["module_dir"].strip("/") else "") == par and par]
        if len(c) == 1: hit, how = c[0]["id"], f"sibling of row folder '{c[0]['module_dir']}'"
    if not hit:   # "part of both Super Sixteen rows": every row whose name starts with the named text
        m = re.search(r"both (.+?) rows", why)
        c = [r for r in rs if m and norm(r["module_name"]).startswith(norm(m.group(1)))]
        if len(c) > 1: hit, how = ",".join(r["id"] for r in c), f"both '{m.group(1)}' rows"
    if not hit and len(rs) == 1: hit, how = rs[0]["id"], "repo's only row"
    (out if hit else unres).append([repo, d, hit or "", how or "", why])
with open(os.path.join(HERE, "skip-panels.tsv"), "w", newline="") as fh:
    fh.write("repo\tskip_dir\tid\thow\treason\n")
    for o in out: fh.write("\t".join(o) + "\n")
print(f"resolved {len(out)}, unresolved {len(unres)}")
for u in unres: print("UNRESOLVED\t" + "\t".join(u), file=sys.stderr)
