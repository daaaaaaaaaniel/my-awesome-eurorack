(function(){
const rows=window.__ROWS__;
const $=s=>document.querySelector(s), $$=(s,el=document)=>[...el.querySelectorAll(s)];
const FACETS=["tags","lic","terms","mount","files","license","proto","maker"];
const state={q:"",tags:new Set(),lic:new Set(),terms:new Set(),mount:new Set(),files:new Set(),license:new Set(),proto:new Set(),maker:new Set(),mode:{},fsort:{},pmode:"hide",view:"table",sort:"name",dir:"asc"};
// --- read URL
const sp=new URLSearchParams(location.search);
for(const k of FACETS){for(const v of sp.getAll(k))state[k].add(v);if(sp.get(k+"_mode")==="all")state.mode[k]="all";const fs=sp.get(k+"_sort");if(fs==="name"||fs==="count")state.fsort[k]=fs;}
if(sp.get("proto_mode")==="show")state.pmode="show";if(sp.get("q"))state.q=sp.get("q");if(sp.get("view"))state.view=sp.get("view");if(sp.get("sort"))state.sort=sp.get("sort");if(sp.get("dir"))state.dir=sp.get("dir");
function writeURL(){const p=new URLSearchParams();if(state.q)p.set("q",state.q);for(const k of FACETS){for(const v of state[k])p.append(k,v);if(state.mode[k]==="all")p.set(k+"_mode","all");if(state.fsort[k])p.set(k+"_sort",state.fsort[k]);}
 if(state.pmode==="show")p.set("proto_mode","show");if(state.view!=="table")p.set("view",state.view);if(state.sort!=="name")p.set("sort",state.sort);if(state.dir!=="asc")p.set("dir",state.dir);
 history.replaceState(null,"",location.pathname+(p.toString()?"?"+p:""));}
// --- facets
const facetDefault={maker:"name"};
function facetHTML(name,key,counts){const by=state.fsort[name]||facetDefault[name]||"count";
 const vals=[...counts.keys()].sort((a,b)=>by==="name"?a.localeCompare(b):counts.get(b)-counts.get(a)||a.localeCompare(b));
 return vals.map(v=>`<label><input type="checkbox" value="${esc(v)}" ${state[key].has(v)?"checked":""}><span>${esc(v)}</span><span class="n">${counts.get(v)}</span></label>`).join("");}
function facet(name,key,getter){const box=$("#f-"+name);const counts=new Map();
 for(const r of rows){for(const v of getter(r))counts.set(v,(counts.get(v)||0)+1);}
 box.innerHTML=facetHTML(name,key,counts);
 box.addEventListener("change",ev=>{const v=ev.target.value;ev.target.checked?state[key].add(v):state[key].delete(v);render();});
 const fs=$(`.fsort[data-f=${name}]`);if(fs){$$("input",fs).forEach(i=>i.checked=(state.fsort[name]||facetDefault[name]||"count")===i.value);
  fs.addEventListener("change",ev=>{state.fsort[name]=ev.target.value;box.innerHTML=facetHTML(name,key,counts);
   const q=$("#maker-q");if(name==="maker"&&q&&q.value){q.dispatchEvent(new Event("input"));}writeURL();});}}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
const G={tags:r=>r.tags,lic:r=>r.lic||[],terms:r=>r.terms||[],mount:r=>[r.mount],files:r=>r.files,license:r=>[r.license||"not determined"],proto:r=>r.proto==="X"?["prototype"]:r.proto==="?"?["prototype?"]:[],maker:r=>r.makers};
if($("#f-tags"))facet("tags","tags",G.tags);if($("#f-lic"))facet("lic","lic",G.lic);if($("#f-terms"))facet("terms","terms",G.terms);facet("mount","mount",G.mount);facet("files","files",G.files);if($("#f-license"))facet("license","license",G.license);facet("proto","proto",G.proto);facet("maker","maker",G.maker);
$("#maker-q").addEventListener("input",ev=>{const q=ev.target.value.toLowerCase();$$("#f-maker label").forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?"":"none");});
// --- filter
function match(r,ignoreProto){
 if(state.q){const q=state.q.toLowerCase();if(!(r.name+" "+r.creator+" "+r.type+" "+r.notes+" "+r.license).toLowerCase().includes(q))return false;}
 if(!ignoreProto&&!state.proto.size&&state.pmode==="hide"&&r.proto)return false;
 for(const k of FACETS){if(state[k].size){const vs=G[k](r);const ok=state.mode[k]==="all"?[...state[k]].every(v=>vs.includes(v)):vs.some(v=>state[k].has(v));if(!ok)return false;}}
 return true;}
function sorted(list){const k=state.sort,d=state.dir==="asc"?1:-1;
 const key=r=>k==="name"?r.name.toLowerCase():k==="maker"?r.creator.toLowerCase():k==="date"?r.date:k==="type"?r.type.toLowerCase():k==="mount"?r.mount:k==="parts"?(r.parts==null?(d>0?1e9:-1):r.parts):r.name.toLowerCase();
 return list.sort((a,b)=>{const x=key(a),y=key(b);return x<y?-d:x>y?d:a.name.localeCompare(b.name);});}
// --- render
function chip(r){let s=r.tags.filter(t=>t!=="not mapped").map(t=>`<span class="chip tag">${esc(t)}</span>`).join("");s+=r.licchips||"";s+=`<span class="chip${r.components?"":" dim"}">${r.components?esc(r.components):"mounting n/d"}</span>`;
 for(const f of r.files)s+=`<span class="chip">${esc(f)}</span>`;
 if(r.proto==="X")s+='<span class="chip warn">prototype</span>';else if(r.proto==="?")s+='<span class="chip warn">prototype?</span>';return s;}
function card(r){return `<div class="card">${r.parts==null?"":`<div class="parts">${r.parts} parts</div>`}<div class="name"><a href="m/${r.slug}/">${esc(r.name)}</a></div><div class="maker">${esc(r.creator)}</div><div class="type">${r.type?esc(r.type):'<span class="nd">type not determined</span>'}</div><div class="chips">${chip(r)}</div></div>`;}
function table(list){const h=[["name","Module"],["maker","Maker"],["type","Type"],["mount","Mounting"],["files","Files"],["license","License"],["parts","Parts"],["date","Date"]];
 return `<table class="list"><thead><tr>${h.map(([k,l])=>`<th data-k="${k}" ${state.sort===k?`data-dir="${state.dir}"`:""}>${l}</th>`).join("")}</tr></thead><tbody>${list.map(r=>`<tr><td><a href="m/${r.slug}/">${esc(r.name)}</a>${r.proto?` <span class="chip warn">${r.proto==="X"?"prototype":"prototype?"}</span>`:""}</td><td>${esc(r.creator)}</td><td>${esc(r.type)}</td><td>${r.components?esc(r.components):'<span class="nd">n/d</span>'}</td><td>${r.files.join(", ")}</td><td>${r.licchips||(r.license?esc(r.license):'<span class="nd">n/d</span>')}</td><td class="num">${r.parts==null?'<span class="nd">—</span>':r.parts+(r.pooled?'<span class="mute" title="summed over several board files in the folder — variants may be pooled">*</span>':'')}</td><td class="mute">${esc(r.date)}</td></tr>`).join("")}</tbody></table>`;}
function render(){const list=sorted(rows.filter(r=>match(r)));const hid=(!state.proto.size&&state.pmode==="hide")?rows.filter(r=>r.proto&&match(r,true)).length:0;
 $("#count").textContent=`${list.length} of ${rows.length} modules`+(hid?` · ${hid} prototypes hidden`:"");
 const pm=$(".pmode");if(pm)pm.classList.toggle("off",state.proto.size>0);
 const out=$("#out");out.innerHTML=state.view==="grid"?`<div class="grid">${list.map(card).join("")}</div>`:table(list);
 if(state.view==="table")$$("#out th").forEach(th=>th.addEventListener("click",()=>{const k=th.dataset.k;if(k==="files")return;if(state.sort===k)state.dir=state.dir==="asc"?"desc":"asc";else{state.sort=k;state.dir="asc";}$("#sort").value=state.sort;render();}));
 $$(".toolbar [data-view]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.view===state.view));writeURL();}
$("#q").value=state.q;$("#q").addEventListener("input",ev=>{state.q=ev.target.value.trim();render();});
$("#sort").value=state.sort;$("#sort").addEventListener("change",ev=>{state.sort=ev.target.value;state.dir=ev.target.value==="date"?"desc":"asc";render();});
$$(".toolbar [data-view]").forEach(b=>b.addEventListener("click",()=>{state.view=b.dataset.view;render();}));
$$(".mode").forEach(m=>{const k=m.dataset.f;const sync=()=>$$("input",m).forEach(i=>i.checked=(state.mode[k]||"any")===i.value);sync();
 m.addEventListener("change",ev=>{state.mode[k]=ev.target.value;render();});});
const pm=$(".pmode");if(pm){$$("input",pm).forEach(i=>i.checked=state.pmode===i.value);pm.addEventListener("change",ev=>{state.pmode=ev.target.value;render();});}
$("#clear").addEventListener("click",()=>{state.q="";state.mode={};state.pmode="hide";$$(".pmode input").forEach(i=>i.checked=i.value==="hide");$$(".mode input").forEach(i=>i.checked=i.value==="any");for(const k of FACETS)state[k].clear();$("#q").value="";$$("aside input[type=checkbox]").forEach(c=>c.checked=false);render();});
if(matchMedia("(max-width:640px)").matches)$$("aside details").forEach(d=>d.open=false);
if(matchMedia("(max-width:640px)").matches)$$("aside details").forEach(d=>d.open=false);
render();
})();
