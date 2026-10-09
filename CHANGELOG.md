# Changelog

## 1.3.0
- **Dynamic seats.** `team-setup` scans the repo (`scan.py`: signals with the evidence that raised
  each, and a size class: tiny, small, medium, large) and offers three teams, lean, recommended and
  full, every seat with its reason (`plan.py`). The owner picks one in setup's single question and
  may edit it.
- **Merged seats**: eight groups one session can hold while the work is small (Growth, Product &
  Design, Engineering & Platform, Quality, Money, Legal & Compliance, Data & ML, Customer), composed
  from their members' rulebooks with every rule kept and recomposed on sync. Check seats never merge
  into a seat whose work they check.
- **New seats**: roles no catalogue seat covers (hardware and firmware, smart contracts, desktop,
  browser extension) and one frontend seat per UI app are derived from a base rulebook and written
  for their role per `references/seat-contract.md` before they work (`seatgen.py`).
- **Eight new catalogue seats**, 29 in all: Mobile engineer, ML engineer, Data engineer, Security,
  Docs writer, Community & DevRel, Game designer, Localization.
- **`team-reevaluate`**, a new skill (`reevaluate.py`): measures each seat's commits, worker runs,
  inbox and blocked lines, re-scans the repo against the setup baseline, and proposes adding,
  retiring, merging, unmerging or splitting seats with the evidence for each; a retired seat is not
  proposed again without a new signal. Nothing changes without the owner's one answer.
- **`scaffold.py`** applies a plan (`--plan`), records the owner's words as a decision (`--record`),
  retires seats with their briefs kept (`--retire`), and records each rulebook's origin in
  `docs/team/seat-skills.lock`. **`gen-team-agents.py --check`** fails while any seated rulebook
  still carries `AUTHORING NEEDED`.
- **Tests**: `python3 -m unittest discover -s tests` runs the scan, planner, scaffold and
  re-evaluation end to end on invented fixture projects.
- Docs: how the team is sized and re-evaluated, the catalogue with merged seats and new roles, the
  walkthrough's three options and its month-later re-evaluation, and when the owner is asked.

## 1.2.0
- Publishable docs: how it works and what it can handle, orchestration diagrams, when the owner
  is asked, the seat catalogue, a prompt-by-prompt walkthrough, and a seated example project (Tally).
- The shared rulebook template gains *When the owner is asked, and when not* (§7).
- Seat rulebooks made domain-neutral throughout.

## 1.1.0
- Installable as a Claude Code plugin with its own marketplace.
- Seat rulebooks travel inside `team-setup` and are copied into each project's `.claude/skills/`
  (workers cannot preload a skill that lives only in a plugin), with a hash lock and `--sync`.

## 1.0.0
- 21 seat rulebooks, `team-setup`, the scaffold, the worker generator, seven model tiers.
