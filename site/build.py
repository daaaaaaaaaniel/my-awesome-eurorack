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
import csv, html, json, os, re, shutil, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(ROOT, "data", "modules.tsv")
TYPEMAP = os.path.join(ROOT, "data", "type-categories.tsv")
ALIASES = os.path.join(ROOT, "data", "maker-aliases.tsv")   # site-side only: alias -> maker
OUT = os.path.join(ROOT, "docs")
REPO_URL = "https://github.com/daaaaaaaaaniel/my-awesome-eurorack"
SITE_TITLE = "Open-source Eurorack modules"

# ---------------------------------------------------------------- data

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"

def load():
    with open(TSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        for k, v in r.items():
            r[k] = (v or "").strip()
    # slug: creator + module name; append id only on collision
    seen = Counter(slugify(r["creator"] + " " + r["module_name"]) for r in rows)
    for r in rows:
        s = slugify(r["creator"] + " " + r["module_name"])
        r["slug"] = s if seen[s] == 1 else f"{s}-{r['id']}"
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

def load_aliases():
    if not os.path.exists(ALIASES):
        return {}
    with open(ALIASES, newline="", encoding="utf-8") as f:
        return {r["alias"].strip(): r["maker"].strip() for r in csv.DictReader(f, delimiter="\t") if r["alias"].strip()}

MAKER_ALIAS = load_aliases()

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
.layout{display:grid;grid-template-columns:230px 1fr;gap:24px}
@media(max-width:640px){.layout{grid-template-columns:1fr}}
aside{font-size:13px}aside details{border-top:1px solid var(--line);padding:6px 0}
aside summary{cursor:pointer;font-weight:600;padding:4px 0;list-style:none;display:flex;justify-content:space-between}
aside summary::after{content:"▾";color:var(--mute)}details[open]>summary::after{content:"▴"}
aside label{display:flex;gap:6px;align-items:center;padding:2px 0;cursor:pointer}
aside label .n{margin-left:auto;color:var(--mute);font-variant-numeric:tabular-nums}
aside input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);font:inherit;margin-bottom:10px}
.maker-list{max-height:260px;overflow:auto}
.toolbar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-bottom:12px;font-size:13px;color:var(--mute)}
.toolbar select,.toolbar button{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}
.toolbar button[aria-pressed=true]{background:var(--chip-on);color:var(--chip-on-fg);border-color:var(--chip-on)}
.toolbar .clear{margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.card .name{font-weight:650;font-size:15px}.card .name a{text-decoration:none}
.card .maker{color:var(--mute);font-size:13px}
.card .type{font-size:13px;margin:2px 0 6px}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:auto}
.chip{font-size:11px;padding:2px 7px;border-radius:999px;background:var(--chip);color:var(--fg);white-space:nowrap}
.chip.warn{background:var(--acc);color:#fff}.chip.tag{background:transparent;border:1px solid var(--line)}.chip.dim{color:var(--mute)}
table.list{width:100%;border-collapse:collapse;font-size:13px}
table.list th,table.list td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
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
.notice{border-left:3px solid var(--acc);padding:8px 12px;font-size:13px;color:var(--mute);margin:20px 0}
footer{padding:24px 16px;border-top:1px solid var(--line);color:var(--mute);font-size:12.5px;text-align:center}
"""

def page(title, body, rel, desc=""):
    """rel = relative path prefix back to docs/ root ('' or '../../')."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="stylesheet" href="{rel}site.css">
</head><body>
<header class="top"><h1><a href="{rel}">{SITE_TITLE}</a></h1>
<span class="sub">a reference table of buildable DIY modules, every cell traced to a file in its repo</span>
<nav><a href="{rel}about.html">about</a><a href="{REPO_URL}">data on GitHub</a></nav></header>
<div class="wrap">{body}</div>
<footer>Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} from <a href="{REPO_URL}/blob/website/data/modules.tsv">data/modules.tsv</a>.
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

