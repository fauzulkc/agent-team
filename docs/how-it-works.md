# How it works

## The idea in one paragraph

A project gets a **team of Claude sessions**, each holding one **seat** (CEO, Engineering, Design…).
A seat is a person-shaped job: it owns a register, rules inside it, and reports in a fixed shape.
**Each seat runs its own team of workers** on cheaper models for the typing and stronger ones for the
thinking, and steers them from above. Seats talk to each other in a compact syntax, cover for each
other when one is away, and bring you only what only you can decide. Speed comes from cutting work
and reversible decisions, never from cutting truth.

## The layers

| Layer | Lives in | Owned by | Changes when |
|---|---|---|---|
| **Role rulebooks** (how a seat thinks and works) | `.claude/skills/seat-<role>/SKILL.md`, copied in from the plugin | the plugin; refreshed with *"sync the team's rulebooks"* | the plugin improves a role |
| **Shared protocol** (tiers, dispatch, who to call, inbox, message syntax, how to report, when to ask you) | `docs/TEAM.md` | the project | you change a team-wide rule |
| **Decisions** (what you and the CEO ruled) | `docs/DECISIONS.md` | the CEO records; you decide what only you may | a decision lands; it outranks everything |
| **Seat briefs** (this project's facts for each seat: registers, paths, commands, traps, done-when) | `docs/team/<team>.md` | each seat keeps its own | a seat learns something about this project |
| **Workers** (each seat's own team, and six shared tiers) | `.claude/agents/*.md`, generated | `scripts/gen-team-agents.py` from the roster | the roster or a model changes |
| **Scratch** (inboxes, run logs, shared context packs) | `scratchpad/team/`, never committed | everyone | constantly |

A seat reads, in order: its **inbox**, `docs/TEAM.md`, **its brief**, recent commits and decisions,
then works. The rulebook says *how*; the brief says *what, here*; a decision says *what wins*.

## Anatomy of a seat rulebook

Every `seat-<role>` skill has the same seven sections, so any seat can read any other:

| § | Section | What it holds |
|---|---|---|
| 0 | The seat | its single loyalty; what it owns and does not own; whom it reports to |
| 1 | First action, every time | inbox → TEAM.md → brief → recent commits and decisions → health check if it uses a live service |
| 2 | How this seat thinks at a fast startup | 3–5 "from → to" shifts with their sources; its one-way and two-way doors |
| 3 | The method | the role's core procedure |
| 4 | Team | what it hands to which tier and what the contract must carry; what other seats may call its team for while it is away; hand-offs to peers |
| 5 | Rules and traps | the hard-won rules, each with its reason |
| 6 | Done, stop, and report | its done-when; the stop line; how it reports to you |

## The work loop

1. **You speak to one seat**, usually the Chief of Staff (or the CEO when there is no Chief of Staff).
2. **The decision, if one is needed, lands in `docs/DECISIONS.md`** and goes to every seat it binds.
3. **The owning seat writes a contract** for its own team or a tier: the question measured, what is
   known, the paths it may touch, the governing decisions, and the verification to paste.
4. **Workers run in the background**; the seat steers with one line when one drifts, and does other
   work meanwhile. A worker returns **ten lines or fewer** and writes its verbose trail to a run log.
5. **The seat reviews what returns**, re-runs the load-bearing command itself, and lands the work.
   Workers never commit.
6. **Another seat checks it** (the Bar Raiser re-measures, Testing owns what "green" means).
7. **The seat sends a stop line** to the Chief of Staff: done, blocked on whom, or waiting on you.
8. **You get one report** in a fixed shape: decision needed → summary → by objective → detail on ask.

See [orchestration-diagrams.md](orchestration-diagrams.md) for these flows drawn out.

## The tier ladder

| Tier | Model (default) | For | How it is spawned |
|---|---|---|---|
| Quick | Haiku 5.5, low effort | a fully specified edit or check | `team-quick` |
| Scout | Haiku 5.5, low effort | read-only searches and counts | `team-scout` |
| Check | Haiku 5.5, medium effort | long checklists finished in full | `team-check` |
| Execution | Sonnet, low effort | each seat's own routine work | `<team>-worker` (the seat's rulebook preloaded) |
| Build | Sonnet, high effort | multi-file builds, debugging, work returned half-done | `team-build` |
| Research | Opus, high effort | probes, audits, reviews, web research | `team-research` |
| Deep | Opus, maximum effort | one-way doors only | `team-deep` |

**Routing:** start at the cheapest tier that can do the job, and move up to the next tier that can do
that kind of work when a worker returns half-done work. The tiers form two ladders: work that edits
climbs Quick, Execution, Build; reading and judging climbs Scout, Check, Research, Deep. **Spawn by tier name only**: a generic agent given a model shorthand can
land on an older model generation. The models live in one place per project (the generator's
`TIERS` and `docs/TEAM.md` §2), so a new model is a one-line change and one command.

## When a seat is away

You won't have every seat open all the time. When a seat needs another that isn't open, it
**spawns that seat's own team** (`design-worker`), which carries that seat's rulebook and brief. The
team can apply existing rulings and do routine work; it **never makes a new ruling**. It writes a
*proposal* instead, and leaves one line in the absent seat's inbox. The seat reads its inbox first
thing when it opens, and agrees or corrects.

## Messages

Between seats, one header line and a few labelled lines; register codes allowed:

```
⚙️ Engineering → 📐 Design · ASK · how does a recurring invoice look in the list?
Need: one ruling, before Frontend builds it
Evidence: the list today (screenshot path)
Context: scratchpad/team/shared/recurring-invoices.md
Reply: by your next stop
```

Fifteen message types (ASK, TASK, QUEUE, HANDOFF, RESULT, FOR REVIEW, PASS/FAIL, LANDED, RULED,
STANDING, OWNER ANSWER, PROPOSAL, OBJECTION, FYI, STOP) cover the traffic. Anything said more than
once goes into `scratchpad/team/shared/` and is cited by path, which keeps messages short.

To you, never codes: plain words, decisions first. See [owner-touchpoints.md](owner-touchpoints.md).

## Capacity: what to expect

**Seats.** The catalogue has 21. Most projects need **4 to 9**: a solo build runs well on CEO,
Engineering, Testing and Bar Raiser; a product with users adds Chief of Staff, Product, Design,
User and Frontend; a startup adds commercial seats as their work appears. The method has been run
with all 21 seated on one production project. A seat with no work is overhead: add it the day its
work appears.

**Open sessions.** Each open seat is one Claude session, so your plan's session and usage limits
are the real ceiling. You don't need every seat open: closed seats are covered by their teams, so a
typical day might run with 3 to 6 seats open and the rest answering through their teams.

**Workers per seat.** Seats run workers in the background; keep each wave **under about ten workers**
so you can still follow them and so they don't contend for the same files (one owner per file per
wave). Waves run back to back as earlier ones finish.

