#!/usr/bin/env python3
"""List module dirs that hold MORE THAN ONE board file (panels excluded).

moduledirs.sh splits modules by directory, so a folder holding several boards
(GroundGrown/eurorack-modules: 72 Eagle .brd in the repo root; Avalon CVMod8_V2: SMD and
THT .kicad_pcb together) is seen as one module - and components.sh would pool every board
into one verdict, the failure CLAUDE.md already paid for once. These dirs need a
per-board file_filter (components.sh's 3rd input column) or a manual split.

usage: python3 data/flat_boards.py [owner/repo ...]     (default: every IN repo)
output TSV: repo, module_dir, n_boards, board basenames

Many hits are one module on several boards (main + ctrl) - fine to pool. The ones to
split are distinct modules (vca, vcf, lfo) and build variants (_SMD / _THT, rev1 / rev2).
"""
import csv, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = re.compile(r"\.(kicad_pcb|brd|pcbdoc|dip|fzz|pcb)$", re.I)
# a panel / faceplate board is part of the same module, not another board
PANEL = re.compile(r"panel|faceplate|frontplate|front_plate|fp$", re.I)


def stem(p):
    return re.sub(r"\.[^.]+$", "", p.rsplit("/", 1)[-1]).lower()


def main(repos):
    if not repos:
        with open(os.path.join(HERE, "triage.tsv"), newline="") as f:
            repos = [r["repo"] for r in csv.DictReader(f, delimiter="\t") if r["bucket"] == "IN"]
    print("repo\tmodule_dir\tn_boards\tboards", end="\n")
    for r in repos:
        key = r.replace("/", "_")
        try:
            tree = open(os.path.join(HERE, "trees", f"{key}.txt")).read().splitlines()
        except FileNotFoundError:
            continue
        out = subprocess.run(["bash", os.path.join(HERE, "moduledirs.sh"), r],
                             capture_output=True, text=True).stdout
        dirs = [l.split(maxsplit=1)[1] for l in out.splitlines() if l.strip()]
        for d in dirs:
            pre = "" if d == "." else d + "/"
            # anywhere under the module dir: part folders (kicad/, hardware/) belong to it
            boards = sorted({stem(p) for p in tree
                             if p.startswith(pre) and BOARD.search(p) and not PANEL.search(stem(p))})
            if len(boards) > 1:
                print(f"{r}\t{d}\t{len(boards)}\t{', '.join(boards)}")


if __name__ == "__main__":
    main(sys.argv[1:])
