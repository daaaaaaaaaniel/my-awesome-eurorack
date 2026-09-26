#!/usr/bin/env python3
"""Build the static site from data/modules.tsv into docs/.

    python3 site/build.py            # writes docs/

Raw data only: every value shown comes straight from a column of
data/modules.tsv. Nothing is normalised or guessed here; a blank cell
renders as "not determined" and gets its own filter bucket. The mapping
tables (type -> category, license -> family) are a later layer.

No dependencies beyond the standard library. Output is plain HTML + one
vanilla-JS filter script; the index embeds the table as JSON.
"""
import csv, hashlib, html, json, os, re, shutil, sys
from collections import Counter, defaultdict
from urllib.parse import quote
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(ROOT, "data", "modules.tsv")
TYPEMAP = os.path.join(ROOT, "data", "type-categories.tsv")
ALIASES = os.path.join(ROOT, "data", "maker-aliases.tsv")   # site-side only: alias -> maker
LICMAP = os.path.join(ROOT, "data", "license-map.tsv")      # raw license string -> grants

FAMILY_LABEL = {"none-found": "no license found", "none-named": "open source, no license named",
                "not-open": "not open source", "custom": "custom terms", "unclear": "unclear"}
TERMS_LABEL = {"permissive": "permissive", "copyleft": "copyleft / share-alike", "non-commercial": "non-commercial",
               "public-domain": "public domain", "custom": "custom terms", "none-named": "open source, no license named",
               "none-found": "no license found", "not-open": "not open source", "unclear": "unclear"}
SCOPE_LABEL = {"unstated": "whole repository (scope not stated)", "hardware": "hardware", "software": "software / firmware",
               "panel": "panel", "docs": "documentation", "hardware+software": "hardware and software"}
SCOPE_SHORT = {"hardware": "hw", "software": "sw", "panel": "panel", "docs": "docs", "hardware+software": "hw+sw"}
OUT = os.path.join(ROOT, "docs")
REPO_URL = "https://github.com/daaaaaaaaaniel/my-awesome-eurorack"
SITE_TITLE = "Open-source Eurorack modules"

# ---------------------------------------------------------------- data

def url_maker(r):
    """Maker used in a module page's URL: the last " + " part of the credit, as spelled in the data."""
    parts = [m.strip() for m in re.split(r"\s+\+\s+", r["creator"]) if m.strip()]
    return parts[-1] if parts else r["creator"]

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"

SHARED = Counter()   # (repo, module_dir) -> number of rows sharing that folder

