#!/usr/bin/env python3
"""Panel and photo columns (d, 2026-09-26 16:52).

  python3 data/panel_photos.py < rows.tsv > out.tsv
  rows.tsv: id<TAB>repo<TAB>module_dir   (module_dir "." = the repo's root module)
  out.tsv:  id, panel, panel_basis, photos, photos_basis, build, build_basis

panel   "12HP · kicad + gerbers" | "1U 12HP · kicad" | "HP ? · svg" | "" (no panel files)
        Panel files are files whose path (inside the module's scope) says panel / faceplate /
        front plate / front panel, by type: kicad, eagle, easyeda, gerbers, svg, dxf, ai, pdf,
        fpd (Front Panel Designer), 3D (stl/step/scad/f3d/FreeCAD). Images are not panel sources.
        HP is MEASURED from a panel outline (KiCad Edge.Cuts, gerber outline layer, Eagle
        dimension layer, DXF, SVG size, PDF MediaBox) and accepted only when the outline is
        3U (127.5-129.5 mm high) or 1U (38.5-44 mm high) and the width is HP x 5.08 mm minus
        0-1 mm (Doepfer: 12HP = 60.6 mm). Otherwise HP is STATED: "12HP" in a panel file or
        folder name, or exactly one HP value in the module's own README. Measured wins over
        stated; a disagreement is written into panel_basis.
photos  space-separated /blob/ links to raster images in the module's scope that are photos or
        renders: not schematics, diagrams, footprints, icons, screenshots, plots, BOMs, gerber
        or layout images, build/placement maps, factory test references, images in firmware /
        software / releases folders, and not panel drawings (png/gif/svg named panel/faceplate).
        Measured and stated HP that disagree give "HP ?" with both in panel_basis.
build   build-guide links (d, 2026-09-26 17:11): documents (pdf, md, html, txt, docx, odt) whose file
        name says build / assembly / construction / instructions / how-to / soldering / kit guide, or
        that sit in a folder named so; plus, for a series of build-step photos (images in a build /
        assembly / kit / steps folder, or 4+ numbered images beside a build document), ONE /tree/ link
        per folder - those images leave the photo column. READMEs, BOMs, iBOMs, schematics, user
        manuals and anything under firmware / software / source folders are not build guides;
        "assembled" folders are finished-module photos and stay in photo.
Module scope comes from data/modulefiles.sh. When the module folder is a generic subfolder
(pcb, hardware, kicad, eagle, electronics, board, ...) its parent folder is searched too,
because panels and photos usually sit beside it.
"""
import concurrent.futures as cf, csv, io, math, os, re, subprocess, sys, urllib.parse, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import photo_check as PC; CHECK = "--no-content-check" not in sys.argv
except ImportError:          # no Pillow: name rules only, and photos_basis says so
    CHECK = False
CHECKS = []   # (row, file, keep|drop, measurements) -> data/photo-checks.tsv
EXCL = set()
if os.path.exists(os.path.join(HERE, "photo-excludes.tsv")):
    for _l in open(os.path.join(HERE, "photo-excludes.tsv"), encoding="utf-8").read().splitlines()[1:]:
        if _l.strip(): _f = _l.split("\t"); EXCL.add((_f[0], _f[1]))
