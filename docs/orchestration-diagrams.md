# How the agents orchestrate: scenario diagrams

Every scenario uses one invented example: **Tally**, a small invoicing app for freelancers, run by
its owner with a seated team. The quoted lines are the prompts as typed, by you or by a seat.
The diagrams are [Mermaid](https://mermaid.js.org/); GitHub renders them in place.

**Legend.** *You* are the owner. A **seat** is a Claude session you open with its skill (`/seat-ceo`).
A **team** is that seat's own worker (`engineering-worker`), spawned by the seat. The **tiers**
(`team-quick`, `team-scout`, `team-check`, `team-build`, `team-research`, `team-deep`) are shared workers on
cheaper or stronger models. A **merged seat** is one session holding several roles while their work
is small, every rule of each kept (📈 Growth holds Sales, SEO and Social). A **new seat** is a role
the catalogue does not have, or one seat split per app (🔌 Hardware & firmware engineer): its
rulebook is derived from the nearest one, then written for its role before it works.
**🧩 team-setup** seats the team once; **🔁 team-reevaluate** resizes it later. You run both.

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
        more["… a catalogue of 29,<br/>merged or new as the repo needs"]
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

Setup scans the repo, sizes it, and offers three teams, every seat with the evidence that put it
there. Tally's repo measures medium (661 source files, four contributors), so the recommended team
keeps each role in its own seat. A smaller repo gets merged seats instead (scenario 8). The whole
setup runs in this one session; seats are opened in new sessions afterwards.

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant Setup as 🧩 team-setup
    participant Tools as scan · plan · scaffold
    participant Repo as Tally repo
    You->>Setup: "set up the team"
    Setup->>Repo: read README, CLAUDE.md, git log, test commands, deploy config
    Setup->>Tools: scan the repo
    Tools->>Repo: manifests, file names, CI, contributors, commits
    Tools-->>Setup: signals, each with its evidence: web UI, an API, payments, sign-in, email,<br/>product analytics, personal data, pricing page, blog, tests, deploy · size: medium<br/>saved as docs/team/scan.json, the baseline for re-evaluating later
    Setup->>Tools: plan three options
    Tools-->>Setup: recommended 19 · lean 10 · full 22, every seat with its why
    Setup-->>You: "Decision needed: which team for Tally?<br/>Recommended, 19 seats, each with its reason:<br/>Frontend engineer, it has a web interface ·<br/>Payments, a payment library is in the dependencies ·<br/>Social, it publishes posts (a blog) · …<br/>Lean, 10: related roles share one session<br/>(Sales, SEO and Social as one Growth seat).<br/>Full, 22: adds Competition, Funding and a Docs writer for the API.<br/>Also: what only you do (publishing, sending, spending, signing),<br/>and when finished work is ready, should the team upload it to the shared code<br/>on its own once checks pass, or ask you each time? (Recommended: ask me.)<br/>Seats are opened in new sessions once setup is done."
    You->>Setup: "recommended, and emailing customers is mine too"
    Setup->>Tools: scaffold that plan, with your answer
    Tools->>Repo: docs/TEAM.md, one brief per seat, .claude/skills, .claude/agents, scratchpad
    Tools->>Repo: DECISIONS.md: DEC-2, the team, with your words verbatim
    opt a seat the catalogue does not have (a new role, or a split)
        Setup->>Repo: write its rulebook for its role, in this session
        Note over Setup,Repo: until it is written the seat has no worker and the generator's check fails
    end
    Setup->>Repo: fill each seat's brief from what it measured (commands, paths, traps)
    Setup-->>You: "Open the CEO and the Chief of Staff now, each in a new session:<br/>/seat-ceo catch up and work your inbox<br/>/seat-chief-of-staff catch up and work your inbox<br/>Open other seats when their work comes up. Their teams cover them meanwhile."
```

**Asks you:** once: which of the three teams, with the two settings (what only you do, and whether
finished work is uploaded to the shared code on its own or you're asked each time). You may edit
the pick (add, drop, merge or split a seat). Everything else is measured from the repo. Your answer
is the register's **DEC-2** (DEC-1, the team method, comes with it).

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
    CEO->>CEO: two-way door, in scope → decides, records DEC-3
    CEO->>PM: RULED · DEC-3: recurring invoices, this milestone
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
    CoS->>CEO: OWNER ANSWER · "turn it on", verbatim → recorded as DEC-4
```

**Asks you:** once, at the end, because turning a feature on for customers is outward. Scope, design,
build, review and the bug fix happened without you. (DEC-2 is the team itself, recorded at setup.)

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
    DW->>Inbox: 2026-03-04 · 📐 Design team (called by 🖥️ Frontend) → 📐 Design · RESULT · overdue badge: P-3 applies · runs/design/2026-03-04-overdue-badge.md
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

**The rule:** start at the cheapest tier that can do the job. Move up to the next tier that can do
that kind of work only when a worker
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

---

## 8 · Sizing the team: merged, separate and new seats

The scan's signals say which roles the repo needs. Its size says how many sessions should hold them.

```mermaid
flowchart TB
    scan["🔎 Repo scan<br/>signals, each with its evidence<br/>web UI · mobile app · payments · sign-in · blog · firmware · …"]
    scan --> size{"Size class<br/>code files · commits · contributors"}
    size -->|"under 60 code files<br/>and 50 commits"| tiny["tiny"]
    size -->|"under 600 code files<br/>and 3 people or fewer"| small["small"]
    size -->|"under 3,000 code files"| medium["medium"]
    size -->|"3,000 or more"| large["large"]
    tiny & small & medium & large --> options
    subgraph options["Three options, every seat with its why"]
        lean["Lean<br/>every allowed merge<br/>optional seats dropped"]
        rec["Recommended<br/>tiny: every merge<br/>small: the commercial seats merge<br/>medium: every role separate<br/>large: separate + a Frontend per UI app"]
        full["Full<br/>every role separate<br/>optional seats added<br/>a Frontend per UI app"]
    end
    options --> pick(["👤 You pick one, and may edit it"])
    pick -->|"lean, or a tiny or small repo"| merged
    pick -->|"full, or a large repo,<br/>with two or more UI apps"| split
    pick -->|"any option, when a signal<br/>has no catalogue seat"| created
    subgraph merged["Merged: one session, several roles"]
        sales["💼 Sales"] & seo["📣 SEO"] & social["💬 Social"] --> growth["📈 Growth<br/>every rule of each kept"]
    end
    subgraph split["Split: one Frontend per UI app"]
        fe["🖥️ Frontend"] --> fe_admin["💻 Frontend engineer (admin)<br/>only apps/admin/"]
        fe --> fe_web["🪟 Frontend engineer (web)<br/>only apps/web/"]
    end
    subgraph created["New: a role the catalogue lacks"]
        firmware["signal: firmware/"] --> derived["🔌 Hardware & firmware engineer<br/>derived from the nearest rulebook"]
        derived --> authored["written for its role<br/>before it works"]
    end
    merged -.-|"every merge obeys"| checks
    subgraph checks["Check seats never merge with a builder"]
        quality["⚖️ Bar Raiser + 🧪 Testing<br/>→ 🛡️ Quality<br/>allowed: still a check"]
        never["⚖️ Bar Raiser + ⚙️ Engineering<br/>never: a seat would<br/>check its own work"]
    end
```

**The rules:** the CEO and the Bar Raiser are in every option (in lean, the Bar Raiser sits inside
Quality). The Chief of Staff joins from five other seats (seven in lean) and the Scope Trimmer from
ten other seats ("other" leaves out those two), because they earn their seat by the sessions they
coordinate. Check seats (Bar Raiser, Scope Trimmer, User, Security) join only a check merge: Quality
is the one, and no merge a re-evaluation proposes holds the CEO or the Bar Raiser. A merge claims its
members, so two merges never share one. Other new roles come the same way as Hardware & firmware: a
smart-contract, desktop or browser-extension engineer, each raised by its own signal.

---

## 9 · Re-evaluating the team a month later

Tally has worked for a month. You ask for a re-evaluation; it measures, proposes, and changes
nothing until you answer.

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant RE as 🔁 team-reevaluate
    participant Tools as reevaluate · scaffold · scan
    participant Repo as Tally repo
    participant Inbox as seat inboxes
    You->>RE: "re-evaluate the team"
    RE->>Tools: measure the last 30 days
    Tools->>Repo: commits by seat prefix (seo: …, design(web): …)
    Tools->>Repo: worker run logs, inbox lines waiting, BLOCKED lines in the tracker
    Tools->>Repo: a fresh scan against the baseline saved at setup
    Tools-->>RE: Sales 1 commit, SEO 1, Social 0, no worker runs for any of them<br/>new since setup: a mobile app in apps/mobile/
    RE-->>You: report: activity per seat, then two proposals, each with its evidence<br/>1. Merge 💼 Sales, 📣 SEO and 💬 Social into one 📈 Growth seat: all three quiet for 30 days<br/>2. Add a 📱 Mobile engineer: a mobile app appeared since setup
    RE-->>You: "Decision needed: apply both changes?"
    You->>RE: "apply all"
    RE->>Tools: scaffold the proposed plan, with your answer
    Tools->>Repo: seat 📈 Growth and 📱 Mobile engineer<br/>retire Sales, SEO and Social (briefs kept, marked retired)
    Tools->>Repo: DECISIONS.md: DEC-5, the team change, with your words verbatim
    opt a seat the catalogue does not have
        RE->>Repo: write its rulebook for its role before it works
    end
    RE->>Tools: save a fresh scan as the new baseline
    RE->>Inbox: one line each to 📈 Growth, 📱 Mobile, ⚙️ Engineering and 🛎️ Chief of Staff:<br/>what moved, and where its brief is
    RE-->>You: "Close the Sales, SEO and Social sessions if they are open.<br/>Open /seat-growth and /seat-mobile in new sessions when their work comes up.<br/>You still talk to the Chief of Staff."
```

**Asks you:** once, after the report. Your answer is one decision row (DEC-5 here, after the two of
scenario 2). Had you said *apply some* or *change nothing*, every proposal you turned down would be
written to `docs/team/declined.json` and not put to you again unless the repo changes in a way that
calls for it. A retired seat keeps its brief, so its history stays readable, and it is not proposed
again unless its signal is new since setup. A merged seat whose work grows to carry the team is
proposed for splitting back into its roles the same way.
