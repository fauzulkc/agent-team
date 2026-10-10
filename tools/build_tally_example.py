#!/usr/bin/env python3
"""Rebuild the generated half of examples/tally/ from the current scaffold, templates and generator.

    python3 tools/build_tally_example.py            rewrite the generated files in examples/tally/
    python3 tools/build_tally_example.py --check    exit 1 and name each generated file that is stale

The example is a team of eight seats picked by name, the path an owner takes when they name the seats
themselves:

    scaffold.py --root <tmp> --project Tally --seats ceo,chief-of-staff,product,engineering,frontend,testing,
                bar-raiser,design --owner-acts "publishing, emailing customers, spending, signing"
                --question "Which seats for Tally?" --record "<the owner's words, below>"

so its decision register numbers the team DEC-2, as a setup with --record does, and the walkthrough's
recurring invoices (DEC-3) and the switch (DEC-4) follow it. Today's date in the scaffold's output is
replaced by the story's date, DATE.

Generated (rewritten here, compared by --check): docs/TEAM.md, CLAUDE.md, .gitignore,
docs/team/seat-skills.lock, scratchpad/team/README.md, .claude/agents/*.md, every seat brief except
docs/team/engineering.md, and docs/DECISIONS.md up to and including the DEC-2 row.
Written by hand, the way a working team fills them (never touched here): README.md,
docs/team/engineering.md, docs/team/tracker.md, docs/team/owner-questions.md, the rows of
docs/DECISIONS.md after DEC-2, and scratchpad/team/{inbox,runs,shared}/.
Left out of the example on purpose: .claude/skills/ (the rulebooks live in skills/team-setup/seats/)
and scripts/gen-team-agents.py (the copied generator).
check.py runs `--check`. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
import tempfile
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252; seat marks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "tally"
SCAFFOLD = ROOT / "skills" / "team-setup" / "scripts" / "scaffold.py"
SEATS = "ceo,chief-of-staff,product,engineering,frontend,testing,bar-raiser,design"
DATE = "2026-03-02"
OWNER_ACTS = "publishing, emailing customers, spending, signing"
QUESTION = "Which seats for Tally?"
WORDS = "the CEO, a Chief of Staff, Product, Engineering, Frontend, Testing, the Bar Raiser and Design; emailing customers is mine too"
HAND = {"README.md", "docs/team/engineering.md", "docs/team/tracker.md", "docs/team/owner-questions.md"}
SKIP_DIRS = (".claude/skills/", "scripts/", "scratchpad/team/inbox/", "scratchpad/team/runs/", "scratchpad/team/shared/")
DECISIONS = "docs/DECISIONS.md"


def generated() -> dict[str, str]:
    """{example-relative path: text} for every generated file, from a fresh scaffold run."""
    with tempfile.TemporaryDirectory(prefix="tally-example-") as tmp:
        out = Path(tmp)
        res = subprocess.run([sys.executable, str(SCAFFOLD), "--root", str(out), "--project", "Tally", "--seats", SEATS,
                              "--owner-acts", OWNER_ACTS, "--question", QUESTION, "--record", WORDS],
                             capture_output=True, text=True, encoding="utf-8")
        if res.returncode:
            raise SystemExit(f"scaffold failed:\n{res.stderr or res.stdout}")
        today = datetime.date.today().isoformat()
        files = {}
        for f in sorted(out.rglob("*")):
            rel = f.relative_to(out).as_posix()
            if f.is_file() and rel not in HAND and not rel.startswith(SKIP_DIRS):
                files[rel] = f.read_text(encoding="utf-8").replace(today, DATE)
    head = files[DECISIONS]
    assert head.rstrip("\n").splitlines()[-1].startswith("| **DEC-2** |"), "the team's decision is no longer DEC-2"
    return files


def hand_rows(text: str) -> str:
    """The example's decision rows after DEC-2, written by hand."""
    lines = text.splitlines(keepends=True)
    at = next((i for i, l in enumerate(lines) if l.startswith("| **DEC-2** |")), None)
    return "".join(lines[at + 1:]) if at is not None else ""


def stale(files: dict[str, str]) -> list[str]:
    """Generated paths whose example copy differs, is missing, or should not exist."""
    out = []
    for rel, text in files.items():
        f = EXAMPLE / rel
        have = f.read_text(encoding="utf-8") if f.is_file() else None
        if rel == DECISIONS:
            ok = have is not None and have.startswith(text)
        else:
            ok = have == text
        if not ok:
            out.append(rel)
    agents = EXAMPLE / ".claude" / "agents"
    for f in sorted(agents.glob("*.md")) if agents.is_dir() else []:
        rel = f.relative_to(EXAMPLE).as_posix()
        if rel not in files:
            out.append(f"{rel} (no longer generated)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 when a generated file in examples/tally is stale")
    a = ap.parse_args()
    files = generated()
    bad = stale(files)
    if a.check:
        for rel in bad:
            print(f"examples/tally/{rel}: stale; run python3 tools/build_tally_example.py")
        if not bad:
            print("examples/tally: generated files current")
        return 1 if bad else 0
    for rel, text in files.items():
        f = EXAMPLE / rel
        if rel == DECISIONS and f.is_file():
            text += hand_rows(f.read_text(encoding="utf-8"))
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    for rel in bad:
        if rel.endswith("(no longer generated)"):
            (EXAMPLE / rel.split(" ")[0]).unlink()
    print(f"examples/tally: {len(bad)} generated file(s) rewritten" + (f": {', '.join(bad)}" if bad else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
