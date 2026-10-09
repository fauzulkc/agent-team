#!/usr/bin/env python3
"""Seat the team in a project: the deterministic half of `team-setup`.

    scaffold.py --root <project> --project "<name>" --seats ceo,engineering,testing,bar-raiser
                [--owner-acts "publishing, sending, spending, signing"]
                [--push-rule "the owner pushes"] [--force]
    scaffold.py --root <project> --add design,user          add seats to an existing team
    scaffold.py --root <project> --sync                    refresh the project's seat rulebooks
    scaffold.py --list                                     print the seat catalogue

Writes, never overwriting an existing file unless --force (it reports what it skipped):
  docs/TEAM.md                 the shared rulebook, with the roster for the chosen seats
  docs/DECISIONS.md            the decision register, DEC-1 recording the team
  docs/team/<team>.md          one project brief per seat (filled in by the setup session)
  docs/team/tracker.md, owner-questions.md   when the Chief of Staff is seated
  .claude/skills/seat-<role>/  each seat's rulebook, copied in from this skill's seats/ folder, so
                               workers can preload it and anyone who clones the project has it;
                               docs/team/seat-skills.lock records each copy's hash for --sync
  scripts/gen-team-agents.py   the worker generator, copied in so the project owns it
  .claude/agents/*.md          generated: one <team>-worker per seat plus six shared tiers
  scratchpad/team/             inbox/, runs/<team>/, shared/ (scratchpad/ added to .gitignore)
  CLAUDE.md                    a pointer to docs/TEAM.md appended (or the file created)
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
TEMPLATES = SKILL / "templates"
CATALOGUE = SKILL / "references" / "seats.md"
SEATS_SRC = SKILL / "seats"

TIER_LABELS = {
    "quick": "Haiku 5.5 (`claude-haiku-5-5`), effort low",
    "scout": "Haiku 5.5 (`claude-haiku-5-5`), effort low",
    "check": "Haiku 5.5 (`claude-haiku-5-5`), effort medium",
    "execution": "Sonnet, effort low",
    "build": "Sonnet, effort high",
    "research": "Opus, effort high",
    "deep": "Opus, effort max",
}
CLAUDE_POINTER = """
## The team

