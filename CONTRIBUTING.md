# Contributing

- **A rulebook change** goes in `skills/team-setup/seats/seat-<role>/SKILL.md`. Keep the seven
  sections, the mark, tier names (never model names), and no project-specific facts. Every rule
  carries its reason. A changed description changes `docs/seats.md`: regenerate it (below).
- **A new seat:** write its rulebook to `skills/team-setup/references/seat-contract.md` (the
  skeleton, what each section holds, the hard rules), add its row to
  `skills/team-setup/references/seats.md`, then regenerate `docs/seats.md` with
  `python3 tools/gen_seats_md.py` (never edit that page by hand). If the scan should propose it,
  raise it from a signal in `scripts/scan.py` and `plan.py`'s `needs()` and `TEAM_SIGNALS`.
- **A new merge group or derived role** goes in `skills/team-setup/scripts/teamlib.py` (`MERGES`,
  `DERIVED_ROLES`); which merges may form is `plan.merge_allowed()`, shared by setup and
  re-evaluation. A check seat (Bar Raiser, Scope Trimmer, User, Security) joins only a check merge.
- **The generated docs.** `docs/seats.md` comes from `tools/gen_seats_md.py`, and the generated half
  of `examples/tally/` from `tools/build_tally_example.py`; `check.py` fails when either is stale and
  names the command to run. A planner change that breaks a sentence the seats page states fails the
  generator itself: fix the sentence in the generator. `python3 tools/measure_tally.py --check`
  re-measures every figure the walkthrough states (it builds a 661-file project, so it is not part
  of `check.py`); run it after changing the scan, the planner, the scaffold or the re-evaluation.
- **A shared-protocol change** goes in `skills/team-setup/templates/TEAM.md`; existing projects
  pick it up by hand (diff their `docs/TEAM.md` against the template).
- **Before a pull request:** `python3 check.py`, `python3 -m unittest discover -s tests` and
  `claude plugin validate .` all pass (and `python3 tools/measure_tally.py --check` when the scripts
  changed), and `CHANGELOG.md` has a line. Bump `version` in
  `.claude-plugin/plugin.json` for a release: installs stay on the version they have until it changes.
