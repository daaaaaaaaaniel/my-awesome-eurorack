#!/usr/bin/env python3
"""Parts table (user, 2026-10-24; design in STATE.md "Parts table"): what every source in a row's scope states about
its parts, one line per group of identical parts per source file -> data/part-observations.tsv.

  python3 data/part_observations.py [--ids=p1,p2] [--part=i/n] [--out=FILE]   rows -> FILE (no header; default stdout)
  python3 data/part_observations.py --merge FILE...                           -> data/part-observations.tsv (sorted)
  CACHE=<dir> keeps fetched files between runs (nothing is cached without it).

Recorded per source, never merged: a board, its schematic, its iBOM and its BOM spreadsheet are separate lines, because
they disagree (older revisions, wrong footprints) and the disagreement is evidence. Parts are grouped only when every
field but refs/qty is identical, so the grouping loses nothing; refs are written out in full. Sources and their readers:
  kicad        .kicad_pcb footprints: footprint, value, mounting from the pads, KiCad 6+ footprint fields, attributes
  kicad-sch    the board's root schematic (same name, .kicad_sch / .sch; sub-sheets followed, via derive_bom.py):
               value, footprint as assigned, every symbol field - where KiCad boards keep their part numbers
  eagle        .brd elements: library:package, value, mounting from the package's own <smd>/<pad>, element attributes
  easyeda-pcb / easyeda-sch   EasyEDA std JSON (loose, else inside the scope's zips): package, attributes, PCB pads
  ibom         Interactive HTML BOM: footprint, value and extra fields, mounting from its pads
  bom          BOM files (csv / tsv / md / xlsx / ods / HTML tables, plus data/html-boms.tsv): the header's columns
Scope is the detector's: modulefiles.sh + html-boms.tsv, stencil copies and backups with a current board left out; a row
sharing its folder with other rows (or pinned in comp_pins.tsv) reads only the files its comp_basis names, plus their
schematics; one whose comp_basis names no files gets no lines (they would be its neighbours' parts). Older revisions (latest_files.py) are kept and marked superseded. Holes, fiducials, logos, test points, net
ties, solder jumpers, '#' power symbols and parts with no pads are not parts and are left out.
A part number goes in a supplier column only when its field name names that supplier (an EasyEDA 'Supplier Part' takes
the supplier named in its 'Supplier' field); a field that names no supplier ('Part Number', 'PN', 'Order code') goes in
other_supplier as 'Field:number'. Nothing is looked up outside the repo."""
import collections, csv, hashlib, io, json, os, re, subprocess, sys, tempfile, urllib.parse, zipfile
import xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import derive_bom as DB
COLS = ["row_id", "repo", "sha", "source_type", "source_file", "board", "refs", "qty", "value", "footprint", "mount", "pads",
        "manufacturer", "mpn", "lcsc", "mouser", "digikey", "tayda", "other_supplier", "not_fitted", "superseded"]
OUT = os.path.join(HERE, "part-observations.tsv")
CACHE = os.environ.get("CACHE", "")
NOTPART = re.compile(r"(^|:)(MountingHole|Fiducial)|mounting[_ ]?hole|logo|test_?point|net_?tie|solder_?(jumper|bridge)|"
                     r"Symbol:|Kibuzzard|Graphic|(^|:)frame|oshw", re.I)

# ---------- fetching ----------
def fetch_bytes(repo, sha, path):
    if CACHE:
        f = os.path.join(CACHE, hashlib.sha1(f"{repo}@{sha}/{path}".encode()).hexdigest())
        if os.path.exists(f): return open(f, "rb").read() or None
    r = subprocess.run(["curl", "-sS", "-m", "60", "--fail", f"https://raw.githubusercontent.com/{repo}/{sha}/" + urllib.parse.quote(path)],
                       capture_output=True)
    d = r.stdout if r.returncode == 0 else b""
    if CACHE and r.returncode in (0, 22): open(f, "wb").write(d)   # 22 = HTTP error (missing file): cache the absence
    return d or None
def fetch_text(repo, sha, path):
    d = fetch_bytes(repo, sha, path)
    return d.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n") if d is not None else None
