// KiCanvas viewer regression test (d, 2026-09-28). Run after ANY change to site/kicanvas/kicanvas.js or kc-embed.js.
//
//   python3 site/build.py                       # docs/ must be current
//   NODE_PATH=$(npm root -g) node site/kicanvas/test/viewer.test.js                 # the fixed cases below
//   NODE_PATH=$(npm root -g) node site/kicanvas/test/viewer.test.js --sample 30     # + 30 random viewer pages
//   NODE_PATH=$(npm root -g) node site/kicanvas/test/viewer.test.js slug1 slug2     # just these module pages
//
// Needs Playwright with Chromium (npm i -g playwright; npx playwright install chromium) and network access to
// raw.githubusercontent.com. Pages are served from docs/ through a fake host, so nothing is deployed.
// Google Fonts / CDNs are blocked on purpose: KiCanvas icons then show as words, which is fine.
// Screenshots go to site/kicanvas/test/out/ (git-ignored). Exit code 1 if any check fails.
//
// What a pass means: the viewer loads, opens on a schematic when there is one, every file link switches the
// main pane to the right kind of view (schematic / board) and highlights the link, the page does not navigate
// away, a missing file (forced 404) is struck out while the rest still load, and a download that fails once
// (network hiccup; it crashes KiCanvas) leads to a "Try again" button that then works.
// One-off failures on real pages can be network flakiness: rerun a failing page alone before debugging.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../../..");
const DOCS = process.env.DOCS || path.join(ROOT, "docs");
const OUT = path.join(__dirname, "out");
const FIXED = ["spielhuus-polivoks-vcf", "karltron-jinx", "allen-synthesis-europi-surface-mount", "dchwebb-addatone"];

const args = process.argv.slice(2);
let slugs = args.filter((a) => !a.startsWith("--") && !/^\d+$/.test(a));
const si = args.indexOf("--sample");
if (!slugs.length) slugs = [...FIXED];
if (si >= 0) {
  const n = +args[si + 1] || 30;
  const all = fs.readdirSync(path.join(DOCS, "m")).filter((d) => {
    const f = path.join(DOCS, "m", d, "index.html");
    return fs.existsSync(f) && fs.readFileSync(f, "utf8").includes('id="kicanvas"');
  });
  for (let i = all.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [all[i], all[j]] = [all[j], all[i]]; }
  slugs.push(...all.filter((s) => !slugs.includes(s)).slice(0, n));
}
fs.mkdirSync(OUT, { recursive: true });