This project is run by a seated team: each seat is a session opened with its skill
(`/seat-ceo`, `/seat-engineering`, …). Who sits where, the model tiers, how seats call each
other's teams, the message syntax and how to report to the owner are in
[docs/TEAM.md](docs/TEAM.md); each seat's project facts are in `docs/team/<team>.md`; decisions
are in [docs/DECISIONS.md](docs/DECISIONS.md) and outrank every seat. Regenerate the workers with
`python3 scripts/gen-team-agents.py` after changing the roster.
"""


def catalogue() -> list[dict[str, str]]:
    rows = []
    for line in CATALOGUE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 8 or cells[0] in ("Mark", "") or set(cells[0]) <= {"-"}:
            continue
        mark, seat, skill, team, kind, register, reports_to, when = cells
        rows.append(dict(mark=mark, seat=seat, skill=skill.strip("`"), team=team.strip("`"),
                         kind=kind, register=register, reports_to=reports_to, when=when))
    return rows


def roster_row(r: dict[str, str]) -> str:
    return f"| {r['mark']} | {r['seat']} | `{r['skill']}` | `{r['team']}` | {r['kind']} | {r['register']} | {r['reports_to']} |"


def fill(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def write(path: Path, body: str, force: bool, report: list[str]) -> None:
    if path.exists() and not force:
        report.append(f"skipped (exists): {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    report.append(f"wrote: {path}")


def tree_hash(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in d.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(d)).encode()); h.update(f.read_bytes())
    return h.hexdigest()


def vendor_seats(root: Path, skills: list[str], sync_all: bool, report: list[str]) -> None:
    """Copy seat rulebooks into <root>/.claude/skills. A copy the project edited is never overwritten."""
    lock_path = root / "docs" / "team" / "seat-skills.lock"
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    if sync_all:
        skills = sorted(set(skills) | set(lock))
    for skill in skills:
        src, dst = SEATS_SRC / skill, root / ".claude" / "skills" / skill
        if not src.is_dir():
            report.append(f"seat rulebook not found in this setup skill: {skill}")
            continue
        new = tree_hash(src)
        if dst.exists():
            cur = tree_hash(dst)
            if cur == new:
                lock[skill] = new
                continue
            if lock.get(skill) != cur:
                report.append(f"kept (edited in this project): .claude/skills/{skill} — merge by hand from {src}")
                continue
            shutil.rmtree(dst)
            report.append(f"updated: .claude/skills/{skill}")
        else:
            report.append(f"copied: .claude/skills/{skill}")
        shutil.copytree(src, dst)
        lock[skill] = new
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path)
    ap.add_argument("--project")
    ap.add_argument("--seats", help="comma-separated team names from the catalogue")
    ap.add_argument("--add", help="comma-separated team names to add to an existing team")
    ap.add_argument("--sync", action="store_true", help="refresh every seat rulebook the project has not edited")
    ap.add_argument("--owner-acts", default="publishing, sending, spending, signing")
    ap.add_argument("--push-rule", default="the owner pushes; a seat never pushes unless DECISIONS.md says otherwise.")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    cat = catalogue()
    by_team = {r["team"]: r for r in cat}
    if a.list:
        for r in cat:
            print(f"{r['mark']} {r['team']:<17} {r['seat']:<30} {r['kind']:<15} seat it when: {r['when']}")
        return 0
    if not a.root:
        ap.error("--root is required")
    root = a.root.resolve()
    report: list[str] = []
    today = datetime.date.today().isoformat()
    team_doc = root / "docs" / "TEAM.md"

    if a.sync:
        if not team_doc.is_file():
            ap.error("--sync needs an existing docs/TEAM.md")
        vendor_seats(root, [], True, report)
        print("\n".join(report) or "all seat rulebooks current")
        return 0

    if a.add:
        if not team_doc.is_file():
            ap.error("--add needs an existing docs/TEAM.md; run a full setup first")
        wanted = [t.strip() for t in a.add.split(",") if t.strip()]
        unknown = [t for t in wanted if t not in by_team]
        if unknown:
            ap.error(f"not in the catalogue: {', '.join(unknown)} (scaffold.py --list)")
        text = team_doc.read_text(encoding="utf-8")
        present = set(re.findall(r"\| `([a-z-]+)` \| [a-z-]+ \|", text))
        new_rows = [roster_row(by_team[t]) for t in wanted if t not in present]
        text = text.replace("<!-- roster:end -->", "\n".join(new_rows) + "\n<!-- roster:end -->") if new_rows else text
        team_doc.write_text(text, encoding="utf-8")
        report.append(f"roster: added {len(new_rows)} seat(s)")
        project = a.project or root.name
        seats = [by_team[t] for t in wanted]
    else:
        if not (a.project and a.seats):
            ap.error("--project and --seats are required for a setup (or use --add)")
        wanted = [t.strip() for t in a.seats.split(",") if t.strip()]
        unknown = [t for t in wanted if t not in by_team]
        if unknown:
            ap.error(f"not in the catalogue: {', '.join(unknown)} (scaffold.py --list)")
        if "ceo" not in wanted:
            wanted.insert(0, "ceo")
            report.append("added ceo: every team keeps a decision register")
        project = a.project
        seats = [r for r in cat if r["team"] in wanted]  # catalogue order
        values = {"PROJECT": project, "DATE": today, "ROSTER_ROWS": "\n".join(roster_row(r) for r in seats),
                  "OWNER_ACTS": a.owner_acts, "PUSH_RULE": a.push_rule}
        values.update({f"TIER_{k.upper()}": v for k, v in TIER_LABELS.items()})
        write(team_doc, fill((TEMPLATES / "TEAM.md").read_text(encoding="utf-8"), values), a.force, report)
        write(root / "docs" / "DECISIONS.md", fill((TEMPLATES / "DECISIONS.md").read_text(encoding="utf-8"), values), a.force, report)

    vendor_seats(root, [r["skill"] for r in seats], False, report)
    brief = (TEMPLATES / "seat-brief.md").read_text(encoding="utf-8")
    for r in seats:
        v = {"PROJECT": project, "MARK": r["mark"], "SEAT": r["seat"], "SKILL": r["skill"],
             "REGISTER": r["register"], "REPORTS_TO": r["reports_to"]}
        write(root / "docs" / "team" / f"{r['team']}.md", fill(brief, v), a.force, report)
        if r["team"] == "chief-of-staff":
            for name in ("tracker.md", "owner-questions.md"):
                write(root / "docs" / "team" / name, fill((TEMPLATES / name).read_text(encoding="utf-8"),
                                                          {"PROJECT": project}), a.force, report)

    gen_dst = root / "scripts" / "gen-team-agents.py"
    if not gen_dst.exists() or a.force:
        gen_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / "gen-team-agents.py", gen_dst)
        report.append(f"wrote: {gen_dst}")
    else:
        report.append(f"skipped (exists): {gen_dst}")

    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if not any(l.strip() in ("scratchpad/", "/scratchpad/", "scratchpad") for l in lines):
        gi.write_text("\n".join(lines + ["", "# the team's ephemeral workspace (docs/TEAM.md §5)", "scratchpad/"]) + "\n", encoding="utf-8")
        report.append("gitignore: scratchpad/ added")

    cm = root / "CLAUDE.md"
    cm_text = cm.read_text(encoding="utf-8") if cm.exists() else f"# {project}\n"
    if "docs/TEAM.md" not in cm_text:
        cm.write_text(cm_text.rstrip() + "\n" + CLAUDE_POINTER, encoding="utf-8")
        report.append("CLAUDE.md: team pointer added")

    res = subprocess.run([sys.executable, str(gen_dst)], cwd=root, capture_output=True, text=True)
    report.append((res.stdout + res.stderr).strip())
    print("\n".join(report))
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
