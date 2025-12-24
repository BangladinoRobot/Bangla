#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, json, html
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import requests
from zoneinfo import ZoneInfo

TZ_IT = ZoneInfo("Europe/Rome")
ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs" / "ildottorpalinsesto"

STATS_DOCS = DOCS / "stats_checked.json"
STATS_ROOT = ROOT / "stats_checked.json"
UPCOMING_DOCS = DOCS / "data" / "calendar_upcoming.json"
PASSED_DOCS = DOCS / "passed_fixtures_stats.json"

def _cfg_get(*names: str, default=None):
    try:
        import importlib
        cfg = importlib.import_module("config")
    except Exception:
        cfg = None
    for n in names:
        if cfg and hasattr(cfg, n):
            v = getattr(cfg, n)
            if v is not None and str(v).strip() != "":
                return v
    return default

BOT_TOKEN = _cfg_get("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", default="")
ALLOWED_CHAT_ID = _cfg_get("TELEGRAM_ALLOWED_CHAT_ID", "ALLOWED_CHAT_ID", default=None)
DASHBOARD_URL = _cfg_get("DASHBOARD_URL", default="https://bangladinorobot.github.io/Bangla/ildottorpalinsesto/index.html")

def _dash_base(url: str) -> str:
    u = (url or "").split("#", 1)[0].strip().rstrip("/")
    # se termina con .html, togli il file
    if u.endswith(".html"):
        u = u.rsplit("/", 1)[0]
    return u.rstrip("/")

DASH_BASE = _dash_base(DASHBOARD_URL)
FIXTURE_URL = f"{DASH_BASE}/fixture.html?id={{fid}}&src=tg"

