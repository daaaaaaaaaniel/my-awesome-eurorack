const box = document.getElementById("photos");
if (box) {
  const e = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  const linkName = u => u.replace(/\/+$/, "").split("/").pop().replace(/(%[0-9A-Fa-f]{2})+/g, m => { try { return decodeURIComponent(m); } catch { return m; } });
  const thumb = (u, dpr = 1) => {
    const raw = u.replace(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/blob\//, "https://raw.githubusercontent.com/$1/$2/");
    const svg = raw.toLowerCase().endsWith(".svg");
    const q = encodeURIComponent(raw).replace(/[!'()*]/g, c => "%" + c.charCodeAt(0).toString(16).toUpperCase());
    return `https://wsrv.nl/?url=${q}${svg ? "&trim=10" : ""}&w=400&h=360&fit=inside${svg ? "" : "&we"}&output=webp&q=78` + (dpr > 1 ? `&dpr=${dpr}` : "");
  };
  const CAPTION = " · thumbnail via wsrv.nl, click for the original";
  box.addEventListener("click", ev => {
    const a = ev.target.closest("ul.links a");
    if (!a || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    ev.preventDefault();
    const old = box.querySelector("a.thumb"), cur = old.getAttribute("href"), next = a.getAttribute("href"), n = linkName(next), h = old.offsetHeight;
    old.outerHTML = `<a class="thumb" href="${e(next)}" title="${e(n)}"><img loading="lazy" decoding="async" alt="${e(n)}" src="${e(thumb(next))}" srcset="${e(thumb(next))} 1x, ${e(thumb(next, 2))} 2x" onerror="this.parentNode.classList.add('broken');this.replaceWith(document.createTextNode(this.alt))"></a>`;
    const t = box.querySelector("a.thumb"), img = t.querySelector("img");
    t.style.minHeight = h + "px";                                 // hold the height while the next image loads
    if (img) ["load", "error"].forEach(k => img.addEventListener(k, () => { t.style.minHeight = ""; }, { once: true }));
    t.nextElementSibling.textContent = n + CAPTION;
    a.setAttribute("href", cur); a.textContent = linkName(cur);
    const r = t.getBoundingClientRect();
    if (r.top < 0 || r.top > innerHeight) t.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
}
