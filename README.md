# agent-team

**Seat a team of AI roles in any project.** Say *"set up the team"* and Claude Code seats the roles
your project needs (CEO, Engineering, Design, Sales and up to 21 more), each one a session with
its own rulebook, its own team of workers on the right model, and a clear line on what it decides
and what it brings to you.

- **Roles that think like the best operator of the job at a fast startup**, written as rulebooks
  with sourced principles, a method, hard-won traps, and a fixed way to report.
- **Every seat runs its own team.** The typing goes to cheap, fast models and the thinking to
  strong ones, steered from above. Verbose work stays in the workers' logs; the seat keeps the judgement.
- **Seats cover for each other.** When a seat isn't open, the others call its team, which works
  under its rulebook and leaves a note for when it returns.
- **You're asked only what only you can decide**: anything public, any spend, anything legal or
  irreversible, real forks in direction. Everything reversible happens without you.
- **Speed from cutting work, never from cutting truth**: reversible decisions are made fast; claims,
  numbers and anything public keep every check.

```mermaid
flowchart LR
    you(["👤 You"]) <-->|"decisions only"| cos["🛎️ Chief of Staff"]
    cos <--> ceo["🧭 CEO · decisions"]
    ceo --> seats["🎯 ⚙️ 🖥️ 📐 💼 … seats"]
    seats <-->|"ASK · HANDOFF · RESULT"| seats
    seats -->|"FOR REVIEW"| br["⚖️ Bar Raiser"]
    seats -->|"contracts, steering"| teams["each seat's own team<br/>+ six model tiers"]
    seats -->|"STOP lines"| cos
```

## Install

As a Claude Code plugin, from any session:

```
/plugin install agent-team --marketplace <github-user>/agent-team
```

or from a shell:

```bash
claude plugin marketplace add <github-user>/agent-team
claude plugin install agent-team@agent-team
```

From a local clone: `claude plugin marketplace add ./agent-team`, then the install line above.
Without the plugin system: `./install.sh` links `team-setup` into your global skills.

## Use

1. **Seat the team.** Open Claude Code in your project and say **"set up the team"**. It reads the
   project, proposes the smallest set of seats with a reason for each, asks you once, then writes the
   team in (rulebooks, roster, decisions register, one brief per seat, workers, scratch space).
2. **Open the seats you need**, each in its own session named after it:
   `/seat-ceo catch up and work your inbox` (the CEO first, then the Chief of Staff).
3. **Talk to the Chief of Staff** like a person: *"Freelancers keep asking for recurring invoices.
   Let's do it."* It comes back with only what needs you, in one shape: decision needed, summary,
   progress by objective, detail if you ask.
4. **Grow it** as the work appears: *"add Sales to the team"*. **Refresh it** after an update:
   *"sync the team's rulebooks"*.

A full prompt-by-prompt story on an example project is in [examples/walkthrough.md](examples/walkthrough.md);
the files it produced are in [examples/tally/](examples/tally/).

## What you'll be asked, and what you won't

| You're asked | You're not asked |
|---|---|
| which seats, at setup | how to build what's already in scope |
| anything public: posts, emails to customers, invites, press | which worker or model does a task |
| any spend, and prices | routing between seats, covering an absent seat |
| sign-ups, contracts, terms | free, reversible experiments and checks |
| anything irreversible | fixing the team's own docs |
| a real fork that cuts against a preference you stated | ordering work inside the current milestone |
| new goals, milestones or seats | recording decisions you already made |

Questions are batched through one seat, asked once, and your answers are recorded word for word.
Full rules: [docs/owner-touchpoints.md](docs/owner-touchpoints.md).

## The model tiers

| Tier | Default model | For |
|---|---|---|
| Quick | Haiku 5.5, low effort | an edit or check a precise brief fully specifies |
| Scout | Haiku 5.5, low effort | read-only searches and counts |
| Check | Haiku 5.5, medium effort | long checklists, finished in full |
| Execution | Sonnet, low effort | each seat's own routine work |
| Build | Sonnet, high effort | multi-file builds, debugging, half-done work |
| Research | Opus, high effort | probes, audits, reviews |
| Deep | Opus, maximum effort | decisions that can't be undone |

Workers start at the cheapest tier that can do the job and move up one step only when work comes
back half-done. Models are named in one place per project, so a new model is a one-line change.

## Capacity, briefly

- **Seats:** 21 in the catalogue; most projects run well on 4 to 9. The method has run with all 21
  seated on one production project.
- **Open at once:** each open seat is a Claude session, so your plan's limits set the ceiling; closed
  seats are covered by their teams, so 3 to 6 open seats is a typical day.
- **Workers:** each seat runs waves of background workers, kept under about ten at a time.
- **Not included:** it doesn't run unattended, never acts publicly, spends, signs or makes legal
  determinations without you.

Details: [docs/how-it-works.md](docs/how-it-works.md#capacity-what-to-expect).

## Docs

| | |
|---|---|
| [How it works](docs/how-it-works.md) | the layers, the seat rulebook anatomy, the work loop, tiers, messages, capacity |
| [Orchestration diagrams](docs/orchestration-diagrams.md) | seven scenarios drawn out, with the prompts at each step |
| [When you're asked](docs/owner-touchpoints.md) | the full line between your decisions and the team's |
| [The seats](docs/seats.md) | all 21, what each does, and when to seat it |
| [Walkthrough](examples/walkthrough.md) | an example project, prompt by prompt |
| [Example project](examples/tally/) | the files a seated project carries |

## Develop

`python3 check.py` proves every seat rulebook has its mark, the seven sections, no model names and
no project-specific facts. `claude plugin validate .` checks the plugin. See [CONTRIBUTING.md](CONTRIBUTING.md).

MIT licensed.
