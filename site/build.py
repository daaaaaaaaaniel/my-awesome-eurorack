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
    # d, 2026-09-28 00:37: the displayed count includes panel parts (jacks, pots, switches, LEDs, headers) where the
    # detector recorded them as panel=N (planned v24; not yet run). The THT/SMD/both verdict never uses this number.
    pm = re.search(r"\bpanel=(\d+)", r["comp_basis"])
    board = smd + smdic + thtp + thto + thtic
    panel = int(pm.group(1)) if pm else None
    return dict(smd=smd, smd_ic=smdic, tht=thtp, tht_to=thto, tht_ic=thtic, board=board, panel=panel,
                total=board + (panel or 0), files=int(f.group(1)) if f else 1)

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
aside label .n{margin-left:auto;color:var(--mute);font-variant-numeric:tabular-nums}aside label.zero{opacity:.45}
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
table.list td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}table.list td:nth-child(9){white-space:nowrap}table.list td.im{width:56px;padding:3px 6px 3px 0;vertical-align:middle}
table.list td.im img{display:block;max-width:56px;max-height:64px;border-radius:3px}table.list th[data-k=img]{cursor:default}table.list th[data-k=parts],table.list th[data-k=hp]{text-align:right}
aside label.solo{margin-top:4px;padding-top:6px;border-top:1px dashed var(--line)}.links li{margin:2px 0;word-break:break-word}
table.list th{position:sticky;top:0;background:var(--bg);cursor:pointer;white-space:nowrap}
table.list th[data-dir]::after{content:" ▴"}table.list th[data-dir=desc]::after{content:" ▾"}
.mute{color:var(--mute)}.small{font-size:13px}
.nd{color:var(--mute);font-style:italic}
/* detail page */
.detail h1{font-size:26px;margin:4px 0 2px}.detail .maker{font-size:16px;color:var(--mute);margin-bottom:16px}
.detail .cols{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:28px}
@media(max-width:800px){.detail .cols{grid-template-columns:minmax(0,1fr)}}
dl.spec{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;margin:0 0 20px;font-size:14px}
dl.spec dt{color:var(--mute)}dl.spec dd{margin:0;overflow-wrap:anywhere}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:14px;font-size:14px}
.box h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);margin:0 0 8px}
.box ul{margin:0;padding-left:18px}.box li{margin:3px 0;overflow-wrap:anywhere}
.ev dt{font-weight:600;font-size:13px;margin-top:8px}.ev dd{margin:2px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;color:var(--fg)}
.more{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.thumb{display:block;min-height:60px}.thumb img{display:block;margin:0 auto;width:auto;height:auto;max-width:100%;max-height:360px;object-fit:contain;background:var(--chip);border-radius:4px}
.thumb.broken{display:flex;background:var(--chip);border-radius:4px;align-items:center;justify-content:center;padding:6px;font-size:12px;text-align:center;word-break:break-all}
/* photo gallery (d 04:28 on website-js, ported 06:14) */
.gal{position:relative;touch-action:pan-y}.gnav{position:absolute;top:50%;transform:translateY(-50%);width:34px;height:34px;padding:0;border:0;border-radius:50%;background:rgba(0,0,0,.45);color:#fff;font:22px/1 system-ui,sans-serif;cursor:pointer;display:flex;align-items:center;justify-content:center;opacity:.8}.gnav:hover,.gnav:focus-visible{opacity:1}.gnav:focus-visible{outline:2px solid var(--acc);outline-offset:2px}.gnav.prev{left:4px}.gnav[hidden]{display:none}.gnav.next{right:4px}
.gcap{margin:6px 0 0;display:flex;gap:6px;align-items:baseline;min-width:0}.gcap a{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:inherit}.gcount{white-space:nowrap;font-variant-numeric:tabular-nums}
.strip{position:relative;display:flex;gap:6px;overflow-x:auto;padding:8px 2px 6px;scroll-snap-type:x proximity;scrollbar-width:thin}.strip a{flex:0 0 auto;width:56px;height:56px;border-radius:5px;overflow:hidden;background:var(--chip);scroll-snap-align:center;opacity:.7;outline:2px solid transparent;outline-offset:-2px;transition:opacity .12s}.strip a:hover{opacity:1}.strip a.on{opacity:1;outline-color:var(--acc)}.strip a:focus-visible{opacity:1;outline-color:var(--fg)}.strip img{display:block;width:100%;height:100%;object-fit:cover}.gnote{font-size:11.5px;margin:2px 0 0}
#photos details{margin-top:8px}td.nw{white-space:nowrap}.kcbtn{padding:8px 14px;border:1px solid var(--line);border-radius:6px;background:var(--chip);color:var(--fg);font:inherit;font-size:14px;cursor:pointer;margin:2px 0 8px}.kcbtn:hover{border-color:var(--fg)}.kcview{margin-top:10px}.kcview kicanvas-embed{display:block;width:100%;height:min(78vh,720px);border-radius:6px;overflow:hidden}.kcfiles{margin:4px 0 6px;padding-left:18px}.kcfiles li{margin:2px 0}.kcfile.on{font-weight:600;color:var(--acc)}.kcfile.bad{text-decoration:line-through;color:var(--mute)}.kcerr{color:var(--acc)}.kcgh{text-decoration:none;margin-left:2px}.kcstatus:empty{display:none}.stlbtn{display:block;width:100%;text-align:left;margin:0 0 6px;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--fg);font:inherit;font-size:13px;cursor:pointer;overflow-wrap:anywhere}.stlbtn.on{border-color:currentColor}.stlview{margin-top:6px;border-radius:6px;overflow:hidden;background:linear-gradient(#f3f1ec,#e3e0d8);touch-action:none}.stlview canvas{display:block}.stlstatus:empty{display:none}.stlhint{margin:6px 0 0}
details.evbox>summary{cursor:pointer;list-style:none;display:flex;gap:10px;align-items:baseline;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);font-weight:600}
details.evbox>summary::-webkit-details-marker{display:none}details.evbox>summary::before{content:"▸";text-transform:none}details.evbox[open]>summary::before{content:"▾"}details.evbox[open]>summary::after{content:none}
details.evbox>summary .small{text-transform:none;letter-spacing:0;font-weight:400}details.evbox .fu,details.evbox .ev{margin-top:12px}details.evbox .fu+.ev{border-top:1px solid var(--line);padding-top:10px}.schem .url{word-break:break-all;margin:0 0 8px}.schem .view{background:#fff;border-radius:4px;overflow:hidden}
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

def page(title, body, rel, desc="", stamp=False, head=""):
    """rel = relative path prefix back to docs/ root ('' or '../../').
    stamp: put the build time in the footer. Only the index and about pages get it, so an
    unchanged module page produces an identical file (and no new git object) on rebuild."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="stylesheet" href="{rel}site.css?v={CSS_V}">{head}
</head><body>
<header class="top"><h1><a href="{rel or "./"}">{SITE_TITLE}</a></h1>
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
    # the list ends at the next " | " section (e.g. "| svg by panel outline: ...", added 2026-09-28)
    m = re.search(r"panel files \((\d+)\): (.*?)(?: \| |$)", r.get("panel_basis") or "")
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

# ---- Schematic sources for rows whose schematic is only inside design files (`x`; d, 2026-09-28 05:42: link "whatever
# filetype contains the schematic" instead of "present in repo"). Chosen from the repo file list, like bom_files.
SCH_SRC = re.compile(r"\.(kicad_sch|sch|schdoc|dch|fzz|epro|easyeda)$", re.I)
SCH_SKIP = re.compile(r"(^|/)(_autosave-|~)|-backups/|-(cache|rescue)\.|(^|/)\.|(^|/)(_?archive|old|obsolete|deprecated)(/|$)", re.I)
SCH_ZIP = re.compile(r"kicad|eagle|easyeda|diptrace|source|design|project", re.I)
SCH_NOTZIP = re.compile(r"gerb|gbr|panel|faceplate|jlc|pcbway|fab|cam|drill|stl|step|bom|library|lib", re.I)
def schematic_sources(r, shared):
    """[(path, label)] for an `x` row: the files that hold its schematic, or [] when none can be located."""
    d = r["module_dir"]
    if d.lower().endswith(".zip") and d in repo_tree(r["repo"]):    # the module is a zip (Erica DIY kits, GMSN Pure)
        return [(d, "zip")]
    tree = [p for p in repo_tree(r["repo"]) if d in (".", "") or p.startswith(d + "/")]
    tree = [p for p in tree if not SCH_SKIP.search(p)]
    c = [p for p in tree if SCH_SRC.search(p)]
    # EasyEDA exports: JSON named as a schematic (Schematic_*.json, *sch*.json)
    c += [p for p in tree if p.lower().endswith(".json") and re.search(r"(^|[/_ -])sch(ematic)?", p, re.I)]
    if shared:
        ks = _module_keys(r)
        near = lambda p: (st := _norm(os.path.splitext(os.path.basename(p))[0])) and any(k == st or (len(k) >= 5 and len(st) >= 4 and (k in st or st in k)) for k in ks)
        c = [p for p in c if near(p)]
        exact = [p for p in c if _norm(os.path.splitext(os.path.basename(p))[0]) in ks]
        c = exact or c                     # "minion" should not also take "midi_minion"
    # a KiCad 5 .sch next to a .kicad_sch of the same name is the pre-conversion copy
    c = [p for p in c if not (p.lower().endswith(".sch") and p[:-4] + ".kicad_sch" in c)]
    real = [p for p in c if not re.search(r"panel|faceplate", os.path.basename(p), re.I)]
    c = real or c
    if not c:   # last resort: a zip that says it holds design sources
        c = [p for p in tree if p.lower().endswith(".zip") and SCH_ZIP.search(os.path.basename(p)) and not SCH_NOTZIP.search(os.path.basename(p))]
    names = set(tree)
    def label(p):
        x, stem, folder = p.rsplit(".", 1)[-1].lower(), p.rsplit(".", 1)[0], os.path.dirname(p)
        if x == "kicad_sch": return "KiCad 6+"
        if x == "sch":
            if stem + ".brd" in names: return "Eagle"
            if any(q.startswith(folder + "/" if folder else "") and q.endswith((".pro", ".kicad_pcb", ".kicad_pro", "-cache.lib")) and os.path.dirname(q) == folder for q in names): return "KiCad 5"
            lay = (r.get("layout") or "").lower()
            return "Eagle" if "eagle" in lay and "kicad" not in lay else "KiCad 5" if "kicad" in lay and "eagle" not in lay else ".sch"
        return {"schdoc": "Altium", "dch": "DipTrace", "fzz": "Fritzing", "epro": "EasyEDA Pro", "easyeda": "EasyEDA",
                "json": "EasyEDA", "zip": "zip"}.get(x, x)
    c.sort(key=lambda p: (p.count("/"), p.lower()))
    return [(p, label(p)) for p in c]

def schematic_cell(r, shared):
    if r["schematic"] != "x":
        return link_or_text(r["schematic"])
    src = schematic_sources(r, shared)
    viewer = kicanvas_box(r, shared) and any(p.endswith(".kicad_sch") for p, _ in src)
    if not src:
        return 'inside the design files <span class="mute small">(no single schematic file located)</span>'
    items = [f'<a href="{e(gh_blob(r, p))}">{e(p)}</a> <span class="mute small">{e(lab)}</span>' for p, lab in src[:4]]
    more = f'<br><span class="mute small">+{len(src) - 4} more in the <a href="{e(r["link"])}">source folder</a></span>' if len(src) > 4 else ""
    head = ('inside the design files — <a href="#kicanvas">open in the viewer below</a>' if viewer
            else 'inside the design files (no PDF or image)') + "<br>"
    return head + "<br>".join(items) + more

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

_bomlinks = None
def bom_links(r):
    """data/bom-links.tsv (working branch): BOM tables inside other documents and off-GitHub iBOMs linked from
    the repo - things the filename rule cannot see (d, 2026-09-28 00:49). [(label, url, note)]"""
    global _bomlinks
    if _bomlinks is None:
        _bomlinks = {}
        f = os.path.join(ROOT, "data", "bom-links.tsv")
        if os.path.exists(f):
            for l in open(f, encoding="utf-8"):
                x = l.rstrip("\n").split("\t")
                if len(x) < 4 or l.startswith("#") or x[0] == "id":
                    continue
                label = x[2].upper() if x[2].lower() in ("md", "csv", "tsv", "txt", "pdf", "xls", "xlsx", "ods") else x[2].replace("ibom", "iBOM")
                note = link_name(x[1]) if x[1].startswith("https://github.com/") else x[1].split("//", 1)[-1].split("/", 1)[0]
                if x[2] == "md":
                    note += " (BOM table inside)"
                _bomlinks.setdefault(x[0], []).append((label, x[1], note))
    return _bomlinks.get(r["id"], [])

def bom_cell(r, shared):
    extra = bom_links(r)
    files = bom_files(r, shared)
    if extra and not files:
        return "<br>".join(f'<a href="{e(u)}">{e(lab)}</a> <span class="mute small">{e(n)}</span>' for lab, u, n in extra)
    if not files:
        return "machine-readable BOM in repo" if r["bom"] == "y" else nd("none found" if r["bom"] == "-" else "")
    files = sorted(files, key=lambda p: (BOM_ORDER.index(bom_label(p)) if bom_label(p) in BOM_ORDER else 99, p.lower()))
    d = r["module_dir"]
    rel = lambda p: p[len(d) + 1:] if d != "." and p.startswith(d + "/") else p
    # iBOM: the label opens the interactive page (htmlpreview); "source" beside it is the GitHub file page, a fallback (d 16:21)
    src = lambda p: f' <a class="small" href="{e(bom_url(r, p, page=False))}" title="GitHub file page (HTML source)">source</a>' if bom_label(p) == "iBOM" else ""
    lines = [f'<a href="{e(bom_url(r, p))}" title="{e(p)}">{e(bom_label(p))}</a>{src(p)} <span class="mute small">{e(rel(p))}</span>' for p in files[:10]]
    lines += [f'<a href="{e(u)}">{e(lab)}</a> <span class="mute small">{e(n)}</span>' for lab, u, n in extra]
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

# ---- KiCanvas test (d, 2026-09-28 02:15; branch kicanvas-test only). KiCanvas (MIT, theacodes/kicanvas) renders
# KiCad 6+ schematics and boards in the browser. Built from source with one patch (site/kicanvas/*.patch: boards open
# fitted to their outline). KiCad 4/5 boards are left out: their footprints do not draw and some crash the viewer.
# data/kicad-versions.tsv = the "(version N)" in each .kicad_pcb header, read with a range request.
KC_MIN = 20211014          # KiCad 6.0 file format
_kcver = {}
def kicad_version(repo, path):
    if not _kcver:
        fn = os.path.join(ROOT, "data", "kicad-versions.tsv")
        if os.path.exists(fn):
            for l in open(fn, encoding="utf-8"):
                f = l.rstrip("\r\n").split("\t")
                if len(f) == 3 and f[0] != "repo":
                    _kcver[(f[0], f[1])] = int(f[2]) if f[2].isdigit() else 0
        _kcver.setdefault(("", ""), 0)
    return _kcver.get((repo, path))

def kicad_files(r, shared):
    """(schematics, boards the viewer can draw, boards it cannot) for a row, mirroring bom_files' scoping."""
    d = r["module_dir"]
    t = [p for p in repo_tree(r["repo"]) if (d == "." or p.startswith(d + "/")) and p.endswith((".kicad_pcb", ".kicad_sch"))]
    t = [p for p in t if not OLD_DIR.search(p)] or t
    t = [p for p in t if not re.search(r"(^|/)_autosave-|-backups/", p)]   # KiCad autosave / backup copies
    pcb, sch = [p for p in t if p.endswith(".kicad_pcb")], [p for p in t if p.endswith(".kicad_sch")]
    named = [p for p in pcb if os.path.basename(p) in r["comp_basis"]]
    ks = _module_keys(r)
    near = lambda p: (st := _norm(os.path.splitext(os.path.basename(p))[0])) and any(k == st or (len(k) >= 5 and len(st) >= 4 and (k in st or st in k)) for k in ks)
    if named:
        pcb = named
    elif shared:
        pcb = [p for p in pcb if near(p)]
    if pcb:
        dirs = {os.path.dirname(p) for p in pcb}
        sch = [x for x in sch if os.path.dirname(x) in dirs] or ([] if shared else sch)
    elif shared:
        sch = [x for x in sch if near(x)]
    stems = {p[:-len(".kicad_pcb")] for p in pcb}
    sch.sort(key=lambda x: (x[:-len(".kicad_sch")] not in stems, x.count("/"), x.lower()))   # root sheet first
    pcb.sort(key=lambda p: ("panel" in p.lower(), p.lower()))
    ok = [p for p in pcb if (kicad_version(r["repo"], p) or 0) >= KC_MIN]
    return sch[:16], ok[:3], [p for p in pcb if p not in ok]

def kicanvas_box(r, shared):
    sch, ok, old = kicad_files(r, shared)
    # KiCanvas keys loaded files by basename: a second file with the same name would collide, so keep the first
    seen, files = set(), []
    for p in sch + ok:
        if os.path.basename(p) not in seen:
            seen.add(os.path.basename(p)); files.append(p)
    if not files:
        return ""
    br = repo_branch(r["repo"])
    raw = lambda p: f"https://raw.githubusercontent.com/{r['repo']}/{br}/{quote(p, safe='/')}"
    ns, nb = sum(p.endswith(".kicad_sch") for p in files), sum(p.endswith(".kicad_pcb") for p in files)
    what = " and ".join(x for x in [f"{ns} schematic sheet{'s' if ns != 1 else ''}" if ns else "",
                                     f"{nb} board{'s' if nb != 1 else ''}" if nb else ""] if x)
    items = "".join(f'<li><a class="kcfile small" href="{e(gh_blob(r, p))}" data-raw="{e(raw(p))}">{e(p)}</a> '
                    f'<a class="kcgh small mute" href="{e(gh_blob(r, p))}" title="Open on GitHub">↗</a><span class="kcerr small"></span></li>' for p in files)
    skip = (f'<p class="small mute">Not shown: {", ".join(e(os.path.basename(p)) for p in old[:4])}{" …" if len(old) > 4 else ""}'
            f' — KiCad 5 or older board file; the viewer reads KiCad 6 and newer.</p>') if old else ""
    return (f'<div class="box kc" id="kicanvas"><h2>Schematic &amp; board viewer</h2>'
            f'<button type="button" class="kcbtn">Open {what} in KiCanvas</button>'
            f'<p class="small mute">KiCanvas is an open-source KiCad viewer; opening it loads the viewer (≈480 KB) and the design files from GitHub. '
            f'Click a file below to show it; ↗ opens it on GitHub.</p>'
            f'<ul class="links kcfiles">{items}</ul>{skip}<p class="kcstatus small mute"></p>'
            f'<div class="kcview" hidden></div></div>'
            f'<script type="module" src="../../kc-embed.js?v={_h(KC_JS)}"></script>')

KC_JS = r"""
// KiCanvas test (d, 2026-09-28 02:15; file links drive the viewer, d 03:16).
// The viewer script is imported only when needed. File links switch the main pane through KiCanvas's own
// "context-request" protocol (how its panels reach the project) and the project's public set_active_page(),
// so KiCanvas itself is not patched for this.
function kcProject(embed) {
  let project = null;
  const ev = new Event("context-request", { bubbles: true, composed: true, cancelable: true });
  ev.context_name = "project";
  ev.callback = (ctx) => { ev.stopPropagation(); project = ctx; };
  embed.dispatchEvent(ev);
  return project;
}
// KiCanvas names a fetched file by its URL's last segment, still percent-encoded ("AddaTone%20components.kicad_sch")
const dec = (x) => { try { return decodeURIComponent(x); } catch (e) { return x; } };
const base = (u) => dec(u.split("/").pop());
const wait = (ms) => new Promise((r) => setTimeout(() => r(false), ms));
document.querySelectorAll(".kc").forEach((box) => {
  const btn = box.querySelector(".kcbtn"), view = box.querySelector(".kcview"), st = box.querySelector(".kcstatus");
  const links = [...box.querySelectorAll(".kcfile")];
  let ready = null;
  const mark = (a) => links.forEach((l) => l.classList.toggle("on", l === a));
  async function open() {
    btn.disabled = true; btn.textContent = "Loading KiCanvas…"; st.textContent = "";
    try { await import(new URL("kicanvas.js", import.meta.url).href); }
    catch (err) { btn.textContent = "Could not load the viewer (" + err.message + ")"; return null; }
    // a file that is gone (renamed or deleted on GitHub) would stop the whole viewer from loading: check first
    const res = await Promise.all(links.map((a) => fetch(a.dataset.raw, { method: "HEAD" }).then((r) => r.ok ? "" : "HTTP " + r.status, (e) => "unreachable")));
    const good = links.filter((a, i) => { if (res[i]) { a.nextElementSibling.nextElementSibling.textContent = " — could not load (" + res[i] + ")"; a.classList.add("bad"); } return !res[i]; });
    if (!good.length) { btn.textContent = "None of the files could be loaded"; return null; }
    const el = document.createElement("kicanvas-embed");
    el.setAttribute("controls", "full"); el.setAttribute("theme", "kicad");
    for (const a of good) { const s = document.createElement("kicanvas-source"); s.setAttribute("src", a.dataset.raw); el.append(s); }
    view.replaceChildren(el); view.hidden = false; btn.hidden = true;
    st.textContent = "Reading " + good.length + " file" + (good.length > 1 ? "s" : "") + "…";
    const project = kcProject(el);
    // "context-request" is KiCanvas-internal: if a future KiCanvas drops it, the viewer still works, only our links don't
    if (!project) { st.textContent = "The file links can't switch this viewer; use the folder icon in its right-hand bar."; return null; }
    const ok = await Promise.race([project.loaded.then(() => true), wait(45000)]);
    if (!ok) {   // a failed download or a file KiCanvas cannot parse: let the reader try again
      st.textContent = "The viewer could not load these files (a network hiccup, or a file it can't read). Try again, or use the GitHub links.";
      view.hidden = true; view.replaceChildren(); btn.hidden = false; btn.disabled = false; btn.textContent = "Try again"; ready = null;
      return null;
    }
    st.textContent = "";
    return { el, project };
  }
  async function show(a) {
    ready ||= open();
    const v = await ready;
    if (!v) return null;
    if (a.classList.contains("bad")) return false;
    const page = [...v.project.pages()].find((p) => dec(p.filename) === base(a.dataset.raw));
    if (!page) { a.nextElementSibling.nextElementSibling.textContent = " — the viewer could not read this file"; return false; }
    v.project.set_active_page(page); mark(a); return true;
  }
  // open on the first schematic (root sheet first); if KiCanvas could not read it, the next file that works
  btn.addEventListener("click", async () => {
    const order = [...links.filter((a) => a.dataset.raw.endsWith(".kicad_sch")), ...links.filter((a) => !a.dataset.raw.endsWith(".kicad_sch"))];
    for (const a of order) if ((await show(a)) !== false) break;   // shown, or the viewer itself failed
  });
  links.forEach((a) => a.addEventListener("click", (ev) => {
    if (ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;   // new tab etc. still goes to GitHub
    ev.preventDefault(); show(a).then(() => view.scrollIntoView({ behavior: "smooth", block: "nearest" }));
  }));
});
"""

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

# ---- 3D view of STL panel files (d, 2026-09-28 02:04). three.js from jsdelivr, loaded only on click;
# the model is fetched from raw.githubusercontent.com (Git LFS pointers retried on media.githubusercontent.com).
THREE_V = "0.170.0"
STL_HEAD = ('<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@' + THREE_V + '/build/three.module.min.js",'
            '"three/addons/":"https://cdn.jsdelivr.net/npm/three@' + THREE_V + '/examples/jsm/"}}</script>')

def stl_files(r):
    return [f for f in panel_files(r)[0] if f.lower().endswith(".stl")]

def stl_box(r):
    fs = stl_files(r)[:4]
    if not fs:
        return ""
    br, rp = repo_branch(r["repo"]), r["repo"]
    btns = "".join(f'<button type="button" class="stlbtn" data-name="{e(link_name(gh_blob(r, f)))}" data-href="{e(gh_blob(r, f))}" '
                   f'data-raw="{e(f"https://raw.githubusercontent.com/{rp}/{br}/{quote(f, safe=chr(47))}")}" '
                   f'data-media="{e(f"https://media.githubusercontent.com/media/{rp}/{br}/{quote(f, safe=chr(47))}")}">'
                   f'View in 3D: {e(link_name(gh_blob(r, f)))}</button>' for f in fs)
    return (f'<div class="box stl" id="stl"><h2>3D model</h2>{btns}<p class="stlstatus small mute"></p>'
            f'<div class="stlview" hidden></div><p class="stlhint small mute" hidden>drag to rotate · scroll or pinch to zoom · right-drag to pan</p></div>'
            f'<script type="module" src="../../stl.js?v={_h(STL_JS)}"></script>')

STL_JS = r"""
// STL panel viewer (d, 2026-09-28 02:04): three.js is fetched only when a button is clicked.
let lib;
const libs = () => lib ||= Promise.all([import("three"), import("three/addons/loaders/STLLoader.js"), import("three/addons/controls/OrbitControls.js")]);
async function getStl(raw, media) {
  let r = await fetch(raw);
  if (!r.ok) throw new Error("HTTP " + r.status);
  let b = await r.arrayBuffer();
  if (b.byteLength < 400 && new TextDecoder().decode(b).startsWith("version https://git-lfs")) {   // Git LFS pointer
    r = await fetch(media);
    if (!r.ok) throw new Error("Git LFS file, HTTP " + r.status);
    b = await r.arrayBuffer();
  }
  return b;
}
function show(view, [THREE, { STLLoader }, { OrbitControls }], buf) {
  if (view._dispose) view._dispose();
  const g = new STLLoader().parse(buf);
  g.computeBoundingBox();
  let s = g.boundingBox.getSize(new THREE.Vector3());
  // a panel is a plate: turn its thinnest axis toward the viewer, then stand its long side upright
  if (s.x <= s.y && s.x <= s.z) g.rotateY(Math.PI / 2); else if (s.y <= s.x && s.y <= s.z) g.rotateX(Math.PI / 2);
  g.computeBoundingBox(); s = g.boundingBox.getSize(new THREE.Vector3());
  if (s.x > s.y) g.rotateZ(Math.PI / 2);
  g.center(); g.computeBoundingBox(); s = g.boundingBox.getSize(new THREE.Vector3());
  const w = view.clientWidth, h = Math.max(260, Math.min(460, Math.round(w * 1.3)));
  const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  ren.setPixelRatio(Math.min(devicePixelRatio, 2)); ren.setSize(w, h);
  view.replaceChildren(ren.domElement);
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(30, w / h, 0.1, 100000);
  const fit = Math.max(s.y, s.x * h / w) / 2 / Math.tan(Math.PI * 15 / 180) * 1.15 + s.z;
  cam.position.set(fit * 0.25, fit * 0.12, fit);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(0.6, 0.8, 1); cam.add(key); scene.add(cam);
  scene.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xb9bdc4, metalness: 0.25, roughness: 0.55, side: THREE.DoubleSide })));
  const ctl = new OrbitControls(cam, ren.domElement);
  const draw = () => ren.render(scene, cam);
  ctl.addEventListener("change", draw); draw();
  const ro = new ResizeObserver(() => { const w2 = view.clientWidth; if (w2 && w2 !== ren.domElement.width / ren.getPixelRatio()) { ren.setSize(w2, h); cam.aspect = w2 / h; cam.updateProjectionMatrix(); draw(); } });
  ro.observe(view);
  view._dispose = () => { ro.disconnect(); ctl.dispose(); g.dispose(); ren.dispose(); };
}
document.querySelectorAll(".stl").forEach(box => box.querySelectorAll(".stlbtn").forEach(btn => btn.addEventListener("click", async () => {
  const view = box.querySelector(".stlview"), st = box.querySelector(".stlstatus"), hint = box.querySelector(".stlhint");
  box.querySelectorAll(".stlbtn").forEach(b => b.classList.toggle("on", b === btn));
  st.textContent = "Loading " + btn.dataset.name + "…"; view.hidden = false;
  try {
    const [three, buf] = await Promise.all([libs(), getStl(btn.dataset.raw, btn.dataset.media)]);
    show(view, three, buf); st.textContent = ""; hint.hidden = false;
  } catch (err) {
    view.hidden = true; hint.hidden = true;
    st.textContent = "Could not show the model here (" + err.message + "). ";
    const a = document.createElement("a"); a.href = btn.dataset.href; a.textContent = "Open it on GitHub"; st.append(a);
  }
})));
"""

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
const FACETS=["tags","lic","terms","mount","files","smt","license","proto","maker"];
const state={q:"",tags:new Set(),lic:new Set(),terms:new Set(),mount:new Set(),files:new Set(),smt:new Set(),license:new Set(),proto:new Set(),maker:new Set(),mode:{},fsort:{},pmode:"hide",panelOnly:false,view:"table",sort:"name",dir:"asc"};
// --- read URL
const sp=new URLSearchParams(location.search);
for(const k of FACETS){for(const v of sp.getAll(k))state[k].add(v);if(sp.get(k+"_mode")==="all")state.mode[k]="all";const fs=sp.get(k+"_sort");if(fs==="name"||fs==="count")state.fsort[k]=fs;}
if(sp.get("proto_mode")==="show")state.pmode="show";if(sp.get("panel")==="1")state.panelOnly=true;if(sp.get("q"))state.q=sp.get("q");if(sp.get("view"))state.view=sp.get("view");if(sp.get("sort"))state.sort=sp.get("sort");if(sp.get("dir"))state.dir=sp.get("dir");
function writeURL(){const p=new URLSearchParams();if(state.q)p.set("q",state.q);for(const k of FACETS){for(const v of state[k])p.append(k,v);if(state.mode[k]==="all")p.set(k+"_mode","all");if(state.fsort[k])p.set(k+"_sort",state.fsort[k]);}
 if(state.pmode==="show")p.set("proto_mode","show");if(state.panelOnly)p.set("panel","1");if(state.view!=="table")p.set("view",state.view);if(state.sort!=="name")p.set("sort",state.sort);if(state.dir!=="asc")p.set("dir",state.dir);
 history.replaceState(null,"",location.pathname+(p.toString()?"?"+p:""));}
// --- facets
const facetDefault={maker:"name"};
// fixed value order (d 05:54): SMT grades in the audit's order; part-number kinds a-z, never by count (they rank equal)
const SMTSHORT={"Parts identified":"parts identified","Placement-ready":"placement-ready","Needs footprint cleanup":"needs cleanup","No SMD parts":"no SMD","Not classified":"not classified"};
const FIXED={smt:["Parts identified","Placement-ready","Needs footprint cleanup","No SMD parts","Not classified","Not checked"]};
function facetHTML(name,key,counts){const by=state.fsort[name]||facetDefault[name]||"count";
 const vals=FIXED[name]?[...FIXED[name].filter(v=>counts.has(v)),...[...counts.keys()].filter(v=>!FIXED[name].includes(v)).sort()]:[...counts.keys()].sort((a,b)=>by==="name"?a.localeCompare(b):counts.get(b)-counts.get(a)||a.localeCompare(b));
 return vals.map(v=>`<label><input type="checkbox" value="${esc(v)}" ${state[key].has(v)?"checked":""}><span>${esc(v)}</span><span class="n">${counts.get(v)}</span></label>`).join("");}
const REG=[];   // live counts (d 06:43): every filter recounts from the modules matching all the OTHER filters
function facet(name,key,getter){const box=$("#f-"+name);const counts=new Map();
 for(const r of rows){for(const v of getter(r))counts.set(v,(counts.get(v)||0)+1);}
 const reg={name,key,getter,box,cur:counts};REG.push(reg);
 box.innerHTML=facetHTML(name,key,counts);
 box.addEventListener("change",ev=>{const v=ev.target.value;ev.target.checked?state[key].add(v):state[key].delete(v);render();});
 const fs=$(`.fsort[data-f=${name}]`);if(fs){$$("input",fs).forEach(i=>i.checked=(state.fsort[name]||facetDefault[name]||"count")===i.value);
  fs.addEventListener("change",ev=>{state.fsort[name]=ev.target.value;box.innerHTML=facetHTML(name,key,reg.cur);recount();
   const q=$("#maker-q");if(name==="maker"&&q&&q.value){q.dispatchEvent(new Event("input"));}writeURL();});}}
function makerLinks(r){return r.mk.map(([s,m])=>`<a class="mk" href="?maker=${encodeURIComponent(m)}">${esc(s)}</a>`).join(" + ");}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
const G={tags:r=>r.tags,lic:r=>r.lic||[],terms:r=>r.terms||[],mount:r=>[r.mount],files:r=>r.files,smt:r=>[r.smt],license:r=>[r.license||"not determined"],proto:r=>r.proto==="X"?["prototype"]:r.proto==="?"?["prototype?"]:[],maker:r=>r.makers};
if($("#f-tags"))facet("tags","tags",G.tags);if($("#f-lic"))facet("lic","lic",G.lic);if($("#f-terms"))facet("terms","terms",G.terms);facet("mount","mount",G.mount);facet("files","files",G.files);facet("smt","smt",G.smt);if($("#f-license"))facet("license","license",G.license);facet("proto","proto",G.proto);facet("maker","maker",G.maker);
$("#maker-q").addEventListener("input",ev=>{const q=ev.target.value.toLowerCase();$$("#f-maker label").forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?"":"none");});
// --- filter
function match(r,ignoreProto,skip){
 if(state.q){const q=state.q.toLowerCase();if(!(r.name+" "+r.creator+" "+r.type+" "+r.notes+" "+r.license).toLowerCase().includes(q))return false;}
 if(state.panelOnly&&!r.pnl&&skip!=="panel")return false;
 if(!ignoreProto&&skip!=="proto"&&!state.proto.size&&state.pmode==="hide"&&r.proto)return false;
 for(const k of FACETS){if(k!==skip&&state[k].size){const vs=G[k](r);const ok=state.mode[k]==="all"?[...state[k]].every(v=>vs.includes(v)):vs.some(v=>state[k].has(v));if(!ok)return false;}}
 return true;}
function sorted(list){const k=state.sort,d=state.dir==="asc"?1:-1;
 const key=r=>k==="name"?r.name.toLowerCase():k==="maker"?r.creator.toLowerCase():k==="date"?r.date:k==="type"?r.type.toLowerCase():k==="mount"?r.mount:k==="parts"?(r.parts==null?(d>0?1e9:-1):r.parts):k==="hp"?(r.hp==null?(d>0?1e9:-1):r.hp):k==="smt"?r.so:r.name.toLowerCase();
 return list.sort((a,b)=>{const x=key(a),y=key(b);return x<y?-d:x>y?d:a.name.localeCompare(b.name);});}
// --- render
function chip(r){let s=r.tags.filter(t=>t!=="not mapped").map(t=>`<span class="chip tag">${esc(t)}</span>`).join("");s+=r.licchips||"";s+=`<span class="chip${r.components?"":" dim"}">${r.components?esc(r.components):"mounting n/d"}</span>`;
 for(const f of r.files)s+=`<span class="chip">${esc(f)}</span>`;
 if(r.proto==="X")s+='<span class="chip warn">prototype</span>';else if(r.proto==="?")s+='<span class="chip warn">prototype?</span>';return s;}
function card(r){const meta=[r.hpt&&r.hpt!=="?"?r.hpt:"",r.parts==null?"":r.parts+" parts"].filter(Boolean).join(" · ");return `<div class="card">${meta?`<div class="parts">${esc(meta)}</div>`:""}<div class="name"><a href="m/${r.slug}/">${esc(r.name)}</a></div><div class="maker">${makerLinks(r)}</div><div class="type">${r.type?esc(r.type):'<span class="nd">type not determined</span>'}</div><div class="chips">${chip(r)}</div></div>`;}
const TH=(p,d)=>"https://wsrv.nl/?url="+encodeURIComponent(/^https?:/.test(p)?p:"https://raw.githubusercontent.com/"+p)+(/\.(svg|ai)$/i.test(p)?"&trim=10&bg=d6d2c8":"")+"&w=56&h=64&fit=inside"+(/\.(svg|ai)$/i.test(p)?"":"&we")+"&output=webp&q=75"+(d>1?"&dpr=2":"");
function pic(r){return r.ph?`<a href="m/${r.slug}/" tabindex="-1"><img loading="lazy" decoding="async" alt="" src="${TH(r.ph,1)}" srcset="${TH(r.ph,1)} 1x, ${TH(r.ph,2)} 2x" onerror="this.remove()"></a>`:"";}
function table(list){const h=[["img",""],["name","Module"],["maker","Maker"],["type","Type"],["mount","Mounting"],["smt","SMT"],["hp","HP"],["parts","Parts"],["files","Files"],["license","License"],["date","Date"]];
 return `<table class="list"><thead><tr>${h.map(([k,l])=>`<th data-k="${k}" ${state.sort===k?`data-dir="${state.dir}"`:""}>${l}</th>`).join("")}</tr></thead><tbody>${list.map(r=>`<tr><td class="im">${pic(r)}</td><td><a href="m/${r.slug}/">${esc(r.name)}</a>${r.proto?` <span class="chip warn">${r.proto==="X"?"prototype":"prototype?"}</span>`:""}</td><td>${makerLinks(r)}</td><td>${esc(r.type)}</td><td>${r.components?esc(r.components):'<span class="nd">n/d</span>'}</td><td class="small nw" title="${esc(r.smt+(r.pn.length?" ("+r.pn[0]+" part numbers)":"")+(r.smt==="Not checked"?": no KiCad board or placement file to read":""))}">${r.smt==="Not checked"?'<span class="nd">not checked</span>':esc(SMTSHORT[r.smt]||r.smt)}</td><td class="num">${r.hpt&&r.hpt!=="?"?esc(r.hpt):r.hpt==="?"?'<span class="nd" title="panel files present, HP not determined">?</span>':'<span class="nd">—</span>'}</td><td class="num" title="${r.parts==null?"":r.pp==null?"board parts only; panel hardware not counted":"includes "+r.pp+" panel parts"}">${r.parts==null?'<span class="nd">—</span>':r.parts+(r.pooled?'<span class="mute" title="summed over several board files in the folder — variants may be pooled">*</span>':'')}</td><td>${r.files.join(", ")}</td><td>${r.licchips||(r.license?esc(r.license):'<span class="nd">n/d</span>')}</td><td class="mute">${esc(r.date)}</td></tr>`).join("")}</tbody></table>`;}
// values of the same filter don't narrow each other ("any"); a filter set to "all" does narrow itself
function recount(){for(const f of REG){const skip=state.mode[f.name]==="all"?null:f.name;const c=new Map();
  for(const r of rows){if(!match(r,false,skip))continue;for(const v of f.getter(r))c.set(v,(c.get(v)||0)+1);}
  f.cur=c;$$("label",f.box).forEach(l=>{const i=l.querySelector("input"),n=l.querySelector(".n");if(!i||!n)return;const k=c.get(i.value)||0;n.textContent=k;l.classList.toggle("zero",!k&&!i.checked);});}
 const po=$("#panel-only");if(po){const n=po.parentNode.querySelector(".n");if(n){const k=rows.filter(r=>r.pnl&&match(r,false,"panel")).length;n.textContent=k;po.parentNode.classList.toggle("zero",!k&&!po.checked);}}}
function render(){recount();const list=sorted(rows.filter(r=>match(r)));const hid=(!state.proto.size&&state.pmode==="hide")?rows.filter(r=>r.proto&&match(r,true)).length:0;
 $("#count").textContent=`${list.length} of ${rows.length} modules`+(hid?` · ${hid} prototypes hidden`:"");
 const pm=$(".pmode");if(pm)pm.classList.toggle("off",state.proto.size>0);
 const out=$("#out");out.innerHTML=state.view==="grid"?`<div class="grid">${list.map(card).join("")}</div>`:table(list);
 if(state.view==="table")$$("#out th").forEach(th=>th.addEventListener("click",()=>{const k=th.dataset.k;if(k==="files"||k==="img")return;if(state.sort===k)state.dir=state.dir==="asc"?"desc":"asc";else{state.sort=k;state.dir="asc";}$("#sort").value=state.sort;render();}));
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

# ---- SMT assembly readiness (d 05:54, via the working-branch session's note 2026-09-28-0557). Read-only audit files keyed
# by row id: data/cpl-rows.tsv (grade per row), cpl-shipped.tsv (designer's placement/BOM files), cpl-audit.tsv (per board).
# d's wording rules: part-number kinds rank equal (no LCSC-first order, no "JLCPCB-ready"); say "parts identified", never
# "assembly-ready"; no-smd is neutral; rows the audit could not read are "not checked", never a negative.
SMT_LABEL = {"parts-identified": "Parts identified", "cpl-ready": "Placement-ready",
             "needs-cleanup": "Needs footprint cleanup", "no-smd": "No SMD parts", "unclassified": "Not classified"}
SMT_ORDER = ["Parts identified", "Placement-ready", "Needs footprint cleanup", "No SMD parts", "Not classified", "Not checked"]
def smt_rank(label):   # a grade the audit adds later sorts after the known ones instead of breaking the build (07:50)
    return SMT_ORDER.index(label) if label in SMT_ORDER else len(SMT_ORDER)
SMT_SAYS = {"parts-identified": "every SMD part has a part number, and the footprints export a clean placement (CPL) file",
            "cpl-ready": "the footprints export a clean placement (CPL) file; not every SMD part has a part number yet",
            "needs-cleanup": "some footprints need fixing before a placement (CPL) file will list every part",
            "no-smd": "no surface-mount parts to place on the boards checked",
            "unclassified": "the designer's placement file lists parts, but no file says which of them are surface-mount"}
PN_LABEL = {"LCSC": "LCSC", "MPN/SKU": "MPN or SKU", "mixed": "mixed"}
SMT_ISSUE = {"smd_pads,_no_smd_attr": "{n} footprint(s) have SMD pads but are marked through-hole: fix their type in the footprint library before exporting a CPL (KiCad's SMD-only export drops them)",
             "no_schematic_link": "{n} SMD part(s) have no schematic link",
             "bad/duplicate_ref": "{n} part(s) have a missing (REF**) or duplicate reference"}
_smt = None
def _smt_load():
    global _smt
    if _smt is None:
        def tsv(n):
            f = os.path.join(ROOT, "data", n)
            if not os.path.exists(f):
                return []
            return list(csv.DictReader(open(f, encoding="utf-8"), delimiter="\t"))
        boards = defaultdict(list)
        for b in tsv("cpl-audit.tsv"):
            boards[b["id"]].append(b)
        _smt = ({x["id"]: x for x in tsv("cpl-rows.tsv")}, {x["id"]: x for x in tsv("cpl-shipped.tsv")}, boards)
    return _smt

def smt_of(r):
    """(label, part-number kind or '') for the index."""
    x = _smt_load()[0].get(r["id"])
    if not x:   # d 08:22: a THT row has no SMD parts by definition, so it is not "not checked" (Mounting column's verdict)
        return ("No SMD parts" if r["components"] == "THT" else "Not checked"), ""
    return SMT_LABEL.get(x["grade"], x["grade"]), (PN_LABEL.get(x["part_numbers"], x["part_numbers"]) if x["grade"] == "parts-identified" else "")

def smt_cell(r):
    x = _smt_load()[0].get(r["id"])
    if not x:
        if r["components"] == "THT":
            return 'No SMD parts <span class="mute small">· from Mounting: every part is through-hole</span>'
        return nd("not checked — no KiCad board or placement file to read")
    lab, pn = smt_of(r)
    src = "from the designer's placement files" if x["source"] == "shipped files" else "from the KiCad board"
    return (f'{e(lab)}{f" ({e(pn)})" if pn else ""} <span class="mute small">· {src} · <a href="#smt">details</a></span>')

def smt_box(r):
    rows_, shipped, boards = _smt_load()
    x = rows_.get(r["id"])
    if not x:
        return ""
    lab, pn = smt_of(r)
    sha = r.get("sha") or repo_branch(r["repo"])
    blob = lambda p: f"https://github.com/{r['repo']}/blob/{sha}/{quote(p, safe='/')}"
    out = [f'<p style="margin:0 0 6px"><b>{e(lab)}</b>{f" ({e(pn)} part numbers)" if pn else ""}: '
           f'<span class="mute">{e(SMT_SAYS.get(x["grade"], ""))}.</span></p>']
    live = [b for b in boards.get(r["id"], []) if not b["grade"].startswith("skipped")]
    smd = sum(int(b["smd"] or 0) for b in live); back = sum(int(b["back_side_smd"] or 0) for b in live)
    if smd:
        side = (" — all on the back side (assemblers price bottom-side placement separately)" if back == smd
                else f", {back} on the back side" if back else ", all on the front")
        out.append(f'<p class="small" style="margin:0 0 6px">{smd} SMD part{"s" if smd != 1 else ""} on {len(live)} board{"s" if len(live) != 1 else ""}{side}.</p>')
    sh = shipped.get(r["id"])
    if sh:
        files = lambda v: [p.strip() for p in (v or "").split("; ") if p.strip() and not p.strip().startswith("(not this row's board")]
        pl, bm = files(sh["placement_files"]), files(sh["bom_files"])
        if pl or bm:
            li = "".join(f'<li><a href="{e(blob(p))}">{e(p)}</a> <span class="mute small">{k}</span></li>'
                         for k, ps in (("placement (CPL)", pl), ("BOM", bm)) for p in ps)
            out.append(f'<p class="small mute" style="margin:6px 0 2px">The designer ships these files for machine assembly:</p><ul class="links">{li}</ul>')
    if int(x.get("shipped_refs_not_on_board") or 0) > 0:
        out.append('<p class="small" style="margin:6px 0 0">The placement file may be older than the board: '
                   f'{int(x["shipped_refs_not_on_board"])} of its references {"is" if int(x["shipped_refs_not_on_board"]) == 1 else "are"} not on the current board.</p>')
    if x["grade"] == "needs-cleanup":
        items = []
        for b in live:
            for kind, n in re.findall(r"issue\[([^\]]+)\]=(\d+)", b.get("issues") or ""):
                t = SMT_ISSUE.get(kind, kind + ": {n}").format(n=n)
                items.append(f'<li>{e(os.path.basename(b["board"]))}: {e(t)}'
                             + (f'<br><span class="mute small">{e(b["issue_footprints"])}</span>' if b.get("issue_footprints") and kind.startswith("smd_pads") else "") + '</li>')
        if items:
            out.append(f'<ul class="links" style="margin-top:6px">{"".join(items)}</ul>')
    out.append('<p class="small mute" style="margin:8px 0 0">Read from the design files only: part stock, rotations and '
               'assembler rules are not checked. Source: <code>data/cpl-*.tsv</code>.</p>')
    return f'<div class="box" id="smt"><h2>SMT assembly</h2>{"".join(out)}</div>'

def build_index(rows, typemap, licmap):
    data = [dict(tags=tags_of(r, typemap), makers=makers_of(r), mk=credit_parts(r), parts=(counts_of(r) or {}).get("total"), pp=(counts_of(r) or {}).get("panel"), pooled=(counts_of(r) or {}).get("files", 1) > 1,
        lic=[family_label(g) for g in grants_of(r, licmap)], terms=[TERMS_LABEL.get(g["terms"], g["terms"]) for g in grants_of(r, licmap)],
        licchips="".join(grant_chip(g) for g in grants_of(r, licmap)) if licmap else "",
        id=r["id"], slug=r["slug"], name=r["module_name"], creator=r["creator"], type=r["type"],
        license=r["license"], components=r["components"], mount=bucket_components(r["components"]),
        files=files_of(r), proto=r["prototype"], date=r["date"], notes=r["notes"],
        hp=hp_of(r)[0], hpt=hp_of(r)[1], pnl=bool(panel_sources(r)),   # ships panel files; a bare "0HP" (d 08:24) has none
        ph=front_raw(r),
        smt=smt_of(r)[0], so=smt_rank(smt_of(r)[0]), pn=[smt_of(r)[1]] if smt_of(r)[1] else [],
    ) for r in rows]
    n_pnl = sum(1 for d in data if d["pnl"])
    MULTI = {"tags", "lic", "terms", "files", "maker"}   # a module can carry several values -> any/all makes sense
    SORTABLE = {"maker", "tags"}                                   # facets with a name/count sort switch
    def facet(name, label, extra="", after=""):
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
        return f'<details open><summary><span>{label}</span></summary>{sw}{extra}<div id="f-{name}" class="{"maker-list" if name=="maker" else ""}"></div>{after}</details>'
    aside = (
        '<input id="q" type="search" placeholder="Search name, maker, type, notes…" aria-label="Search">'
        + (facet("tags", "Type <span class=\"mute\" style=\"font-weight:400\">(draft tags)</span>") if typemap else "")
        + facet("files", "Files in repo")
        + facet("mount", "Mounting")
        + facet("smt", "SMT assembly", after='<p class="small mute" style="margin:4px 0 0">From the design files; through-hole (THT) modules count as "no SMD parts"; "not checked" = no KiCad board or placement file to read.</p>')

        + (facet("terms", "License terms <span class=\"mute\" style=\"font-weight:400\">(draft)</span>") if licmap else facet("license", "License (as recorded)"))
        # the per-family "License" facet is hidden (d, 2026-09-26 14:17); ?lic=<family> in the URL still filters
        + facet("maker", "Maker", '<input id="maker-q" type="search" placeholder="filter makers" aria-label="Filter makers">')
        # panel checkbox lives in Build status (d, 2026-09-26 17:49)
        + facet("proto", "Build status", after=f'<label class="solo" title="Modules that ship panel files: kicad, eagle, easyeda, gerbers, svg, dxf, ai, pdf, Front Panel Designer or 3D"><input type="checkbox" id="panel-only"><span>only modules with panel source files</span><span class="n">{n_pnl}</span></label>')
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
    """Just the value (d, 2026-09-28 08:06): how it was measured or stated is in the Evidence box (panel_basis)."""
    _, t = hp_of(r)
    if t and t != "?":
        return f'<b>{e(t)}</b>'
    if t == "?":
        return nd("not determined")
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

# Photo thumbnail (d, 2026-09-26 18:00; one per module, the front view if the name says so - d 18:01): resized
# on request by wsrv.nl (open-source image proxy, Cloudflare-cached) from the raw GitHub file - nothing stored.
# Originals total 1.9 GB (p90 3.9 MB each), so they are never loaded as thumbnails. Other photos stay links.
FRONT_PLUS = {"front": 10, "frontpanel": 10, "faceplate": 8, "panel": 3, "assembled": 3, "finished": 3, "built": 2,
              "module": 1, "render": 1, "rendering": 1, "f": 2, "photo": 1}
FRONT_MINUS = {"back": 10, "rear": 10, "bottom": 8, "side": 8, "pcb": 6, "board": 5, "boards": 5, "inside": 6,
               "internal": 6, "top": 3, "detail": 4, "closeup": 4, "solder": 5, "soldering": 5, "soldered": 5, "bb": 5, "breadboard": 6,
               "proto": 3, "prototype": 3, "tutorial": 4, "handbuch": 4, "seite": 4, "screen": 5, "scope": 6,
               "result": 3, "b": 2, "power": 2, "usb": 2, "din": 2}

def front_photo(urls, name="", basis=""):
    # photos picked by hand (data/photo-includes.tsv, first in the list) are used as given (d, 2026-09-28 01:45)
    if "photo-includes" in basis:
        return urls[0]
    return _front_photo(urls, name)

def _front_photo(urls, name=""):
    """Pick the photo most likely to show the module's front: scored on filename words, ties keep list order.
    An (SMD)/(THT) row prefers photos of its own variant."""
    other = {"smd": "tht", "tht": "smd"}.get(next((v for v in ("smd", "tht") if f"({v})" in name.lower()), ""), "")
    def score(u):
        words = re.findall(r"[a-z]+", link_name(u).lower().rsplit(".", 1)[0])
        return (sum(FRONT_PLUS.get(w, 0) for w in words) - sum(FRONT_MINUS.get(w, 0) for w in words)
                - (6 if other and other in words else 0))
    return urls[max(range(len(urls)), key=lambda i: (score(urls[i]), -i))]

def fallback_thumb(r):
    """No photo: a panel drawing instead (d, 2026-09-28 00:49) - the first .svg among the recorded panel files
    (hand additions such as Lights' drawing live in data/panel-includes.tsv on the working branch, d 00:57).
    Returns a github.com /blob/ URL or ''."""
    # .ai panel files too (d, 2026-09-28 07:38): Illustrator's PDF-compatible .ai renders through wsrv like a PDF - all 61
    # on the site tested in a browser, 07:34; SVG first when a module has both
    fs = panel_files(r)[0]
    svg = [p for p in fs if p.lower().endswith(".svg")] + [p for p in fs if p.lower().endswith(".ai")]
    return gh_blob(r, svg[0]) if svg else ""

# Readable copies of hairline panel drawings (d, 2026-09-28 05:30): site/drawing_copies.py writes them to site/drawings/,
# main() publishes them in docs/drawings/, and only the THUMBNAIL of such a drawing is made from the copy - links and
# the "Files" lists still point at the original in its repo. Copy names carry a content hash, so wsrv never serves a
# stale thumbnail after a copy changes.
SITE_URL = "https://daaaaaaaaaniel.github.io/my-awesome-eurorack/"
DRAWINGS = os.path.join(ROOT, "site", "drawings")
def load_drawing_copies():
    f = os.path.join(DRAWINGS, "index.tsv")
    if not os.path.exists(f):
        return {}
    out = {}
    for l in open(f, encoding="utf-8"):
        x = l.rstrip("\n").split("\t")
        if len(x) >= 3 and not l.startswith("#") and x[0] != "slug" and os.path.exists(os.path.join(DRAWINGS, x[2])):
            out[x[1]] = SITE_URL + "drawings/" + x[2]
    return out
DRAWING_COPY = load_drawing_copies()   # original github.com blob URL -> published copy URL

def front_raw(r):
    """Index image column (d, 2026-09-26 19:42): 'owner/repo/branch/path' of the module's front photo, or ''."""
    urls = (r.get("photos") or "").split()
    if not urls:
        fb = fallback_thumb(r)
        if fb in DRAWING_COPY:
            return DRAWING_COPY[fb]
        return re.sub(r"^https://github\.com/([^/]+)/([^/]+)/blob/", r"\1/\2/", fb) if fb else ""
    return re.sub(r"^https://github\.com/([^/]+)/([^/]+)/blob/", r"\1/\2/", front_photo(urls, r["module_name"], r.get("photos_basis") or ""))

def thumb_src(u, w=400, h=360, dpr=1):
    u = DRAWING_COPY.get(u, u)   # a readable copy of a hairline drawing, when there is one
    # SVG drawings sit on light grey #d6d2c8 (d 2026-09-28 04:55, from website-js): transparent drawings stay readable in both
    # themes - the page background hid black lines in dark mode, white hid white print (Bit Reactor's jack circles).
    # SVG panel drawings are often an A4 Inkscape page with the panel in one corner: trim=10 crops the blank
    # page (wsrv trims before resizing, so the panel then fills the box). SVGs may be enlarged; photos never are.
    raw = re.sub(r"^https://github\.com/([^/]+)/([^/]+)/blob/", r"https://raw.githubusercontent.com/\1/\2/", u)
    return f"https://wsrv.nl/?url={quote(raw, safe='')}{'&trim=10&bg=d6d2c8' if raw.lower().endswith(('.svg', '.ai')) else ''}&w={w}&h={h}&fit=inside{'' if raw.lower().endswith(('.svg', '.ai')) else '&we'}&output=webp&q=78" + (f"&dpr={dpr}" if dpr > 1 else "")

def drawing_box(u):
    n = link_name(u)
    return (f'<div class="box" id="photos"><h2>Panel drawing</h2><a class="thumb" href="{e(u)}" title="{e(n)}"><img loading="lazy" '
            f'decoding="async" alt="{e(n)}" src="{e(thumb_src(u))}" srcset="{e(thumb_src(u))} 1x, {e(thumb_src(u, dpr=2))} 2x" '
            f'onerror="this.parentNode.classList.add(\'broken\');this.replaceWith(document.createTextNode(this.alt))"></a>'
            f'<p class="small mute" style="margin:4px 0 0">{e(n)} · no photo in the repo, so the panel drawing is shown</p></div>')

# ---- Photo gallery (d, 2026-09-28 04:28 on website-js, ported 06:14): the main photo with prev/next arrows, a strip of
# small square thumbnails of every photo below it (the one shown is highlighted) and the file name as a muted
# "3 / 31 · name" caption. Order: the front photo first, then the repo's order. Arrows, strip clicks, <-/-> and touch
# swipes change the photo (PHOTOS_JS); Cmd/Ctrl-clicks on the strip and clicks on the photo open the original. Without
# JavaScript the strip thumbnails are plain links to the originals and the arrows stay hidden. The frame is the image
# itself (d 04:11/04:14: fitted to the image, 360px cap; no flex/fit-content frame, which drew wide images squished).
def strip_src(u, dpr=1):
    """Square strip thumbnail: 64px, cropped to the most interesting part (wsrv a=attention); SVGs on grey like thumb_src."""
    raw = re.sub(r"^https://github\.com/([^/]+)/([^/]+)/blob/", r"https://raw.githubusercontent.com/\1/\2/", u)
    svg = raw.lower().endswith((".svg", ".ai"))
    return (f"https://wsrv.nl/?url={quote(raw, safe='')}{'&trim=10&bg=d6d2c8' if svg else ''}&w=64&h=64&fit=cover&a=attention"
            f"{'' if svg else '&we'}&output=webp&q=70" + (f"&dpr={dpr}" if dpr > 1 else ""))

def photo_cap(i, n, u):
    return ((f'<span class="gcount">{i + 1} / {n}</span> · ' if n > 1 else "")
            + f'<a href="{e(u)}" title="Open the original on GitHub">{e(link_name(u))}</a>')

def photo_box(urls, name="", fold=12, basis=""):
    if not urls:
        return ""
    main = front_photo(urls, name, basis)
    lst = [main] + [u for u in urls if u != main]
    n, nm = len(lst), link_name(main)
    img = (f'<a class="thumb" href="{e(main)}" title="{e(nm)}"><img loading="lazy" decoding="async" alt="{e(nm)}" '
           f'src="{e(thumb_src(main))}" srcset="{e(thumb_src(main))} 1x, {e(thumb_src(main, dpr=2))} 2x" '
           f'onerror="this.parentNode.classList.add(\'broken\');this.replaceWith(document.createTextNode(this.alt))"></a>')
    nav = ('<button type="button" class="gnav prev" aria-label="Previous photo" hidden>‹</button>'
           '<button type="button" class="gnav next" aria-label="Next photo" hidden>›</button>') if n > 1 else ""
    strip = ""
    if n > 1:
        strip = '<div class="strip">' + "".join(
            f'<a href="{e(u)}" data-i="{i}" title="{e(link_name(u))}" aria-label="Photo {i + 1} of {n}: {e(link_name(u))}"'
            + ("" if i else ' class="on" aria-current="true"')
            + f'><img loading="lazy" decoding="async" alt="" src="{e(strip_src(u))}" srcset="{e(strip_src(u))} 1x, {e(strip_src(u, 2))} 2x" onerror="this.remove()"></a>'
            for i, u in enumerate(lst)) + "</div>"
    return (f'<div class="box" id="photos"><h2>Photos <span class="mute" style="text-transform:none;letter-spacing:0">({n})</span></h2>'
            f'<div class="gal">{img}{nav}</div><p class="gcap small mute">{photo_cap(0, n, main)}</p>{strip}'
            f'<p class="gnote mute">thumbnails via wsrv.nl · click the photo for the original</p></div>'
            + (f'<script type="module" src="../../photos.js?v={_h(PHOTOS_JS)}"></script>' if n > 1 else ""))

# The gallery's behaviour. thumb() mirrors thumb_src() and cap() mirrors photo_cap(), so a photo shown after a click is
# the same thumbnail the page would have built for it.
PHOTOS_JS = r"""
const box = document.getElementById("photos"), strip = box && box.querySelector(".strip");
if (strip) {
  const e = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  const linkName = u => u.replace(/\/+$/, "").split("/").pop().replace(/(%[0-9A-Fa-f]{2})+/g, m => { try { return decodeURIComponent(m); } catch { return m; } });
  const thumb = (u, dpr = 1) => {
    const raw = u.replace(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\//, "https://raw.githubusercontent.com/$1/$2/");
    const svg = /\.(svg|ai)$/i.test(raw);
    const q = encodeURIComponent(raw).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
    return `https://wsrv.nl/?url=${q}${svg ? "&trim=10&bg=d6d2c8" : ""}&w=400&h=360&fit=inside${svg ? "" : "&we"}&output=webp&q=78` + (dpr > 1 ? `&dpr=${dpr}` : "");
  };
  const cap = (i, n, u) => `<span class="gcount">${i + 1} / ${n}</span> · <a href="${e(u)}" title="Open the original on GitHub">${e(linkName(u))}</a>`;
  const list = [...strip.children].map(a => a.getAttribute("href")), N = list.length;
  const gal = box.querySelector(".gal"), capEl = box.querySelector(".gcap");
  let cur = 0;
  const show = i => {
    cur = (i + N) % N;
    const u = list[cur], n = linkName(u), old = box.querySelector("a.thumb"), h = old.offsetHeight;
    old.outerHTML = `<a class="thumb" href="${e(u)}" title="${e(n)}"><img loading="lazy" decoding="async" alt="${e(n)}" src="${e(thumb(u))}" srcset="${e(thumb(u))} 1x, ${e(thumb(u, 2))} 2x" onerror="this.parentNode.classList.add('broken');this.replaceWith(document.createTextNode(this.alt))"></a>`;
    const t = box.querySelector("a.thumb"), img = t.querySelector("img");
    t.style.minHeight = h + "px";                                 // hold the height while the next image loads
    if (img) ["load", "error"].forEach(k => img.addEventListener(k, () => { t.style.minHeight = ""; }, { once: true }));
    capEl.innerHTML = cap(cur, N, u);
    [...strip.children].forEach((a, k) => { a.classList.toggle("on", k === cur); if (k === cur) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current"); });
    const a = strip.children[cur];                                // keep the highlighted thumbnail in view, inside the strip only
    strip.scrollTo({ left: a.offsetLeft - (strip.clientWidth - a.offsetWidth) / 2, behavior: "smooth" });
    for (const k of [cur + 1, cur - 1]) (new Image()).src = thumb(list[(k + N) % N], devicePixelRatio > 1 ? 2 : 1);
  };
  box.querySelectorAll(".gnav").forEach(b => { b.hidden = false; });
  box.querySelector(".gnav.prev").addEventListener("click", () => show(cur - 1));
  box.querySelector(".gnav.next").addEventListener("click", () => show(cur + 1));
  strip.addEventListener("click", ev => {
    const a = ev.target.closest("a[data-i]");
    if (!a || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    ev.preventDefault(); show(+a.dataset.i);
  });
  box.addEventListener("keydown", ev => {
    if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") { ev.preventDefault(); show(cur + (ev.key === "ArrowRight" ? 1 : -1)); }
  });
  let x0 = null, swiped = false;                                  // touch/pen swipe on the main photo
  gal.addEventListener("pointerdown", ev => { x0 = ev.pointerType === "mouse" ? null : ev.clientX; });
  gal.addEventListener("pointerup", ev => {
    if (x0 === null) return;
    const dx = ev.clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) { swiped = true; show(cur + (dx < 0 ? 1 : -1)); }
  });
  gal.addEventListener("click", ev => { if (swiped) { swiped = false; ev.preventDefault(); } }, true);
}
"""


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
        ("Board parts", (lambda c: (f'<b>{c["total"]}</b> footprints — ' + (f'{c["panel"]} panel parts (jacks, pots, switches, LEDs, headers) + {c["board"]} on the board: ' if c["panel"] is not None else "") + f'SMD {c["smd"]} (+{c["smd_ic"]} ICs), THT {c["tht"]} (+{c["tht_ic"]} ICs, +{c["tht_to"]} TO-92/220)'
                                      ' <span class="mute small">· ' + ('panel parts included' if c["panel"] is not None else 'panel hardware not counted') + (f' · summed over {c["files"]} board files in the folder, so variants may be pooled' if c["files"] > 1 else "") + '</span>') if c else nd("not counted (no board file or machine-readable BOM in scope)"))(counts_of(r))),
        ("Layout files", nd(r["layout"])),
        ("Schematic", schematic_cell(r, SHARED[(r["repo"], r["module_dir"])] > 1)),
        ("BOM", bom_cell(r, SHARED[(r["repo"], r["module_dir"])] > 1)),
        ("SMT assembly", smt_cell(r)),
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
    ev_box = f'<div class="ev"><h2>Evidence — why the cells say what they say</h2><dl>{ev}</dl></div>' if ev else ""
    lic_box = ""
    if grants:
        trs = "".join(f'<tr><td>{e(SCOPE_LABEL.get(g["scope"], g["scope"]))}</td><td>{e(family_label(g))}{(" " + e(version_label(g))) if g["version"] else ""}</td><td>{e(TERMS_LABEL.get(g["terms"], g["terms"]))}</td><td class="mute">{e(g["note"].replace("qualifier: ", "").replace("scope text: ", ""))}{(" <b>source: " + e(g["source"]) + "</b>") if g.get("source") and g["source"] != "repo" else ""}</td></tr>' for g in grants)
        draft = ' <span style="text-transform:none;letter-spacing:0">(draft categorisation)</span>' if any(g["status"] != "ok" for g in grants) else ""
        lic_box = f'<div class="box"><h2>License{draft}</h2><table class="grants"><tr><th>covers</th><th>license</th><th>terms</th><th></th></tr>{trs}</table><p class="small mute" style="margin:8px 0 0">Terms describe the license family, not this repository. Check the repository before relying on any of it.</p></div>'
    notes = f'<div class="box"><h2>Notes</h2>{e(r["notes"])}</div>' if r["notes"] else ""
    follow = f'<div class="fu"><h2>Open follow-up</h2>{e(r["followup"])}</div>' if r["followup"] else ""
    # d, 2026-09-28 01:52: evidence and open follow-up sit in one collapsible block, closed by default
    label = " and open follow-up".join(["Evidence", ""]) if (follow and ev_box) else ("Evidence" if ev_box else "Open follow-up")
    more_box = (f'<details class="box evbox"><summary><span>{label}</span><span class="mute small">why the cells say what they say</span></summary>'
                f'{follow}{ev_box}</details>') if (follow or ev_box) else ""
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
<div class="cols"><div><dl class="spec">{dl}</dl>{smt_box(r)}{lic_box}{notes}{more_box}</div>
<div><div class="box"><h2>Files &amp; links</h2><ul>{"".join(links)}</ul></div>
{photo_box((r.get("photos") or "").split(), r["module_name"], basis=r.get("photos_basis") or "") or (drawing_box(fallback_thumb(r)) if fallback_thumb(r) else "")}{stl_box(r)}{link_box("Build guide", (r.get("build") or "").split(), build_link)}
<div class="box"><h2>Record</h2>row <code>{e(r["id"])}</code> · detector v{e(r["detector_version"])} · <a href="{REPO_URL}/blob/website/data/modules.tsv">data/modules.tsv</a><br>
<span class="mute small">Blank cells are blank on purpose: the repo didn't state it, so we don't either.</span></div></div></div>
{schem_box(r)}{kicanvas_box(r, SHARED[(r["repo"], r["module_dir"])] > 1)}
<div class="notice">This is a third-party design. Check the repository (and its license) before ordering parts or selling boards.</div>
{more}</div>"""
    desc = f"{r['module_name']} by {r['creator']}" + (f" — {r['type']}" if r["type"] else "") + (f", {r['components']}" if r["components"] else "")
    return page(title, body, "../../", desc, head=STL_HEAD if stl_files(r) else "")

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
<dt>Board parts</dt><dd>Footprint counts from the board file or a machine-readable BOM, shown only for rows whose component confidence is <b>Strong</b> (548 of 993; another 114 rows have a tally but from weaker evidence and are not shown). The number <b>includes panel parts</b> (jacks, pots, switches, LEDs, headers; not mounting holes) where the detector recorded a panel count; elsewhere it is board parts only, and the module page and the tooltip say which. This number never feeds the THT / SMD / both call, which ignores panel hardware. A <b>*</b> after the number means the folder held several board files and the detector summed them, so alternate versions may be pooled (the module page says how many). Pin counts are not recorded.</dd>
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
    if DRAWING_COPY:
        os.makedirs(os.path.join(OUT, "drawings"))
        for u in DRAWING_COPY.values():
            shutil.copyfile(os.path.join(DRAWINGS, u.rsplit("/", 1)[1]), os.path.join(OUT, "drawings", u.rsplit("/", 1)[1]))
    with open(os.path.join(OUT, "site.css"), "w", encoding="utf-8") as f: f.write(CSS.strip() + "\n")
    with open(os.path.join(OUT, "site.js"), "w", encoding="utf-8") as f: f.write(JS.strip() + "\n")
    with open(os.path.join(OUT, "schem.js"), "w", encoding="utf-8") as f: f.write(SCHEM_JS.strip() + "\n")
    with open(os.path.join(OUT, "stl.js"), "w", encoding="utf-8") as f: f.write(STL_JS.strip() + "\n")
    with open(os.path.join(OUT, "photos.js"), "w", encoding="utf-8") as f: f.write(PHOTOS_JS.strip() + "\n")
    with open(os.path.join(OUT, "kc-embed.js"), "w", encoding="utf-8") as f: f.write(KC_JS.strip() + "\n")
    shutil.copyfile(os.path.join(ROOT, "site", "kicanvas", "kicanvas.js"), os.path.join(OUT, "kicanvas.js"))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f: f.write(build_index(rows, typemap, licmap))
    with open(os.path.join(OUT, "about.html"), "w", encoding="utf-8") as f: f.write(build_about(rows))
    for r in rows:
        d = os.path.join(OUT, "m", r["slug"]); os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f: f.write(build_detail(r, by_maker, typemap, licmap))
    # KiCanvas test index (branch kicanvas-test): which pages carry the viewer, and what it leaves out
    kc = [(r, *kicad_files(r, SHARED[(r["repo"], r["module_dir"])] > 1)) for r in rows]
    shown = [x for x in kc if x[1] or x[2]]
    li = "".join(f'<tr><td><a href="m/{r["slug"]}/index.html#kicanvas">{e(r["module_name"])}</a></td><td>{e(r["creator"])}</td><td>{len(sc)}</td><td>{len(ok)}</td><td>{len(old)}</td></tr>' for r, sc, ok, old in shown)
    body = (f'<div class="detail" style="max-width:900px"><h1>KiCanvas viewer coverage</h1><p>{sum(1 for x in kc if x[1] or x[2] or x[3])} rows have KiCad files in scope; '
            f'{len(shown)} module pages get the viewer ({sum(1 for x in shown if x[2])} with a board, {sum(1 for x in shown if x[1])} with schematics). '
            f'{sum(1 for x in kc if x[3] and not (x[1] or x[2]))} have only KiCad 5 or older files and get no viewer. '
            f'Board columns: drawable (KiCad 6+) / left out (KiCad 5 or older).</p>'
            f'<table class="t"><thead><tr><th>Module</th><th>Maker</th><th>Sheets</th><th>Boards</th><th>Left out</th></tr></thead><tbody>{li}</tbody></table></div>')
    with open(os.path.join(OUT, "kicanvas-coverage.html"), "w", encoding="utf-8") as f: f.write(page("KiCanvas viewer coverage — " + SITE_TITLE, body, "", "Which module pages carry the KiCanvas viewer."))
    print(f"wrote {len(rows)} module pages + index/about to {os.path.relpath(OUT, ROOT)}/")

if __name__ == "__main__":
    main()
