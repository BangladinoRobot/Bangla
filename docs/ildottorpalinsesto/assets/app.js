async function fetchJson(u){
  try{ const r = await fetch(u + "?t=" + Date.now()); if(!r.ok) return null; return await r.json(); }
  catch(e){ return null; }
}
function toArr(x){ if(!x) return []; if(Array.isArray(x)) return x; if(typeof x==="object") return Object.values(x); return []; }
function isUpcoming(iso){
  if(!iso) return false;
  const d = new Date(iso); if(isNaN(d.getTime())) return false;
  return d.getTime() >= Date.now() - 2*60*60*1000;
}
function fmtDate(iso){
  const d = new Date(iso); if(isNaN(d.getTime())) return "Data?";
  return d.toLocaleDateString("it-IT",{weekday:"short", day:"2-digit", month:"2-digit", year:"numeric"});
}
function fmtTime(iso){
  const d = new Date(iso); if(isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("it-IT",{hour:"2-digit", minute:"2-digit"});
}
function norm(s){ return (s||"").toString().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,""); }
function matchQuery(item,q){
  if(!q) return true;
  const hay = norm([
    item.league_country, item.league_name, item.home_name, item.away_name,
    item.home, item.away
  ].filter(Boolean).join(" "));
  return hay.includes(q);
}
function countLine(x){
  // se esistono breakdown separati, li usiamo, altrimenti mostriamo il totale combinato
  const h00 = x.home_0_0 ?? x.h00, h11 = x.home_1_1 ?? x.h11;
  const a00 = x.away_0_0 ?? x.a00, a11 = x.away_1_1 ?? x.a11;
  if([h00,h11,a00,a11].some(v=>typeof v==="number")){
    const th00 = (h00||0)+(a00||0), th11=(h11||0)+(a11||0);
    return `0-0: ${th00} • 1-1: ${th11} • Tot: ${th00+th11}/14`;
  }
  const tot = (typeof x.total_0_0_1_1==="number") ? x.total_0_0_1_1 : (x.total||0);
  return `Tot 0-0/1-1: ${tot}/14`;
}
function groupByDay(arr){
  const m = new Map();
  for(const x of arr){
    const key = (x.fixture_date||"").slice(0,10) || "????-??-??";
    if(!m.has(key)) m.set(key, []);
    m.get(key).push(x);
  }
  return [...m.entries()].sort((a,b)=>a[0].localeCompare(b[0]));
}
function el(tag, cls, html){
  const e = document.createElement(tag);
  if(cls) e.className = cls;
  if(html!==undefined) e.innerHTML = html;
  return e;
}
function renderRows(container, items, makeHref){
  container.innerHTML = "";
  if(!items.length){
    container.appendChild(el("div","muted","Nessuna partita trovata."));
    return;
  }
  const grouped = groupByDay(items);
  for(const [day, list] of grouped){
    const h = el("div","pill", fmtDate(day+"T00:00:00Z"));
    container.appendChild(h);
    const rows = el("div","rows");
    list.sort((a,b)=> (a.fixture_date||"").localeCompare(b.fixture_date||""));
    for(const x of list){
      const league = `${x.league_country||""}${x.league_country?" - ":""}${x.league_name||""}`.trim();
      const title = `${x.home_name||x.home||"Home"} vs ${x.away_name||x.away||"Away"}`;
      const meta = `${league} • ${fmtTime(x.fixture_date||"")}` + (x.passes_7_on_14===true ? ` • ${x.total_0_0_1_1}/14` : "");
      const a = el("a","row");
      a.href = makeHref(x);
      a.innerHTML = `
        <div class="row-top">
          <div class="row-title">⚽ ${title}</div>
          <div class="pill">${fmtTime(x.fixture_date||"")}</div>
        </div>
        <div class="row-meta">${meta}</div>
        <div class="row-meta">${countLine(x)}</div>
      `;
      rows.appendChild(a);
    }
    container.appendChild(rows);
    container.appendChild(el("div","hr"));
  }
}
