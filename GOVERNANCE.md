# Governance

How agent-team is run: who decides, how, and how that changes as more people help.

## Roles

| Role | Who | What they do |
|---|---|---|
| **Maintainer** | [@fauzulkc](https://github.com/fauzulkc) | reviews and merges pull requests, triages issues, cuts releases, holds the repository settings, enforces the [Code of Conduct](CODE_OF_CONDUCT.md), and has the final say |
| **Contributor** | anyone who opens an issue, answers a discussion, reviews or sends a pull request | proposes and builds changes under [CONTRIBUTING.md](CONTRIBUTING.md) |

Today the project has one maintainer. The maintainers are the people listed in the table above and
in [.github/CODEOWNERS](.github/CODEOWNERS); both change together.

## How decisions are made

**In the open.** Decisions are made on the issue, pull request or discussion they concern, with the
reason written there. Two things are handled in private: a security report, which stays in its
private advisory until it is published (see [SECURITY.md](SECURITY.md)), and a conduct report, which
the [Code of Conduct](CODE_OF_CONDUCT.md) keeps private to protect the reporter.

**Small changes by review.** A fix, a wording change or a test that passes every check is merged
once the maintainer has reviewed it. No issue is needed first.

**Larger changes start as an issue.** Open an issue before building any of these, so the work is
agreed before it is done:

- a new seat (the **Seat proposal** form), or a change to what an existing seat owns (the **Feature request** form, area "A seat rulebook");
- a change to the seat contract (`skills/team-setup/references/seat-contract.md`), the shared
  protocol (`skills/team-setup/templates/TEAM.md`) or the limits `check.py` enforces;
- a change to how the team is sized or re-evaluated: the scan's signals, the planner's thresholds,
  the merge groups or the derived roles;
- anything a seated project relies on changing incompatibly, which is a major release.

The maintainer decides, writes the reason on the issue, and labels it. A decision can be reopened
with new evidence: a fixture project the change mishandles, a measurement, a rule that fails in use.

**Measured, not argued.** Where a question can be settled by running the scripts on an invented
project, that run decides it. The tests in `tests/` and `tools/measure_tally.py` exist for this.

## What does not change by vote

These hold for every change, because users trust the toolkit inside their own repositories on them:

- **The owner decides anything outward, any spend, anything legal or irreversible.** No change lets
  a seat or its workers publish, post, email people, spend, sign or push past the owner's push rule
  on its own.
- **A user's files are kept.** A project's own rulebooks are never overwritten, synced or deleted;
  retiring a seat never loses a rulebook the catalogue can't restore (a derived, edited, untracked
  or project-own one is archived); recorded decisions are appended to, never rewritten.
- **No role is held twice**, and the CEO and the Bar Raiser are always held.
- **The toolkit is project-neutral.** Nothing in it identifies a real project, its people or its
  customers; examples use the invented app Tally.
- **Standard library only.** The scripts run on Python 3.9 or later with nothing to install.

## How seat rulebooks are accepted

A seat is accepted when it is a role real projects need and the toolkit can hold it well:

1. **A seat proposal issue comes first.** It names the role, why no catalogue seat, merged seat or
   derived role already covers it, the signal in a repository that should raise it, and a draft of
   its four hard rules. The maintainer accepts, declines or asks for a narrower role on the issue.
2. **It is project-neutral.** It describes how the best operator of the role works at a fast,
   early-stage company. Facts about any one project belong in that project's seat brief, never in
   the rulebook.
3. **It meets the seat contract.** It follows
   [skills/team-setup/references/seat-contract.md](skills/team-setup/references/seat-contract.md):
   the seven sections in order, the mark on the description and the H1, sourced shifts, tiers by name
   and never a model's, 130 to 200 lines, a description of at most 700 characters. `check.py` passes.
4. **It fits the catalogue.** Its mark is free, its row is in
   `skills/team-setup/references/seats.md`, and its hand-off tables agree with the seats it hands
   work to and takes work from, updated in the same pull request.
5. **It is raised by evidence** where a repository can show the need: a signal in `scan.py` and
   `plan.py`, with a test in `tests/`. A seat with no repository signal states plainly when an owner
   should seat it by hand.

A new seat ships in a minor release. Changing the meaning of a rule seated projects rely on is a
major release.

## Releases

The maintainer cuts releases. `tools/bump_version.py X.Y.Z` moves the `## Unreleased` notes in
`CHANGELOG.md` under the new version, sets the version everywhere it is written
(`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CITATION.cff`) and regenerates
`docs/facts.json`; a `vX.Y.Z` tag on `main` runs every check again and publishes the GitHub Release
with that version's notes. Versions follow semantic versioning: an incompatible change
to a rule or a script behaviour a seated project relies on is a major, a new seat, flag or skill is a
minor, and fixes and wording are a patch.

## Becoming a maintainer

Maintainers are invited by the existing maintainers. The invitation follows sustained, careful work:
several merged pull requests, reviews of other people's changes, help with triage and with questions
in Discussions, and a working command of the seat contract and the rules above.

A new maintainer starts with triage access (labelling, closing and reopening issues), then write
access once their reviews have been reliable, and is added to the table above and to `CODEOWNERS` in
the same pull request.

Once there are two or more maintainers:

- a maintainer's own pull request is merged after another maintainer approves it;
- a release is cut by any maintainer, under the same steps;
- when maintainers disagree, the lead maintainer, [@fauzulkc](https://github.com/fauzulkc), decides
  and writes the reason on the issue.

A maintainer can step down at any time. Former maintainers are thanked by name in this file.

## Changing this document

By pull request, decided by the maintainers like any larger change.
