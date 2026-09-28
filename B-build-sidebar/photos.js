const box = document.getElementById("photos"), strip = box && box.querySelector(".strip");
if (strip) {
  const e = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  const linkName = u => u.replace(/\/+$/, "").split("/").pop().replace(/(%[0-9A-Fa-f]{2})+/g, m => { try { return decodeURIComponent(m); } catch { return m; } });
  const thumb = (u, dpr = 1) => {
    const raw = u.replace(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\//, "https://raw.githubusercontent.com/$1/$2/");
    const svg = /\.(svg|ai)$/i.test(raw);
    const q = encodeURIComponent(raw).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
    return `https://wsrv.nl/?url=${q}${svg ? "&trim=10&bg=d6d2c8" : ""}&w=400&h=360&fit=inside${svg ? "" : "&we"}&output=webp&q=78` + (dpr > 1 ? `&dpr=${dpr}` : "");
  };
  const cap = (i, n, u) => `<span class="gcount">${i + 1} / ${n}</span> · <a href="${e(u)}" title="Open the original on GitHub">${e(linkName(u))}</a>`;
  const list = [...strip.children].map(a => a.getAttribute("href")), N = list.length;
  const gal = box.querySelector(".gal"), capEl = box.querySelector(".gcap");
  let cur = 0;
  const show = i => {
    cur = (i + N) % N;
    const u = list[cur], n = linkName(u), old = box.querySelector("a.thumb"), h = old.offsetHeight;
    old.outerHTML = `<a class="thumb" href="${e(u)}" title="${e(n)}"><img loading="lazy" decoding="async" alt="${e(n)}" src="${e(thumb(u))}" srcset="${e(thumb(u))} 1x, ${e(thumb(u, 2))} 2x" onerror="this.parentNode.classList.add('broken');this.replaceWith(document.createTextNode(this.alt))"></a>`;
    const t = box.querySelector("a.thumb"), img = t.querySelector("img");
    t.style.minHeight = h + "px";                                 // hold the height while the next image loads
    if (img) ["load", "error"].forEach(k => img.addEventListener(k, () => { t.style.minHeight = ""; }, { once: true }));
    capEl.innerHTML = cap(cur, N, u);
    [...strip.children].forEach((a, k) => { a.classList.toggle("on", k === cur); if (k === cur) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current"); });
    const a = strip.children[cur];                                // keep the highlighted thumbnail in view, inside the strip only
    strip.scrollTo({ left: a.offsetLeft - (strip.clientWidth - a.offsetWidth) / 2, behavior: "smooth" });
    for (const k of [cur + 1, cur - 1]) (new Image()).src = thumb(list[(k + N) % N], devicePixelRatio > 1 ? 2 : 1);
  };
  box.querySelectorAll(".gnav").forEach(b => { b.hidden = false; });
  box.querySelector(".gnav.prev").addEventListener("click", () => show(cur - 1));
  box.querySelector(".gnav.next").addEventListener("click", () => show(cur + 1));
  strip.addEventListener("click", ev => {
    const a = ev.target.closest("a[data-i]");
    if (!a || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    ev.preventDefault(); show(+a.dataset.i);
  });
  box.addEventListener("keydown", ev => {
    if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") { ev.preventDefault(); show(cur + (ev.key === "ArrowRight" ? 1 : -1)); }
  });
  let x0 = null, swiped = false;                                  // touch/pen swipe on the main photo
  gal.addEventListener("pointerdown", ev => { x0 = ev.pointerType === "mouse" ? null : ev.clientX; });
  gal.addEventListener("pointerup", ev => {
    if (x0 === null) return;
    const dx = ev.clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) { swiped = true; show(cur + (dx < 0 ? 1 : -1)); }
  });
  gal.addEventListener("click", ev => { if (swiped) { swiped = false; ev.preventDefault(); } }, true);
}
