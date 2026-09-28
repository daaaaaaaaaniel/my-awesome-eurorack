#!/usr/bin/env python3
"""BOM generated from a module's KiCad schematic(s) (d, 2026-09-28 19:01), for rows whose repo ships no BOM file.

  python3 data/derive_bom.py [--board] < jobs.tsv            jobs.tsv: id<TAB>repo<TAB>sha<TAB>schematic[;schematic...][<TAB>partlist]
  writes data/derived-boms/<id>.tsv and prints one summary line per row (id, boards, parts, lines, notes).

Each schematic is a board's ROOT sheet (KiCad 6+ .kicad_sch or KiCad 4/5 .sch); hierarchical sub-sheets are followed,
and a sheet used N times contributes its parts N times under their instance references. Parts left out: power
symbols and flags (reference starting '#'), symbols marked (in_bom no) or (dnp yes), mounting holes and fiducials. Parts are grouped per board by
value + footprint, like KiCad's own grouped BOM export; every other field a designer filled in on the symbols
(MPN, manufacturer, LCSC, Mouser, description ...) becomes a column. Nothing is added from outside the repo: the
optional partlist is a file IN the repo (spielhuus/elektrophon lib/partlist.yaml, which its own index.rmd uses to
describe its BOMs), matched on footprint + value.
Columns: board, qty, references, value, footprint, then extra fields in first-seen order.
--board (d, 2026-09-28 ~19:20): the same BOM read from each schematic's .kicad_pcb instead -> <id>-board.tsv. Made for rows
whose schematic and board disagree, so both versions can be shown side by side with a warning."""
import collections, os, re, subprocess, sys, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "derived-boms")
SKIP_FIELDS = {"reference", "value", "footprint", "datasheet", "ki_keywords", "ki_description", "ki_fp_filters", "sim.enable",
               "sim.device", "sim.type", "sim.pins", "sim.params", "sim.library", "sim.name", "spice_primitive", "spice_model",
               "spice_netlist_enabled", "spice_lib_file", "sheetname", "sheetfile", "sheet name", "sheet file", "intersheetrefs"}

def fetch(repo, sha, path):
    r = subprocess.run(["curl", "-sS", "-m", "60", "--fail", f"https://raw.githubusercontent.com/{repo}/{sha}/" + urllib.parse.quote(path)], capture_output=True)
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n") if r.returncode == 0 else None

def sexp_blocks(t, head):
    """yield (start, end) of every balanced '(head ...' block at any depth, not nested inside another match"""
    i = 0
    while True:
        i = t.find("(" + head, i)
        if i < 0: return
        nxt = t[i + 1 + len(head): i + 2 + len(head)]
        if nxt and not (nxt.isspace() or nxt == ")"): i += 1; continue
        d = 0; j = i; q = False
        while j < len(t):
            c = t[j]
            if c == '"' and t[j - 1] != "\\": q = not q
            elif not q:
                if c == "(": d += 1
                elif c == ")":
                    d -= 1
                    if d == 0: break
            j += 1
        yield i, j + 1; i = j + 1

def props(b):
    return {m.group(1): m.group(2).replace('\\"', '"') for m in re.finditer(r'\(property\s+"((?:[^"\\]|\\.)*)"\s+"((?:[^"\\]|\\.)*)"', b)}