INV = {r["repo"]: r for r in csv.DictReader(open(os.path.join(HERE, "inventory.tsv")), delimiter="\t")}
PANELW = re.compile(r"panel|face[_ -]?plate|front[_ -]?plate|frontplate", re.I)
GENERIC = re.compile(r"^(pcbs?|hardware|kicad|eagle|electronics?|boards?|main|main[_ -]?board|schematics?|kicad[_ -]?project|kicad[_ -]?files|pcb[_ -]?files|cad|design|production|fab|gerbers?)$", re.I)
IMG = re.compile(r"\.(jpe?g|png|gif|webp)$", re.I)
NOT_PHOTO = re.compile(r"sch|circuit|diagram|block|wiring|layout|footprint|symbol|icon|logo|favicon|badge|screen|scope|graph|plot|chart|bom|gerber|drill|silk|mask|copper|dimension|drawing|pin_?out|datasheet|manual|legend|label|template|thumb|/libs?/|librar|\.pretty/|/fonts?/|/assets/|\.github/|node_modules|/datasheets?/|waveform|trace|oscillo|spectrum|response|bode|sim(ulation)?[^a-z]|ltspice|falstad|kicad_mod|/factory/|/tests?/|calibrat|build_?map|placement|/(firmware|software|releases?|src|code|web|app|drivers?|art)/|/doc/res/|controls?\.|concept|calc|art[-_ ]?card|artcard|tinyalloc|zadig|device[-_ ]?manager", re.I)
BUILD_NAME = re.compile(r"build|assembl|construct|instruction|how[-_ ]?to|solder|kit[-_ ]?guide|build[-_ ]?guide|step[-_ ]?by[-_ ]?step", re.I)
BUILD_DIR = re.compile(r"(^|/)(build(?!s?/)[^/]*|build|assembly[^/]*|assembling[^/]*|construct[^/]*|instructions?|kit|steps?|build[-_ ]?guide[^/]*)/", re.I)   # not "assembled" (finished-module photos)
DOC = re.compile(r"\.(pdf|md|markdown|html?|txt|docx?|odt|rst)$", re.I)
NOT_BUILD_NAME = re.compile(r"user[ _-]?(manual|guide)|readme|bom|bill[ _-]?of|sch(ematic|em)?[^a-z]|schematic|datasheet|license|cmake|cache|order|[^a-z]dev[^a-z]|setup|install", re.I)   # file name only
NOT_BUILD = re.compile(r"ibom|/(firmware|software|src|code|lib|libraries|\.github|uf2[^/]*|docker[^/]*|node_modules|test[s]?)/|uf2|docker|programming|toolchain|compile|makefile|changelog|license", re.I)
PANEL_DRAW = re.compile(r"panel|face[_ -]?plate|front[_ -]?plate", re.I)
HP_NAME = re.compile(r"(?<![0-9a-z])(\d{1,2})\s?[-_]?hp(?![a-z])", re.I)
HP_TEXT = re.compile(r"(?<![0-9.])(\d{1,2})\s?(?:-\s?)?hp\b", re.I)

def kind(p):
    b = p.lower()
    if b.endswith(".kicad_pcb"): return "kicad"
    if b.endswith(".brd"): return "eagle"
    if b.endswith(".json") and "easyeda" in b or re.search(r"(pcb|panel)[^/]*\.json$", b): return "easyeda"
    if re.search(r"\.(gbr|ger|gtl|gbl|gko|gm\d*|gml|gto|gbo|gts|gbs|gtp|gbp|drl|xln|cmp|sol|pho|art)$", b): return "gerbers"
    if b.endswith(".zip") and "-backups/" not in b: return "gerbers"
    if b.endswith(".svg"): return "svg"
    if b.endswith(".dxf"): return "dxf"
    if re.search(r"\.(ai|eps)$", b): return "ai"
    if b.endswith(".pdf"): return "pdf"
    if b.endswith(".fpd"): return "fpd"
    if re.search(r"\.(stl|step|stp|scad|f3d|fcstd|3mf)$", b): return "3D"
    return None
ORDER = ["kicad", "eagle", "easyeda", "gerbers", "svg", "dxf", "ai", "pdf", "fpd", "3D"]

def fetch(repo, path, limit=None):
    sha = INV[repo]["head_sha"].strip()
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/" + urllib.parse.quote(path)
    cmd = ["curl", "-sS", "-m", "60", "--fail", url]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout if r.returncode == 0 else None

# ---------- outline measurement: every function returns a list of (w, h) in mm ----------
def bbox(pts):
    if len(pts) < 2: return []
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return [(max(xs) - min(xs), max(ys) - min(ys))]

