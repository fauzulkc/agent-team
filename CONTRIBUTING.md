# Contributing to agent-team

Thanks for helping. agent-team is a Claude Code plugin: two skills, `team-setup` and
`team-reevaluate`, a catalogue of 29 seat rulebooks, and the standard-library Python scripts that
scan a repository, plan a team, write it in and re-evaluate it. Fixes, tests, docs, rulebook
improvements and new seats are all welcome.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md). Security problems go through
[SECURITY.md](SECURITY.md), never a public issue. Questions go to
[Discussions](https://github.com/fauzulkc/agent-team/discussions); see [SUPPORT.md](SUPPORT.md).

## Before you start

- **Small fixes** (a bug, a typo, a missing test): open a pull request directly.
- **Anything larger**: open an issue first so the work is agreed before you build it. That covers
  a new seat (use the **Seat proposal** form), a change to the seat contract or the shared protocol,
  the scan's signals, the planner's thresholds, the merge groups, and anything a seated project
  relies on. [GOVERNANCE.md](GOVERNANCE.md) says how these are decided.
- **Looking for a first task?** Issues labelled
  [`good first issue`](https://github.com/fauzulkc/agent-team/labels/good%20first%20issue) are small
  and described well enough to do without knowing the whole codebase;
  [`help wanted`](https://github.com/fauzulkc/agent-team/labels/help%20wanted) marks accepted work
  open for anyone to pick up. Say on the issue that you're taking it, so two people don't build the
  same thing.

## What lives where

| Path | Holds |
|---|---|
| `skills/team-setup/SKILL.md` | the setup skill: read, scan, plan, ask once, write the team in |
| `skills/team-reevaluate/SKILL.md` | the re-evaluation skill: measure, propose, apply the owner's answer |
| `skills/team-setup/seats/seat-<team>/SKILL.md` | the 29 seat rulebooks |
| `skills/team-setup/references/` | `seats.md` (the catalogue), `seat-contract.md` (how a rulebook is written), `role-research.md` (sources) |
| `skills/team-setup/scripts/` | `scan.py`, `plan.py`, `scaffold.py`, `seatgen.py`, `reevaluate.py`, `teamlib.py`, and `gen-team-agents.py`, which is copied into each seated project |
| `skills/team-setup/templates/` | the files a seated project starts from: `TEAM.md` (the shared protocol), `DECISIONS.md`, the seat brief, the tracker, the owner questions |
| `tests/` | unit and end-to-end tests on invented fixture projects (`repo_fixtures.py` builds them) |
| `tools/` | the generators for the generated files, `measure_tally.py`, and the maintainer's release tools |
| `docs/`, `examples/` | the user docs, the walkthrough and the example project, Tally |
| `check.py` | the repository's shape check |

## Development setup

You need **Python 3.9 or later** and **git**. There is nothing to install: the scripts, tests and
tools use the standard library only, and must keep doing so. Fork the repository on GitHub, then:

```bash
git clone https://github.com/<you>/agent-team
cd agent-team
python3 check.py
```

To try your working copy in Claude Code, add the clone as a local marketplace and install from it:

```bash
cd ..   # from the folder that holds the clone
claude plugin marketplace add ./agent-team
claude plugin install agent-team@agent-team
```

Without the plugin system, `./install.sh` links both skills from your clone into
`~/.agents/skills/` and `~/.claude/skills/`. Open a new session after either, then say
*"set up the team"* in a throwaway project.

**Python 3.9 is the floor, and CI runs it.** No `match` statements, no `tomllib`, and no `X | Y`
unions outside annotations (the scripts use `from __future__ import annotations`).

## The checks

Run these before every pull request. CI runs the first three on Python 3.9 and 3.12, plus a walk
through the skills' commands in order on a fresh project.

| Command | What it proves |
|---|---|
| `python3 check.py` | every rulebook has its mark, the seven sections in order, 130 to 200 lines, a description of at most 700 characters, a source for every section-2 shift, the catalogue's marks, no model names and no project words; the top-level skills are in shape; every generated file matches what its generator writes today; the version is the same in `plugin.json`, `marketplace.json`, `CITATION.cff` and the newest `CHANGELOG.md` heading, under `## Unreleased` |
| `python3 -m unittest discover -s tests` | the scan, planner, scaffold and re-evaluation behave on invented fixture projects, end to end |
| `python3 tools/measure_tally.py --check` | every figure in `examples/walkthrough.md` still matches what the scripts give a Tally-shaped project; it builds a 661-file project, so it sits outside `check.py`: run it whenever you change the scan, the planner, the scaffold or the re-evaluation |
| `claude plugin validate .` | the plugin manifest is valid (needs Claude Code installed) |

`check.py` prints `note: no private leak-word list found; only generic checks ran` on your machine.
That is expected: see [Project neutrality](#project-neutrality).

## Generated files

These files are written by tools, never by hand. `check.py` fails when one is stale and prints the
command that fixes it.

| File | Generator | Regenerate after changing |
|---|---|---|
| `docs/seats.md` | `python3 tools/gen_seats_md.py` | the catalogue, a rulebook's description, `MERGES` or `DERIVED_ROLES`, the planner |
| the generated files of `examples/tally/` | `python3 tools/build_tally_example.py` | `scaffold.py`, the templates, `gen-team-agents.py`, or the rulebook of one of the example's eight seats (their hashes are in its `seat-skills.lock`) |
| `docs/facts.json` | `python3 tools/export_facts.py` | the catalogue, a rulebook's or a skill's description, `MERGES`, `DERIVED_ROLES`, the tier table in `gen-team-agents.py`, `.claude-plugin/plugin.json` or `marketplace.json` |

Each takes `--check`, which exits 1 without writing. `build_tally_example.py`'s docstring lists which
example files it owns; the rest of the example (its README, the engineering brief, the tracker, the
owner questions, the decision rows after the team's own, the scratchpad notes) is written by hand.

If a planner change breaks a sentence `docs/seats.md` states, `gen_seats_md.py` itself fails: fix the
sentence in the generator, not the page. A figure on a hand-written page (the README,
`docs/how-it-works.md`) has no generator: when you move a number the scripts produce, search the docs
for the old one and fix every place it appears.

## Changing a seat rulebook

A rulebook is `skills/team-setup/seats/seat-<team>/SKILL.md`, written to
[the seat contract](skills/team-setup/references/seat-contract.md).

- **Keep the shape:** the mark on the description and the H1, the seven `## n · ` sections in order,
  tiers by name (`team-quick`, `team-build`, `<team>-worker`) and never a model's name.
- **Bold the rule, then give its reason.** Every rule carries its reason in one line.
- **No project facts.** Paths, register files and traps a particular project has paid for belong in
  that project's seat brief, `docs/team/<team>.md`.
- **Hand-offs agree on both sides.** If you change what a seat hands to a peer, change the peer's
  table in the same pull request.
- **A changed description changes generated files:** regenerate `docs/seats.md` and
  `docs/facts.json`.

## Adding a seat

1. **Open a seat proposal issue first** and wait for it to be accepted. It asks for the role, why no
   catalogue seat, merged seat or derived role covers it, the signal in a repository that should raise
   it, and a draft of its four hard rules.
2. **Write the rulebook** to `skills/team-setup/references/seat-contract.md` at
   `skills/team-setup/seats/seat-<team>/SKILL.md`, with `name: seat-<team>` equal to its folder.
   Research the role as the contract says, and tag every section-2 source `[read]` (you opened the
   page) or `[found]` (it surfaced in search). Cite and paraphrase sources; never paste a page's text.
3. **Add its catalogue row** to `skills/team-setup/references/seats.md`: mark, seat, skill, team,
   kind, default register, reports to, seat it when. The mark must be free: not used by another
   catalogue seat, a merged seat or a derived role. Add the new skill to `CONTRACT_SEATS` in
   `check.py` so its sources are held to the tagged rule.
4. **Stay inside `check.py`'s limits:** 130 to 200 lines, a description of at most 700 characters
   that opens with the mark, and every catalogue seat written with its catalogue mark.
5. **Raise it from evidence** if a repository can show the need: a signal in `scripts/scan.py`, the
   rule in `plan.py`'s `needs()`, its signal keys in `TEAM_SIGNALS`, and a test in `tests/` with a
   fixture that raises it and one that does not.
6. **Update the neighbours' hand-off tables**, regenerate the generated files, and update the seat
   count wherever the docs state it.

**A new merge group or derived role** goes in `skills/team-setup/scripts/teamlib.py` (`MERGES`,
`DERIVED_ROLES`). Which merges may form is decided in one place, `plan.merge_allowed()`, shared by
setup and re-evaluation. A check seat (Bar Raiser, Scope Trimmer, User, Security) joins only a check
merge.

**A shared-protocol change** goes in `skills/team-setup/templates/TEAM.md`. Seated projects pick it
up by hand (they diff their `docs/TEAM.md` against the template), so the CHANGELOG line says what
changed.

## Changing the scripts

- **Every behaviour change has a test** in `tests/` that fails without it. Fixture projects are
  invented and built in a temporary folder by `tests/repo_fixtures.py`; never commit a real project.
- **A script that writes into a user's project keeps its promises:** it never writes outside the
  project root, never overwrites, syncs or deletes a project's own rulebook, archives on retire any
  rulebook the catalogue can't restore, and keeps each file's line endings. Its header says what it
  writes.
- **Seated projects keep their own copy of `scripts/gen-team-agents.py`.** A change there reaches
  them only when they copy it again, so the CHANGELOG line says so.

## Commits

Write the subject as `<area>: <what changed>`, in plain words, for example
`docs: the install line names the repo` or `scan: a mobile app needs Android or iOS evidence`. The
area is the part you touched: `seat-<team>`, `scan`, `plan`, `scaffold`, `reevaluate`, `tools`,
`tests`, `docs`, `ci`. Use the body for why, when the subject can't carry it. One logical change per
commit.

Using Claude Code or another assistant to write a change is fine. The change is still yours: read
it, run the checks, and make sure it is yours to license.

## Pull requests

The pull request template asks you to confirm:

- [ ] `python3 check.py` passes
- [ ] `python3 -m unittest discover -s tests` passes
- [ ] `python3 tools/measure_tally.py --check` passes, if the scan, planner, scaffold or re-evaluation
      changed
- [ ] generated files regenerated with their tools, not edited by hand
- [ ] a line under `## Unreleased` in `CHANGELOG.md` saying what changed for a user (replacing
      `Nothing yet.` if it is the first)
- [ ] project-neutral: examples use Tally, and nothing identifies a real project, its people or its
      customers
- [ ] a new seat, or a change to what a seat owns: links its accepted seat proposal issue

Leave the version alone: the maintainer sets it at release with `tools/bump_version.py`, which also
moves the Unreleased notes under the new version. A pull request is merged after review once every
check is green.

## Project neutrality

The toolkit is shared by projects that have nothing to do with each other, so nothing in it may
belong to one of them.

- **Examples use Tally**, the invented invoicing app for freelancers in
  [examples/walkthrough.md](examples/walkthrough.md). Test fixtures are invented projects too.
- **Nothing identifies a project the toolkit was used in**: not its name, its people, its places,
  its customers or its vendors, in a rulebook, an example, a test or a doc. Naming the source of an
  idea in a rulebook (an author, a company's published method) is a citation, and welcome.
- **No project's register codes in a rulebook.** `check.py` rejects decision-style codes such as
  `DEC-1` in a rulebook; the example project uses them on purpose.
- **Maintainers run an extra private word check in CI**: a list of words from projects the toolkit
  has been used in, kept out of the repository. It cannot run on a pull request from a fork, so the
  maintainer runs it before merging; if it flags your change, the maintainer points you to the line.

## Licence

agent-team is released under the [MIT licence](LICENSE). Contributions are accepted under the same
licence, inbound equals outbound: by opening a pull request you agree that your contribution is
licensed under the MIT licence in `LICENSE`. There is no contributor licence agreement and no
sign-off line to add. Contribute only work you have the right to license: your own, or third-party
material under an MIT-compatible licence that you name in the pull request.
