---
name: team-setup
description: "🧩 Seat an AI team in any project: scans the repo, offers three team sizes (lean, recommended, full) from a catalogue of 29 roles (CEO, Chief of Staff, Product, Engineering, Frontend, Mobile, Testing, Platform, Research, Bar Raiser, Design, Sales, Security, Data, ML, Docs and more), merges roles into one session for a small project, splits or creates seats for a large one, then writes docs/TEAM.md, a decision register, a brief and a rulebook per seat, and each seat's workers. Use when the user says \"set up the team\", \"seat the team\", \"team setup\" or \"bring the seats to this project\", adds, merges or splits a seat while the team is being chosen, or says \"sync the team's rulebooks\", \"refresh the rulebooks\" or \"update the seats after a plugin update\". Do NOT use to act as a seat (its seat-<role> skill), to change a decision, or to change a seated team: adding, retiring, merging, splitting or resizing is team-reevaluate."
---

# 🧩 Team setup

Seats a team of AI sessions in the current project. **The roles** are the 29 `seat-<role>`
rulebooks in this skill's `seats/` folder; setup **copies the chosen ones into the project's
`.claude/skills/`**, composes a merged rulebook where one session holds several roles, and derives a
new one where no catalogue role fits, so anyone who clones the project has the seats. **The project
facts** stay local (`docs/TEAM.md`, `docs/DECISIONS.md`, `docs/team/<team>.md`, `.claude/agents/`). A
seat is a session the owner opens with its skill; it runs its own workers on cheaper tiers.

This skill's folder is `${CLAUDE_SKILL_DIR}`. `scripts/`: `scan.py`, `plan.py`, `scaffold.py`,
`seatgen.py` (merged and derived rulebooks), `gen-team-agents.py` (copied into the project) and
`reevaluate.py` (for `team-reevaluate`). `references/`: `seats.md` (the catalogue), `seat-contract.md`
(how a rulebook is written), `role-research.md` (the sources behind each seat's thinking).

**Setup runs start to finish in this session.** The workers and tiers it generates load only in a
later session, so this session writes the new seats' rulebooks and fills the briefs itself (steps 6
and 7); the owner opens the seats in new sessions afterwards (step 8).

---

## 1 · Read the project before proposing anything

**Measure, don't guess.** In one read-only pass:
- **What it is:** README, CLAUDE.md or AGENTS.md, `git log --oneline -30`, open issues if any.
- **How it is built and checked:** the manifests, test commands, CI, linters; whether a suite exists.
- **Where it runs:** deploy configs and anything that costs money.
- **Who it is for:** users, buyers, testers, content channels, data sources and their licences.
- **What exists already.** `docs/TEAM.md` with a roster means a team is seated and this is no setup:
  "sync the team's rulebooks" (or refresh, or update after a plugin update) is **Sync** below; any
  change to the team, named by the owner or not (add, retire, merge, split, resize), is
  `team-reevaluate`. A `seat-<team>` folder already in `.claude/skills/` is the project's own:
  scaffold keeps it, records it, and never overwrites or syncs it.

## 2 · Scan

```
python3 ${CLAUDE_SKILL_DIR}/scripts/scan.py --root <project> --save
```

**`--save` writes `docs/team/scan.json`, the baseline `team-reevaluate` diffs against.** Every signal
carries its evidence; read them against step 1. A signal raised by a stray dependency or an example
folder is noise (say so); a need no signal raised (a planned launch, a grant) is an edit in step 3.

## 3 · Present three options, ask once

```
python3 ${CLAUDE_SKILL_DIR}/scripts/plan.py --scan <project>/docs/team/scan.json --markdown
```

**It prints the options ready for the owner** (the size, then Recommended, Lean and Full: each seat,
how it is held and why, in plain words). Check it against step 1 (noise, a need no signal raised: say
which) and present it as printed in one question, Recommended labelled `(Recommended)`. Then, once:
- **A merged seat is one session holding several roles**, every rule of each kept; it splits back
  when its work grows.
- **A new seat** (one no catalogue role covers, or a split) **gets its rulebook written for its role
  before it works**; this session writes it.
- **The owner may edit any option**: add, remove, merge or split a seat.

In the same question, two settings in plain words, each with its recommendation:
- **What only you do** (recommended: publishing, sending, spending and signing).
- **Uploading finished work:** "When finished work is ready, should the team upload it to the shared
  code repository on its own once the checks pass, or ask you each time? (Recommended: ask me each
  time.)" The owner may also say they upload it themselves.

