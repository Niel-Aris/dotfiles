#!/usr/bin/env python3
"""Model-Workflow helper: shared agent memory in an Obsidian vault.

An Operation is a git repo with a .mw.json file. Each worktree (Superset
workspace) is an agent. Memory lives in <vault>/Operations/<operation>/,
outside every branch, so all agents see the same files.

Run `mw.py -h` for commands. Everything here is deterministic; the models
write prose, this script moves code, dates, and tables around.
"""

import argparse
import datetime as dt
import difflib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

SKILL_DIR = Path.home() / ".claude/skills/model-workflow"
DEFAULT_VAULT = Path.home() / "Documents/Model-Workflow"
SCRIPT = "mw" if shutil.which("mw") else "python3 -I ~/.claude/scripts/mw.py"

CARD_MAX = 60
OPERATION_MAX = 80
LAZY_CHECKPOINT = 25          # journal lines since last checkpoint before a forced refresh
LEVELS = ["new", "seen", "ok", "solid"]
REVIEW_DAYS = {"new": 1, "seen": 2, "ok": 5, "solid": 14}
JOURNAL_KINDS = ["asked", "taught", "built", "decided", "learner", "note"]

LANG = {".py": "python", ".js": "javascript", ".ts": "typescript", ".html": "html",
        ".css": "css", ".sql": "sql", ".json": "json", ".md": "markdown", ".sh": "bash",
        ".toml": "toml", ".yml": "yaml", ".yaml": "yaml", ".c": "c", ".h": "c",
        ".jsx": "jsx", ".tsx": "tsx", ".txt": "text", ".cfg": "ini", ".ini": "ini"}


# ---------- small utilities ----------

def die(msg, code=1):
    print(f"mw: {msg}", file=sys.stderr)
    sys.exit(code)


def now():
    return dt.datetime.now().replace(second=0, microsecond=0)


def today():
    return dt.date.today()


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def repo_root(start=None):
    if start is None:
        logical = os.environ.get("PWD", "")
        if "/.op/" in logical + "/" and Path(logical).resolve() == Path.cwd().resolve():
            start = logical.split("/.op")[0]
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start or os.getcwd(),
                       capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def read_fm(path):
    """Parse flat YAML frontmatter. Returns (dict, body)."""
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v.startswith("["):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                v = [x.strip().strip('"\'') for x in v.strip("[]").split(",") if x.strip()]
        elif len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        fm[k] = v
    body = text[end + 4:].lstrip("\n")
    return fm, body


