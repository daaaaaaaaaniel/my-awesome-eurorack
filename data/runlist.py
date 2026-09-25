#!/usr/bin/env python3
"""Build data/runlist.tsv - the work queue for the bulk run (Phase 3).

One line per (repo, module_dir) of every IN repo, in the order to work them:
  tier 1  single-module repos           (one row each, cheapest, most numerous)
  tier 2  collections of 2-5 module dirs
  tier 3  collections of 6-20
  tier 4  collections of >20            (half of all module dirs; do last, per repo)
Zipped / document-only repos that detect 0 dirs appear once with module_dir "." so
nothing is dropped. `status` is derived, never typed:
  done   (repo, module_dir) already has a row in data/modules.tsv
  todo   everything else
`boards` (from flat_boards.py logic) counts board files under the dir, panels excluded:
>1 means the dir may hold several modules or variants - split before writing rows.

Rebuild after every batch: python3 data/runlist.py   (idempotent; status refreshes)
"""
import csv, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "runlist.tsv")
BOARD = re.compile(r"\.(kicad_pcb|brd|pcbdoc|dip|fzz|pcb)$", re.I)
PANEL = re.compile(r"panel|faceplate|frontplate|front_plate|fp$", re.I)


def stem(p):
    return re.sub(r"\.[^.]+$", "", p.rsplit("/", 1)[-1]).lower()


with open(os.path.join(HERE, "triage.tsv"), newline="") as f:
    repos = [r["repo"] for r in csv.DictReader(f, delimiter="\t") if r["bucket"] == "IN"]
with open(os.path.join(HERE, "modules.tsv"), newline="") as f:
    done = {(m["repo"], m["module_dir"]) for m in csv.DictReader(f, delimiter="\t")}

rows = []
for r in repos:
    key = r.replace("/", "_")
    try:
        tree = open(os.path.join(HERE, "trees", f"{key}.txt")).read().splitlines()
    except FileNotFoundError:
        tree = []
    out = subprocess.run(["bash", os.path.join(HERE, "moduledirs.sh"), r],
                         capture_output=True, text=True).stdout
    dirs = [l.split(maxsplit=1)[1] for l in out.splitlines() if l.strip() and l.strip() != "NO_TREE"]
    if not dirs:
        dirs = ["."]
    n = len(dirs)
    tier = 1 if n == 1 else 2 if n <= 5 else 3 if n <= 20 else 4
    for d in dirs:
        pre = "" if d == "." else d + "/"
        boards = {stem(p) for p in tree if p.startswith(pre) and BOARD.search(p) and not PANEL.search(stem(p))}
        # a zipped repo's rows use the zip name as module_dir (erica-synths): count those done
        # done if this dir has a row, a row's module_dir is a parent of it (a row written
        # at module level covers its per-board sub-dirs), or the repo was done as zips
        st = "todo"
        if (r, d) in done or any(rr == r and m != "." and d.startswith(m + "/") for rr, m in done):
            st = "done"
        elif d == "." and any(rr == r and m.endswith(".zip") for rr, m in done):
            st = "done"
        rows.append((tier, r, d, n, len(boards), st))

rows.sort(key=lambda x: (x[0], x[1].lower(), x[2]))
with open(OUT, "w", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["tier", "repo", "module_dir", "dirs_in_repo", "boards", "status"])
    w.writerows(rows)
todo = sum(1 for x in rows if x[5] == "todo")
print(f"wrote {OUT}: {len(rows)} module dirs in {len(repos)} IN repos; todo {todo}, done {len(rows)-todo}; "
      + ", ".join(f"tier {t}: {sum(1 for x in rows if x[0]==t)}" for t in (1, 2, 3, 4)))
