#!/usr/bin/env python3
"""Seat the team in a project, or change it: the deterministic half of `team-setup` and `team-reevaluate`.

    scaffold.py --root <project> --plan docs/team/plan.json [--record "<owner's words>"]
        First run: writes the whole team for the plan's seats. Later runs: adds the plan's seats that
        are not seated yet and retires the plan's "retire" list. A plan comes from plan.py or
        reevaluate.py; a seat spec is catalogue, merge or derive (see plan.py).
    scaffold.py --root <project> --project "<name>" --seats ceo,engineering,testing   (catalogue seats only)
    scaffold.py --root <project> --add design,user        add catalogue seats
    scaffold.py --root <project> --retire user            retire seats (briefs kept, workers removed)
    scaffold.py --root <project> --sync                   refresh rulebooks the project has not edited
    scaffold.py --list                                    print the seat catalogue

Writes, never overwriting an existing file unless --force (it reports what it skipped):
  docs/TEAM.md, docs/DECISIONS.md, docs/team/<team>.md (one brief per seat), docs/team/tracker.md and
  owner-questions.md (with a Chief of Staff), .claude/skills/seat-<role>/ (each seat's rulebook:
  copied from the catalogue, composed for a merge, or derived for a new role), docs/team/seat-skills.lock
  (each rulebook's origin and hash, for --sync), scripts/gen-team-agents.py, .claude/agents/*.md
  (generated), scratchpad/team/ (gitignored), and a pointer in CLAUDE.md.
A derived rulebook carries an AUTHORING NEEDED block until the session rewrites it for its role;
the generator's --check fails while any seated rulebook still carries it.
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
sys.path.insert(0, str(HERE))
from seatgen import AUTHORING_MARK, compose_derive, compose_merge  # noqa: E402
from teamlib import (ALWAYS, MERGES, SEATS_SRC, SKILL, catalogue, load_lock, roster,  # noqa: E402
                     roster_row, save_lock)

TEMPLATES = SKILL / "templates"
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
`python3 scripts/gen-team-agents.py` after changing the roster. Re-evaluate the team with
`team-reevaluate` ("re-evaluate the team").
"""


