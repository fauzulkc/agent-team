---
name: team-setup
description: "🧩 Seat an AI team in any project: scans the repo, offers three team sizes (lean, recommended, full) drawn from a catalogue of 29 roles (CEO, Chief of Staff, Product, Engineering, Frontend, Mobile, Testing, Platform, Research, Bar Raiser, Design, Sales, SEO, Payments, Security, Data, ML, Docs and more), merges roles into one session for a small project, splits or creates seats for a large one, then writes the shared rulebook docs/TEAM.md, a decision register, a brief per seat, each seat's worker team and the model tiers in .claude/agents. Use when the user says \"set up the team\", \"seat the team\", \"team setup\", \"add a seat\", \"add Design to the team\", \"bring the seats to this project\", \"merge seats\" or \"split a seat\" while the team is being chosen, or opens a new project that should run with seats. Do NOT use to act as a seat (open its seat-<role> skill), to change a project's existing decisions, or to resize a team that has already worked (team-reevaluate)."
---

# 🧩 Team setup

Seats a team of AI sessions in the current project. **The roles** are the 29 `seat-<role>`
rulebooks in this skill's `seats/` folder; setup **copies the chosen ones into the project's
`.claude/skills/`**, composes a merged rulebook where one session holds several roles, and derives a
new one where no catalogue role fits. Anyone who clones the project has the seats with nothing to
install. **The project facts** stay local (`docs/TEAM.md`, `docs/DECISIONS.md`, `docs/team/<team>.md`,
generated `.claude/agents/`). A seat is a session the owner opens with its skill; each seat runs its
own workers on cheaper tiers and steers them.

