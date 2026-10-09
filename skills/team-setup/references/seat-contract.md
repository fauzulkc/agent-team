# How to author a seat rulebook

Every seat's rulebook (`.claude/skills/seat-<team>/SKILL.md`) follows this contract, whether it came
from the catalogue, was derived for a role the catalogue doesn't hold, or was written by hand. A
**derived** rulebook arrives as a copy of its base, its paths already renamed to the new seat's, with
an `AUTHORING NEEDED` banner line under the H1. Until that line is gone the seat has no worker and the
generator's `--check` fails, so a seat never works from a rulebook written for someone else.

## Before writing

1. Read the project's `docs/TEAM.md` (the shared protocol). The rulebook **points to it** as
   `docs/TEAM.md §n`; it never restates tiers, message syntax, the inbox, git rules or the owner's
   report shape.
2. Read the seat's brief, `docs/team/<team>.md`: project facts live there, not in the rulebook.
3. Read the base rulebook it was derived from, and two or three neighbouring seats it hands off to,
   so the hand-off tables agree on both sides.
4. Research the role: three to five searches on how the best operator of this role works at a fast,
   early-stage company. Cite only pages you opened (`[read]`) or found (`[found]`); label anything
   second-hand `(secondary)`. When a split seat shares its base's role, research only what differs.

## The skeleton (these headings, in this order)

```
---
name: seat-<team>
description: "<mark> <one sentence: the role>. Use when … (the triggers). Use in a project whose docs/TEAM.md seats this role. Do NOT use for … (the seat-* skills it defers to)."   ≤ 700 characters
---

# <mark> <Seat>

**Single loyalty: <one line>.**

## 0 · The seat
## 1 · First action, every time
## 2 · How this seat thinks at a fast startup
## 3 · The method
## 4 · Team
## 5 · Rules and traps
## 6 · Done, stop, and report
```

| § | Holds |
|---|---|
| 0 | What it owns and does not own (a table; exact files and paths are in the brief); whom it reports to; its kind; "a decision in `docs/DECISIONS.md` outranks this rulebook and your brief" |
| 1 | Read the inbox (delete exactly the lines read) → `docs/TEAM.md` → the brief → `git log` since its last commit, new decisions, the tracker → a health check only if it uses a live service |
| 2 | 3–5 shifts written "from → to", each with its source; then its one-way doors (every check, every time) and two-way doors (decide in the seat, time-box, correct in place) |
| 3 | The role's core procedure, step by step |
| 4 | A table: task it delegates → tier by **name** (`team-quick`, `team-scout`, `team-check`, `<team>-worker`, `team-build`, `team-research`, `team-deep`) → what the contract must carry; steering (`docs/TEAM.md §3`); what other seats may call its team for while it is away, and what waits for it as a PROPOSAL; a hand-off table of peer seats by mark and name ("if seated") |
| 5 | Its rules and traps, each with a one-line reason; ends "Traps this project has paid for live in your brief; add new ones there." |
| 6 | Done means (plus the brief's *Done means here*); the stop line (`docs/TEAM.md §6`); the owner's report shape (`docs/TEAM.md §7`: plain words, no codes, decision first) |

## Hard rules

- **Seven sections, the mark in the description and the H1, the `name` equal to its folder.**
- **No model names**: tiers by name only, so a model change is one edit in `docs/TEAM.md` §2.
- **Project-neutral if it will be shared**; project facts go in the brief.
- **Bold the rule, then the reason.** Dense and imperative; 130–200 lines.
- **A check seat never signs off work its own seat built.** A split seat states its scope in §0 and
  names its sibling, and every hand-off between them goes through ASK or HANDOFF.
- **Delete the `AUTHORING NEEDED` banner line last**, then run `python3 scripts/gen-team-agents.py`
  (it writes the seat's worker now) and `python3 scripts/gen-team-agents.py --check` until it passes.
