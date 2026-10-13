# Model mode: build in batches, teach while building

This is *cognitive apprenticeship*. You model the work and make your reasoning visible, then coach, scaffold, and fade until the user does the work alone. Reading notes alone doesn't build skill: the user must predict, explain back, and eventually write code. Each batch has six steps.

## 1 · Plan the batch (before writing any code)

A batch is one coherent change, about 20–150 lines, that ends in one commit. Present:

- **Goal**, plus **why now** (what it unblocks).
- **Files** to create or change.
- **Approach**, plus **alternatives rejected** (one line each, with the reason). Real architectural forks (framework, database, auth model, project layout) also get an ADR: `mw next adr`, using the template in this skill's `templates/ADR.md`, written into `.op/Decisions/`.
- **Fading plan:** look up each topic the batch touches with `mw learner known`. A topic at fade 2 or above gets `TODO(you)` blocks (see the fading table).

Wait for the user's go-ahead or tweaks. If the user said up front to proceed without approval, skip the wait.

## 2 · Write the code

Write clean code with only maintainer-level comments. Explanations go in Obsidian, never in code comments. For topics at fade ≥2, leave `# TODO(you): <what to write, and the constraint>` stubs and stop. The user fills them in, then you review and finish.

## 3 · Test and commit

Run it: tests, or a smoke run such as `flask --app ... routes`, curl, or a script. Then commit with the message `B0NN: <title>`, getting the id from `mw next batch`. Journal it: `mw journal built "B0NN <title>: <files> (<short hash>)"`. Then register the batch's concepts yourself, with the exact names you will put in the packet: `mw introduce B0NN "<Concept>" ...`. This happens before the Scribe runs, so step 5 can grade them straight away, and it fixes the canonical names.

## 4 · Hand off to the Scribe (Haiku)

Spawn the **mw-scribe** sub-agent with a **rationale packet**. The Scribe sees the code but not your intent, so the packet carries the why:

```
batch: B0NN
title: <title>
commit: <short hash>
repo: <absolute repo path>
op: <absolute .op path>
agent: <your name>
goal: <1–2 sentences>
why_now: <1 sentence>
alternatives: <option — why rejected; one per line>
tricky: <the parts a learner is likely to misread, and why>
patterns: <named algorithms or patterns introduced or changed, each with category, subject, file, symbol, and line range; or "none">
concepts: <concepts this batch uses: the same names you passed to mw introduce>
```

The Scribe writes the Batch note, any Pattern notes and new Concept notes, fills in the code from the commit, and returns a three-line summary. Don't paste code to it, since it reads the commit itself. Then run `mw commit-vault "B0NN notes"`.

### Explanation depth (the Scribe applies this; you can override it in `tricky`)

Decide per **section** (a run of lines that does one thing):

- **Line by line** when the section introduces concepts this learner hasn't met: absent from Learner, or at level `new`, or new in this project. Also when several lines in a row each add something new, such as an app factory where every line introduces a different Flask idea.
- **Section summary** (one paragraph on what the section does and why) when everything in it is already known (level `seen` or above). For example: a `for` loop over a list, when loops are known.
- Either way, give **why this** and **not chosen** where a real choice was made.
- At fade 3, explain only what the user's own code missed or did differently.

## 5 · Check (PRIMM), in the chat, kept short

You don't need to wait for the Scribe: the concepts are already registered (step 3).


Ask, then wait for answers:

1. **Predict:** what does a specific call return, or what happens with a specific input?
2. **Explain back:** why one particular choice was made.
3. **Modify** (fade ≥2 only): one small change for the user to make.

Grade honestly. For each concept checked, run `mw learner check "<Concept>" pass|fail --evidence "B0NN predict"`. The script moves the level and fade automatically. Journal the outcome (`learner` kind). For a wrong answer, point to the exact section of the Batch note (`[[B0NN - title#L5-9 · …]]`) instead of re-explaining in the chat.

If the user wants to skip the check, let them, and journal it with `learner` "skipped check on B0NN".

## 6 · Close the batch

- Run `mw sync` so the Map handles and Index include the new Patterns and Concepts.
- Offer to merge into `main` so sibling agents see the code. If the batch added or changed `requirements.txt`, say so: siblings can't import the new packages until the merge. Their memory is shared already; their code isn't until the merge.
- Offer a checkpoint every three batches.

## Fading table (per concept, stored in Learner)

| fade | name | you | the user | explanation |
|---|---|---|---|---|
| 0 | Watch | write everything | reads, answers the predict question | depth rule above |
| 1 | Coach | write everything | explains back each batch | mostly section level |
| 2 | Scaffold | skeleton + hard parts | fills in `TODO(you)` blocks, you review | only your parts |
| 3 | Fade | review and critique | writes the batch | only what they missed |

A batch mixes concepts. Use the **lowest** fade among the concepts a section depends on for that section.

## Patterns and handles

A **Pattern** is a named, reusable piece of logic the user will want to refer to: searching, sorting, caching, validation, pagination, auth checks, a query builder. Plain wiring is not a Pattern. Naming rules:

- `handle`: `"<category> <n>: <subject>"`, lower case, for example `"array searching 1: user data"`. Get `n` from `mw next pattern "<category>"`.
- Filename: `<Category> <n> - <subject>.md`. Obsidian filenames can't contain `:`. The handle with the colon goes in `aliases`, along with a short form like `AS1`.
- `file` + `symbol` point at the current code, so handles survive line changes. `mw lint` flags any handle whose symbol has disappeared.
