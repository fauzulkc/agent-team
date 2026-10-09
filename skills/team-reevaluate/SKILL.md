---
name: team-reevaluate
description: "🔁 Change a seated team: re-evaluate it against how it actually works and what the repo needs now (each seat's commits, worker runs, inbox and blocked lines over a window; the repo against the setup baseline), propose seats to add, retire, merge, unmerge or split with the evidence for each and apply what the owner approves, or carry out a change the owner names. Records the owner's words as a decision, remembers what was declined, and tells every seat it touches. Use when the user says \"re-evaluate the team\", \"review the team\", \"do we need more seats\", \"add a seat\", \"add Sales to the team\", \"retire Design\", \"merge seats\", \"split a seat\", \"resize the team\", \"the team feels too big\" or \"too small\", or when a milestone closes and the owner asked for it then. Use in a project whose docs/TEAM.md seats a team. Do NOT use to seat a first team or sync rulebooks (team-setup), to act as a seat, to change a decision, or for any outward act."
---

# 🔁 Team re-evaluation

**Single loyalty: the team the work needs now, not the one it needed at setup.** A seat with no work
is overhead; a session holding five busy roles is a bottleneck. Measure both, propose, and change
nothing without the owner's yes.

**The scripts and the seat contract live in the `team-setup` skill**: `$SETUP` below is
`${CLAUDE_SKILL_DIR}/../team-setup` (`scripts/`, `references/seat-contract.md`); **if that path is
missing**, find team-setup's folder via the skill list. Run every command from the project root.

---

## What this never does

- **No outward act.** Nothing is published, sent, bought or signed.
- **Never leaves the team without a CEO or a Bar Raiser.** No proposal merges either after setup, and
  the scaffold refuses a retire that would leave either held by no seat (`not retired: …`).
- **Never deletes an authored or edited rulebook.** Retiring archives a derived, edited, untracked or
  project-own one to `docs/team/retired/`; only an unedited catalogue or merged copy is deleted.
- **Never changes a decision.** A team change is one new row in `docs/DECISIONS.md` with the owner's
  words verbatim; earlier rows stand. A proposal a decision contradicts is dropped and named.
- **Never asks twice.** A declined proposal is kept in `docs/team/declined.json` and a retired seat in
  its brief; neither comes back unless the repo shows a signal for it that is new since the baseline.

## Two ways in

- **"Re-evaluate the team"** (or a milestone closed and the owner asked for it then): steps 1 to 10.
- **The owner names the change** ("add Sales to the team", "retire Design", "merge Sales and SEO",
  "split the Frontend engineer per app"): step 1, step 11, then steps 6, 8, 9 and 10. **The owner's
  words are the approval**; no question unless the measurement cuts against them.

## 1 · Confirm a team is seated, and a baseline

`docs/TEAM.md` with a roster must exist. **No roster means no team: hand to `team-setup`.** **No
`docs/team/scan.json`** (a team seated with `--seats`, or before baselines existed): run
`python3 $SETUP/scripts/scan.py --root . --save` first and tell the owner the repo comparison starts
today. Then catch up: `git log` since the last team change (`git log --oneline -- docs/TEAM.md`), new
rows in `docs/DECISIONS.md`, the tracker, and the seat changes waiting under *For the next team
re-evaluation* in `docs/team/owner-questions.md` (step 3 weighs each; clear them once the owner has
answered). A peer's uncommitted work does not count yet.

## 2 · Measure

```
python3 $SETUP/scripts/reevaluate.py --root . --days 30 --out docs/team/reevaluation.json
```

**Thirty days unless the owner names another window.** It prints activity per seat, repo signals
new or gone since the baseline, the proposals (`- **<title>**: <why>`, in plain words), what it noted
but did not propose, and each proposal's key; it writes the plan (`--json` prints the specs) and
changes nothing else. **It already holds back** the CEO and the Bar Raiser, seats seated inside the
window, seats a signal or the team's size still calls for (derived roles and frontend splits
included), merges a check seat or size rules out, and what was declined or retired before.

## 3 · Read the report yourself before the owner does

