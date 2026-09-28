#!/usr/bin/env node
// Render every module page to plain HTML with Node, no browser (branch website-js).
//
//   node site/render_pages.js [--out DIR] [--compare OLD_DOCS_DIR]
//
// Reads docs/m/<slug>.html (stub + inline JSON) and docs/cards.json, renders each page with the same
// docs/module.js the browser runs. --out writes the rendered pages to DIR/<slug>.html, for grep-style checks
// across all pages. --compare checks each rendered page against a static page from before the JS rewrite
// (a docs/ tree of the `website` branch, where pages were m/<slug>/index.html): title, description and the page
// body must match, apart from the script tags the static pages carried inline and the move from m/<slug>/ to
// m/<slug>.html (links one level shallower, sibling links end in .html).
const fs = require("fs"), path = require("path");
const args = process.argv.slice(2), opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const DOCS = path.join(__dirname, "..", "docs");
const M = require(path.join(DOCS, "module.js"));
const cards = JSON.parse(fs.readFileSync(path.join(DOCS, "cards.json"), "utf8"));
const out = opt("--out"), old = opt("--compare");
if (out) fs.mkdirSync(out, { recursive: true });

const between = (s, a, b) => { const i = s.indexOf(a); if (i < 0) return null; const j = s.indexOf(b, i + a.length); return j < 0 ? null : s.slice(i + a.length, j); };
const meta = (s, name) => (s.match(new RegExp(`<meta name="${name}" content="([^"]*)">`)) || [])[1];
// The photo box was redesigned on this branch (gallery, d 04:28): pages with photos are compared without it (it is
// checked in a browser instead). Panel-drawing boxes are still compared.
const dropPhotos = s => {
  const i = s.indexOf('<div class="box" id="photos"><h2>Photos ');
  if (i < 0) return s;
  const re = /<div\b|<\/div>/g; re.lastIndex = i; let depth = 0, m;
  while ((m = re.exec(s))) { depth += m[0] === "</div>" ? -1 : 1; if (!depth) return s.slice(0, i) + s.slice(re.lastIndex); }
  return s;
};
const normOld = s => s
  .replace(/<script type="module" src="\.\.\/\.\.\/(schem|stl)\.js\?v=\w+"><\/script>/g, "")
  .replace(/<noscript><p class="pdfstatus">[^<]*<\/p><\/noscript>/g, "")
  .replace(/href="\.\.\/\.\.\//g, 'href="../').replace(/href="\.\.\/([a-z0-9-]+)\/"/g, 'href="$1.html"');

let n = 0, bad = 0, missing = 0;
const diffs = [];
for (const name of fs.readdirSync(path.join(DOCS, "m")).sort()) {
  if (!name.endsWith(".html")) continue;
  const slug = name.slice(0, -5), f = path.join(DOCS, "m", name);
  if (!fs.existsSync(f)) continue;
  const stub = fs.readFileSync(f, "utf8");
  const json = between(stub, '<script type="application/json" id="module-data">', "</script>");
  if (json == null) { console.error("no module data:", slug); bad++; continue; }
  const d = JSON.parse(json);
  n++;
  if (out) {
    const head = stub.slice(0, stub.indexOf("<body>") + 6);
    fs.writeFileSync(path.join(out, slug + ".html"), head + "\n" + M.page(d, cards) + "\n</body></html>\n");
  }
  if (old) {
    const of = path.join(old, "m", slug, "index.html");
    if (!fs.existsSync(of)) { missing++; continue; }
    const o = fs.readFileSync(of, "utf8");
    const checks = [
      ["title", between(o, "<title>", "</title>"), between(stub, "<title>", "</title>")],
      ["description", meta(o, "description"), meta(stub, "description")],
      ["body", dropPhotos(normOld(between(o, '<div class="wrap">', "</div>\n<footer>") || "")), dropPhotos(M.body(d, cards))],
    ];
    for (const [what, a, b] of checks) if (a !== b) {
      bad++;
      let i = 0; while (i < a.length && a[i] === b[i]) i++;
      diffs.push(`${slug} ${what} @${i}\n  old: ${JSON.stringify(a.slice(Math.max(0, i - 60), i + 100))}\n  new: ${JSON.stringify((b || "").slice(Math.max(0, i - 60), i + 100))}`);
      break;
    }
  }
}
console.log(`${n} pages rendered` + (out ? ` to ${out}` : "") + (old ? `; ${n - bad - missing} identical to the static pages, ${bad} differ, ${missing} have no static page` : ""));
if (diffs.length) console.log(diffs.slice(0, 15).join("\n"));
process.exit(bad ? 1 : 0);
