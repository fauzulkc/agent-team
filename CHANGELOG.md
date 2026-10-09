# Changelog

## 1.3.0
- **Dynamic seats.** `team-setup` scans the repo (`scan.py`: signals with the evidence that raised
  each, and a size class: tiny, small, medium, large) and offers three teams, lean, recommended and
  full, every seat with its reason (`plan.py`). The owner picks one in setup's single question and
  may edit it.
- **Merged seats**: eight groups one session can hold while the work is small (Growth, Product &
  Design, Engineering & Platform, Quality, Money, Legal & Compliance, Data & ML, Customer), composed
  from their members' rulebooks with every rule kept and recomposed on sync. A check seat joins only
  a check merge (Quality), and no merge proposed after setup holds the CEO or the Bar Raiser.
- **New seats**: roles no catalogue seat covers (hardware and firmware, smart contracts, desktop,
  browser extension) and one frontend seat per UI app are derived from a base rulebook and written
  for their role per `references/seat-contract.md` before they work (`seatgen.py`).
- **Eight new catalogue seats**, 29 in all: Mobile engineer, ML engineer, Data engineer, Security,
  Docs writer, Community & DevRel, Game designer, Localization.
- **`team-reevaluate`**, a new skill (`reevaluate.py`): measures each seat's commits, worker runs,
  inbox and blocked lines, re-scans the repo against the setup baseline, and proposes adding,
  retiring, merging, unmerging or splitting seats with the evidence for each; a retired seat is not
  proposed again without a new signal. Nothing changes without the owner's one answer.
- **`scaffold.py`** applies a plan (`--plan`), records the owner's words as a decision (`--record`),
  retires seats with their briefs kept (`--retire`), and records each rulebook's origin in
  `docs/team/seat-skills.lock`. **`gen-team-agents.py --check`** fails while any seated rulebook
  still carries `AUTHORING NEEDED`.
- **Tests**: `python3 -m unittest discover -s tests` runs the scan, planner, scaffold and
  re-evaluation end to end on invented fixture projects.
- Docs: how the team is sized and re-evaluated, the catalogue with merged seats and new roles, the
  walkthrough's three options and its month-later re-evaluation, and when the owner is asked.

### Fixed in review, before release
- **The lock records where each rulebook came from and when.** Every entry in
  `docs/team/seat-skills.lock` carries its origin (`catalogue`, `merge:…`, `derive:…`, or `project`
  for a rulebook the project already had) and the date its seat was seated. A project's own rulebook
  is never synced, overwritten or deleted. Old bare-hash entries still read, as catalogue copies.
- **Every team change is one decision, in the owner's words.** Setup records the team as DEC-2;
  `--record` works with `--plan`, `--add`, `--retire` and `--seats`, and `--question` names what was
  asked. The row says what changed in seat names (seated, retired, merged, split) and what was
  declined. A run that changes nothing records nothing.
- **Declines are remembered.** `scaffold.py --only KEY,...` (or `--only none`) applies the proposals
  the owner approved; every other one goes to `docs/team/declined.json` and is not proposed again
  unless a repo signal it rests on is new since the baseline.
- **A role is never held twice, and the CEO and the Bar Raiser always are.** Adding a role a merged
  seat holds is refused unless the same change splits that seat; a new seat's mark must be free; a
  retire that would leave the CEO or the Bar Raiser held by no seat is refused, in plain words.
- **No worker before a new seat's rulebook is written.** The generator writes none for a rulebook
  still marked `AUTHORING NEEDED` and removes an old one; a derived rulebook now points at its own
  brief, inbox, run logs and worker, not its base's.
- **Retiring archives, never deletes,** a rulebook that is derived, the project's own, untracked or
  edited, to `docs/team/retired/<skill>-<date>`. Re-adding a seat removes its "Retired" line, and a
  derived seat comes back from its archived copy.
- **Re-evaluation measures against what was chosen.** It compares with the option picked at setup;
  holds back seats seated inside the window; never merges the CEO or the Bar Raiser, nor Engineering
  & Platform past 2,000 source files; lets each merge claim its members; keeps new roles, per-app
  frontend seats and the coordination seats while they are called for; treats a missing baseline as
  nothing new. Each proposal has a key and a title in seat names, and the plan carries the project's
  name.
- **The planner's rules are shared and stated once.** The Chief of Staff joins at five other seats
  (seven in lean), the Scope Trimmer at ten; split seats never reuse a catalogue mark, and past four
  UI apps the Frontend engineer holds the rest; `plan.py --markdown` prints the owner-ready question.
- **The scan reads what it should.** The team's own files never move a signal; Python dependencies
  come from dependency tables only; a mobile app needs Android or iOS evidence; a monorepo needs
  manifests in two folders or a workspace config.
- **Sync walks the roster**, never touches a derived or project-own rulebook, and says what it
  compared. Line endings of the team's files are kept as found.
- **`check.py` checks more:** every rulebook is 130 to 200 lines, its description at most 700
  characters, every section-2 shift carries its source, marks match the catalogue for short names
  too (`🌱 Community`), and the generated docs are current.
- **Docs that cannot drift.** `docs/seats.md` is generated by `tools/gen_seats_md.py` (29 rows, the
  merged seats, the new roles, and starter shapes measured on the test projects);
  `tools/build_tally_example.py` rebuilds the example's generated files, now numbered as the
  walkthrough (the team DEC-2, recurring invoices DEC-3, the switch DEC-4) and labelled as a team of
  eight the owner named; `tools/measure_tally.py --check` re-measures the walkthrough's figures.
- **Plainer for the owner.** Setup asks whether finished work is uploaded on its own or the owner is
  asked each time, instead of "who pushes", and ends by naming whom to open now (the CEO and the
  Chief of Staff). The Game design seat is renamed **Game designer**. `install.sh` links both skills.
- **A change the owner names is made, not re-asked.** "Add Sales", "retire Design": `team-reevaluate`
  measures, applies with the owner's words as the record, and asks only when the measurement argues
  against the request. A declined merge keeps its members, so "change nothing" is not asked again in
  another shape.
- **Tests and CI:** 94 tests, none marked as expected to fail; CI runs them on Python 3.9 and 3.12,
  walks the skills' commands in order on a fresh project, and re-measures the walkthrough's figures.
- **Upgrading a 1.2 project:** the project keeps its copy of `scripts/gen-team-agents.py`; copy the
  new one from `skills/team-setup/scripts/` to get the no-worker-before-authoring rule.

## 1.2.0
- Publishable docs: how it works and what it can handle, orchestration diagrams, when the owner
  is asked, the seat catalogue, a prompt-by-prompt walkthrough, and a seated example project (Tally).
- The shared rulebook template gains *When the owner is asked, and when not* (§7).
- Seat rulebooks made domain-neutral throughout.

## 1.1.0
- Installable as a Claude Code plugin with its own marketplace.
- Seat rulebooks travel inside `team-setup` and are copied into each project's `.claude/skills/`
  (workers cannot preload a skill that lives only in a plugin), with a hash lock and `--sync`.

## 1.0.0
- 21 seat rulebooks, `team-setup`, the scaffold, the worker generator, seven model tiers.