**The script counts; you judge.** Check every proposal against what you know, and keep one line per
proposal you drop, saying why:
- **Quiet can be seasonal.** Funding between rounds, Payments before launch, Compliance before an
  audit, Security between releases: if the active milestone, the tracker or owner-questions holds
  work for it, it stays.
- **Unprefixed commits hide work.** Activity counts subjects starting with the seat's team
  (`design:`, `design(web):`). A large "unattributed" count means seats commit without prefixes:
  read `git log` on the paths the seat's brief owns before calling it quiet, and say so to the owner.
- **A retire leaves no orphan work.** Each retiring seat's open tracker lines, owner questions,
  inbox lines and register name a new holder, or the retire waits.
- **An add needs live evidence.** Open the signal's evidence path: a dependency nothing imports, or
  an example folder, is not a role.
- **An unmerge needs strain, not volume.** A merged seat carrying most commits may be the project's
  real work; unmerge when its stop lines show it blocked or queueing one role behind another.
- **A split names its sibling**, and each half's scope ends where the other's starts.
- **Decisions outrank the script.** Search `docs/DECISIONS.md` for each seat a proposal names.

**A proposal you drop stays in the plan:** the owner sees it under what you dropped, and it is
declined with the rest unless the owner takes it back. **A change the script missed** goes into the
plan's `proposals` before you ask, in the same shape (a unique `key` such as `add:<team>`, `action`,
`title`, `why` with your evidence, `signals: []`, `seats`, `retire`), so step 5 can name it.

## 4 · Ask the owner once