def parse_new(t):
    """KiCad 6+: returns (uuid, symbols, sheets, symbol_instances)"""
    ls = t.find("(lib_symbols")
    if ls >= 0:
        for a, b in sexp_blocks(t[ls:], "lib_symbols"): t = t[:ls] + t[ls + b:]; break
    root_uuid = (re.search(r'^\s*\(kicad_sch[^\n]*\n(?:.*\n){0,6}?\s*\(uuid\s+"?([0-9a-f-]+)', t) or [None, ""])[1]
    syms, sheets, sinst = [], [], {}
    for a, b in sexp_blocks(t, "symbol"):
        blk = t[a:b]
        if not blk.startswith("(symbol (lib_id") and not re.match(r'\(symbol\s+\(lib_id', blk): continue
        head = blk.split("(property", 1)[0]
        uu = (re.search(r'\(uuid\s+"?([0-9a-f-]+)', head) or [None, ""])[1]
        excl = bool(re.search(r'\(in_bom no\)|\(dnp yes\)', head))
        p = props(blk)
        inst = [(m.group(1), m.group(2)) for m in re.finditer(r'\(path\s+"([^"]*)"\s*\(reference\s+"([^"]*)"', blk)]
        lib = re.match(r'\(symbol\s+\(lib_id\s+"([^"]*)"', blk).group(1)
        syms.append(dict(uuid=uu, excl=excl, p=p, inst=inst, lib=lib))
    for a, b in sexp_blocks(t, "sheet"):
        blk = t[a:b]
        if not re.match(r'\(sheet\s', blk): continue
        p = props(blk); f = p.get("Sheetfile") or p.get("Sheet file") or ""
        uu = (re.search(r'\(uuid\s+"?([0-9a-f-]+)', blk) or [None, ""])[1]
        inst = [m.group(1) for m in re.finditer(r'\(path\s+"([^"]*)"\s*\(page', blk)]
        if f: sheets.append(dict(file=f, uuid=uu, inst=inst))
    for a, b in sexp_blocks(t, "symbol_instances"):
        for m in re.finditer(r'\(path\s+"([^"]*)"\s*\(reference\s+"([^"]*)"\s*\(unit\s+\d+\)(?:\s*\(value\s+"((?:[^"\\]|\\.)*)"\))?(?:\s*\(footprint\s+"((?:[^"\\]|\\.)*)"\))?', t[a:b]):
            sinst[m.group(1)] = (m.group(2), m.group(3), m.group(4))
    return root_uuid, syms, sheets, sinst

def parse_old(t):
    """KiCad 4/5 .sch: symbols [(ts, ref, value, fp, fields, AR{path:ref})], sheets [(file, ts)]"""
    syms, sheets = [], []
    for c in re.findall(r"\$Comp\n(.*?)\$EndComp", t, re.S):
        L = re.search(r"^L (\S+) (\S+)", c, re.M); U = re.search(r"^U \d+ \d+ ([0-9A-Fa-f]+)", c, re.M)
        F = {int(m.group(1)): (m.group(2), m.group(3)) for m in re.finditer(r'^F (\d+) "((?:[^"\\]|\\.)*)"[^\n]*?(?:"([^"]*)")?\s*$', c, re.M)}
        ar = {m.group(1): m.group(2) for m in re.finditer(r'AR Path="([^"]*)" Ref="([^"]*)"', c)}
        ref = F.get(0, ("",))[0] or (L.group(2) if L else "")
        extra = {F[k][1]: F[k][0] for k in F if k >= 4 and F[k][1]}
        syms.append(dict(ts=U.group(1) if U else "", ref=ref, value=F.get(1, ("",))[0], fp=F.get(2, ("",))[0], p=extra, ar=ar, lib=L.group(1) if L else ""))
    for s in re.findall(r"\$Sheet\n(.*?)\$EndSheet", t, re.S):
        f = re.search(r'^F1 "([^"]*)"', s, re.M); u = re.search(r"^U ([0-9A-Fa-f]+)", s, re.M)
        if f: sheets.append((f.group(1), u.group(1) if u else ""))
    return syms, sheets

