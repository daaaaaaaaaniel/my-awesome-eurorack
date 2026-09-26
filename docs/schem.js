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
