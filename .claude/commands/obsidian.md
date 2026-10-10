---
description: Obsidian vault: sync (push/pull), edit a note, rewrite a note, or index its concepts
argument-hint: push | pull | <file-or-folder> [rewrite | index | <instruction>]
---

The vault is at ~/Documents/Lynux-System on every machine. Its git remote is github.com/Niel-Aris/obsidian-vault (private). Ignore `.obsidian/` unless a mode says otherwise.

Arguments: $ARGUMENTS

## Routing

- First word `push` or `pull`: sync. Run only the matching section below, then stop.
- Otherwise the first token (or quoted string) is the target. Everything after it is the mode:
  - exactly `rewrite`: Rewrite mode
  - exactly `index`: Index mode
  - anything else: Edit mode, which follows the instruction literally
- If the target or mode is missing, ask for it and stop.

## Vault layout (keep it this way)

- `Index.md`: the concept index and home page. Only Index mode adds entries here.
- `Concepts/`: one note per concept. The file name is the canonical term.
- `Templates/`: `Learning Log`, `Concept`, `Project`.
- `Attachments/`: every image and attachment. New files go here automatically.
- `Learning-C/<project>/Project overview.md` and `Learning-C/<project>/Day N/What I learned.md` and `Learning-C/<project>/Day N/Instructions.md`. Projects are the folders in ~/projects.

## Target resolution (all modes)

1. Check whether the exact path exists under the vault root. A `.md` extension is optional.
2. If not, search by name, case-insensitive, ignoring `.obsidian/`. One match: use it. Several: ask which one. None: if the mode creates content, create the file, adding `.md` if there's no extension. Otherwise ask.
3. If the target is a folder, apply the mode to each `.md` file in it and report one summary.

## Safety (all modes except push and pull)

- Before editing a file that has uncommitted changes, commit its current version locally: `git add "<file>" && git commit -m "snapshot before <mode>: <file>"`. Don't push as part of this step. Never force, reset, or discard.
- Report what changed. `git diff` in the vault shows every change, and `git checkout -- "<file>"` undoes a change.

## Sync

**push**
1. `cd ~/Documents/Lynux-System`. If it isn't a git repo, say so and stop.
2. `git status --short`. If nothing changed, report "nothing to push" and stop.
3. `git add -A`, then commit with the message `vault sync: <hostname -s> <YYYY-MM-DD HH:MM>` and the trailer `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`.
4. `git push`. If the remote has newer commits, stop and tell the user to run `/obsidian pull` first. Never force-push.
5. Report the commit hash and the files included.

**pull**
1. `cd ~/Documents/Lynux-System`. If it isn't a git repo, say so and stop.
2. `git status --short`. If there are uncommitted changes, stop and tell the user to run `/obsidian push` first.
3. Note the current commit with `git rev-parse HEAD`, then `git pull --ff-only`. If the histories have diverged, stop and report the error. Never merge or rebase automatically.
4. If the commit changed, list the new commits with `git log --oneline <old>..HEAD` and the files with `git diff --stat <old>..HEAD`. Otherwise report "already up to date".
5. If plugin or appearance files changed, tell the user to press Ctrl+R (Cmd+R on Mac) in Obsidian to reload. Note changes show up without a reload.

## Rewrite mode

Goal: turn the note into clean, readable, less informal writing. This is more than a typo pass: restructure and extend the note so it reads well, while it stays the user's own writing.

- Restructure freely: reorganize sections, headings, and bullets so related points sit together. Merge duplicate lines, fix heading levels, and make bullet lists consistent.
- Extend: expand terse fragments into complete sentences, and add the connecting words needed to read smoothly. Extending means fuller wording of what's already there, not new content.
- Don't add facts, examples, conclusions, or explanations the user didn't write.
- Tone: plain and less informal. Replace casual phrasing (slang, shorthand, "a couple times", and similar) with neutral wording, but keep the language simple and everyday.
- Technical language: use it only where the user already used it, and keep the term exactly as written (for example `%zu format identifier`, `do while`). Don't introduce technical terms or make the note more technical than it is.
- Keep every fact, example, and question from the original. Keep the section names unless they're unclear.
- Leave frontmatter, `[[links]]`, `#tags`, code blocks, and images alone, except to fix obvious typos in prose.
- Fix spelling, grammar, and punctuation as part of the rewrite.
- Report the changes grouped by type (structure, wording, spelling, merged lines, extended lines).

## Index mode

Goal: link the note's concepts to one definition per concept, and keep the index free of duplicates.

1. Read the note. Read `Index.md` and every `Concepts/*.md`, including their frontmatter `aliases`.
2. Pick the concepts. Include only terms from systems engineering or the note's theme (C, memory, binary data, networking, operating systems, virtual machines, cloud, tools). Skip everyday words, names of people, and generic words.
3. Match each candidate against existing concept titles and aliases, case-insensitively, and by meaning. The same thing gets one concept even when it's spelled differently. For example, "water" and "H2O" both point to `Concepts/Water.md`, and `H2O` goes into its `aliases`. If the spelling is new, add it to `aliases`. Never create a second note for the same thing.
4. For a genuinely new concept, create `Concepts/<Canonical Term>.md` from the Concept template. It needs a short accurate definition, systems-engineering use cases, related concepts as `[[links]]`, and tags. Set `source: generated` so the user can review it. Keep it short. Avoid characters that aren't allowed in file names.
5. Add each concept to `Index.md` under its area heading, in the form `- [[Canonical Term]] — short definition`. Keep each area alphabetical. Only add a concept that isn't already listed.
6. In the note, link the first mention of each concept as `[[Canonical Term|the words as written]]`. Don't change the wording.
7. Tags. Frontmatter `tags` for concept notes: `concept` plus area tags such as `memory`, `cloud`, `networking`, `binary`, `c`, `vm`, `os`. For learning notes, add `learning`, `project/<name>`, and `day/<n>` if they're missing.
8. Report: concepts linked, new concepts created, aliases added, and anything skipped with the reason.

## Edit mode

Apply the instruction to the target.

- For a file, read it first. Make only the change the instruction describes, and leave the rest alone.
- For a folder, do what the instruction asks inside it, such as creating a note there or summarising its notes.
- If the instruction is a question rather than an edit, answer it and don't modify anything.
- Keep frontmatter, `[[wiki-links]]`, and the existing heading style.
- Report the file you changed or created and summarise the change in one or two sentences.