def collect(repo, sha, root, notes):
    """-> {ref: (value, footprint, {field: val})} for one board"""
    parts = {}; cache = {}
    def get(path):
        if path not in cache: cache[path] = fetch(repo, sha, path)
        return cache[path]
    def join(base, f): return os.path.normpath(os.path.join(os.path.dirname(base), f)).replace("\\", "/")
    t = get(root)
    if t is None: notes.append(f"fetch failed: {root}"); return parts
    if root.endswith(".kicad_sch"):
        ruu, _, _, sinst = parse_new(t)
        allsyms = {}
        def walk(path, ipath, depth):
            tt = get(path)
            if tt is None: notes.append(f"sheet missing: {path}"); return
            if depth > 12: notes.append("hierarchy too deep"); return
            _, syms, sheets, _ = parse_new(tt)
            for s in syms:
                allsyms[s["uuid"]] = s
                if sinst: continue                      # KiCad 6: the root's symbol_instances decide below
                refs = [r for (pth, r) in s["inst"] if pth == ipath] or ([s["p"].get("Reference", "")] if not s["inst"] or depth == 0 else [])
                if not refs and s["inst"]: refs = [s["inst"][0][1]]; notes.append(f"instance path not matched in {path}")
                for r in refs:
                    if r and not r.startswith("#") and not s["lib"].startswith("power:") and not s["excl"] and r not in parts:
                        parts[r] = (s["p"].get("Value", ""), s["p"].get("Footprint", ""), {k: v for k, v in s["p"].items() if k.lower() not in SKIP_FIELDS and v.strip() and v != "~"})
            for sh in sheets: walk(join(path, sh["file"]), ipath + "/" + sh["uuid"], depth + 1)
        walk(root, "/" + ruu if ruu else "", 0)
        for pth, (ref, val, fp) in sinst.items():         # KiCad 6 root table: path ends in the symbol's uuid
            s = allsyms.get(pth.rsplit("/", 1)[-1])
            if ref.startswith("#") or (s and (s["excl"] or s["lib"].startswith("power:"))) or ref in parts: continue
            if s is None: notes.append(f"instance without symbol: {ref}"); continue
            parts[ref] = (val if val is not None else s["p"].get("Value", ""), fp if fp is not None else s["p"].get("Footprint", ""), {k: v for k, v in s["p"].items() if k.lower() not in SKIP_FIELDS and v.strip() and v != "~"})
    else:
        if "EESchema Schematic File" not in t[:200]: notes.append(f"not a KiCad schematic: {root}"); return parts
        def walk(path, ipath, depth):
            tt = get(path)
            if tt is None: notes.append(f"sheet missing: {path}"); return
            syms, sheets = parse_old(tt)
            for s in syms:
                r = s["ar"].get(ipath + "/" + s["ts"]) or s["ref"]
                if r and not r.startswith("#") and "?" not in r and r not in parts:
                    parts[r] = (s["value"], s["fp"], s["p"])
                elif r and "?" in r and not r.startswith("#"): notes.append(f"unannotated {r}")
            for f, ts in sheets: walk(join(path, f), ipath + "/" + ts, depth + 1)
        walk(root, "", 0)
    return parts

NOTPART = re.compile(r"(^|:)(MountingHole|Fiducial)|mounting[_ ]?hole", re.I)   # holes and fiducials are not parts (the designer's BOM.md leaves them out)
def board_parts(repo, sha, pcb, notes):
    """-> {ref: (value, footprint, {})} from a .kicad_pcb (KiCad 5 'module' or 6+ 'footprint' blocks). Footprints marked
    board_only / exclude_from_bom / dnp, references starting '#' or REF**, and holes / fiducials / logos / test points /
    net ties / solder jumpers are left out."""
    t = fetch(repo, sha, pcb); parts = {}
    if t is None: notes.append(f"fetch failed: {pcb}"); return parts
    for head in ("footprint", "module"):
        for a, b in sexp_blocks(t, head):
            blk = t[a:b]
            m = re.match(r'\((?:footprint|module)\s+"?([^"\s)]+)"?', blk)
            if not m: continue
            fp = m.group(1)
            ref = re.search(r'\(property\s+"Reference"\s+"([^"]*)"|\(fp_text\s+reference\s+"?([^"\s)]+)"?', blk)
            val = re.search(r'\(property\s+"Value"\s+"((?:[^"\\]|\\.)*)"|\(fp_text\s+value\s+"?((?:[^"\\]|\\.)*?)"?[\s)]', blk)
            r = (ref.group(1) or ref.group(2)) if ref else ""
            v = ((val.group(1) if val.group(1) is not None else val.group(2)) or "") if val else ""
            if not r or r.startswith("#") or "**" in r or NOTBOARD.search(fp) or r in parts: continue
            if re.search(r'\(attr[^)]*(board_only|exclude_from_bom|dnp)', blk): continue
            parts[r] = (v, fp, {})
    return parts