def set_fm(path, **updates):
    """Update flat frontmatter keys in place, keeping order and the body."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        die(f"{path} has no frontmatter")
    end = text.find("\n---", 4)
    lines = text[4:end].splitlines()
    seen = set()
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z_][\w-]*):", line)
        if m and m.group(1) in updates:
            lines[i] = f"{m.group(1)}: {updates[m.group(1)]}"
            seen.add(m.group(1))
    lines += [f"{k}: {v}" for k, v in updates.items() if k not in seen]
    path.write_text("---\n" + "\n".join(lines) + text[end:], encoding="utf-8")


def replace_block(text, name, content):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if start not in text:
        return text.rstrip() + f"\n\n{start}\n{content}\n{end}\n"
    pre, rest = text.split(start, 1)
    post = rest.split(end, 1)[1] if end in rest else ""
    return f"{pre}{start}\n{content}\n{end}{post}"


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "agent"


# ---------- context: which operation / agent are we in ----------

class Ctx:
    def __init__(self, start=None, need_agent=True):
        self.root = repo_root(start)
        if not self.root or not (self.root / ".mw.json").exists():
            die("not inside a Model-Workflow repo (no .mw.json at the repo root)")
        cfg = json.loads((self.root / ".mw.json").read_text())
        self.vault = Path(os.path.expanduser(cfg.get("vault", str(DEFAULT_VAULT))))
        self.op_name = cfg["operation"]
        self.op = self.vault / "Operations" / self.op_name
        self.agent = None
        ident = self.root / ".op-agent"
        if ident.exists():
            self.ident = json.loads(ident.read_text())
            self.agent = self.ident["name"]
        elif need_agent:
            die("this worktree is not registered as an agent; run: mw.py register")

    @property
    def agent_dir(self):
        return self.op / "Agents" / self.agent

    @property
    def card(self):
        return self.agent_dir / "Card.md"

    def state_path(self):
        return self.root / ".op-state"

    def state(self):
        p = self.state_path()
        return json.loads(p.read_text()) if p.exists() else {}

    def save_state(self, **kw):
        s = self.state()
        s.update(kw)
        self.state_path().write_text(json.dumps(s))


def tmpl(name, **kw):
    text = (SKILL_DIR / "templates" / f"{name}.md").read_text(encoding="utf-8")
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


# ---------- init / register ----------

def ensure_vault(vault):
    created = not vault.exists()
    for d in ["Operations", "Concepts", "Me", "Templates", "Attachments"]:
        (vault / d).mkdir(parents=True, exist_ok=True)
    for name in ["Batch", "Pattern", "Concept", "Challenge", "ADR", "Card"]:
        dst = vault / "Templates" / f"{name}.md"
        if not dst.exists():
            shutil.copy(SKILL_DIR / "templates" / f"{name}.md", dst)
    learner = vault / "Me" / "Learner.md"
    if not learner.exists():
        learner.write_text(tmpl("Learner", date=today()), encoding="utf-8")
    home = vault / "Home.md"
    if not home.exists():
        home.write_text(tmpl("Home"), encoding="utf-8")
    gi = vault / ".gitignore"
    if not gi.exists():
        gi.write_text(".obsidian/workspace*.json\n.obsidian/cache\n.trash/\n")
    if not (vault / ".git").exists():
        git("init", "-q", "-b", "main", cwd=vault)
    return created


VENV_SETUP = ("[ -f requirements.txt ] && { python3 -m venv .venv && "
              ".venv/bin/pip install -q -r requirements.txt; } || true")


def write_if_missing(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def cmd_init(a):
    repo = Path(os.path.expanduser(a.repo)).resolve()
    vault = Path(os.path.expanduser(a.vault)).resolve()
    if not (repo / ".git").exists():
        die(f"{repo} is not a git repo (git init it first)")
    ensure_vault(vault)
    vault_str = str(vault).replace(str(Path.home()), "~", 1)
    made = []
    files = {
        ".mw.json": json.dumps({"vault": vault_str, "operation": a.op}, indent=2) + "\n",
        ".superset/config.json": json.dumps(
            {"setup": [f'python3 -I "$HOME/.claude/scripts/mw.py" register', VENV_SETUP] + (a.setup or [])},
            indent=2) + "\n",
        ".claude/settings.json": json.dumps({
            "model": a.model,
            "hooks": {
                "SessionStart": [{"hooks": [{"type": "command", "timeout": 10,
                    "command": 'python3 -I "$HOME/.claude/scripts/mw.py" context'}]}],
                "UserPromptSubmit": [{"hooks": [{"type": "command", "timeout": 5,
                    "command": 'python3 -I "$HOME/.claude/scripts/mw.py" hook-prompt'}]}],
                "Stop": [{"hooks": [{"type": "command", "timeout": 5,
                    "command": 'python3 -I "$HOME/.claude/scripts/mw.py" hook-stop'}]}],
            }}, indent=2) + "\n",
        "CLAUDE.md": tmpl("RepoClaude", op=a.op),
    }
    for rel, content in files.items():
        if write_if_missing(repo / rel, content):
            made.append(rel)
    gi = repo / ".gitignore"
    existing = gi.read_text() if gi.exists() else ""
    add = [x for x in [".op", ".op-agent", ".op-state"] if x not in existing.split()]
    if add:
        gi.write_text(existing + ("" if existing.endswith("\n") or not existing else "\n")
                      + "# Model-Workflow (per-worktree links)\n" + "\n".join(add) + "\n")
        made.append(".gitignore")
    op = vault / "Operations" / a.op
    for d in ["Agents", "Batches", "Patterns", "Challenges", "Decisions"]:
        (op / d).mkdir(parents=True, exist_ok=True)
    repo_str = str(repo).replace(str(Path.home()), "~", 1)
    if write_if_missing(op / "Operation.md", tmpl("Operation", op=a.op, repo=repo_str, date=today())):
        made.append(f"vault: Operations/{a.op}/Operation.md")
    write_if_missing(op / "Map.md", tmpl("Map", op=a.op))
    sync(vault, op, repo)
    print("created: " + (", ".join(made) if made else "nothing (already initialised)"))


def default_agent_name(root):
    name = os.environ.get("SUPERSET_WORKSPACE_NAME")
    if name:
        return slug(name)
    branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root).strip()
    return slug(re.sub(r"-[0-9a-f]{8}$", "", branch.split("/")[-1]))


def register(ctx, name=None, mode=None, role=None, quiet=False):
    name = slug(name) if name else (ctx.agent or default_agent_name(ctx.root))
    ws_id = os.environ.get("SUPERSET_WORKSPACE_ID", "")
    branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=ctx.root).strip()
    link = ctx.root / ".op"
    if link.is_symlink() or link.exists():
        if link.is_symlink():
            link.unlink()
    if not link.exists():
        link.symlink_to(ctx.op, target_is_directory=True)
    (ctx.root / ".op-agent").write_text(json.dumps({"name": name, "workspace_id": ws_id}))
    ctx.agent = name
    d = ctx.agent_dir
    (d / "Journal").mkdir(parents=True, exist_ok=True)
    new = write_if_missing(d / "Card.md", tmpl(
        "Card", agent=name, workspace_id=ws_id or "none", branch=branch,
        mode=mode or "model", role=role or "unset", date=today()))
    if not new:
        upd = {"branch": branch, "status": "active"}
        if ws_id:
            upd["workspace_id"] = ws_id
        if mode:
            upd["mode"] = mode
        if role:
            upd["role"] = json.dumps(role)
        set_fm(d / "Card.md", **upd)
    elif role:
        set_fm(d / "Card.md", role=json.dumps(role))
    fill_role(d / "Card.md")
    write_if_missing(d / "Inbox.md", f"# Inbox · {name}\n\nQuestions from other agents. "
                     "`- [ ]` open, `- [x]` answered (answer after →).\n\n")
    sync(ctx.vault, ctx.op, ctx.root)
    if not quiet:
        print(f"registered agent '{name}' ({'new' if new else 'existing'}) → {d}")
    return name


ROLE_PLACEHOLDER = "## Role\n_Not set yet._"


def fill_role(card):
    """Copy the frontmatter role into the body while the body still has the placeholder."""
    fm, _ = read_fm(card)
    role = str(fm.get("role", "")).strip()
    text = card.read_text(encoding="utf-8")
    if role and role != "unset" and ROLE_PLACEHOLDER in text:
        card.write_text(text.replace(ROLE_PLACEHOLDER, f"## Role\n{role.rstrip('.')}."), encoding="utf-8")


def cmd_register(a):
    ctx = Ctx(need_agent=False)
    register(ctx, a.name, a.mode, a.role)


# ---------- journal ----------

def journal_path(ctx, day=None):
    return ctx.agent_dir / "Journal" / f"{day or today()}.md"


def cmd_journal(a):
    ctx = Ctx()
    if a.kind == "skip":
        ctx.save_state(journaled=dt.datetime.now().isoformat())
        return
    if a.kind not in JOURNAL_KINDS:
        die(f"kind must be one of {', '.join(JOURNAL_KINDS)} (or skip)")
    text = " ".join(a.text).strip()
    if not text:
        die("empty journal text")
    p = journal_path(ctx)
    if not p.exists():
        p.write_text(f"# {ctx.agent} · {today()}\n\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- {now():%H:%M} · {a.kind} · {text}\n")
    ctx.save_state(journaled=dt.datetime.now().isoformat())


def journal_lines_since(agent_dir, since):
    """Journal entries after an ISO timestamp (or all, if since is falsy/'never')."""
    try:
        cutoff = dt.datetime.fromisoformat(since) if since and since != "never" else None
    except ValueError:
        cutoff = None
    out = []
    for f in sorted((agent_dir / "Journal").glob("*.md")):
        try:
            day = dt.date.fromisoformat(f.stem)
        except ValueError:
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^- (\d\d):(\d\d) · ", line)
            if not m:
                continue
            t = dt.datetime.combine(day, dt.time(int(m.group(1)), int(m.group(2))))
            if cutoff is None or t > cutoff:
                out.append((t, line))
    return out


# ---------- learner model ----------

LEARNER_RE = re.compile(r"^- \[\[(?P<c>[^\]]+)\]\](?P<rest>.*)$")


def learner_path(vault):
    return vault / "Me" / "Learner.md"


@contextmanager
def learner_lock(vault):
    """Serialise read-modify-write of Learner.md across agents and sub-agents."""
    key = hashlib.sha1(str(vault.resolve()).encode()).hexdigest()[:12]
    with open(Path(tempfile.gettempdir()) / f"mw-learner-{key}.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def learner_load(vault):
    text = learner_path(vault).read_text(encoding="utf-8")
    items = {}
    for line in text.splitlines():
        m = LEARNER_RE.match(line)
        if not m:
            continue
        rec = {"concept": m.group("c")}
        for part in m.group("rest").split(" · "):
            if ":" in part:
                k, v = part.split(":", 1)
                rec[k.strip()] = v.strip()
        rec.setdefault("level", "new")
        rec.setdefault("fade", "0")
        rec.setdefault("streak", "0")
        items[rec["concept"].lower()] = rec
    return text, items


def learner_line(r):
    parts = [f"- [[{r['concept']}]]", f"level: {r['level']}", f"fade: {r['fade']}",
             f"streak: {r['streak']}", f"seen: {r.get('seen', today())}",
             f"review: {r.get('review', today())}"]
    if r.get("evidence"):
        parts.append(f"evidence: {r['evidence']}")
    return " · ".join(parts)


def learner_save(vault, text, items):
    body = "\n".join(learner_line(items[k]) for k in sorted(items))
    text = replace_block(text, "concepts", body)
    text = re.sub(r"^updated: .*$", f"updated: {today()}", text, count=1, flags=re.M)
    learner_path(vault).write_text(text, encoding="utf-8")


def schedule(r):
    r["seen"] = str(today())
    r["review"] = str(today() + dt.timedelta(days=REVIEW_DAYS[r["level"]]))


def add_evidence(r, ev):
    if not ev:
        return
    old = [e.strip() for e in r.get("evidence", "").split(";") if e.strip()]
    r["evidence"] = "; ".join((old + [ev])[-3:])


def concept_names(vault):
    """{lowercase name or alias: canonical note name} for every Concept note."""
    names = {}
    for c in (vault / "Concepts").glob("*.md"):
        names[c.stem.lower()] = c.stem
        al = read_fm(c)[0].get("aliases") or []
        for x in ([al] if isinstance(al, str) else al):
            names.setdefault(str(x).lower(), c.stem)
    return names


def resolve_concept(vault, items, name, allow_new):
    """Canonical concept name; refuses unknown names unless allow_new, so typos don't fork entries."""
    key = name.lower()
    if key in items:
        return items[key]["concept"]
    notes = concept_names(vault)
    if key in notes:
        return notes[key]
    if allow_new:
        return name
    pool = sorted({r["concept"] for r in items.values()} | set(notes.values()))
    close = difflib.get_close_matches(name, pool, n=3, cutoff=0.6)
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    die(f"unknown concept '{name}' (not in Learner.md or Concepts/).{hint} "
        "Use --new to add it as a new concept.")


