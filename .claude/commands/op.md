---
description: "Model-Workflow: status | checkpoint | batch | ask <agent> <q> | mode <m> | quiz [topic] | fade <concept> up|down | handle <name> | lint"
argument-hint: "[status|checkpoint|batch|ask|mode|quiz|fade|handle|lint] ..."
---

Load the `model-workflow` skill if it isn't loaded yet. The helper is `mw` (a wrapper in `~/.local/bin`; if it's missing, use `python3 -I ~/.claude/scripts/mw.py`).

Arguments: $ARGUMENTS

Route on the first word. If it's empty, use `status`.

- **status**: run `mw status` and show the result. Then add one line on what this agent is doing now, from your Card, and list due reviews or open inbox items.
- **checkpoint**: spawn the **mw-clerk** sub-agent with "checkpoint <your agent name>" and the repo path. Relay its 2–3-line result, then re-read your Card.
- **batch**: Model mode. Finish the current batch: steps 3–6 of `model.md` (test, commit, Scribe, check, close). If no batch is in progress, start step 1 and plan the next one.
- **ask <agent> <question>**: run the ask ladder from the skill (section 4) on that agent. Use mw-clerk for steps 2–3. Give the answer with its sources. If the notes can't answer, offer the inbox.
- **mode <learn|build|model>**: run `mw register --mode <m>`, journal it as `note`, read the new mode file, and confirm in one line.
- **quiz [topic]**: 3–5 retrieval questions. Use concepts due for review (`mw learner show --due`), then never-checked ones (`mw learner show --unchecked`), or the given topic. Ask one at a time. Grade each with `mw learner check`, and journal the result as `learner`.
- **fade <concept> up|down**: read the current fade from `mw learner known`, then set it one step up or down with `mw learner set "<concept>" --fade <n>`. Confirm the new level and what it changes.
- **handle <words>**: run `mw handle <words>` and show the file:line, the symbol, and a link to the Pattern note.
- **lint**: run `mw lint --write`. If it reports issues, offer to have mw-clerk fix the safe ones.
