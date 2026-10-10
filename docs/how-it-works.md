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
| **Role rulebooks** (how a seat thinks and works) | `.claude/skills/seat-<team>/SKILL.md`: copied from the catalogue, composed for a merged seat, or derived and then written for a new role | the plugin for catalogue and merged seats (refreshed with *"sync the team's rulebooks"*); the project for a derived one, for one it edited, and for one it had before setup | the plugin improves a role, or a new role is written |
| **Shared protocol** (tiers, dispatch, who to call, inbox, message syntax, how to report, when to ask you) | `docs/TEAM.md` | the project | you change a team-wide rule |
| **Decisions** (what you and the CEO ruled) | `docs/DECISIONS.md` | the CEO records; you decide what only you may | a decision lands; it outranks everything |
| **Seat briefs** (this project's facts for each seat: registers, paths, commands, traps, done-when) | `docs/team/<team>.md` | each seat keeps its own | a seat learns something about this project |
| **Workers** (each seat's own team, and six shared tiers) | `.claude/agents/*.md`, generated | `scripts/gen-team-agents.py` from the roster | the roster or a model changes |
| **Scratch** (inboxes, run logs, shared context packs) | `scratchpad/team/`, never committed | everyone | constantly |
| **Repo scan** (the signals and size setup sized the team from) | `docs/team/scan.json` | `scan.py --save` | at setup, and again after each re-evaluation is applied (the new baseline) |
| **Team plan** (the option you picked, with your edits, each seat with its why) | `docs/team/plan.json` | `plan.py`, edited to your answer | at setup; a re-evaluation compares against the option it names |
| **Re-evaluation plan** (each proposal with a key, its evidence and the seats it adds or retires) | `docs/team/reevaluation.json` | `reevaluate.py`; you approve proposals by key | each re-evaluation |
| **Declined proposals** (what you said no to, and the evidence it rested on) | `docs/team/declined.json` | `scaffold.py --only`, which applies what you approved and records the rest | each re-evaluation you answer with *some* or *none* |
| **Rulebook origins** (where each rulebook came from, its hash, and the date its seat was seated) | `docs/team/seat-skills.lock`: `catalogue`, `merge:sales+seo+social`, `derive:seat-mobile`, or `project` (a rulebook the project already had: never synced, never deleted) | the scripts | a seat is added, retired or synced; a copy the project edited is never overwritten |
| **Retired seats** (kept for the record) | the brief stays in `docs/team/<team>.md` under a "Retired" line; a rulebook that is derived, the project's own or edited is archived to `docs/team/retired/<skill>-<date>` | the scripts | a seat is retired or merged away |

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
| open source, licensed data, hardware, smart contracts, monorepo | `CONTRIBUTING.md`, a code of conduct; `datasets/`, `NOTICE`; `platformio.ini`, KiCad files; `*.sol`, `hardhat`; package manifests in two or more folders, or a workspace config |

`--save` writes the result to `docs/team/scan.json`, the baseline a later re-evaluation compares against.

**2. The size class** comes from source files, commits and contributors:

| Class | When | What the recommended team does |
|---|---|---|
| **tiny** | under 60 source files and under 50 commits | takes every allowed merge; leaves Research out unless there are data pipelines |
| **small** | under 600 source files, three contributors or fewer | merges the commercial seats: Growth, Legal & Compliance, Customer, Data & ML |
| **medium** | under 3,000 source files | keeps every role in its own seat |
| **large** | 3,000 source files or more | keeps every role separate and, with two or more UI apps, splits the frontend per app |

**3. The three options** (`plan.py`), each seat carrying its *why*:

| Option | What it is |
|---|---|
| **Lean** | the fewest sessions: every allowed merge, and User, Competition, Funding and Research dropped |
| **Recommended** | what the evidence calls for, scaled to the size class above |
| **Full** | every role in its own seat, the optional seats added (Competition and Funding when it will be sold, Docs writer for an API, Research when a model is involved, and User, Customer Success or Security where the evidence is softer), and, with two or more UI apps, the frontend split per app |

Every option keeps the CEO and the Bar Raiser. The **Chief of Staff** joins once five or more other
seats run (seven in lean), the **Scope Trimmer** once ten or more other seats do: they earn their
seat by the sessions they coordinate. *Other seats* leaves out those two; a merged, split or new seat
counts as one. A re-evaluation adds and keeps them by the same rule.

**Merged seats.** One session holds several roles while each one's work is small. Its rulebook is
composed from the members' rulebooks, each member's opening and every section of each kept under
"As <member>", and `--sync` recomposes it when they improve; its brief carries the members' briefs.

| Mark | Merged seat | Holds | Kind |
|---|---|---|---|
| 📈 | Growth | Sales & Marketing, SEO & Publicity, Social Media Manager | director |
| 🎨 | Product & Design | Product, Design | director |
| 🔧 | Engineering & Platform | Engineering, Platform (never past 2,000 source files, at setup or later) | director |
| 🛡️ | Quality | Testing, Bar Raiser | check |
| 💰 | Money | Funding, Revenue & Investment; Payments & Company Legal (never at setup unless you edit the plan: see below) | director |
| 📜 | Legal & Compliance | Payments & Company Legal; Compliance & Audit | director |
| 🧮 | Data & ML | Data engineer, ML engineer | director |
| 🫱 | Customer | Customer Success, Community & DevRel | director |

A merge needs two or more of its members present, and **claims them**: two merges never share a
member, so Money and Legal & Compliance can't both take Payments. **Money never forms at setup** unless
you edit the plan: it needs Funding, which only the full option seats, and full merges nothing; so
Payments goes to Legal & Compliance, and a later re-evaluation can propose Money once Funding is
seated and both are quiet. **Check seats (Bar Raiser, Scope Trimmer, User, Security) join only a
check merge**: Quality, which setup forms in lean or for a tiny project. No merge a re-evaluation
proposes holds the CEO or the Bar Raiser.

**New roles.** When a signal calls for a role no catalogue seat covers, setup derives one:

| Signal | New seat | Derived from |
|---|---|---|
| hardware | 🔌 Hardware & firmware engineer | `seat-mobile` |
| blockchain | ⛓️ Smart-contract engineer | `seat-security` |
| desktop | 🖱️ Desktop engineer | `seat-mobile` |
| extension | 🧷 Browser-extension engineer | `seat-frontend` |

A derived rulebook is a copy of its base under the new name and mark, with the base's own paths
(its brief, inbox, run logs and worker) rewritten to the new seat's, the seat's scope in §0, and an
**`AUTHORING NEEDED`** banner on top telling any reader not to act under it. The scaffold prints
`NEEDS AUTHORING` for it, and the session that seated it (setup's, or a re-evaluation's) rewrites
it for the role following `skills/team-setup/references/seat-contract.md` (research the role, the
seven sections, hand-offs that agree with the neighbouring seats), then deletes the banner. **Until then the seat has no
worker, and `gen-team-agents.py --check` fails naming it**, so no seat works from a rulebook written
for someone else. After the rewrite, `python3 scripts/gen-team-agents.py` writes its worker and
`--check` passes.

**Splits.** With two or more web UI apps (folders whose `package.json` depends on a web UI framework),
*full* offers one frontend seat per app, up to four (💻 🪟 📟 🧩), each derived from `seat-frontend`
with its scope set to its own folder; past four apps the 🖥️ Frontend engineer stays and holds the
rest. *Recommended* does the same once the project is large.

**4. One question.** The owner sees the three options (recommended first), each seat with its reason
in plain words, and the two settings the rulebook needs: what only the owner does, and whether the
team uploads finished work to the shared code on its own once checks pass or asks each time. The
question also says that seats are opened in new sessions once setup finishes. The answer, with any
edit, is written to `docs/team/plan.json`, applied by `scaffold.py --plan --record "<your words>"`,
and recorded word for word in `docs/DECISIONS.md` as **DEC-2** (DEC-1, the team method, comes with
the register). Setup then finishes in the same session: it writes any new seat's rulebook and fills
every brief. Last, it tells you whom to open: **the CEO and the Chief of Staff now** (the CEO alone
when there is no Chief of Staff), other seats when their work comes up; the seats you don't open
are covered by their teams, and three to six open at once is typical.

## Re-evaluating the team

Say *"re-evaluate the team"* when a milestone closes, or when the team feels too big or too small.
`team-reevaluate` runs `reevaluate.py`, which **changes nothing**: it measures and proposes.

**What it measures**, per seated seat, over the last 30 days (or the window you name):

| Measure | Read from |
|---|---|
| commits | subjects that start with the seat's prefix: `design: …` or `design(web): …` (anything else counts as unattributed) |
| worker runs | run logs written under `scratchpad/team/runs/<team>/` |
| inbox | lines waiting in `scratchpad/team/inbox/<team>.md` |
| blocked | tracker lines inside the window where the seat is BLOCKED |
| repo changes | a fresh scan, diffed against `docs/team/scan.json`: signals new or gone since the baseline. With no baseline (a team seated by name, or before 1.3.0), nothing counts as new or gone, and the session saves one first so the comparison starts that day |

**What it proposes**, each with its evidence:

| Proposal | When |
|---|---|
| **add** | the option you picked at setup (`docs/team/plan.json`), planned on today's repo, calls for a seat that nothing seated covers (a merged seat covers its members, a frontend seat per app covers the Frontend engineer); the Chief of Staff once five or more other seats would run (seven in lean), the Scope Trimmer ten |
| **retire** | a seat with **no** commits, worker runs or inbox lines in the window, **and** nothing calling for it: no repo signal (a new role's or a per-app frontend seat's included, while its app folder stands), and not a Chief of Staff or Scope Trimmer the team still earns. Never the CEO or the Bar Raiser |
| **merge** | two or more members of one merge group are all **quiet**: at most 2 commits and at most 2 worker runs in the window, and not blocked. Never holding the CEO or the Bar Raiser, never Engineering & Platform past 2,000 source files; each merge claims its members, the one with more quiet members first |
| **unmerge** | a merged seat carries **at least 10 commits and at least 30%** of the commits attributed to any seat: it has outgrown the merge and splits back into its roles |
| **split** | the project is large, has two or more UI apps, and seats the Frontend engineer: one frontend seat per app |

**What is held back**, and listed under *Noted, not proposed* instead:
- **a seat seated inside the window** (its date in the lock): it gets no retire or merge proposal yet;
- **a retired seat**, unless the signal that called for it is new since the baseline;
- **a proposal you declined**: it is not put to you again unless one of the signals it rests on is
  new since the baseline, and was not already there when you declined it.

A seat idle for the window but still called for by the repo (Social, while there is a blog) is not
retired; it is a merge candidate.

**The session judges what the script counts.** Before the owner sees anything, it drops what the
numbers get wrong (seasonal work such as Funding between rounds, work committed without a prefix)
and says why. Then **one question**: the proposals in plain words, what was dropped or held back,
which sessions to open and close and whom you talk to now, and *apply all, apply some, or change
nothing*.

**Applying** is `scaffold.py --plan docs/team/reevaluation.json --only <the keys you approved>
--record "<your words>" --question "<the question>"`. *Apply all* passes every key put to you (a
proposal the session dropped stays declined unless you take it back), and *change nothing* is
`--only none`. Your words become one decision row: what changed, in seat names, and
what you declined. Every proposal you did not approve goes to `docs/team/declined.json`, so it is not
asked again. A change that is refused leaves the project untouched: seating a role a merged seat
already holds (unless the same plan splits that seat), or a mark already in use. Retired seats keep
their briefs under a "Retired" line and their workers are removed; a rulebook that is derived, the
project's own or edited since it was seated is archived to `docs/team/retired/<skill>-<date>`, never
deleted, and an unedited catalogue or merged copy is removed (the plugin still holds it). A merged
seat's brief carries its members' briefs; new derived seats are written for their role before they
work. When a re-evaluation's change was applied, **the baseline resets** (`scan.py --save`), so the
next re-evaluation diffs against today and a signal already answered is never raised twice; after
*change nothing* it stays (the declines are remembered instead), and so it does after a change you
named yourself. The generator's check runs green, every affected seat gets an inbox
line, and a session opened before the change is reopened to load the new rulebook.

## Anatomy of a seat rulebook

Every `seat-<team>` skill has the same seven sections, so any seat can read any other. A merged
seat's rulebook keeps each member's opening and sections under "As <member>"; a new seat's is written
to the same seven sections from `skills/team-setup/references/seat-contract.md`:

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
7. **The seat sends a stop line** to the Chief of Staff (the CEO when none is seated): done,
   blocked on whom, or waiting on you.
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
climbs Quick, Execution, Build; reading and judging climbs Scout, Check, Research, Deep. **Spawn by
tier name only**: a generic agent given a model shorthand can land on an older model generation. The models live in one place per project (the generator's
`TIERS` and `docs/TEAM.md` §2), so a new model is a one-line change and one command.

## When a seat is away

You won't have every seat open all the time. When a seat needs another that isn't open, it
**spawns that seat's own team** (`design-worker`), which carries that seat's rulebook and brief. The
team can apply existing rulings and do routine work; it **never makes a new ruling**. It writes a
*proposal* instead, and leaves one line in the absent seat's inbox, in the one format every inbox
line uses (`docs/TEAM.md` §5):

```
<date> · <sender mark and seat> → <recipient> · <TYPE> · <subject> · <evidence or path>
2026-03-04 · 📐 Design team (called by 🖥️ Frontend) → 📐 Design · RESULT · overdue badge: P-3 applies · scratchpad/team/runs/design/2026-03-04-overdue-badge.md
```

The seat reads its inbox first thing when it opens, deletes exactly the lines it read, and agrees or
corrects.

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
library gets 5 seats lean, 6 recommended, 7 full; a web product with sign-ups, payments, product
analytics, a pricing page and a blog gets 10 lean, then 12 recommended when tiny (every merge), 16
when small (the commercial seats merged, Research added) and 19 when medium (every role separate),
and 21 full, or 22 when it serves an API (a Docs writer joins). Lean is the answer when sessions are
scarce: for that web product, ten sessions hold sixteen roles. The [seats page](seats.md#starter-shapes)
keeps these figures, regenerated from the planner. The method has run with 21 seats on one
production project. A seat with no work is overhead, and re-evaluation finds it.

**Open sessions.** Each open seat is one Claude session, so your plan's session and usage limits
are the real ceiling. You don't need every seat open: closed seats are covered by their teams, so a
typical day might run with 3 to 6 seats open and the rest answering through their teams.

**Workers per seat.** Seats run workers in the background; keep each wave **under about ten workers**
so you can still follow them and so they don't contend for the same files (one owner per file per
wave). Waves run back to back as earlier ones finish.

**Cost shape.** Most of the volume runs on the cheap tiers. At short prompts, the Quick, Scout and
Check tiers cost roughly a twentieth of the Execution and Build tiers (the model publisher's figures),
so pushing exact-contract work down the ladder is the biggest saving. The seat sessions themselves
run on your session model and spend their tokens on judgement, steering and review, not on typing.

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
  rulebooks, and rulebooks the project had before setup, are the project's own and never synced.
  It ends by naming what it compared; reopen any session whose rulebook changed.
- **A newer generator:** the project's `scripts/gen-team-agents.py` is copied once, at setup, and
  never replaced. To pick up a newer one (1.3.0 writes no worker for a rulebook still awaiting
  authoring), copy `skills/team-setup/scripts/gen-team-agents.py` from the plugin over it, keeping
  any `TIERS` edit, and run it.
- **Resize the team:** *"re-evaluate the team"*: it measures, proposes, and applies only what you approve.
- **New seat:** *"add Design to the team"*: `team-reevaluate` carries out a change you name
  (`scaffold.py --add design --record "<your words>"`). You named it, so there is no question unless
  the measurement cuts against it; your words are the decision. A role a merged seat already holds is
  refused by `--add` alone, so the merged seat is split back into its roles in the same run
  (`--add sales,seo,social --retire growth`), and you are told.
- **Drop a seat:** *"retire Design"* (`scaffold.py --retire design --record "<your words>"`): its roster
  row and worker go, its brief stays with a "Retired" line on top, and its rulebook is archived to
  `docs/team/retired/` when it is derived, the project's own or edited (an unedited copy is removed).
  The CEO and the Bar Raiser are never retired on their own. Adding a retired seat back removes the
  "Retired" line, and a derived seat returns from its archived rulebook.
- **Audit the team:** read `scratchpad/team/inbox/` and `runs/`, and count which agents sessions
  spawned on which models. Generic agents with a model shorthand are the usual leak.