def load():
    with open(TSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        for k, v in r.items():
            r[k] = (v or "").strip()
    # slug: maker + module name; append id only on collision. With several makers ("Original + Porter")
    # the URL uses only the last one - the maker of this build (d, 2026-09-26 15:32); displayed fields keep the full credit.
    seen = Counter(slugify(url_maker(r) + " " + r["module_name"]) for r in rows)
    for r in rows:
        s = slugify(url_maker(r) + " " + r["module_name"])
        r["slug"] = s if seen[s] == 1 else f"{s}-{r['id']}"
    SHARED.update(Counter((r["repo"], r["module_dir"]) for r in rows))
    return rows

def load_typemap():
    """type string -> (tags, status). Missing file = no Type facet."""
    if not os.path.exists(TYPEMAP):
        return {}
    with open(TYPEMAP, newline="", encoding="utf-8") as f:
        return {r["type"]: ([t.strip() for t in r["tags"].split(",") if t.strip()], r["status"])
                for r in csv.DictReader(f, delimiter="\t")}

def tags_of(r, typemap):
    tags, _ = typemap.get(r["type"], ([], "UNMAPPED"))
    return tags or ["not mapped"]

def load_licmap():
    """raw license string -> [grant dicts], from data/license-map.tsv (empty = no license facets)."""
    if not os.path.exists(LICMAP):
        return {}
    out = defaultdict(list)
    with open(LICMAP, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            out[r["license"]].append({k: (v or "").strip() for k, v in r.items()})
    for k in out:
        out[k].sort(key=lambda g: int(g["seq"] or 0))
    return dict(out)

def grants_of(r, licmap):
    gs = licmap.get(r["license"])
    if gs is None:   # string not in the map yet
        return [dict(family="not mapped", version="", scope="unstated", scope_raw="", terms="not mapped", status="", note="")]
    return gs

def family_label(g):
    return FAMILY_LABEL.get(g["family"], g["family"])

def version_label(g):
    """As the repos write it: 'GPL v3', 'CERN-OHL-P v2', 'CC BY-SA 4.0'."""
    if not g["version"]:
        return ""
    return ("v" if g["family"] in ("GPL", "CERN-OHL-P", "CERN-OHL-S", "CERN-OHL-W") and "." not in g["version"] else "") + g["version"]

def grant_chip(g):
    lab = family_label(g) + (f' {version_label(g)}' if g["version"] else "")
    if g["scope"] in SCOPE_SHORT:
        lab += f' · {SCOPE_SHORT[g["scope"]]}'
    cls = "chip lic" + (" warn" if g["terms"] in ("not-open",) else " dim" if g["terms"] in ("none-found", "not mapped") else "")
    return f'<span class="{cls}">{e(lab)}</span>'

def load_aliases():
    if not os.path.exists(ALIASES):
        return {}
    with open(ALIASES, newline="", encoding="utf-8") as f:
        return {r["alias"].strip(): r["maker"].strip() for r in csv.DictReader(f, delimiter="\t") if r["alias"].strip()}

MAKER_ALIAS = load_aliases()

COUNTS = re.compile(r"smd=(\d+)\s+tht_passive=(\d+)\s+tht_to=(\d+)\s+tht_ic=(\d+)(?:\s*\(panel excluded\))?\s*smd_ic=(\d+)")

def counts_of(r):
    """Board component counts from comp_basis, only when the detector counted them from a board
    file or machine-readable BOM (comp_conf = Strong). Panel hardware (pots, jacks, switches,
    LEDs, headers) is excluded by the detector, so this is board parts, not a shopping list."""
    if r["comp_conf"] != "Strong":
        return None
    m = COUNTS.search(r["comp_basis"])
    if not m:
        return None
    smd, thtp, thto, thtic, smdic = map(int, m.groups())
    f = re.search(r"files=(\d+)", r["comp_basis"])
    return dict(smd=smd, smd_ic=smdic, tht=thtp, tht_to=thto, tht_ic=thtic, total=smd + smdic + thtp + thto + thtic,
                files=int(f.group(1)) if f else 1)

def makers_of(r):
    """Split a joined creator string ("Sluisbrinkie + poetaster") into its makers,
    exact strings, deduplicated, order kept (d, 2026-09-26 13:26). The raw creator
    string is still what the card and page show."""
    out = []
    for m in re.split(r"\s+\+\s+", r["creator"]):
        m = MAKER_ALIAS.get(m.strip(), m.strip())
        if m and m not in out:
            out.append(m)
    return out

def credit_parts(r):
    """The creator string as shown, one [shown, maker] pair per " + " part: `shown` keeps the
    repo's spelling, `maker` is the alias-folded name the Maker filter uses (so the link lands)."""
    return [[m.strip(), MAKER_ALIAS.get(m.strip(), m.strip())] for m in re.split(r"\s+\+\s+", r["creator"]) if m.strip()]

def maker_href(m, prefix=""):
    return f"{prefix}?maker={quote(m, safe='')}"

def is_url(s):
    return s.startswith("http://") or s.startswith("https://")

def bucket_components(v):
    return v if v in ("SMD", "THT", "both") else "not determined"

def files_of(r):
    """Which kinds of files the row records. Raw column semantics:
    schematic: URL or 'x' = present; layout: free text naming EDA tool /
    gerbers; bom: 'y' / '-'."""
    out = []
    if r["schematic"] and r["schematic"] not in ("n/a",):
        out.append("schematic")
    lay = r["layout"].lower()
    if "kicad" in lay: out.append("kicad")
    if "eagle" in lay: out.append("eagle")
    if "gerber" in lay: out.append("gerbers")
    if lay and not any(t in lay for t in ("kicad", "eagle", "gerber")):
        out.append("other layout")
    if r["bom"] == "y": out.append("bom")
    return out

# ---------------------------------------------------------------- html

CSS = r"""
:root{--bg:#fbfaf7;--fg:#1d1c1a;--mute:#6b6862;--line:#e3e0d8;--card:#fff;--acc:#b5451b;--chip:#f1eee6;--chip-on:#1d1c1a;--chip-on-fg:#fff}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#171614;--fg:#ebe8e1;--mute:#9b978e;--line:#2c2a26;--card:#1f1e1b;--acc:#f08a5b;--chip:#26241f;--chip-on:#ebe8e1;--chip-on-fg:#171614}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:inherit}a:hover{color:var(--acc)}
header.top{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;padding:14px 16px;border-bottom:1px solid var(--line)}
header.top h1{font-size:18px;margin:0;font-weight:650}header.top h1 a{text-decoration:none}
header.top .sub{color:var(--mute);font-size:13px}
header.top nav{margin-left:auto;font-size:13px}header.top nav a{margin-left:14px}
.wrap{max-width:1400px;margin:0 auto;padding:16px}
.layout{display:grid;grid-template-columns:230px minmax(0,1fr);gap:24px}
#out{overflow-x:auto}
@media(max-width:640px){.layout{grid-template-columns:1fr}}
aside{font-size:13px}aside details{border-top:1px solid var(--line);padding:6px 0}
aside summary{cursor:pointer;font-weight:600;padding:4px 0;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:6px}
aside summary>span:first-child{flex:1}aside summary::-webkit-details-marker{display:none}
.moderow{font-size:11px;margin:2px 0 4px}
.moderow .mode{margin-right:8px}
.seg{display:inline-flex;vertical-align:middle;border:1px solid var(--mute);border-radius:6px;overflow:hidden;font-weight:400;font-size:11px;line-height:1}
.seg label{display:inline-flex;padding:0;margin:0;cursor:pointer}
.seg input{position:absolute;opacity:0;width:0;height:0;margin:0;-webkit-appearance:none;appearance:none}
.seg span{display:block;padding:3px 8px;color:var(--mute);background:var(--card);transition:background .12s,color .12s}
.seg label+label span{border-left:1px solid var(--mute)}
.seg input:checked+span{background:var(--chip-on);color:var(--chip-on-fg)}
.seg input:focus-visible+span{outline:2px solid var(--acc);outline-offset:-2px}
.seg.off{opacity:.45;pointer-events:none}

aside summary::after{content:"▾";color:var(--mute)}details[open]>summary::after{content:"▴"}
aside label{display:flex;gap:6px;align-items:center;padding:2px 0;cursor:pointer}
aside label .n{margin-left:auto;color:var(--mute);font-variant-numeric:tabular-nums}
aside input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);font:inherit;margin-bottom:10px}
.maker-list{max-height:260px;overflow:auto}
.toolbar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-bottom:12px;font-size:13px;color:var(--mute)}
.toolbar select,.toolbar button{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer;-webkit-appearance:none;appearance:none}
.toolbar button[aria-pressed=true]{background:var(--chip-on);color:var(--chip-on-fg);border-color:var(--chip-on)}
.toolbar .clear{margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.card .name{font-weight:650;font-size:15px}.card .name a{text-decoration:none}
.card .maker{color:var(--mute);font-size:13px}.card .parts{float:right;color:var(--mute);font-size:12px;font-variant-numeric:tabular-nums}
.card .type{font-size:13px;margin:2px 0 6px}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:auto}
.chip{font-size:11px;padding:2px 7px;border-radius:999px;background:var(--chip);color:var(--fg);white-space:nowrap}
.chip.warn{background:var(--acc);color:#fff}.chip.tag{background:transparent;border:1px solid var(--line)}.chip.lic{background:var(--chip);border:1px dashed var(--mute)}
table.grants{border-collapse:collapse;font-size:13px;width:100%;margin:6px 0 0}table.grants th,table.grants td{text-align:left;padding:4px 8px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}table.grants th{color:var(--mute);font-weight:500}.chip.dim{color:var(--mute)}
table.list{width:100%;border-collapse:collapse;font-size:13px}
table.list th,table.list td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
table.list td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}table.list td:nth-child(8){white-space:nowrap}table.list th[data-k=parts],table.list th[data-k=hp]{text-align:right}
aside label.solo{padding:4px 0 10px;font-weight:500}.links li{margin:2px 0;word-break:break-word}
table.list th{position:sticky;top:0;background:var(--bg);cursor:pointer;white-space:nowrap}
table.list th[data-dir]::after{content:" ▴"}table.list th[data-dir=desc]::after{content:" ▾"}
.mute{color:var(--mute)}.small{font-size:13px}
.nd{color:var(--mute);font-style:italic}
/* detail page */
.detail h1{font-size:26px;margin:4px 0 2px}.detail .maker{font-size:16px;color:var(--mute);margin-bottom:16px}
.detail .cols{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:28px}
@media(max-width:800px){.detail .cols{grid-template-columns:1fr}}
dl.spec{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;margin:0 0 20px;font-size:14px}
dl.spec dt{color:var(--mute)}dl.spec dd{margin:0;overflow-wrap:anywhere}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:14px;font-size:14px}
.box h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);margin:0 0 8px}
.box ul{margin:0;padding-left:18px}.box li{margin:3px 0;overflow-wrap:anywhere}
.ev dt{font-weight:600;font-size:13px;margin-top:8px}.ev dd{margin:2px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;color:var(--fg)}
.more{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.schem .url{word-break:break-all;margin:0 0 8px}.schem .view{background:#fff;border-radius:4px;overflow:hidden}
.schem img{display:block;max-width:100%;height:auto;margin:0 auto}.pdfpage{background:#fff}.pdfpage+.pdfpage{border-top:1px solid #d8d4ca}
.pdfpage canvas{display:block;width:100%;height:auto}.pdfframe{display:block;width:100%;height:min(85vh,1100px);min-height:480px;border:0;background:#525659}.pdfstatus{margin:0;padding:10px 12px;color:#6b6862;font-size:13px}
.notice{border-left:3px solid var(--acc);padding:8px 12px;font-size:13px;color:var(--mute);margin:20px 0}
footer{padding:24px 16px;border-top:1px solid var(--line);color:var(--mute);font-size:12.5px;text-align:center}
"""

BUILT = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

def _h(text):
    """Short content hash for cache-busting asset URLs (site.css?v=..., site.js?v=...)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
CSS_V = _h(CSS)

def page(title, body, rel, desc="", stamp=False):
    """rel = relative path prefix back to docs/ root ('' or '../../').
    stamp: put the build time in the footer. Only the index and about pages get it, so an
    unchanged module page produces an identical file (and no new git object) on rebuild."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="stylesheet" href="{rel}site.css?v={CSS_V}">
</head><body>
<header class="top"><h1><a href="{rel}">{SITE_TITLE}</a></h1>
<span class="sub">a reference table of buildable DIY modules, every cell traced to a file in its repo</span>
<nav><a href="{rel}about.html">about</a><a href="{REPO_URL}">data on GitHub</a></nav></header>
<div class="wrap">{body}</div>
<footer>Generated{(" " + BUILT) if stamp else ""} from <a href="{REPO_URL}/blob/website/data/modules.tsv">data/modules.tsv</a>.
Third-party designs: check the source repository before ordering parts.</footer>
</body></html>"""

def e(s):
    return html.escape(s)

def nd(s, fallback="not determined"):
    return e(s) if s else f'<span class="nd">{fallback}</span>'

def short_url(s, n=70):
    s = re.sub(r"^https?://(www\.)?", "", s)
    return s if len(s) < n else s[:n-3] + "…"

def schem_name(u):
    return os.path.basename(u.split("?")[0]) or u

# ---- Panel / HP / photos / build guides (d, 2026-09-26 17:21), from the panel, photos, build columns
# (working branch 968cfd9 / d5953b8; rules in CLAUDE.md "The deliverable", evidence in *_basis).
def hp_of(r):
    """(number or None, display text): '12HP', '1U 22HP', '?' (panel files but HP not determined), '' (no panel files)."""
    p = (r.get("panel") or "").strip()
    m = re.match(r"(?:(1U)\s+)?(\d+(?:\.\d+)?)HP\b", p)
    if m:
        return float(m.group(2)), (m.group(1) + " " if m.group(1) else "") + m.group(2) + "HP"
    return (None, "?") if p else (None, "")

def panel_sources(r):
    p = r.get("panel") or ""
    return [x.strip() for x in p.split("·", 1)[1].split("+") if x.strip()] if "·" in p else []

def panel_files(r):
    """Panel file paths (repo-relative) listed in panel_basis, and the total the basis states."""
    m = re.search(r"panel files \((\d+)\): (.*)$", r.get("panel_basis") or "")
    if not m:
        return [], 0
    n, files = int(m.group(1)), [x.strip() for x in m.group(2).split(", ") if x.strip()]
    if len(files) > n:                       # a comma inside a filename: don't guess
        return [], n
    if len(files) < n and files and files[-1].endswith(("…", "...")):
        files = files[:-1]
    return files, n

def gh_blob(r, path):
    return f"https://github.com/{r['repo']}/blob/{repo_branch(r['repo'])}/{quote(path, safe='/')}"

def link_name(u):
    from urllib.parse import unquote
    return unquote(u.rstrip("/").split("/")[-1])

# ---- BOM files (d, 2026-09-26 16:07): link the actual BOM files instead of "machine-readable BOM in repo".
# Same filename rule as data/cards.py (which set bom=y), over the repo file listings in data/trees/.
BOMF = re.compile(r"(bom|parts?[ _-]?list|bill[ _-]?of[ _-]?materials?|stückliste)[^/]*\.(csv|tsv|txt|md|xlsx?|ods|pdf|html?)$|ibom[^/]*\.html?$", re.I)
OLD_DIR = re.compile(r"(^|/)(old|obsolete|zzz[^/]*obsolete[^/]*|archive|archived|deprecated|[^/]*backup[^/]*)(/|$)", re.I)
BOM_ORDER = ["iBOM", "CSV", "TSV", "XLSX", "XLS", "ODS", "PDF", "MD", "TXT"]
_trees, _branch = {}, {}

def repo_tree(repo):
    if repo not in _trees:
        f = os.path.join(ROOT, "data", "trees", repo.replace("/", "_") + ".txt")
        _trees[repo] = open(f, encoding="utf-8").read().splitlines() if os.path.exists(f) else []
    return _trees[repo]

def repo_branch(repo):
    if not _branch:
        for l in open(os.path.join(ROOT, "data", "inventory.tsv"), encoding="utf-8"):
            f = l.rstrip("\r\n").split("\t")
            if len(f) >= 7 and f[1] != "repo":
                _branch[f[1]] = f[6] or "main"
    return _branch.get(repo, "main")

def _norm(x):
    return re.sub(r"[^a-z0-9]", "", x.lower())

def _bom_stem(path):
    b = os.path.splitext(os.path.basename(path))[0]
    return _norm(re.sub(r"(?i)interactive|i?bom|parts[ _-]?list|stückliste|full assembly", "", b))

def _module_keys(r):
    ks = {_norm(r["module_name"])}
    m = re.search(r"files=\d+: ([^)]*)\)", r["comp_basis"])
    if m:
        ks |= {_norm(os.path.splitext(x.strip())[0]) for x in m.group(1).split(",")}
    from urllib.parse import unquote
    ks.add(_norm(os.path.splitext(unquote(r["link"].rstrip("/").split("/")[-1].split("#")[-1]))[0]))
    ks |= {re.sub(r"v\d+$", "", k) for k in list(ks)}
    return {k for k in ks if len(k) >= 3}

def bom_files(r, shared):
    """BOM files for a bom=y row. A BOM path named in comp_basis wins; a folder with only this module gives all
    its BOMs; a folder shared with other modules gives only BOMs whose name matches this module or its board
    file (none rather than a wrong one). BOMs under old/obsolete/archive dirs are dropped when others exist."""
    if r["bom"] != "y":
        return []
    d = r["module_dir"]
    c = [p for p in repo_tree(r["repo"]) if (d == "." or p.startswith(d + "/")) and BOMF.search(os.path.basename(p))]
    cur = [p for p in c if not OLD_DIR.search(p)]
    c = cur or c
    named = [p for p in c if p in r["comp_basis"] or os.path.basename(p) in r["comp_basis"]]
    if named:
        return named
    if not shared:
        return c
    ks = _module_keys(r)
    return [p for p in c if (st := _bom_stem(p)) and any(k == st or (len(k) >= 5 and len(st) >= 4 and (k in st or st in k)) for k in ks)]

def bom_label(path):
    b = os.path.basename(path).lower()
    if "ibom" in b or b.endswith((".html", ".htm")):
        return "iBOM"
    return os.path.splitext(b)[1].lstrip(".").upper()

def bom_url(r, path, page=True):
    """page=False: always the GitHub file page (for an iBOM that shows its source code)."""
    enc = quote(path, safe="/")
    blob = f"https://github.com/{r['repo']}/blob/{repo_branch(r['repo'])}/{enc}"
    if page and bom_label(path) == "iBOM":
        # GitHub shows HTML as source. htmlpreview renders it in the browser so the iBOM runs; githack was
        # dropped because it shows an "External Content Notice" interstitial on first visit (d 16:27).
        return "https://htmlpreview.github.io/?" + blob
    return blob

def bom_cell(r, shared):
    files = bom_files(r, shared)
    if not files:
        return "machine-readable BOM in repo" if r["bom"] == "y" else nd("none found" if r["bom"] == "-" else "")
    files = sorted(files, key=lambda p: (BOM_ORDER.index(bom_label(p)) if bom_label(p) in BOM_ORDER else 99, p.lower()))
    d = r["module_dir"]
    rel = lambda p: p[len(d) + 1:] if d != "." and p.startswith(d + "/") else p
    # iBOM: the label opens the interactive page (htmlpreview); "source" beside it is the GitHub file page, a fallback (d 16:21)
    src = lambda p: f' <a class="small" href="{e(bom_url(r, p, page=False))}" title="GitHub file page (HTML source)">source</a>' if bom_label(p) == "iBOM" else ""
    lines = [f'<a href="{e(bom_url(r, p))}" title="{e(p)}">{e(bom_label(p))}</a>{src(p)} <span class="mute small">{e(rel(p))}</span>' for p in files[:10]]
    if len(files) > 10:
        lines.append(f'<span class="mute small">+{len(files) - 10} more in the <a href="{e(r["link"])}">source folder</a></span>')
    return "<br>".join(lines)

IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")

def schem_raw(u):
    """github.com/<o>/<r>/blob/<ref>/<path> -> raw.githubusercontent.com/<o>/<r>/<ref>/<path>, the file itself
    (served with CORS *, so PDF.js can fetch it; images load in <img>). None if not a GitHub blob URL
    or not a PDF/image."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/(.+)$", u or "")
    if not m:
        return None, None
    kind = "pdf" if m.group(3).lower().endswith(".pdf") else "img" if m.group(3).lower().endswith(IMG_EXT) else None
    return (f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}", kind) if kind else (None, None)

def schem_box(r):
    raw, kind = schem_raw(r["schematic"])
    if not raw:
        return ""
    u = r["schematic"]
    head = f'<div class="box schem" id="schematic"><h2>Schematic</h2><p class="url small"><a href="{e(u)}">{e(u)}</a></p>'
    if kind == "img":
        return head + f'<div class="view"><a href="{e(u)}"><img src="{e(raw)}" loading="lazy" alt="Schematic: {e(schem_name(u))}"></a></div></div>'
    return head + (f'<div class="view pdfview" data-src="{e(raw)}" data-href="{e(u)}"><p class="pdfstatus">Loading PDF…</p>'
                   f'<noscript><p class="pdfstatus">Showing the PDF here needs JavaScript; use the link above.</p></noscript></div></div>'
                   f'<script type="module" src="../../schem.js?v={_h(SCHEM_JS)}"></script>')

def link_or_text(s):
    if is_url(s):
        return f'<a href="{e(s)}">{e(short_url(s))}</a>'
    return nd(s)

def chips(r):
    out = []
    c = r["components"]
    out.append(f'<span class="chip{"" if c else " dim"}">{e(c) if c else "mounting n/d"}</span>')
    for f in files_of(r):
        out.append(f'<span class="chip">{e(f)}</span>')
    if r["prototype"] == "X":
        out.append('<span class="chip warn">prototype</span>')
    elif r["prototype"] == "?":
        out.append('<span class="chip warn">prototype?</span>')
    return "".join(out)

# ---------------------------------------------------------------- index

SCHEM_JS = r"""
// Module pages: show a PDF schematic inline (d, 2026-09-26 15:59).
// GitHub serves raw PDFs as octet-stream with X-Frame-Options: deny, so they can't be iframed directly. The raw
// host allows CORS, so we fetch the bytes and:
//  - desktop browsers with a built-in PDF viewer: wrap them as an application/pdf File, iframe its blob: URL
//    (native zoom / search / pages). The blob URL is made fresh on every page view and dies with the page.
//  - touch devices, or no built-in viewer: draw each page to a canvas with PDF.js, lazily.
const PDFJS = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/";
const box = document.querySelector(".pdfview");
if (box) {
  const st = box.querySelector(".pdfstatus");
  const fail = () => { st.innerHTML = 'Couldn’t show this PDF here. <a href="' + box.dataset.href + '">Open it on GitHub</a>.'; };
  const near = (el, fn) => { const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { io.disconnect(); fn(); } }, { rootMargin: "800px" }); io.observe(el); };
  const native = navigator.pdfViewerEnabled === true && !matchMedia("(pointer: coarse)").matches;
  near(box, async () => {
    try {
      const res = await fetch(box.dataset.src);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const buf = await res.arrayBuffer();
      if (native) {
        const name = decodeURIComponent(box.dataset.src.split("/").pop());
        const url = URL.createObjectURL(new File([buf], name, { type: "application/pdf" }));
        const f = document.createElement("iframe");
        f.className = "pdfframe"; f.title = "Schematic: " + name; f.src = url;
        st.remove(); box.appendChild(f);
        return;
      }
      await canvases(buf);
    } catch (err) { console.error(err); fail(); }
  });
  async function canvases(buf) {
    const lib = await import(PDFJS + "pdf.min.mjs");
    lib.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.mjs";
    const doc = await lib.getDocument({ data: new Uint8Array(buf) }).promise;
    const first = (await doc.getPage(1)).getViewport({ scale: 1 });
    st.textContent = doc.numPages > 1 ? doc.numPages + " pages" : "";
    if (!st.textContent) st.remove();
    for (let i = 1; i <= doc.numPages; i++) {
      const wrap = document.createElement("div"); wrap.className = "pdfpage";
      wrap.style.aspectRatio = first.width + " / " + first.height;
      box.appendChild(wrap);
      near(wrap, async () => {
        try {
          const page = await doc.getPage(i), v1 = page.getViewport({ scale: 1 });
          wrap.style.aspectRatio = v1.width + " / " + v1.height;
          // sharp enough to read part values: 2x the shown width, capped at ~16 Mpx (iOS canvas limit)
          let scale = wrap.clientWidth * Math.max(2, window.devicePixelRatio || 1) / v1.width;
          scale = Math.min(scale, Math.sqrt(16e6 / (v1.width * v1.height)));
          const vp = page.getViewport({ scale }), c = document.createElement("canvas");
          c.width = Math.floor(vp.width); c.height = Math.floor(vp.height);
          c.setAttribute("aria-label", "Schematic page " + i);
          wrap.appendChild(c);
          await page.render({ canvasContext: c.getContext("2d"), viewport: vp }).promise;
        } catch (err) { console.error(err); wrap.remove(); }
      });
    }
  }
}
"""

JS = r"""
(function(){
const rows=window.__ROWS__;
const $=s=>document.querySelector(s), $$=(s,el=document)=>[...el.querySelectorAll(s)];
const FACETS=["tags","lic","terms","mount","files","license","proto","maker"];
const state={q:"",tags:new Set(),lic:new Set(),terms:new Set(),mount:new Set(),files:new Set(),license:new Set(),proto:new Set(),maker:new Set(),mode:{},fsort:{},pmode:"hide",panelOnly:false,view:"table",sort:"name",dir:"asc"};
// --- read URL
const sp=new URLSearchParams(location.search);
for(const k of FACETS){for(const v of sp.getAll(k))state[k].add(v);if(sp.get(k+"_mode")==="all")state.mode[k]="all";const fs=sp.get(k+"_sort");if(fs==="name"||fs==="count")state.fsort[k]=fs;}
if(sp.get("proto_mode")==="show")state.pmode="show";if(sp.get("panel")==="1")state.panelOnly=true;if(sp.get("q"))state.q=sp.get("q");if(sp.get("view"))state.view=sp.get("view");if(sp.get("sort"))state.sort=sp.get("sort");if(sp.get("dir"))state.dir=sp.get("dir");
function writeURL(){const p=new URLSearchParams();if(state.q)p.set("q",state.q);for(const k of FACETS){for(const v of state[k])p.append(k,v);if(state.mode[k]==="all")p.set(k+"_mode","all");if(state.fsort[k])p.set(k+"_sort",state.fsort[k]);}
 if(state.pmode==="show")p.set("proto_mode","show");if(state.panelOnly)p.set("panel","1");if(state.view!=="table")p.set("view",state.view);if(state.sort!=="name")p.set("sort",state.sort);if(state.dir!=="asc")p.set("dir",state.dir);
 history.replaceState(null,"",location.pathname+(p.toString()?"?"+p:""));}
// --- facets
const facetDefault={maker:"name"};
function facetHTML(name,key,counts){const by=state.fsort[name]||facetDefault[name]||"count";
 const vals=[...counts.keys()].sort((a,b)=>by==="name"?a.localeCompare(b):counts.get(b)-counts.get(a)||a.localeCompare(b));
 return vals.map(v=>`<label><input type="checkbox" value="${esc(v)}" ${state[key].has(v)?"checked":""}><span>${esc(v)}</span><span class="n">${counts.get(v)}</span></label>`).join("");}
function facet(name,key,getter){const box=$("#f-"+name);const counts=new Map();
 for(const r of rows){for(const v of getter(r))counts.set(v,(counts.get(v)||0)+1);}
 box.innerHTML=facetHTML(name,key,counts);
 box.addEventListener("change",ev=>{const v=ev.target.value;ev.target.checked?state[key].add(v):state[key].delete(v);render();});
 const fs=$(`.fsort[data-f=${name}]`);if(fs){$$("input",fs).forEach(i=>i.checked=(state.fsort[name]||facetDefault[name]||"count")===i.value);
  fs.addEventListener("change",ev=>{state.fsort[name]=ev.target.value;box.innerHTML=facetHTML(name,key,counts);
   const q=$("#maker-q");if(name==="maker"&&q&&q.value){q.dispatchEvent(new Event("input"));}writeURL();});}}
function makerLinks(r){return r.mk.map(([s,m])=>`<a class="mk" href="?maker=${encodeURIComponent(m)}">${esc(s)}</a>`).join(" + ");}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
const G={tags:r=>r.tags,lic:r=>r.lic||[],terms:r=>r.terms||[],mount:r=>[r.mount],files:r=>r.files,license:r=>[r.license||"not determined"],proto:r=>r.proto==="X"?["prototype"]:r.proto==="?"?["prototype?"]:[],maker:r=>r.makers};
if($("#f-tags"))facet("tags","tags",G.tags);if($("#f-lic"))facet("lic","lic",G.lic);if($("#f-terms"))facet("terms","terms",G.terms);facet("mount","mount",G.mount);facet("files","files",G.files);if($("#f-license"))facet("license","license",G.license);facet("proto","proto",G.proto);facet("maker","maker",G.maker);
$("#maker-q").addEventListener("input",ev=>{const q=ev.target.value.toLowerCase();$$("#f-maker label").forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?"":"none");});
// --- filter
function match(r,ignoreProto){
 if(state.q){const q=state.q.toLowerCase();if(!(r.name+" "+r.creator+" "+r.type+" "+r.notes+" "+r.license).toLowerCase().includes(q))return false;}
 if(state.panelOnly&&!r.pnl)return false;
 if(!ignoreProto&&!state.proto.size&&state.pmode==="hide"&&r.proto)return false;
 for(const k of FACETS){if(state[k].size){const vs=G[k](r);const ok=state.mode[k]==="all"?[...state[k]].every(v=>vs.includes(v)):vs.some(v=>state[k].has(v));if(!ok)return false;}}
 return true;}
function sorted(list){const k=state.sort,d=state.dir==="asc"?1:-1;
 const key=r=>k==="name"?r.name.toLowerCase():k==="maker"?r.creator.toLowerCase():k==="date"?r.date:k==="type"?r.type.toLowerCase():k==="mount"?r.mount:k==="parts"?(r.parts==null?(d>0?1e9:-1):r.parts):k==="hp"?(r.hp==null?(d>0?1e9:-1):r.hp):r.name.toLowerCase();
 return list.sort((a,b)=>{const x=key(a),y=key(b);return x<y?-d:x>y?d:a.name.localeCompare(b.name);});}
// --- render
function chip(r){let s=r.tags.filter(t=>t!=="not mapped").map(t=>`<span class="chip tag">${esc(t)}</span>`).join("");s+=r.licchips||"";s+=`<span class="chip${r.components?"":" dim"}">${r.components?esc(r.components):"mounting n/d"}</span>`;
 for(const f of r.files)s+=`<span class="chip">${esc(f)}</span>`;
 if(r.proto==="X")s+='<span class="chip warn">prototype</span>';else if(r.proto==="?")s+='<span class="chip warn">prototype?</span>';return s;}
function card(r){const meta=[r.hpt&&r.hpt!=="?"?r.hpt:"",r.parts==null?"":r.parts+" parts"].filter(Boolean).join(" · ");return `<div class="card">${meta?`<div class="parts">${esc(meta)}</div>`:""}<div class="name"><a href="m/${r.slug}/">${esc(r.name)}</a></div><div class="maker">${makerLinks(r)}</div><div class="type">${r.type?esc(r.type):'<span class="nd">type not determined</span>'}</div><div class="chips">${chip(r)}</div></div>`;}
function table(list){const h=[["name","Module"],["maker","Maker"],["type","Type"],["mount","Mounting"],["hp","HP"],["parts","Parts"],["files","Files"],["license","License"],["date","Date"]];
 return `<table class="list"><thead><tr>${h.map(([k,l])=>`<th data-k="${k}" ${state.sort===k?`data-dir="${state.dir}"`:""}>${l}</th>`).join("")}</tr></thead><tbody>${list.map(r=>`<tr><td><a href="m/${r.slug}/">${esc(r.name)}</a>${r.proto?` <span class="chip warn">${r.proto==="X"?"prototype":"prototype?"}</span>`:""}</td><td>${makerLinks(r)}</td><td>${esc(r.type)}</td><td>${r.components?esc(r.components):'<span class="nd">n/d</span>'}</td><td class="num">${r.hpt&&r.hpt!=="?"?esc(r.hpt):r.hpt==="?"?'<span class="nd" title="panel files present, HP not determined">?</span>':'<span class="nd">—</span>'}</td><td class="num">${r.parts==null?'<span class="nd">—</span>':r.parts+(r.pooled?'<span class="mute" title="summed over several board files in the folder — variants may be pooled">*</span>':'')}</td><td>${r.files.join(", ")}</td><td>${r.licchips||(r.license?esc(r.license):'<span class="nd">n/d</span>')}</td><td class="mute">${esc(r.date)}</td></tr>`).join("")}</tbody></table>`;}
function render(){const list=sorted(rows.filter(r=>match(r)));const hid=(!state.proto.size&&state.pmode==="hide")?rows.filter(r=>r.proto&&match(r,true)).length:0;
 $("#count").textContent=`${list.length} of ${rows.length} modules`+(hid?` · ${hid} prototypes hidden`:"");
 const pm=$(".pmode");if(pm)pm.classList.toggle("off",state.proto.size>0);
 const out=$("#out");out.innerHTML=state.view==="grid"?`<div class="grid">${list.map(card).join("")}</div>`:table(list);
 if(state.view==="table")$$("#out th").forEach(th=>th.addEventListener("click",()=>{const k=th.dataset.k;if(k==="files")return;if(state.sort===k)state.dir=state.dir==="asc"?"desc":"asc";else{state.sort=k;state.dir="asc";}$("#sort").value=state.sort;render();}));
 $$(".toolbar [data-view]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.view===state.view));writeURL();}
$("#q").value=state.q;$("#q").addEventListener("input",ev=>{state.q=ev.target.value.trim();render();});
$("#sort").value=state.sort;$("#sort").addEventListener("change",ev=>{state.sort=ev.target.value;state.dir=ev.target.value==="date"?"desc":"asc";render();});
$$(".toolbar [data-view]").forEach(b=>b.addEventListener("click",()=>{state.view=b.dataset.view;render();}));
$$(".mode").forEach(m=>{const k=m.dataset.f;const sync=()=>$$("input",m).forEach(i=>i.checked=(state.mode[k]||"any")===i.value);sync();
 m.addEventListener("change",ev=>{state.mode[k]=ev.target.value;render();});});
const po=$("#panel-only");if(po){po.checked=state.panelOnly;po.addEventListener("change",ev=>{state.panelOnly=ev.target.checked;render();});}
const pm=$(".pmode");if(pm){$$("input",pm).forEach(i=>i.checked=state.pmode===i.value);pm.addEventListener("change",ev=>{state.pmode=ev.target.value;render();});}
$("#clear").addEventListener("click",()=>{state.q="";state.mode={};state.pmode="hide";state.panelOnly=false;$$(".pmode input").forEach(i=>i.checked=i.value==="hide");$$(".mode input").forEach(i=>i.checked=i.value==="any");for(const k of FACETS)state[k].clear();$("#q").value="";$$("aside input[type=checkbox]").forEach(c=>c.checked=false);render();});
if(matchMedia("(max-width:640px)").matches)$$("aside details").forEach(d=>d.open=false);
if(matchMedia("(max-width:640px)").matches)$$("aside details").forEach(d=>d.open=false);
render();
})();
"""

def build_index(rows, typemap, licmap):
    data = [dict(tags=tags_of(r, typemap), makers=makers_of(r), mk=credit_parts(r), parts=(counts_of(r) or {}).get("total"), pooled=(counts_of(r) or {}).get("files", 1) > 1,
        lic=[family_label(g) for g in grants_of(r, licmap)], terms=[TERMS_LABEL.get(g["terms"], g["terms"]) for g in grants_of(r, licmap)],
        licchips="".join(grant_chip(g) for g in grants_of(r, licmap)) if licmap else "",
        id=r["id"], slug=r["slug"], name=r["module_name"], creator=r["creator"], type=r["type"],
        license=r["license"], components=r["components"], mount=bucket_components(r["components"]),
        files=files_of(r), proto=r["prototype"], date=r["date"], notes=r["notes"],
        hp=hp_of(r)[0], hpt=hp_of(r)[1], pnl=bool((r.get("panel") or "").strip()),
    ) for r in rows]
    n_pnl = sum(1 for d in data if d["pnl"])
    MULTI = {"tags", "lic", "terms", "files", "maker"}   # a module can carry several values -> any/all makes sense
    SORTABLE = {"maker", "tags"}                                   # facets with a name/count sort switch
    def facet(name, label, extra=""):
        sw = ""
        if name in MULTI:
            sw += (f'<span class="mute">match</span> <span class="seg mode" data-f="{name}" title="Checked values: match any of them, or all of them">'
                   f'<label><input type="radio" name="mode-{name}" value="any" checked><span>any</span></label>'
                   f'<label><input type="radio" name="mode-{name}" value="all"><span>all</span></label></span>')
        if name in SORTABLE:
            sw += (f' <span class="mute">sort</span> <span class="seg fsort" data-f="{name}" title="Order the list by name or by number of modules">'
                   f'<label><input type="radio" name="sort-{name}" value="name"{" checked" if name == "maker" else ""}><span>a–z</span></label>'
                   f'<label><input type="radio" name="sort-{name}" value="count"{"" if name == "maker" else " checked"}><span>count</span></label></span>')
        if name == "proto":
            sw = (f'<span class="mute">prototypes</span> <span class="seg pmode" title="Hide prototype-marked modules, or show them alongside the rest. Ignored while a mark is checked.">'
                  f'<label><input type="radio" name="pmode" value="hide" checked><span>hide</span></label>'
                  f'<label><input type="radio" name="pmode" value="show"><span>show</span></label></span>')
        if sw:
            sw = f'<div class="moderow">{sw}</div>'
        return f'<details open><summary><span>{label}</span></summary>{sw}{extra}<div id="f-{name}" class="{"maker-list" if name=="maker" else ""}"></div></details>'
    aside = (
        '<input id="q" type="search" placeholder="Search name, maker, type, notes…" aria-label="Search">'
        + f'<label class="solo" title="Modules that ship panel files: kicad, eagle, easyeda, gerbers, svg, dxf, ai, pdf, Front Panel Designer or 3D"><input type="checkbox" id="panel-only"><span>only modules with panel source files</span><span class="n">{n_pnl}</span></label>'
        + (facet("tags", "Type <span class=\"mute\" style=\"font-weight:400\">(draft tags)</span>") if typemap else "")
        + facet("mount", "Mounting")
        + facet("files", "Files in repo")
        + (facet("terms", "License terms <span class=\"mute\" style=\"font-weight:400\">(draft)</span>") if licmap else facet("license", "License (as recorded)"))
        # the per-family "License" facet is hidden (d, 2026-09-26 14:17); ?lic=<family> in the URL still filters
        + facet("maker", "Maker", '<input id="maker-q" type="search" placeholder="filter makers" aria-label="Filter makers">')
        + facet("proto", "Build status")
    )
    body = f"""<div class="layout"><aside>{aside}</aside><main>
<div class="toolbar"><span id="count"></span>
<label>sort <select id="sort"><option value="name">name</option><option value="maker">maker</option><option value="type">type</option><option value="mount">mounting</option><option value="hp">HP (narrowest)</option><option value="date">date (newest)</option><option value="parts">parts (fewest)</option></select></label>
<span><button data-view="table" aria-pressed="true">table</button> <button data-view="grid">grid</button></span>
<button id="clear" class="clear">clear filters</button></div>
<div id="out"></div></main></div>
<script>window.__ROWS__={json.dumps(data, ensure_ascii=False, separators=(",", ":"))};</script>
<script src="site.js?v={_h(JS)}"></script>"""
    return page(SITE_TITLE, body, "", f"{len(rows)} buildable open-source Eurorack modules, filterable by mounting, files, license and maker.", stamp=True)

# ---------------------------------------------------------------- detail

BASIS = [("comp_basis", "Components (mounting)"), ("type_basis", "Type"),
         ("creator_basis", "Creator"), ("license_basis", "License"), ("prototype_basis", "Prototype mark"),
         ("panel_basis", "Panel / HP"), ("photos_basis", "Photos"), ("build_basis", "Build guide")]

def hp_cell(r):
    _, t = hp_of(r)
    why = (r.get("panel_basis") or "").split(" | ")[0].strip()
    if t and t != "?":
        how = re.sub(r"^measured ([\d.]+) x ([\d.]+) mm outline in (.*?)(;.*)?$", r"measured from the panel outline (\1 × \2 mm, \3)\4", why)
        return f'<b>{e(t)}</b>' + (f' <span class="mute small">· {e(how)}</span>' if how else "")
    if t == "?":
        return nd("not determined") + (f' <span class="mute small">· {e(why)}</span>' if why else "")
    return nd("no panel files found")

def panel_cell(r):
    src = panel_sources(r)
    if not src:
        return nd("none found")
    files, n = panel_files(r)
    out = e(" · ".join(src))
    if files:
        # design files first; individual gerber layers collapse into one link per folder
        LAYER = re.compile(r"\.(gbr|gtl|gbl|gts|gbs|gto|gbo|gtp|gbp|gko|gm\d*|gml|drl|xln|txt)$", re.I)
        items, folders = [], {}
        for f in files:
            if LAYER.search(f):
                folders.setdefault(os.path.dirname(f), []).append(f)
            else:
                items.append(f'<a href="{e(gh_blob(r, f))}" class="small">{e(f)}</a>')
        for d, fs in folders.items():
            if len(fs) == 1:
                items.append(f'<a href="{e(gh_blob(r, fs[0]))}" class="small">{e(fs[0])}</a>')
            else:
                u = f"https://github.com/{r['repo']}/tree/{repo_branch(r['repo'])}/{quote(d, safe='/')}" if d else r["link"]
                items.append(f'<a href="{e(u)}" class="small">{e(d or "(repo root)")}/</a> <span class="mute small">{len(fs)} gerber layers</span>')
        out += "<br>" + "<br>".join(items[:8])
        shown = len(files) if len(items) <= 8 else None
        if len(items) > 8 or n > len(files):
            more = (len(items) - 8 if len(items) > 8 else 0) + (n - len(files))
            out += f'<br><span class="mute small">+{more} more in the <a href="{e(r["link"])}">source folder</a></span>'
    return out

def link_box(title, urls, fmt, fold=12):
    if not urls:
        return ""
    items = [f"<li>{fmt(u)}</li>" for u in urls]
    body = f'<ul class="links">{"".join(items[:fold])}</ul>'
    if len(items) > fold:
        body += f'<details><summary class="small">all {len(items)}</summary><ul class="links">{"".join(items[fold:])}</ul></details>'
    return f'<div class="box"><h2>{title} <span class="mute" style="text-transform:none;letter-spacing:0">({len(urls)})</span></h2>{body}</div>'

def build_link(u):
    if "/tree/" in u:
        return f'<a href="{e(u)}">{e(link_name(u))}/</a> <span class="mute small">folder of build-step photos</span>'
    return f'<a href="{e(u)}">{e(link_name(u))}</a>'

def photo_link(u):
    return f'<a href="{e(u)}">{e(link_name(u))}</a>'


def mini(r):
    return f'<div class="card"><div class="name"><a href="../{r["slug"]}/">{e(r["module_name"])}</a></div><div class="maker">{e(r["creator"])}</div><div class="type small">{nd(r["type"], "type not determined")}</div><div class="chips">{chips(r)}</div></div>'

def build_detail(r, by_maker, typemap, licmap):
    tags = [t for t in tags_of(r, typemap) if t != "not mapped"]
    grants = grants_of(r, licmap) if licmap else []
    title = f"{r['module_name']} — {r['creator']}"
    spec = [
        ("Maker", e(r["creator"])),
        ("Type", nd(r["type"]) + (f' <span class="mute small">· tags (draft): {e(", ".join(tags))}</span>' if tags else "")),
        ("Mounting", nd(r["components"])),
        ("HP", hp_cell(r)),
        ("Panel files", panel_cell(r)),
        ("Component confidence", (e(r["comp_conf"]) if r["comp_conf"] else nd(""))),
        ("Board parts", (lambda c: (f'<b>{c["total"]}</b> footprints — SMD {c["smd"]} (+{c["smd_ic"]} ICs), THT {c["tht"]} (+{c["tht_ic"]} ICs, +{c["tht_to"]} TO-92/220)'
                                      ' <span class="mute small">· panel hardware not counted' + (f' · summed over {c["files"]} board files in the folder, so variants may be pooled' if c["files"] > 1 else "") + '</span>') if c else nd("not counted (no board file or machine-readable BOM in scope)"))(counts_of(r))),
        ("Layout files", nd(r["layout"])),
        ("Schematic", link_or_text(r["schematic"]) if r["schematic"] != "x" else "present in repo"),
        ("BOM", bom_cell(r, SHARED[(r["repo"], r["module_dir"])] > 1)),
        ("License (as recorded)", nd(r["license"], "blank — no LICENSE file or README statement found in the files checked")),
        ("Build status", {"X": '<span class="chip warn">prototype</span> — repo labels it a prototype / untested',
                          "?": '<span class="chip warn">prototype?</span> — wording is ambiguous'}.get(r["prototype"], "no prototype mark")),
        ("Last commit seen", nd(r["date"])),
    ]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in spec)
    links = [f'<li>Source: <a href="{e(r["link"])}">{e(short_url(r["link"], 90))}</a></li>']
    if is_url(r["schematic"]):
        links.append(f'<li>Schematic: <a href="{e(r["schematic"])}">{e(schem_name(r["schematic"]))}</a></li>')
    links.append(f'<li>Repository: <a href="https://github.com/{e(r["repo"])}">{e(r["repo"])}</a> at <code>{e(r["sha"])}</code>'
                 + (f' (folder <code>{e(r["module_dir"])}</code>)' if r["module_dir"] else "") + "</li>")
    ev = "".join(f"<dt>{lab}</dt><dd>{e(r[k])}</dd>" for k, lab in BASIS if r[k])
    ev_box = f'<div class="box ev"><h2>Evidence — why the cells say what they say</h2><dl>{ev}</dl></div>' if ev else ""
    lic_box = ""
    if grants:
        trs = "".join(f'<tr><td>{e(SCOPE_LABEL.get(g["scope"], g["scope"]))}</td><td>{e(family_label(g))}{(" " + e(version_label(g))) if g["version"] else ""}</td><td>{e(TERMS_LABEL.get(g["terms"], g["terms"]))}</td><td class="mute">{e(g["note"].replace("qualifier: ", "").replace("scope text: ", ""))}{(" <b>source: " + e(g["source"]) + "</b>") if g.get("source") and g["source"] != "repo" else ""}</td></tr>' for g in grants)
        draft = ' <span style="text-transform:none;letter-spacing:0">(draft categorisation)</span>' if any(g["status"] != "ok" for g in grants) else ""
        lic_box = f'<div class="box"><h2>License{draft}</h2><table class="grants"><tr><th>covers</th><th>license</th><th>terms</th><th></th></tr>{trs}</table><p class="small mute" style="margin:8px 0 0">Terms describe the license family, not this repository. Check the repository before relying on any of it.</p></div>'
    notes = f'<div class="box"><h2>Notes</h2>{e(r["notes"])}</div>' if r["notes"] else ""
    follow = f'<div class="box"><h2>Open follow-up</h2>{e(r["followup"])}</div>' if r["followup"] else ""
    more = ""
    for m in makers_of(r):
        others = [o for o in by_maker[m] if o["id"] != r["id"]]
        if not others:
            continue
        more += f'<h2 class="small mute" style="margin-top:28px">More by {e(m)} ({len(others)})</h2><div class="more">{"".join(mini(o) for o in others[:12])}</div>'
        if len(others) > 12:
            more += f'<p class="small"><a href="{e(maker_href(m, "../../"))}">all {len(others)+1} by {e(m)}</a></p>'
    body = f"""<div class="detail"><p class="small"><a href="../../">← all modules</a></p>
<h1>{e(r["module_name"])}</h1><div class="maker">{" + ".join(f'<a href="{e(maker_href(m, "../../"))}">{e(m)}</a>' for m in makers_of(r))}</div>
<div class="cols"><div><dl class="spec">{dl}</dl>{lic_box}{notes}{follow}{ev_box}</div>
<div><div class="box"><h2>Files &amp; links</h2><ul>{"".join(links)}</ul></div>
{link_box("Build guide", (r.get("build") or "").split(), build_link)}{link_box("Photos", (r.get("photos") or "").split(), photo_link)}
<div class="box"><h2>Record</h2>row <code>{e(r["id"])}</code> · detector v{e(r["detector_version"])} · <a href="{REPO_URL}/blob/website/data/modules.tsv">data/modules.tsv</a><br>
<span class="mute small">Blank cells are blank on purpose: the repo didn't state it, so we don't either.</span></div></div></div>
{schem_box(r)}
<div class="notice">This is a third-party design. Check the repository (and its license) before ordering parts or selling boards.</div>
{more}</div>"""
    desc = f"{r['module_name']} by {r['creator']}" + (f" — {r['type']}" if r["type"] else "") + (f", {r['components']}" if r["components"] else "")
    return page(title, body, "../../", desc)

