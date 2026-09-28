// KiCanvas test (d, 2026-09-28 02:15; file links drive the viewer, d 03:16).
// The viewer script is imported only when needed. File links switch the main pane through KiCanvas's own
// "context-request" protocol (how its panels reach the project) and the project's public set_active_page(),
// so KiCanvas itself is not patched for this.
function kcProject(embed) {
  let project = null;
  const ev = new Event("context-request", { bubbles: true, composed: true, cancelable: true });
  ev.context_name = "project";
  ev.callback = (ctx) => { ev.stopPropagation(); project = ctx; };
  embed.dispatchEvent(ev);
  return project;
}
// KiCanvas names a fetched file by its URL's last segment, still percent-encoded ("AddaTone%20components.kicad_sch")
const dec = (x) => { try { return decodeURIComponent(x); } catch (e) { return x; } };
const base = (u) => dec(u.split("/").pop());
const wait = (ms) => new Promise((r) => setTimeout(() => r(false), ms));
document.querySelectorAll(".kc").forEach((box) => {
  const btn = box.querySelector(".kcbtn"), view = box.querySelector(".kcview"), st = box.querySelector(".kcstatus");
  const links = [...box.querySelectorAll(".kcfile")];
  let ready = null;
  const mark = (a) => links.forEach((l) => l.classList.toggle("on", l === a));
  async function open() {
    btn.disabled = true; btn.textContent = "Loading KiCanvas…"; st.textContent = "";
    try { await import(new URL("kicanvas.js", import.meta.url).href); }
    catch (err) { btn.textContent = "Could not load the viewer (" + err.message + ")"; return null; }
    // a file that is gone (renamed or deleted on GitHub) would stop the whole viewer from loading: check first
    const res = await Promise.all(links.map((a) => fetch(a.dataset.raw, { method: "HEAD" }).then((r) => r.ok ? "" : "HTTP " + r.status, (e) => "unreachable")));
    const good = links.filter((a, i) => { if (res[i]) { a.nextElementSibling.nextElementSibling.textContent = " — could not load (" + res[i] + ")"; a.classList.add("bad"); } return !res[i]; });
    if (!good.length) { btn.textContent = "None of the files could be loaded"; return null; }
    const el = document.createElement("kicanvas-embed");
    el.setAttribute("controls", "full"); el.setAttribute("theme", "kicad");  // ignored by this KiCanvas build (viewers use Witch Hazel); left in case a later build honours it. d 08:45: no workaround
    for (const a of good) { const s = document.createElement("kicanvas-source"); s.setAttribute("src", a.dataset.raw); el.append(s); }
    view.replaceChildren(el); view.hidden = false; btn.hidden = true;
    st.textContent = "Reading " + good.length + " file" + (good.length > 1 ? "s" : "") + "…";
    const project = kcProject(el);
    // "context-request" is KiCanvas-internal: if a future KiCanvas drops it, the viewer still works, only our links don't
    if (!project) { st.textContent = "The file links can't switch this viewer; use the folder icon in its right-hand bar."; return null; }
    const ok = await Promise.race([project.loaded.then(() => true), wait(45000)]);
    if (!ok) {   // a failed download or a file KiCanvas cannot parse: let the reader try again
      st.textContent = "The viewer could not load these files (a network hiccup, or a file it can't read). Try again, or use the GitHub links.";
      view.hidden = true; view.replaceChildren(); btn.hidden = false; btn.disabled = false; btn.textContent = "Try again"; ready = null;
      return null;
    }
    st.textContent = "";
    return { el, project };
  }
  async function show(a) {
    ready ||= open();
    const v = await ready;
    if (!v) return null;
    if (a.classList.contains("bad")) return false;
    const page = [...v.project.pages()].find((p) => dec(p.filename) === base(a.dataset.raw));
    if (!page) { a.nextElementSibling.nextElementSibling.textContent = " — the viewer could not read this file"; return false; }
    v.project.set_active_page(page); mark(a); return true;
  }
  // open on the first schematic (root sheet first); if KiCanvas could not read it, the next file that works
  btn.addEventListener("click", async () => {
    const order = [...links.filter((a) => a.dataset.raw.endsWith(".kicad_sch")), ...links.filter((a) => !a.dataset.raw.endsWith(".kicad_sch"))];
    for (const a of order) if ((await show(a)) !== false) break;   // shown, or the viewer itself failed
  });
  links.forEach((a) => a.addEventListener("click", (ev) => {
    if (ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;   // new tab etc. still goes to GitHub
    ev.preventDefault(); show(a).then(() => view.scrollIntoView({ behavior: "smooth", block: "nearest" }));
  }));
});