def fill(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def write(path: Path, body: str, force: bool, report: list[str]) -> bool:
    if path.exists() and not force:
        report.append(f"skipped (exists): {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    report.append(f"wrote: {path}")
    return True


def tree_hash(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in d.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(d)).encode()); h.update(f.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------- seat specs → rows, rulebooks

def spec_row(spec: dict, cat: dict) -> dict[str, str]:
    t = spec.get("type", "catalogue")
    if t == "catalogue":
        return dict(cat[spec["team"]])
    if t == "merge":
        members = [cat[m] for m in spec["of"]]
        return dict(mark=spec["mark"], seat=spec["seat"], skill=f"seat-{spec['team']}", team=spec["team"],
                    kind=spec.get("kind", "director"), register="; ".join(m["register"] for m in members),
                    reports_to=spec.get("reports_to", "CEO"))
    return dict(mark=spec["mark"], seat=spec["seat"], skill=f"seat-{spec['team']}", team=spec["team"],
                kind=spec.get("kind", "implementation"), register=spec.get("register", spec.get("scope", "")),
                reports_to=spec.get("reports_to", "CEO"))


def rulebook_text(spec: dict) -> str | None:
    t = spec.get("type", "catalogue")
    if t == "merge":
        return compose_merge(spec["team"], spec["seat"], spec["mark"], spec["of"])
    if t == "derive":
        return compose_derive(spec["team"], spec["seat"], spec["mark"], spec["base"], spec.get("kind", "implementation"),
                              spec.get("reports_to", "CEO"), spec.get("scope", ""), spec.get("register", ""),
                              spec.get("sibling", ""))
    return None


def vendor(root: Path, spec: dict, cat: dict, lock: dict, report: list[str]) -> None:
    """Put one seat's rulebook into <root>/.claude/skills and record its origin in the lock."""
    t = spec.get("type", "catalogue")
    skill = cat[spec["team"]]["skill"] if t == "catalogue" else f"seat-{spec['team']}"
    dst = root / ".claude" / "skills" / skill
    if t == "catalogue":
        src = SEATS_SRC / skill
        if not src.is_dir():
            report.append(f"seat rulebook not found in this setup skill: {skill}")
            return
        if not dst.exists():
            shutil.copytree(src, dst)
            report.append(f"copied: .claude/skills/{skill}")
        lock[skill] = {"hash": tree_hash(dst), "origin": "catalogue"}
        return
    if dst.exists():
        report.append(f"kept (exists): .claude/skills/{skill}")
        lock.setdefault(skill, {"hash": tree_hash(dst), "origin": f"{t}:project"})
        return
    (dst).mkdir(parents=True, exist_ok=True)
    (dst / "SKILL.md").write_text(rulebook_text(spec), encoding="utf-8")
    entry = {"hash": tree_hash(dst), "seat": spec["seat"], "mark": spec["mark"]}
    if t == "merge":
        entry["origin"] = "merge:" + "+".join(spec["of"])
        report.append(f"composed: .claude/skills/{skill} (holds {', '.join(spec['of'])})")
    else:
        entry["origin"] = f"derive:{spec['base']}"
        report.append(f"derived: .claude/skills/{skill} from {spec['base']} — NEEDS AUTHORING for its role")
    lock[skill] = entry


def sync(root: Path, report: list[str]) -> None:
    lock = load_lock(root)
    for skill, entry in sorted(lock.items()):
        dst = root / ".claude" / "skills" / skill
        origin = entry.get("origin", "catalogue")
        if origin == "catalogue":
            src = SEATS_SRC / skill
            if not src.is_dir():
                report.append(f"not in this version's catalogue: {skill}")
                continue
            new_text_dir = src
            fresh = tree_hash(src)
        elif origin.startswith("merge:"):
            members = origin[len("merge:"):].split("+")
            team = skill[len("seat-"):]
            text = compose_merge(team, entry.get("seat", team), entry.get("mark", "🔗"), members)
            fresh = hashlib.sha256(b"SKILL.md" + text.encode()).hexdigest()
            new_text_dir = None
        else:
            if dst.is_dir() and AUTHORING_MARK in (dst / "SKILL.md").read_text(encoding="utf-8"):
                report.append(f"still needs authoring: .claude/skills/{skill}")
            continue  # derived rulebooks are the project's own
        if not dst.exists():
            report.append(f"missing, re-created: .claude/skills/{skill}")
        else:
            cur = tree_hash(dst)
            if cur == fresh:
                continue
            if cur != entry.get("hash"):
                report.append(f"kept (edited in this project): .claude/skills/{skill}")
                continue
            shutil.rmtree(dst)
            report.append(f"updated: .claude/skills/{skill}")
        if new_text_dir is not None:
            shutil.copytree(new_text_dir, dst)
        else:
            dst.mkdir(parents=True, exist_ok=True)
            (dst / "SKILL.md").write_text(text, encoding="utf-8")
        entry["hash"] = tree_hash(dst)
    save_lock(root, lock)


# ---------------------------------------------------------------------------- roster edits

def add_rows(team_doc: Path, rows: list[dict[str, str]], report: list[str]) -> None:
    text = team_doc.read_text(encoding="utf-8")
    present = {r["team"] for r in roster(team_doc)}
    new = [roster_row(r) for r in rows if r["team"] not in present]
    if new:
        text = text.replace("<!-- roster:end -->", "\n".join(new) + "\n<!-- roster:end -->")
        team_doc.write_text(text, encoding="utf-8")
    report.append(f"roster: added {len(new)} seat(s)")


def retire(root: Path, teams: list[str], report: list[str]) -> None:
    team_doc = root / "docs" / "TEAM.md"
    rows = {r["team"]: r for r in roster(team_doc)}
    text = team_doc.read_text(encoding="utf-8")
    lock = load_lock(root)
    today = datetime.date.today().isoformat()
    for t in teams:
        if t in ALWAYS:
            report.append(f"not retired: {t} (every team keeps it)")
            continue
        r = rows.get(t)
        if not r:
            report.append(f"not seated: {t}")
            continue
        text = "\n".join(l for l in text.splitlines() if not re.match(rf"^\|[^|]*\|[^|]*\| `[^`]*` \| `{re.escape(t)}` \|", l)) + "\n"
        skill_dir = root / ".claude" / "skills" / r["skill"]
        origin = lock.get(r["skill"], {}).get("origin", "catalogue")
        if skill_dir.exists():
            if origin.startswith("derive:"):
                archive = root / "docs" / "team" / "retired" / r["skill"]
                archive.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(skill_dir), str(archive))
                report.append(f"archived (authored): docs/team/retired/{r['skill']}")
            else:
                shutil.rmtree(skill_dir)
        lock.pop(r["skill"], None)
        brief = root / "docs" / "team" / f"{t}.md"
        if brief.exists():
            b = brief.read_text(encoding="utf-8")
            if "**Retired" not in b:
                brief.write_text(f"> **Retired {today}.** Kept for the record; its work moved as docs/DECISIONS.md says.\n\n" + b,
                                 encoding="utf-8")
        report.append(f"retired: {r['mark']} {r['seat']}")
    team_doc.write_text(text, encoding="utf-8")
    save_lock(root, lock)


def record_decision(root: Path, question: str, words: str, report: list[str]) -> None:
    p = root / "docs" / "DECISIONS.md"
    if not p.exists():
        return
    text = p.read_text(encoding="utf-8")
    n = max([int(x) for x in re.findall(r"\*\*DEC-(\d+)\*\*", text)] or [0]) + 1
    today = datetime.date.today().isoformat()
    row = (f"| **DEC-{n}** | {question} | `docs/team/plan.json`, `docs/TEAM.md` | ✅ {today}, the owner, verbatim: "
           f"*\"{words}\"* (recorded by the team scripts on the owner's word) |")
    p.write_text(text.rstrip() + "\n" + row + "\n", encoding="utf-8")
    report.append(f"recorded: DEC-{n}")


def write_briefs(root: Path, project: str, rows: list[dict[str, str]], specs: dict[str, dict], force: bool,
                 report: list[str]) -> None:
    brief = (TEMPLATES / "seat-brief.md").read_text(encoding="utf-8")
    for r in rows:
        v = {"PROJECT": project, "MARK": r["mark"], "SEAT": r["seat"], "SKILL": r["skill"],
             "REGISTER": r["register"], "REPORTS_TO": r["reports_to"]}
        body = fill(brief, v)
        spec = specs.get(r["team"], {})
        if spec.get("type") == "merge":  # carry the members' project facts into the merged seat's brief
            for m in spec["of"]:
                mb = root / "docs" / "team" / f"{m}.md"
                if mb.exists():
                    body += f"\n\n## Carried over from the {m} brief\n\n" + re.sub(r"^#", "###", mb.read_text(encoding="utf-8"), flags=re.M)
        if spec.get("type") == "derive" and spec.get("scope"):
            body = body.replace("- **Paths:** _(", f"- **Scope:** {spec['scope']}\n- **Paths:** _(", 1)
        write(root / "docs" / "team" / f"{r['team']}.md", body, force, report)
        if r["team"] == "chief-of-staff" or (spec.get("type") == "merge" and "chief-of-staff" in spec.get("of", [])):
            for name in ("tracker.md", "owner-questions.md"):
                write(root / "docs" / "team" / name, fill((TEMPLATES / name).read_text(encoding="utf-8"),
                                                          {"PROJECT": project}), force, report)


def finish(root: Path, project: str, force: bool, report: list[str]) -> int:
    gen_dst = root / "scripts" / "gen-team-agents.py"
    if not gen_dst.exists() or force:
        gen_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / "gen-team-agents.py", gen_dst)
        report.append(f"wrote: {gen_dst}")
    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if not any(l.strip() in ("scratchpad/", "/scratchpad/", "scratchpad") for l in lines):
        gi.write_text("\n".join(lines + ["", "# the team's ephemeral workspace (docs/TEAM.md §5)", "scratchpad/"]) + "\n",
                      encoding="utf-8")
        report.append("gitignore: scratchpad/ added")
    cm = root / "CLAUDE.md"
    cm_text = cm.read_text(encoding="utf-8") if cm.exists() else f"# {project}\n"
    if "docs/TEAM.md" not in cm_text:
        cm.write_text(cm_text.rstrip() + "\n" + CLAUDE_POINTER, encoding="utf-8")
        report.append("CLAUDE.md: team pointer added")
    res = subprocess.run([sys.executable, str(gen_dst)], cwd=root, capture_output=True, text=True)
    report.append((res.stdout + res.stderr).strip())
    pending = [str(p.parent.relative_to(root)) for p in (root / ".claude" / "skills").glob("seat-*/SKILL.md")
               if AUTHORING_MARK in p.read_text(encoding="utf-8")]
    for p in pending:
        report.append(f"NEEDS AUTHORING: {p}/SKILL.md (rewrite for its role per references/seat-contract.md)")
    return res.returncode


