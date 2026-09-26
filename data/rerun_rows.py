#!/usr/bin/env python3
"""Re-run components.sh over every detector-derived row of data/modules.tsv at the current
DETECTOR_VERSION, pinned to the files each row recorded (files=N: a, b -> filter), keeping any
hand-written suffix after the tally. Writes a report; applies changes only with --apply."""
import csv, os, re, subprocess, sys
APPLY = "--apply" in sys.argv
p = "data/modules.tsv"; raw = open(p, newline="").read(); NL = "\r\n" if "\r\n" in raw else "\n"; L = raw.split(NL)
h = L[0].split("\t"); ix = {k: h.index(k) for k in h}
DV = open("data/generate.py").read().split('DETECTOR_VERSION = "')[1].split('"')[0]
DET = re.compile(r"^(kicad footprints|BOM[ (]|easyeda|eagle|no \.kicad_pcb|fetch failed|\d+ \.kicad_pcb fetched)")
TALLY = re.compile(r"smd_ic=\d+")
jobs = []
for n, l in enumerate(L[1:], 1):
    if not l: continue
    f = l.split("\t"); b = f[ix["comp_basis"]]
    if not DET.match(b): continue
    fm = re.search(r"\(files=\d+: ([^)]*)\)", b)
    # pin to the recorded files only for rows split by hand from one folder (their name says
    # which build); otherwise re-run unpinned so new sources (e.g. Eagle, v15) are seen
    split = re.search(r"\((SMD|THT)\)$", f[ix["module_name"]]) and fm
    filt = "|".join(re.escape(x.strip()) + "$" for x in fm.group(1).split(",")) if split else ""
    md = f[ix["module_dir"]] or "."   # never an empty field: bash read collapses empty TSV fields
    jobs.append((n, f[ix["repo"]], md, filt, b))
inp = "".join(f"{r}\t{md}\t{flt}\n" for _, r, md, flt, _ in jobs)
out = subprocess.run(["bash", "data/components.sh"], input=inp, capture_output=True, text=True).stdout.splitlines()
assert len(out) == len(jobs), (len(out), len(jobs))
changed = 0; rep = []
for (n, r, md, flt, oldb), o in zip(jobs, out):
    c = o.split("\t"); f = L[n].split("\t")
    suf = ""
    m = TALLY.search(oldb)
    if m: suf = oldb[m.end():]
    newb = c[3] + (suf if suf and not TALLY.search(suf) else "")
    if (f[ix["components"]], f[ix["comp_conf"]]) != (c[2], c[4]):
        changed += 1; rep.append(f"CHANGED {f[ix['id']]} {r} [{md or '.'}]: {f[ix['components']] or '-'}/{f[ix['comp_conf']]} -> {c[2] or '-'}/{c[4]} | {c[3][:160]}")
    elif "superseded" in c[3] or "eagle brd" in c[3]:
        rep.append(f"same    {f[ix['id']]} {r}: {c[3][:160]}")
    f[ix["components"]], f[ix["comp_conf"]], f[ix["comp_basis"]] = c[2], c[4], newb
    L[n] = "\t".join(f)
L = [L[0]] + ["\t".join(x.split("\t")[:ix["detector_version"]] + [DV] + x.split("\t")[ix["detector_version"] + 1:]) if x else x for x in L[1:]]
print(f"rows re-run: {len(jobs)}; verdict/confidence changed: {changed}")
print("\n".join(rep))
if APPLY: open(p, "w", newline="").write(NL.join(L)); print("applied")
