// Module pages: draw a PDF schematic inline with PDF.js, one canvas per page, each page rendered when it nears the viewport.
const PDFJS = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/";
const box = document.querySelector(".pdfview");
if (box) {
  const st = box.querySelector(".pdfstatus");
  const fail = () => { st.innerHTML = 'Couldn\u2019t show this PDF here. <a href="' + box.dataset.href + '">Open it on GitHub</a>.'; };
  const near = (el, fn) => { const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { io.disconnect(); fn(); } }, { rootMargin: "800px" }); io.observe(el); };
  near(box, async () => {
    try {
      const lib = await import(PDFJS + "pdf.min.mjs");
      lib.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.mjs";
      const doc = await lib.getDocument({ url: box.dataset.src }).promise;
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
    } catch (err) { console.error(err); fail(); }
  });
}
