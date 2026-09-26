"""What evidence sits in the folders the detector left blank? (prep for Pass B)

  python3 data/blanks.py   -> data/blanks.tsv (+ counts on stdout)

For every components-out.tsv row with an empty verdict, list the file kinds in that module
scope (data/trees, recursive under module_dir) and name the best remaining evidence, in order:
  xlsx/ods BOM, PDF/HTML/md BOM, Eagle .sch, KiCad schematic, Fritzing, gerber/zip only,
  schematic PDF/image only, nothing hardware.
"""
import csv, os, re
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
K = [  # (kind, regex on path) - first match in this order is the "best evidence"
 ("bom-spreadsheet", r"(bom|parts|stückliste)[^/]*\.(xlsx?|ods|numbers)$"),
 ("bom-doc",         r"(bom|parts|stückliste)[^/]*\.(pdf|html?|md|txt|rtf|docx?)$"),
 ("ibom-html",       r"ibom[^/]*\.html?$|interactive.?bom"),
 ("eagle-sch",       r"\.sch$"),
 ("kicad-sch",       r"\.kicad_sch$"),
 ("fritzing",        r"\.fzz?$"),
 ("easyeda-other",   r"\.(epro|eprj)$"),
 ("gerber/zip",      r"\.(zip|gbr|gtl|gbl|gko|gm1|drl)$|gerber"),
 ("schematic-pdf/img", r"(sch|schematic|circuit)[^/]*\.(pdf|png|jpe?g|gif|svg)$"),
 ("other-pdf",       r"\.pdf$"),
]
trees = {}
def tree(repo):
    if repo not in trees:
        f = os.path.join(HERE, "trees", repo.replace("/", "_") + ".txt")
        trees[repo] = open(f, encoding="utf-8").read().splitlines() if os.path.exists(f) else []
    return trees[repo]
out, best = [], Counter()
for r in csv.DictReader(open(os.path.join(HERE, "components-out.tsv")), delimiter="\t", quoting=csv.QUOTE_NONE):
    if r["components"]: continue
    d = r["module_scope"].split(" [")[0]
    files = [p for p in tree(r["repo"]) if d in (".", "") or p.startswith(d + "/")]
    kinds = Counter()
    for p in files:
        for k, rx in K:
            if re.search(rx, p, re.I): kinds[k] += 1; break
    empty = "held no footprints" in r["comp_basis"]
    b = next((k for k, _ in K if kinds[k]), "nothing hardware")
    if empty and b in ("gerber/zip", "schematic-pdf/img", "other-pdf", "nothing hardware", "kicad-sch"):
        b = "empty-kicad-board" if b in ("nothing hardware", "kicad-sch") else b
    best[b] += 1
    out.append([r["repo"], r["module_scope"], b, " ".join(f"{k}={v}" for k, v in kinds.most_common()), str(len(files))])
out.sort(key=lambda x: ([k for k, _ in K] + ["empty-kicad-board", "nothing hardware"]).index(x[2]) if x[2] in [k for k, _ in K] + ["empty-kicad-board", "nothing hardware"] else 99)
with open(os.path.join(HERE, "blanks.tsv"), "w") as fh:
    fh.write("repo\tmodule_scope\tbest_evidence\tfile_kinds\tfiles_in_scope\n")
    for x in out: fh.write("\t".join(x) + "\n")
print(len(out), "blank rows"); [print(f"  {k}: {v}") for k, v in best.most_common()]
