# Decisions: Tally

**The owner's decision register, kept by the 🧭 CEO.** A decision here outranks every seat's
rulebook and `docs/TEAM.md`. Seats propose; the CEO records; the owner decides what only the owner
may (anything outward, any spend, anything that cannot be undone).

**How a decision is kept.**
- One row per decision, numbered `DEC-n` in order; never renumber, never delete.
- The row carries the question, the evidence (commits, files), the decision, and the owner's words
  verbatim when the owner gave them.
- A later change is a dated line appended to the row, and the operative sentence is fixed in place.
- After recording, search the docs for every line that still reads "pending", "proposed" or
  "waiting on the owner" for this question, and close each one.
- Tell every seat the decision binds (`RULED` to its inbox, or `STANDING` to all seats).

| Decision | Question | Evidence | Decided |
|---|---|---|---|
| **DEC-1** | The team method: seats, workers, tiers and the shared rulebook | `docs/TEAM.md` | ✅ 2026-03-02: the team is seated as `docs/TEAM.md`'s roster lists, set up with `team-setup` |
| **DEC-2** | Which seats for Tally? | named by the owner | ✅ 2026-03-02: seated 🧭 CEO, 🛎️ Chief of Staff, 🎯 Product, ⚙️ Engineering, 🖥️ Frontend engineer, 🧪 Testing, ⚖️ Bar Raiser, 📐 Design. Declined: nothing. Owner's words: "the CEO, a Chief of Staff, Product, Engineering, Frontend, Testing, the Bar Raiser and Design; emailing customers is mine too" |
| **DEC-3** | Recurring invoices: this milestone or after the mobile app? | 9 support emails asking for it; 2 asking for a mobile app | ✅ 2026-03-03 (CEO, a two-way door inside the owner's scope): recurring invoices join the active milestone, **monthly and weekly only, no proration** (Product's scope note). Reopen if a paying customer asks for proration. |
| **DEC-4** | Turn recurring invoices on for every customer? | Built behind a switch; Bar Raiser PASS after the 31st-of-month fix (commit `abc123`) | ✅ 2026-03-05, the owner, verbatim: *"turn it on"* (given to the Chief of Staff; owner-questions #4). Engineering flips the switch; neither Customer Success nor Sales is seated, so Product drafts the in-app note and the owner approves its words. |