def checked(r):
    return "✓" in r.get("evidence", "") or "✗" in r.get("evidence", "")


def learner_vault():
    root = repo_root()
    return Ctx(need_agent=False).vault if root and (root / ".mw.json").exists() else DEFAULT_VAULT


def cmd_learner(a):
    vault = learner_vault()
    if a.action in ("show", "known"):
        learner_read(vault, a)
        return
    with learner_lock(vault):
        learner_write(vault, a)


def learner_read(vault, a):
    _, items = learner_load(vault)
    if a.action == "show":
        rows = sorted(items.values(), key=lambda r: r["concept"].lower())
        if a.concept:
            q = a.concept.lower()
            rows = [r for r in rows if q in r["concept"].lower()]
        if a.unchecked:
            rows = [r for r in rows if not checked(r)]
        if a.due:
            rows = [r for r in rows if r.get("review", "9999") <= str(today())]
        for r in rows:
            print(learner_line(r)[2:])
        if not rows:
            print("(none)")
        return
    if a.action == "known":
        for r in sorted(items.values(), key=lambda r: r["concept"].lower()):
            print(f"{r['concept']}\t{r['level']}\tfade={r['fade']}")


def learner_write(vault, a):
    text, items = learner_load(vault)
    if not a.concept:
        die("concept required")
    name = resolve_concept(vault, items, a.concept, a.new)
    key = name.lower()
    r = items.get(key) or {"concept": name, "level": "new", "fade": "0", "streak": "0"}
    note = ""
    if a.action == "set":
        if a.level:
            if a.level not in LEVELS:
                die(f"level must be one of {LEVELS}")
            r["level"] = a.level
        if a.fade is not None:
            r["fade"] = str(max(0, min(3, a.fade)))
        add_evidence(r, a.evidence)
        schedule(r)
    elif a.action == "check":
        if a.result not in ("pass", "fail"):
            die("result must be pass or fail")
        lvl, fade, streak = LEVELS.index(r["level"]), int(r["fade"]), int(r["streak"])
        if a.result == "pass" and streak > 0 and str(today()) < r.get("review", ""):
            # spaced retrieval: a second pass only counts once the review date has come
            note = f"\n(pass recorded; streak counts again from {r['review']})"
        elif a.result == "pass":
            streak += 1
            if streak >= 2:
                lvl, fade, streak = min(lvl + 1, 3), min(fade + 1, 3), 0
        else:
            lvl, fade, streak = max(lvl - 1, 0), max(fade - 1, 0), 0
        r.update(level=LEVELS[lvl], fade=str(fade), streak=str(streak))
        add_evidence(r, f"{a.evidence or 'check'} {'✓' if a.result == 'pass' else '✗'} ({today()})")
        if not note:
            schedule(r)
    items[key] = r
    learner_save(vault, text, items)
    print(learner_line(r)[2:] + note)