JS = r"""
(function(){
const rows=window.__ROWS__;
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const state={q:"",tags:new Set(),mount:new Set(),files:new Set(),license:new Set(),proto:new Set(),maker:new Set(),view:"grid",sort:"name",dir:"asc"};
// --- read URL
const sp=new URLSearchParams(location.search);
for(const k of ["tags","mount","files","license","proto","maker"]){for(const v of sp.getAll(k))state[k].add(v);}
if(sp.get("q"))state.q=sp.get("q");if(sp.get("view"))state.view=sp.get("view");if(sp.get("sort"))state.sort=sp.get("sort");if(sp.get("dir"))state.dir=sp.get("dir");
function writeURL(){const p=new URLSearchParams();if(state.q)p.set("q",state.q);for(const k of ["tags","mount","files","license","proto","maker"])for(const v of state[k])p.append(k,v);
 if(state.view!=="grid")p.set("view",state.view);if(state.sort!=="name")p.set("sort",state.sort);if(state.dir!=="asc")p.set("dir",state.dir);
 history.replaceState(null,"",location.pathname+(p.toString()?"?"+p:""));}
// --- facets
function facet(name,key,getter){const box=$("#f-"+name);const counts=new Map();
 for(const r of rows){for(const v of getter(r))counts.set(v,(counts.get(v)||0)+1);}
 const vals=[...counts.keys()].sort((a,b)=>name==="maker"?a.localeCompare(b):counts.get(b)-counts.get(a)||a.localeCompare(b));
 box.innerHTML=vals.map(v=>`<label><input type="checkbox" value="${esc(v)}" ${state[key].has(v)?"checked":""}><span>${esc(v)}</span><span class="n">${counts.get(v)}</span></label>`).join("");
 box.addEventListener("change",ev=>{const v=ev.target.value;ev.target.checked?state[key].add(v):state[key].delete(v);render();});}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
const G={tags:r=>r.tags,mount:r=>[r.mount],files:r=>r.files,license:r=>[r.license||"not determined"],proto:r=>[r.proto==="X"?"prototype":r.proto==="?"?"prototype?":"no mark"],maker:r=>r.makers};
if($("#f-tags"))facet("tags","tags",G.tags);facet("mount","mount",G.mount);facet("files","files",G.files);facet("license","license",G.license);facet("proto","proto",G.proto);facet("maker","maker",G.maker);
$("#maker-q").addEventListener("input",ev=>{const q=ev.target.value.toLowerCase();$$("#f-maker label").forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?"":"none");});
// --- filter
function match(r){
 if(state.q){const q=state.q.toLowerCase();if(!(r.name+" "+r.creator+" "+r.type+" "+r.notes+" "+r.license).toLowerCase().includes(q))return false;}
 for(const k of ["tags","mount","files","license","proto","maker"]){if(state[k].size){const vs=G[k](r);if(!vs.some(v=>state[k].has(v)))return false;}}
 return true;}
function sorted(list){const k=state.sort,d=state.dir==="asc"?1:-1;
 const key=r=>k==="name"?r.name.toLowerCase():k==="maker"?r.creator.toLowerCase():k==="date"?r.date:k==="type"?r.type.toLowerCase():k==="mount"?r.mount:r.name.toLowerCase();
 return list.sort((a,b)=>{const x=key(a),y=key(b);return x<y?-d:x>y?d:a.name.localeCompare(b.name);});}
// --- render
function chip(r){let s=r.tags.filter(t=>t!=="not mapped").map(t=>`<span class="chip tag">${esc(t)}</span>`).join("");s+=`<span class="chip${r.components?"":" dim"}">${r.components?esc(r.components):"mounting n/d"}</span>`;
 for(const f of r.files)s+=`<span class="chip">${esc(f)}</span>`;
 if(r.proto==="X")s+='<span class="chip warn">prototype</span>';else if(r.proto==="?")s+='<span class="chip warn">prototype?</span>';return s;}
function card(r){return `<div class="card"><div class="name"><a href="m/${r.slug}/">${esc(r.name)}</a></div><div class="maker">${esc(r.creator)}</div><div class="type">${r.type?esc(r.type):'<span class="nd">type not determined</span>'}</div><div class="chips">${chip(r)}</div></div>`;}
function table(list){const h=[["name","Module"],["maker","Maker"],["type","Type"],["mount","Mounting"],["files","Files"],["license","License"],["date","Date"]];
 return `<table class="list"><thead><tr>${h.map(([k,l])=>`<th data-k="${k}" ${state.sort===k?`data-dir="${state.dir}"`:""}>${l}</th>`).join("")}</tr></thead><tbody>${list.map(r=>`<tr><td><a href="m/${r.slug}/">${esc(r.name)}</a>${r.proto?` <span class="chip warn">${r.proto==="X"?"prototype":"prototype?"}</span>`:""}</td><td>${esc(r.creator)}</td><td>${esc(r.type)}</td><td>${r.components?esc(r.components):'<span class="nd">n/d</span>'}</td><td>${r.files.join(", ")}</td><td>${r.license?esc(r.license):'<span class="nd">n/d</span>'}</td><td class="mute">${esc(r.date)}</td></tr>`).join("")}</tbody></table>`;}
function render(){const list=sorted(rows.filter(match));$("#count").textContent=`${list.length} of ${rows.length} modules`;
 const out=$("#out");out.innerHTML=state.view==="grid"?`<div class="grid">${list.map(card).join("")}</div>`:table(list);
 if(state.view==="table")$$("#out th").forEach(th=>th.addEventListener("click",()=>{const k=th.dataset.k;if(k==="files")return;if(state.sort===k)state.dir=state.dir==="asc"?"desc":"asc";else{state.sort=k;state.dir="asc";}$("#sort").value=state.sort;render();}));
 $$(".toolbar [data-view]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.view===state.view));writeURL();}
$("#q").value=state.q;$("#q").addEventListener("input",ev=>{state.q=ev.target.value.trim();render();});
$("#sort").value=state.sort;$("#sort").addEventListener("change",ev=>{state.sort=ev.target.value;state.dir=ev.target.value==="date"?"desc":"asc";render();});
$$(".toolbar [data-view]").forEach(b=>b.addEventListener("click",()=>{state.view=b.dataset.view;render();}));
$("#clear").addEventListener("click",()=>{state.q="";for(const k of ["tags","mount","files","license","proto","maker"])state[k].clear();$("#q").value="";$$("aside input[type=checkbox]").forEach(c=>c.checked=false);render();});
if(matchMedia("(max-width:640px)").matches)$$("aside details").forEach(d=>d.open=false);
if(matchMedia("(max-width:640px)").matches)$$("aside details").forEach(d=>d.open=false);
render();
})();
"""

