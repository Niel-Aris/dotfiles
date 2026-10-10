---
description: Rewrite an Obsidian note: restructure and extend it in plain, less informal writing
argument-hint: <file-or-folder>
---

Rewrite a note in the Obsidian vault at ~/Documents/Lynux-System. Ignore `.obsidian/`.

Target: $ARGUMENTS

## Target resolution

1. Check whether the exact path exists under the vault root. A `.md` extension is optional.
2. If not, search by name, case-insensitive, ignoring `.obsidian/`. One match: use it. Several: ask which one. None: ask.
3. If the target is a folder, rewrite each `.md` file in it and report one summary.

## Safety

- Before editing a file that has uncommitted changes, commit its current version locally: `git add "<file>" && git commit -m "snapshot before rewrite: <file>"`. Don't push as part of this step. Never force, reset, or discard.
- Report what changed. `git diff` in the vault shows every change, and `git checkout -- "<file>"` undoes a change.

## Rules

Goal: turn the note into clean, readable, less informal writing. This is more than a typo pass: restructure and extend the note so it reads well, while it stays the user's own writing.

- Restructure freely: reorganize sections, headings, and bullets so related points sit together. Merge duplicate lines, fix heading levels, and make bullet lists consistent.
- Extend: expand terse fragments into complete sentences, and add the connecting words needed to read smoothly. Extending means fuller wording of what's already there, not new content.
- Don't add facts, examples, conclusions, or explanations the user didn't write.
- Tone: plain and less informal. Replace casual phrasing (slang, shorthand, "a couple times", and similar) with neutral wording, but keep the language simple and everyday.
- Technical language: use it only where the user already used it, and keep the term exactly as written (for example `%zu format identifier`, `do while`). Don't introduce technical terms or make the note more technical than it is.
- Keep every fact, example, and question from the original. Keep the section names unless they're unclear. Leave the `## Review` section unchanged.
- Leave frontmatter, `[[links]]`, `#tags`, code blocks, and images alone, except to fix obvious typos in prose.
- Fix spelling, grammar, and punctuation as part of the rewrite.
- Report the changes grouped by type (structure, wording, spelling, merged lines, extended lines).

## Efficiency

- Batch independent calls into one turn: the snapshot and the read run together.
- Don't re-read a file after editing it, and skip a verification diff unless the report needs it.
