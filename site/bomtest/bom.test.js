// BOM box test (d, 2026-09-28): opens each sample module page, clicks every BOM file, checks something real is shown.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const DOCS = process.env.DOCS || "/tmp/pv/docs";
const OUT = process.env.OUT || "/tmp/bomtest/out";
fs.mkdirSync(OUT, { recursive: true });
const slugs = process.argv.slice(2);
const TYPES = { ".js": "text/javascript", ".css": "text/css", ".html": "text/html" };
(async () => {
  const b = await chromium.launch({ args: ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"] });
  const fails = [];
  for (const slug of slugs) {
    const p = await b.newPage({ viewport: { width: 1300, height: 1000 } });
    const errs = []; p.on("pageerror", e => errs.push(e.message.slice(0, 120)));
    await p.route(/wsrv\.nl|fonts\.|jsdelivr|github\.io/, r => r.abort());
    await p.route("http://site.test/**", r => {
      const u = decodeURIComponent(new URL(r.request().url()).pathname);
      const f = path.join(DOCS, u.endsWith("/") ? u + "index.html" : u);
      return fs.existsSync(f) && fs.statSync(f).isFile() ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || "application/octet-stream" }) : r.fulfill({ status: 404, body: "nf" });
    });
    await p.goto(`http://site.test/m/${slug}/`);
    if (!(await p.locator("#bom").count())) { fails.push(`${slug}: no BOM box`); await p.close(); continue; }
    const files = await p.$$eval(".bomfile", a => a.map(x => ({ t: x.textContent, k: x.dataset.kind, raw: x.dataset.raw })));
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (!/raw\.githubusercontent/.test(f.raw) || f.k === "pdf") { console.log(`  skip ${slug} ${f.t} (${f.k}, needs a host this container can't reach)`); continue; }
      if (i === 0) await p.click("#bom .bombtn"); else await p.locator(".bomfile").nth(i).click();
      await p.waitForFunction(() => { const s = document.querySelector(".bomstatus").textContent; return !/Loading/.test(s); }, null, { timeout: 45000 }).catch(() => {});
      const r = await p.evaluate(() => ({
        status: document.querySelector(".bomstatus").textContent,
        rows: document.querySelectorAll(".bomview table.bomtable tbody tr").length,
        cols: document.querySelector(".bomview table.bomtable thead tr")?.children.length || 0,
        frame: !!document.querySelector(".bomview iframe.bomframe"),
        pre: document.querySelector(".bomview pre")?.textContent.length || 0,
        head: [...(document.querySelector(".bomview table.bomtable thead tr")?.children || [])].map(c => c.textContent).slice(0, 6).join(" | "),
      }));
      let ibom = null;
      if (r.frame) { await p.waitForTimeout(2500); ibom = await p.frameLocator(".bomview iframe").locator("#bomtable tr, .bom tr, table tr").count().catch(() => -1); }
      const ok = !/Couldn/.test(r.status) && (r.rows > 0 || r.cols > 0 || r.pre > 0 || (r.frame && ibom > 0));
      console.log(`${ok ? "ok  " : "FAIL"} ${slug} :: ${f.t} [${f.k}] rows=${r.rows} cols=${r.cols} frame=${r.frame}${r.frame ? " ibomRows=" + ibom : ""} pre=${r.pre} ${r.head ? "head: " + r.head : ""} ${r.status}`);
      if (!ok) fails.push(`${slug} ${f.t}: ${r.status}`);
      await p.locator("#bom").screenshot({ path: path.join(OUT, `${slug}-${i}.png`) }).catch(() => {});
    }
    if (errs.length) { console.log("  pageerrors:", errs.join(" | ")); }
    await p.close();
  }
  await b.close();
  console.log(fails.length ? `\n${fails.length} failure(s)` : "\nall passed");
})();