def cmd_introduce(a):
    """Register the concepts a batch, challenge or intake brings in, before any check or note."""
    vault = learner_vault()
    intake = a.source.lower() == "intake"
    notes = concept_names(vault)
    with learner_lock(vault):
        text, items = learner_load(vault)
        for raw in a.concepts:
            name = resolve_concept(vault, items, raw, allow_new=True)
            key = name.lower()
            if key in items:
                print(f"known  {name} ({items[key]['level']}, fade {items[key]['fade']})")
                continue
            # self-report is not evidence: intake tops out at seen / fade 1
            r = {"concept": name, "level": "seen" if intake else "new",
                 "fade": "1" if intake else "0", "streak": "0"}
            add_evidence(r, "intake (self-report)" if intake else f"{a.source} introduced")
            schedule(r)
            items[key] = r
            hint = "" if key in notes else f"  → no Concept note yet: Concepts/{name}.md"
            print(f"new    {name}{hint}")
        learner_save(vault, text, items)


# ---------- roster / map / index ----------

def sync(vault, op, repo):
    roster(op)
    build_map(op, repo)
    build_index(vault)


def roster(op):
    rows = []
    for card in sorted((op / "Agents").glob("*/Card.md")):
        fill_role(card)
        fm, _ = read_fm(card)
        name = fm.get("agent", card.parent.name)
        rel = card.relative_to(op.parent.parent).with_suffix("").as_posix()
        rows.append(f"| [[{rel}\\|{name}]] | {fm.get('mode', '?')} | "
                    f"{fm.get('status', '?')} | {fm.get('role', '')} | {fm.get('updated', '')} |")
    table = ("| Agent | Mode | Status | Role | Updated |\n|---|---|---|---|---|\n"
             + ("\n".join(rows) if rows else "| _none yet_ | | | | |"))
    p = op / "Operation.md"
    if p.exists():
        p.write_text(replace_block(p.read_text(encoding="utf-8"), "roster", table), encoding="utf-8")


def find_symbol(repo, file, symbol):
    """Line number of a def/class/assignment of symbol in file, or None."""
    p = Path(repo) / file
    if not symbol or not p.exists():
        return None
    pat = re.compile(rf"^\s*(?:async\s+def|def|class|function|const|let|var)?\s*{re.escape(symbol)}\b\s*[\(:=]?")
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if pat.match(line):
            return i
    return None


def handle_location(repo, fm):
    """(status, detail) for a Pattern's code as seen from this worktree.
    status: ok | unmerged | stale"""
    f, sym, commit = fm.get("file", ""), fm.get("symbol", ""), fm.get("commit", "")
    line = find_symbol(repo, f, sym)
    if line:
        return "ok", f"{f}:{line}"
    if commit:
        merged = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=repo,
                                capture_output=True).returncode == 0
        exists = subprocess.run(["git", "cat-file", "-e", f"{commit}:{f}"], cwd=repo,
                                capture_output=True).returncode == 0
        if not merged and exists:
            branches = git("branch", "--contains", commit, "--format=%(refname:short)", cwd=repo, check=False)
            where = ", ".join(branches.split()) or "another branch"
            return "unmerged", f"{f} (not merged into this branch yet; at {commit} on {where})"
    return "stale", f"{f} (symbol `{sym}` not found — code renamed or removed)"


def patterns(op):
    out = []
    for p in sorted((op / "Patterns").glob("*.md")):
        fm, _ = read_fm(p)
        if fm.get("handle"):
            out.append((p, fm))
    return out


def build_map(op, repo):
    rows = []
    for p, fm in patterns(op):
        rows.append(f"| **{fm['handle']}** | `{fm.get('file', '')}` | `{fm.get('symbol', '')}` | "
                    f"[[{p.stem}]] | {fm.get('introduced', '')} |")
    table = ("| Handle | File | Symbol | Pattern note | Introduced |\n|---|---|---|---|---|\n"
             + ("\n".join(rows) if rows else "| _no handles yet_ | | | | |"))
    m = op / "Map.md"
    if m.exists():
        m.write_text(replace_block(m.read_text(encoding="utf-8"), "handles", table), encoding="utf-8")


def build_index(vault):
    idx = vault / "Index.md"
    rows = []
    for c in sorted((vault / "Concepts").glob("*.md"), key=lambda p: p.stem.lower()):
        fm, _ = read_fm(c)
        al = fm.get("aliases") or []
        al = [al] if isinstance(al, str) else al
        rows.append(f"- [[{c.stem}]]" + (f" ({', '.join(al)})" if al else ""))
    body = "\n".join(rows) if rows else "_No concepts yet._"
    text = idx.read_text(encoding="utf-8") if idx.exists() else (
        "# Index\n\nEvery concept, one note each. Generated by `mw.py sync`; don't edit inside the block.\n")
    idx.write_text(replace_block(text, "index", body), encoding="utf-8")


def cmd_sync(a):
    ctx = Ctx(need_agent=False)
    sync(ctx.vault, ctx.op, ctx.root)
    print("roster, map, index regenerated")


# ---------- code copying for notes ----------

def file_at(repo, commit, path):
    r = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"{path} not in {commit}: {r.stderr.strip()}")
    return r.stdout.splitlines()


def changed_files(repo, commit):
    has_parent = subprocess.run(["git", "rev-parse", "--verify", "-q", f"{commit}^"], cwd=repo,
                                capture_output=True).returncode == 0
    if has_parent:
        out = git("diff", "--name-status", f"{commit}^", commit, cwd=repo)
    else:
        out = git("show", "--name-status", "--format=", commit, cwd=repo)
    files = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append((parts[0][0], parts[-1]))
    return files, has_parent


def changed_ranges(repo, commit, path, has_parent):
    if not has_parent:
        return None
    diff = git("diff", "-U0", f"{commit}^", commit, "--", path, cwd=repo)
    lines = []
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines += range(start, start + count)
    return compress(sorted(set(lines)))


def compress(nums):
    if not nums:
        return []
    out, s, p = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == p + 1:
            p = n
            continue
        out.append((s, p))
        s = p = n
    out.append((s, p))
    return out


