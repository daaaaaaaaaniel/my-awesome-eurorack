#!/usr/bin/env python3
"""Shipped placement files for the CPL audit (d, 2026-09-28 05:17: "add it and re-run").

A repo that ships a CPL / position file (JLCPCB Fabrication Toolkit CPL-*.csv, KiCad *-pos.csv /
.pos, pick-and-place, centroid, XYRS exports) states which parts the designer means to be machine
placed - better evidence than grading the board (dchwebb Punck: board check 85/96 SMD parts with
LCSC, shipped BOM 95/95). This module finds those files in a row's scope, reads their references
and sides, pairs them with a BOM in the same folder for LCSC / other part numbers, and grades:

  shipped-lcsc  every placed reference has an LCSC number in the shipped BOM (JLCPCB as-is)
  shipped-mpn   every placed reference has some part number (MPN or distributor SKU)
  shipped-cpl   a placement file, but part numbers missing (or no BOM beside it)

`stale` = placed references that no board of the row has (a file generated from an older board)."""
import csv, io, os, re, subprocess, tempfile, urllib.parse

PLACE = re.compile(r"(^|[-_ .])(cpl|pnp|pick[-_ ]?(and|n|&)?[-_ ]?place|centroid|xyrs|placement|positions?)([-_ .]|$)"
                   r"|[-_](all|top|bottom|both|front|back)[-_]pos\.|(^|[-_ ])pos\.(csv|txt)$|\.pos$", re.I)
EXT = re.compile(r"\.(csv|txt|pos|tsv|xlsx|xls)$", re.I)
BOMF = re.compile(r"(^|[-_ .])(bom|bill[-_ ]?of[-_ ]?materials?)([-_ .]|$)", re.I)
REFCOL = re.compile(r"^(designators?|ref(s|des|erence|erences)?|part|name|parts?\s*id|component)$", re.I)
SIDECOL = re.compile(r"^(layer|side|tb|top\s*/\s*bottom|mirror)$", re.I)
LCSCCOL = re.compile(r"lcsc|jlc", re.I)
PNCOL = re.compile(r"lcsc|jlc|mpn|manufacturer[ _]*(part|pn|no)|mfr|mfg|part[ _]*(number|num|no|#)|partnum|mouser|digi-?key|supplier[ _]*(part|pn)|vendor[ _]*part|^pn$|^p/n$", re.I)
REF = re.compile(r"^[A-Za-z]{1,4}\d{1,4}[A-Za-z]?$")

BACKUP = re.compile(r"(^|/)[^/]*backups?[^/]*/", re.I)   # KiCAD9-BACKUP/, *-backups/: copies, not shipped files

def is_place(path):
    b = path.rsplit("/", 1)[-1]
    return bool(EXT.search(b) and PLACE.search(b) and not BOMF.search(b) and not BACKUP.search(path))

def pair(pfile, boards):
    """the board a placement file was exported from: same folder, or one folder apart, or the board's
    name inside the file name; None when nothing pairs (then staleness is not judged)"""
    pd = pfile.rsplit("/", 1)[0] if "/" in pfile else ""
    # drop the side suffix first: fjol-top-pos.csv is board "fjol" (top side), not board "fjol-top"
    pb = re.sub(r"[-_ ](all|top|bottom|both|front|back)[-_ ]?(pos|positions?|cpl|pnp)\b.*$|\.[a-z]+$", "", pfile.rsplit("/", 1)[-1].lower())
    best = None
    for b in boards:
        bd = b.rsplit("/", 1)[0] if "/" in b else ""
        stem = b.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        near = bd == pd or (pd.startswith(bd + "/") and pd.count("/") - bd.count("/") <= 2) or (bd.startswith(pd + "/") and bd.count("/") - pd.count("/") <= 1)
        named = len(stem) >= 3 and stem in pb
        score = (2 if named else 0) + (1 if near else 0)
        if score and (best is None or score > best[0]): best = (score, b)
    return best[1] if best else None