NOTBOARD = re.compile(r"(^|:)(MountingHole|Fiducial)|mounting[_ ]?hole|logo|TestPoint|NetTie|SolderJumper|Symbol:|Kibuzzard|Graphic", re.I)

def natkey(r): return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", r)]

def partlist(repo, sha, path):
    PL = []; cur = None; t = fetch(repo, sha, path) or ""
    for l in t.splitlines():
        m = re.match(r'^- "(.*)":\s*$', l)
        if m: cur = {"description": m.group(1)}; PL.append(cur); continue
        m = re.match(r'^\s+- (\w+): "(.*)"', l)
        if m and cur is not None: cur[m.group(1)] = m.group(2)
    return PL

def run(rid, repo, sha, roots, pl_path="", suffix=""):
    notes = []; rows = []; extra_cols = []
    PL = partlist(repo, sha, pl_path) if pl_path else []
    total = 0; nb = 0
    for root in roots:
        parts = board_parts(repo, sha, root, notes) if root.endswith(".kicad_pcb") else collect(repo, sha, root, notes)
        parts = {r: v for r, v in parts.items() if not NOTPART.search(v[1]) and not (NOTPART.search(v[0]) and not v[1])}
        if not parts: continue
        nb += 1; total += len(parts)
        g = collections.OrderedDict()
        for r in sorted(parts, key=natkey):
            v, f, ex = parts[r]
            g.setdefault((v, f), []).append((r, ex))
        for (v, f), lst in sorted(g.items(), key=lambda kv: natkey(kv[1][0][0])):
            ex = {}
            for _, e in lst:
                for k, val in e.items():
                    ex.setdefault(k, val)
                    if ex[k] != val: ex[k] = ex[k]                 # first value wins; grouping is by value+footprint only
            if PL:
                hit = [x for x in PL if x.get("footprint") == f and x.get("value") == v] or [x for x in PL if x.get("footprint") == f and "value" not in x]
                if hit:
                    ex.setdefault("description (lib/partlist.yaml)", hit[0]["description"])
                    if hit[0].get("mouser"): ex.setdefault("mouser (lib/partlist.yaml)", hit[0]["mouser"])
            for k in ex:
                if k not in extra_cols: extra_cols.append(k)
            rows.append([os.path.basename(root).rsplit(".", 1)[0], str(len(lst)), ", ".join(r for r, _ in lst), v, f, ex])
    if rows:
        clean = lambda s: str(s).replace("\t", " ").replace("\n", " ")
        with open(os.path.join(OUT, f"{rid}{suffix}.tsv"), "w", encoding="utf-8", newline="") as fh:
            fh.write("\t".join(["board", "qty", "references", "value", "footprint"] + extra_cols) + "\n")
            for r in rows: fh.write("\t".join(clean(x) for x in r[:5] + [r[5].get(k, "") for k in extra_cols]) + "\n")
    return [rid, str(nb), str(total), str(len(rows)), "; ".join(dict.fromkeys(notes))]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for l in sys.stdin:
        if not l.strip() or l.startswith("#"): continue
        f = l.rstrip("\n").split("\t")
        roots = [x for x in f[3].split(";") if x]
        if "--board" in sys.argv: roots = [x.rsplit(".", 1)[0] + ".kicad_pcb" for x in roots]
        print("\t".join(run(f[0], f[1], f[2], roots, "" if "--board" in sys.argv else (f[4] if len(f) > 4 else ""), "-board" if "--board" in sys.argv else "")), flush=True)
