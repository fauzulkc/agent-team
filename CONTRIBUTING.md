# Contributing

- **A rulebook change** goes in `skills/team-setup/seats/seat-<role>/SKILL.md`. Keep the seven
  sections, the mark, tier names (never model names), and no project-specific facts. Every rule
  carries its reason.
- **A new seat:** write its rulebook to `skills/team-setup/references/seat-contract.md` (the
  skeleton, what each section holds, the hard rules), add its row to
  `skills/team-setup/references/seats.md`, and add it to `docs/seats.md`. If the scan should propose
  it, raise it from a signal in `scripts/scan.py` and `plan.py`'s `needs()`.
- **A new merge group or derived role** goes in `skills/team-setup/scripts/teamlib.py` (`MERGES`,
  `DERIVED_ROLES`). A check seat (Bar Raiser, Scope Trimmer, User, Security) never merges into a
  seat whose work it checks.
- **A shared-protocol change** goes in `skills/team-setup/templates/TEAM.md`; existing projects
  pick it up by hand (diff their `docs/TEAM.md` against the template).
- **Before a pull request:** `python3 check.py`, `python3 -m unittest discover -s tests` and
  `claude plugin validate .` all pass, and `CHANGELOG.md` has a line. Bump `version` in
  `.claude-plugin/plugin.json` for a release: installs stay on the version they have until it changes.