DB.fetch = fetch_text   # derive_bom's schematic walker fetches sub-sheets through this

# ---------- part-number fields ----------
SUPPLIERS = {"lcsc": "lcsc", "jlc": "lcsc", "mouser": "mouser", "digikey": "digikey", "digi key": "digikey", "tayda": "tayda"}
NOTNUM = re.compile(r"class|price|stock|link|url|qty|quantity|cost|description|datasheet|note|comment", re.I)
MPN = re.compile(r"^(mpn|mfr ?pn|mfr part( (number|no))?|mfg part( (number|no))?|manf part|manufacturer (part|pn)( (number|no))?|"
                 r"manufacturer ?part ?(number|no)?|mf part|part number manufacturer|mfn)$")
MFR = re.compile(r"^(manufacturer|manufacturer name|mfr|mfr name|mf|manf|mfg|hersteller)$")
AMBIG = re.compile(r"^(part number|partnumber|part no|pn|p n|order code|ordering code|order no|order number|sku|oc .*|supplier part( (number|no))?)$")
OTHER = re.compile(r"farnell|newark|element14|reichelt|conrad|arrow|thonk|banzai|rs (components|online|part|stock|no)|^rs$|"
                   r"pcbway|octopart|tme|futurlec|aliexpress|amazon|ebay|musikding|synthcube|smallbear|rapid")
BLANK = {"", "~", "-", "--", "n/a", "na", "none", "?", "tbd", "x", "nc", "no", "0", "unknown", "undefined", "null"}
FLAGS = {"yes", "no", "true", "false", "y", "n", "basic", "extended", "preferred"}
FORMAT = {"lcsc": re.compile(r"^C\d+$", re.I), "mouser": re.compile(r"\d"), "digikey": re.compile(r"\d"), "tayda": re.compile(r"\d")}
def nname(k):
    k = re.sub(r"^bom_", "", k.strip(), flags=re.I).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9#]+", " ", k)).replace("#", "").strip()
def map_fields(fields):
    """{field name: value} -> {manufacturer, mpn, lcsc, mouser, digikey, tayda, other_supplier}; values as written."""
    out = collections.defaultdict(list)
    sup = next((nname(v) for k, v in fields.items() if nname(k) == "supplier" and v.strip()), "")
    for k, v in fields.items():
        v = str(v).strip(); n = nname(k)
        if v.lower() in BLANK or not n or NOTNUM.search(n): continue
        col = None
        if MPN.match(n): col = "mpn"
        elif MFR.match(n): col = "manufacturer"
        elif n.startswith("supplier part") and sup:
            col = next((c for s, c in SUPPLIERS.items() if s in sup), None)
            if not col: out["other_supplier"].append(f"{k.strip()} ({sup}):{v}"); continue
        elif n == "supplier": continue
        else:
            col = next((c for s, c in SUPPLIERS.items() if re.search(r"(^|\s)" + s, n)), None)
            if not col and (OTHER.search(n) or AMBIG.match(n)): out["other_supplier"].append(f"{k.strip()}:{v}"); continue
        if v.lower() in FLAGS: continue   # 'LCSC Assembly: Yes', 'JLCPCB SMD: No' - flags, not numbers
        if col in ("lcsc", "mouser", "digikey", "tayda") and not FORMAT[col].search(v):
            out["other_supplier"].append(f"{k.strip()}:{v}"); continue   # not that supplier's number format: keep it, with its field name
        if col and v not in out[col]: out[col].append(v)
    return {c: " | ".join(v) for c, v in out.items()}

# ---------- readers: each returns [dict(ref, value, footprint, mount, pads, fields, not_fitted)] ----------
STD_PROPS = {"reference", "value", "footprint", "datasheet", "description", "sheetfile", "sheetname", "sheet file",
             "sheet name", "ki_description", "ki_keywords", "ki_fp_filters"}