const TYPES = { ".js": "text/javascript", ".css": "text/css", ".html": "text/html" };
async function run(browser, slug, break404) {
  const p = await browser.newPage({ viewport: { width: 1100, height: 1100 } });
  const errs = [];
  p.on("pageerror", (e) => errs.push(e.message.slice(0, 160)));
  await p.route(/wsrv\.nl|jsdelivr|fonts\.|github\.io/, (r) => r.abort());
  if (break404) await p.route(break404, (r) => r.fulfill({ status: 404, body: "nf", headers: { "access-control-allow-origin": "*" } }));
  await p.route("http://site.test/**", (r) => {
    const u = decodeURIComponent(new URL(r.request().url()).pathname);
    const f = path.join(DOCS, u.endsWith("/") ? u + "index.html" : u);
    return fs.existsSync(f) && fs.statSync(f).isFile()
      ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || "application/octet-stream" })
      : r.fulfill({ status: 404, body: "nf" });
  });
  await p.goto(`http://site.test/m/${slug}/`);
  const fail = [];
  if (!(await p.locator("#kicanvas .kcbtn").count())) { await p.close(); return [`${slug}: no viewer on the page`]; }
  const links = await p.$$eval(".kcfile", (a) => a.map((x) => ({ text: x.textContent, raw: x.dataset.raw })));
  const shown = () => p.evaluate(() => {
    const e = document.querySelector("kicanvas-embed");
    return e ? [...e.shadowRoot.querySelectorAll("kc-schematic-app,kc-board-app")].filter((a) => !a.hidden).map((a) => a.tagName) : null;
  });
  await p.click("#kicanvas .kcbtn");
  await p.waitForFunction(() => document.querySelector(".kcfile.on") || /could not|can't/.test(document.querySelector(".kcstatus")?.textContent || ""), null, { timeout: 60000 }).catch(() => {});
  const status = (await p.textContent(".kcstatus")) || "";
  if (/could not|can't/.test(status)) fail.push(`status: ${status}`);
  const first = await p.evaluate(() => document.querySelector(".kcfile.on")?.textContent);
  const firstSch = links.find((l) => l.text.endsWith(".kicad_sch") && !(break404 && break404.test(l.raw)));
  if (firstSch && first !== firstSch.text) fail.push(`opened on ${first}, expected ${firstSch.text}`);
  await p.locator("#kicanvas").screenshot({ path: path.join(OUT, `${slug}${break404 ? "-404" : ""}-open.png`) });
  for (let i = 0; i < links.length; i++) {
    const l = links[i];
    if (break404 && break404.test(l.raw)) {
      const bad = await p.locator(".kcfile").nth(i).evaluate((a) => a.classList.contains("bad"));
      if (!bad) fail.push(`${l.text}: forced 404 not struck out`);
      continue;
    }
    await p.locator(".kcfile").nth(i).click();
    await p.waitForTimeout(1500);
    const on = await p.evaluate(() => document.querySelector(".kcfile.on")?.textContent);
    const view = (await shown()) || [];
    const want = l.text.endsWith(".kicad_pcb") ? "KC-BOARD-APP" : "KC-SCHEMATIC-APP";
    if (on !== l.text) fail.push(`${l.text}: link not highlighted (on=${on})`);
    else if (view.length !== 1 || view[0] !== want) fail.push(`${l.text}: shows ${view.join("+") || "nothing"}, want ${want}`);
  }
  if (!p.url().endsWith(`/m/${slug}/`)) fail.push(`navigated away to ${p.url()}`);
  await p.locator("#kicanvas").screenshot({ path: path.join(OUT, `${slug}${break404 ? "-404" : ""}-last.png`) });
  fail.push(...errs.map((e) => `pageerror: ${e}`));
  await p.close();
  return fail.map((f) => `${slug}${break404 ? " (forced 404)" : ""}: ${f}`);
}

(async () => {
  const b = await chromium.launch({ args: ["--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"] });
  const all = [];
  for (const s of slugs) {
    const f = await run(b, s).catch((e) => [`${s}: ${e.message.slice(0, 160)}`]);
    console.log(f.length ? `FAIL ${s}\n  ` + f.join("\n  ") : `ok   ${s}`);
    all.push(...f);
  }
  // forced 404 on the second file of the first fixed case: the rest must still load
  const f = await run(b, FIXED[0], /mount\.kicad_sch$/).catch((e) => [`404 case: ${e.message.slice(0, 160)}`]);
  console.log(f.length ? `FAIL ${FIXED[0]} (forced 404)\n  ` + f.join("\n  ") : `ok   ${FIXED[0]} (forced 404)`);
  all.push(...f);
  // network hiccup: the first download of a board fails once; the page must offer "Try again", and that must work
  const g = await (async () => {
    const p = await b.newPage({ viewport: { width: 1100, height: 1100 } });
    let failed = false;
    await p.route(/wsrv\.nl|jsdelivr|fonts\.|github\.io/, (r) => r.abort());
    await p.route(/\.kicad_pcb$/, (r) => (!failed && r.request().method() === "GET") ? (failed = true, r.abort("failed")) : r.continue());
    await p.route("http://site.test/**", (r) => {
      const u = decodeURIComponent(new URL(r.request().url()).pathname);
      const f = path.join(DOCS, u.endsWith("/") ? u + "index.html" : u);
      return fs.existsSync(f) && fs.statSync(f).isFile() ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || "application/octet-stream" }) : r.fulfill({ status: 404, body: "nf" });
    });
    await p.goto(`http://site.test/m/${FIXED[0]}/`);
    await p.click("#kicanvas .kcbtn");
    const out = [];
    await p.waitForFunction(() => /Try again/.test(document.querySelector(".kcbtn")?.textContent || "") && !document.querySelector(".kcbtn").hidden, null, { timeout: 70000 })
      .catch(() => out.push("no 'Try again' after a failed download"));
    if (!out.length) {
      await p.click("#kicanvas .kcbtn");
      await p.waitForFunction(() => document.querySelector(".kcfile.on"), null, { timeout: 60000 }).catch(() => out.push("'Try again' did not load the viewer"));
    }
    await p.close();
    return out.map((x) => `${FIXED[0]} (network hiccup): ${x}`);
  })().catch((e) => [`hiccup case: ${e.message.slice(0, 160)}`]);
  console.log(g.length ? `FAIL ${FIXED[0]} (network hiccup)\n  ` + g.join("\n  ") : `ok   ${FIXED[0]} (network hiccup, Try again)`);
  all.push(...g);
  await b.close();
  console.log(all.length ? `\n${all.length} problem(s); screenshots in ${path.relative(ROOT, OUT)}/` : `\nall passed; screenshots in ${path.relative(ROOT, OUT)}/`);
  process.exit(all.length ? 1 : 0);
})();
