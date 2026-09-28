#!/usr/bin/env python3
"""Run cpl_check.py over the boards of every KiCad-footprint row (d, 2026-09-28 04:52). READ-ONLY:
writes data/cpl-audit.tsv (one line per row x board) and prints a summary; modules.tsv and the
CSV are not touched.

Boards = the files a row's comp_basis counted (files=N: ...), found in the row's scope, else once
in the repo tree (pooled sibling-folder boards). Panel boards are skipped (d 04:37). Fetched at the
pinned inventory SHA. Row grade = the worst of its SMD boards (needs-cleanup < cpl-ready <
parts-mpn < parts-lcsc); rows whose boards hold no SMD placements read no-smd / no-placements."""
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
    for x in names:
        hit = [p for p in scope if at(p, x)] or [p for p in tree if at(p, x)]
        if len(hit) != 1: unres.append((m["id"], x, len(hit))); continue
        jobs.append((m["id"], m["repo"], sha, hit[0]))

def run(j):
    rid, repo, sha, path = j
    if C.PANEL_FILE.search(path): return j, "grade=skipped-panel", []
    u = f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}"
    r = subprocess.run(["curl", "-sS", "--fail", "-m", "120", u], capture_output=True)   # in memory: no disk cache
    if r.returncode: return j, "grade=fetch-failed", []
    s, iss = C.grade(r.stdout.decode("utf-8", "replace"))
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
RANK = ["needs-cleanup", "cpl-ready", "parts-mpn", "parts-lcsc"]
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