def read_kicad(t):
    parts = []
    for head in ("footprint", "module"):
        for a, b in DB.sexp_blocks(t, head):
            blk = t[a:b]
            m = re.match(r'\((?:footprint|module)\s+"?([^"\s)]+)"?', blk)
            if not m: continue
            ref = re.search(r'\(property\s+"Reference"\s+"([^"]*)"|\(fp_text\s+reference\s+"?([^"\s)]+)"?', blk)
            val = re.search(r'\(property\s+"Value"\s+"((?:[^"\\]|\\.)*)"|\(fp_text\s+value\s+"?((?:[^"\\]|\\.)*?)"?[\s)]', blk)
            r = (ref.group(1) or ref.group(2)) if ref else ""
            v = ((val.group(1) if val.group(1) is not None else val.group(2)) or "") if val else ""
            kinds = re.findall(r'\(pad\s+(?:"[^"]*"|\S+)\s+(smd|thru_hole|np_thru_hole|connect)\b', blk)
            mount = "smd" if "smd" in kinds else ("tht" if "thru_hole" in kinds else "")
            attr = " ".join(re.findall(r'\(attr\s+([^)]*)\)', blk))
            nf = [x for x, k in (("board only", "board_only"), ("not in BOM", "exclude_from_bom"), ("dnp", "dnp"), ("virtual", "virtual")) if k in attr]
            props = {k: x for k, x in DB.props(blk).items() if k.lower() not in STD_PROPS and not k.lower().startswith("ki_")}
            parts.append(dict(ref=r, value=v, footprint=m.group(1), mount=mount,
                              pads=str(len([k for k in kinds if k in ("smd", "thru_hole")])), fields=props, not_fitted=",".join(nf)))
    return parts
def read_kicad_sch(repo, sha, root):
    notes = []
    return [dict(ref=r, value=v, footprint=fp, mount="", pads="", fields=f, not_fitted="")
            for r, (v, fp, f) in DB.collect(repo, sha, root, notes).items()]
def read_eagle(raw):
    if not raw.lstrip().startswith(b"<?xml") and b"<eagle" not in raw[:2000]: return []
    try: root = ET.fromstring(raw)
    except ET.ParseError: return []
    kind = {}
    for lib in root.iter("library"):
        for pk in lib.iter("package"):
            ns, np_ = len(pk.findall("smd")), len(pk.findall("pad"))
            kind[(lib.get("name", ""), pk.get("name", ""))] = ("smd" if ns else ("tht" if np_ else ""), ns + np_)
    parts = []
    for el in root.iter("element"):
        lib, pkg = el.get("library", ""), el.get("package", "")
        k = kind.get((lib, pkg)) or next((v for (l, p), v in kind.items() if p == pkg), ("", 0))
        f = {a.get("name", ""): a.get("value", "") for a in el.findall("attribute") if a.get("name", "").upper() not in ("NAME", "VALUE", "POPULARITY", "SPICEPREFIX")}
        parts.append(dict(ref=el.get("name", ""), value=el.get("value", ""), footprint=f"{lib}:{pkg}", mount=k[0], pads=str(k[1]) if k[1] else "",
                          fields=f, not_fitted=""))
    return parts
def easyeda_mount(rec):   # as easyeda_parts.py (v26): any top/bottom pad without a hole = smd; all multi-layer drilled = th
    pads = [p.split("~") for p in rec.split("#@$") if p.startswith("PAD~")]
    pads = [p for p in pads if len(p) > 9]
    if not pads: return "", ""
    def hole(p):
        try: return float(p[9] or 0) > 0
        except ValueError: return False
    if any(p[6] in ("1", "2") and not hole(p) for p in pads): return "smd", str(len(pads))
    if all(p[6] == "11" and hole(p) for p in pads): return "tht", str(len(pads))
    return "", str(len(pads))