def build_index(rows, typemap):
    data = [dict(tags=tags_of(r, typemap), makers=makers_of(r),
        id=r["id"], slug=r["slug"], name=r["module_name"], creator=r["creator"], type=r["type"],
        license=r["license"], components=r["components"], mount=bucket_components(r["components"]),
        files=files_of(r), proto=r["prototype"], date=r["date"], notes=r["notes"],
    ) for r in rows]
    def facet(name, label, extra=""):
        return f'<details open><summary>{label}</summary>{extra}<div id="f-{name}" class="{"maker-list" if name=="maker" else ""}"></div></details>'
    aside = (
        '<input id="q" type="search" placeholder="Search name, maker, type, notes…" aria-label="Search">'
        + (facet("tags", "Type <span class=\"mute\" style=\"font-weight:400\">(draft tags)</span>") if typemap else "")
        + facet("mount", "Mounting")
        + facet("files", "Files in repo")
        + facet("proto", "Build status")
        + facet("license", "License (as recorded)")
        + facet("maker", "Maker", '<input id="maker-q" type="search" placeholder="filter makers" aria-label="Filter makers">')
    )
    body = f"""<div class="layout"><aside>{aside}</aside><main>
<div class="toolbar"><span id="count"></span>
<label>sort <select id="sort"><option value="name">name</option><option value="maker">maker</option><option value="type">type</option><option value="mount">mounting</option><option value="date">date (newest)</option></select></label>
<span><button data-view="grid" aria-pressed="true">grid</button> <button data-view="table">table</button></span>
<button id="clear" class="clear">clear filters</button></div>
<div id="out"></div></main></div>
<script>window.__ROWS__={json.dumps(data, ensure_ascii=False, separators=(",", ":"))};</script>
<script src="site.js"></script>"""
    return page(SITE_TITLE, body, "", f"{len(rows)} buildable open-source Eurorack modules, filterable by mounting, files, license and maker.")

# ---------------------------------------------------------------- detail

BASIS = [("comp_basis", "Components (mounting)"), ("type_basis", "Type"),
         ("creator_basis", "Creator"), ("license_basis", "License"), ("prototype_basis", "Prototype mark")]

def mini(r):
    return f'<div class="card"><div class="name"><a href="../{r["slug"]}/">{e(r["module_name"])}</a></div><div class="maker">{e(r["creator"])}</div><div class="type small">{nd(r["type"], "type not determined")}</div><div class="chips">{chips(r)}</div></div>'