**Cost shape.** Most of the volume runs on the cheap tiers. At short prompts, a Haiku 5.5 tier costs
roughly a twentieth of what Sonnet does (its publisher's figures), so pushing exact-contract work
down the ladder is the biggest saving. The seat sessions themselves run on your session model and
spend their tokens on judgement, steering and review, not on typing.

**Context.** Verbose output stays in the workers' run logs; a seat sees ten lines per worker. Shared
context packs are cited by path instead of repeated. Long-running seats still compact eventually:
anything that must survive goes into the seat's brief, the decisions, or a commit, never only into
a conversation.

**What it does not do.**
- It does not run unattended: you open the seats; they don't start themselves.
- It takes no outward act without you: no publishing, sending, spending or signing.
- It makes no legal determination; compliance and payments seats record and prepare, you decide.
- It does not replace your judgement on taste you reserved, or on a fork that cuts against what you said.
- Workers can't preload a rulebook that lives only inside a plugin, so setup copies the chosen
  rulebooks into the project; a newly generated worker file loads in the next session.

## Keeping it current

- **New model:** edit `TIERS` in `scripts/gen-team-agents.py` and `docs/TEAM.md` §2, run the
  generator, open a new session, and confirm with a one-line spawn that quotes its model id.
- **Better rulebooks:** update the plugin, then say *"sync the team's rulebooks"* in the project; any
  rulebook the project edited itself is kept and reported for a hand merge.
- **New seat:** *"add Design to the team"*.
- **Drop a seat:** delete its roster row and run the generator; its worker is removed, its brief kept.
- **Audit the team:** read `scratchpad/team/inbox/` and `runs/`, and count which agents sessions
  spawned on which models. Generic agents with a model shorthand are the usual leak.