def read_easyeda(raw):
    """-> (doctype 'pcb'|'sch'|None, parts); multi-unit parts (U1.1, U1.2) recorded once"""
    head = raw[:400]
    if "editorVersion" not in head: return None, []
    dt = "pcb" if re.search(r'"docType": ?"?3', head) else "sch"
    seen = {}; anon = []
    SKIPK = ("package", "pre", "spicePre", "spiceSymbolName", "Contributor", "link", "3DModel", "timeStamp", "sourceId", "subpart_no",
             "nameAlias", "Value", "value", "description", "image", "license", "Designator")
    def add(d, ref, mount="", pads=""):
        ref = re.sub(r"\.\d+$", "", (ref or "").strip())
        p = dict(ref=ref, value=d.get("Value") or d.get("value") or d.get("nameAlias") or "", footprint=(d.get("package") or "").strip(),
                 mount=mount, pads=pads, fields={k: str(v) for k, v in d.items() if k and k not in SKIPK and isinstance(v, (str, int, float))}, not_fitted="")
        if not p["footprint"]: return
        if ref and "?" not in ref: seen.setdefault(ref, p)
        else: anon.append(p)
    def strings(o):   # as easyeda_parts.py: walk the parsed JSON; newer exports keep attributes as an object
        if isinstance(o, str): yield o
        elif isinstance(o, dict):
            if isinstance(o.get("package"), str): add(o, o.get("pre") or o.get("Designator"))
            for v in o.values(): yield from strings(v)
        elif isinstance(o, list):
            for v in o: yield from strings(v)
    try: recs = [s for s in strings(json.loads(raw)) if "package`" in s]
    except Exception: recs = re.findall(r'"(LIB~[^"]*package`[^"]*)"', raw)
    for rec in recs:
        kvs = re.search(r"[^~]*package`[^~]*", rec).group(0).split("`"); d = dict(zip(kvs[0::2], kvs[1::2]))
        ref = d.get("pre") or d.get("Designator") or ""
        # schematic labels: T~P~x~y~rot~color~font~size~weight~style~baseline~type~TEXT~... (P = designator, N = name/value)
        lab = {s.split("~")[1]: s.split("~")[12] for s in rec.split("#@$") if s.startswith(("T~P~", "T~N~")) and len(s.split("~")) > 12}
        # PCB labels: TEXT~P~x~y~width~rotation~mirror~layer~net~size~TEXT~...
        lab.update({s.split("~")[1]: s.split("~")[10] for s in rec.split("#@$") if s.startswith(("TEXT~P~", "TEXT~N~")) and len(s.split("~")) > 10})
        if (not ref or "?" in ref) and re.fullmatch(r"[A-Za-z_]{1,8}\d+(\.\d+)?", lab.get("P", "")): ref = lab["P"]
        if not (d.get("Value") or d.get("value")) and lab.get("N"): d["value"] = lab["N"]
        if not ref or "?" in ref:   # PCB records: the designator is a TEXT~P~ label inside the same record
            t = re.search(r"T~P~(?:[^~]*~){9}([A-Za-z]{1,4}\d+(?:\.\d+)?)~", rec) or \
                re.search(r"~([A-Za-z]{1,4}\d+\.\d+)~", rec) or re.search(r"T~P~[^#]*?~([A-Za-z]{1,4}\d+)~", rec)
            ref = t.group(1) if t else ""
        if ref.lower().startswith("gge"): ref = ""   # an EasyEDA shape id, not a designator
        add(d, ref, *(easyeda_mount(rec) if dt == "pcb" else ("", "")))
    return dt, list(seen.values()) + anon
