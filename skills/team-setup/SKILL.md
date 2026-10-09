---
name: team-setup
description: "🧩 Seat an AI team in any project: picks the seats the work needs from a catalogue of 21 (CEO, Chief of Staff, Product, Engineering, Frontend, Testing, Platform, Research, Bar Raiser, Scope Trimmer, Design, Motion, Sales, SEO, Social, Competition, Customer Success, Funding, Payments, Compliance, User), writes the shared rulebook docs/TEAM.md, a decision register, a project brief per seat, generates each seat's worker team and the six model tiers in .claude/agents, and sets up the scratch workspace. Use when the user says \"set up the team\", \"seat the team\", \"team setup\", \"add a seat\", \"add Design to the team\", \"bring the seats to this project\", or opens a new project that should run with seats. Do NOT use to act as a seat (open that seat's seat-<role> skill) or to change a project's existing decisions."
---

# 🧩 Team setup

Seats a team of AI sessions in the current project. **The roles** are the 21 `seat-<role>`
rulebooks kept in this skill's `seats/` folder; setup **copies the chosen ones into the project's
`.claude/skills/`**, so each seat's workers can preload its rulebook and anyone who clones the
project has the seats with nothing to install. **The project facts** stay local too
(`docs/TEAM.md`, `docs/DECISIONS.md`, `docs/team/<team>.md`, generated `.claude/agents/`). A seat is
a session the owner opens with its skill; each seat runs its own workers on cheaper models and
steers them.

This skill's folder is `${CLAUDE_SKILL_DIR}`. It holds `scripts/scaffold.py` (the deterministic
setup), `scripts/gen-team-agents.py` (copied into the project), `seats/` (the 21 rulebooks),
`templates/`, `references/seats.md` (the catalogue) and `references/role-research.md` (the sources
behind each seat's thinking).

---

## 1 · Read the project before proposing anything

Measure, don't guess. In one pass (a read-only search is enough):
- **What it is:** README, CLAUDE.md or AGENTS.md, `git log --oneline -30`, open issues if any.
- **The stack:** `package.json`, `go.mod`, `pyproject.toml`, `Cargo.toml`, Dockerfiles, CI files.
- **How it is checked:** the test commands, CI, linters; whether a test suite exists at all.
- **Where it runs:** deploy configs (Fly, Vercel, Cloudflare, Docker, cloud), anything that costs money.
- **Who it is for:** users, buyers, testers, content channels, data sources and their licences.
- **What exists already:** `docs/TEAM.md` (then this is an *add* or an *update*, never a fresh
  setup), `docs/DECISIONS.md`, an existing `.claude/agents/` or `.claude/skills/` with seat-like
  skills (the project's own skills win; never shadow them).

## 2 · Propose the seats, then ask once

Read `references/seats.md`. **Seat the smallest set that covers the work** and name the reason
for each seat in one line from what you measured. Always: CEO (the decision register), Bar Raiser
(the independent check), and Engineering for a code project. Add the Chief of Staff once three or
more seats run. Add a seat the day its work appears, never "in case".

Ask the owner one question with the proposed set as the recommended option, plus the two
settings the rulebook needs, each with a default:
- **What only the owner does** (default: publishing, sending, spending, signing).
- **Who pushes** (default: the owner pushes; a seat never pushes unless a decision says so).

Word everything for the owner in plain words, no codes (docs/TEAM.md §7's shape). Tell the owner,
in two lines, what they will be asked from now on (anything public, any spend, prices, legal and
irreversible acts, real forks, new scope) and what they will not (everything reversible inside
scope); the full line is `docs/TEAM.md` §7.

## 3 · Scaffold

```
python3 ${CLAUDE_SKILL_DIR}/scripts/scaffold.py --root <project> --project "<name>" \
  --seats ceo,chief-of-staff,engineering,testing,bar-raiser,... \
  --owner-acts "<the owner's acts>" --push-rule "<who pushes>"
```

It never overwrites an existing file (it says what it skipped); `--force` only on the owner's word.
To add seats to a seated project: `scaffold.py --root <project> --add design,user`.
`scaffold.py --list` prints the catalogue.

Then confirm: `python3 scripts/gen-team-agents.py --check` in the project prints the agents as
current, and every seat's rulebook resolves in `.claude/skills/`. **A new session is needed** for
the copied skills and generated workers to load.

## 4 · Fill each seat's project brief

`docs/team/<team>.md` arrives as a template. **A seat with an empty brief starts blind**, so fill
every section from what step 1 measured, for that seat only:
- **Owns here:** the register file (create it with a one-paragraph header saying who keeps it and
  how) and the exact paths the seat edits.
- **Does not own here:** the near-misses, and whose they are.
- **Project facts:** the commands this seat runs (test, build, deploy, render), environments, data
  sources, with the date measured.
- **Traps paid for:** anything the git log or docs show already went wrong in this seat's area.
- **Done means here:** the concrete done-when (which tests, which review, deployed or not).

For more than six seats, split the briefs across research-tier workers (one per three seats, each
given the step-1 measurements as a shared file in `scratchpad/team/shared/`), then review each
brief yourself. Mark anything not measured `UNVERIFIED`; never invent a command or a path.

## 5 · Hand over to the owner

Report in the owner's shape: the decision needed (if any), then a summary, then the seats by
objective. Include the table of how to open each seat:

| Seat | Open a new session named after it, first message |
|---|---|
| 🧭 CEO | `/seat-ceo catch up and work your inbox` |
| … | `/seat-<role> catch up and work your inbox` |

Say which seat to open first (the CEO, to record anything pending), that seats spawn their own
workers (the owner never does), and that a seat that is away has its team called by the others.
Commit the setup with explicit paths (`git add <paths>`, `git commit -o <paths>`), never `-A`.

---

## Maintaining a seated project

- **A new model ships:** edit `TIERS` in `scripts/gen-team-agents.py` and the tier table in
  `docs/TEAM.md` §2, run the generator, and confirm with a one-line spawn that quotes its model id
  **after** the session reloads the agent files (a spawn straight after an edit runs the old one).
- **A seat is no longer needed:** delete its roster row and run the generator (it removes the
  orphaned worker); keep its brief for the record.
- **The rulebooks improve** (a new version of this skill): run
  `python3 ${CLAUDE_SKILL_DIR}/scripts/scaffold.py --root <project> --sync`. It refreshes every seat
  rulebook the project has not edited (`docs/team/seat-skills.lock` holds each copy's hash) and names
  any it kept because the project changed it. A change to the shared protocol does not reach a
  project's `docs/TEAM.md` by itself: diff it against `templates/TEAM.md` and carry over what applies.
- **Why the rulebooks are copied, not shared:** a worker's `skills:` preload finds project and
  user skills by name, but not a skill that lives only inside a plugin (measured 2026-10-09: both
  the plain and the `plugin:` name preloaded nothing).
- **Audit how the team works:** read `scratchpad/team/inbox/` and `runs/`, and count which agent
  types the sessions spawned and on which models. Generic agents with a model shorthand are the
  usual leak (they can land on an older model); seats should spawn by tier name.

---

## Example

A seated example project and a prompt-by-prompt walkthrough are in the plugin's repo
(`examples/tally/`, `examples/walkthrough.md`); the orchestration diagrams and the owner-touchpoint
rules are in `docs/`.
