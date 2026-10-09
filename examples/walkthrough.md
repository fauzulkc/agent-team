# Walkthrough: seating a team on Tally

**Tally** is an invented invoicing app for freelancers: a React web app with a pricing page and
product analytics, a Node API on Express, Postgres, card payments, sign-ups, an email service and a
blog. This is the prompt-by-prompt story of seating a team on it, shipping one feature, and resizing
the team a month later. What you type is in **bold quotes**; what the team says back is condensed.
Every count and every proposal below was measured by running the scripts on a project built to this
description (`python3 tools/measure_tally.py`). The files a seated project carries are in
[tally/](tally/), with a smaller team of eight seats the owner named.

---

## 1. Install (once per machine)

```
/plugin install agent-team --marketplace fauzulkc/agent-team
```

## 2. Seat the team (once per project)

Open Claude Code in the Tally repo:

> **"set up the team"**

`team-setup` reads the README, the CI workflow and the last thirty commits, then scans the repo. The
scan finds, each with its evidence: React in the dependencies, an API framework (Express), a payment
library, a sign-in library, an email service, product analytics, a pricing page, a `blog/` folder, a
Dockerfile and a hosting config, a test suite run by CI, and email columns in the database schema.
It sizes Tally as **medium** (661 source files, four contributors) and saves the scan as the
baseline for later. Then it asks once:

> *Decision needed: which team for Tally?*

| Option | Seats | What it is |
|---|---|---|
| **Recommended** | 19 | every role the evidence calls for, each in its own seat: Tally is past the size where one session should hold several roles |
| Lean | 10 | the fewest sessions, sixteen roles in ten: Sales, SEO and Social share one **Growth** seat; Product with Design; Engineering with Platform; Testing with the Bar Raiser as **Quality**; Payments with Compliance as **Legal & Compliance**; no User, Research or Scope Trimmer seat |
| Full | 22 | the recommended team plus Competition & Market, Funding, and a Docs writer for the API |

> *The recommended seats, and why each:*

| | Seat | Why |
|---|---|---|
| 🧭 | CEO | every team keeps one decision register |
| 🛎️ | Chief of Staff | seventeen other seats: one seat talks to you and keeps the tracker |
| 🎯 | Product | people pay for it (a payment library is in the dependencies) |
| ⚙️ | Engineering | 661 source files |
| 🖥️ | Frontend engineer | a React web app |
| 🧪 | Testing | a test suite that CI runs |
| 🛰️ | Platform | a Dockerfile and a hosting config: it is deployed |
| 🔬 | Research | product analytics: claims will rest on measurement |
| ⚖️ | Bar Raiser | every team keeps one independent check |
| ✂️ | Scope Trimmer | seventeen other seats: someone cuts the queue to the shortest path to a customer |
| 📐 | Design | a React web app: people look at it |
| 💼 | Sales & Marketing | a payment library: it will be sold |
| 📣 | SEO & Publicity | a pricing page: people must find it |
| 💬 | Social Media Manager | a blog to publish and share |
| 🤝 | Customer Success | a sign-in library: people join and need to reach their first invoice |
| 💳 | Payments & Company Legal | a payment library: it takes money |
| 🗂️ | Compliance & Audit | customers' email addresses in the database |
| 👤 | User | people sign up and pay: someone walks it as a customer would |
| 🔐 | Security | sign-in plus payments and personal data: someone checks what an attacker could reach |

> *A merged seat is one session holding several roles, every rule of each kept; it splits back when
> its work grows. Any option can be edited: add, drop, merge or split a seat.*
> *Also: what only you do (default: publishing, sending, spending, signing). And when finished work
> is ready, should the team upload it to the shared code on its own once checks pass, or ask you
> each time? (Recommended: ask me each time.) Seats are opened in new sessions once setup is done.*

> **"recommended, and emailing customers is mine too"**