def build_detail(r, by_maker, typemap):
    tags = [t for t in tags_of(r, typemap) if t != "not mapped"]
    title = f"{r['module_name']} — {r['creator']}"
    spec = [
        ("Maker", e(r["creator"])),
        ("Type", nd(r["type"]) + (f' <span class="mute small">· tags (draft): {e(", ".join(tags))}</span>' if tags else "")),
        ("Mounting", nd(r["components"])),
        ("Component confidence", (e(r["comp_conf"]) if r["comp_conf"] else nd(""))),
        ("Layout files", nd(r["layout"])),
        ("Schematic", link_or_text(r["schematic"]) if r["schematic"] != "x" else "present in repo"),
        ("BOM", "machine-readable BOM in repo" if r["bom"] == "y" else nd("none found" if r["bom"] == "-" else "")),
        ("License", nd(r["license"])),
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
    notes = f'<div class="box"><h2>Notes</h2>{e(r["notes"])}</div>' if r["notes"] else ""
    follow = f'<div class="box"><h2>Open follow-up</h2>{e(r["followup"])}</div>' if r["followup"] else ""
    more = ""
    for m in makers_of(r):
        others = [o for o in by_maker[m] if o["id"] != r["id"]]
        if not others:
            continue
        more += f'<h2 class="small mute" style="margin-top:28px">More by {e(m)} ({len(others)})</h2><div class="more">{"".join(mini(o) for o in others[:12])}</div>'
        if len(others) > 12:
            more += f'<p class="small"><a href="../../?maker={e(m)}">all {len(others)+1} by {e(m)}</a></p>'
    body = f"""<div class="detail"><p class="small"><a href="../../">← all modules</a></p>
<h1>{e(r["module_name"])}</h1><div class="maker">{" + ".join(f'<a href="../../?maker={e(m)}">{e(m)}</a>' for m in makers_of(r))}</div>
<div class="cols"><div><dl class="spec">{dl}</dl>{notes}{follow}{ev_box}</div>
<div><div class="box"><h2>Files &amp; links</h2><ul>{"".join(links)}</ul></div>
<div class="box"><h2>Record</h2>row <code>{e(r["id"])}</code> · detector v{e(r["detector_version"])} · <a href="{REPO_URL}/blob/website/data/modules.tsv">data/modules.tsv</a><br>
<span class="mute small">Blank cells are blank on purpose: the repo didn't state it, so we don't either.</span></div></div></div>
<div class="notice">This is a third-party design. Check the repository (and its licence) before ordering parts or selling boards.</div>
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
<dt>Files in repo</dt><dd>Which design files exist: a schematic (linked when it's a single PDF), KiCad / Eagle / other layout sources, gerbers, a machine-readable BOM.</dd>
<dt>License</dt><dd>Exactly as the repository states it. Not normalised (yet), so "CC BY-SA" and "CC BY-SA 4.0" are separate values.</dd>
<dt>Build status</dt><dd><b>prototype</b> when the repo clearly labels the build untested or in progress; <b>prototype?</b> when the wording is ambiguous. Never inferred from a version number.</dd>
<dt>Evidence</dt><dd>Each module page quotes the file path or README line every non-blank cell came from.</dd>
</dl>
<h2>Rules the data follows</h2>
<ul><li>Never invent a value. A blank cell is correct; a plausible guess would be acted on when ordering parts.</li>
<li>Every non-blank cell traces to a file path in the repository tree or a quoted line of text.</li>
<li>One row per buildable module variant, not per repository.</li></ul>
<p class="small mute">Modelled loosely on <a href="https://signalfunctionset.com/builds/">signalfunctionset.com/builds</a>, whose catalogue is curated by hand; this one is extracted from the repos and shows its working.</p></div>"""
    return page("About — " + SITE_TITLE, body, "", "How the module table is built and what its fields mean.")

# ---------------------------------------------------------------- main

def main():
    rows = load()
    typemap = load_typemap()
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
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f: f.write(build_index(rows, typemap))
    with open(os.path.join(OUT, "about.html"), "w", encoding="utf-8") as f: f.write(build_about(rows))
    for r in rows:
        d = os.path.join(OUT, "m", r["slug"]); os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f: f.write(build_detail(r, by_maker, typemap))
    print(f"wrote {len(rows)} module pages + index/about to {os.path.relpath(OUT, ROOT)}/")

if __name__ == "__main__":
    main()
