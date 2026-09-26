#!/usr/bin/env python3
"""Bulk-run helper 1/2: next N todo module dirs -> compact review cards + prefilled drafts.

  python3 data/cards.py N            # prints cards, writes data/drafts/current.json

Mechanical columns are drafted from the prefetch (components-out.tsv, readme-extracts/,
trees/, inventory.tsv): sha, date, link, components/*, layout, schematic, license (+basis),
bom, detector_version. Judgment columns (module_name, type, creator, notes) are drafted
only as hints; data/commit_chunk.py applies the reviewer's decisions on top.
Skips dirs already in modules.tsv, skips.tsv or needs-ruling.tsv.
"""
import csv, json, os, re, subprocess, sys
from collections import Counter
from datetime import datetime
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15
csv.field_size_limit(10**8)

def tsv(name, quoting=csv.QUOTE_MINIMAL):
    p = os.path.join(HERE, name)
    return list(csv.DictReader(open(p, encoding="utf-8", newline=""), delimiter="\t", quoting=quoting)) if os.path.exists(p) else []

inv = {}
for l in open(os.path.join(HERE, "inventory.tsv"), encoding="utf-8"):
    f = l.rstrip("\r\n").split("\t")
    if len(f) >= 7 and f[1] != "repo":
        inv[f[1]] = {"desc": f[2], "updated": f[4], "sha": f[5], "branch": f[6]}