def cmd_batch_info(a):
    root = repo_root()
    commit = git("rev-parse", "--short", a.commit, cwd=root).strip()
    files, has_parent = changed_files(root, commit)
    print(f"commit {commit}: {git('log', '-1', '--format=%s', commit, cwd=root).strip()}\n")
    for status, path in files:
        if status == "D":
            print(f"## {path} (deleted)\n")
            continue
        code = file_at(root, commit, path)
        ranges = changed_ranges(root, commit, path, has_parent) if status != "A" else None
        label = "new" if status == "A" else "changed"
        rtxt = "whole file" if ranges is None else ", ".join(f"{s}-{e}" for s, e in ranges) or "none"
        print(f"## {path} ({label}, {len(code)} lines; changed lines: {rtxt})")
        show = set(range(1, len(code) + 1))
        if ranges is not None and len(code) > 200:
            show = {n for s, e in ranges for n in range(max(1, s - 3), min(len(code), e + 3) + 1)}
        width = len(str(len(code)))
        for i, line in enumerate(code, 1):
            if i in show:
                print(f"{i:>{width}} | {line}")
        print()


CODE_RE = re.compile(r"\{\{(code|fullcode)\s+(\S+)(?:\s+(\d+)-(\d+))?\}\}")


def render_note(repo, note, commit=None):
    note = Path(note)
    fm, _ = read_fm(note)
    commit = commit or fm.get("commit")
    if not commit:
        die(f"{note.name}: no commit in frontmatter and none given")
    text = note.read_text(encoding="utf-8")
    cache = {}

    def sub(m):
        kind, path, s, e = m.group(1), m.group(2), m.group(3), m.group(4)
        if path not in cache:
            cache[path] = file_at(repo, commit, path)
        lines = cache[path]
        if not s:
            s, e = 1, len(lines)
        elif not (1 <= int(s) <= int(e) <= len(lines)):
            die(f"{note.name}: {path} {s}-{e} out of range (file has {len(lines)} lines)")
        s, e = int(s), int(e)
        lang = LANG.get(Path(path).suffix, "")
        chunk = "\n".join(lines[s - 1:e])
        if kind == "fullcode":
            quoted = "\n".join("> " + l if l else ">" for l in (f"```{lang}\n{chunk}\n```").splitlines())
            return f"> [!example]- Full file: `{path}` @ {commit}\n{quoted}"
        return f"```{lang}\n{chunk}\n```"

    new, n = CODE_RE.subn(sub, text)
    note.write_text(new, encoding="utf-8")
    return n


def cmd_render(a):
    root = repo_root()
    total = 0
    for note in a.notes:
        n = render_note(root, note, a.commit)
        total += n
        print(f"{Path(note).name}: {n} code block(s) filled")
    ctx = Ctx(need_agent=False)
    sync(ctx.vault, ctx.op, ctx.root)


# ---------- numbering / handles / inbox ----------

def cmd_next(a):
    ctx = Ctx(need_agent=False)
    if a.kind in ("batch", "challenge", "adr"):
        folder, prefix = {"batch": ("Batches", "B"), "challenge": ("Challenges", "C"),
                          "adr": ("Decisions", "ADR-")}[a.kind]
        nums = [int(m.group(1)) for p in (ctx.op / folder).glob("*.md")
                if (m := re.match(rf"{re.escape(prefix)}(\d+)", p.name))]
        print(f"{prefix}{(max(nums) + 1 if nums else 1):03d}")
    else:  # pattern <category>
        cat = (a.category or "").strip().lower()
        if not cat:
            die("pattern needs a category, e.g. next pattern 'array searching'")
        nums = [int(fm.get("number", 0)) for _, fm in patterns(ctx.op)
                if str(fm.get("category", "")).lower() == cat]
        print(max(nums) + 1 if nums else 1)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def cmd_handle(a):
    ctx = Ctx(need_agent=False)
    q = norm(" ".join(a.query))
    hits = []
    for p, fm in patterns(ctx.op):
        al = fm.get("aliases") or []
        al = [al] if isinstance(al, str) else al
        names = [fm["handle"], p.stem, *al]
        if any(q == norm(n) for n in names):
            hits = [(p, fm)]
            break
        if any(q in norm(n) for n in names):
            hits.append((p, fm))
    if not hits:
        die(f"no handle matches '{' '.join(a.query)}' (see Map.md)", 2)
    for p, fm in hits:
        _, loc = handle_location(ctx.root, fm)
        print(f"{fm['handle']} → {loc} · symbol {fm.get('symbol')} · note: {p}")


def cmd_inbox(a):
    ctx = Ctx()
    target = ctx.op / "Agents" / slug(a.agent) / "Inbox.md"
    if not target.exists():
        die(f"no agent '{a.agent}' in this operation")
    with target.open("a", encoding="utf-8") as f:
        f.write(f"- [ ] {today()} from **{ctx.agent}**: {' '.join(a.text)}\n")
    print(f"queued for {a.agent}")


def open_inbox(agent_dir):
    p = agent_dir / "Inbox.md"
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("- [ ]")] if p.exists() else []


def open_challenges(op, agent=None):
    out = []
    for p in sorted((op / "Challenges").glob("*.md")):
        fm, _ = read_fm(p)
        if fm.get("status", "open") == "open" and (agent is None or fm.get("agent") == agent):
            out.append(p.stem)
    return out


REQ_STAMP = ".mw-requirements"


def req_hash(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def has_file(root, ref, path):
    return subprocess.run(["git", "cat-file", "-e", f"{ref}:{path}"], cwd=root,
                          capture_output=True).returncode == 0


def deps_notice(root):
    """None, or (title, advice) when this worktree can't run the project's Python code yet."""
    req, venv = root / "requirements.txt", root / ".venv"
    if req.exists():
        if not venv.exists():
            return ("requirements.txt exists but .venv doesn't",
                    f"Run `{SCRIPT} setup` before running code or tests.")
        stamp = venv / REQ_STAMP
        if stamp.exists() and stamp.read_text().strip() != req_hash(req):
            return ("requirements.txt changed since .venv was built",
                    f"Run `{SCRIPT} setup` to install the new packages.")
        return None
    here = git("rev-parse", "--abbrev-ref", "HEAD", cwd=root, check=False).strip()
    main = next((b for b in ("main", "master") if has_file(root, b, ".mw.json")), None)
    if main and main != here and has_file(root, main, "requirements.txt"):
        return (f"{main} has requirements.txt but this branch doesn't",
                f"Merge it in (`git merge {main}`), then `{SCRIPT} setup`.")
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=root, check=False).split()
    waiting = [b for b in refs if b not in (here, main) and has_file(root, b, "requirements.txt")]
    if waiting:
        return (f"requirements.txt exists only on unmerged branch(es): {', '.join(waiting)}",
                f"Code here can't import those packages yet. Ask the user to merge "
                f"{', '.join(waiting)} into {main or 'main'}, then `git merge {main or 'main'}` and `{SCRIPT} setup`.")
    return None


