# Contributing

- **A rulebook change** goes in `skills/team-setup/seats/seat-<role>/SKILL.md`. Keep the seven
  sections, the mark, tier names (never model names), and no project-specific facts. Every rule
  carries its reason.
- **A shared-protocol change** goes in `skills/team-setup/templates/TEAM.md`; existing projects
  pick it up by hand (diff their `docs/TEAM.md` against the template).
- **A new seat:** add a row to `skills/team-setup/references/seats.md`, write its rulebook, and run the checks.
- **Before a pull request:** `python3 check.py` and `claude plugin validate .` both pass, and
  `CHANGELOG.md` has a line. Bump `version` in `.claude-plugin/plugin.json` for a release: installs
  stay on the version they have until it changes.
