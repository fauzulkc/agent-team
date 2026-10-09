---
name: team-reevaluate
description: "🔁 Re-evaluate a seated team against how it actually works and what the repo needs now: measures each seat's commits, worker runs, inbox and blocked lines over a window, re-scans the repo against the setup baseline, proposes seats to add, retire, merge, unmerge or split with the evidence for each, applies what the owner approves, records the owner's words as a decision and tells every seat it touches. Use when the user says \"re-evaluate the team\", \"review the team\", \"do we need more seats\", \"merge seats\", \"split a seat\", \"retire a seat\", \"resize the team\", \"the team feels too big\" or \"too small\", or when a milestone closes and the owner asks. Use in a project whose docs/TEAM.md seats a team. Do NOT use to seat a first team (team-setup), to act as a seat, to change a decision, or for any outward act."
---

# 🔁 Team re-evaluation

**Single loyalty: the team the work needs now, not the one it needed at setup.** A seat with no work
is overhead; a session holding five busy roles is a bottleneck. Measure both, propose, and change
nothing without the owner's yes.

**The scripts live in the `team-setup` skill**, at `${CLAUDE_SKILL_DIR}/../team-setup/scripts/`
(`reevaluate.py`, `scaffold.py`, `scan.py`), with the seat contract at
`${CLAUDE_SKILL_DIR}/../team-setup/references/seat-contract.md`. **If that path is missing**, locate
team-setup's folder via the skill list and use it; below, `$SETUP` stands for that folder. Run every
command from the project root.

---

## What this never does

- **No outward act.** Nothing is published, sent, bought or signed; the owner's acts stay the owner's.
- **Never retires the CEO or the Bar Raiser**, and never folds the Bar Raiser into a merge after
  setup: the scaffold keeps it seated, so the merge would leave two seats holding one rulebook.
- **Never deletes an authored rulebook.** A derived rulebook is archived to `docs/team/retired/` by
  the script; a catalogue or merged copy the project edited is archived by hand first (step 5).
- **Never changes a decision.** A team change is one new row in `docs/DECISIONS.md` carrying the
  owner's words verbatim; earlier rows stand as written. A proposal that contradicts a decision is
  dropped and named, never put to the owner as if the decision were not there.
- **Never applies what the owner did not approve**, and never re-proposes a retired seat unless its
  signal is new since setup.

## 1 · Confirm a team is seated

`docs/TEAM.md` with a roster must exist. **No roster means no team: hand to `team-setup`.** Then
catch up: `git log` since the last team change (`git log --oneline -- docs/TEAM.md`), new rows in
`docs/DECISIONS.md`, the tracker if one is kept. A peer's uncommitted work does not count yet.

## 2 · Measure

```
python3 $SETUP/scripts/reevaluate.py --root . --days 30 --out docs/team/reevaluation.json
```

**Thirty days unless the owner names another window.** It prints the report (activity per seat,
repo signals new or gone since `docs/team/scan.json`, proposals, and what it noted but did not
propose) and writes the proposed plan. `--json` prints each proposal with the exact spec and retire
entries it puts in that plan. It changes nothing in the project.

## 3 · Read the report yourself before the owner does

**The script counts; you judge.** Check every proposal against what you know, drop or adjust what is
wrong, and keep one line per change saying why:
- **New is not idle.** A seat seated inside the window has no history yet: drop its retire or merge.
  The decision row that seated it carries the date.
- **Quiet can be seasonal.** Funding between rounds, Payments before launch, Compliance before an
  audit, Security between releases: if the active milestone, the tracker or owner-questions holds
  work for it, it stays.
- **Unprefixed commits hide work.** Activity counts commits whose subject starts with the seat's
  team (`design:`, `design(web):`). A large "unattributed" count means seats commit without prefixes:
  read `git log` on the paths the seat's brief owns before calling it quiet, and say so to the owner.
- **A check never joins a builder.** Drop any merge that puts the Bar Raiser, Scope Trimmer, User
  or Security in one session with a seat whose work it checks, and any merge that takes in the Bar
  Raiser.
- **A retire leaves no orphan work.** Each retiring seat's open tracker lines, owner questions,
  inbox lines and register name a new holder, or the retire waits.
- **An add needs live evidence.** Open the signal's evidence path: a dependency nothing imports, or
  an example folder, is not a role.
- **An unmerge needs strain, not volume.** A merged seat carrying most commits may be the project's
  real work; unmerge when its stop lines show it blocked or queueing one role behind another.
- **A split names its sibling**, and each half's scope ends where the other's starts.
- **Decisions outrank the script.** Search `docs/DECISIONS.md` for each seat a proposal names.

