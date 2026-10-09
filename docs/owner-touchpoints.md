# When the team asks you, and when it doesn't

The team is built so that **you decide what only you can decide, and nothing else.** Everything
reversible happens without you; everything that leaves the building, costs money, binds you legally
or can't be undone waits for your word. The same rules are written into every seated project's
`docs/TEAM.md` §7, so every seat follows them.

## You will be asked

| When | Typical question | Who asks |
|---|---|---|
| **Setting up the team**: one question that holds the team option and the two settings | "Which team: recommended (19 seats), lean (10) or full (22)? Each seat has its reason; add, drop, merge or split any. What do only you do? When finished work is ready, should the team upload it to the shared code on its own once checks pass, or ask you each time? (Recommended: ask me each time.)" | `team-setup`, once |
| **Re-evaluating the team**, when you ask for it: every proposal in one question | "Merge Sales, SEO and Social into one Growth seat (all three quiet for 30 days) and add a Mobile engineer (a mobile app appeared)? Apply all, some, or none?" | `team-reevaluate`, once per re-evaluation |
| **Anything outward**: publishing, posting, emailing customers, inviting users, press, a public claim's first release | "Approve this post, word for word, for Thursday?" | Chief of Staff, relaying Sales or Social |
| **Any spend**: a subscription, a paid API beyond the agreed budget, a purchase, a paid tier | "Turn on the paid search API at about $20 a month?" | the seat that needs it, via the Chief of Staff |
| **Prices**, discounts, trials, free tiers | "Price the Pro plan at the level in the pricing case?" | Sales, through the CEO |
| **Legal and identity**: sign-ups, contracts, terms, incorporation, identity checks | "Sign up to the payment provider with these details?" | Payments, via the Chief of Staff |
| **Irreversible acts**: deleting data, a migration with no rollback, rewriting git history, revoking access | "Delete the 2023 test accounts? There is no undo." | the seat proposing it |
| **Secrets**: a credential only you hold | "Set the email service's key under the name `MAIL_API_KEY`." (you set it; the value is never pasted into chat) | Platform |
| **A real fork in direction**: two good paths, and the evidence cuts against a preference you stated | "Ship recurring invoices before the mobile app, against your earlier note? Here is why." | CEO |
| **New scope**: a new goal, a milestone beyond the active one | "Open the reporting milestone next?" | CEO or Product |
| **Taste you reserved**: anything you asked to see before it ships (a brand mark, a launch video) | "Here is the cut; ship it?" | Design or Motion |
| **Uploading finished work to the shared code**, if you chose to be asked each time | "Upload the five finished changes to the shared code?" | CEO |

## You will not be asked

| The team decides, and tells you in the next report | Why it is safe |
|---|---|
| How to build something already in scope: code, refactors, tests, internal docs, drafts | reversible; reviewed by another seat before it counts |
| Which worker, which model tier, how many workers | an internal cost and speed choice, governed by the tier ladder |
| Routing work between seats, calling an away seat's team | every hand-off is logged in that seat's inbox |
| Experiments, probes and audits that cost nothing | free and reversible |
| Fixing a mistake in the team's own docs | fixed in place, with the record appended |
| Commits (by the shared-tree rules), and deploys if you gave standing permission | commits are reversible; deploys follow your setup choice |
| Ordering work inside the active milestone | the CEO's job, inside the scope you set |
| Recording a decision you already made | your words are quoted verbatim, never re-asked |
| Reviews, re-measurements, checks | they only make claims safer |
| Each new, merged or split seat on its own, or how its rulebook is written | seats come to you only inside setup's or a re-evaluation's one question, or when you name one yourself (*"add Motion to the team"*: you named it, so your words are the decision); a seat that sees the need for one notes it in `docs/team/owner-questions.md` for the next re-evaluation; a merged rulebook keeps every member's rules, and a new seat's is written to the seat contract and has no worker until it is |
| Measuring how the team works (the re-evaluation report itself) | read-only; nothing changes until you answer |
| Resetting the scan baseline after a team change you approved | bookkeeping that keeps a settled signal from being raised again |

## How the asking works

1. **One channel.** Questions collect in `docs/team/owner-questions.md`. The Chief of Staff (or the
   CEO, if no Chief of Staff is seated) brings them to you, batched, not one interruption per seat.
   That is also whom you talk to: after setup or a re-evaluation you are told to open the CEO and the
   Chief of Staff (the CEO alone when there is no Chief of Staff), and other seats only when their
   work comes up; the seats you don't open are covered by their teams.
2. **One shape.** *Decision needed* (a plain question, its options, a recommendation) → a few summary
   bullets → one section per objective → detail only if you ask. No register codes, no jargon, no
   time estimates.
3. **Asked once.** Before asking, seats search earlier answers. Your answer is recorded word for
   word, with where you gave it, and every seat it touches is told. Nobody asks again.
4. **Never assumed.** A seat words an open ask as a question ("for the owner: approve X?"), never
   as a fact, so no other seat mistakes it for an approval.
5. **Team changes come batched too.** Setup asks once, with the option and the settings together.
   A re-evaluation asks once, with every proposal and its evidence, and *apply all, some, or none*.
   "Change nothing" is a complete answer: the team runs as it is, and your answer is recorded as one
   decision that lists what you declined. **What you decline is remembered** (`docs/team/declined.json`):
   it is not proposed again unless one of the repo signals it rests on is new since the last baseline.
   The option you picked at setup counts too: a re-evaluation compares against it, so seats the lean
   option left out are not offered back as new. A retired seat is not proposed again unless the repo
   changes in a way that calls for it.
6. **A pause means stop talking, not stop working.** If you say pause, seats stop messaging each
   other and editing shared files; renders, tests and scripts already running keep going.

## Changing the line

The defaults above live in your project's `docs/TEAM.md` (§7 lists what only you do and when you are
asked; §6 holds the rule for uploading finished work, kept there as the push rule). Change them there, or record a decision in `docs/DECISIONS.md` (for example: *"Platform may
deploy without asking once the tests are green and a reviewer has passed the change"*). A decision
outranks every rulebook. Your answers at setup and at each re-evaluation are recorded there too, word
for word, so the team's shape always traces back to what you said.
