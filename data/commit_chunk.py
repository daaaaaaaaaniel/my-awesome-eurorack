#!/usr/bin/env python3
"""Bulk-run helper 2/2: apply review decisions to the drafts from data/cards.py.

  python3 data/commit_chunk.py data/drafts/decisions.jsonl

One JSON object per line, keyed by the card number "k":
  {"k":1, "do":"row", "type":"VCO", "type_basis":"README ...", <any draft column to override>}
  {"k":1, "do":"row", "filter":"_SMD", "module_name":"X (SMD)", ...}   # split: re-runs components.sh
  {"k":2, "do":"skip", "reason":"firmware only, no hardware"}          # -> data/skips.tsv
  {"k":3, "do":"ruling", "q":"IN or OUT?", "evidence":"..."}             # -> data/needs-ruling.tsv
A card with no decision line is left for the next chunk. Rows get the next free p-ids.
"""
import csv, json, os, re, subprocess, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
csv.field_size_limit(10**8)
drafts = {d["k"]: d for d in json.load(open(os.path.join(HERE, "drafts", "current.json")))}
dec = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]

from urllib.parse import quote
branch = {}
for l in open(os.path.join(HERE, "inventory.tsv"), encoding="utf-8"):
    f = l.rstrip("\r\n").split("\t")
    if len(f) >= 7: branch[f[1]] = f[6]
mp = os.path.join(HERE, "modules.tsv")
with open(mp, encoding="utf-8", newline="") as f:
    rd = csv.DictReader(f, delimiter="\t"); cols = rd.fieldnames; mods = list(rd)
nid = max(int(m["id"][1:]) for m in mods if re.fullmatch(r"p\d+", m["id"])) + 1

def comp_for(repo, d, filt):
    line = f"{repo}\t{d}\t{filt}\n"
    out = subprocess.run(["bash", os.path.join(HERE, "components.sh")], input=line, capture_output=True, text=True, timeout=150).stdout
    f = (out.strip().splitlines() or [""])[-1].split("\t")
    return {"components": f[2], "comp_basis": f[3], "comp_conf": f[4], "detector_version": f[5]} if len(f) >= 6 else None

new, skips, rulings, defers, bad = [], [], [], [], []
for x in dec:
    d = drafts.get(x["k"])
    if not d: bad.append(f"k={x['k']}: no such card"); continue
    if x["do"] == "skip":
        skips.append([d["repo"], d["module_dir"], x["reason"]]); continue
    if x["do"] == "defer":
        defers.append([d["repo"], d["module_dir"], x["reason"]]); continue
    if x["do"] == "ruling":
        rulings.append([d["repo"], d["module_dir"], x["q"], x.get("evidence", d["link"]), date.today().isoformat()]); continue
    row = {c: "" for c in cols}
    row.update({k: v for k, v in d.items() if k in cols})
    if x.get("filter"):
        c = comp_for(d["repo"], x.get("module_dir", d["module_dir"]), x["filter"])
        if not c: bad.append(f"k={x['k']}: components.sh gave nothing for filter {x['filter']}"); continue
        row.update(c)
    if x.get("pool"):                                   # sub-boards in sibling folders -> one count
        tot, files, ver = dict.fromkeys(("smd", "tht_passive", "tht_to", "tht_ic", "smd_ic"), 0), [], ""
        for pd in x["pool"]:
            c = comp_for(d["repo"], pd, "")
            m = c and re.search(r"files=\d+: (.*?)\): smd=", c["comp_basis"])
            if not m: bad.append(f"k={x['k']}: pool dir {pd} gave no counted files"); break
            files += m.group(1).split(", "); ver = c["detector_version"]; src = c["comp_basis"].split(" ")[0]
            for k in tot: tot[k] += int(re.search(k + r"=(\d+)", c["comp_basis"]).group(1))
        else:
            v = ("both" if tot["tht_ic"] or tot["tht_passive"] > 5 else "SMD") if tot["smd"] else ("THT" if any(tot[k] for k in ("tht_passive", "tht_to", "tht_ic")) else "")
            row.update(components=v, comp_conf="Strong" if src in ("kicad", "eagle", "easyeda") else "Stated", detector_version=ver,
                       comp_basis=f"{src} {'footprints' if src == 'kicad' else 'packages' if src == 'eagle' else 'parts'} (files={len(files)}: {', '.join(files)}): "
                                  f"smd={tot['smd']} tht_passive={tot['tht_passive']} tht_to={tot['tht_to']} tht_ic={tot['tht_ic']} (panel excluded) smd_ic={tot['smd_ic']}")
    row.update({k: v for k, v in x.items() if k in cols})
    if "module_dir" in x and "link" not in x and x["module_dir"] not in (".", ""):   # moved row -> link its folder
        import urllib.parse
        br = next((l.rstrip("\r\n").split("\t")[6] for l in open(os.path.join(HERE, "inventory.tsv"), encoding="utf-8") if l.split("\t")[1:2] == [d["repo"]]), "HEAD")
        row["link"] = f"https://github.com/{d['repo']}/tree/{br}/" + urllib.parse.quote(x["module_dir"])
    if row["schematic"].startswith("path:"):
        row["schematic"] = f"https://github.com/{d['repo']}/blob/{branch[d['repo']]}/{quote(row['schematic'][5:], safe='/')}"
    for need in ("module_name", "type", "type_basis", "creator"):
        if not row[need].strip(): bad.append(f"k={x['k']}: {need} empty")
    row["id"] = f"p{nid}"; nid += 1
    new.append(row)
