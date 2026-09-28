// Module pages: the BOM box (d, 2026-09-28 17:51). Nothing is fetched until the reader asks. Each file is fetched from
// raw.githubusercontent.com (CORS allowed) or the maker's own host and shown by format:
//  - iBOM: the file's own HTML runs in a sandboxed iframe (srcdoc, scripts only: no access to this page or its storage)
//  - CSV / TSV / TXT / Markdown / HTML tables / Google Sheet (CSV export): drawn as a plain table, text only
//  - XLSX / XLS / ODS: read by SheetJS inside a Web Worker (bom-sheet.js), so a hostile file can't touch the page
//  - PDF: the browser's own viewer (blob iframe), or PDF.js page canvases on touch devices
// A file that fails is struck out and the reader can open it on GitHub instead.
const PDFJS = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/";
const MAXROWS = 3000, MAXCOLS = 60;
const box = document.getElementById("bom");
if (box) {
  const btn = box.querySelector(".bombtn"), view = box.querySelector(".bomview"), st = box.querySelector(".bomstatus");
  const files = [...box.querySelectorAll(".bomfile")];
  let seq = 0;
  const say = (html) => { st.innerHTML = html || ""; };
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const table = (rows, note) => {
    rows = rows.map(r => r.map(c => (c == null ? "" : String(c)).trim())).filter(r => r.some(c => c));
    if (!rows.length) throw new Error("empty");
    let w = Math.min(MAXCOLS, Math.max(...rows.map(r => r.length)));
    const keep = [...Array(w).keys()].filter(i => rows.some(r => r[i]));          // drop columns that are empty everywhere
    rows = rows.map(r => keep.map(i => r[i] || "")); w = keep.length;
    // the header is the first row that fills at least half the columns; title rows above it become a note
    let h = rows.slice(0, 10).findIndex(r => r.filter(c => c).length >= Math.max(2, Math.ceil(w / 2)));
    if (h < 0) h = 0;
    const titles = rows.slice(0, h).map(r => r.filter(c => c).join(" · ")).join(" — ");
    if (titles) note = note ? note + " — " + titles : titles;
    rows = rows.slice(h);
    const cut = rows.length > MAXROWS + 1;
    const head = rows[0], body = rows.slice(1, MAXROWS + 1);
    const t = document.createElement("table"); t.className = "bomtable";
    const th = t.createTHead().insertRow();
    for (let i = 0; i < w; i++) { const c = document.createElement("th"); c.textContent = head[i] || ""; th.appendChild(c); }
    const tb = t.createTBody();
    for (const r of body) {
      const tr = tb.insertRow();
      for (let i = 0; i < w; i++) {
        const td = tr.insertCell(), v = r[i] || "";
        if (/^https?:\/\/\S+$/.test(v)) { const a = document.createElement("a"); a.href = v; a.rel = "noopener nofollow"; a.target = "_blank"; a.textContent = v; td.appendChild(a); }
        else td.textContent = v;
      }
    }
    const wrap = document.createElement("div"); wrap.className = "bomscroll"; wrap.appendChild(t);
    const frag = document.createDocumentFragment();
    if (note) { const p = document.createElement("p"); p.className = "small mute bomnote"; p.textContent = note; frag.appendChild(p); }
    frag.appendChild(wrap);
    if (!body.length) { const p = document.createElement("p"); p.className = "small mute"; p.textContent = "The file has column headings but lists no parts."; frag.appendChild(p); }
    if (cut) { const p = document.createElement("p"); p.className = "small mute"; p.textContent = `First ${MAXROWS} rows of ${rows.length - 1}.`; frag.appendChild(p); }
    return frag;
  };
  // CSV/TSV with quotes; the delimiter is the one that gives the most consistent column count
  const parseDelim = (text, d) => {
    const rows = []; let row = [], cell = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; continue; }
      if (ch === '"' && cell === "") q = true;
      else if (ch === d) { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
      else cell += ch;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    return rows;
  };
  const guessDelim = (text) => {
    const lines = text.split(/\r?\n/).filter(l => l.trim()).slice(0, 30);
    let best = null, bestScore = 0;
    for (const d of ["\t", ",", ";", "|"]) {
      const freq = new Map();
      for (const l of lines) { const n = parseDelim(l, d)[0]?.length || 0; freq.set(n, (freq.get(n) || 0) + 1); }
      let mode = 0, hits = 0;
      for (const [n, k] of freq) if (n > 1 && k > hits) { mode = n; hits = k; }
      const score = hits * Math.min(mode, 8);
      if (hits >= Math.max(2, lines.length * 0.6) && score > bestScore) { best = d; bestScore = score; }
    }
    return best;
  };
  const mdTables = (text) => {
    const out = []; let cur = null;
    for (const l of text.split(/\r?\n/)) {
      if (/^\s*\|/.test(l) && (l.match(/\|/g) || []).length >= 2) {   // a table row (the closing pipe is optional)
        const cells = l.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
        if (cells.every(c => /^:?-+:?$/.test(c))) continue;                          // the |---|---| row
        (cur = cur || []).push(cells.map(c => c.replace(/\*\*|`/g, "").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1").replace(/<br\s*\/?>/gi, " · ").replace(/<[^>]+>/g, "")));
      } else if (cur) { out.push(cur); cur = null; }
    }
    if (cur) out.push(cur);
    return out;
  };
  const htmlTables = (text) => {
    const doc = new DOMParser().parseFromString(text, "text/html");   // parsed inert: scripts never run
    return [...doc.querySelectorAll("table")].map(t => [...t.rows].map(r => [...r.cells].map(c => c.textContent.replace(/\s+/g, " ").trim())))
      .filter(t => t.length > 1);
  };
  const frame = (html, title) => {
    const f = document.createElement("iframe");
    f.className = "bomframe"; f.title = title;
    f.setAttribute("sandbox", "allow-scripts allow-popups allow-modals");
    f.srcdoc = html; return f;
  };
  async function pdf(buf, name, token) {
    if (navigator.pdfViewerEnabled === true && !matchMedia("(pointer: coarse)").matches) {
      const f = document.createElement("iframe"); f.className = "bomframe"; f.title = "BOM: " + name;
      f.src = URL.createObjectURL(new File([buf], name, { type: "application/pdf" }));
      return f;
    }
    const lib = await import(PDFJS + "pdf.min.mjs");
    lib.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.mjs";
    const doc = await lib.getDocument({ data: new Uint8Array(buf) }).promise;
    const wrap = document.createElement("div");
    (async () => {                                   // pages appear one by one; the status line is already cleared
      for (let i = 1; i <= Math.min(doc.numPages, 20); i++) {
        if (token !== seq) return;
        try {
          const page = await doc.getPage(i), v1 = page.getViewport({ scale: 1 });
          const scale = Math.min(2 * Math.max(view.clientWidth, 300) / v1.width, Math.sqrt(16e6 / (v1.width * v1.height)));
          const vp = page.getViewport({ scale }), c = document.createElement("canvas");
          c.width = Math.floor(vp.width); c.height = Math.floor(vp.height); c.className = "bompage";
          wrap.appendChild(c);
          await page.render({ canvasContext: c.getContext("2d"), viewport: vp }).promise;
        } catch (err) { console.error(err); }
      }
    })();
    return wrap;
  }
  const sheet = (buf) => new Promise((ok, bad) => {
    const w = new Worker(box.dataset.sheetjs);
    const t = setTimeout(() => { w.terminate(); bad(new Error("spreadsheet took too long")); }, 20000);
    w.onmessage = (ev) => { clearTimeout(t); w.terminate(); ev.data.error ? bad(new Error(ev.data.error)) : ok(ev.data.sheets); };
    w.onerror = (ev) => { clearTimeout(t); w.terminate(); bad(new Error(ev.message || "worker failed")); };
    w.postMessage({ buf, maxRows: MAXROWS + 1, maxCols: MAXCOLS }, [buf]);
  });
  const sheetsView = (sheets) => {
    sheets = sheets.filter(s => s.rows.some(r => r.some(c => c !== "" && c != null)));
    if (!sheets.length) throw new Error("empty");
    const out = document.createElement("div");
    const pane = document.createElement("div");
    const show = (i) => { pane.replaceChildren(table(sheets[i].rows)); tabs && [...tabs.children].forEach((b, k) => b.classList.toggle("on", k === i)); };
    let tabs = null;
    if (sheets.length > 1) {
      tabs = document.createElement("div"); tabs.className = "bomtabs";
      sheets.forEach((s, i) => { const b = document.createElement("button"); b.type = "button"; b.textContent = s.name; b.onclick = () => show(i); tabs.appendChild(b); });
      out.appendChild(tabs);
    }
    out.appendChild(pane); show(0);
    return out;
  };
  async function load(a) {
    const token = ++seq;
    files.forEach(x => x.classList.toggle("on", x === a));
    btn.hidden = true;
    say("Loading " + esc(a.textContent) + "…");
    view.replaceChildren();
    const kind = a.dataset.kind, src = a.dataset.raw, name = a.textContent;
    try {
      const res = await fetch(src);
      if (!res.ok) throw new Error("HTTP " + res.status);
      let node;
      if (kind === "sheet") node = sheetsView(await sheet(await res.arrayBuffer()));
      else if (kind === "pdf") node = await pdf(await res.arrayBuffer(), name, token);
      else {
        const text = await res.text();
        if (kind === "html") {
          if (/pcbdata|InteractiveHtmlBom/i.test(text)) node = frame(text, "Interactive BOM: " + name);
          else { const ts = htmlTables(text); if (!ts.length) throw new Error("no table"); node = table(ts.sort((x, y) => y.length - x.length)[0]); }
        } else if (kind === "md") {
          const ts = mdTables(text);
          if (ts.length) { node = document.createDocumentFragment(); ts.forEach(t => node.appendChild(table(t))); }
          else { node = document.createElement("pre"); node.className = "bompre"; node.textContent = text; }
        } else {
          const d = kind === "tsv" ? "\t" : kind === "csv" ? guessDelim(text) || "," : guessDelim(text);
          if (d) node = table(parseDelim(text, d));
          else { node = document.createElement("pre"); node.className = "bompre"; node.textContent = text; }
        }
      }
      if (token !== seq) return;
      view.replaceChildren(node); say("");
    } catch (err) {
      if (token !== seq) return;
      console.error(err);
      a.classList.add("bad");
      say('Couldn’t show ' + esc(name) + ' here. <a href="' + esc(a.getAttribute("href")) + '">Open it on ' + esc(a.dataset.host || "GitHub") + '</a>.');
    }
  }
  const first = files.find(x => x.dataset.kind) || null;
  btn.addEventListener("click", () => first && load(first));
  files.forEach(a => a.addEventListener("click", (ev) => {
    if (!a.dataset.kind || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    ev.preventDefault(); load(a);
  }));
}