This skill's folder is `${CLAUDE_SKILL_DIR}`. `scripts/`: `scan.py`, `plan.py`, `scaffold.py`,
`seatgen.py` (merged and derived rulebooks), `gen-team-agents.py` (copied into the project) and
`reevaluate.py` (for `team-reevaluate`). `references/`: `seats.md` (the catalogue), `seat-contract.md`
(how a rulebook is written), `role-research.md` (the sources behind each seat's thinking).

---

## 1 · Read the project before proposing anything

**Measure, don't guess.** In one read-only pass:
- **What it is:** README, CLAUDE.md or AGENTS.md, `git log --oneline -30`, open issues if any.
- **How it is built and checked:** the manifests, test commands, CI, linters; whether a suite exists.
- **Where it runs:** deploy configs and anything that costs money.
- **Who it is for:** users, buyers, testers, content channels, data sources and their licences.
- **What exists already.** `docs/TEAM.md` present means this is not a fresh setup: the owner naming a
  seat is `scaffold.py --root <project> --add <team>`; anything else (too big, too small, merge, split,
  retire) is `team-reevaluate`. Existing `.claude/skills/` win: never shadow a project's own skill.

## 2 · Scan

```
python3 ${CLAUDE_SKILL_DIR}/scripts/scan.py --root <project> --save
```

**`--save` writes `docs/team/scan.json`, the baseline `team-reevaluate` diffs against.** Every signal
carries its evidence. Read them against step 1: a signal raised by a stray dependency or an example
folder is noise (say so to the owner); a need step 1 found that no signal raised (a launch the README
plans, a grant being written) becomes an owner edit in step 3.

## 3 · Present three options, ask once

```
python3 ${CLAUDE_SKILL_DIR}/scripts/plan.py --scan <project>/docs/team/scan.json --markdown
```

**One question, three options, recommended first** and labelled `(Recommended)`, then lean, then
full. Each option lists its seats by mark and name, each with its one-line why **in plain words**
(translate the evidence: "a payment library is in the dependencies", never a signal key). Under the
options say, once:
- **A merged seat is one session holding several roles**, every rule of each kept; it splits back
  when its work grows.
- **A new seat** (one no catalogue role covers, or a split) **gets its rulebook written for its role
  before it works**; setup does that in step 6.
- **The owner may edit any option**: add, remove, merge or split a seat.

In the same question, ask the two settings the rulebook needs, each with its default:
- **What only the owner does** (default: publishing, sending, spending, signing).
- **Who pushes** (default: the owner pushes; a seat never pushes unless a decision says so).

Then tell the owner in two lines what they will be asked from now on (anything outward, any spend,
prices, legal and irreversible acts, real forks, new scope) and what they will not (everything
reversible inside scope). No codes, no team slugs: `docs/TEAM.md §7`'s shape.

## 4 · Write the plan

```
python3 ${CLAUDE_SKILL_DIR}/scripts/plan.py --scan <project>/docs/team/scan.json --option <lean|recommended|full> \
  --out <project>/docs/team/plan.json --project "<name>" --owner-acts "<the owner's acts>" --push-rule "<who pushes>"
```

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
  --record "<the owner's answer, verbatim>"
```

It writes `docs/TEAM.md` (the roster), `docs/DECISIONS.md` with the owner's words as a decision row,
one brief per seat, the tracker and owner-questions with a Chief of Staff, each rulebook in
`.claude/skills/` with its origin and hash in `docs/team/seat-skills.lock`, `scripts/gen-team-agents.py`,
the generated `.claude/agents/`, a gitignored `scratchpad/team/` and a pointer in `CLAUDE.md`.
**It never overwrites an existing file** (it says what it skipped); `--force` only on the owner's word.
It prints `NEEDS AUTHORING` for every derived seat. **A new session is needed** for the copied
skills and generated workers to load.

## 6 · Author every new seat

**A seat never works from a rulebook written for someone else.** For each `NEEDS AUTHORING` line:
1. Read `${CLAUDE_SKILL_DIR}/references/seat-contract.md`, the project's `docs/TEAM.md`, the seat's
   brief, its base rulebook and the two or three seats it hands off to.
2. Research the role (three to five searches on how the best operator of it works at a fast,
   early-stage company); cite only what you opened. A split shares its base's role: research only
   what differs, and name the sibling in §0.
3. Rewrite `.claude/skills/seat-<team>/SKILL.md` to the contract's seven sections; delete the
   `AUTHORING NEEDED` block last.
4. In the project, run `python3 scripts/gen-team-agents.py --check` until it passes.

For several new seats, give each to a research-tier worker with the step-1 measurements as a shared
file in `scratchpad/team/shared/`, then review every rulebook yourself against the contract.

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

For more than six seats, give the briefs to research-tier workers (three seats each, the step-1
file shared), then review each yourself. Mark anything not measured `UNVERIFIED`; never invent a path.

## 8 · Hand over to the owner

Report in `docs/TEAM.md §7`'s shape: the decision needed (if any), a summary, then the seats by
objective. Include how to open each seat:

| Seat | Open a new session named after it, first message |
|---|---|
| 🧭 CEO | `/seat-ceo catch up and work your inbox` |
| … | `/seat-<team> catch up and work your inbox` |

Then, in plain words:
- **Open the CEO first**, to record anything pending. Seats spawn their own workers (the owner
  never does); a seat that is away has its team called by the others.
- **The owner's touchpoints:** what they will be asked and what they will not, as step 3 told them
  (the full line is `docs/TEAM.md §7`; the plugin's `docs/owner-touchpoints.md` explains it).
- **Say "re-evaluate the team" any time**; after each milestone is a good moment. It measures how
  each seat actually works and proposes changes; nothing changes without the owner's yes.

Commit the setup with explicit paths (`git add <paths>`, then `git commit -o <paths>`), never `-A`.

---

## Maintaining a seated project

- **Re-evaluate the team:** `team-reevaluate` ("re-evaluate the team") measures each seat's commits,
  worker runs, inbox and blocked lines, re-scans the repo against `docs/team/scan.json`, and proposes
  adds, retires, merges, unmerges and splits for the owner to approve.
- **Add a seat the owner names:** `scaffold.py --root <project> --add <team>` (catalogue seats).
- **Retire a seat:** `scaffold.py --root <project> --retire <team>`. It removes the roster row, the
  rulebook copy and the worker, and **keeps the brief** with a "Retired" line on top; an authored
  (derived) rulebook moves to `docs/team/retired/` (copy there by hand any other rulebook the
  project edited, first). The CEO and the Bar Raiser are never retired.
- **A new model ships:** edit `TIERS` in `scripts/gen-team-agents.py` and the tier table in
  `docs/TEAM.md` §2, run the generator, and confirm with a one-line spawn that quotes its model id
  **after** the session reloads the agent files (a spawn straight after an edit runs the old one).
- **The rulebooks improve** (a new version of this skill): `scaffold.py --root <project> --sync`
  refreshes every catalogue copy the project has not edited **and recomposes every merged seat from
  its members' new rulebooks**, unless the project edited it (`docs/team/seat-skills.lock` holds each
  copy's origin and hash). It names what it kept, and any derived seat still waiting for authoring;
  derived rulebooks are the project's own and never refreshed. A change to the shared protocol does
  not reach a project's `docs/TEAM.md` by itself: diff it against `templates/TEAM.md` and carry over
  what applies.
- **Why the rulebooks are copied, not shared:** a worker's `skills:` preload finds project and user
  skills by name, but not a skill that lives only inside a plugin (measured 2026-10-09: both the plain
  and the `plugin:` name preloaded nothing).
- **Audit how the team works:** read `scratchpad/team/inbox/` and `runs/`, and count which agent
  types the sessions spawned and on which models. Generic agents with a model shorthand are the
  usual leak (they can land on an older model); seats should spawn by tier name.

**Example:** a seated project and a prompt-by-prompt walkthrough are in the plugin's repo
(`examples/tally/`, `examples/walkthrough.md`); the orchestration diagrams are in its `docs/`.
