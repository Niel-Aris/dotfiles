---
description: Update <vault folder>/Progress.md with Pomodoro history (daily, weekly, monthly, yearly, sessions)
argument-hint: <vault folder, e.g. Learning-C>
---

Update the progress note for the vault folder `$ARGUMENTS`.

Run this one command and report its output line. Don't read, edit, or summarise the note; the script rewrites only the block between its markers:

`python3 -I ~/.claude/scripts/obsidian_progress.py "$ARGUMENTS"`

The Pomodoro folder is found by name, with `-` and spaces treated alike, so `Learning-C` reads `~/Pomodoro/Learning C/history.jsonl`. If the script exits with an error, show the error and stop.
