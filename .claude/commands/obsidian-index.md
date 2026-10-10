---
description: Link an Obsidian note's concepts to one definition per concept in Concepts/ and Index.md, with commented C examples
argument-hint: <file-or-folder>
---

Index a note in the Obsidian vault at ~/Documents/Lynux-System. Ignore `.obsidian/`.

Target: $ARGUMENTS

## Vault layout (keep it this way)

- `Index.md`: the concept index and home page. Only this command adds entries here.
- `Concepts/`: one note per concept. The file name is the canonical term.
- `Templates/`: `Learning Log`, `Concept`, `Project`.

## Target resolution

1. Check whether the exact path exists under the vault root. A `.md` extension is optional.
2. If not, search by name, case-insensitive, ignoring `.obsidian/`. One match: use it. Several: ask which one. None: ask.
3. If the target is a folder, index each `.md` file in it and report one summary.

## Safety

- Before editing a file that has uncommitted changes, commit its current version locally: `git add "<file>" && git commit -m "snapshot before index: <file>"`. Don't push as part of this step. Never force, reset, or discard.
- Report what changed. `git diff` in the vault shows every change, and `git checkout -- "<file>"` undoes a change.

## Steps

Goal: link the note's concepts to one definition per concept, and keep the index free of duplicates.

1. Read the note and `Index.md`. Get the titles and frontmatter `aliases` of existing concepts with one grep over `Concepts/*.md`, and read a concept note only when you need to edit or link it.
2. Pick the concepts. Include only terms from systems engineering or the note's theme (C, memory, binary data, networking, operating systems, virtual machines, cloud, tools). Skip everyday words, names of people, and generic words.
3. Match each candidate against existing concept titles and aliases, case-insensitively, and by meaning. The same thing gets one concept even when it's spelled differently. For example, "water" and "H2O" both point to `Concepts/Water.md`, and `H2O` goes into its `aliases`. If the spelling is new, add it to `aliases`. Never create a second note for the same thing.
4. For a genuinely new concept, create `Concepts/<Canonical Term>.md` from the Concept template. It needs a short accurate definition, an example, systems-engineering use cases, related concepts as `[[links]]`, and tags. Set `source: generated` so the user can review it. Keep the definition short. Avoid characters that aren't allowed in file names.
   - Example section: place it after **Definition** under a `**Example**` heading, as a fenced `c` code block. The concept notes are the user's own reference for what they learned, so make the example something they can return to and understand.
   - For a language construct (such as `switch`, `do while`, `break`, `sizeof`, data types): write a short, complete program (under about 25 lines) that uses the construct in a realistic way, such as a menu for `switch`. Put a `//` comment on the lines that matter, saying what that line does in plain words (for example `//switch here is providing a menu with options`). Where the construct has a common mistake, such as a missing `break` falling through, show it briefly and comment on what happens.
   - For a set of items (such as format specifiers): one block listing each item with a `//` comment saying what it means, for example `printf("%d", x);   // %d prints an int as signed decimal`. Don't add a full program unless it helps.
   - Check the code compiles: run `gcc -Wall -Wextra -fsyntax-only` on it if gcc is available, and fix any errors or warnings before saving. Mention in the report if the check couldn't run.
   - Examples go only in concept notes, not in the learning note. Don't add facts the user didn't write to the learning note.
4a. For a concept note that already exists but has no **Example** section, add one using the rules in step 4, and keep the rest of the note as it is.
5. Add each concept to `Index.md` under its area heading, in the form `- [[Canonical Term]] — short definition`. Keep each area alphabetical. Only add a concept that isn't already listed.
6. In the note, link the first mention of each concept as `[[Canonical Term|the words as written]]`. Don't change the wording.
7. Tags. Frontmatter `tags` for concept notes: `concept` plus area tags such as `memory`, `cloud`, `networking`, `binary`, `c`, `vm`, `os`. For learning notes, add `learning`, `project/<name>`, and `day/<n>` if they're missing.
8. Report: concepts linked, new concepts created, aliases added, and anything skipped with the reason.

## Efficiency

- Batch independent calls into one turn: snapshots, reads, and greps run together, and new files are written together.
- Don't re-read a file after editing it, and skip a verification diff unless the report needs it.
