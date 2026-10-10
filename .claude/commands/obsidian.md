---
description: Obsidian vault: sync (push/pull) or edit a note. Rewrite, index, and review have their own commands.
argument-hint: push | pull | <file-or-folder> <instruction>
---

The vault is at ~/Documents/Lynux-System on every machine. Its git remote is github.com/Niel-Aris/obsidian-vault (private). Ignore `.obsidian/` unless a mode says otherwise.

Arguments: $ARGUMENTS

## Routing

- First word `push` or `pull`: sync. Run only the matching section below, then stop.
- Otherwise the first token (or quoted string) is the target. Everything after it is the mode:
  - exactly `rewrite`: don't do it here. Tell the user to run `/obsidian-rewrite <target>`, then stop.
  - exactly `index`: tell the user to run `/obsidian-index <target>`, then stop.
  - exactly `review`: tell the user to run `/obsidian-review <target>`, then stop.
  - anything else: Edit mode, which follows the instruction literally
- If the target or mode is missing, ask for it and stop.

## Vault layout (keep it this way)

- `Index.md`: the concept index and home page. Only `/obsidian-index` adds entries here.
- `Concepts/`: one note per concept. The file name is the canonical term.
- `Templates/`: `Learning Log`, `Concept`, `Project`.
- `Attachments/`: every image and attachment. New files go here automatically.
- `Learning-C/<project>/Project overview.md` and `Learning-C/<project>/Day N/What I learned.md` and `Learning-C/<project>/Day N/Instructions.md`. Projects are the folders in ~/projects.

## Target resolution (edit mode)

1. Check whether the exact path exists under the vault root. A `.md` extension is optional.
2. If not, search by name, case-insensitive, ignoring `.obsidian/`. One match: use it. Several: ask which one. None: if the mode creates content, create the file, adding `.md` if there's no extension. Otherwise ask.
3. If the target is a folder, apply the mode to each `.md` file in it and report one summary.

## Safety (edit mode and sync)

- Before editing a file that has uncommitted changes, commit its current version locally: `git add "<file>" && git commit -m "snapshot before edit: <file>"`. Don't push as part of this step. Never force, reset, or discard.
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

## Edit mode

Apply the instruction to the target.

- For a file, read it first. Make only the change the instruction describes, and leave the rest alone.
- For a folder, do what the instruction asks inside it, such as creating a note there or summarising its notes.
- If the instruction is a question rather than an edit, answer it and don't modify anything.
- Keep frontmatter, `[[wiki-links]]`, and the existing heading style.
- Report the file you changed or created and summarise the change in one or two sentences.

## Efficiency

- Batch independent calls into one turn.
- Don't re-read a file after editing it, and skip a verification diff unless the report needs it.
