---
description: Edit, create, or ask about a note or folder in the Obsidian vault
argument-hint: <folder-or-file> <what to do>
---

The Obsidian vault is at /home/lynx/Documents/Lynux-System. Ignore its `.obsidian/` folder.

Arguments: $ARGUMENTS

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