_ns = {}
exec(open(os.path.join(HERE, "ibom_parts.py")).read().split("raw = sys.stdin.read()")[0], _ns)   # lz_b64 only
def read_ibom(raw):
    if "pcbdata" not in raw: return []
    m = re.search(r'pcbdata\s*=\s*JSON\.parse\(\s*LZString\.decompressFromBase64\(\s*"([^"]+)"', raw)
    try:
        if m: pcb = json.loads(_ns["lz_b64"](m.group(1)))
        else:
            m = re.search(r"var\s+pcbdata\s*=\s*", raw)
            if not m: return []
            pcb, _ = json.JSONDecoder().raw_decode(raw[m.end():])
    except Exception: return []
    cm = re.search(r"var\s+config\s*=\s*(\{.*?\})\s*;?\s*\n", raw)
    try: cfg = json.loads(cm.group(1)) if cm else {}
    except Exception: cfg = {}
    names = cfg.get("fields") or (["Value", "Footprint"] + list(cfg.get("extra_fields") or []))
    fps = pcb.get("footprints") or pcb.get("modules") or []; bom = pcb.get("bom") or {}
    skipped = set(bom.get("skipped") or []); fields = {}
    for fid, fv in (bom.get("fields") or {}).items():
        if isinstance(fv, list): fields[int(fid)] = dict(zip(names, [str(x) for x in fv]))
    for grp in bom.get("both") or []:            # old format: [qty, value, footprint, [[ref, id]...], extra...]
        if grp and not isinstance(grp[0], list) and len(grp) > 3:
            for ri in grp[3]:
                if isinstance(ri, list) and len(ri) > 1:
                    fields.setdefault(int(ri[1]), dict(zip(["Value", "Footprint"] + list(cfg.get("extra_fields") or []), [str(grp[1]), str(grp[2])] + [str(x) for x in grp[4:]])))
    parts = []
    for i, f in enumerate(fps):
        types = [p.get("type") for p in f.get("pads", [])]
        fv = fields.get(i, {})
        parts.append(dict(ref=f.get("ref", ""), value=fv.get("Value", ""), footprint=fv.get("Footprint", ""),
                          mount="smd" if "smd" in types else ("tht" if "th" in types else ""), pads=str(len(types)) if types else "",
                          fields={k: v for k, v in fv.items() if k not in ("Value", "Footprint")}, not_fitted="not in BOM (iBOM skipped)" if i in skipped else ""))
    return parts
REFCOL = {"designator", "designators", "reference", "references", "ref", "refs", "reference(s)", "references(s)", "refdes", "ref des", "ref. des.",
          "location", "locations", "position", "designation", "parts", "part", "component", "components", "part reference"}
QTYCOL = {"qty", "quantity", "qnty", "count", "amount", "anzahl", "qty.", "quantity per pcb", "menge"}
VALCOL = {"value", "val", "wert", "comment", "values"}
FPCOL = {"footprint", "package", "case", "package type", "case/package", "footprint name", "pcb footprint", "gehäuse", "size"}
DNPCOL = re.compile(r"^(dnp|dnf|fitted|populate|populated|place|mounted|do not populate|do not place)$", re.I)
DESIG = re.compile(r"^[A-Za-z]{1,4}\d+[A-Za-z]?$")
def expand_refs(s):
    out = []
    for tok in [x for x in re.split(r"[,;\s]+", s) if x]:
        m = re.fullmatch(r"([A-Za-z]+)(\d+)-(?:\1)?(\d+)", tok)
        if m and int(m.group(3)) >= int(m.group(2)) and int(m.group(3)) - int(m.group(2)) < 500:
            out += [f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(3)) + 1)]
        else: out.append(tok)
    return out
def table_rows(text):
    lines = [l for l in text.lstrip("﻿").splitlines() if l.strip()]
    if not lines: return []
    if any(l.lstrip().startswith("|") for l in lines[:20]):
        return [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines if l.lstrip().startswith("|") and not re.fullmatch(r"[\s|:-]+", l)]
    sample = "\n".join(lines[:15])
    delim = max(("\t", ",", ";"), key=lambda d: sample.count(d))
    return list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delim))