def setup_commands(root):
    p = root / ".superset" / "config.json"
    return json.loads(p.read_text()).get("setup", []) if p.exists() else []


def cmd_setup(a):
    root = repo_root()
    if not root:
        die("not in a git repo")
    for c in setup_commands(root):
        print(f"$ {c}")
        r = subprocess.run(c, shell=True, cwd=root)
        if r.returncode != 0:
            die(f"setup step failed ({r.returncode}): {c}")
    req, venv = root / "requirements.txt", root / ".venv"
    if req.exists() and venv.exists():
        (venv / REQ_STAMP).write_text(req_hash(req) + "\n")
    print("setup done")


def vault_has_remote(vault):
    return bool(git("remote", cwd=vault, check=False).strip())


# ---------- checkpoint / vault commit ----------

def cmd_stamp(a):
    ctx = Ctx()
    set_fm(ctx.card, checkpoint=now().isoformat(timespec="minutes"), updated=today())
    n = len(read_text_lines(ctx.card))
    roster(ctx.op)
    print(f"card stamped ({n} lines{'; OVER BUDGET' if n > CARD_MAX else ''})")


def read_text_lines(p):
    return Path(p).read_text(encoding="utf-8").splitlines()


def cmd_commit_vault(a):
    ctx = Ctx(need_agent=False)
    v = ctx.vault
    git("add", "-A", ".", cwd=v)
    if not git("status", "--porcelain", cwd=v).strip():
        print("vault: nothing to commit")
        return
    for _ in range(3):
        r = subprocess.run(["git", "commit", "-q", "-m", a.message], cwd=v, capture_output=True, text=True)
        if r.returncode == 0:
            break
        if "index.lock" not in r.stderr:
            die(r.stderr.strip())
        import time
        time.sleep(1)
    msg = f"vault: committed '{a.message}'"
    if git("remote", cwd=v).strip():
        r = subprocess.run(["git", "push", "-q"], cwd=v, capture_output=True, text=True)
        msg += "; pushed" if r.returncode == 0 else f"; PUSH FAILED: {r.stderr.strip()}"
    else:
        msg += "; no remote configured, not pushed"
    print(msg)


# ---------- session hooks ----------

def hook_input():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def strip_fm(path):
    body = read_fm(path)[1]
    return re.sub(r"^<!-- \w+:(start|end) -->\n?", "", body, flags=re.M).strip()


def cmd_context(a):
    data = hook_input()
    root = repo_root(data.get("cwd"))
    if not root or not (root / ".mw.json").exists():
        return
    ctx = Ctx(start=root, need_agent=False)
    if not ctx.agent:
        register(ctx, quiet=True)
    fm, card_body = read_fm(ctx.card)
    _, learner = learner_load(ctx.vault)
    due = [r for r in learner.values() if r.get("review", "9999") <= str(today())]
    counts = {lv: sum(1 for r in learner.values() if r["level"] == lv) for lv in LEVELS}
    recent = sorted(learner.values(), key=lambda r: r.get("seen", ""), reverse=True)[:8]
    pending = journal_lines_since(ctx.agent_dir, fm.get("checkpoint"))
    inbox = open_inbox(ctx.agent_dir)
    others = [c.parent.name for c in (ctx.op / "Agents").glob("*/Card.md") if c.parent.name != ctx.agent]
    first = fm.get("checkpoint", "never") == "never" and not pending
    role = str(fm.get("role", "unset")).strip()
    op_text = (ctx.op / "Operation.md").read_text(encoding="utf-8")

    out = [f"<model-workflow>",
           f"You are agent **{ctx.agent}** in Operation **{ctx.op_name}** (Model-Workflow). "
           f"Mode: **{fm.get('mode', 'model')}**. Load the `model-workflow` skill now and follow it; "
           f"it tells you which mode file to read.",
           f"Shared memory: `.op/` → {ctx.op}  ·  Global learner: {learner_path(ctx.vault)}",
           f"Journal every exchange: `{SCRIPT} journal <{'|'.join(JOURNAL_KINDS)}> \"text\"` "
           f"(or `journal skip` for small talk). A Stop hook enforces this.",
           "", "## Operation.md", strip_fm(ctx.op / "Operation.md"),
           "", f"## Your Card (Agents/{ctx.agent}/Card.md)", card_body.strip(),
           "", "## Learner snapshot (full file: Me/Learner.md; query: "
               f"`{SCRIPT} learner known`)",
           "levels: " + " · ".join(f"{lv} {counts[lv]}" for lv in LEVELS),
           "due for review: " + (", ".join(f"{r['concept']} ({r['level']})" for r in due[:10]) or "none"),
           "recent: " + (", ".join(f"{r['concept']} ({r['level']}, fade {r['fade']})" for r in recent) or "none")]
    unchecked = sorted((r["concept"] for r in learner.values() if not checked(r)), key=str.lower)
    if unchecked:
        out += [f"never checked ({len(unchecked)}; taught but not verified): " + ", ".join(unchecked[:10])
                + (" …" if len(unchecked) > 10 else "")]
    chal = open_challenges(ctx.op, ctx.agent)
    if chal:
        out += ["", "## Open challenges (yours): " + ", ".join(chal)
                + " — ask how the learner is getting on before starting anything new"]
    deps = deps_notice(ctx.root)
    if deps:
        out += ["", f"## Setup: {deps[0]}", deps[1]]
    news = sibling_news(ctx.op, ctx.agent)
    if news:
        out += ["", "## Sibling news (built/decided since their last checkpoint)", *news]
    if "_One paragraph" in op_text:
        out += ["", "## Operation Goal is empty",
                "Before planning anything, agree the Goal with the user (one paragraph: what is built or "
                "learned, for whom, and what the learner already knows) and write it into the ## Goal "
                "section of .op/Operation.md."]
    if not learner:
        out += ["", "## Learner model is empty",
                "Run a 2-minute intake: ask what the user already knows in this area, then "
                f"`{SCRIPT} introduce intake \"<Concept>\" ...`. Self-report counts as `seen`, fade 1; "
                "levels above that only come from `learner check`."]
    if inbox:
        out += ["", f"## Inbox: {len(inbox)} open question(s) from other agents — answer them first",
                *inbox[:10]]
    if first:
        out += ["", "## First session for this agent",
                (f"Your role is set: {role}. Confirm it with the user in one line."
                 if role not in ("", "unset") else
                 "Your Card is empty. Ask the user what this agent's role is, then set it with "
                 f"`{SCRIPT} register --role \"...\"`.")
                + (f" Before starting work, read the **For other agents** section of these Cards: "
                   + ", ".join(f".op/Agents/{o}/Card.md" for o in others) + "." if others else "")]
    elif len(pending) >= LAZY_CHECKPOINT:
        out += ["", f"## Housekeeping: {len(pending)} journal lines since your last checkpoint",
                "Before other work, run the checkpoint procedure (`/op checkpoint`: spawn mw-clerk)."]
    out.append("</model-workflow>")
    print("\n".join(out))


