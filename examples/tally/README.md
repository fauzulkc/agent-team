# Example: Tally, a seated project

**Tally** is an invented invoicing app for freelancers. This folder shows what a project carries
after `team-setup` seated a team and the team worked for a couple of days.

**The team here is eight seats the owner named** (`scaffold.py --seats`, the path for an owner who
picks the seats by name instead of from the three options), kept small so each file stays short to
read. The [walkthrough](../walkthrough.md) seats the larger recommended team of nineteen on the same
app; the files a project carries, and how a working team fills them, are the same either way. The
decisions are numbered as the walkthrough's: setup records the team as **DEC-2** (DEC-1, the team
method, comes with the template), so recurring invoices is **DEC-3** and turning them on is **DEC-4**.

| File | What to look at |
|---|---|
| `docs/TEAM.md` | the shared rulebook with Tally's roster |
| `docs/DECISIONS.md` | the team method (DEC-1), the team as the owner named it, in their words (DEC-2), a two-way door the CEO took (DEC-3), and one only the owner could take (DEC-4) |
| `docs/team/engineering.md` | a filled seat brief: paths, commands, decisions that bind it, traps, done-when |
| `docs/team/tracker.md` | the Chief of Staff's tracker with stop lines |
| `docs/team/owner-questions.md` | one open question and one answered, in the owner's words |
| `docs/team/seat-skills.lock` | where each seat's rulebook came from, its hash and the date it was seated |
| `.claude/agents/` | the generated workers: one per seat, plus the six shared tiers |
| `scratchpad/team/` | an inbox line left for an away seat, the worker's run log, a shared context pack (in a real project this folder is never committed) |

**Generated, and written by hand.** `docs/TEAM.md`, `CLAUDE.md`, the lock, the workers, the briefs
other than Engineering's, and the decision register up to DEC-2 are exactly what `scaffold.py` writes
today (dated with the story's date); `python3 tools/build_tally_example.py` rebuilds them, and
`python3 check.py` fails when they fall behind. The Engineering brief, the tracker, the owner
questions, the decisions after DEC-2 and the scratchpad are written by hand, the way a working team
fills them.

Not included: `.claude/skills/seat-*` (the rulebooks setup copies in; they live in
`skills/team-setup/seats/` in this repo) and the copied generator script.
