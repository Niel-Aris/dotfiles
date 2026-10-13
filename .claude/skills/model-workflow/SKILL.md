---
name: model-workflow
description: Shared-memory agent protocol for Model-Workflow Operations. A Superset project is an Operation, and each workspace is an agent that keeps a Card and a Journal in the Obsidian vault and reads its siblings' Cards when it needs them. Load at the start of any session whose context contains a <model-workflow> block or whose repo has a .mw.json file, and whenever the user runs /op.
---

# Model-Workflow protocol

You are one agent in an **Operation**: a git repo whose memory lives in an Obsidian vault, outside every branch. The SessionStart hook already gave you your identity, the Operation brief and roster, your Card, a learner snapshot, and any inbox questions. Don't re-read those files unless you need a part the hook didn't show.

Paths: `.op/` is this Operation's vault folder. The global learner model is `<vault>/Me/Learner.md`, and global concept notes are `<vault>/Concepts/`. The helper is `mw` (a wrapper in `~/.local/bin`; if it's missing, use `python3 -I ~/.claude/scripts/mw.py`). `mw learner set/check` refuses concept names it doesn't know, which catches typos; pass `--new` for a concept that really is new.

## 1. Read your mode file

Your mode is in the context block. Read the matching file in this skill's directory before your first substantive reply:

- `model` → [model.md](model.md): you build in batches and teach as you go. This is the main workflow.
- `learn` → [learn.md](learn.md): education only. Challenges and hints, no solution code.
- `build` → [build.md](build.md): plain agentic coding with light documentation.

The user can switch modes with `/op mode <mode>`.

## 2. Journal every exchange

After each exchange, append 1–3 short lines: `mw journal <kind> "text"`.

| kind | when |
|---|---|
| `asked` | the user asked something; record the gist |
| `taught` | you explained a concept; name it and say what you emphasised |
| `built` | you changed code; give the batch id, files, and the commit |
| `decided` | a choice was made; say what was chosen over what, and link the ADR if there is one |
| `learner` | evidence about the user: a struggle, a misconception, a success |
| `note` | anything else worth keeping |

Use `mw journal skip` for small talk. A Stop hook blocks you from ending a turn without one of these. Write each line so it makes sense months later without the conversation, using names, handles, and batch ids. The Journal is the ground truth; your Card is a summary of it.

## 3. Write only in your own lane

- You may edit: `.op/Agents/<you>/**`, Batch, Pattern, Challenge and ADR notes you create, and new Concept notes.
- Don't edit another agent's Card or Journal. Ask it instead (section 4).
- Never hand-edit generated blocks (`<!-- roster -->`, `<!-- handles -->`, `<!-- index -->`, `<!-- concepts -->`). Use `mw sync` and `mw learner ...` to change them.
- Never load whole Journals into context. Search them with grep.

## 4. Asking other agents: climb only as far as you need

1. **Roster** (already in your context): who owns what.
2. **Their Card**: read `.op/Agents/<them>/Card.md`. This is usually enough.
3. **Targeted search**: grep their `Journal/`, plus `.op/Decisions`, `.op/Patterns` and `.op/Batches`, for the specific thing.
4. **Inbox**: `mw inbox <them> "question"`. They answer at their next session start.
5. **Live ping, last resort**: only if the question is urgent and needs their judgement, and they're running. Use `superset terminals read/send` (see the superset:orchestrate skill), and journal the answer on both sides.

For steps 2–3 on more than one agent, or for broad questions, delegate to the **mw-clerk** sub-agent so the raw notes stay out of your context. It returns a short answer with sources.

When your inbox has open questions, answer them first. Change `- [ ]` to `- [x]` and append `→ answer` on the same line, in your own Inbox.md, which you may edit.

## 5. Checkpoint (`/op checkpoint`, or when the hook asks)

First journal a `decided` line saying what comes next ("next: …", or "next: ask the learner"), so the Card's next step comes from the journal rather than a guess. Then delegate to **mw-clerk** with: agent name, Card path, and "checkpoint". It rebuilds your Card from the old Card plus the journal lines since the last checkpoint, keeping it within 60 lines, then runs `mw stamp`, `mw sync` and `mw commit-vault`. Afterwards, re-read your Card.

Run a checkpoint when the user says they're done for the day, after every 3 batches, and whenever the context block shows the Housekeeping notice.

## 6. First session of a new agent

The context block says so. Ask the user for this agent's role in one line (the technology or area, plus the mode if not `model`). Run `mw register --role "..."` (with `--mode` if needed). Read the **For other agents** section of each sibling Card, then tell the user in 3–5 lines what you already know from them, so the user can see the handoff worked.

## 7. Models

- **You** (the main agent, Opus 5.5 by repo setting) write code, plan batches, and talk to the user.
- **mw-scribe** (Haiku 5.5) writes Batch, Pattern and Concept notes from a commit and your rationale packet.
- **mw-clerk** (Sonnet 5.5) does checkpoints, cross-agent lookups, and lint fixes.

## 8. Handles

When the user names a handle ("array searching 1", "AS1", "user data search"), resolve it with `mw handle <words>`. That gives the file, line, symbol, and Pattern note. Open exactly that symbol. If the handle is stale (symbol not found), say so and offer to update the Pattern note.

## 9. Git

- If the context block shows a **Setup** notice (`.venv` missing), run `mw setup` before running code or tests.

- Code: one batch = one commit on this agent's branch. Merging into `main` is the user's call; offer it after each batch.
- Vault: `mw commit-vault "<message>"` at checkpoints and after each batch's notes are written. It pushes only if the vault has a remote.