def sibling_news(op, me, per_agent=3):
    out = []
    for card in sorted((op / "Agents").glob("*/Card.md")):
        name = card.parent.name
        if name == me:
            continue
        since = read_fm(card)[0].get("checkpoint")
        lines = [l for _, l in journal_lines_since(card.parent, since)
                 if re.match(r"^- \d\d:\d\d · (built|decided) · ", l)]
        out += [f"- **{name}** {l[2:]}" for l in lines[-per_agent:]]
    return out


def cmd_hook_prompt(a):
    data = hook_input()
    root = repo_root(data.get("cwd"))
    if not root or not (root / ".op-agent").exists():
        return
    ctx = Ctx(start=root)
    ctx.save_state(prompted=dt.datetime.now().isoformat())


def cmd_hook_stop(a):
    data = hook_input()
    root = repo_root(data.get("cwd"))
    if not root or not (root / ".op-agent").exists() or data.get("stop_hook_active"):
        return
    ctx = Ctx(start=root)
    s = ctx.state()
    prompted, journaled = s.get("prompted"), s.get("journaled")
    if not prompted:
        return
    if journaled and journaled >= prompted:
        return
    print(json.dumps({"decision": "block", "reason":
        "Model-Workflow: this exchange isn't in your journal yet. Append 1–3 lines with "
        f"`{SCRIPT} journal <kind> \"...\"` (kinds: {', '.join(JOURNAL_KINDS)}), "
        f"or `{SCRIPT} journal skip` if nothing worth recording happened. Then stop."}))


# ---------- status / lint ----------

def cmd_status(a):
    ctx = Ctx(need_agent=False)
    print(f"Operation: {ctx.op_name}  ({ctx.op})")
    print(f"This worktree: agent {ctx.agent or '(unregistered)'}\n")
    for card in sorted((ctx.op / "Agents").glob("*/Card.md")):
        fm, _ = read_fm(card)
        pend = len(journal_lines_since(card.parent, fm.get("checkpoint")))
        inbox = len(open_inbox(card.parent))
        print(f"- {fm.get('agent')}: {fm.get('mode')}, {fm.get('status')}, role: {fm.get('role')}; "
              f"{pend} journal lines since checkpoint; {inbox} open inbox")
    _, learner = learner_load(ctx.vault)
    due = [r["concept"] for r in learner.values() if r.get("review", "9999") <= str(today())]
    print(f"\nLearner: {len(learner)} concepts; due for review: {', '.join(due) or 'none'}")
    print(f"Batches: {len(list((ctx.op / 'Batches').glob('*.md')))} · "
          f"Patterns: {len(patterns(ctx.op))} · Decisions: {len(list((ctx.op / 'Decisions').glob('*.md')))}")
    chal = open_challenges(ctx.op)
    if chal:
        print(f"Open challenges: {', '.join(chal)}")
    if not vault_has_remote(ctx.vault):
        print(f"WARNING: vault {ctx.vault} has no git remote; commit-vault only commits locally (no backup)")
    deps = deps_notice(ctx.root)
    if deps:
        print(f"WARNING: {deps[0]}. {deps[1]}")


def all_note_names(vault):
    names = set()
    for p in vault.rglob("*.md"):
        if ".obsidian" in p.parts or ".trash" in p.parts:
            continue
        names.add(p.stem.lower())
        parts = p.relative_to(vault).with_suffix("").parts
        for i in range(len(parts)):
            names.add("/".join(parts[i:]).lower())
        fm, _ = read_fm(p)
        al = fm.get("aliases") or []
        for x in ([al] if isinstance(al, str) else al):
            names.add(str(x).lower())
    return names


FENCE_RE = re.compile(r"^\s*(?:>\s*)*(```|~~~)")


def strip_code(text):
    """Text without fenced blocks (also inside callouts) and inline code, for link scanning."""
    out, fenced = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            out.append(re.sub(r"`[^`\n]*`", "", line))
    return "\n".join(out)