def kicad_outline(t):
    pts = []
    # one graphic item at a time: split at each "(gr_" so a match never runs into the next item
    for chunk in re.split(r"(?=\(gr_)", t)[1:]:
        m = re.match(r"\(gr_(line|rect|arc|poly|circle|curve)\b", chunk)
        if not m: continue
        body = chunk[:4000]
        lay = re.search(r"\(layer\s+\"?([^\s\")]+)", body)
        if not lay or lay.group(1) != "Edge.Cuts": continue
        for x, y in re.findall(r"\((?:start|end|mid|center|xy)\s+(-?[\d.]+)\s+(-?[\d.]+)\)", body):
            pts.append((float(x), float(y)))
    return bbox(pts)

def gerber_outline(t):
    fs = re.search(r"%FS([LTD]?)([AI])X(\d)(\d)Y(\d)(\d)\*%", t)
    zs, xi, xd = (fs.group(1), int(fs.group(3)), int(fs.group(4))) if fs else ("L", 2, 4)
    sc = 25.4 if "%MOIN*%" in t else 1.0
    def v(s):
        neg = s.startswith("-"); s = s.lstrip("+-")
        if zs == "T": s = s.ljust(xi + xd, "0")
        return (-1 if neg else 1) * int(s) / 10 ** xd * sc
    pts = []; x = y = None
    for st in t.replace("\n", "").replace("\r", "").split("*"):
        m = re.match(r"^(?:G0?[123])?(?:X([+-]?\d+))?(?:Y([+-]?\d+))?(?:I[+-]?\d+)?(?:J[+-]?\d+)?D0?[12]$", st)
        if not m: continue
        if m.group(1): x = v(m.group(1))
        if m.group(2): y = v(m.group(2))
        if x is not None and y is not None: pts.append((x, y))
    return bbox(pts)

def eagle_outline(t):
    pts = []
    for m in re.finditer(r"<wire\b[^>]*>", t):
        w = m.group(0)
        if re.search(r'layer="20"', w):
            a = dict(re.findall(r'(\w+)="([-\d.]+)"', w))
            if all(k in a for k in ("x1", "y1", "x2", "y2")):
                pts += [(float(a["x1"]), float(a["y1"])), (float(a["x2"]), float(a["y2"]))]
    return bbox(pts)