BASE_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_call(method: str, params: Dict[str, Any], timeout=30):
    if not BOT_TOKEN:
        return None
    url = f"{BASE_API}/{method}"
    for attempt in range(3):
        try:
            r = requests.post(url, data=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(1 + attempt)
    return None

def tg_send(chat_id: int, text_html: str):
    return tg_call("sendMessage", {
        "chat_id": chat_id,
        "text": text_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    })

def _read_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore") or "")
    except Exception:
        pass
    return default

def load_stats_checked_dict() -> Dict[str, Any]:
    # preferisco docs (quello pubblicato), poi merge root come fallback
    d_docs = _read_json(STATS_DOCS, {})
    d_root = _read_json(STATS_ROOT, {})
    out = {}
    if isinstance(d_root, dict):
        out.update(d_root)
    if isinstance(d_docs, dict):
        out.update(d_docs)
    return out if isinstance(out, dict) else {}

def load_upcoming_list() -> List[Dict[str, Any]]:
    d = _read_json(UPCOMING_DOCS, [])
    return d if isinstance(d, list) else []

def parse_dt_any(s: Any) -> Optional[datetime]:
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def pick_score(e: Dict[str, Any]) -> Tuple[str, str, str]:
    # ritorna (score, mark, status_short)
    st = (e.get("ft_status") or e.get("status_short") or e.get("fixture_status_short") or "").toString().strip() if hasattr(str, "toString") else str((e.get("ft_status") or e.get("status_short") or e.get("fixture_status_short") or "")).strip()
    # prefer ft_score, altrimenti ft_home/ft_away o goals_*
    h = e.get("ft_home", None)
    a = e.get("ft_away", None)
    if h is None or a is None:
        h = e.get("goals_home", h)
        a = e.get("goals_away", a)
    score = (e.get("ft_score") or "").strip()
    if not score and (h is not None and a is not None):
        try:
            score = f"{int(h)}-{int(a)}"
        except Exception:
            score = f"{h}-{a}"
    mark = (e.get("ft_mark") or "").strip()
    if not mark and score:
        mark = "✅" if score.strip() == "0-0" else "❌"
    return score, mark, st

def _passes(e: Dict[str, Any]) -> bool:
    return (e.get("passes_7_on_14") is True) or (e.get("passes_7on14") is True)

def build_results_day(entries: List[Dict[str, Any]], day_start_it: datetime, day_end_it: datetime) -> List[Tuple[int, str, str, str]]:
    # ritorna [(fid, "HOME - AWAY", score_or_ND, mark)]
    start_utc = day_start_it.astimezone(timezone.utc)
    end_utc = day_end_it.astimezone(timezone.utc)
    rows = []
    for e in entries:
        if not isinstance(e, dict) or not _passes(e):
            continue
        dt = parse_dt_any(e.get("fixture_date") or e.get("date"))
        if not dt or not (start_utc <= dt < end_utc):
            continue

        score, mark, st = pick_score(e)

        # IMPORTANT: per evitare “ieri ma in realtà gioca oggi” -> considero solo FINITE
        finished = (st == "FT") or bool(score)
        if not finished:
            continue

        try:
            fid = int(e.get("fixture_id") or e.get("id") or 0)
        except Exception:
            fid = 0
        home = (e.get("home_name") or "").strip()
        away = (e.get("away_name") or "").strip()
        name = f"{home} - {away}".strip(" -")
        s = score.strip() if score else "N/D"
        m = "✅" if s == "0-0" else "❌"
        rows.append((dt.astimezone(TZ_IT), fid, name, s, m))
    rows.sort(key=lambda r: r[0])  # cronologico
    out = [(fid, name, s, m) for (_, fid, name, s, m) in rows]
    return out

def fmt_results(title: str, rows: List[Tuple[int, str, str, str]]) -> str:
    # rows: (fid, name, score, mark)
    out = [html.escape(title), ""]
    n = len(rows)
    prese = sum(1 for (_, _, score, _) in rows if str(score).strip() == "0-0")
    out.append(f"Prese {prese} su {n}:")
    if n == 0:
        out.append("Nessuna partita.")
        return "\n".join(out)
    for fid, name, score, mark in rows:
        link = FIXTURE_URL.format(fid=fid) if fid else ""
        team = f'<a href="{html.escape(link)}">{html.escape(name)}</a>' if link else html.escape(name)
        out.append(f"{mark} {html.escape(str(score))} • {team}")
    return "\n".join(out)

def build_upcoming_day(upcoming: List[Dict[str, Any]], day_start_it: datetime, day_end_it: datetime) -> List[Tuple[str, int, str]]:
    # ritorna [(HH:MM, fid, "HOME - AWAY")] ordinato
    start_utc = day_start_it.astimezone(timezone.utc)
    end_utc = day_end_it.astimezone(timezone.utc)
    rows = []
    for it in upcoming:
        if not isinstance(it, dict):
            continue
        if not _passes(it):
            continue
        dt = parse_dt_any(it.get("fixture_date") or it.get("date"))
        if not dt or not (start_utc <= dt < end_utc):
            continue
        dt_it = dt.astimezone(TZ_IT)
        t = dt_it.strftime("%H:%M")
        try:
            fid = int(it.get("fixture_id") or it.get("id") or 0)
        except Exception:
            fid = 0
        home = (it.get("home_name") or "").strip()
        away = (it.get("away_name") or "").strip()
        name = f"{home} - {away}".strip(" -")
        rows.append((dt_it, t, fid, name))
    rows.sort(key=lambda r: r[0])
    return [(t, fid, name) for (_, t, fid, name) in rows]

def fmt_upcoming(title: str, rows: List[Tuple[str, int, str]]) -> str:
    out = [html.escape(title), ""]
    if not rows:
        out.append("Nessuna partita.")
        return "\n".join(out)

    cur = None
    for t, fid, name in rows:
        if t != cur:
            if cur is not None:
                out.append("")  # riga vuota tra blocchi orario
            out.append(html.escape(t))
            cur = t
        link = FIXTURE_URL.format(fid=fid) if fid else ""
        team = f'<a href="{html.escape(link)}">{html.escape(name)}</a>' if link else html.escape(name)
        out.append(f"• {team}")
    return "\n".join(out)

def _midnight_it(dt_it: datetime) -> datetime:
    return dt_it.replace(hour=0, minute=0, second=0, microsecond=0)

def handle_command(chat_id: int, text: str):
    parts = (text or "").strip().split()
    cmd = parts[0] if parts else ""
    cmd = cmd.split("@", 1)[0]  # /domani@BotName
    arg = parts[1] if len(parts) > 1 else None

    if cmd == "/help":
        tg_send(chat_id, "Comandi:\n/ieri\n/oggi\n/domani\n/check [ore]\n/help")
        return

    reg = load_stats_checked_dict()
    entries = list(reg.values()) if isinstance(reg, dict) else []
    now_it = datetime.now(TZ_IT)

    if cmd == "/ieri":
        end_it = _midnight_it(now_it)
        start_it = end_it - timedelta(days=1)
        rows = build_results_day(entries, start_it, end_it)
        title = f"Partite di ieri ({start_it.strftime('%d/%m/%y')})"
        tg_send(chat_id, fmt_results(title, rows))
        return

    if cmd == "/oggi":
        start_it = _midnight_it(now_it)
        end_it = start_it + timedelta(days=1)
        rows = build_results_day(entries, start_it, end_it)
        title = f"Partite di oggi ({start_it.strftime('%d/%m/%y')})"
        tg_send(chat_id, fmt_results(title, rows))
        return

    if cmd == "/domani":
        start_it = _midnight_it(now_it) + timedelta(days=1)
        end_it = start_it + timedelta(days=1)
        upcoming = load_upcoming_list()
        rows = build_upcoming_day(upcoming, start_it, end_it)
        title = f"Partite di domani ({start_it.strftime('%d/%m/%y')})"
        tg_send(chat_id, fmt_upcoming(title, rows))
        return

    if cmd == "/check":
        hours = 48
        if arg:
            try:
                hours = int(arg)
            except Exception:
                hours = 48
        if hours < 1: hours = 1
        if hours > 168: hours = 168
        end_it = _midnight_it(now_it) + timedelta(days=1)
        start_it = end_it - timedelta(hours=hours)
        rows = build_results_day(entries, start_it, end_it)
        title = f"Check ultime {hours} ore (fino a {now_it.strftime('%d/%m/%y %H:%M')})"
        tg_send(chat_id, fmt_results(title, rows))
        return

    tg_send(chat_id, "Comando non riconosciuto\nElenco comandi ➡️ /help")

def main():
    if not BOT_TOKEN:
        print("ERRORE: manca TELEGRAM_BOT_TOKEN (config.py).")
        return 1
    offset = 0
    print("✅  Bot avviato. In ascolto...")
    while True:
        j = tg_call("getUpdates", {"timeout": 50, "offset": offset}, timeout=60)
        if not j or not j.get("ok"):
            time.sleep(2)
            continue
        for upd in j.get("result", []):
            offset = int(upd.get("update_id", 0)) + 1
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = msg.get("chat") or {}
            chat_id = chat.get("id")
            text = msg.get("text") or ""
            if not chat_id:
                continue
            try:
                chat_id = int(chat_id)
            except Exception:
                continue
            if ALLOWED_CHAT_ID is not None:
                try:
                    if int(ALLOWED_CHAT_ID) != chat_id:
                        continue
                except Exception:
                    pass
            if text.startswith("/"):
                handle_command(chat_id, text)
        time.sleep(0.2)

if __name__ == "__main__":
    raise SystemExit(main())