def cmd_lint(a):
    ctx = Ctx(need_agent=False)
    issues = []
    op_lines = len(read_text_lines(ctx.op / "Operation.md"))
    if op_lines > OPERATION_MAX + 20:  # the roster table is generated; allow for it
        issues.append(f"Operation.md is {op_lines} lines (budget {OPERATION_MAX} + roster)")
    for card in sorted((ctx.op / "Agents").glob("*/Card.md")):
        fm, _ = read_fm(card)
        n = len(read_text_lines(card))
        if n > CARD_MAX:
            issues.append(f"{card.parent.name}/Card.md is {n} lines (budget {CARD_MAX}) → checkpoint it")
        pend = len(journal_lines_since(card.parent, fm.get("checkpoint")))
        if pend >= LAZY_CHECKPOINT:
            issues.append(f"{card.parent.name}: {pend} journal lines since checkpoint")
        for line in open_inbox(card.parent):
            m = re.match(r"- \[ \] (\d{4}-\d\d-\d\d)", line)
            if m and (today() - dt.date.fromisoformat(m.group(1))).days > 3:
                issues.append(f"{card.parent.name}: inbox item older than 3 days: {line[6:80]}")
    names = all_note_names(ctx.vault)
    for p in sorted(ctx.op.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(ctx.op)
        if "{{code" in text or "{{fullcode" in text:
            issues.append(f"{rel}: unrendered {{{{code}}}} markers → mw.py render")
        if rel.parts[0] in ("Agents",) and "Journal" in rel.parts:
            continue
        for link in re.findall(r"\[\[([^\]|#]+)", strip_code(text)):
            t = link.strip().rstrip("\\").lower()
            if t and t not in names:
                issues.append(f"{rel}: broken link [[{link.strip()}]]")
    _, learner = learner_load(ctx.vault)
    for folder in ("Batches", "Challenges"):
        for p in sorted((ctx.op / folder).glob("*.md")):
            cs = read_fm(p)[0].get("concepts") or []
            for c in ([cs] if isinstance(cs, str) else cs):
                c = re.sub(r"^\[\[|\]\]$", "", str(c)).split("|")[0].strip()
                if c and c.lower() not in learner:
                    issues.append(f"{folder}/{p.stem}: concept [[{c}]] not in Learner.md "
                                  f"→ mw learner set \"{c}\" --new --evidence \"{p.stem[:4]} introduced\"")
    for card in sorted((ctx.op / "Agents").glob("*/Card.md")):
        if ROLE_PLACEHOLDER in card.read_text(encoding="utf-8"):
            has = str(read_fm(card)[0].get("role", "unset")) not in ("", "unset")
            issues.append(f"{card.parent.name}/Card.md: Role section empty → "
                          + ("mw sync (copies it from frontmatter)" if has else 'mw register --role "..."'))
    if not vault_has_remote(ctx.vault):
        issues.append("vault has no git remote: commit-vault never backs it up")
    for p, fm in patterns(ctx.op):
        status, loc = handle_location(ctx.root, fm)
        if status == "stale":
            issues.append(f"stale handle '{fm['handle']}': {loc}")
    report = "\n".join(f"- {i}" for i in issues) or "- clean"
    print(f"lint {ctx.op_name}: {len(issues)} issue(s)\n{report}")
    if a.write:
        (ctx.op / "Lint.md").write_text(f"# Lint · {now():%Y-%m-%d %H:%M}\n\n{report}\n", encoding="utf-8")
    sys.exit(1 if issues and a.strict else 0)


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(prog="mw.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("init", help="make a repo an Operation and create its vault folder")
    p.add_argument("--repo", required=True)
    p.add_argument("--op", required=True, help="Operation name (vault folder name)")
    p.add_argument("--vault", default=str(DEFAULT_VAULT))
    p.add_argument("--model", default="claude-opus-5-5", help="main agent model for this repo")
    p.add_argument("--setup", action="append", help="extra Superset setup command (repeatable)")
    p.set_defaults(f=cmd_init)

    p = sp.add_parser("register", help="register this worktree as an agent (Superset setup runs this)")
    p.add_argument("--name")
    p.add_argument("--mode", choices=["learn", "build", "model"])
    p.add_argument("--role")
    p.set_defaults(f=cmd_register)

    p = sp.add_parser("journal", help="append a journal line for this agent")
    p.add_argument("kind")
    p.add_argument("text", nargs="*")
    p.set_defaults(f=cmd_journal)

    p = sp.add_parser("learner", help="global learner model")
    p.add_argument("action", choices=["show", "known", "set", "check"])
    p.add_argument("concept", nargs="?")
    p.add_argument("result", nargs="?", help="pass|fail for check")
    p.add_argument("--level")
    p.add_argument("--fade", type=int)
    p.add_argument("--evidence")
    p.add_argument("--due", action="store_true")
    p.add_argument("--unchecked", action="store_true", help="show: only concepts never checked")
    p.add_argument("--new", action="store_true", help="set/check: allow a concept not seen before")
    p.set_defaults(f=cmd_learner)

    p = sp.add_parser("introduce", help="register concepts a batch/challenge/intake brings in")
    p.add_argument("source", help="B0NN, C00N, or 'intake' (self-report: seen, fade 1)")
    p.add_argument("concepts", nargs="+")
    p.set_defaults(f=cmd_introduce)

    p = sp.add_parser("batch-info", help="files, changed lines and numbered code of a commit")
    p.add_argument("commit", nargs="?", default="HEAD")
    p.set_defaults(f=cmd_batch_info)

    p = sp.add_parser("render", help="replace {{code path a-b}} markers with code from the commit")
    p.add_argument("notes", nargs="+")
    p.add_argument("--commit")
    p.set_defaults(f=cmd_render)

    p = sp.add_parser("next", help="next id: batch | challenge | adr | pattern <category>")
    p.add_argument("kind", choices=["batch", "challenge", "adr", "pattern"])
    p.add_argument("category", nargs="?")
    p.set_defaults(f=cmd_next)

    p = sp.add_parser("handle", help="resolve a handle like 'array searching 1' to file:line")
    p.add_argument("query", nargs="+")
    p.set_defaults(f=cmd_handle)

    p = sp.add_parser("inbox", help="leave a question in another agent's inbox")
    p.add_argument("agent")
    p.add_argument("text", nargs="+")
    p.set_defaults(f=cmd_inbox)

    sp.add_parser("sync", help="regenerate roster, Map handles, concept Index").set_defaults(f=cmd_sync)
    sp.add_parser("stamp", help="mark this agent's Card as checkpointed now").set_defaults(f=cmd_stamp)
    sp.add_parser("status", help="operation overview").set_defaults(f=cmd_status)
    sp.add_parser("setup", help="re-run this repo's .superset/config.json setup (venv etc.)").set_defaults(f=cmd_setup)

    p = sp.add_parser("commit-vault", help="commit (and push, if a remote exists) the vault")
    p.add_argument("message")
    p.set_defaults(f=cmd_commit_vault)

    p = sp.add_parser("lint", help="budgets, broken links, stale handles, unrendered code")
    p.add_argument("--write", action="store_true", help="also write Lint.md in the operation")
    p.add_argument("--strict", action="store_true", help="exit 1 when issues are found")
    p.set_defaults(f=cmd_lint)

    for name, f in [("context", cmd_context), ("hook-prompt", cmd_hook_prompt), ("hook-stop", cmd_hook_stop)]:
        sp.add_parser(name, help="(hook)").set_defaults(f=f)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
