# agent-team

[![check](https://github.com/fauzulkc/agent-team/actions/workflows/check.yml/badge.svg)](https://github.com/fauzulkc/agent-team/actions/workflows/check.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/fauzulkc/agent-team)](https://github.com/fauzulkc/agent-team/releases)

**agent-team is a Claude Code plugin that seats a team of AI roles in your project:** a CEO, an
Engineering lead, a Bar Raiser and whichever other seats your repo calls for, each one a session with
its own rulebook, its own workers on the right model, and a clear line on what it decides and what it
brings to you. Say *"set up the team"* and it scans the repo and offers three teams sized to it; later,
*"re-evaluate the team"* measures how each seat actually works and proposes changes.

**Who it is for:** anyone building a real project with Claude Code, alone or with a small team, who
wants the work split into roles that check each other, and wants to be asked only the questions that
are theirs to answer. It works in any repository: a small library gets five to seven seats, a web
product that takes sign-ups and payments ten to twenty-two.

**Status:** MIT licence. Every release is listed in [CHANGELOG.md](CHANGELOG.md).

```mermaid
flowchart LR
    you(["👤 You"]) <-->|"decisions only"| cos["🛎️ Chief of Staff"]
    cos <--> ceo["🧭 CEO · decisions"]
    ceo --> seats["🎯 ⚙️ 🖥️ 📐 💼 … seats"]
    seats <-->|"ASK · HANDOFF · RESULT"| seats
    seats -->|"FOR REVIEW"| br["⚖️ Bar Raiser"]
    seats -->|"contracts, steering"| teams["each seat's own team<br/>+ seven model tiers"]
    seats -->|"STOP lines"| cos
```

- **A team sized from evidence, not a template.** The scan reads manifests, file names, CI, deploy
  configs and git history; each proposed seat cites what raised it (*"a payment library is in the
  dependencies"*). A small project gets merged seats; a large one with several apps gets a frontend
  seat per app.
- **The team changes as the work does.** Re-evaluation counts each seat's commits, worker runs, inbox
  and blocked lines, re-scans the repo, and proposes adding, retiring, merging, splitting back or
  splitting seats. Nothing changes without your yes.
- **Roles that think like the best operator of the job at a fast startup**, written as rulebooks with
  sourced principles, a method, hard-won traps, and a fixed way to report.
- **Every seat runs its own team.** The typing goes to cheap, fast models and the thinking to strong
  ones, steered from above. Verbose work stays in the workers' logs; the seat keeps the judgement.
- **Seats cover for each other.** When a seat isn't open, the others call its team, which works under
  its rulebook and leaves a note for when it returns.
- **Speed from cutting work, never from cutting truth.** Reversible decisions are made fast; claims,
  numbers and anything public keep every check.

## Install

You need [Claude Code](https://github.com/anthropics/claude-code), `python3` 3.9 or newer (the skills'
scripts use the standard library only) and `git` (the scan and the re-evaluation read the project's
history).

**As a plugin** (recommended), from a shell:

```bash
claude plugin marketplace add fauzulkc/agent-team
claude plugin install agent-team@agent-team
```

or from inside a Claude Code session: `/plugin marketplace add fauzulkc/agent-team`, then
`/plugin install agent-team@agent-team`. Open a new session afterwards so the two skills load. Recent
Claude Code versions also take one line, `claude plugin install agent-team --marketplace fauzulkc/agent-team`;
an older version without that option uses the two steps above.

**On Windows**, the scripts run as `python3` from Claude Code's Git Bash, so `python3` must open a real
Python: turn off the Microsoft Store aliases for `python.exe` and `python3.exe` (Settings, Apps,
Advanced app settings, App execution aliases) and make sure a `python3` command is on your PATH.

**Without the plugin system**, clone the repo and link the skills:

```bash
git clone https://github.com/fauzulkc/agent-team
./agent-team/install.sh
```

`install.sh` links `team-setup` and `team-reevaluate` from the clone into `~/.claude/skills/` and
`~/.agents/skills/`, and prints each link it made. It never replaces a real folder of the same name.
To remove the skills, delete those links.

**From a local clone, as a plugin** (to try a change before it is released):
`claude plugin marketplace add ./agent-team`, then `claude plugin install agent-team@agent-team`.

### Update

```bash
claude plugin marketplace update agent-team
claude plugin update agent-team@agent-team
```

Restart Claude Code to load the new version. With the manual install, `git -C agent-team pull` is the
whole update: the links point at the clone. Then, in each project that already has a team, say
**"sync the team's rulebooks"**: it refreshes every rulebook copied from the catalogue and recomposes
every merged seat, keeps any rulebook the project wrote or edited exactly as it is, and names what it
compared. What changed in each version is in [CHANGELOG.md](CHANGELOG.md).

## Quick start

1. **Seat the team.** Open Claude Code in your project and say **"set up the team"**. It reads and
   scans the project, sizes it, and asks you once: which of three teams (lean, recommended, full,
   each seat with its reason), what only you do, and whether the team uploads finished work to your
   shared code on its own once checks pass or asks you each time. You can edit the pick: add, drop,
   merge or split a seat. Then it writes the team in: rulebooks, roster, a decisions register with
   your answer word for word, one brief per seat, workers and scratch space. A seat created for a role
   no catalogue seat covers gets its rulebook written before it works.
2. **Open the CEO and the Chief of Staff**, each in a new session named after it:
   `/seat-ceo catch up and work your inbox`, then `/seat-chief-of-staff catch up and work your inbox`
   (the CEO alone when the team has no Chief of Staff). Open other seats when their work comes up;
   the seats you don't open are covered by their teams. Three to six open at once is typical.
3. **Talk to the Chief of Staff** (or the CEO, when there is no Chief of Staff) like a person:
   *"Freelancers keep asking for recurring invoices. Let's do it."* It comes back with only what
   needs you, in one shape: decision needed, summary, progress by objective, detail if you ask.
4. **Re-evaluate it later.** As the work changes (after a milestone is a good moment), say
   **"re-evaluate the team"**. It reports each seat's activity over the last 30 days and what changed
   in the repo, then asks once: apply all, some or none of its proposals. What you decline is
   remembered and not put to you again unless the repo changes in a way that calls for it.

You can also **change the team by name** at any time: *"add Motion to the team"*, *"retire Design"*.
You named it, so your words are the decision and there is no question unless the measurement cuts
against them. A role a merged seat already holds (*"add Sales"* while 📈 Growth holds it) comes back
by splitting that seat into its roles, and you are told.

The [walkthrough](examples/walkthrough.md) tells the whole story prompt by prompt on an invented app,
Tally; [examples/tally/](examples/tally/) holds the files a seated project carries.

## What is inside

**Two skills.**

| Skill | Say | What it does |
|---|---|---|
| 🧩 `team-setup` | *"set up the team"*, *"sync the team's rulebooks"* | scans the repo, offers lean, recommended and full teams with the evidence for each seat, writes the team into the project, and later refreshes its rulebooks after a plugin update |
| 🔁 `team-reevaluate` | *"re-evaluate the team"*, *"add Sales to the team"*, *"retire Design"* | measures how each seat works and what the repo needs now, proposes seats to add, retire, merge, unmerge or split, applies what you approve, and carries out a change you name |

**The seats.** A catalogue of **29 rulebooks**: CEO, Chief of Staff, Product, Engineering, Frontend
engineer, Mobile engineer, Testing, Platform, Security, Research, Bar Raiser, Scope Trimmer, Design,
Motion & Production, Sales & Marketing, SEO & Publicity, Data engineer, ML engineer, Docs writer,
Community & DevRel and more. All 29, with what each does and when to seat it, are in
[docs/seats.md](docs/seats.md).

- **Merged seats.** While the work is small, one session can hold several roles: 📈 Growth (Sales,
  SEO, Social), 🎨 Product & Design, 🔧 Engineering & Platform, 🛡️ Quality (Testing and the Bar
  Raiser), 💰 Money, 📜 Legal & Compliance, 🧮 Data & ML and 🫱 Customer. A merged rulebook is
  composed from its members' rulebooks with every rule kept, and recomposed on each sync.
- **New seats.** Four roles no catalogue seat covers are derived from a base rulebook when the repo
  calls for them (hardware and firmware, smart contracts, desktop, browser extension), and a large
  project gets one frontend seat per UI app. Each is written for its role before it works.
- **Model tiers.** Every seat's workers start at the cheapest tier that can do the job and move up only
  when work comes back half-done: edits climb Quick, Execution, Build; reading and judging climb
  Scout, Check, Research, Deep. Models are named in one place per project, so a new model is a
  one-line change.

| Tier | Default model | For |
|---|---|---|
| Quick | Haiku 5.5, low effort | an edit or check a precise brief fully specifies |
| Scout | Haiku 5.5, low effort | read-only searches and counts |
| Check | Haiku 5.5, medium effort | long checklists, finished in full |
| Execution | Sonnet, low effort | each seat's own routine work |
| Build | Sonnet, high effort | multi-file builds, debugging, half-done work |
| Research | Opus, high effort | probes, audits, reviews |
| Deep | Opus, maximum effort | decisions that can't be undone |

**What a seated project carries.** The chosen rulebooks are copied into the project's
`.claude/skills/`, so anyone who clones it has the seats; `docs/TEAM.md` holds the roster and the
shared rules, `docs/DECISIONS.md` the decisions in your words, `docs/team/` one brief per seat,
`.claude/agents/` each seat's workers, and `scratchpad/team/` the inboxes and run logs.

### Capacity, briefly

- **Seats:** the scan sizes the project as **tiny** (under 60 source files and 50 commits), **small**
  (under 600 source files, three contributors or fewer), **medium** (under 3,000 source files) or
  **large**, and the recommended team scales with it: every allowed merge when tiny, the commercial
  seats merged when small, every role separate when medium, and a frontend seat per UI app when
  large. Measured on invented test projects: a small library gets 5 to 7 seats; a web product that
  takes sign-ups and payments gets 10 lean, and 12 recommended when tiny, 16 when small, 19 when
  medium; 21 full, or 22 when it serves an API. The method has run with 21 seats on one production
  project.
- **Open at once:** each open seat is a Claude session, so your plan's limits set the ceiling; closed
  seats are covered by their teams, so 3 to 6 open seats is a typical day.
- **Workers:** each seat runs waves of background workers, kept under about ten at a time.
- **Not included:** it doesn't run unattended, and it never acts publicly, spends, signs or makes a
  legal determination without you.

Details: [docs/how-it-works.md](docs/how-it-works.md#capacity-what-to-expect).

## How you stay in charge

You're asked only what only you can decide: anything public, any spend, anything legal or
irreversible, and real forks in direction. Everything reversible happens without you.

| You're asked | You're not asked |
|---|---|
| which team, at setup: lean, recommended or full, with any edits; and whether finished work is uploaded on its own or you're asked each time | how to build what's already in scope |
| a re-evaluation's proposals, once, when you ask for one | each seat one by one, or how a merged or new seat's rulebook is written |
| anything public: posts, emails to customers, invites, press | which worker or model does a task |
| any spend, and prices | routing between seats, covering an absent seat |
| sign-ups, contracts, terms | free, reversible experiments and checks |
| anything irreversible | fixing the team's own docs |
| a real fork that cuts against a preference you stated | ordering work inside the current milestone |
| new goals or milestones | recording decisions you already made |

Questions are batched through one seat, asked once, and your answers are recorded word for word; a
team change you decline is not proposed again unless the repo changes in a way that calls for it. The
full line between your decisions and the team's: [docs/owner-touchpoints.md](docs/owner-touchpoints.md).

## Documentation

| Page | What it covers |
|---|---|
| [How it works](docs/how-it-works.md) | the layers, how the team is sized and re-evaluated, the seat rulebook anatomy, the work loop, tiers, messages, capacity |
| [Orchestration diagrams](docs/orchestration-diagrams.md) | the scenarios drawn out, from seating and sizing the team to re-evaluating it, with the prompts at each step |
| [When you're asked](docs/owner-touchpoints.md) | the full line between your decisions and the team's |
| [The seats](docs/seats.md) | all 29, the merged seats and the new roles: what each does, and when to seat it |
| [Walkthrough](examples/walkthrough.md) | an example project, prompt by prompt |
| [Example project](examples/tally/) | the files a seated project carries |
| [Maintaining](docs/maintaining.md) | for maintainers: triage, reviewing a pull request, cutting a release, generated files, repository settings |

## Contributing

Contributions are welcome: a sharper rule in a rulebook, a new seat, a fix to the scan or the planner.
[CONTRIBUTING.md](CONTRIBUTING.md) explains where each kind of change goes. A pull request adds a line
under **Unreleased** in [CHANGELOG.md](CHANGELOG.md), and these pass:

```bash
python3 check.py                          # rulebook shape, project neutrality, generated docs current
python3 -m unittest discover -s tests     # scan, planner, scaffold and re-evaluation on fixture projects
python3 tools/measure_tally.py --check    # the walkthrough's figures, when the scripts changed
claude plugin validate .                  # the plugin and marketplace manifests
```

- **Bugs, ideas and new seats:** [open an issue](https://github.com/fauzulkc/agent-team/issues/new/choose);
  there is a form for each.
- **Questions and help:** [SUPPORT.md](SUPPORT.md).
- **Security issues:** report them privately as [SECURITY.md](SECURITY.md) describes, never in a public
  issue.
- **Conduct:** everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
- **How decisions are made:** [GOVERNANCE.md](GOVERNANCE.md).

The repository's layout:

```
.claude-plugin/          plugin.json (the version lives here) and marketplace.json
skills/team-setup/       the setup skill: SKILL.md, scripts/, templates/, references/
  seats/                 the 29 catalogue rulebooks, seat-<role>/SKILL.md
skills/team-reevaluate/  the re-evaluation skill (it runs team-setup's scripts)
docs/                    the documentation above; seats.md and facts.json are generated
examples/                the walkthrough and the seated example project, Tally
tools/                   the generators, the walkthrough's measurement, bump_version.py for releases
tests/                   unit and end-to-end tests on invented fixture projects
.github/                 the check and release workflows, issue forms, labels
check.py                 the repo check CI runs on every push and pull request
install.sh               the install without the plugin system
```

## Licence

MIT. Copyright (c) 2026 Fauzul Chowdhury. See [LICENSE](LICENSE).
