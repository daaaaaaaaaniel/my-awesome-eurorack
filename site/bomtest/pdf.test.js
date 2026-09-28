const { chromium } = require("playwright"); const fs = require("fs"), path = require("path");
const DOCS = "/tmp/pv/docs", PJ = "/tmp/sj/pdfjs/package/build/";
(async () => {
  const b = await chromium.launch({ args: ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"] });
  for (const slug of process.argv.slice(2)) {
    const p = await b.newPage({ viewport: { width: 1300, height: 1000 } });
    await p.addInitScript(() => Object.defineProperty(Navigator.prototype, "pdfViewerEnabled", { get: () => false }));
    await p.route(/wsrv\.nl|fonts\./, r => r.abort());
    await p.route(/cdn\.jsdelivr\.net\/npm\/pdfjs-dist@4\.10\.38\/build\/(.*)$/, r => { const f = PJ + r.request().url().split("/build/")[1]; return r.fulfill({ path: f, contentType: "text/javascript" }); });
    await p.route("http://site.test/**", r => { const u = decodeURIComponent(new URL(r.request().url()).pathname); const f = path.join(DOCS, u.endsWith("/") ? u + "index.html" : u);
      return fs.existsSync(f) && fs.statSync(f).isFile() ? r.fulfill({ path: f, contentType: { ".js": "text/javascript", ".css": "text/css", ".html": "text/html" }[path.extname(f)] || "application/octet-stream" }) : r.fulfill({ status: 404, body: "nf" }); });
    await p.goto(`http://site.test/m/${slug}/`);
    const n = await p.locator('.bomfile[data-kind="pdf"]').count();
    for (let i = 0; i < n; i++) {
      const a = p.locator('.bomfile[data-kind="pdf"]').nth(i); const t = await a.textContent();
      await a.click(); await p.waitForTimeout(6000);
      const r = await p.evaluate(() => ({ st: document.querySelector(".bomstatus").textContent, c: document.querySelectorAll(".bomview canvas").length, w: document.querySelector(".bomview canvas")?.width || 0, ink: (() => { const c = document.querySelector(".bomview canvas"); if (!c) return 0; const d = c.getContext("2d").getImageData(0, 0, c.width, Math.min(c.height, 400)).data; let k = 0; for (let j = 0; j < d.length; j += 4) if (d[j] < 200) k++; return k; })() }));
      console.log(`${r.c && r.ink ? "ok  " : "FAIL"} ${slug} :: ${t} canvases=${r.c} width=${r.w} dark-pixels=${r.ink} ${r.st}`);
    }
    await p.screenshot({ path: `/tmp/bomtest/out/pdf-${slug}.png` }).catch(() => {});
    await p.close();
  }
  await b.close();
})();
