// KiCanvas test (d, 2026-09-28 02:15): the viewer script is imported only on click.
document.querySelectorAll(".kc").forEach(box => {
  const btn = box.querySelector(".kcbtn"), view = box.querySelector(".kcview");
  btn.addEventListener("click", async () => {
    btn.disabled = true; btn.textContent = "Loading KiCanvas…";
    try { await import(new URL("kicanvas.js", import.meta.url).href); }
    catch (err) { btn.textContent = "Could not load the viewer (" + err.message + ")"; return; }
    const el = document.createElement("kicanvas-embed");
    el.setAttribute("controls", "full"); el.setAttribute("theme", box.dataset.theme || "kicad");
    for (const u of JSON.parse(btn.dataset.src)) { const s = document.createElement("kicanvas-source"); s.setAttribute("src", u); el.append(s); }
    view.replaceChildren(el); view.hidden = false; btn.hidden = true;
  });
});
