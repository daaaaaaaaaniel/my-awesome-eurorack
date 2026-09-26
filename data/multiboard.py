"""Sort multi-board folders of data/components-out.tsv into review classes (a GUESS from filenames).

  python3 data/multiboard.py   -> data/multiboard.tsv (+ counts on stdout)

Classes (see d's multi-board ruling, relayed in messages/2026-09-26-0130-from-fable.md):
  revisions   - one board in several versions/dates/_fixed   -> newest counts, flag
  variants    - SMD/THT (or similar) builds of one module     -> one row per variant
  sub-boards  - main + ctrl/io/front/back/expander/...        -> pooled into one row
  collection  - several different modules flat in one folder  -> split per board at enrichment
  mixed       - more than one of the above                    -> read by hand
Every multi-board row is flagged for manual check whatever the guess says.
"""
import csv, os, re
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
SUB = r"cntl|ctl|mount|oled|lcd|breakout|components|controls?|screen|connectors?|jackboard|jacks?board|programming-board|adapter|breakout|mainboard|main|mainboard|mother|ctrl|control|controls|io|i-o|jack|jacks|pot|pots|front|back|rear|top|bottom|bot|panel-?pcb|daughter|daughtercard|daughterboard|expander|exp|power|psu|interface|ui|cv|audio|display|led|leds|switch|switches|faders?|mcu|cpu|dsp|core|digital|analog|upper|lower|left|right|a|b|board|pcb|brd"
VAR = r"stripboard|perfboard|vero|protoboard|smd|tht|th|through-?hole|sm|dip|soic"
EXT = re.compile(r"\.(kicad_pcb|brd|json|csv|tsv|xlsx?|txt|ods|html?)$", re.I)
VER = re.compile(r"(?:^|[ _.\-])(?:v|ver|version|rev|r)[ _.\-]?\d+(?:\.\d+)*|\d{4}-\d{2}-\d{2}|\d{8}|(?:^|[ _.\-])fixed|(?:^|[ _.\-])copy|(?:^|[ _.\-])bom|(?:^|[ _.\-])pcb", re.I)

def stem(f):
    s = EXT.sub("", os.path.basename(f).strip())
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s).lower()            # camelCase -> words
    s = re.sub(r"\s*\(\d+\)$|\s+\d$", " copy", s)              # "fjol(1)", "fjol 2" = copies
    s = re.sub(r"^fixed-", "", s)
    return s

def core(s, drop):
    s = VER.sub(" ", s)
    s = re.sub(r"(?:^|[ _.\-])(%s)(?=$|[ _.\-])" % drop, " ", s)
    return re.sub(r"[ _.\-]+", " ", s).strip()

PANEL = re.compile(r"panel|face ?plate|front ?plate|frontpanel|(?:^|[ _.\-])fp(?:$|[ _.\-])|screenfit", re.I)

def toks(s): return [t for t in re.split(r"[ _.\-]+", s) if t]

def classify(files):
    """-> (guess, name_groups). Panel boards are set aside: board + panel is ONE board."""
    boards = [f for f in files if not PANEL.search(os.path.basename(f)) and not re.search(r"(^|/)_?autosave|-bak$|\.bak", f, re.I)]
    if len(boards) < 2:
        return "board+panel", 1
    stems = [stem(f) for f in boards]
    bare = [core(s, "(?!)") for s in stems]              # versions/dates/fixed stripped
    novar = {core(s, VAR) for s in stems}
    kinds = []
    if len(set(bare)) < len(bare): kinds.append("revisions")
    if len(novar) < len(set(bare)): kinds.append("variants")
    rest = sorted(novar)
    if len(rest) > 1:
        nosub = {core(x, SUB) for x in rest} - {""}
        pre = os.path.commonprefix(rest).strip(" ")
        if len(nosub) <= 1 or len(pre) >= 4: kinds.append("sub-boards")      # main/ctrl/... or shared name
        elif len(rest) == 2: kinds.append("unclear-pair")
        else: kinds.append("collection")
    groups = len(rest)
    if not kinds: kinds = ["unclear"]
    return ("mixed:" + "+".join(kinds)) if len(kinds) > 1 else kinds[0], groups

rows, counts = [], defaultdict(int)
for r in csv.DictReader(open(os.path.join(HERE, "components-out.tsv")), delimiter="\t", quoting=csv.QUOTE_NONE):
    b = r["comp_basis"]
    m = re.search(r"\(files=(\d+): (.*?)\): smd=", b)
    sup = re.search(r"\[superseded, not counted: (.*?)\]", b)
    files = m.group(2).split(", ") if m else []
    allf = files + (sup.group(1).split(", ") if sup else [])
    if len(allf) < 2: continue
    cls, groups = classify(allf)
    counts[cls] += 1
    rows.append([r["repo"], r["module_scope"], str(len(allf)), str(groups), cls, r["components"],
                 ", ".join(files), sup.group(1) if sup else ""])
rows.sort(key=lambda x: (x[4], x[0], x[1]))
with open(os.path.join(HERE, "multiboard.tsv"), "w") as fh:
    fh.write("repo\tmodule_scope\tboard_files\tname_groups\tguess\tpooled_verdict\tcounted_files\tsuperseded\n")
    for x in rows: fh.write("\t".join(x) + "\n")
print(len(rows), "multi-board folders"); [print(f"  {k}: {v}") for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