if bad:
    print("NOT APPLIED:\n  " + "\n  ".join(bad)); sys.exit(1)
# Panel and photo columns (d 2026-09-26 16:52): filled for every new row by panel_photos.py
if new and "panel" in cols:
    inp = "".join(f"{r['id']}\t{r['repo']}\t{r.get('module_dir') or '.'}\n" for r in new)
    pp = subprocess.run(["python3", os.path.join(HERE, "panel_photos.py")], input=inp, capture_output=True, text=True, timeout=900).stdout
    got = {l.split("\t")[0]: l.rstrip("\n").split("\t") for l in pp.splitlines() if l.strip()}
    for r in new:
        o = got.get(r["id"])
        if o: r["panel"], r["panel_basis"], r["photos"], r["photos_basis"] = (v.replace('"', "'") for v in o[1:5])
with open(mp, "a", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, delimiter="\t", lineterminator="\n"); w.writerows(new)
for name, rows, hdr in (("skips.tsv", skips, "repo\tmodule_dir\treason\n"),
                        ("needs-ruling.tsv", rulings, "repo\tmodule_dir\tquestion\tevidence\tdate\n"),
                        ("deferred.tsv", defers, "repo\tmodule_dir\treason\n")):
    if not rows: continue
    p = os.path.join(HERE, name)
    if not os.path.exists(p): open(p, "w").write(hdr)
    with open(p, "a", encoding="utf-8", newline="") as f:
        for r in rows: f.write("\t".join(v.replace("\t", " ").replace("\n", " ") for v in r) + "\n")
# a decided key leaves the deferred list (rows, skips, rulings; a new defer keeps it)
done = {(r[0], r[1]) for r in skips + rulings} | {(r["repo"], r["module_dir"]) for r in new} | {(drafts[x["k"]]["repo"], drafts[x["k"]]["module_dir"]) for x in dec if x["do"] == "row"}
dp = os.path.join(HERE, "deferred.tsv")
if os.path.exists(dp):
    L = open(dp, encoding="utf-8").read().splitlines()
    keep = [L[0]] + [l for l in L[1:] if tuple(l.split("\t")[:2]) not in done or any(tuple(d[:2]) == tuple(l.split("\t")[:2]) for d in defers)]
    last = {tuple(l.split("\t")[:2]): i for i, l in enumerate(keep)}          # a re-defer replaces the old reason
    keep = [l for i, l in enumerate(keep) if i == 0 or last[tuple(l.split("\t")[:2])] == i]
    if len(keep) != len(L): open(dp, "w", encoding="utf-8").write("\n".join(keep) + "\n")
subprocess.run(["python3", os.path.join(HERE, "runlist.py")], capture_output=True)
print(f"rows +{len(new)} ({new[0]['id']}..{new[-1]['id']})" if new else "rows +0", f"| skips +{len(skips)} | rulings +{len(rulings)} | deferred +{len(defers)}")
