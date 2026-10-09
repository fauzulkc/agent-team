# How the agents orchestrate: scenario diagrams

Every scenario uses one invented example: **Tally**, a small invoicing app for freelancers, run by
its owner with a seated team. The quoted lines are the prompts as typed, by you or by a seat.
The diagrams are [Mermaid](https://mermaid.js.org/); GitHub renders them in place.

**Legend.** *You* are the owner. A **seat** is a Claude session you open with its skill (`/seat-ceo`).
A **team** is that seat's own worker (`engineering-worker`), spawned by the seat. The **tiers**
(`team-quick`, `team-scout`, `team-check`, `team-build`, `team-research`, `team-deep`) are shared workers on
cheaper or stronger models.

---

## 0 · The shape of the team

```mermaid
flowchart TB
    owner(["👤 You, the owner"])
    subgraph owner_side["Owner-side seats"]
        cos["🛎️ Chief of Staff<br/>talks to you, keeps the tracker"]
        ceo["🧭 CEO<br/>decision register, queue"]
    end
    subgraph directors["Director, manager and implementation seats (only the ones the work needs)"]
        product["🎯 Product"]
        eng["⚙️ Engineering"]
        fe["🖥️ Frontend"]
        design["📐 Design"]
        sales["💼 Sales"]
        more["… up to 21 seats"]
    end
    subgraph checks["Check seats"]
        br["⚖️ Bar Raiser"]
        user["👤 User"]
    end
    subgraph tiers["Shared tiers (cheapest first)"]
        quick["team-quick"] --- scout["team-scout"] --- check["team-check"]
        build["team-build"] --- research["team-research"] --- deep["team-deep"]
    end
    workers["Each seat's own team<br/>engineering-worker, design-worker, …"]

    owner <-->|"decisions, approvals"| cos
    cos <-->|"evidence, relays"| ceo
    ceo -->|"decisions, queue"| directors
    directors <-->|"ASK, HANDOFF, RESULT"| directors
    directors -->|"FOR REVIEW"| checks
    directors -->|"dispatch, steer"| workers
    directors -->|"dispatch by tier"| tiers
    directors -->|"STOP lines"| cos
```

---

## 1 · Seating the team

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant Setup as 🧩 team-setup
    participant Repo as Tally repo
    You->>Setup: "set up the team"
    Setup->>Repo: read README, package.json, CI, deploy config, git log
    Setup-->>You: "Seat CEO, Chief of Staff, Product, Engineering, Frontend, Testing, Bar Raiser? Only you publish, spend and sign. You push."
    You->>Setup: "yes, and add Design"
    Setup->>Repo: scaffold: docs/TEAM.md, DECISIONS.md, one brief per seat, .claude/skills, .claude/agents, scratchpad
    Setup->>Repo: fill each seat's brief from what it measured (commands, paths, traps)
    Setup-->>You: "Open the CEO first: /seat-ceo catch up and work your inbox"
```

**Asks you:** once, for the seats and the two settings. Everything else is measured from the repo.

---

## 2 · A feature, from your sentence to shipped

You type one sentence to the Chief of Staff. Six seats and several workers move; you are asked once.

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant CoS as 🛎️ Chief of Staff
    participant CEO as 🧭 CEO
    participant PM as 🎯 Product
    participant ENG as ⚙️ Engineering
    participant W as engineering-worker / team-build
    participant FE as 🖥️ Frontend
    participant DS as 📐 Design
    participant BR as ⚖️ Bar Raiser

    You->>CoS: "Freelancers keep asking for recurring invoices. Let's do it."
    CoS->>CEO: ASK · recurring invoices into the active milestone? (evidence: 9 support emails)
    CEO->>CEO: two-way door, in scope → decides, records DEC-2
    CEO->>PM: RULED · DEC-2: recurring invoices, this milestone
    PM->>ENG: HANDOFF · scope note: monthly and weekly only, no proration (appetite: one milestone)
    ENG->>W: contract: schema + scheduler, tests to paste, paths allowed, "no git"
    W-->>ENG: ≤10 lines: done, tests green (pasted), run log path
    ENG->>DS: ASK · how does a recurring invoice look in the list?
    DS-->>ENG: RULED · a repeat badge, never a second colour (pattern P-3)
    ENG->>FE: QUEUE · 1. list badge per P-3, 2. schedule picker
    FE->>FE: spawns frontend-worker, runs the web tests, screenshots both widths
    FE->>BR: FOR REVIEW · commit abc123
    BR->>BR: re-measures on the running app, tries a 31st-of-month schedule
    BR-->>FE: FAIL · Feb 31 → crash (guard test attached)
    FE->>FE: fix, guard seen red then green
    BR-->>ENG: PASS
    ENG->>CoS: STOP · recurring invoices · DONE · deployed behind the flag
    CoS-->>You: "Recurring invoices are built and behind a switch. Decision needed: turn it on for everyone?"
    You->>CoS: "turn it on"
```

**Asks you:** once, at the end, because turning a feature on for customers is outward. Scope, design,
build, review and the bug fix happened without you.

---

## 3 · A seat is away: its team covers

Design isn't open today. Frontend needs a design ruling and doesn't wait for one.

```mermaid
sequenceDiagram
    autonumber
    participant FE as 🖥️ Frontend
    participant DW as design-worker (Design's own team)
    participant Inbox as scratchpad/team/inbox/design.md
    participant DS as 📐 Design (opens tomorrow)

    FE->>FE: list open sessions → Design not open
    FE->>DW: "Under your rulebook and docs/team/design.md: does the overdue badge reuse pattern P-3? If it needs a new ruling, PROPOSE it."
    DW-->>FE: RESULT · P-3 covers it (red is reserved for errors, overdue uses the warning tone)
    DW->>Inbox: 2026-03-04 · 🖥️ Frontend · overdue badge · RESULT P-3 applies · runs/design/2026-03-04-overdue.md
    Note over DW,Inbox: anything needing a NEW ruling is written as PROPOSAL, never decided by the team
    DS->>Inbox: first action next session: read, absorb, delete exactly those lines
    DS->>DS: agrees, or records a correction and tells Frontend
```

**Asks you:** never. A team can apply its seat's existing rulings and propose new ones; only the seat rules.

---

## 4 · The tier ladder: start cheap, move up one step

```mermaid
flowchart LR
    task["Task: rename `client` to `customer` across 40 files"] --> quick["team-quick<br/>exact contract, cheapest"]
    quick -->|"returns a summary where the contract asked for the diff list"| exec["engineering-worker<br/>execution tier"]
    exec -->|"two tests now fail: a fixture still says client"| build["team-build<br/>reasons before typing"]
    build -->|"fixed, whole test leg pasted"| review["⚙️ Engineering reviews:<br/>re-runs the load-bearing command"]
    review --> land["commit by explicit paths"]
```

**The rule:** start at the cheapest tier that can do the job. Move up one tier only when a worker
returns half-done work: a summary instead of a table, a skipped check, a guess where the contract
said stop, or a fix that doesn't pass the whole test leg. `team-deep` is never a default.

---

## 5 · A one-way door: a public claim

Sales wants a homepage line: *"Freelancers get paid 9 days faster with Tally."*

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant S as 💼 Sales
    participant R as 🔬 Research
    participant D as team-deep
    participant CoS as 🛎️ Chief of Staff

    S->>R: ASK · can we say "paid 9 days faster"? (source: last month's dashboard)
    R->>D: one-way door: "re-derive 9 days from raw payments, name every way it could be wrong, check the denominator"
    D-->>R: the 9 days compares Pro users to Free users: a selection effect. Same users before/after: 4 days (n=212)
    R-->>S: RESULT · "4 days faster, measured on the same freelancers before and after" is defensible, "9" is not
    S->>S: rewords: "Freelancers on Tally get paid 4 days sooner."
    S->>CoS: owner ask: approve this line for the homepage, word for word
    CoS-->>You: "Decision needed: put 'Freelancers on Tally get paid 4 days sooner.' on the homepage?"
    You->>CoS: "approved"
```

**Asks you:** once, for the published words. The audit that turned 9 into an honest 4 needed nobody's permission.

---

## 6 · Should this go to the owner?

```mermaid
flowchart TD
    start(["A seat is about to act"]) --> outward{"Does it leave the building?<br/>publish · send · invite · post"}
    outward -->|yes| ask(["Ask the owner<br/>via the Chief of Staff, batched"])
    outward -->|no| money{"Does it spend money<br/>or set a price?"}
    money -->|yes| ask
    money -->|no| legal{"Legal or identity?<br/>sign · contract · terms"}
    legal -->|yes| ask
    legal -->|no| undo{"Can it be undone cheaply?"}
    undo -->|no| ask
    undo -->|yes| scope{"Inside the active scope<br/>and the owner's stated preferences?"}
    scope -->|"no: new goal, new milestone,<br/>or evidence against a stated preference"| ceo["CEO decides whether it is the owner's call"]
    ceo -->|"material fork"| ask
    ceo -->|"within prior decisions"| decide
    scope -->|yes| decide(["Decide in the seat · log it · report it"])
```

---

## 7 · A day, end to end

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant CoS as 🛎️ Chief of Staff
    participant Seats as Open seats
    participant Teams as Seat teams + tiers
    You->>CoS: morning: "catch me up"
    CoS-->>You: Decision needed (2) · summary · by milestone
    You->>CoS: answers, in your words
    CoS->>Seats: OWNER ANSWER, verbatim, to every seat it touches
    loop all day
        Seats->>Teams: contracts (background), steer with one line when they drift
        Teams-->>Seats: ≤10-line results, verbose logs in scratchpad/team/runs/
        Seats->>Seats: ASK · HANDOFF · FOR REVIEW · PASS/FAIL · LANDED
        Seats->>CoS: STOP lines
    end
    CoS-->>You: evening: what landed, what is blocked on whom, what waits on you
```