def read_bom(text):
    rows = table_rows(text); hdr = None
    for i, r in enumerate(rows[:15]):
        low = [c.strip().lower() for c in r]
        if sum(1 for c in low if c in REFCOL | QTYCOL | VALCOL | FPCOL or MPN.match(nname(c)) or "lcsc" in c or "mouser" in c) >= 2: hdr = i; break
    if hdr is None: return []
    H = [c.strip() for c in rows[hdr]]; low = [c.lower() for c in H]
    def col(names, test=None):
        for j, c in enumerate(low):
            if c in names and (test is None or test(j)): return j
    def desig(j):
        vals = [r[j].strip() for r in rows[hdr + 1:] if j < len(r) and r[j].strip()]
        return bool(vals) and sum(all(DESIG.match(x) or re.fullmatch(r"[A-Za-z]+\d+-[A-Za-z]*\d+", x) for x in re.split(r"[,;\s]+", v) if x) for v in vals) * 2 >= len(vals)
    ri = col(REFCOL - {"part", "parts", "component", "components"})
    if ri is None: ri = col({"part", "parts", "component", "components", "location", "position"}, desig)
    qi, vi, fi = col(QTYCOL), col(VALCOL), col(FPCOL)
    di = next((j for j, c in enumerate(H) if DNPCOL.match(c)), None)
    used = {ri, qi, vi, fi, di}
    parts = []
    for r in rows[hdr + 1:]:
        if not any(c.strip() for c in r): continue
        g = lambda j: r[j].strip() if j is not None and j < len(r) else ""
        f = {H[j]: r[j] for j in range(min(len(H), len(r))) if j not in used and H[j]}
        nf = ""
        dv = g(di).lower()
        if di is not None and (dv in ("dnp", "dnf", "x", "yes") if DNPCOL.match(H[di]).group(1).lower() in ("dnp", "dnf", "do not populate", "do not place") else dv in ("no", "0", "n", "false", "dnp")): nf = "dnp"
        if re.fullmatch(r"(dnp|dnf|do not (fit|place|populate)|not fitted)", g(vi), re.I): nf = "dnp"
        refs = expand_refs(g(ri)) if ri is not None else []
        q = re.match(r"\s*(\d+)", g(qi)); qty = int(q.group(1)) if q else None
        if not refs and qty is None and not (g(vi) or g(fi)): continue
        base = dict(value=g(vi), footprint=g(fi), mount="", pads="", fields=f, not_fitted=nf)
        if refs: parts += [dict(base, ref=x) for x in refs]
        else: parts.append(dict(base, ref="", qty=qty or 1))
    return parts

# ---------- scope ----------
def tsv_rows(path):
    raw = open(path, newline="", encoding="utf-8").read(); NL = "\r\n" if "\r\n" in raw else "\n"; L = []
    for pl in raw.split(NL):
        if L and L[-1].count('"') % 2: L[-1] += NL + pl
        else: L.append(pl)
    h = L[0].split("\t")
    def qsplit(x):
        out, cur, q = [], [], False
        for ch in x:
            if ch == '"': q = not q
            if ch == "\t" and not q: out.append("".join(cur)); cur = []
            else: cur.append(ch)
        out.append("".join(cur)); return out
    return [dict(zip(h, qsplit(l))) for l in L[1:] if l]
def latest(paths):
    """-> {path: superseded?} via latest_files.py (newest of each board group kept)"""
    if not paths: return {}
    o = subprocess.run(["python3", os.path.join(HERE, "latest_files.py")], input="\n".join(paths) + "\n", capture_output=True, text=True).stdout.splitlines()
    res = {p: False for p in paths}
    for x in o:
        if x.startswith("#SUP\t"): res[x.split("\t", 1)[1]] = True
    return res
BOMF = re.compile(r"(^|/)[^/]*bom[^/]*\.(csv|md|txt|tsv|xlsx|ods|html?)$", re.I)
BK = re.compile(r"(^|/)[^/]*backups?[^/]*/", re.I)
def scope(r, flat, inv_sha):
    md = r["module_dir"] or "."
    files = subprocess.run(["bash", os.path.join(HERE, "modulefiles.sh"), r["repo"], md], capture_output=True, text=True,
                           env={**os.environ, "TREES": os.path.join(HERE, "trees")}).stdout.splitlines()[1:]
    xb = [l.split("\t")[3] for l in open(os.path.join(HERE, "html-boms.tsv"), encoding="utf-8").read().splitlines()[1:]
          if l.count("\t") >= 3 and l.split("\t")[1] == r["repo"] and l.split("\t")[2] == md]
    files = sorted(set(files + xb))
    note = ""
    if flat:
        b = r["comp_basis"]
        fm = re.search(r"\(files=\d+: (.*?)\): smd=", b) or re.search(r"\(files=\d+: ([^)]*)\)", b)
        if fm:
            sm = re.search(r"\[superseded, not counted: ([^\]]*)\]", b)
            names = [x.strip() for x in fm.group(1).split(", ") + (sm.group(1).split(", ") if sm else []) if x.strip()]
            stems = {re.sub(r"\.[^.]+$", "", os.path.basename(x)) for x in names}
            files = [f for f in files if os.path.basename(f) in names or (f.lower().endswith((".kicad_sch", ".sch")) and re.sub(r"\.[^.]+$", "", os.path.basename(f)) in stems)]
        else: return [], xb, "skipped"   # its files cannot be told from its neighbours': pooling would give it theirs
    files = [f for f in files if not re.search(r"(^|/)[^/]*stencil[^/]*$", f, re.I)]
    cur = {os.path.basename(f) for f in files if not BK.search(f)}
    files = [f for f in files if not (BK.search(f) and os.path.basename(f) in cur)]
    return files, xb, note