# ---------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path)
    ap.add_argument("--plan", type=Path, help="a plan from plan.py or reevaluate.py")
    ap.add_argument("--project")
    ap.add_argument("--seats", help="comma-separated catalogue teams (shorthand for a plan)")
    ap.add_argument("--add", help="comma-separated catalogue teams to add")
    ap.add_argument("--retire", help="comma-separated teams to retire")
    ap.add_argument("--sync", action="store_true", help="refresh every rulebook the project has not edited")
    ap.add_argument("--record", help="the owner's words approving this change; recorded as a decision")
    ap.add_argument("--owner-acts", default="publishing, sending, spending, signing")
    ap.add_argument("--push-rule", default="the owner pushes; a seat never pushes unless DECISIONS.md says otherwise.")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    cat = catalogue()
    if a.list:
        for r in cat.values():
            print(f"{r['mark']} {r['team']:<17} {r['seat']:<32} {r['kind']:<15} seat it when: {r['when']}")
        return 0
    if not a.root:
        ap.error("--root is required")
    root = a.root.resolve()
    team_doc = root / "docs" / "TEAM.md"
    report: list[str] = []

    if a.sync:
        if not team_doc.is_file():
            ap.error("--sync needs an existing docs/TEAM.md")
        sync(root, report)
        print("\n".join(report) or "all seat rulebooks current")
        return 0

    plan: dict = {"seats": [], "retire": []}
    if a.plan:
        plan.update(json.loads(a.plan.read_text(encoding="utf-8")))
    for t in (a.seats or "").split(",") + (a.add or "").split(","):
        if t.strip():
            plan["seats"].append({"team": t.strip(), "type": "catalogue", "why": "named on the command line"})
    plan["retire"] = list(plan.get("retire") or []) + [t.strip() for t in (a.retire or "").split(",") if t.strip()]
    unknown = [s["team"] for s in plan["seats"] if s.get("type", "catalogue") == "catalogue" and s["team"] not in cat]
    unknown += [m for s in plan["seats"] if s.get("type") == "merge" for m in s["of"] if m not in cat]
    if unknown:
        ap.error(f"not in the catalogue: {', '.join(sorted(set(unknown)))} (scaffold.py --list)")

    fresh = not team_doc.is_file()
    project = a.project or plan.get("project") or root.name
    if fresh:
        if not plan["seats"]:
            ap.error("a first setup needs --plan or --seats")
        teams = {s["team"] for s in plan["seats"]} | {m for s in plan["seats"] if s.get("type") == "merge" for m in s["of"]}
        for t in ALWAYS:
            if t not in teams:
                plan["seats"].insert(0, {"team": t, "type": "catalogue", "why": "every team keeps it"})
                report.append(f"added {t}: every team keeps it")
    specs = {s["team"]: s for s in plan["seats"]}
    order = list(cat)
    rows = sorted((spec_row(s, cat) for s in plan["seats"]),
                  key=lambda r: (order.index(r["team"]) if r["team"] in order else len(order), r["team"]))

    if fresh:
        values = {"PROJECT": project, "DATE": datetime.date.today().isoformat(),
                  "ROSTER_ROWS": "\n".join(roster_row(r) for r in rows),
                  "OWNER_ACTS": plan.get("owner_acts", a.owner_acts), "PUSH_RULE": plan.get("push_rule", a.push_rule)}
        values.update({f"TIER_{k.upper()}": v for k, v in TIER_LABELS.items()})
        write(team_doc, fill((TEMPLATES / "TEAM.md").read_text(encoding="utf-8"), values), a.force, report)
        write(root / "docs" / "DECISIONS.md", fill((TEMPLATES / "DECISIONS.md").read_text(encoding="utf-8"), values),
              a.force, report)
    else:
        seated = {r["team"] for r in roster(team_doc)}
        rows = [r for r in rows if r["team"] not in seated]
        add_rows(team_doc, rows, report)

    lock = load_lock(root)
    for r in rows:
        vendor(root, specs.get(r["team"], {"team": r["team"], "type": "catalogue"}), cat, lock, report)
    save_lock(root, lock)
    write_briefs(root, project, rows, specs, a.force, report)
    if plan["retire"]:
        retire(root, plan["retire"], report)
    if a.record:
        what = []
        if rows:
            what.append("seat " + ", ".join(f"{r['mark']} {r['seat']}" for r in rows))
        if plan["retire"]:
            what.append("retire " + ", ".join(plan["retire"]))
        record_decision(root, ("The team: " if fresh else "Team change: ") + "; ".join(what), a.record, report)
    rc = finish(root, project, a.force, report)
    print("\n".join(report))
    return rc


if __name__ == "__main__":
    sys.exit(main())
