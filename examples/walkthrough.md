# Walkthrough: seating a team on Tally

**Tally** is an invented invoicing app for freelancers (Node API, React web, Postgres). This is the
prompt-by-prompt story of seating a team on it and shipping one feature. What you type is in
**bold quotes**; what the team says back is condensed. The files it produced are in [tally/](tally/).

---

## 1. Install (once per machine)

```
/plugin install agent-team --marketplace <github-user>/agent-team
```

## 2. Seat the team (once per project)

Open Claude Code in the Tally repo:

> **"set up the team"**

`team-setup` reads the README, `package.json`, the CI workflow and the last thirty commits, then asks
once:

> *Decision needed: seat these seven roles for Tally?*
> *CEO (decision register) · Chief of Staff (three or more seats) · Product (paying users) ·
> Engineering (a code project) · Frontend (a React web app) · Testing (a CI suite exists) ·
> Bar Raiser (the independent check).*
> *Also: what only you do (default: publishing, sending, spending, signing), and who pushes (default: you).*

> **"yes, add Design, and emailing customers is mine too"**

It scaffolds `docs/TEAM.md`, `docs/DECISIONS.md`, eight seat briefs, the copied rulebooks, fourteen
workers and the scratch area, then fills each brief from what it measured (test commands, paths,
the dev server's health URL). It ends with:

> *Open the CEO first: `/seat-ceo catch up and work your inbox`. Then the Chief of Staff, who you'll
> talk to day to day.*

**Asked you: once.**

## 3. Open the seats you need today

Each in its own session, named after the seat:

```
/seat-ceo catch up and work your inbox
/seat-chief-of-staff catch up and work your inbox
/seat-engineering catch up and work your inbox
/seat-frontend catch up and work your inbox
```

Design, Product, Testing and Bar Raiser stay closed for now. Their teams cover them.

## 4. Ask for a feature, in one sentence

To the Chief of Staff:

> **"Freelancers keep asking for recurring invoices. Let's do it."**

What happens without you:

1. The Chief of Staff takes it to the CEO with the evidence (nine support emails).
2. The CEO judges it a reversible call inside your scope, records **DEC-2**, and tells the seats.
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

Your words are recorded verbatim as **DEC-3**
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

## 7. Grow the team when the work appears

> **"add Sales to the team"**: Tally is about to charge for a Pro plan.

> **"sync the team's rulebooks"**: after a plugin update, this refreshes every rulebook the project
> hasn't edited, and names any it kept.

A new model ships: edit `TIERS` in `scripts/gen-team-agents.py` and the table in `docs/TEAM.md` §2,
run `python3 scripts/gen-team-agents.py`, open a new session, and ask one worker which model it runs.

---

## What you were asked, in total

| Asked | Not asked |
|---|---|
| which seats, what only you do, who pushes (setup) | scope of recurring invoices |
| turn recurring invoices on for everyone | the design of the badge |
| the reminder email's words | how to build it, which workers, which models |
| | the review, the failure and the fix |
| | covering the four closed seats |
| | recording your answers |
