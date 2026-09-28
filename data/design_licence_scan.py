#!/usr/bin/env python3
"""Licence statements inside a module's own design files (d, 2026-09-28 21:33: the elektrophon schematics say
"License CC BY 4.0 - Attribution 4.0 International" in the title block).

  python3 data/design_licence_scan.py < jobs.tsv > hits.tsv     jobs.tsv: id<TAB>repo<TAB>sha<TAB>file[;file...]
  hits.tsv: id, licence text(s) found (" || "-joined), files they were found in

Fetches each KiCad (.kicad_sch/.kicad_pcb/.sch), Eagle (.sch/.brd) or EasyEDA (.json) file at the pinned SHA and keeps
only text the DESIGNER places: KiCad title-block comments / title / company, schematic text and board gr_text /
fp_text user, Eagle <text> elements, EasyEDA TEXT items. Licence text inside part libraries (Eagle <description>,
SparkFun "Licensing: Creative Commons") and "Open Source Hardware" logo footprints are NOT licences and are ignored.
First run 2026-09-28 over the 220 blank-licence rows with design files (3,333 files): 36 rows -> data/design-licences.tsv."""
import concurrent.futures as cf, re, subprocess, sys, urllib.parse
PAT = re.compile(r'licen[cs]e|creative ?commons|\bCC[- _]?BY|\bCC0\b|CERN[- ]?OHL|\bOHL[- ]|\bGPL|\bLGPL|\bMIT\b|TAPR|solderpad|public domain|copyleft|open[- ]?source hardware|\bOSHW', re.I)
PLACED = re.compile(r'\(comment \d+ "([^"]*)"|Comment\d+ "([^"]*)"|\(gr_text "([^"]*)"|\(fp_text user "([^"]*)"|\(text "([^"]*)"|<text [^>]*>([^<]*)<|\(company "([^"]*)"|Comp "([^"]*)"|\(title "([^"]*)"|Title "([^"]*)"|"text"\s*:\s*"([^"]*)"|>([^<>]*)</text>|TEXT~(?:[^~]*~){9}([^~]*)~|rot="[^"]*">([^<>]{20,})$')
LIC = re.compile(r'licen[cs]e|creative ?commons|CC[- _]?BY|\bCC0\b|CERN|\bOHL|\bGPL|\bMIT\b|TAPR|solderpad|public domain|copyleft|OSHW|open.?source', re.I)

def hits(repo, sha, f):
    r = subprocess.run(["curl", "-sS", "-m", "90", "--fail", "https://raw.githubusercontent.com/%s/%s/%s" % (repo, sha, urllib.parse.quote(f))], capture_output=True)
    if r.returncode: return None
    t = r.stdout.decode("utf-8", "replace"); out = []
    for m in PAT.finditer(t):
        s = t[max(0, m.start() - 80): m.end() + 100].replace("\n", " ").replace("\r", " ").replace("\t", " ")
        for p in PLACED.finditer(s):
            txt = next(g for g in p.groups() if g is not None).strip()
            if LIC.search(txt) and txt not in out: out.append(txt)
    return out

def row(job):
    rid, repo, sha, fs = job
    found = {}
    for f in fs.split(";"):
        for txt in hits(repo, sha, f) or []: found.setdefault(txt, []).append(f)
    return rid, found

if __name__ == "__main__":
    jobs = [l.rstrip("\n").split("\t")[:4] for l in sys.stdin if l.strip()]
    with cf.ThreadPoolExecutor(16) as ex:
        for rid, found in ex.map(row, jobs):
            if found:
                files = list(dict.fromkeys(f for v in found.values() for f in v))
                print(rid + "\t" + " || ".join(found) + "\t" + "; ".join(files), flush=True)