def run_row(r, flat, sha):
    files, xb, note = scope(r, flat, sha)
    repo = r["repo"]; out = []   # (source_type, source_file, board, superseded, parts)
    pcbs = latest([f for f in files if f.lower().endswith(".kicad_pcb")])
    for p, sup in pcbs.items():
        t = fetch_text(repo, sha, p)
        if t is None: continue
        out.append(("kicad", p, p, sup, read_kicad(t)))
        stem = re.sub(r"\.kicad_pcb$", "", p, flags=re.I)
        root = next((s for s in (stem + ".kicad_sch", stem + ".sch") if s in files), None)
        if root: out.append(("kicad-sch", root, p, sup, read_kicad_sch(repo, sha, root)))
    for p, sup in latest([f for f in files if f.lower().endswith(".brd")]).items():
        raw = fetch_bytes(repo, sha, p)
        if raw: out.append(("eagle", p, p, sup, read_eagle(raw)))
    ej = [f for f in files if f.lower().endswith(".json") and not re.search(r"package\.json|\.vscode|tsconfig|manifest", f, re.I)][:12]
    got = []
    for p in ej:
        t = fetch_text(repo, sha, p)
        if t is None: continue
        dt, parts = read_easyeda(t)
        if dt: got.append(("easyeda-" + dt, p, p if dt == "pcb" else "", False, parts))
    if not got:   # v26: EasyEDA exports often ship zipped
        for z in [f for f in files if f.lower().endswith(".zip")][:6]:
            raw = fetch_bytes(repo, sha, z)
            if not raw: continue
            try: zf = zipfile.ZipFile(io.BytesIO(raw))
            except zipfile.BadZipFile: continue
            def members(zf, prefix, depth):
                for n in zf.namelist():
                    if n.lower().endswith(".json"): yield prefix + n, zf.read(n).decode("utf-8", "replace")
                    elif n.lower().endswith(".zip") and depth < 1:
                        try: yield from members(zipfile.ZipFile(io.BytesIO(zf.read(n))), prefix + n + "!", depth + 1)
                        except zipfile.BadZipFile: pass
            for name, t in members(zf, "", 0):
                dt, parts = read_easyeda(t)
                if dt: got.append(("easyeda-" + dt, f"{z}!{name}", f"{z}!{name}" if dt == "pcb" else "", False, parts))
    out += got
    htmls = latest([f for f in files if re.search(r"\.html?$", f, re.I)][:12])
    boms = latest([f for f in files if (BOMF.search(f) or f in xb) and not re.search(r"\.html?$", f, re.I)])
    for p, sup in htmls.items():
        t = fetch_text(repo, sha, p)
        if t is None: continue
        parts = read_ibom(t)
        if parts: out.append(("ibom", p, "", sup, parts)); continue
        if BOMF.search(p) or p in xb:
            tsv = subprocess.run(["python3", os.path.join(HERE, "html2tsv.py")], input=t, capture_output=True, text=True).stdout
            if tsv.strip(): out.append(("bom", p, "", sup, read_bom(tsv)))
    for p, sup in boms.items():
        if p.lower().endswith((".xlsx", ".ods")):
            raw = fetch_bytes(repo, sha, p)
            if not raw: continue
            d = tempfile.mkdtemp(); tf = os.path.join(d, "bom" + os.path.splitext(p)[1].lower()); open(tf, "wb").write(raw)
            t = subprocess.run(["python3", os.path.join(HERE, "xl2tsv.py"), tf], capture_output=True, text=True).stdout
            subprocess.run(["rm", "-rf", d])
        else: t = fetch_text(repo, sha, p)
        if t: out.append(("bom", p, "", sup, read_bom(t)))
    # a BOM, iBOM or EasyEDA schematic describes the row's one current board when there is exactly one
    cur = sorted({b for st, _, b, s, _ in out if b and not s and st in ("kicad", "eagle", "easyeda-pcb")})
    lines = []
    for st, src, board, sup, parts in out:
        if not board and len(cur) == 1: board = cur[0]
        groups = collections.OrderedDict()
        for p in parts:
            ref = (p.get("ref") or "").strip()
            if ref.startswith("#") or "**" in ref or NOTPART.search(p.get("footprint", "")): continue
            if st in ("kicad", "eagle", "ibom", "easyeda-pcb") and not p.get("mount"): continue   # no pads: not a part
            nums = map_fields(p.get("fields") or {})
            key = (p.get("value", ""), p.get("footprint", ""), p.get("mount", ""), p.get("pads", ""),
                   *[nums.get(c, "") for c in ("manufacturer", "mpn", "lcsc", "mouser", "digikey", "tayda", "other_supplier")], p.get("not_fitted", ""))
            g = groups.setdefault(key, [[], 0]); g[1] += p.get("qty", 1)
            if ref: g[0].append(ref)
        for key, (refs, qty) in groups.items():
            refs = sorted(set(refs), key=DB.natkey)
            lines.append([r["id"], repo, sha, st, src, board, ",".join(refs), str(len(refs) if refs else qty), *key[:4], *key[4:11], key[11], "superseded" if sup else ""])
    return lines, note

