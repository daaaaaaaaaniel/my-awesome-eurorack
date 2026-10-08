#!/usr/bin/env python3
"""Smell-test page for data/readme-links.tsv (+ cart lines of data/bom-links.tsv): one card per module, links grouped
as a module page could show them. <span class=tag>collection</span> = the link's README covers several rows.
  python3 data/readme_links_preview.py > readme-links-preview.html"""
import csv, html, collections, os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); csv.field_size_limit(10 ** 9); e = html.escape
M = {x["id"]: x for x in csv.DictReader(open(os.path.join(here, "modules.tsv"), newline="", encoding="utf-8"), delimiter="\t")}
R = list(csv.DictReader(open(os.path.join(here, "readme-links.tsv"), newline="", encoding="utf-8"), delimiter="\t"))
by = collections.defaultdict(list)
for r in R:
    ids = r["ids"].split(",")
    for i in ids: by[i].append((r, len(ids) > 1))
for l in open(os.path.join(here, "bom-links.tsv"), encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) == 4 and re.search("cart", f[2], re.I):
        by[f[0]].append(({"kind": "cart", "url": f[1], "domain": f[2], "link_text": "", "context": f[3]}, False))
GROUPS = [("Buy", ("shop", "shop-?")), ("Carts (BOM)", ("cart",)), ("Video", ("video",)), ("Community", ("community",)),
          ("Maker site / docs / audio", ("site", "docs", "audio")), ("PCB fab", ("fab",))]
css = """:root{--bg:#fff;--fg:#1c1c1e;--mut:#6b6b70;--line:#e3e3e6;--card:#fafafa;--acc:#0a58ca;--tag:#eef2f7;--warn:#8a5a00}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141416;--fg:#e9e9eb;--mut:#9a9aa1;--line:#2c2c30;--card:#1b1b1e;--acc:#7ab0ff;--tag:#23262d;--warn:#e0b050}}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;padding:16px;max-width:1100px;margin:auto}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}h1{font-size:21px;margin:4px 0}.m{color:var(--mut)}
input{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);font-size:14px;margin:10px 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}.card{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--card)}
.card h2{font-size:15px;margin:0 0 2px}.who{color:var(--mut);font-size:12px;margin-bottom:6px}.g{margin-top:6px}.g b{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
ul{margin:2px 0 0;padding-left:16px}li{margin:1px 0;overflow-wrap:anywhere}.tag{font-size:11px;background:var(--tag);border-radius:4px;padding:0 5px;margin-left:4px;color:var(--mut)}.q{color:var(--warn)}.stats span{margin-right:12px}"""
kc = collections.Counter(r["kind"] for r in R); ids = sorted(by, key=lambda i: int(i[1:]))
out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>README links preview</title><style>{css}</style></head><body>",
       "<h1>README links: module-page preview</h1>",
       f"<p class=m>Smell test for data/readme-links.tsv ({len(R)} links) + the cart lines of data/bom-links.tsv. <span class=tag>collection</span> = from a README shared by several rows. Hover a link for the sentence around it.</p>",
       "<p class='m stats'>" + " ".join(f"<span>{k}: {v}</span>" for k, v in kc.most_common()) + f"<span>modules: {len(ids)}</span></p>",
       "<input id=q placeholder='Filter: module, maker, domain, id (e.g. tindie, p406, Winterbloom)'>", "<div class=grid>"]
for i in ids:
    m = M.get(i)
    if not m: continue
    parts = []
    for title, kinds in GROUPS:
        li = []; seen = set()
        for r, coll in by[i]:
            if r["kind"] not in kinds or r["url"] in seen: continue
            seen.add(r["url"])
            label = re.sub(r"<[^>]+>", "", r.get("link_text") or "").strip() or r["domain"]
            extra = (" <span class=tag>collection</span>" if coll else "") + (" <span class='tag q'>shop-?</span>" if r["kind"] == "shop-?" else "") + (f" <span class=tag>{e(r['kind'])}</span>" if r["kind"] in ("site", "docs", "audio") else "")
            li.append(f"<li><a href='{e(r['url'])}' title='{e((r.get('context') or '')[:300])}'>{e(label[:80])}</a> <span class=m>· {e(r['domain'])}</span>{extra}</li>")
        if li: parts.append(f"<div class=g><b>{title}</b><ul>{''.join(li)}</ul></div>")
    if not parts: continue
    key = f"{i} {m['module_name']} {m['creator']} {m['repo']} " + " ".join(r["domain"] for r, _ in by[i])
    out.append(f"<div class=card data-k='{e(key.lower())}'><h2>{e(m['module_name'])} <span class=m style='font-weight:normal;font-size:12px'>{i}</span></h2><div class=who>{e(m['creator'])} · <a href='https://github.com/{e(m['repo'])}'>{e(m['repo'])}</a></div>{''.join(parts)}</div>")
out.append("</div><script>const q=document.getElementById('q');q.oninput=()=>{const v=q.value.toLowerCase().trim();for(const c of document.querySelectorAll('.card'))c.style.display=!v||c.dataset.k.includes(v)?'':'none'}</script></body></html>")
sys.stdout.write("\n".join(out))