One question, in `docs/TEAM.md §7`'s shape and plain words: seat names, never team slugs or codes.
- **The proposals as a list**, each with its evidence in words ("📐 Design: no commits, no worker
  runs, nothing waiting in its inbox for 30 days, and nothing in the repo calls for it").
- **What you dropped**, one line each with the reason.
- **What changes for the owner**: sessions to open or close, and any new seat that needs its
  rulebook written before it works.
- **Options:** "Apply all (Recommended)", "Apply some" (they name which), "Change nothing".
- **Only when `docs/DECISIONS.md` holds no answer to it yet**, one more line: "Re-evaluate the team
  each time a milestone closes from now on? The Chief of Staff (or the CEO) would start it."

**No proposals: one line to the owner, not a question** (the team fits the work, with the
measurement). Nothing is recorded; the baseline stays.

## 5 · Apply exactly what was answered

```
python3 $SETUP/scripts/scaffold.py --root . --plan docs/team/reevaluation.json --only <keys> \
  --record "<the owner's answer, verbatim>" --question "<the question asked, in one line>"
```

**`<keys>` is the accepted proposals' keys**, comma-separated (every key put to the owner for "Apply
all"), or `none` for "Change nothing". **Every proposal not named is declined:** listed in the
decision row and kept in `docs/team/declined.json`, so it is not asked again on the same evidence.
It adds the rows, rulebooks and briefs, retires the listed seats (brief kept with a "Retired" line,
worker removed), brings a returning seat's brief back into use, appends the row, regenerates the
workers and prints `NEEDS AUTHORING` for each new derived seat. **A refusal changes nothing**
(`nothing was changed:`, one line per cause); a `not retired: …` line means the rest applied: tell
the owner which seat stayed, and why.

**"Change nothing"** records the declines and nothing else: go to step 9; the baseline stays.

## 6 · Author new seats and fill their briefs

**A seat never works from a rulebook written for someone else.** For each `NEEDS AUTHORING` seat,
rewrite `.claude/skills/seat-<team>/SKILL.md` per `$SETUP/references/seat-contract.md` (research the
role, name a split's sibling, delete the `AUTHORING NEEDED` line last), then run
`python3 scripts/gen-team-agents.py` to write its worker. A `restored:` seat is authored unless its
line says otherwise; a `note: an earlier copy … is archived` line means carrying that copy's project
edits over by hand. Fill every new brief from the project's facts: fold a merged seat's carried-over
briefs into one set of sections; refresh a seat brought back by an unmerge from the merged seat's.

## 7 · Reset the baseline, after an applied change only

```
python3 $SETUP/scripts/scan.py --root . --save
```

**The next re-evaluation diffs against today**, so a signal already answered is never raised twice.
Not after "Change nothing" (its declines are remembered instead), and not on the named path (signals
the owner has not seen stay new).

## 8 · Check

```
python3 scripts/gen-team-agents.py --check
```

**Green before anyone is told.** It fails on a stale, missing or orphaned worker, on a roster row that
does not parse, and on any seated rulebook still carrying `AUTHORING NEEDED`.

## 9 · Tell every seat it touches, then the owner

**One inbox line per affected seat**, in `scratchpad/team/inbox/<team>.md`, `docs/TEAM.md §5`'s format,
signed as the seat this session holds (a session holding none signs `🔁 Team re-evaluation`):

```
<date> · 🧭 CEO → 💰 Money · HANDOFF · you now hold Funding and Payments; both briefs carried into yours · docs/team/money.md
<date> · 🧭 CEO → 🛎️ Chief of Staff · FYI · team changed: Money seated, Funding and Payments retired · docs/DECISIONS.md, last row
```

**A retired seat's inbox has no reader:** move its unread lines to the seat that took its work. Tell
the Chief of Staff (or the CEO) so the tracker's lines move with the work. **A yes to re-evaluating
at each milestone** goes to the same seat as a `STANDING` line naming the decision row.

To the owner, in plain words: what changed, **which sessions to close** (each retired or merged-away
seat), **which to open and when** (a new seat when its work comes up, with
`/seat-<team> catch up and work your inbox`), **who they talk to** (the Chief of Staff, or the CEO
when none is seated now), and that **a session opened before the change holds the old rulebook**:
reopen it or send the command again.

## 10 · Commit

Check `git diff --cached` first (a peer's staged file rides along otherwise). Then `git add` the new
paths and `git commit -o <every path> -m "team: <what changed>"`: `docs/TEAM.md`, `docs/DECISIONS.md`,
`docs/team/` (briefs, `scan.json`, `seat-skills.lock`, `reevaluation.json`, `declined.json`, any
change plan, `retired/`), the added and removed `.claude/skills/seat-*` and `.claude/agents/*`.
**Never `git add -A`, never a bare commit.** Read `git show --stat HEAD`. Pushes follow the push rule.

## 11 · The owner named the change

1. **Measure the seats it names:** step 2's command without `--out`; read their rows, their open work
   (tracker, inbox, owner-questions) and `docs/DECISIONS.md`.
2. **Ask only when the measurement cuts against the request**: one question with the evidence and a
   recommendation ("📐 Design has 14 commits and 3 open tasks this month; retire it anyway?").
   **A merge the rules hold back** (the CEO or the Bar Raiser in any merge, a check seat with work it
   checks, Engineering & Platform past 2,000 source files) is not made: say why in one line, and what
   fits instead. Otherwise apply at once.
3. **Apply with the owner's words as the record.** Every run carries `--record "<their words>"`,
   `--question "<the change, in seat names>"` and `--project "<name>"` (the name in
   `docs/team/plan.json`, else in `docs/TEAM.md`'s first paragraph; without it a new brief names the
   folder). `--add <team>` adds a catalogue seat; `--retire <team>` retires one. **A role a merged
   seat holds** is refused by `--add` (`… is held by …`): unmerge it with
   `--add <each member> --retire <merged team>` (members: its lock entry's origin or `of`), and tell
   the owner its other roles get their own seats too. **A merge, a split or a new role** goes in
   `docs/team/change-<date>.json`, `{"project": …, "seats": [<specs>], "retire": [<teams>]}`, applied
   with `--plan`; write the specs as team-setup's step-4 table shows. **Never apply
   `reevaluation.json` with `--only` here:** it would decline proposals the owner never saw.

---

## When to run it

**When the owner asks**, or when a milestone closes once the owner has said yes to that (the Chief of
Staff, or the CEO, starts it). Seats stopping BLOCKED on one peer are a reason to suggest one.