It writes the plan, then scaffolds `docs/TEAM.md`, `docs/DECISIONS.md` with your answer word for
word as **DEC-2** (DEC-1, the team method, comes with the register), nineteen seat briefs, the
nineteen rulebooks copied from the catalogue, twenty-five workers (one per seat plus the six shared
tiers) and the scratch area. Your answer left the upload question alone, so the team asks you before
each upload. It fills each brief from what it measured (test commands, paths, the dev server's
health URL). No seat here is new to the catalogue, so no rulebook needs writing; all of it happened
in this one session. It ends with:

> *Open the CEO and the Chief of Staff now, each in a new session. Talk to the Chief of Staff day to
> day. Open other seats when their work comes up; the ones you don't open are covered by their
> teams. Say "re-evaluate the team" whenever a milestone closes.*

**Asked you: once.**

## 3. Open the CEO and the Chief of Staff

Each in its own new session, named after the seat:

```
/seat-ceo catch up and work your inbox
/seat-chief-of-staff catch up and work your inbox
```

When the work below starts, Engineering and Frontend are worth opening too
(`/seat-engineering catch up and work your inbox`, the same for `/seat-frontend`): four open is a
typical day. The other fifteen stay closed. Their teams cover them.

## 4. Ask for a feature, in one sentence

To the Chief of Staff:

> **"Freelancers keep asking for recurring invoices. Let's do it."**

What happens without you:

1. The Chief of Staff takes it to the CEO with the evidence (nine support emails).
2. The CEO judges it a reversible call inside your scope, records **DEC-3** (DEC-2 is the team
   itself), and tells the seats.
3. Product is closed, so the CEO calls the Product team (`product-worker`). It writes the scope
   note *"monthly and weekly only, no proration"*, and leaves a line in Product's inbox.
4. Engineering writes a contract for its own team: schema and scheduler, the tests to paste, the
   paths it may touch. The worker returns ten lines, with its full log in a run file.
5. Frontend needs a design ruling. Design is closed, so Frontend calls the Design team. It finds an
   existing pattern covers the badge, writes no new ruling, and leaves an inbox line
   ([tally/scratchpad/team/inbox/design.md](tally/scratchpad/team/inbox/design.md)).
6. Frontend builds, runs the whole web test leg, screenshots both widths, and sends it to Bar Raiser.
7. Bar Raiser is closed too, so Engineering calls `bar-raiser-worker`. It re-measures on the running
   app, tries an invoice due on the 31st, and gets a crash in February: **FAIL**, with a guard test.
8. Frontend fixes it; the guard fails before the fix and passes after; the review passes.
9. Engineering lands the change behind a switch and sends the Chief of Staff a stop line.

## 5. The one question you get

> *Decision needed: recurring invoices are built and behind a switch. Turn them on for everyone?*
> *Summary: monthly and weekly; tests green; the 31st-of-month crash found in review and fixed.*

> **"turn it on"**

Your words are recorded verbatim as **DEC-4**
([tally/docs/DECISIONS.md](tally/docs/DECISIONS.md)), and every seat they touch is told.

**Asked you: once, because turning a feature on for customers is outward.**

## 6. The next day

> **"catch me up"**

> *Decision needed: approve this reminder email, word for word, for invoices three days overdue?*
> *"Hi {name}, a quick nudge: invoice {number} for {amount} was due on {date}…"*
>
> *Summary: recurring invoices are live; the invoice list is being made faster (it measured 1.8 s
> at 500 invoices, aiming under 1 s).*

Emailing customers is yours, so the email waits for you. Making the list faster doesn't.

## 7. A month later: re-evaluate

Tally has started a mobile app in `apps/mobile/`, and the blog launch has slipped. After the
milestone closes:

> **"re-evaluate the team"**

`team-reevaluate` counts each seat's commits, worker runs, inbox lines and blocked lines over the
last 30 days, and re-scans the repo against the baseline saved at setup. Condensed:

