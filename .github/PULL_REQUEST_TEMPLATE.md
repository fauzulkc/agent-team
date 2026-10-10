## What changed

<!-- In plain words, what a user or contributor will notice. -->

## Why

<!-- The problem it solves. Link the issue: "Closes #123". -->

## Checklist

- [ ] `python3 check.py` passes
- [ ] `python3 -m unittest discover -s tests` passes
- [ ] `python3 tools/measure_tally.py --check` passes, if the scan, planner, scaffold or re-evaluation changed
- [ ] Generated files regenerated with their tools, not edited by hand (`tools/gen_seats_md.py`, `tools/build_tally_example.py`, `tools/export_facts.py`)
- [ ] A line under `## Unreleased` in `CHANGELOG.md`
- [ ] Project-neutral: examples use Tally, and nothing identifies a real project, its people or its customers
- [ ] A new seat links its accepted seat proposal issue; a change to what a seat owns links its accepted feature request