Anything you add on your own evidence (a seat the script missed) goes in with that evidence.

## 4 · Ask the owner once

One question, in `docs/TEAM.md §7`'s shape and plain words: seat names, never team slugs or codes.
- **The proposals as a list**, each with its evidence in words ("Design: no commits, no worker runs,
  nothing waiting in its inbox for 30 days, and nothing in the repo calls for it").
- **What you dropped**, one line each with the reason.
- **What changes for the owner**: sessions to open or close, and any new seat that needs its
  rulebook written before it works.
- **Options:** "Apply all (Recommended)", "Apply some" (they name which), "Change nothing".

**No proposals means one line to the owner, not a question:** the team fits the work, with the
measurement. **Change nothing is a complete result**: record nothing, keep the report.

## 5 · Apply exactly what was approved

**Edit `docs/team/reevaluation.json` to the approved set.** Remove both halves of a declined proposal:

| Proposal | In `seats` | In `retire` |
|---|---|---|
| add | its spec | — |
| retire | — | the seat |
| merge | the merged seat's spec | each member |
| unmerge | each member's spec | the merged seat |
| split | each new seat's spec | the seat it splits |

**Before a retire, archive any rulebook the project edited.** If `git log --oneline --
.claude/skills/seat-<team>/` shows commits after the one that seated it, copy that folder to
`docs/team/retired/` first: the scaffold archives only derived rulebooks. Then:

```
python3 $SETUP/scripts/scaffold.py --root . --plan docs/team/reevaluation.json \
  --record "<the owner's answer, verbatim>"
```

It adds the roster rows, rulebooks and briefs (a merged seat's brief carries its members' briefs),
retires the listed seats (brief kept with a "Retired" line on top, worker removed), appends the
decision row and regenerates the workers. It prints `NEEDS AUTHORING` for each new derived seat.

## 6 · Author new seats and fill their briefs

**A seat never works from a rulebook written for someone else.** For each `NEEDS AUTHORING` seat,
rewrite `.claude/skills/seat-<team>/SKILL.md` per `$SETUP/references/seat-contract.md`: research the
role, name the sibling of a split, delete the block last. Fill every new brief from the project's
facts: fold a merged seat's carried-over briefs into one set of sections; a seat brought back by an
unmerge keeps its old brief, so delete its "Retired" line and refresh it from the merged seat's brief.

## 7 · Reset the baseline

```
python3 $SETUP/scripts/scan.py --root . --save
```

**The next re-evaluation diffs against today**, so a signal already answered is never raised twice.

## 8 · Check

```
python3 scripts/gen-team-agents.py --check
```

**Green before anyone is told.** It fails on a stale or orphaned worker and on any seated rulebook
still carrying `AUTHORING NEEDED`.

## 9 · Tell every seat it touches, then the owner

**One inbox line per affected seat**, in `scratchpad/team/inbox/<team>.md`, `docs/TEAM.md §5`'s format,
signed as the seat this session holds (a session holding none signs `🔁 Team re-evaluation`):

```
<date> · 🧭 CEO → 💰 Money · HANDOFF · you now hold Funding and Payments; both briefs carried into yours · docs/team/money.md
<date> · 🧭 CEO → 🛎️ Chief of Staff · FYI · team changed: Money seated, Funding and Payments retired · docs/DECISIONS.md, last row
```

**A retired seat's inbox has no reader:** move its unread lines to the seat that took its work. Tell
the Chief of Staff (or the CEO) so the tracker's lines move with the work.

To the owner, in plain words: what changed, **which sessions to close** (each retired or merged-away
seat), **which to open** (`/seat-<team> catch up and work your inbox`), and that **a session opened
before the change holds the old rulebook**: reopen it or send the command again; new workers load
only in a new session.

## 10 · Commit

Check `git diff --cached` first (a peer's staged file rides along otherwise). Then `git add` the new
paths and `git commit -o <every path> -m "team: <what changed>"`: `docs/TEAM.md`, `docs/DECISIONS.md`,
`docs/team/` (briefs, `scan.json`, `seat-skills.lock`, `reevaluation.json`, `retired/`), the added and
removed `.claude/skills/seat-*` and `.claude/agents/*`. **Never `git add -A`, never a bare commit.**
Read `git show --stat HEAD`. Pushes follow the project's push rule.

---

## When to run it

**When the owner asks.** A good moment is when a milestone closes, or when a seat's stop lines keep
reading BLOCKED on the same peer. **Running it on a schedule is the owner's choice:** suggest it once,
after a milestone, and record the answer as a decision. Nothing schedules itself.
