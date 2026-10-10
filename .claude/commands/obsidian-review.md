---
description: Review a finished C learning day: check its code against the instructions and write a review into What I learned
argument-hint: Learning-C/<project>/Day N
---

Review a finished day in the Obsidian vault at ~/Documents/Lynux-System. Ignore `.obsidian/`.

Target: $ARGUMENTS

## Target

The target is a day folder (`Learning-C/<project>/Day N`) or its `What I learned.md`. Read both `Instructions.md` and `What I learned.md` in that folder. If the target doesn't resolve to a day folder, ask which day. Never edit the project's code.

## Safety

- Before editing `What I learned.md`, if it has uncommitted changes, commit its current version locally: `git add "<file>" && git commit -m "snapshot before review: <file>"`. Don't push as part of this step. Never force, reset, or discard.
- Report what changed. `git diff` in the vault shows every change, and `git checkout -- "<file>"` undoes a change.

## Steps

Goal: write a review of the day into the `## Review` section of its `What I learned.md`: what was asked, what was done, mistakes and code problems, what to change before the next day, and whether this day is a good base for the next day. The review is for the user to learn from. Point at the problem and the line, and say what to change. Don't write replacement code.

1. Read `Instructions.md`. Its frontmatter `source` is where the code is. If it's a file, that file is the code, and its directory is the project repo. If it's a directory, that's the project. Read the Approach, Deliverable, and Stretch sections.
2. Read the code. If the project directory is a git repo, run `git -C <repo> status --short` and `git -C <repo> log --oneline -5 -- <path>`, and read `git diff` for uncommitted changes. Projects may have no per-day commits, so review the current code and say which history you used. If the source is missing or has no code yet, say so and review against the instructions only.
3. Read the day's `What I learned.md`: what the user says they learned, what broke, and their questions.
4. Check the work against the instructions. Mark each Approach, Deliverable, and Stretch item as done, partial, or missing. For mistakes and code problems, give the file and line, and say why it matters (for example, an unchecked return value, a leak, undefined behaviour, a missing `free`). Note any question from the notes that the code doesn't answer.
5. Next day: if `Day N+1/Instructions.md` exists, read it and say what this day's code is missing or gets wrong for it. If there is no next day, say so.
6. Write the review into `## Review` in `What I learned.md`, replacing the placeholder, in this order:
   - **Asked vs done:** the instruction items with done / partial / missing.
   - **Mistakes:** each with file:line and why it matters.
   - **Code problems:** each with file:line, what to change, and why. Most severe first.
   - **Before Day N+1:** a numbered list of the changes that must be made first.
   - **Base for next day:** Ready, Ready with the changes above, or Not ready, with one or two sentences of reason.
   Keep it under about 60 lines. Leave the other sections and the frontmatter as they are.
7. Snapshot the note first if it has uncommitted changes (Safety). Then edit only the `## Review` section.
8. Report the file changed, the verdict, and whether the code was read or missing.

## Efficiency

- Batch independent calls into one turn: the reads, the git commands, and the snapshot run together.
- Don't re-read a file after editing it, and skip a verification diff unless the report needs it.