def clean(x): return re.sub(r"[\t\r\n]+", " ", str(x)).strip()
if __name__ == "__main__":
    if "--merge" in sys.argv:
        L = []
        for f in [a for a in sys.argv[1:] if not a.startswith("--")]: L += [l.rstrip("\n").split("\t") for l in open(f, encoding="utf-8") if l.strip()]
        L.sort(key=lambda x: (int(re.sub(r"\D", "", x[0]) or 0), x[0], x[4], DB.natkey(x[6]), x[8], x[9]))
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            f.write("\t".join(COLS) + "\n"); f.writelines("\t".join(x) + "\n" for x in L)
        print(f"{OUT}: {len(L)} lines, {len({x[0] for x in L})} rows"); sys.exit()
    rows = tsv_rows(os.path.join(HERE, "modules.tsv"))
    inv = {}
    for l in open(os.path.join(HERE, "inventory.tsv"), encoding="utf-8").read().splitlines()[1:]:
        p = l.rstrip("\r").split("\t")
        if len(p) > 6: inv[p[1]] = p[5] or p[6] or "main"
    pins = {l.split("\t")[0] for l in open(os.path.join(HERE, "comp_pins.tsv")).read().splitlines()[1:] if l.strip()}
    share = collections.Counter((r["repo"], r["module_dir"] or ".") for r in rows)
    ids = set(",".join(a[6:] for a in sys.argv if a.startswith("--ids=")).split(",")) - {""}
    pa = [a for a in sys.argv if a.startswith("--part=")]
    todo = [r for r in rows if r.get("repo") in inv and os.path.exists(os.path.join(HERE, "trees", r["repo"].replace("/", "_") + ".txt"))
            and (not ids or r["id"] in ids)]
    if pa:
        i, n = map(int, pa[0][7:].split("/")); todo = [r for r in todo if int(re.sub(r"\D", "", r["id"]) or 0) % n == i]
    of = next((a[6:] for a in sys.argv if a.startswith("--out=")), None)
    out = open(of, "w", encoding="utf-8") if of else sys.stdout
    for r in todo:
        flat = share[(r["repo"], r["module_dir"] or ".")] > 1 or r["module_name"].endswith(("(SMD)", "(THT)")) or r["id"] in pins
        try: lines, note = run_row(r, flat, inv[r["repo"]])
        except Exception as e: print(f"{r['id']}: {type(e).__name__}: {e}", file=sys.stderr); continue
        out.writelines("\t".join(clean(x) for x in l) + "\n" for l in lines); out.flush()
        if note: print(f"{r['id']}: {note} - shares its folder with other rows and its comp_basis names no files", file=sys.stderr)
