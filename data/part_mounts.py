#!/usr/bin/env python3
"""Part number -> mounting (smd / tht), derived from data/part-observations.tsv (design in STATE.md "Parts table").

  python3 data/part_mounts.py          -> data/part-mounts.tsv

A part's mounting is known only from a pad-bearing source (kicad, eagle, easyeda-pcb, ibom). Its part numbers can sit in
any source of the same board - KiCad keeps them in the schematic, EasyEDA mostly in the schematic JSON - so lines are
joined per row + board + reference, and a number takes the mounting of the parts it was written on. One board counts
once, however many sources describe it. A number seen on SMD and on THT parts is 'conflict', never resolved here.
Supplier numbers (LCSC, Mouser, Digi-Key, Tayda) name one package; bare MPNs often name a family (TL072 is DIP and
SOIC), so their lines are listed with lookup = 'no' until d rules. data/known_parts.tsv (hand rulings) overrides this
file wherever it is used. Nothing here feeds the components verdict yet."""
import collections, csv, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = os.path.join(HERE, "part-observations.tsv"), os.path.join(HERE, "part-mounts.tsv")
PADS = {"kicad", "eagle", "easyeda-pcb", "ibom"}
KINDS = ["lcsc", "mouser", "digikey", "tayda", "mpn"]
L = list(csv.DictReader(open(SRC, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))
mount = {}                                   # (row, board, ref) -> smd/tht, from pad sources
fps = collections.defaultdict(set)           # (row, board, ref) -> footprints as written
for x in L:
    if x["source_type"] in PADS and x["mount"] and x["board"]:
        for r in filter(None, x["refs"].split(",")):
            k = (x["row_id"], x["board"], r)
            if mount.get(k, x["mount"]) != x["mount"]: mount[k] = "conflict"   # two pad sources disagree on one part
            else: mount[k] = x["mount"]
            fps[k].add(x["footprint"])
seen = collections.defaultdict(lambda: collections.defaultdict(set))   # (kind, number) -> mount -> {(row, board)}
ex = {}; fpn = collections.defaultdict(set); unjoined = collections.Counter()
for x in L:
    nums = [(k, n.strip()) for k in KINDS for n in x[k].split(" | ") if n.strip()]
    if not nums: continue
    refs = [r for r in x["refs"].split(",") if r]
    hits = [(r, mount.get((x["row_id"], x["board"], r))) for r in refs] if x["board"] else []
    if x["source_type"] in PADS and x["mount"] and not hits: hits = [("", x["mount"])]   # number written on the pad source itself
    hits = [(r, m) for r, m in hits if m]
    for k, n in nums:
        if not hits: unjoined[k] += 1; continue
        for r, m in hits:
            seen[(k, n)][m].add((x["row_id"], x["board"]))
            ex.setdefault((k, n, m), f"{x['row_id']}:{os.path.basename(x['board'])}:{r}" if r else f"{x['row_id']}:{os.path.basename(x['board'])}")
            fpn[(k, n)] |= fps.get((x["row_id"], x["board"], r), {x["footprint"]} if x["footprint"] else set())
rows = []
for (k, n), ms in seen.items():
    smd, tht = len(ms.get("smd", ())), len(ms.get("tht", ()))
    m = "conflict" if (smd and tht) or ms.get("conflict") else ("smd" if smd else "tht")
    rows.append([k, n, m, str(smd), str(tht), " | ".join(sorted(fpn[(k, n)])[:3]),
                 ex.get((k, n, "smd")) or ex.get((k, n, "tht")) or ex.get((k, n, "conflict"), ""), "no (MPN)" if k == "mpn" else "yes"])
rows.sort(key=lambda r: (KINDS.index(r[0]), r[1].lower()))
with open(OUT, "w", encoding="utf-8", newline="") as f:
    f.write("kind\tnumber\tmount\tboards_smd\tboards_tht\tfootprints\texample\tlookup\n")
    f.writelines("\t".join(r) + "\n" for r in rows)
c = collections.Counter((r[0], r[2]) for r in rows)
print(f"{OUT}: {len(rows)} numbers;", ", ".join(f"{k} {m} {v}" for (k, m), v in sorted(c.items())),
      "| numbers on lines with no pad-source part to join:", dict(unjoined))
