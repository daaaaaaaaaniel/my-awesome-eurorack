#!/usr/bin/env python3
"""Re-run components.sh over every detector-derived row of data/modules.tsv at the current
DETECTOR_VERSION, pinned to the files each row recorded (files=N: a, b -> filter), keeping any
hand-written suffix after the tally. Writes a report; applies changes only with --apply."""
import csv, os, re, subprocess, sys
APPLY = "--apply" in sys.argv
def qsplit(x):
    """split a record on tabs outside double-quoted fields (licence quotes can hold tabs)"""
    out, cur, q = [], [], False
    for ch in x:
        if ch == '"': q = not q
        if ch == "\t" and not q: out.append("".join(cur)); cur = []
        else: cur.append(ch)
    out.append("".join(cur)); return out
p = "data/modules.tsv"; raw = open(p, newline="").read(); NL = "\r\n" if "\r\n" in raw else "\n"
# a quoted field can hold newlines (licence quotes): join physical lines into logical records
L = []
for pl in raw.split(NL):
    if L and L[-1].count('"') % 2: L[-1] += NL + pl   # inside an open quoted field
    else: L.append(pl)
h = L[0].split("\t"); ix = {k: h.index(k) for k in h}
DV = open("data/generate.py").read().split('DETECTOR_VERSION = "')[1].split('"')[0]
DET = re.compile(r"^(kicad footprints|BOM[ (]|easyeda|eagle|no \.kicad_pcb|fetch failed|\d+ \.kicad_pcb fetched)")
TALLY = re.compile(r"smd_ic=\d+")
jobs = []
# --basis=REGEX: re-run only rows whose comp_basis matches (a change confined to one detector
# path cannot move rows decided by another; their detector_version is still bumped below)
BA = [a[8:] for a in sys.argv if a.startswith("--basis=")]
# data/comp_pins.tsv (id, file_filter, basis): rows pinned to named board files by a ruling
PINS = {}
if os.path.exists("data/comp_pins.tsv"):
    for pl in open("data/comp_pins.tsv").read().splitlines()[1:]:
        if pl.strip(): pid, pf = pl.split("\t")[:2]; PINS[pid] = pf
for n, l in enumerate(L[1:], 1):
    if not l: continue
    f = qsplit(l); b = f[ix["comp_basis"]]
    if not DET.match(b): continue
    if BA and not re.match(BA[0], b): continue
    fm = re.search(r"\(files=\d+: (.*?)\): smd=", b) or re.search(r"\(files=\d+: ([^)]*)\)", b)   # names may hold ( ) and ,
    # pin to the recorded files only for rows split by hand from one folder (their name says
    # which build); otherwise re-run unpinned so new sources (e.g. Eagle, v15) are seen
    split = re.search(r"\((SMD|THT)\)$", f[ix["module_name"]]) and fm
    filt = "|".join(re.escape(x.strip()) + "$" for x in fm.group(1).split(",")) if split else ""
    # --pin-all: a change to how files are COUNTED (not which are found) re-runs each row on the
    # files it recorded, counted and superseded alike, so flat-folder board rows keep their scope
    if "--pin-all" in sys.argv and fm:
        sm = re.search(r"\[superseded, not counted: ([^\]]*)\]", b)
        names = fm.group(1).split(", ") + (sm.group(1).split(", ") if sm else [])
        filt = "|".join(re.escape(x.strip()) + "$" for x in names if x.strip())
    filt = PINS.get(f[ix["id"]], filt)
    md = f[ix["module_dir"]] or "."   # never an empty field: bash read collapses empty TSV fields
    jobs.append((n, f[ix["repo"]], md, filt, b))
# --part=i/n: only every n-th job starting at i (a sandboxed shell call has a time limit;
# run the parts one after another, each with --apply)
pa = [a for a in sys.argv if a.startswith("--part=")]
if pa:
    i, n_ = map(int, pa[0][7:].split("/")); jobs = jobs[i::n_]
inp = "".join(f"{r}\t{md}\t{flt}\n" for _, r, md, flt, _ in jobs)
out = subprocess.run(["bash", "data/components.sh"], input=inp, capture_output=True, text=True).stdout.splitlines()
assert len(out) == len(jobs), (len(out), len(jobs))
changed = 0; rep = []
for (n, r, md, flt, oldb), o in zip(jobs, out):
    c = o.split("\t"); f = qsplit(L[n])
    suf = ""
    m = TALLY.search(oldb)
    if m: suf = oldb[m.end():]
    newb = c[3] + (suf if suf and not TALLY.search(suf) else "")
    nf = lambda x: (re.search(r"\(files=(\d+)", x) or [0, "?"])[1]
    if nf(oldb) != nf(c[3]) and f[ix["id"]] not in PINS:
        rep.append(f"FILES   {f[ix['id']]} {r}: files {nf(oldb)} -> {nf(c[3])}")
    if (f[ix["components"]], f[ix["comp_conf"]]) != (c[2], c[4]):
        changed += 1; rep.append(f"CHANGED {f[ix['id']]} {r} [{md or '.'}]: {f[ix['components']] or '-'}/{f[ix['comp_conf']]} -> {c[2] or '-'}/{c[4]} | {c[3][:160]}")
    elif "superseded" in c[3] or "eagle brd" in c[3]:
        rep.append(f"same    {f[ix['id']]} {r}: {c[3][:160]}")
    f[ix["components"]], f[ix["comp_conf"]], f[ix["comp_basis"]] = c[2], c[4], newb
    L[n] = "\t".join(f)
L = [L[0]] + ["\t".join(qsplit(x)[:ix["detector_version"]] + [DV] + qsplit(x)[ix["detector_version"] + 1:]) if x else x for x in L[1:]]
print(f"{pa[0] if pa else 'all'}: rows re-run: {len(jobs)}; verdict/confidence changed: {changed}")
print("\n".join(rep))
if APPLY: open(p, "w", newline="").write(NL.join(L)); print("applied")
