#!/usr/bin/env bash
set -euo pipefail

ts="$(date +%Y%m%d_%H%M%S)"
echo "==> Backup: $ts"
mkdir -p "backups/$ts"
cp -a docs/ildottorpalinsesto "backups/$ts/docs_ildottorpalinsesto" 2>/dev/null || true
cp -a ildottorpalinsesto "backups/$ts/ildottorpalinsesto" 2>/dev/null || true

# Dove scrivere (entrambe le copie)
TARGETS=("docs/ildottorpalinsesto" "ildottorpalinsesto")
for d in "${TARGETS[@]}"; do
  mkdir -p "$d/assets"
done

# ---------- Helper: header+topbar uniformi ----------
read -r -d '' HEAD <<'HTML'
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Il Dottor Palinsesto</title>

  <!-- SOCCER_THEME_V1 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/theme.css">

  <style>
    /* UI_ENHANCE_V1 (solo per layout pagine nuove) */
    .subhead{margin-top:12px}
    .grid-2{
      display:grid;
      grid-template-columns:1fr;
      gap:12px;
      margin-top:12px;
    }
    @media(min-width:360px){
      .grid-2{grid-template-columns:1fr 1fr;}
    }
    .chip{
      display:inline-flex; align-items:center; gap:8px;
      padding:7px 10px;
      border-radius:999px;
      border:1px solid var(--border);
      background:rgba(255,255,255,.06);
      color:var(--muted);
      font-weight:800;
      font-size:12px;
    }
    .row{
      display:flex; flex-direction:column; gap:6px;
      padding:12px;
      border-radius:16px;
      border:1px solid var(--border);
      background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
    }
    a.row{display:block; text-decoration:none}
    a.row:hover{text-decoration:none}
    .row-top{display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap}
    .row-title{font-weight:900}
    .row-meta{color:var(--muted); font-size:12px}
    .rows{display:grid; gap:10px; margin-top:12px}
    .tabs{display:flex; gap:10px; flex-wrap:wrap; margin-top:12px}
    .tab{padding:8px 10px; border-radius:12px; border:1px solid var(--border); background:rgba(255,255,255,.06); font-weight:900}
    .tab.active{background:rgba(34,197,94,.20); border-color:rgba(34,197,94,.35)}
    .right{margin-left:auto}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <div class="brand-badge">⚽</div>
        <div>
          <div style="font-size:14px;opacity:.85;font-weight:900">Il Dottor Palinsesto</div>
          <div class="muted" style="font-size:12px">Dashboard filtri — tema calcio</div>
        </div>
      </div>
      <div class="right" style="display:flex; gap:10px; flex-wrap:wrap">
        <a class="btn" href="campionati.html">Campionati</a>
        <a class="btn" href="archivio.html">Archivio</a>
      </div>
    </div>
HTML

read -r -d '' FOOT <<'HTML'
    <div class="hr"></div>
    <div class="muted" style="font-size:12px">
      Dati letti dai file JSON salvati dal bot (nessuna chiamata API dal sito).
    </div>
  </div>

<script>
/* DATA_LOADER_V1
   Primo filtro: stats_checked.json (passes_7_on_14 == true)
   Secondo filtro: passed_fixtures_stats.json (se presente)
*/
function parseJsonMaybe(t){ try{return JSON.parse(t);}catch(e){return null;} }

async function fetchJson(url){
  try{
    const r = await fetch(url + "?t=" + Date.now());
    if(!r.ok) return null;
    return await r.json();
  }catch(e){ return null; }
}

function toArrayFromAny(obj){
  if(!obj) return [];
  if(Array.isArray(obj)) return obj;
  // dict keyed by fixture_id -> value
  if(typeof obj === "object") return Object.values(obj);
  return [];
}

function isUpcoming(iso){
  if(!iso) return false;
  const d = new Date(iso);
  if(isNaN(d.getTime())) return false;
  return d.getTime() >= Date.now() - 2*60*60*1000; // tolleranza 2h
}

