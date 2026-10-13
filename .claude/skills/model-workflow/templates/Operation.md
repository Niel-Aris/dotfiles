---
operation: {{op}}
repo: {{repo}}
created: {{date}}
---
# {{op}}

## Goal
_One paragraph: what is being built or learned, and for whom._

## Stack
_Decided in Decisions/ (ADRs). One line per layer._

## Roster
Generated from each agent's Card. Don't edit inside the block.
<!-- roster:start -->
<!-- roster:end -->

## Map of content
- [[Map]]: code handles (named patterns → file and symbol)
- `Batches/`: one note per Model-mode batch (= one commit)
- `Patterns/`: one note per named algorithm or pattern
- `Decisions/`: ADRs, only for real forks
- `Challenges/`: Learn-mode exercises

## Conventions
- 1 batch = 1 commit = 1 Batch note. Batches merge into `main` when the user approves.
- Agents write only their own `Agents/<name>/` folder, their own notes, and Learner lines through `mw.py learner`.
