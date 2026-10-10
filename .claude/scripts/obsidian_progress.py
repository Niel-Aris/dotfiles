#!/usr/bin/env python3
"""Write Pomodoro progress into a vault note.

usage: obsidian_progress.py FOLDER [--root DIR] [--vault DIR]

FOLDER is a vault folder such as Learning-C. The Pomodoro tag folder is found
by matching the name with '-', '_' and ' ' treated alike, so Learning-C matches
~/Pomodoro/Learning C. Only the block between the progress markers in
<vault>/<FOLDER>/Progress.md is rewritten; everything else is left as written.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

START = "<!-- progress:start -->"
END = "<!-- progress:end -->"
BAR_WIDTH = 20
HEAT_WEEKS = 52
PARTS_OF_DAY = [("Night (00-05)", 0, 5), ("Morning (05-12)", 5, 12),
                ("Afternoon (12-17)", 12, 17), ("Evening (17-24)", 17, 24)]


def norm(text):
    return re.sub(r"[\s_-]+", " ", text).strip().lower()


def fmt_hm(seconds):
    minutes = int(round(seconds / 60))
    return f"{minutes // 60}h {minutes % 60:02d}m"


def fmt_bar(value, peak):
    if peak <= 0 or value <= 0:
        return "░" * BAR_WIDTH
    filled = max(1, round(BAR_WIDTH * value / peak))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def find_tag_dir(root, folder):
    dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    matches = [p for p in dirs if norm(p.name) == norm(folder)]
    if len(matches) != 1:
        names = ", ".join(p.name for p in dirs) or "none"
        sys.exit(f"No single Pomodoro folder matches '{folder}' in {root} (found: {names}).")
    return matches[0]


def load(path):
    sessions, skipped = [], 0
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                sessions.append({
                    "start": datetime.fromisoformat(row["start"]),
                    "end": datetime.fromisoformat(row["end"]) if row.get("end") else None,
                    "seconds": int(row["seconds"]),
                    "ext": bool(row.get("ext")),
                })
            except (ValueError, KeyError, TypeError):
                skipped += 1
    sessions.sort(key=lambda s: s["start"])
    return sessions, skipped


def totals(daily_secs, daily_count, since, until):
    secs = sum(v for d, v in daily_secs.items() if since <= d <= until)
    count = sum(v for d, v in daily_count.items() if since <= d <= until)
    return secs, count


def summarize(sessions, today):
    daily_secs, daily_count = defaultdict(int), defaultdict(int)
    for s in sessions:
        d = s["start"].date()
        daily_secs[d] += s["seconds"]
        if not s["ext"]:
            daily_count[d] += 1
    monday = today - timedelta(days=today.weekday())
    starts = {
        "Today": today,
        "This week": monday,
        "This month": today.replace(day=1),
        "This year": today.replace(month=1, day=1),
        "All time": date.min,
    }
    periods = {name: totals(daily_secs, daily_count, since, today) for name, since in starts.items()}
    active = {d for d, secs in daily_secs.items() if secs > 0}
    streak = 0
    day = today if today in active else today - timedelta(days=1)
    while day in active:
        streak += 1
        day -= timedelta(days=1)
    longest = run = 0
    prev = None
    for d in sorted(active):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    best = max(active, key=lambda d: daily_secs[d]) if active else None
    return {"daily_secs": daily_secs, "daily_count": daily_count, "periods": periods,
            "active": active, "streak": streak, "longest": longest, "best": best}


def overview_lines(stats):
    lines = ["> [!tip] Overview", "> | Period | Time | Sessions | Avg / session |", "> |---|---:|---:|---:|"]
    for name, (secs, count) in stats["periods"].items():
        avg = fmt_hm(secs / count) if count else "—"
        lines.append(f"> | {name} | {fmt_hm(secs)} | {count} | {avg} |")
    return lines + [""]


def streak_lines(stats):
    best = stats["best"]
    best_text = f"**{best:%a %d %b %Y}** ({fmt_hm(stats['daily_secs'][best])})" if best else "—"
    return [
        "> [!abstract] Streak",
        f"> **{stats['streak']}** day(s) in a row · longest **{stats['longest']}** · "
        f"**{len(stats['active'])}** active days · best day {best_text}",
        "",
    ]


def heatmap_lines(daily_secs, today):
    monday = today - timedelta(days=today.weekday())
    first = monday - timedelta(weeks=HEAT_WEEKS - 1)

    def level(d):
        if d > today:
            return " "
        secs = daily_secs.get(d, 0)
        if secs <= 0:
            return "·"
        if secs < 3600:
            return "░"
        if secs < 7200:
            return "▒"
        if secs < 14400:
            return "▓"
        return "█"

    header = [" "] * (4 + 2 * HEAT_WEEKS)
    for col in range(HEAT_WEEKS):
        for k in range(7):
            d = first + timedelta(weeks=col, days=k)
            if d.day == 1:
                label = d.strftime("%b")
                pos = 4 + 2 * col
                if pos + len(label) <= len(header) and all(c == " " for c in header[pos:pos + len(label)]):
                    header[pos:pos + len(label)] = label
    lines = ["## Heatmap · last 52 weeks", "", "```text", "".join(header).rstrip()]
    names = ["Mon", "   ", "Wed", "   ", "Fri", "   ", "Sun"]
    for k in range(7):
        row = names[k] + " "
        for col in range(HEAT_WEEKS):
            row += level(first + timedelta(weeks=col, days=k)) + " "
        lines.append(row.rstrip())
    return lines + ["```", "", "· none   ░ under 1h   ▒ 1–2h   ▓ 2–4h   █ 4h+", ""]


def table_lines(title, label, rows):
    peak = max((secs for _, secs, _ in rows), default=0)
    lines = [title, "", f"| {label} | Time | Sessions | Progress |", "|---|---:|---:|---|"]
    for name, secs, count in rows:
        lines.append(f"| {name} | {fmt_hm(secs)} | {count} | `{fmt_bar(secs, peak)}` |")
    return lines + [""]


def period_rows(daily_secs, daily_count, today):
    weeks, days, months = [], [], []
    monday = today - timedelta(days=today.weekday())
    for i in range(12):
        start = monday - timedelta(weeks=i)
        secs, count = totals(daily_secs, daily_count, start, start + timedelta(days=6))
        weeks.append((f"{start:%Y-%m-%d}", secs, count))
    for i in range(14):
        d = today - timedelta(days=i)
        secs, count = totals(daily_secs, daily_count, d, d)
        days.append((f"{d:%a %d %b %Y}", secs, count))
    for m in range(1, today.month + 1):
        start = date(today.year, m, 1)
        end = (date(today.year + 1, 1, 1) if m == 12 else date(today.year, m + 1, 1)) - timedelta(days=1)
        secs, count = totals(daily_secs, daily_count, start, end)
        months.append((f"{start:%B}", secs, count))
    return weeks, days, months


def build_block(sessions, now, source):
    today = now.date()
    stats = summarize(sessions, today)
    lines = [f"_Last updated {now:%Y-%m-%d %H:%M} · source `{source}`_", ""]
    if not sessions:
        lines += ["> [!question] No sessions yet",
                  "> Log a work session tagged with this folder in the Pomodoro app, then run `/obsidian-progress`.", ""]
    lines += overview_lines(stats)
    if sessions:
        daily_secs, daily_count = stats["daily_secs"], stats["daily_count"]
        weeks, days, months = period_rows(daily_secs, daily_count, today)
        first_year = sessions[0]["start"].year
        years = []
        for y in range(first_year, today.year + 1):
            secs, count = totals(daily_secs, daily_count, date(y, 1, 1), date(y, 12, 31))
            years.append((str(y), secs, count))
        parts = []
        for name, lo, hi in PARTS_OF_DAY:
            secs = sum(s["seconds"] for s in sessions if not s["ext"] and lo <= s["start"].hour < hi)
            count = sum(1 for s in sessions if not s["ext"] and lo <= s["start"].hour < hi)
            parts.append((name, secs, count))
        log = [f"> [!example]- All sessions ({len(sessions)})",
               "> | Date | Start | End | Length | Kind |", "> |---|---|---|---:|---|"]
        for s in reversed(sessions):
            end_text = s["end"].strftime("%H:%M") if s["end"] else "—"
            kind = "extension" if s["ext"] else "session"
            log.append(f"> | {s['start']:%a %d %b %Y} | {s['start']:%H:%M} | {end_text} | "
                       f"{fmt_hm(s['seconds'])} | {kind} |")
        lines += streak_lines(stats)
        lines += heatmap_lines(daily_secs, today)
        lines += table_lines("## Weeks · last 12", "Week of", weeks)
        lines += table_lines("## Last 14 days", "Date", days)
        lines += table_lines(f"## Months · {today.year}", "Month", months)
        lines += table_lines("## Years", "Year", years)
        lines += table_lines("## When you focus", "Part of day", parts)
        lines += log + [""]
    return "\n".join(lines).rstrip() + "\n"


def update_note(path, folder, block):
    if not path.is_file():
        text = ("---\nproject: " + folder + "\ntags:\n  - learning\n  - progress\n---\n"
                "# Progress\n\n" + START + "\n" + block + END + "\n\n## My notes\n\n"
                "Write your own notes here. The script only rewrites the block between the markers.\n")
    else:
        old = path.read_text(encoding="utf-8")
        if START in old and END in old:
            head, rest = old.split(START, 1)
            tail = rest.split(END, 1)[1]
            text = head + START + "\n" + block + END + tail
        else:
            text = old.rstrip("\n") + "\n\n" + START + "\n" + block + END + "\n"
    path.write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--root", default=str(Path.home() / "Pomodoro"))
    ap.add_argument("--vault", default=str(Path.home() / "Documents/Lynux-System"))
    args = ap.parse_args()

    vault_folder = Path(args.vault) / args.folder
    if not vault_folder.is_dir():
        sys.exit(f"No vault folder {vault_folder}")
    tag_dir = find_tag_dir(Path(args.root), args.folder)
    sessions, skipped = load(tag_dir / "history.jsonl")
    block = build_block(sessions, datetime.now(), f"~/Pomodoro/{tag_dir.name}")
    note = vault_folder / "Progress.md"
    update_note(note, args.folder, block)
    total = sum(s["seconds"] for s in sessions)
    extra = f", {skipped} malformed line(s) skipped" if skipped else ""
    print(f"Updated {note}: {len(sessions)} record(s), {fmt_hm(total)} total{extra}")


if __name__ == "__main__":
    main()