| Seat | Commits | Worker runs |
|---|---|---|
| ⚙️ Engineering, 🖥️ Frontend, ⚖️ Bar Raiser and thirteen more | active | active |
| 💼 Sales & Marketing | 1 | 0 |
| 📣 SEO & Publicity | 1 | 0 |
| 💬 Social Media Manager | 0 | 0 |

*New in the repo since setup: a mobile app (a mobile app framework in `apps/mobile/`'s dependencies).*

The session reads the numbers before you do: nothing in the tracker or the active milestone holds
work for the three quiet seats, and their commits are prefixed, so the counts are real. Then:

> *Decision needed: apply these two changes to the team?*
> *1. Merge Sales, SEO and Social into one Growth seat. All three were quiet for 30 days (one
> commit each from Sales and SEO, nothing from Social, no worker runs). The blog still needs
> Social's work, so it is merged rather than retired.*
> *2. Add a Mobile engineer: a mobile app appeared since setup (it uses Expo).*
> *For you: close the Sales, SEO and Social sessions if they are open; open Growth and Mobile
> engineer when their work comes up. You still talk to the Chief of Staff.*
> *Apply all (recommended), apply some, or change nothing? Anything you turn down is remembered and
> not asked again unless the repo changes in a way that calls for it.*

> **"apply all"**

What happens without you:

1. The plan is applied: **📈 Growth** is seated with a rulebook composed from Sales's, SEO's and
   Social's (every rule of each kept) and a brief that carries all three briefs; **📱 Mobile engineer**
   is copied from the catalogue.
2. Sales, SEO and Social are retired: their briefs stay, under a "Retired" line, and their workers
   are removed. Their rulebooks were unedited catalogue copies, so they are removed too (Growth's
   holds every rule of each); an edited one would have been archived to `docs/team/retired/`.
   Their unread inbox lines move to Growth.
3. Your words go into `docs/DECISIONS.md` verbatim as **DEC-5**: *seated 📱 Mobile engineer; merged
   💼 Sales & Marketing, 📣 SEO & Publicity, 💬 Social Media Manager into 📈 Growth*. Had you answered
   *"just the mobile engineer"*, the merge would be listed there as declined and kept in
   `docs/team/declined.json`, and the next re-evaluation would not raise it again on the same evidence.
4. The scan baseline resets to today, so the mobile app is not raised again.
5. The generator's check runs green; Growth, Mobile, Engineering and the Chief of Staff each get an
   inbox line saying what moved and where the brief is.

Had the scan found a role the catalogue does not hold (firmware for a card reader, say), the new
seat's rulebook would be written for its role before it worked, and it would have been one more
line in the same question, not a question of its own.

**Asked you: once.**

## 8. Keep it current

> **"add Motion to the team"**: when a launch video is planned. You named it, so there is no question;
> your words are recorded as the decision. Had you said *"add Sales to the team"* after the merge, the
> Growth seat would be split back into Sales, SEO and Social, and you would be told.

> **"sync the team's rulebooks"**: after a plugin update, this refreshes every rulebook the project
> hasn't edited, recomposes Growth from its members' new rulebooks, and names any it kept.

A new model ships: edit `TIERS` in `scripts/gen-team-agents.py` and the table in `docs/TEAM.md` §2,
run `python3 scripts/gen-team-agents.py`, open a new session, and ask one worker which model it runs.

---

## What you were asked, in total

| Asked | Not asked |
|---|---|
| which team (recommended), what only you do, whether finished work is uploaded on its own (setup) | the nineteen seats, one by one |
| turn recurring invoices on for everyone | scope of recurring invoices |
| the reminder email's words | the design of the badge |
| the re-evaluation's two changes, together | how to build it, which workers, which models |
| | the review, the failure and the fix |
| | covering the closed seats |
| | how Growth's rulebook was composed, or the scan baseline reset |
| | recording your answers |