function fmtDate(iso){
  try{
    const d = new Date(iso);
    return d.toLocaleString("it-IT",{weekday:"short", day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit"});
  }catch(e){ return iso; }
}

function groupBy(arr, keyFn){
  const m = new Map();
  for(const x of arr){
    const k = keyFn(x) || "Altro";
    if(!m.has(k)) m.set(k, []);
    m.get(k).push(x);
  }
  return m;
}

function leagueLabel(x){
  const c = x.league_country ? (x.league_country + " - ") : "";
  const n = x.league_name || "Campionato";
  return c + n;
}

function matchLabel(x){
  const h = x.home_name || x.homeTeam || x.home || "Home";
  const a = x.away_name || x.awayTeam || x.away || "Away";
  return h + " vs " + a;
}

async function loadAll(){
  const statsChecked = await fetchJson("stats_checked.json");
  const passedSecond = await fetchJson("passed_fixtures_stats.json");

  const allChecked = toArrayFromAny(statsChecked);

  const firstAll = allChecked.filter(x => x && x.passes_7_on_14 === true);
  const firstUpcoming = firstAll.filter(x => isUpcoming(x.fixture_date));

  const secondAll = toArrayFromAny(passedSecond);
  const secondUpcoming = secondAll.filter(x => isUpcoming(x.fixture_date));

  return { firstAll, firstUpcoming, secondAll, secondUpcoming, allChecked };
}

function setText(id, v){
  const el = document.getElementById(id);
  if(el) el.textContent = String(v);
}

window.__DATA__ = null;
window.addEventListener("DOMContentLoaded", async ()=>{
  window.__DATA__ = await loadAll();

  setText("kpi_first", window.__DATA__.firstUpcoming.length);
  setText("kpi_second", window.__DATA__.secondUpcoming.length);

  // campionati: conteggio unici (solo upcoming)
  const leagues1 = new Set(window.__DATA__.firstUpcoming.map(leagueLabel));
  const leagues2 = new Set(window.__DATA__.secondUpcoming.map(leagueLabel));
  setText("kpi_leagues1", leagues1.size);
  setText("kpi_leagues2", leagues2.size);

  // ultimo aggiornamento (se presente in stats_summary.json, altrimenti usa ora)
  const sum = await fetchJson("stats_summary.json");
  const ts = sum && (sum.updated_at || sum.last_update || sum.ts || sum.generated_at);
  setText("updated_at", ts ? ts : new Date().toLocaleString("it-IT"));
});
</script>

</body>
</html>
HTML

# ---------- 1) HOME: due card affiancate + niente lista campionati ----------
read -r -d '' HOME_BODY <<'HTML'
    <div class="subhead">
      <div class="pill">Ultimo aggiornamento: <span id="updated_at">...</span></div>
    </div>

    <div class="grid-2">
      <a class="card card-clickable" href="primo-filtro.html" style="text-decoration:none">
        <div class="chip">Primo filtro</div>
        <div class="kpi" id="kpi_first">0</div>
        <div class="label">Partite (ancora da giocare) che passano 7/14 (0-0 o 1-1)</div>
        <div class="hint">Tocca per vedere l’elenco e i dettagli</div>
      </a>

      <a class="card card-clickable" href="secondo-filtro.html" style="text-decoration:none">
        <div class="chip">Secondo filtro</div>
        <div class="kpi" id="kpi_second">0</div>
        <div class="label">Partite (ancora da giocare) che passano il filtro quote</div>
        <div class="hint">Tocca per vedere l’elenco e i dettagli</div>
      </a>
    </div>

    <div class="cards" style="margin-top:12px">
      <a class="card card-clickable" href="campionati.html" style="text-decoration:none">
        <div class="chip">Campionati</div>
        <div style="display:flex; gap:16px; flex-wrap:wrap; margin-top:6px">
          <div>
            <div class="kpi" style="font-size:26px" id="kpi_leagues1">0</div>
            <div class="label">campionati nel Primo filtro (upcoming)</div>
          </div>
          <div>
            <div class="kpi" style="font-size:26px" id="kpi_leagues2">0</div>
            <div class="label">campionati nel Secondo filtro (upcoming)</div>
          </div>
        </div>
        <div class="hint">La lista NON è in home: è nella pagina dedicata.</div>
      </a>
    </div>
HTML

# ---------- 2) PAGINA LISTA FILTRO (template unico con JS che cambia sorgente) ----------
read -r -d '' LIST_PAGE <<'HTML'
    <div class="subhead">
      <div class="pill" id="page_pill">...</div>
    </div>

    <div class="tabs">
      <a class="tab" id="tab_upcoming" href="#">Da giocare</a>
      <a class="tab" id="tab_all" href="#">Archivio (tutte)</a>
      <a class="btn" href="campionati.html">Campionati</a>
      <a class="btn" href="archivio.html">Archivio completo</a>
    </div>

    <div class="rows" id="rows"></div>

<script>
/* LIST_RENDER_V1 */
function getParam(name){
  const u = new URL(location.href);
  return u.searchParams.get(name);
}
function setActive(el){ if(el) el.classList.add("active"); }

function renderRows(arr, title){
  const root = document.getElementById("rows");
  root.innerHTML = "";
  if(!arr || arr.length === 0){
    root.innerHTML = '<div class="card"><div class="label">Nessuna partita trovata.</div></div>';
    return;
  }

  // group by date (YYYY-MM-DD)
  const groups = new Map();
  for(const x of arr){
    const iso = x.fixture_date || "";
    const day = (iso.slice(0,10) || "Data sconosciuta");
    if(!groups.has(day)) groups.set(day, []);
    groups.get(day).push(x);
  }

  const days = Array.from(groups.keys()).sort();
  for(const day of days){
    const sec = document.createElement("div");
    sec.className = "card";
    sec.innerHTML = '<h3 style="margin-bottom:10px">📅 ' + day + '</h3>';
    const inner = document.createElement("div");
    inner.className = "rows";

    for(const x of groups.get(day)){
      const fid = x.fixture_id || x.id || x.fixtureId;
      const href = "dettaglio.html?fixture_id=" + encodeURIComponent(fid);

      const league = (x.league_country ? (x.league_country + " - ") : "") + (x.league_name || "Campionato");
      const when = x.fixture_date ? (new Date(x.fixture_date)).toLocaleString("it-IT",{weekday:"short", day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit"}) : "";

      const h00 = (x.home_0_0_1_1 ?? "");
      const a00 = (x.away_0_0_1_1 ?? "");
      const tot = (x.total_0_0_1_1 ?? "");
      const score = (tot !== "" ? (tot + "/14") : "");

      const row = document.createElement("a");
      row.className = "row";
      row.href = href;

      row.innerHTML = `
        <div class="row-top">
          <div class="row-title">⚽ ${x.home_name || "Home"} vs ${x.away_name || "Away"}</div>
          <div class="pill">${score}</div>
        </div>
        <div class="row-meta">🏟 ${league} • 🕒 ${when}</div>
        <div class="muted" style="font-size:12px">
          Home: ${h00} su 7 • Away: ${a00} su 7 • Totale: ${tot} su 14
        </div>
      `;
      inner.appendChild(row);
    }

    sec.appendChild(inner);
    root.appendChild(sec);
  }
}

window.addEventListener("DOMContentLoaded", async ()=>{
  const which = document.body.getAttribute("data-which") || "first"; // first|second
  const mode = getParam("mode") || "upcoming"; // upcoming|all

  const tabUpcoming = document.getElementById("tab_upcoming");
  const tabAll = document.getElementById("tab_all");
  tabUpcoming.href = location.pathname + "?mode=upcoming";
  tabAll.href = location.pathname + "?mode=all";

  if(mode === "all") setActive(tabAll); else setActive(tabUpcoming);

  // usa i dati già caricati dal FOOT (window.__DATA__)
  const d = window.__DATA__ || await (async()=>{ return await (await fetch(location.pathname.replace(/[^/]+$/,"") + "index.html")).text(); })();

  const data = window.__DATA__;
  const pill = document.getElementById("page_pill");

  let arr = [];
  if(which === "first"){
    pill.textContent = "Primo filtro — " + (mode==="all" ? "Archivio" : "Da giocare");
    arr = (mode==="all") ? data.firstAll : data.firstUpcoming;
  }else{
    pill.textContent = "Secondo filtro — " + (mode==="all" ? "Archivio" : "Da giocare");
    arr = (mode==="all") ? data.secondAll : data.secondUpcoming;
  }

  // ordina per data
  arr = (arr||[]).slice().sort((a,b)=> (a.fixture_date||"").localeCompare(b.fixture_date||""));
  renderRows(arr);
});
</script>
HTML

# ---------- 3) PAGINA CAMPIONATI (cliccabili) ----------
read -r -d '' LEAGUES_PAGE <<'HTML'
    <div class="subhead">
      <div class="pill">Campionati (cliccabili)</div>
    </div>

    <div class="tabs">
      <a class="tab active" id="tab_l1" href="#">Primo filtro</a>
      <a class="tab" id="tab_l2" href="#">Secondo filtro</a>
      <a class="btn" href="primo-filtro.html">Partite (F1)</a>
      <a class="btn" href="secondo-filtro.html">Partite (F2)</a>
    </div>

    <div class="rows" id="leagues"></div>

<script>
function leagueLabel(x){
  const c = x.league_country ? (x.league_country + " - ") : "";
  const n = x.league_name || "Campionato";
  return c + n;
}

function renderLeagueList(arr, which){
  const root = document.getElementById("leagues");
  root.innerHTML = "";
  const m = new Map();
  for(const x of arr){
    const name = leagueLabel(x);
    if(!m.has(name)) m.set(name, []);
    m.get(name).push(x);
  }
  const names = Array.from(m.keys()).sort();

  if(names.length === 0){
    root.innerHTML = '<div class="card"><div class="label">Nessun campionato trovato.</div></div>';
    return;
  }

  for(const name of names){
    const count = m.get(name).length;
    const link = (which==="first" ? "primo-filtro.html" : "secondo-filtro.html");
    // filtro per campionato via query (semplice contains)
    const href = link + "?mode=upcoming&league=" + encodeURIComponent(name);

    const row = document.createElement("a");
    row.className = "row";
    row.href = href;
    row.innerHTML = `
      <div class="row-top">
        <div class="row-title">🏟 ${name}</div>
        <div class="pill">${count} partite</div>
      </div>
      <div class="row-meta">Tocca per aprire l’elenco partite di questo campionato</div>
    `;
    root.appendChild(row);
  }
}

window.addEventListener("DOMContentLoaded", ()=>{
  const tab1 = document.getElementById("tab_l1");
  const tab2 = document.getElementById("tab_l2");

  function show(which){
    tab1.classList.toggle("active", which==="first");
    tab2.classList.toggle("active", which==="second");
    const data = window.__DATA__;
    const arr = (which==="first") ? data.firstUpcoming : data.secondUpcoming;
    renderLeagueList(arr, which);
  }

  tab1.addEventListener("click", (e)=>{e.preventDefault(); show("first");});
  tab2.addEventListener("click", (e)=>{e.preventDefault(); show("second");});
  show("first");
});
</script>
HTML

# ---------- 4) DETTAGLIO PARTITA (cliccando riga/card) ----------
read -r -d '' DETAIL_PAGE <<'HTML'
    <div class="subhead">
      <div class="pill">Dettaglio partita</div>
    </div>

    <div class="cards">
      <div class="card" id="detail_card">
        <div class="label">Carico i dati…</div>
      </div>
      <a class="btn" href="javascript:history.back()">← Indietro</a>
    </div>

<script>
function getParam(name){
  const u = new URL(location.href);
  return u.searchParams.get(name);
}
function esc(s){ return String(s||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;"); }

window.addEventListener("DOMContentLoaded", ()=>{
  const fid = getParam("fixture_id");
  const box = document.getElementById("detail_card");
  const data = window.__DATA__;

  if(!fid){
    box.innerHTML = "<div class='label'>fixture_id mancante.</div>";
    return;
  }

  const all = (data.allChecked || []);
  const x = all.find(v => String(v.fixture_id) === String(fid)) || null;

  if(!x){
    box.innerHTML = "<div class='label'>Partita non trovata in stats_checked.json (forse è solo nel secondo filtro).</div>";
    return;
  }

  const league = (x.league_country ? (x.league_country + " - ") : "") + (x.league_name || "Campionato");
  const when = x.fixture_date ? (new Date(x.fixture_date)).toLocaleString("it-IT",{weekday:"long", day:"2-digit", month:"long", hour:"2-digit", minute:"2-digit"}) : "";

  box.innerHTML = `
    <h2 style="margin-bottom:6px">⚽ ${esc(x.home_name)} vs ${esc(x.away_name)}</h2>
    <div class="muted">🏟 ${esc(league)} • 🕒 ${esc(when)}</div>

    <div class="hr"></div>

    <div class="pill">Primo filtro (7/14): ${x.passes_7_on_14 ? "✅ Passa" : "❌ Non passa"}</div>
    <div style="margin-top:10px" class="muted">
      Home: ${esc(x.home_0_0_1_1)} su 7 • Away: ${esc(x.away_0_0_1_1)} su 7 • Totale: <b>${esc(x.total_0_0_1_1)} su 14</b>
    </div>

    <div class="hr"></div>
    <div class="label">Quote e risultati: predisposti (li aggiungiamo dopo).</div>
  `;
});
</script>
HTML

# ---------- 5) ARCHIVIO (placeholder minimale, poi lo estendiamo) ----------
read -r -d '' ARCHIVE_PAGE <<'HTML'
    <div class="subhead">
      <div class="pill">Archivio completo</div>
    </div>

    <div class="cards">
      <a class="card card-clickable" href="primo-filtro.html?mode=all" style="text-decoration:none">
        <div class="chip">Archivio Primo filtro</div>
        <div class="label">Tutte le partite che hanno passato il Primo filtro (storico)</div>
      </a>

      <a class="card card-clickable" href="secondo-filtro.html?mode=all" style="text-decoration:none">
        <div class="chip">Archivio Secondo filtro</div>
        <div class="label">Tutte le partite che hanno passato il Secondo filtro (storico)</div>
      </a>
    </div>
HTML

# Scrittura file su entrambe le cartelle
write_page () {
  local file="$1"
  local body="$2"
  for d in "${TARGETS[@]}"; do
    cat > "$d/$file" <<EOF
$HEAD
$body
$FOOT
EOF
  done
}

write_page "index.html"         "$HOME_BODY"
write_page "primo-filtro.html"  "$(printf '%s' "$LIST_PAGE")"
write_page "secondo-filtro.html" "$(printf '%s' "$LIST_PAGE")"
write_page "campionati.html"    "$LEAGUES_PAGE"
write_page "dettaglio.html"     "$DETAIL_PAGE"
write_page "archivio.html"      "$ARCHIVE_PAGE"

# Set attributo data-which nelle pagine filtro (così il JS sa cosa mostrare)
python3 - <<'PY'
from pathlib import Path

targets = [Path("docs/ildottorpalinsesto"), Path("ildottorpalinsesto")]
for base in targets:
    for name, which in [("primo-filtro.html","first"), ("secondo-filtro.html","second")]:
        p = base / name
        if not p.exists(): 
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        txt = txt.replace("<body>", f"<body data-which=\"{which}\">", 1)
        p.write_text(txt, encoding="utf-8")
print("OK: data-which impostato")
PY

echo "==> OK: nuove pagine create (home + filtri + campionati + dettaglio + archivio)"
echo "==> NOTE: i JSON devono essere pubblicati nella stessa cartella (stats_checked.json, passed_fixtures_stats.json, stats_summary.json)"