def table(path, data):
    """rows (list of lists) from csv / tsv / KiCad .pos / xlsx bytes"""
    if path.lower().endswith(".xls"):   # old binary Excel (CATs Eurosynth position files)
        import xlrd
        sh = xlrd.open_workbook(file_contents=data).sheet_by_index(0)
        return [[str(c).strip() for c in sh.row_values(i)] for i in range(sh.nrows)]
    if re.search(r"\.xlsx$", path, re.I):
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(path)[1], delete=False) as t: t.write(data)
        r = subprocess.run(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "xl2tsv.py"), t.name], capture_output=True, text=True)
        os.unlink(t.name)
        return [l.split("\t") for l in r.stdout.splitlines()]
    # EasyEDA writes its pick-and-place CSV as UTF-16 (508-loop-detected, DatanoiseTV)
    txt = data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode("utf-8-sig", "replace")
    lines = [l for l in txt.splitlines() if l.strip()]
    if lines and (lines[0].startswith("#") or path.lower().endswith(".pos")) and not ("," in lines[0] and lines[0].count(",") > 2):
        # KiCad ascii .pos: "# Ref Val Package PosX PosY Rot Side", space-separated, header behind '#'
        hdr = next((l.lstrip("#").split() for l in lines if l.lstrip("#").strip().lower().startswith("ref")), None)
        body = [l.split() for l in lines if not l.startswith("#")]
        return ([hdr] if hdr else []) + body
    dl = max([",", ";", "\t"], key=lambda d: lines[0].count(d) if lines else 0)
    return list(csv.reader(io.StringIO(txt), delimiter=dl))

def header(rows, want):
    """index of the first row that has a column matching `want`"""
    for i, r in enumerate(rows[:15]):
        if any(want.search(c.strip()) for c in r): return i
    return None

def refs_of(cell):
    out = []
    for x in re.split(r"[,;\s]+", cell.strip()):
        m = re.fullmatch(r"([A-Za-z]+)(\d+)\s*[-–]\s*\1?(\d+)", x)
        if m and int(m.group(3)) - int(m.group(2)) < 200:
            out += [f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif REF.match(x): out.append(x)
    return out

def placements(path, data):
    """(set of references, Counter-ish dict of sides) from a placement file"""
    rows = table(path, data)
    h = header(rows, REFCOL)
    if h is None:   # no header: first column holding designators
        return {r[0].strip() for r in rows if r and REF.match(r[0].strip())}, {}
    hd = [c.strip() for c in rows[h]]
    ri = next(i for i, c in enumerate(hd) if REFCOL.search(c))
    si = next((i for i, c in enumerate(hd) if SIDECOL.search(c)), None)
    refs, sides = set(), {}
    for r in rows[h + 1:]:
        if len(r) <= ri: continue
        for x in refs_of(r[ri]):
            refs.add(x)
            if si is not None and len(r) > si:
                s = r[si].strip().lower()
                s = "bottom" if s.startswith(("b", "bot")) or s == "yes" else "top" if s else "?"
                sides[s] = sides.get(s, 0) + 1
    return refs, sides

def bom_parts(path, data):
    """{ref: (has_lcsc, has_pn)} from a BOM, or {} when it names no designators"""
    rows = table(path, data)
    h = header(rows, REFCOL)
    if h is None: return {}
    hd = [c.strip() for c in rows[h]]
    ri = next(i for i, c in enumerate(hd) if REFCOL.search(c))
    lc = [i for i, c in enumerate(hd) if LCSCCOL.search(c)]
    pn = [i for i, c in enumerate(hd) if PNCOL.search(c)]
    out = {}
    for r in rows[h + 1:]:
        if len(r) <= ri: continue
        v = lambda ix: [r[i].strip() for i in ix if i < len(r) and r[i].strip() not in ("", "-", "~", "n/a", "N/A", "DNP", "dnp")]
        has_l = any(re.fullmatch(r"C\d{3,}", x) for x in v(lc))
        has_p = has_l or bool(v(pn))
        for x in refs_of(r[ri]):
            a, b = out.get(x, (False, False)); out[x] = (a or has_l, b or has_p)
    return out
