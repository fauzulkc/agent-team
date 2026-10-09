# How it works

## The idea in one paragraph

A project gets a **team of Claude sessions**, each holding one **seat** (CEO, Engineering, Design…).
A seat is a person-shaped job: it owns a register, rules inside it, and reports in a fixed shape.
**Each seat runs its own team of workers** on cheaper models for the typing and stronger ones for the
thinking, and steers them from above. Seats talk to each other in a compact syntax, cover for each
other when one is away, and bring you only what only you can decide. **The team is sized from the
repo**: setup scans it and offers three teams with the evidence for every seat, and a re-evaluation
later measures how each seat actually works and proposes changes. Speed comes from cutting work
and reversible decisions, never from cutting truth.

## The layers

| Layer | Lives in | Owned by | Changes when |
|---|---|---|---|
| **Role rulebooks** (how a seat thinks and works) | `.claude/skills/seat-<team>/SKILL.md`: copied from the catalogue, composed for a merged seat, or derived and then written for a new role | the plugin for catalogue and merged seats (refreshed with *"sync the team's rulebooks"*); the project for a derived one | the plugin improves a role, or a new role is written |
| **Shared protocol** (tiers, dispatch, who to call, inbox, message syntax, how to report, when to ask you) | `docs/TEAM.md` | the project | you change a team-wide rule |
| **Decisions** (what you and the CEO ruled) | `docs/DECISIONS.md` | the CEO records; you decide what only you may | a decision lands; it outranks everything |
| **Seat briefs** (this project's facts for each seat: registers, paths, commands, traps, done-when) | `docs/team/<team>.md` | each seat keeps its own | a seat learns something about this project |
| **Workers** (each seat's own team, and six shared tiers) | `.claude/agents/*.md`, generated | `scripts/gen-team-agents.py` from the roster | the roster or a model changes |
| **Scratch** (inboxes, run logs, shared context packs) | `scratchpad/team/`, never committed | everyone | constantly |
| **Repo scan** (the signals and size setup sized the team from) | `docs/team/scan.json` | `scan.py --save` | at setup, and again after each re-evaluation is applied (the new baseline) |
| **Team plan** (the option you picked, with your edits, each seat with its why) | `docs/team/plan.json` | `plan.py`, edited to your answer | at setup |
| **Re-evaluation plan** (the proposals, cut to what you approved) | `docs/team/reevaluation.json` | `reevaluate.py`, edited to your answer | each re-evaluation |
| **Rulebook origins** (where each rulebook came from, and its hash) | `docs/team/seat-skills.lock`: `catalogue`, `merge:sales+seo+social` or `derive:seat-mobile` | the scripts | a seat is added, retired or synced; a copy the project edited is never overwritten |
| **Retired seats** (kept for the record) | the brief stays in `docs/team/<team>.md` under a "Retired" line; an authored rulebook moves to `docs/team/retired/` | the scripts | a seat is retired or merged away |

A seat reads, in order: its **inbox**, `docs/TEAM.md`, **its brief**, recent commits and decisions,
then works. The rulebook says *how*; the brief says *what, here*; a decision says *what wins*.

## How the team is sized

Setup never starts from a template. It **scans the repo, sizes it, and offers three teams**; you pick
one, edit it if you like, and the scaffold writes exactly that.

**1. The scan** (`scan.py`) reads file names, manifests and dependency lists, a few schema and config
files, and git history; it sends nothing anywhere. Each signal keeps the evidence that raised it:

| Signals | Raised by, for example |
|---|---|
| web UI, mobile app, desktop app, browser extension, game | `react-dom`, `vue`, `next`; `ios/`, `react-native`; `electron`, `tauri`; a `manifest.json` with `manifest_version`; `phaser`, `project.godot` |
| API, database, migrations | `express`, `fastapi`; `prisma`, `pg`, `sqlalchemy`; `migrations/`, `alembic/` |
| models, data pipelines, analytics | `torch`, `transformers`, notebooks; `dbt_project.yml`, `dags/`; a product-analytics SDK |
| payments, sign-in, email, personal data | a payment SDK; `next-auth`, `passport`; `nodemailer`; email or address columns in a schema |
| landing, content, video, docs site, localization | a pricing page; `blog/`, `posts/`; `remotion`; `mkdocs.yml`; `locales/`, `i18next` |
| deploy, CI, tests, security policy | `Dockerfile`, a hosting config; `.github/workflows/`; `tests/`, `*.test.ts`; `SECURITY.md` |
| open source, licensed data, hardware, smart contracts, monorepo | `CONTRIBUTING.md`, a code of conduct; `datasets/`, `NOTICE`; `platformio.ini`, KiCad files; `*.sol`, `hardhat`; several package manifests |

`--save` writes the result to `docs/team/scan.json`, the baseline a later re-evaluation compares against.

**2. The size class** comes from source files, commits and contributors:

| Class | When | What the recommended team does |
|---|---|---|
| **tiny** | under 60 source files and under 50 commits | takes every allowed merge; drops Competition, Funding and Research (Research stays if there are data pipelines) |
| **small** | under 600 source files, three contributors or fewer | merges the commercial seats: Growth, Money, Legal & Compliance, Customer, Data & ML |
| **medium** | under 3,000 source files | keeps every role in its own seat |
| **large** | 3,000 source files or more | keeps every role separate and, with two or more UI apps, splits the frontend per app |

**3. The three options** (`plan.py`), each seat carrying its *why*:

| Option | What it is |
|---|---|
| **Lean** | the fewest sessions: every allowed merge, and User, Competition, Funding and Research dropped |
| **Recommended** | what the evidence calls for, scaled to the size class above |
| **Full** | every role in its own seat, the optional seats added (Competition and Funding when it will be sold, Docs writer for an API, Research when a model is involved, and User, Customer Success or Security where the evidence is softer), and, with two or more UI apps, the frontend split per app |

Every option keeps the CEO and the Bar Raiser. The **Chief of Staff** joins once five or more other
seats run (seven in lean), the **Scope Trimmer** once ten or more: they earn their seat by the
sessions they coordinate.

**Merged seats.** One session holds several roles while each one's work is small. Its rulebook is
composed from the members' rulebooks with every section of each kept under "As <member>", and
`--sync` recomposes it when they improve; its brief carries the members' briefs.

| Mark | Merged seat | Holds | Kind |
|---|---|---|---|
| 📈 | Growth | Sales & Marketing, SEO & Publicity, Social Media Manager | director |
| 🎨 | Product & Design | Product, Design | director |
| 🔧 | Engineering & Platform | Engineering, Platform (never past 2,000 source files) | director |
| 🛡️ | Quality | Testing, Bar Raiser | check |
| 💰 | Money | Funding, Revenue & Investment; Payments & Company Legal | director |
| 📜 | Legal & Compliance | Payments & Company Legal; Compliance & Audit | director |
| 🧮 | Data & ML | Data engineer, ML engineer | director |
| 🫱 | Customer | Customer Success, Community & DevRel | director |

A merge needs two or more of its members present. **Check seats (Bar Raiser, Scope Trimmer, User,
Security) never merge into a seat whose work they check.** Quality is the one merge that holds a
check seat, and it is itself a check seat; after setup, the Bar Raiser is never folded into a merge.

**New roles.** When a signal calls for a role no catalogue seat covers, setup derives one:

| Signal | New seat | Derived from |
|---|---|---|
| hardware | 🔌 Hardware & firmware engineer | `seat-mobile` |
| blockchain | ⛓️ Smart-contract engineer | `seat-security` |
| desktop | 🖱️ Desktop engineer | `seat-mobile` |
| extension | 🧷 Browser-extension engineer | `seat-frontend` |

A derived rulebook is a copy of its base under the new name and mark, with the seat's scope in §0 and
an **`AUTHORING NEEDED`** block on top. The scaffold prints `NEEDS AUTHORING` for it, and the session
that seated it rewrites it for the role following `skills/team-setup/references/seat-contract.md`
(research the role, the seven sections, hand-offs that agree with the neighbouring seats), then
deletes the block. **`gen-team-agents.py --check` fails while any seated rulebook still carries the
block**, so no seat works from a rulebook written for someone else.

**Splits.** With two or more web UI apps (folders whose `package.json` depends on a web UI framework),
*full* offers one frontend seat per app, up to four (🖥️ 💻 🪟 📟), each derived from `seat-frontend`
with its scope set to its own folder. *Recommended* does the same once the project is large.

**4. One question.** The owner sees the three options (recommended first), each seat with its reason
in plain words, and the two settings the rulebook needs (what only the owner does, who pushes), in
one question. The answer, with any edit, is written to `docs/team/plan.json`, applied by
`scaffold.py --plan`, and recorded word for word in `docs/DECISIONS.md`.

## Re-evaluating the team

Say *"re-evaluate the team"* when a milestone closes, or when the team feels too big or too small.
`team-reevaluate` runs `reevaluate.py`, which **changes nothing**: it measures and proposes.

**What it measures**, per seated seat, over the last 30 days (or the window you name):

| Measure | Read from |
|---|---|
| commits | subjects that start with the seat's prefix: `design: …` or `design(web): …` (anything else counts as unattributed) |
| worker runs | run logs written under `scratchpad/team/runs/<team>/` |
| inbox | lines waiting in `scratchpad/team/inbox/<team>.md` |
| blocked | tracker lines where the seat is BLOCKED |
| repo changes | a fresh scan, diffed against `docs/team/scan.json`: signals new or gone since setup |

**What it proposes**, each with its evidence:

| Proposal | When |
|---|---|
| **add** | the recommended team for today's repo calls for a seat that nothing seated, merged or not, covers; the Chief of Staff once the team would have five seats, the Scope Trimmer ten |
| **retire** | a seat with **no** commits, worker runs or inbox lines in the window, **and** no repo signal calling for it. Never the CEO or the Bar Raiser; never the Chief of Staff while five or more seats run |
| **merge** | two or more members of one merge group are all **quiet**: at most 2 commits and at most 2 worker runs in the window, and not blocked |
| **unmerge** | a merged seat carries **at least 10 commits and at least 30%** of the commits attributed to any seat: it has outgrown the merge and splits back into its roles |
| **split** | the project is large and has two or more UI apps: one frontend seat per app |

**A retired seat is not proposed again** unless the signal that called for it is new since the
baseline; the report lists it under *Noted, not proposed* instead. A seat idle for the window but
still called for by the repo (Social, while there is a blog) is not retired; it is a merge candidate.

**The session judges what the script counts.** Before the owner sees anything, it drops what the
numbers get wrong (a seat seated inside the window, seasonal work such as Funding between rounds,
work committed without a prefix) and says why. Then **one question**: the proposals in plain words,
what was dropped, which sessions to open and close, and *apply all, apply some, or change nothing*.

**Applying** is `scaffold.py --plan docs/team/reevaluation.json --record "<your words>"`, after the
plan is cut to what you approved. Retired seats keep their briefs under a "Retired" line, their
workers are removed, and an authored rulebook is archived in `docs/team/retired/`; a merged seat's
brief carries its members' briefs; new derived seats are written for their role before they work.
Then **the baseline resets** (`scan.py --save`), so the next re-evaluation diffs against today and a
signal already answered is never raised twice. The generator's check runs green, every affected seat
gets an inbox line, and a session opened before the change is reopened to load the new rulebook.

## Anatomy of a seat rulebook

Every `seat-<team>` skill has the same seven sections, so any seat can read any other. A merged
seat's rulebook keeps each member's sections under "As <member>"; a new seat's is written to the same
seven sections from `skills/team-setup/references/seat-contract.md`:

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

**Seats.** The catalogue has 29, plus 8 merged seats and 4 new roles. The team scales with the size
class ([above](#how-the-team-is-sized)). Measured on invented test projects: a tiny open-source
library gets 5 seats lean, 6 recommended, 7 full; a web product with sign-ups, payments, a pricing
page and a blog gets 10 to 12 lean, 13 to 15 recommended when tiny or small (merged seats) and 19
when medium (every role separate), and 21 or 22 full. Lean is the answer when sessions are scarce:
for that web product, ten sessions hold sixteen roles. The method has run with 21 seats on one
production project. A seat with no work is overhead, and re-evaluation finds it.

**Open sessions.** Each open seat is one Claude session, so your plan's session and usage limits
are the real ceiling. You don't need every seat open: closed seats are covered by their teams, so a
typical day might run with 3 to 6 seats open and the rest answering through their teams.

**Workers per seat.** Seats run workers in the background; keep each wave **under about ten workers**
so you can still follow them and so they don't contend for the same files (one owner per file per
wave). Waves run back to back as earlier ones finish.

**Cost shape.** Most of the volume runs on the cheap tiers. At short prompts, the Quick, Scout and
Check tiers cost roughly a twentieth of the Execution and Build tiers (the model publisher's figures),
so pushing exact-contract work down the ladder is the biggest saving. The seat sessions themselves run on your session model and
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
- **Better rulebooks:** update the plugin, then say *"sync the team's rulebooks"* in the project. It
  refreshes every catalogue copy and recomposes every merged seat from its members' new rulebooks;
  any rulebook the project edited itself is kept and reported for a hand merge, and derived
  rulebooks are the project's own.
- **Resize the team:** *"re-evaluate the team"*: it measures, proposes, and applies only what you approve.
- **New seat:** *"add Design to the team"* (`scaffold.py --add design`).
- **Drop a seat:** `scaffold.py --retire <team>`: its roster row, rulebook copy and worker go, its brief
  stays with a "Retired" line on top, and an authored rulebook moves to `docs/team/retired/`.
- **Audit the team:** read `scratchpad/team/inbox/` and `runs/`, and count which agents sessions
  spawned on which models. Generic agents with a model shorthand are the usual leak.