# ---------------------------------------------------------------- about

def build_about(rows):
    n_repo = len({r["repo"] for r in rows}); n_mk = len({m for r in rows for m in makers_of(r)})
    body = f"""<div class="detail" style="max-width:760px"><h1>About</h1>
<p>{len(rows)} buildable open-source Eurorack modules from {n_repo} GitHub repositories by {n_mk} makers.
The table behind this site is <a href="{REPO_URL}/blob/website/data/modules.tsv">data/modules.tsv</a> in
<a href="{REPO_URL}">daaaaaaaaaniel/my-awesome-eurorack</a>; the site is regenerated from it and adds nothing.</p>
<h2>What the fields mean</h2>
<dl class="spec">
<dt>Type</dt><dd>The raw type string from the repo, plus <b>tags</b> from <a href="{REPO_URL}/blob/website/data/type-categories.tsv">data/type-categories.tsv</a> (multi-function modules get several). Tags marked <i>draft</i> are keyword-rule proposals awaiting review.</dd>
<dt>Maker</dt><dd>As recorded in the repo. A clone or port is credited "Original + Porter" (e.g. "Mutable Instruments + Sluisbrinkie"); the Maker filter lists each name separately, so the module appears under both. Spelling variants of one maker are folded together by <a href="{REPO_URL}/blob/website/data/maker-aliases.tsv">data/maker-aliases.tsv</a>; the credit line keeps the repo's spelling.</dd>
<dt>Mounting</dt><dd><b>SMD</b>, <b>THT</b> or <b>both</b>, read from the board files' footprints or from a statement in the repo. Blank means neither was available in scope — it is <i>not</i> a guess. "Component confidence" says which: <b>Strong</b> (footprints counted), <b>Stated</b> (repo says so in text), <b>Weak</b>, <b>Deferred</b> (no machine-readable board file or BOM found).</dd>
<dt>Board parts</dt><dd>Footprint counts from the board file or a machine-readable BOM, shown only for rows whose component confidence is <b>Strong</b> (548 of 993; another 114 rows have a tally but from weaker evidence and are not shown). Pots, jacks, switches, LEDs, headers and mounting holes are excluded by the detector, so this is a board-complexity number, not a shopping list. A <b>*</b> after the number means the folder held several board files and the detector summed them, so alternate versions may be pooled (the module page says how many). Pin counts are not recorded.</dd>
<dt>HP</dt><dd>Panel width. <b>Measured</b> from the panel outline when it is 3U (127.5–129.5 mm) or 1U high and the width is a whole number of HP (5.08 mm each, minus up to 1 mm); otherwise <b>stated</b> in a panel file name or the README. <b>?</b> = panel files exist but no width could be settled (no measurable outline, or measured and stated disagree). The module page says which.</dd>
<dt>Panel files</dt><dd>The panel's source files: KiCad, Eagle, EasyEDA, gerbers, SVG, DXF, Illustrator, PDF, Front Panel Designer or 3D (STL/STEP/…). Photos of a panel don't count. "Only modules with panel source files" keeps the modules that have any.</dd>
<dt>Photos, Build guide</dt><dd>Links to photos and renders in the module's folder, and to build/assembly documents or a folder of build-step photos. Schematics, diagrams and screenshots are left out.</dd>
<dt>Files in repo</dt><dd>Which design files exist: a schematic (linked when it's a single PDF), KiCad / Eagle / other layout sources, gerbers, a machine-readable BOM.</dd>
<dt>License</dt><dd>The raw statement is kept as recorded. On top of it, <a href="{REPO_URL}/blob/website/data/license-map.tsv">data/license-map.tsv</a> splits each statement into <b>grants</b> — a module can carry one license for hardware and another for firmware — each with a version-free family (filterable by <code>?lic=</code> in the URL) and a <b>terms</b> class that describes the license family, never the module (the <b>License terms</b> filter). Versions are shown only when the repo states one. A blank cell means <b>no license found</b> in the files checked, which is not the same as the repo saying there is none. Rules in <a href="{REPO_URL}/blob/website/data/licenses.md">data/licenses.md</a>.</dd>
<dt>Build status</dt><dd><b>prototype</b> when the repo clearly labels the build untested or in progress; <b>prototype?</b> when the wording is ambiguous. Never inferred from a version number.</dd>
<dt>Evidence</dt><dd>Each module page quotes the file path or README line every non-blank cell came from.</dd>
</dl>
<h2>Rules the data follows</h2>
<ul><li>Never invent a value. A blank cell is correct; a plausible guess would be acted on when ordering parts.</li>
<li>Every non-blank cell traces to a file path in the repository tree or a quoted line of text.</li>
<li>One row per buildable module variant, not per repository.</li></ul>
<p class="small mute">Modelled loosely on <a href="https://signalfunctionset.com/builds/">signalfunctionset.com/builds</a>, whose catalogue is curated by hand; this one is extracted from the repos and shows its working.</p></div>"""
    return page("About — " + SITE_TITLE, body, "", "How the module table is built and what its fields mean.", stamp=True)

# ---------------------------------------------------------------- main

def main():
    rows = load()
    typemap = load_typemap()
    licmap = load_licmap()
    by_maker = defaultdict(list)
    for r in rows:
        for m in makers_of(r):
            by_maker[m].append(r)
    for k in by_maker:
        by_maker[k].sort(key=lambda r: r["module_name"].lower())

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "m"))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    with open(os.path.join(OUT, "site.css"), "w", encoding="utf-8") as f: f.write(CSS.strip() + "\n")
    with open(os.path.join(OUT, "site.js"), "w", encoding="utf-8") as f: f.write(JS.strip() + "\n")
    with open(os.path.join(OUT, "schem.js"), "w", encoding="utf-8") as f: f.write(SCHEM_JS.strip() + "\n")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f: f.write(build_index(rows, typemap, licmap))
    with open(os.path.join(OUT, "about.html"), "w", encoding="utf-8") as f: f.write(build_about(rows))
    for r in rows:
        d = os.path.join(OUT, "m", r["slug"]); os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f: f.write(build_detail(r, by_maker, typemap, licmap))
    print(f"wrote {len(rows)} module pages + index/about to {os.path.relpath(OUT, ROOT)}/")

if __name__ == "__main__":
    main()