Then, in plain lines (`docs/TEAM.md §7`'s shape, no codes, no team slugs): **what they will be asked
from now on** (anything outward, any spend, prices, legal and irreversible acts, real forks, new
scope) and not (everything reversible in scope); and **what happens next**: this session writes the
team in and finishes setup, then the owner opens seats in new sessions, the CEO and the Chief of
Staff (the CEO alone without one) right away and every other seat when its work comes up. A seat not
open is covered by its team; three to six open at once is typical.

## 4 · Write the plan

```
python3 ${CLAUDE_SKILL_DIR}/scripts/plan.py --scan <project>/docs/team/scan.json --option <lean|recommended|full> \
  --out <project>/docs/team/plan.json --project "<name>" --owner-acts "<what only the owner does>" --push-rule "<rule>"
```

**`--push-rule` from the uploading answer:**
- *ask me each time*: `a seat asks the owner before each push and pushes on the owner's yes.`
- *on its own*: `a seat pushes its landed work once the checks pass and a reviewing seat has passed it, and reports the push after.`
- *I upload it myself*: `the owner pushes; a seat never pushes unless DECISIONS.md says otherwise.`

**Apply the owner's edits by editing `docs/team/plan.json`'s `seats` list**, one spec per seat:

| Edit | Spec |
|---|---|
| add a catalogue seat | `{"team": "design", "type": "catalogue", "why": "the owner asked"}` (`scaffold.py --list` names them) |
| remove | delete its spec; the CEO and the Bar Raiser come back unless a merge holds them |
| merge | replace the members with `{"team": "growth", "type": "merge", "of": ["sales", "seo", "social"], "seat": "Growth", "mark": "📈", "kind": "director", "why": "…"}`; the named groups and marks are `MERGES` in `scripts/teamlib.py` |
| split or create | `{"team": "frontend-web", "type": "derive", "base": "seat-frontend", "seat": "…", "mark": "…", "kind": "implementation", "register": "…", "reports_to": "Engineering", "scope": "only apps/web/", "sibling": "frontend-admin", "why": "…"}` |

**A check seat (Bar Raiser, Scope Trimmer, User, Security) never merges into a seat whose work it
checks**; Quality (Testing with the Bar Raiser) is the one check merge. **A merge needs two or more
catalogue members. A split names its sibling**, so each half knows where its scope ends.

## 5 · Scaffold

```
python3 ${CLAUDE_SKILL_DIR}/scripts/scaffold.py --root <project> --plan <project>/docs/team/plan.json \
  --record "<the owner's answer, verbatim>" --question "<the question asked, in one line>"
```

It writes `docs/TEAM.md` (the roster), `docs/DECISIONS.md` with the owner's question and words as a
decision row, a brief per seat, the tracker and owner-questions with a Chief of Staff, each rulebook in
`.claude/skills/` (origin, hash and seated date in `docs/team/seat-skills.lock`), the generator and
`.claude/agents/`, a gitignored `scratchpad/team/` and a `CLAUDE.md` pointer. **It never overwrites a
file** (it says what it skipped); `--force` only on the owner's word. **A refusal changes nothing:**
`nothing was changed:` and one line per cause (a mark two seats share, a role two seats would hold);
fix the plan and rerun. `NEEDS AUTHORING` names each derived seat: no worker until it is written.

## 6 · Author every new seat

**A seat never works from a rulebook written for someone else.** For each `NEEDS AUTHORING` line:
1. Read `${CLAUDE_SKILL_DIR}/references/seat-contract.md`, the project's `docs/TEAM.md`, the seat's
   brief, its base rulebook and the two or three seats it hands off to.
2. Research the role (three to five searches on how the best operator of it works at a fast,
   early-stage company); cite only what you opened. A split shares its base's role: research only
   what differs, and name the sibling in §0.
3. Rewrite `.claude/skills/seat-<team>/SKILL.md` to the contract's seven sections; delete the
   `AUTHORING NEEDED` banner line last.
4. In the project, run `python3 scripts/gen-team-agents.py` (it writes the seat's worker now that the
   rulebook is its own), then `python3 scripts/gen-team-agents.py --check` until it passes.

**For several new seats, spawn general-purpose subagents from this session**, one seat each, with no
model override (they run on this session's model), steps 1 to 3 and the paths in the prompt, and the
step-1 measurements written once to `scratchpad/team/shared/setup-facts.md`. **Never spawn by tier
name here:** the tiers load only in a new session. Review every rulebook against the contract yourself.

## 7 · Fill each seat's brief

`docs/team/<team>.md` arrives as a template. **A seat with an empty brief starts blind**, so fill
every section from what step 1 measured, for that seat only:
- **Owns here:** the register file (create it with a one-paragraph header saying who keeps it and
  how) and the exact paths the seat edits. A merged seat's brief carries its members' briefs: merge
  them into one set of sections.
- **Does not own here:** the near-misses, and whose they are.
- **Project facts:** the commands this seat runs (test, build, deploy, render), environments, data
  sources, with the date measured.
- **Traps paid for:** anything the git log or docs show already went wrong in this seat's area.
- **Done means here:** the concrete done-when (which tests, which review, deployed or not).

For more than six seats, give the briefs to subagents as in step 6 (three seats each), then review
each yourself. Mark anything not measured `UNVERIFIED`; never invent a path.

## 8 · Hand over to the owner

Report in `docs/TEAM.md §7`'s shape: the decision needed (if any), a summary, then the seats by
objective. Then, in plain words:
- **Open now**, each in a new session named after it: 🧭 CEO with
  `/seat-ceo catch up and work your inbox`, then 🛎️ Chief of Staff with
  `/seat-chief-of-staff catch up and work your inbox` (the CEO alone when no Chief of Staff is
  seated). Talk to that seat like a person.
- **Every other seat when its work comes up**, the same way: `/seat-<team> catch up and work your inbox`.
  Name them in one line. A seat not open is covered by its team, which the other seats call (the
  owner never spawns workers); three to six open at once is typical.
- **The owner's touchpoints**, as step 3 told them (`docs/TEAM.md §7`; the plugin's
  `docs/owner-touchpoints.md`).
- **Say "re-evaluate the team" any time**; after each milestone is a good moment. Name a change
  directly too ("add Sales to the team"); after a plugin update, say "sync the team's rulebooks".

Commit the setup with explicit paths (`git add <paths>`, then `git commit -o <paths>`), never `-A`.

---

## Maintaining a seated project

- **Change the team: `team-reevaluate`.** "Re-evaluate the team" measures each seat and proposes
  adds, retires, merges, unmerges and splits for one answer; a change the owner names ("add Sales",
  "retire Design") is made with the owner's words as the record, asked about only when the measurement
  cuts against it. Every change is a decision row; **never add or remove a roster row by hand.**
- **Sync** ("sync the team's rulebooks", after a plugin update):
  `python3 ${CLAUDE_SKILL_DIR}/scripts/scaffold.py --root <project> --sync`. It refreshes every
  catalogue copy the project has not edited and recomposes every merged seat from its members' new
  rulebooks unless edited (`docs/team/seat-skills.lock` holds each copy's origin and hash); derived
  rulebooks and the project's own are never touched. `updated:` and `missing, re-created:` name what
  changed; `kept (edited in this project)`, `not tracked`, `not synced` and `still needs authoring`
  each need a look. **Tell the owner which seats' rulebooks changed**, by mark and name, and that a
  session of those seats opened before the sync holds the old rulebook: reopen it, or send
  `/seat-<team> catch up and work your inbox` again. **Sync leaves the generator and the protocol
  alone:** carry this skill's `scripts/gen-team-agents.py` over the project's, keeping its `TIERS`,
  then run it and `--check`; diff `docs/TEAM.md` against `templates/TEAM.md` and carry over what
  applies, the roster untouched. Commit the changed paths.
- **A new model ships:** edit `TIERS` in `scripts/gen-team-agents.py` and the tier table in
  `docs/TEAM.md` §2, run the generator, and confirm with a one-line spawn that quotes its model id
  **after** the session reloads the agent files (a spawn straight after an edit runs the old one).
- **Why the rulebooks are copied:** a worker's `skills:` preload finds project and user skills by
  name, never a plugin-only skill (measured 2026-10-09: plain and `plugin:` names preloaded nothing).
- **Audit how the team works:** read `scratchpad/team/inbox/` and `runs/`, and count which agent
  types the sessions spawned and on which models. Generic agents with a model shorthand are the
  usual leak (they can land on an older model); seats should spawn by tier name.

**Example:** a seated project and a prompt-by-prompt walkthrough are in the plugin's repo
(`examples/tally/`, `examples/walkthrough.md`); the orchestration diagrams are in its `docs/`.
