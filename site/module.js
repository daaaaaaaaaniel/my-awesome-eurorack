// Module page renderer (branch website-js, 2026-09-28).
// Each docs/m/<slug>.html carries its module's record as JSON in <script id="module-data">; this file turns it
// into the page. Python (site/build.py) decides WHAT is shown; this file decides HOW. Everything below is plain
// functions from data to HTML strings, so Node can render every page without a browser (site/render_pages.js).
// `SITE` (title, repo URL, asset versions) is prepended by build.py when it writes docs/module.js.
(function () {
"use strict";
const S = typeof SITE !== "undefined" ? SITE
  : { title: "Open-source Eurorack modules", repo: "https://github.com/daaaaaaaaaniel/my-awesome-eurorack", three: "0.170.0", schem: "", stl: "" };
const TSV = S.repo + "/blob/website/data/modules.tsv";

// ---- helpers (each mirrors the Python it replaced, so output matches the static pages)
const e = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");                                   // html.escape
const nd = (s, fb = "not determined") => s ? e(s) : `<span class="nd">${fb}</span>`;
const quote = (s, safe = "/") => {                                                      // urllib.parse.quote
  let q = encodeURIComponent(s).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
  return safe.includes("/") ? q.replace(/%2F/g, "/") : q;
};
const unquote = s => s.replace(/(%[0-9A-Fa-f]{2})+/g, m => { try { return decodeURIComponent(m); } catch { return m; } });
const basename = p => p.slice(p.lastIndexOf("/") + 1);
const dirname = p => p.includes("/") ? p.slice(0, p.lastIndexOf("/")) : "";
const isUrl = s => /^https?:\/\//.test(s || "");
const shortUrl = (s, n = 70) => { s = s.replace(/^https?:\/\/(www\.)?/, ""); const a = [...s]; return a.length < n ? s : a.slice(0, n - 3).join("") + "…"; };
const schemName = u => basename(u.split("?")[0]) || u;
const linkName = u => unquote(u.replace(/\/+$/, "").split("/").pop());
const ghBlob = (d, p) => `https://github.com/${d.repo}/blob/${d.branch}/${quote(p)}`;
const makerHref = (m, prefix = "") => `${prefix}?maker=${quote(m, "")}`;
const MUTE_H2 = '<span class="mute" style="text-transform:none;letter-spacing:0">';
const ONERR = `onerror="this.parentNode.classList.add('broken');this.replaceWith(document.createTextNode(this.alt))"`;

// thumbnails resized on request by wsrv.nl from the raw GitHub file; SVG panel drawings get their blank page trimmed
function thumb(u, w = 400, h = 360, dpr = 1) {
  const raw = u.replace(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\//, "https://raw.githubusercontent.com/$1/$2/");
  const svg = raw.toLowerCase().endsWith(".svg");
  return `https://wsrv.nl/?url=${quote(raw, "")}${svg ? "&trim=10" : ""}&w=${w}&h=${h}&fit=inside${svg ? "" : "&we"}&output=webp&q=78` + (dpr > 1 ? `&dpr=${dpr}` : "");
}
const thumbImg = u => { const n = linkName(u);
  return `<a class="thumb" href="${e(u)}" title="${e(n)}"><img loading="lazy" decoding="async" alt="${e(n)}" src="${e(thumb(u))}" srcset="${e(thumb(u))} 1x, ${e(thumb(u, 400, 360, 2))} 2x" ${ONERR}></a>`; };

// ---- spec cells
function hpCell(d) {
  const t = d.hp || "", why = d.hp_why || "";
  if (t && t !== "?") {
    const how = why.replace(/^measured ([\d.]+) x ([\d.]+) mm outline in (.*?)(;.*)?$/, "measured from the panel outline ($1 × $2 mm, $3)$4");
    return `<b>${e(t)}</b>` + (how ? ` <span class="mute small">· ${e(how)}</span>` : "");
  }
  if (t === "?") return nd("not determined") + (why ? ` <span class="mute small">· ${e(why)}</span>` : "");
  return nd("no panel files found");
}

const LAYER = /\.(gbr|gtl|gbl|gts|gbs|gto|gbo|gtp|gbp|gko|gm\d*|gml|drl|xln|txt)$/i;
function panelCell(d) {
  const src = d.panel_src || [];
  if (!src.length) return nd("none found");
  const files = d.panel_files || [], n = d.panel_n || 0;
  let out = e(src.join(" · "));
  if (files.length) {
    // design files first; individual gerber layers collapse into one link per folder
    const items = [], folders = new Map();
    for (const f of files) {
      if (LAYER.test(f)) { const k = dirname(f); if (!folders.has(k)) folders.set(k, []); folders.get(k).push(f); }
      else items.push(`<a href="${e(ghBlob(d, f))}" class="small">${e(f)}</a>`);
    }
    for (const [k, fs] of folders) {
      if (fs.length === 1) items.push(`<a href="${e(ghBlob(d, fs[0]))}" class="small">${e(fs[0])}</a>`);
      else {
        const u = k ? `https://github.com/${d.repo}/tree/${d.branch}/${quote(k)}` : d.link;
        items.push(`<a href="${e(u)}" class="small">${e(k || "(repo root)")}/</a> <span class="mute small">${fs.length} gerber layers</span>`);
      }
    }
    out += "<br>" + items.slice(0, 8).join("<br>");
    if (items.length > 8 || n > files.length) {
      const more = (items.length > 8 ? items.length - 8 : 0) + (n - files.length);
      out += `<br><span class="mute small">+${more} more in the <a href="${e(d.link)}">source folder</a></span>`;
    }
  }
  return out;
}

function partsCell(c) {
  if (!c) return nd("not counted (no board file or machine-readable BOM in scope)");
  const hasPanel = c.panel != null;
  return `<b>${c.total}</b> footprints — `
    + (hasPanel ? `${c.panel} panel parts (jacks, pots, switches, LEDs, headers) + ${c.board} on the board: ` : "")
    + `SMD ${c.smd} (+${c.smd_ic} ICs), THT ${c.tht} (+${c.tht_ic} ICs, +${c.tht_to} TO-92/220)`
    + ' <span class="mute small">· ' + (hasPanel ? "panel parts included" : "panel hardware not counted")
    + (c.files > 1 ? ` · summed over ${c.files} board files in the folder, so variants may be pooled` : "") + "</span>";
}

const BOM_ORDER = ["iBOM", "CSV", "TSV", "XLSX", "XLS", "ODS", "PDF", "MD", "TXT"];
function bomLabel(p) {
  const b = basename(p).toLowerCase();
  if (b.includes("ibom") || b.endsWith(".html") || b.endsWith(".htm")) return "iBOM";
  const i = b.lastIndexOf(".");
  return i > 0 ? b.slice(i + 1).toUpperCase() : "";
}
// an iBOM opens rendered via htmlpreview (GitHub shows HTML as source); page=false gives the GitHub file page
const bomUrl = (d, p, page = true) => (page && bomLabel(p) === "iBOM" ? "https://htmlpreview.github.io/?" : "") + ghBlob(d, p);
function bomCell(d) {
  const extra = (d.bom_extra || []).map(([lab, u, n]) => `<a href="${e(u)}">${e(lab)}</a> <span class="mute small">${e(n)}</span>`);
  let files = d.bom_files || [];
  if (extra.length && !files.length) return extra.join("<br>");
  if (!files.length) return d.bom === "y" ? "machine-readable BOM in repo" : nd(d.bom === "-" ? "none found" : "");
  const rank = p => { const i = BOM_ORDER.indexOf(bomLabel(p)); return i < 0 ? 99 : i; };
  const cmp = (a, b) => a < b ? -1 : a > b ? 1 : 0;
  files = [...files].sort((a, b) => rank(a) - rank(b) || cmp(a.toLowerCase(), b.toLowerCase()));
  const dir = d.dir || "";
  const rel = p => dir !== "." && p.startsWith(dir + "/") ? p.slice(dir.length + 1) : p;
  const src = p => bomLabel(p) === "iBOM" ? ` <a class="small" href="${e(bomUrl(d, p, false))}" title="GitHub file page (HTML source)">source</a>` : "";
  const lines = files.slice(0, 10).map(p => `<a href="${e(bomUrl(d, p))}" title="${e(p)}">${e(bomLabel(p))}</a>${src(p)} <span class="mute small">${e(rel(p))}</span>`);
  lines.push(...extra);
  if (files.length > 10) lines.push(`<span class="mute small">+${files.length - 10} more in the <a href="${e(d.link)}">source folder</a></span>`);
  return lines.join("<br>");
}

const linkOrText = s => isUrl(s) ? `<a href="${e(s)}">${e(shortUrl(s))}</a>` : nd(s);

// ---- boxes
function licBox(d) {
  const gs = d.grants || [];
  if (!gs.length) return "";
  const trs = gs.map(g => `<tr><td>${e(g.scope)}</td><td>${e(g.lic)}</td><td>${e(g.terms)}</td><td class="mute">${e(g.note)}${g.source ? " <b>source: " + e(g.source) + "</b>" : ""}</td></tr>`).join("");
  const draft = d.grants_draft ? ' <span style="text-transform:none;letter-spacing:0">(draft categorisation)</span>' : "";
  return `<div class="box"><h2>License${draft}</h2><table class="grants"><tr><th>covers</th><th>license</th><th>terms</th><th></th></tr>${trs}</table><p class="small mute" style="margin:8px 0 0">Terms describe the license family, not this repository. Check the repository before relying on any of it.</p></div>`;
}

const BASIS = [["comp_basis", "Components (mounting)"], ["type_basis", "Type"], ["creator_basis", "Creator"],
  ["license_basis", "License"], ["prototype_basis", "Prototype mark"], ["panel_basis", "Panel / HP"],
  ["photos_basis", "Photos"], ["build_basis", "Build guide"]];
function evidenceBox(d) {
  const b = d.basis || {};
  const ev = BASIS.filter(([k]) => b[k]).map(([k, lab]) => `<dt>${lab}</dt><dd>${e(b[k])}</dd>`).join("");
  const evBox = ev ? `<div class="ev"><h2>Evidence — why the cells say what they say</h2><dl>${ev}</dl></div>` : "";
  const follow = d.followup ? `<div class="fu"><h2>Open follow-up</h2>${e(d.followup)}</div>` : "";
  if (!follow && !evBox) return "";
  // d, 2026-09-28 01:52: evidence and open follow-up sit in one collapsible block, closed by default
  const label = follow && evBox ? "Evidence and open follow-up" : evBox ? "Evidence" : "Open follow-up";
  return `<details class="box evbox"><summary><span>${label}</span><span class="mute small">why the cells say what they say</span></summary>${follow}${evBox}</details>`;
}

function foldList(items, fold = 12) {
  let body = `<ul class="links">${items.slice(0, fold).join("")}</ul>`;
  if (items.length > fold) body += `<details><summary class="small">all ${items.length}</summary><ul class="links">${items.slice(fold).join("")}</ul></details>`;
  return body;
}

function photoBox(d) {
  const urls = d.photos || [];
  if (urls.length) {
    const main = d.photo, rest = urls.filter(u => u !== main);
    let more = "";
    if (rest.length) more = `<p class="small mute" style="margin:10px 0 4px">Other photos (${rest.length})</p>`
      + foldList(rest.map(u => `<li><a href="${e(u)}">${e(linkName(u))}</a></li>`));
    return `<div class="box" id="photos"><h2>Photos ${MUTE_H2}(${urls.length})</span></h2>${thumbImg(main)}<p class="small mute" style="margin:4px 0 0">${e(linkName(main))} · thumbnail via wsrv.nl, click for the original</p>${more}</div>`;
  }
  if (d.drawing) return `<div class="box" id="photos"><h2>Panel drawing</h2>${thumbImg(d.drawing)}<p class="small mute" style="margin:4px 0 0">${e(linkName(d.drawing))} · no photo in the repo, so the panel drawing is shown</p></div>`;
  return "";
}

function stlBox(d) {
  const fs = d.stl || [];
  if (!fs.length) return "";
  const btns = fs.map(f => { const u = ghBlob(d, f), n = linkName(u), p = quote(f);
    return `<button type="button" class="stlbtn" data-name="${e(n)}" data-href="${e(u)}" data-raw="${e(`https://raw.githubusercontent.com/${d.repo}/${d.branch}/${p}`)}" data-media="${e(`https://media.githubusercontent.com/media/${d.repo}/${d.branch}/${p}`)}">View in 3D: ${e(n)}</button>`; }).join("");
  return `<div class="box stl" id="stl"><h2>3D model</h2>${btns}<p class="stlstatus small mute"></p><div class="stlview" hidden></div><p class="stlhint small mute" hidden>drag to rotate · scroll or pinch to zoom · right-drag to pan</p></div>`;
}

function buildBox(d) {
  const urls = d.build || [];
  if (!urls.length) return "";
  const li = u => `<li>${u.includes("/tree/") ? `<a href="${e(u)}">${e(linkName(u))}/</a> <span class="mute small">folder of build-step photos</span>` : `<a href="${e(u)}">${e(linkName(u))}</a>`}</li>`;
  return `<div class="box"><h2>Build guide ${MUTE_H2}(${urls.length})</span></h2>${foldList(urls.map(li))}</div>`;
}

// GitHub blob URL -> the raw file (CORS *, so schem.js can fetch a PDF); only PDFs and images are shown inline
function schemRaw(u) {
  const m = /^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\/(.+)$/.exec(u || "");
  if (!m) return [null, null];
  const p = m[3].toLowerCase();
  const kind = p.endsWith(".pdf") ? "pdf" : [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"].some(x => p.endsWith(x)) ? "img" : null;
  return kind ? [`https://raw.githubusercontent.com/${m[1]}/${m[2]}/${m[3]}`, kind] : [null, null];
}
function schemBox(d) {
  const u = d.schematic || "", [raw, kind] = schemRaw(u);
  if (!raw) return "";
  const head = `<div class="box schem" id="schematic"><h2>Schematic</h2><p class="url small"><a href="${e(u)}">${e(u)}</a></p>`;
  if (kind === "img") return head + `<div class="view"><a href="${e(u)}"><img src="${e(raw)}" loading="lazy" alt="Schematic: ${e(schemName(u))}"></a></div></div>`;
  return head + `<div class="view pdfview" data-src="${e(raw)}" data-href="${e(u)}"><p class="pdfstatus">Loading PDF…</p></div></div>`;
}

// ---- "More by <maker>": cards = docs/cards.json, already sorted by name
function chips(c) {
  let s = `<span class="chip${c.k ? "" : " dim"}">${c.k ? e(c.k) : "mounting n/d"}</span>`;
  for (const f of c.f || []) s += `<span class="chip">${e(f)}</span>`;
  if (c.p === "X") s += '<span class="chip warn">prototype</span>';
  else if (c.p === "?") s += '<span class="chip warn">prototype?</span>';
  return s;
}
const mini = c => `<div class="card"><div class="name"><a href="${c.s}.html">${e(c.n)}</a></div><div class="maker">${e(c.c)}</div><div class="type small">${nd(c.t, "type not determined")}</div><div class="chips">${chips(c)}</div></div>`;
function moreBy(d, cards) {
  let out = "";
  for (const m of d.makers || []) {
    const others = cards.filter(c => c.i !== d.id && (c.m || []).includes(m));
    if (!others.length) continue;
    out += `<h2 class="small mute" style="margin-top:28px">More by ${e(m)} (${others.length})</h2><div class="more">${others.slice(0, 12).map(mini).join("")}</div>`;
    if (others.length > 12) out += `<p class="small"><a href="${e(makerHref(m, "../"))}">all ${others.length + 1} by ${e(m)}</a></p>`;
  }
  return out;
}

// ---- the page
function spec(d) {
  const tags = d.tags || [];
  const rows = [
    ["Maker", e(d.creator)],
    ["Type", nd(d.type) + (tags.length ? ` <span class="mute small">· tags (draft): ${e(tags.join(", "))}</span>` : "")],
    ["Mounting", nd(d.components)],
    ["HP", hpCell(d)],
    ["Panel files", panelCell(d)],
    ["Component confidence", d.comp_conf ? e(d.comp_conf) : nd("")],
    ["Board parts", partsCell(d.counts)],
    ["Layout files", nd(d.layout)],
    ["Schematic", d.schematic !== "x" ? linkOrText(d.schematic || "") : "present in repo"],
    ["BOM", bomCell(d)],
    ["License (as recorded)", nd(d.license, "blank — no LICENSE file or README statement found in the files checked")],
    ["Build status", { X: '<span class="chip warn">prototype</span> — repo labels it a prototype / untested',
                       "?": '<span class="chip warn">prototype?</span> — wording is ambiguous' }[d.prototype] || "no prototype mark"],
    ["Last commit seen", nd(d.date)],
  ];
  return rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
}

function links(d) {
  const out = [`<li>Source: <a href="${e(d.link)}">${e(shortUrl(d.link || "", 90))}</a></li>`];
  if (isUrl(d.schematic)) out.push(`<li>Schematic: <a href="${e(d.schematic)}">${e(schemName(d.schematic))}</a></li>`);
  out.push(`<li>Repository: <a href="https://github.com/${e(d.repo)}">${e(d.repo)}</a> at <code>${e(d.sha)}</code>`
    + (d.dir ? ` (folder <code>${e(d.dir)}</code>)` : "") + "</li>");
  return out.join("");
}

// cards: the parsed cards.json, or null to leave a placeholder that the browser fills once it has loaded
function body(d, cards) {
  const notes = d.notes ? `<div class="box"><h2>Notes</h2>${e(d.notes)}</div>` : "";
  return `<div class="detail"><p class="small"><a href="../">← all modules</a></p>
<h1>${e(d.name)}</h1><div class="maker">${(d.makers || []).map(m => `<a href="${e(makerHref(m, "../"))}">${e(m)}</a>`).join(" + ")}</div>
<div class="cols"><div><dl class="spec">${spec(d)}</dl>${licBox(d)}${notes}${evidenceBox(d)}</div>
<div><div class="box"><h2>Files &amp; links</h2><ul>${links(d)}</ul></div>
${photoBox(d)}${stlBox(d)}${buildBox(d)}
<div class="box"><h2>Record</h2>row <code>${e(d.id)}</code> · detector v${e(d.detector)} · <a href="${TSV}">data/modules.tsv</a><br>
<span class="mute small">Blank cells are blank on purpose: the repo didn't state it, so we don't either.</span></div></div></div>
${schemBox(d)}
<div class="notice">This is a third-party design. Check the repository (and its license) before ordering parts or selling boards.</div>
${cards ? moreBy(d, cards) : '<div id="more"></div>'}</div>`;
}

const header = () => `<header class="top"><h1><a href="../">${e(S.title)}</a></h1>
<span class="sub">a reference table of buildable DIY modules, every cell traced to a file in its repo</span>
<nav><a href="../about.html">about</a><a href="${S.repo}">data on GitHub</a></nav></header>`;
const footer = () => `<footer>Generated from <a href="${TSV}">data/modules.tsv</a>.
Third-party designs: check the source repository before ordering parts.</footer>`;
const page = (d, cards) => `${header()}\n<div class="wrap">${body(d, cards)}</div>\n${footer()}`;

const api = { page, body, moreBy };
if (typeof module !== "undefined" && module.exports) { module.exports = api; return; }   // Node: render_pages.js

// ---- browser
const el = document.getElementById("module-data");
if (!el) return;
const d = JSON.parse(el.textContent);
document.body.insertAdjacentHTML("afterbegin", page(d, null));
const add = (tag, attrs, text) => { const s = document.createElement(tag); Object.assign(s, attrs); if (text) s.textContent = text; document.head.appendChild(s); };
// the import map must be in place before the first module script loads
if ((d.stl || []).length) add("script", { type: "importmap" }, JSON.stringify({ imports: {
  three: `https://cdn.jsdelivr.net/npm/three@${S.three}/build/three.module.min.js`,
  "three/addons/": `https://cdn.jsdelivr.net/npm/three@${S.three}/examples/jsm/` } }));
if (document.querySelector(".pdfview")) add("script", { type: "module", src: `../schem.js?v=${S.schem}` });
if (document.querySelector(".stl")) add("script", { type: "module", src: `../stl.js?v=${S.stl}` });
if ((d.makers || []).length) fetch("../cards.json").then(r => r.ok ? r.json() : Promise.reject(r.status))
  .then(cards => { const box = document.getElementById("more"); if (box) box.outerHTML = moreBy(d, cards); })
  .catch(err => console.error("cards.json:", err));
})();
