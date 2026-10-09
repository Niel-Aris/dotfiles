"""Storage + stats for the pomodoro app (no GUI imports, so the CLI stays fast).

Layout:
    ~/Pomodoro/<tag>/history.jsonl   one JSON object per finished work session
    ~/.config/pomodoro/config.json   timer settings
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("POMODORO_DIR", Path.home() / "Pomodoro"))
CONFIG_FILE = Path.home() / ".config" / "pomodoro" / "config.json"
HISTORY = "history.jsonl"

DEFAULT_CONFIG = {
    "work_min": 25,
    "short_break_min": 5,
    "long_break_min": 15,
    "sessions_before_long": 4,
    "extend_min": 5,
    "sound": True,
    "last_tag": "General",
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text()))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def safe_name(tag):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", tag.strip()).strip(". ")


def list_tags():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tags = sorted((p.name for p in DATA_DIR.iterdir() if p.is_dir()), key=str.lower)
    if not tags:
        add_tag("General")
        tags = ["General"]
    return tags


def add_tag(tag):
    name = safe_name(tag)
    if not name:
        return None
    (DATA_DIR / name).mkdir(parents=True, exist_ok=True)
    return name


def log_session(tag, start, end, seconds, ext=False):
    """Append a work segment. start/end are datetimes; ext marks an extension
    of a previous session (counts toward time, not toward the session count)."""
    folder = DATA_DIR / (add_tag(tag) or "General")
    folder.mkdir(parents=True, exist_ok=True)
    rec = {
        "start": start.isoformat(timespec="seconds"),
        "end": end.isoformat(timespec="seconds"),
        "seconds": int(seconds),
    }
    if ext:
        rec["ext"] = True
    with open(folder / HISTORY, "a") as f:
        f.write(json.dumps(rec) + "\n")


def read_sessions(tag):
    path = DATA_DIR / tag / HISTORY
    out = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    out.append((datetime.fromisoformat(r["start"]), int(r["seconds"]), bool(r.get("ext"))))
                except (ValueError, KeyError):
                    continue
    except OSError:
        pass
    return out


def period_start(period, now=None):
    now = now or datetime.now()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return day - timedelta(days=day.weekday())  # Monday
    if period == "month":
        return day.replace(day=1)
    if period == "year":
        return day.replace(month=1, day=1)
    raise ValueError(period)


def totals(tag):
    """Seconds + session count for this week/month/year (calendar periods)."""
    now = datetime.now()
    starts = {p: period_start(p, now) for p in ("week", "month", "year")}
    res = {p: [0, 0] for p in starts}
    for start, secs, ext in read_sessions(tag):
        for p, s in starts.items():
            if start >= s:
                res[p][0] += secs
                res[p][1] += 0 if ext else 1
    return {p: tuple(v) for p, v in res.items()}


def by_day(tag, since):
    days = {}
    for start, secs, _ext in read_sessions(tag):
        if start >= since:
            d = start.date()
            days[d] = days.get(d, 0) + secs
    return days


def fmt_hm(seconds):
    m = int(round(seconds / 60))
    return f"{m // 60}h {m % 60:02d}m"