def dxf_outline(t):
    L = [l.strip() for l in t.splitlines()]
    def hdr(name):
        try:
            i = L.index(name); vals = {}
            for j in range(i + 1, i + 12, 2):
                if L[j] in ("10", "20"): vals[L[j]] = float(L[j + 1])
            return vals
        except (ValueError, IndexError): return None
    lo, hi = hdr("$EXTMIN"), hdr("$EXTMAX")
    out = []
    if lo and hi and "10" in lo and "10" in hi:
        w, h = hi["10"] - lo["10"], hi["20"] - lo["20"]
        if 0 < w < 1e6 and 0 < h < 1e6: out += [(w, h), (w * 25.4, h * 25.4)]
    if not out:   # header extents missing or uninitialised (+-1e20): scan entity vertices
        E = L[L.index("ENTITIES"):] if "ENTITIES" in L else L
        num = lambda v: re.match(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$", v) and abs(float(v)) < 1e6
        xs = [float(E[i + 1]) for i in range(len(E) - 1) if E[i] == "10" and num(E[i + 1])]
        ys = [float(E[i + 1]) for i in range(len(E) - 1) if E[i] == "20" and num(E[i + 1])]
        if xs and ys:
            w, h = max(xs) - min(xs), max(ys) - min(ys); out += [(w, h), (w * 25.4, h * 25.4)]
    return out

def svg_outline(t):
    m = re.search(r"<svg\b[^>]*>", t, re.S)
    if not m: return []
    tag = m.group(0)
    def dim(a):
        mm = re.search(a + r'="\s*([\d.]+)\s*(mm|cm|in|px|pt)?\s*"', tag)
        if not mm: return None
        v, u = float(mm.group(1)), (mm.group(2) or "px")
        return v * {"mm": 1, "cm": 10, "in": 25.4, "px": 25.4 / 96, "pt": 25.4 / 72}[u]
    w, h = dim("width"), dim("height")
    out = []
    if w and h: out.append((w, h))
    vb = re.search(r'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', tag)
    if vb: out += [(float(vb.group(1)), float(vb.group(2))), (float(vb.group(1)) * 25.4 / 96, float(vb.group(2)) * 25.4 / 96)]
    return out

def pdf_outline(b):
    m = re.search(rb"/MediaBox\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\]", b)
    if not m: return []
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    return [((x1 - x0) * 25.4 / 72, (y1 - y0) * 25.4 / 72)]

OUTLINE_GERB = re.compile(r"edge[_.]?cuts|\.gko$|\.gm\d*$|\.gml$|outline|boardoutline", re.I)
def measure(name, data):
    b = name.lower(); t = None
    try:
        if b.endswith(".kicad_pcb"): return kicad_outline(data.decode("utf-8", "replace"))
        if b.endswith(".brd"): return eagle_outline(data.decode("utf-8", "replace"))
        if b.endswith(".dxf"): return dxf_outline(data.decode("latin-1"))
        if b.endswith(".svg"): return svg_outline(data.decode("utf-8", "replace"))
        if b.endswith(".pdf"): return pdf_outline(data)
        if OUTLINE_GERB.search(b): return gerber_outline(data.decode("latin-1"))
        if b.endswith(".zip"):
            z = zipfile.ZipFile(io.BytesIO(data)); out = []
            for n in z.namelist():
                if OUTLINE_GERB.search(n.rsplit("/", 1)[-1]): out += gerber_outline(z.read(n).decode("latin-1"))
                elif n.lower().endswith(".kicad_pcb"): out += kicad_outline(z.read(n).decode("utf-8", "replace"))
            return out
    except Exception:
        return []
    return []

def to_hp(w, h):
    """(label, hp) if (w, h) is a eurorack panel outline, else None; accepts a rotated panel."""
    for W, H in ((w, h), (h, w)):
        fmt = "3U" if 127.5 <= H <= 129.5 else "1U" if 38.5 <= H <= 44.0 else None
        if not fmt: continue
        hp = round(W / 5.08)
        if hp >= 1 and -0.3 <= hp * 5.08 - W <= 1.0: return fmt, hp
    return None

def scope_files(repo, md):
    out = subprocess.run(["bash", os.path.join(HERE, "modulefiles.sh"), repo, md], capture_output=True, text=True).stdout.splitlines()
    if not out: return ".", []
    scope = out[0].split("\t", 1)[1] if out[0].startswith("SCOPE") else md
    files = out[1:]
    tree = open(os.path.join(HERE, "trees", repo.replace("/", "_") + ".txt")).read().splitlines()
    # generic subfolder: add its parent's files that are not in another module's own folder
    if scope not in (".", "") and GENERIC.match(scope.rstrip("/").rsplit("/", 1)[-1]):
        parent = scope.rstrip("/").rsplit("/", 1)[0] if "/" in scope.rstrip("/") else "."
        if parent == ".":
            if len(subprocess.run(["bash", os.path.join(HERE, "moduledirs.sh"), repo], capture_output=True, text=True).stdout.split("\n")) <= 2:
                files = sorted(set(files) | {f for f in tree})
        else:
            files = sorted(set(files) | {f for f in tree if f.startswith(parent + "/")})
    return scope, files

def norm(name):
    b = name.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
    b = re.sub(r"\d{4}-\d{2}-\d{2}(_\d+)?|\bv\d+(\.\d+)*\b|\brev\s?\w+\b|panel|front|face ?plate|pcb|main|board|gerbers?|final|_bom|\bbom\b", " ", b)
    return re.sub(r"[^a-z0-9]", "", b)

def row(rid, repo, md, hint=""):
    if repo not in INV: return [rid, "", "repo not in inventory", "", "", "", ""]
    br = INV[repo].get("default_branch", "main").strip() or "main"
    scope, files = scope_files(repo, md)
    base = "" if scope in (".", "") else scope.rstrip("/") + "/"
    rel = lambda f: f[len(base):] if base and f.startswith(base) else f
    # a folder shared by several rows (flat collections): keep only files named after this
    # row's own board(s) - hint is "|"-separated board file names or the module name
    stems = [norm(h) for h in hint.split("|") if norm(h)] if hint else []
    if stems:
        files = [f for f in files if any(norm(f).startswith(st) or st.startswith(norm(f)) and len(norm(f)) >= 4 for st in stems)]
    # ---- panel ----
    pf = [f for f in files if PANELW.search(rel(f)) and kind(f)]
    kinds = sorted({kind(f) for f in pf}, key=ORDER.index)
    panel = basis = ""
    if pf:
        meas = []
        cand = [f for f in pf if re.search(r"\.(kicad_pcb|brd|dxf|svg|pdf|zip)$", f, re.I) or OUTLINE_GERB.search(f.rsplit("/", 1)[-1])]
        cand = sorted(cand, key=lambda f: (not f.lower().endswith((".kicad_pcb", ".brd")), f))[:6]
        for f in cand:
            data = fetch(repo, f)
            if not data: continue
            for w, h in measure(f, data):
                r = to_hp(w, h)
                if r: meas.append((r, f, w, h)); break
        stated = sorted({int(m.group(1)) for f in pf + ([scope] if scope != "." else []) for m in HP_NAME.finditer(f)})
        src = ""
        if not stated:
            rd = [f for f in files if re.match(r"(?i)(readme|index)(\.(md|txt|rst|markdown))?$", f.rsplit("/", 1)[-1]) and (f.rsplit("/", 1)[0] + "/" == base or (not base and "/" not in f))]
            for f in rd[:1]:
                txt = (fetch(repo, f) or b"").decode("utf-8", "replace")
                vals = sorted({int(v) for v in HP_TEXT.findall(txt) if 1 <= int(v) <= 104})
                if len(vals) == 1: stated, src = vals, f"README {f}"
                elif vals: src = f"README {f} names several HP values {vals} - not used"
        else:
            src = "file/folder name"
        hps = sorted({(r[0][0], r[0][1]) for r in meas})
        if len(hps) == 1:
            (fmt, hp) = hps[0]; f, w, h = meas[0][1], meas[0][2], meas[0][3]
            label = (f"1U {hp}HP" if fmt == "1U" else f"{hp}HP")
            basis = f"measured {w:.2f} x {h:.2f} mm outline in {f}"
            if stated and stated != [hp]:   # sources disagree: do not pick one (d 2026-09-26)
                label = "HP ?"; basis = f"CONFLICT: measured {hp}HP ({w:.2f} x {h:.2f} mm outline in {f}) but stated {stated} ({src})"
            elif stated: basis += f"; agrees with {src} ({stated[0]}HP)"
        elif len(hps) > 1:
            label = "HP ?"; basis = "outlines disagree: " + ", ".join(f"{fmt} {hp}HP in {f}" for ((fmt, hp), f, _, _) in meas)
        elif len(stated) == 1:
            label = f"{stated[0]}HP"; basis = f"stated in {src}" + (" (" + ", ".join(f for f in pf if HP_NAME.search(f))[:200] + ")" if src == "file/folder name" else "")
        else:
            label = "HP ?"; basis = "no measurable outline" + (f"; {src}" if src else "") + (f"; names state {stated}" if len(stated) > 1 else "")
        panel = f"{label} · {' + '.join(kinds)}"
        basis += f" | panel files ({len(pf)}): " + ", ".join(pf[:8]) + (" ..." if len(pf) > 8 else "")
    # ---- build guides ----
    bdocs = [f for f in files if DOC.search(f) and (BUILD_NAME.search(rel(f).rsplit("/", 1)[-1]) or BUILD_DIR.search("/" + rel(f)))
             and not NOT_BUILD.search("/" + rel(f)) and not NOT_BUILD_NAME.search(rel(f).rsplit("/", 1)[-1])]
    im = [f for f in files if IMG.search(f)]
    bimg = [f for f in im if BUILD_DIR.search("/" + rel(f)) or re.search(r"assembly|assembling|build[-_ ]?step|(^|[^a-z])step[-_ ]?\d", rel(f).rsplit("/", 1)[-1], re.I)]
    # numbered photo series ("1-tools.jpg", "10-teensy.jpg") beside a build document are its steps
    if bdocs:
        numbered = [f for f in im if re.match(r"\d{1,3}[-_ .]", f.rsplit("/", 1)[-1]) and f not in bimg]
        if len(numbered) >= 4: bimg += numbered
    bdirs = sorted({f.rsplit("/", 1)[0] if "/" in f else "." for f in bimg})
    blinks = [f"https://github.com/{repo}/blob/{br}/{urllib.parse.quote(f, safe='/')}" for f in bdocs] + \
             [f"https://github.com/{repo}/tree/{br}/{urllib.parse.quote(d, safe='/')}" for d in bdirs if d != "."]
    bbasis = (f"{len(bdocs)} document(s)" + (f", {len(bimg)} build-step photo(s) in {len(bdirs)} folder(s)" if bimg else "")) if blinks else ""
    # ---- photos ----
    im = [f for f in im if f not in set(bimg)]
    ph = [f for f in im if not NOT_PHOTO.search("/" + rel(f)) and not (PANEL_DRAW.search(rel(f)) and not re.search(r"\.jpe?g$", f, re.I))]
    if re.search(r"schem", repo.split("/")[1], re.I): ph = []          # a repo of schematics (bastlSchematics) has no photos
    ph = [f for f in ph if (repo, f) not in EXCL]                          # d's hand rulings (data/photo-excludes.tsv)
    # content check (photo_check.py): drop schematics, layout plots, diagrams, screenshots, artwork
    dropped = []
    if CHECK and ph:
        kept = []
        for f in ph:
            data = fetch(repo, f)
            ok, why = PC.check(data, f) if data else (True, "not fetched")
            (kept if ok else dropped).append(f)
            CHECKS.append((rid, f, "keep" if ok else "drop", why))
        ph = kept
    links = " ".join(f"https://github.com/{repo}/blob/{br}/{urllib.parse.quote(f, safe='/')}" for f in ph)
    pbasis = f"{len(ph)} of {len(im)} images in scope" + (f"; {len(dropped)} dropped by content check (not photos)" if dropped else "") + (f"; left out: " + ", ".join(sorted({f.rsplit('/', 1)[-1] for f in im if f not in ph})[:6]) if len(im) > len(ph) else "")
    return [rid, panel, basis, links, pbasis if im else "", " ".join(blinks), bbasis]

if __name__ == "__main__":
    rows = [l.rstrip("\n").split("\t") for l in sys.stdin if l.strip()]
    ck = [a[len("--checks="):] for a in sys.argv if a.startswith("--checks=")]
    with cf.ThreadPoolExecutor(8) as ex:
        for out in ex.map(lambda r: row(*r[:4]), rows):
            print("\t".join(x.replace("\t", " ").replace("\n", " ") for x in out), flush=True)
    if ck:
        with open(ck[0], "w") as fh:
            fh.write("id\tfile\tresult\tmeasured\n" + "".join("\t".join(c) + "\n" for c in sorted(CHECKS)))
