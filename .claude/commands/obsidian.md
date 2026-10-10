---
description: Edit vault notes, or sync the Obsidian vault with `push` / `pull`
argument-hint: push | pull | <folder-or-file> <what to do>
---

The Obsidian vault is at ~/Documents/Lynux-System on every machine. Its git remote is github.com/Niel-Aris/obsidian-vault (private). Ignore its `.obsidian/` folder when editing notes.

Arguments: $ARGUMENTS

If the first word is `push` or `pull`, this is a sync command. Run only the matching steps below, then stop. Don't edit any notes.

**push** (send this machine's vault changes to GitHub):
1. `cd ~/Documents/Lynux-System`. If it isn't a git repo, say so and stop.
2. Run `git status --short`. If there are no changes, report "nothing to push" and stop.
3. Run `git add -A`, then commit with the message `vault sync: <hostname -s> <YYYY-MM-DD HH:MM>` and the trailer `Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>`.
4. Run `git push`. If the push is rejected because the remote has newer commits, stop and tell the user to run `/obsidian pull` first. Never force-push.
5. Report the commit hash and the files included.

**pull** (bring the latest vault from GitHub onto this machine):
1. `cd ~/Documents/Lynux-System`. If it isn't a git repo, say so and stop.
2. Run `git status --short`. If there are uncommitted changes, stop and tell the user to run `/obsidian push` first. Don't stash, reset, or discard anything.
3. Note the current commit with `git rev-parse HEAD`, then run `git pull --ff-only`. If it fails because the histories have diverged, stop and report the error. Don't merge or rebase automatically.
4. If the commit changed, list what came in with `git log --oneline <old>..HEAD` and `git diff --stat <old>..HEAD`. If it didn't, report "already up to date".
5. If plugin or appearance files changed, tell the user to press Ctrl+R (Cmd+R on Mac) in Obsidian to reload. Note changes show up without a reload.

Otherwise, treat the arguments as a note edit:

Parse the arguments:
- The first token is the target: a file or folder path relative to the vault root. If the path contains spaces, it will be quoted. A `.md` extension is optional.
- Everything after the target is the instruction.
- If either part is missing, ask for it and stop.

Resolve the target:
1. Check whether the exact path exists under the vault root.
2. If it doesn't, search the vault by name (case-insensitive, ignoring `.obsidian/`). Use the single match if there is one. If there are several, ask which one. If there are none and the instruction creates or writes content, create the file at the given path with `.md` appended when there's no extension.

Apply the instruction:
- If the target is a folder, do what the instruction asks inside it, such as creating a new note there or summarising its notes.
- If the target is a file, read it first. Make only the change the instruction describes and leave the rest of the note alone. Keep any frontmatter, `[[wiki-links]]`, and the existing heading style.
- If the instruction is a question rather than an edit, answer it and don't modify anything.

When you finish, report the file you changed or created and summarise the change in one or two sentences.