def month(s):
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%B %d, %Y"):
        try: return datetime.strptime(s.strip(), fmt).strftime("%Y-%m")
        except ValueError: pass
    m = re.search(r"(\d{4})-(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}" if m else ""

have = {(r["repo"], r["module_dir"]) for r in tsv("modules.tsv")}
have |= {(r["repo"], r["module_dir"]) for r in tsv("skips.tsv")}
have |= {(r["repo"], r["module_dir"]) for r in tsv("needs-ruling.tsv")}
have |= {(r["repo"], r["module_dir"]) for r in tsv("deferred.tsv")}   # collections etc., for a later pass
comp = {}
for r in tsv("components-out.tsv", csv.QUOTE_NONE):
    comp[(r["repo"], r["module_scope"].split(" [")[0] or ".")] = r
mb = {(r["repo"], r["module_scope"].split(" [")[0] or "."): r["guess"] for r in tsv("multiboard.tsv", csv.QUOTE_NONE)}

KEYS = os.environ.get("KEYS")          # deferred pass: "owner/repo|module_dir" per line in this file
if KEYS:
    want = [tuple(l.rstrip("\n").split("|", 1)) for l in open(KEYS, encoding="utf-8") if "|" in l]
    rl = {(r["repo"], r["module_dir"]): r for r in tsv("runlist.tsv", csv.QUOTE_NONE)}
    todo = [rl.get(k) or {"repo": k[0], "module_dir": k[1], "tier": "4", "status": "todo"} for k in want]
    N = len(todo)
else:
    todo = [r for r in tsv("runlist.tsv", csv.QUOTE_NONE) if r["status"] == "todo" and (r["repo"], r["module_dir"]) not in have]
if not KEYS: todo.sort(key=lambda r: (int(r["tier"]), r["repo"], r["module_dir"]))
pick = todo[:N]

trees = {}
def tree(repo):
    if repo not in trees:
        p = os.path.join(HERE, "trees", repo.replace("/", "_") + ".txt")
        trees[repo] = open(p, encoding="utf-8").read().splitlines() if os.path.exists(p) else []
    return trees[repo]

def extract(repo, d):
    key = repo.replace("/", "_")
    cands = [f"{key}.txt"] if d == "." else [f"{key}@{d.replace('/', '_').replace(' ', '_')}.txt"]
    if d == ".":
        cands += sorted(x for x in os.listdir(os.path.join(HERE, "readme-extracts")) if x.startswith(key + "@"))
    for c in cands:
        p = os.path.join(HERE, "readme-extracts", c)
        if os.path.exists(p):
            return open(p, encoding="utf-8", errors="replace").read().replace("\x00", "")
    return ""

def sections(text):
    out, cur = {}, None
    for l in text.splitlines():
        m = re.match(r"^(===|---) (.*?)(?: ===| ---)?$", l)
        if m and (l.startswith("=== ") or l.startswith("--- ")):
            cur = m.group(2).split(":")[0].strip(); out.setdefault(cur, [])
            if ":" in m.group(2): out[cur].append("@" + m.group(2).split(":", 1)[1].strip())
            continue
        if cur: out[cur].append(l)
    return out

LIC = [
    (r"CERN[- ]OHL[- ]?S", "CERN-OHL-S v2"), (r"CERN[- ]OHL[- ]?W", "CERN-OHL-W v2"), (r"CERN[- ]OHL[- ]?P", "CERN-OHL-P v2"),
    (r"CERN[- ]OHL", "CERN-OHL"),
    (r"NonCommercial[- ]ShareAlike 4\.0|by-nc-sa[/ -]?4|CC[- ]BY[- ]NC[- ]SA[- ]4", "CC BY-NC-SA 4.0"),
    (r"NonCommercial[- ]ShareAlike 3\.0|by-nc-sa[/ -]?3|CC[- ]BY[- ]NC[- ]SA[- ]3", "CC BY-NC-SA 3.0"),
    (r"Attribution[- ]ShareAlike 4\.0|by-sa[/ -]?4|CC[- ]BY[- ]SA[- ]4", "CC BY-SA 4.0"),
    (r"Attribution[- ]ShareAlike 3\.0|by-sa[/ -]?3|CC[- ]BY[- ]SA[- ]3", "CC BY-SA 3.0"),
    (r"NonCommercial 4\.0|by-nc[/ -]4|CC[- ]BY[- ]NC[- ]4", "CC BY-NC 4.0"),
    (r"CC0|Creative Commons Zero|publicdomain/zero", "CC0"),
    (r"Attribution 4\.0|licenses/by/4|CC[- ]BY[- ]4", "CC BY 4.0"),
    (r"Affero", "AGPL v3"), (r"LESSER GENERAL PUBLIC|LGPL", "LGPL"),
    (r"GENERAL PUBLIC LICENSE\s*\n?\s*Version 3|GPL[- ]?v?3|GPL-3|GNU GPL v3", "GPL v3"),
    (r"GENERAL PUBLIC LICENSE\s*\n?\s*Version 2|GPL[- ]?v?2|GPL-2", "GPL v2"),
    (r"MIT License|Permission is hereby granted, free of charge|\bMIT\b", "MIT"),
    (r"Apache License|Apache[- ]2", "Apache 2.0"), (r"TAPR", "TAPR OHL"),
    (r"BSD", "BSD"), (r"Unlicense", "Unlicense"), (r"Mozilla Public|\bMPL\b", "MPL 2.0"),
    (r"GNU GENERAL PUBLIC|GPL", "GPL"),
]
def license_of(sec):
    lic = [l for l in sec.get("LICENSE", []) if l.strip() and not l.startswith("@")]
    src = next((l[1:] for l in sec.get("LICENSE", []) if l.startswith("@")), "LICENSE")
    if re.search(r"(^|/)(lib|libs|libraries|vendor|third[_-]?party|external|node_modules|drivers|cmsis|middlewares)/", src, re.I):
        lic = []                                   # a vendored library's LICENSE says nothing about the module
    body = "\n".join(lic[:25])
    for rx, name in LIC:
        m = re.search(rx, body, re.I)
        if m:
            line = next((l for l in lic if re.search(rx, l, re.I)), m.group(0)).strip()
            return name, f'{src} "{line[:90]}"'
    readme = [l for l in sec.get("README", []) if re.search(r"licen[cs]", l, re.I)]
    for l in readme:
        for rx, name in LIC:
            if re.search(rx, l, re.I):
                return name, f'README "{re.sub(r"^[0-9]+:", "", l).strip()[:90]}"'
    return "", "no LICENSE file, no README statement" if not lic and not readme else "unclear - see card"

SCH = re.compile(r"(sch|schem|circuit)[^/]*\.(pdf|png|jpe?g|svg)$", re.I)
EDA = re.compile(r"\.(kicad_pcb|kicad_sch|kicad_pro|pro|sch|brd|dch|dip|fzz|json|epro)$", re.I)
GERB = re.compile(r"gerber|\.(gbr|gtl|gbl|gko|gm1|drl)$|(gerb|fab|pcb|jlc|seeed|pcbway|oshpark|board|panel)[^/]*\.zip$", re.I)
BOMF = re.compile(r"(bom|parts[ _-]?list|stückliste)[^/]*\.(csv|tsv|txt|md|xlsx?|ods|pdf|html?)$|ibom[^/]*\.html?$", re.I)

def latest(paths):
    if len(paths) < 2: return paths[0] if paths else ""
    out = subprocess.run(["python3", os.path.join(HERE, "latest_files.py")], input="\n".join(paths),
                         capture_output=True, text=True).stdout.splitlines()
    keep = [l for l in out if l and not l.startswith("#SUP")]
    pdf = [p for p in keep if p.lower().endswith(".pdf")]
    return (pdf or keep or paths)[0]

drafts = []
for i, r in enumerate(pick):
    repo, d = r["repo"], r["module_dir"]
    iv = inv.get(repo, {}); br = iv.get("branch", "main")
    files = [p for p in tree(repo) if d == "." or p.startswith(d + "/")]
    ext = Counter(os.path.splitext(p)[1].lower().lstrip(".") or "-" for p in files)
    c = comp.get((repo, d), {})
    sec = sections(extract(repo, d))
    lic, lic_b = license_of(sec)
    head = [l for l in sec.get("README head", []) if l.strip() and not l.startswith(("![", "[!", "<", "@"))]
    title = next((l.lstrip("# ").strip() for l in head if l.startswith("#")), "")
    fm = [l for l in sec.get("FRONT MATTER", []) if re.match(r"\s*(title|subtitle|draft)\s*:", l)]
    fmt = next((l.split(":", 1)[1].strip().strip("'\"") for l in fm if l.strip().startswith("title")), "")
    name = fmt or title or (os.path.basename(d) if d != "." else repo.split("/")[1])
    schs = [p for p in files if SCH.search(os.path.basename(p))
            or (re.search(r"schem", os.path.dirname(p), re.I) and re.search(r"\.(pdf|png|jpe?g|svg)$", p, re.I))]
    schs = [p for p in schs if not re.search(r"bom|parts|layout|placement|panel|silk", os.path.basename(p), re.I)]
    src = (c.get("comp_basis", "").split(" ") or [""])[0]
    has_eda = any(EDA.search(p) for p in files if not p.lower().endswith(".json")) or src in ("easyeda", "kicad", "eagle")
    sch = f"https://github.com/{repo}/blob/{br}/{quote(latest(schs), safe='/')}" if schs else ("x" if has_eda else "")
    lay = []
    if src == "kicad" or ext["kicad_pcb"] or ext["kicad_sch"] or ext["kicad_pro"]: lay.append("kicad")
    elif src == "eagle" or (ext["brd"] and not ext["pro"]): lay.append("eagle")
    elif ext["sch"] and ext["pro"]: lay.append("kicad")
    if src == "easyeda" or ext["epro"]: lay.append("easyEDA")
    if ext["dip"] or ext["dch"]: lay.append("diptrace")
    if ext["fzz"]: lay.append("fritzing")
    if any(GERB.search(p) for p in files): lay.append("gerbers")
    bomf = [p for p in files if BOMF.search(os.path.basename(p))]
    link = f"https://github.com/{repo}" if d == "." else f"https://github.com/{repo}/tree/{br}/{quote(d, safe='/')}"
    drafts.append({
        "k": i + 1, "repo": repo, "sha": iv.get("sha", ""), "date": month(iv.get("updated", "")), "module_dir": d,
        "creator": repo.split("/")[0], "module_name": name, "type": "", "license": lic, "schematic": sch,
        "layout": " + ".join(lay), "components": c.get("components", ""), "link": link, "notes": "",
        "comp_conf": c.get("comp_conf", "Deferred"), "comp_basis": c.get("comp_basis", "not prefetched"),
        "type_basis": "", "creator_basis": "GitHub owner (no brand name in repo)", "license_basis": lic_b,
        "bom": "y" if bomf else "-", "followup": "", "detector_version": c.get("detector_version", ""),
    })
    # ---- card ----
    cb = c.get("comp_basis", "")
    tally = re.search(r"smd=(\d+) tht_passive=(\d+) tht_to=(\d+) tht_ic=(\d+)", cb)
    extra = " ".join(re.findall(r"\[(?:superseded|unclassified|no package)[^\]]*\]", cb))[:120]
    top = ", ".join(f"{k}={v}" for k, v in ext.most_common(7))
    print(f"[{i+1}] {repo} | {d} | t{r['tier']} | {c.get('components') or '-'} {c.get('comp_conf','')} {src}"
          + (f" s{tally.group(1)}/p{tally.group(2)}/to{tally.group(3)}/ic{tally.group(4)}" if tally else "")
          + (f" | MB:{mb[(repo, d)]}" if (repo, d) in mb else "") + (f" {extra}" if extra else ""))
    print(f"   files({len(files)}): {top}")
    same = drafts and len(drafts) > 1 and drafts[-2]["repo"] == repo
    if iv.get("desc") and not same: print(f"   desc: {iv['desc'][:150]}")
    print(f"   title: {title[:80]}" + (f" | fm: {'; '.join(x.strip() for x in fm)[:90]}" if fm else ""))
    hl = [x for x in head if not x.startswith("#")][:2]
    if same and hl == getattr(sys.modules[__name__], "_prevhead", None): hl = []
    else: sys.modules[__name__]._prevhead = hl
    for l in hl: print(f"   head: {l.strip()[:150]}")
    print(f"   lic: {lic or '-'} <- {lic_b[:110]}")
    br_sig = [l for l in sec.get("brand/creator signals", []) if l.strip()][:2]
    for l in ([] if same else br_sig): print(f"   brand: {re.sub(r'^[0-9]+:', '', l).strip()[:140]}")
    print(f"   sch: {sch.split('/blob/'+br+'/')[-1][:80] if sch.startswith('http') else sch or '-'}"
          + (f" (of {len(schs)})" if len(schs) > 1 else "") + f" | layout: {' + '.join(lay) or '-'} | bom: {len(bomf)}")
os.makedirs(os.path.join(HERE, "drafts"), exist_ok=True)
json.dump(drafts, open(os.path.join(HERE, "drafts", "current.json"), "w"), indent=0, ensure_ascii=False)
print(f"-- {len(drafts)} drafted; {len(todo) - len(drafts)} todo left after this chunk")
