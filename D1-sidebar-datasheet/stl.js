// STL panel viewer (d, 2026-09-28 02:04): three.js is fetched only when a button is clicked.
let lib;
const libs = () => lib ||= Promise.all([import("three"), import("three/addons/loaders/STLLoader.js"), import("three/addons/controls/OrbitControls.js")]);
async function getStl(raw, media) {
  let r = await fetch(raw);
  if (!r.ok) throw new Error("HTTP " + r.status);
  let b = await r.arrayBuffer();
  if (b.byteLength < 400 && new TextDecoder().decode(b).startsWith("version https://git-lfs")) {   // Git LFS pointer
    r = await fetch(media);
    if (!r.ok) throw new Error("Git LFS file, HTTP " + r.status);
    b = await r.arrayBuffer();
  }
  return b;
}
function show(view, [THREE, { STLLoader }, { OrbitControls }], buf) {
  if (view._dispose) view._dispose();
  const g = new STLLoader().parse(buf);
  g.computeBoundingBox();
  let s = g.boundingBox.getSize(new THREE.Vector3());
  // a panel is a plate: turn its thinnest axis toward the viewer, then stand its long side upright
  if (s.x <= s.y && s.x <= s.z) g.rotateY(Math.PI / 2); else if (s.y <= s.x && s.y <= s.z) g.rotateX(Math.PI / 2);
  g.computeBoundingBox(); s = g.boundingBox.getSize(new THREE.Vector3());
  if (s.x > s.y) g.rotateZ(Math.PI / 2);
  g.center(); g.computeBoundingBox(); s = g.boundingBox.getSize(new THREE.Vector3());
  const w = view.clientWidth, h = Math.max(260, Math.min(460, Math.round(w * 1.3)));
  const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  ren.setPixelRatio(Math.min(devicePixelRatio, 2)); ren.setSize(w, h);
  view.replaceChildren(ren.domElement);
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(30, w / h, 0.1, 100000);
  const fit = Math.max(s.y, s.x * h / w) / 2 / Math.tan(Math.PI * 15 / 180) * 1.15 + s.z;
  cam.position.set(fit * 0.25, fit * 0.12, fit);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(0.6, 0.8, 1); cam.add(key); scene.add(cam);
  scene.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0xb9bdc4, metalness: 0.25, roughness: 0.55, side: THREE.DoubleSide })));
  const ctl = new OrbitControls(cam, ren.domElement);
  const draw = () => ren.render(scene, cam);
  ctl.addEventListener("change", draw); draw();
  const ro = new ResizeObserver(() => { const w2 = view.clientWidth; if (w2 && w2 !== ren.domElement.width / ren.getPixelRatio()) { ren.setSize(w2, h); cam.aspect = w2 / h; cam.updateProjectionMatrix(); draw(); } });
  ro.observe(view);
  view._dispose = () => { ro.disconnect(); ctl.dispose(); g.dispose(); ren.dispose(); };
}
document.querySelectorAll(".stl").forEach(box => box.querySelectorAll(".stlbtn").forEach(btn => btn.addEventListener("click", async () => {
  const view = box.querySelector(".stlview"), st = box.querySelector(".stlstatus"), hint = box.querySelector(".stlhint");
  box.querySelectorAll(".stlbtn").forEach(b => b.classList.toggle("on", b === btn));
  st.textContent = "Loading " + btn.dataset.name + "…"; view.hidden = false;
  try {
    const [three, buf] = await Promise.all([libs(), getStl(btn.dataset.raw, btn.dataset.media)]);
    show(view, three, buf); st.textContent = ""; hint.hidden = false;
  } catch (err) {
    view.hidden = true; hint.hidden = true;
    st.textContent = "Could not show the model here (" + err.message + "). ";
    const a = document.createElement("a"); a.href = btn.dataset.href; a.textContent = "Open it on GitHub"; st.append(a);
  }
})));
