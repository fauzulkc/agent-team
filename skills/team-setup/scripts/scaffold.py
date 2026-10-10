#!/usr/bin/env python3
"""Seat the team in a project, or change it: the deterministic half of `team-setup` and `team-reevaluate`.

    scaffold.py --root <project> --plan docs/team/plan.json [--only KEY,...|none] [--record "<owner's words>"]
                [--question "<the question the owner answered>"]
        First run: writes the whole team for the plan's seats. Later runs: adds the plan's seats that
        are not seated yet and retires the plan's "retire" list. A plan comes from plan.py (top-level
        "seats" and "retire") or reevaluate.py (also "proposals", each with a unique "key"); a seat spec
        is catalogue, merge or derive (see plan.py). With --only, only the named proposals apply and
        every other proposal is declined; --only none applies nothing. Without --only, the top-level
        "seats" and "retire" apply.
    scaffold.py --root <project> --project "<name>" --seats ceo,engineering,testing   (catalogue seats only)
    scaffold.py --root <project> --add design,user        add catalogue seats
    scaffold.py --root <project> --retire user            retire seats (briefs kept, workers removed)
    scaffold.py --root <project> --sync                   refresh rulebooks the project has not edited
    scaffold.py --list                                    print the seat catalogue

--record and --question work with --plan, --add, --retire and --seats. A run that changes the team
or declines a proposal, with --record, appends one row to docs/DECISIONS.md:
    | **DEC-n** | <question> | <the plan applied, relative to the root, or "named by the owner"> |
      ✅ <date>: <what changed, in seat names with marks>. Declined: <titles, or nothing>. Owner's words: "<verbatim>" |
A plan outside the project is cited by its file name alone. The default push rule written into a new
TEAM.md is "a seat asks the owner before each push and pushes on the owner's yes." (--push-rule). The question defaults to "Team change" for a plan and "Team change named by the owner" otherwise.
A run that changes nothing and declines nothing records no row and prints
"nothing changed; no decision recorded". Declined proposals are appended to docs/team/declined.json
(a JSON list of {"key", "title", "action", "signals", "date", "decision"}; "decision" is the row's
DEC-n, or null without --record), which reevaluate.py reads so it does not propose them again.

Refusals, checked before anything is written (the run exits 2 and writes nothing):
  - a seat spec with an unknown type, a missing key, a member or team not in the catalogue, or a
    derive base that is not a seat rulebook in this setup skill; a team named both to seat and to retire;
  - a roster row in docs/TEAM.md that does not parse to seven cells (fix it by hand first; --sync too);
  - --only with no proposal key (an empty list is refused, never read as "none");
  - a new roster row whose mark (compared without U+FE0F) is already seated or used twice in the plan;
  - a new seat for a role a seated merged seat already holds, unless the same plan retires that merged
    seat (an unmerge), or a new merged seat whose member is seated on its own, unless the same plan
    retires that member; --force overrides these two, never the others.
The retire list is settled before those checks, so a seat counts as gone only when its retire goes ahead.
A retire of a seat with no roster row of its own is reported ("not seated") and skipped. A retire that
would leave the CEO or the Bar Raiser held by no seat is refused on its own ("not retired"): retiring the
Bar Raiser needs a merged seat that holds it in the same plan, and retiring a merged seat that holds it
needs the same plan to seat it again. A new seat that needed a refused retire is then refused with the
other conflicts, and nothing is written.

Writes, never overwriting an existing file unless --force (it reports what it skipped):
  docs/TEAM.md, docs/DECISIONS.md, docs/team/<team>.md (one brief per seat; a brief marked Retired is never
  overwritten, even with --force, and a merged seat's surviving brief gets the member briefs it lacks),
  docs/team/tracker.md and owner-questions.md (on every run, never overwritten; kept by the Chief of Staff,
  or by the CEO while none is seated), .claude/skills/seat-<role>/ (each seat's rulebook:
  copied from the catalogue, composed for a merge, or derived for a new role), docs/team/seat-skills.lock
  (each rulebook's origin, hash and the date it was seated, for --sync; see teamlib), scripts/gen-team-agents.py,
  .claude/agents/*.md (generated), scratchpad/team/ (gitignored), and a pointer in CLAUDE.md.
A rulebook folder that already exists is kept: recorded with origin "project" (the project's own; --sync
never touches it) unless it holds a SKILL.md byte-identical to what this version would write. A folder with
no SKILL.md keeps its files and gets this version's rulebook beside them, recorded as "project". Retiring a seat archives,
never deletes, a rulebook that is derived, the project's own, untracked, or edited since it was seated:
to docs/team/retired/<skill>-<date> (-2, -3 if taken). Re-adding a seat removes the "Retired" line from
its brief, and a derived seat comes back from its newest archived copy instead of a fresh unauthored one.
A seated row the plan names whose rulebook, brief or lock entry is missing is repaired.
A derived rulebook carries an AUTHORING NEEDED banner until the session rewrites it for its role; until
then the generator writes it no worker and its --check fails. Line endings of TEAM.md, DECISIONS.md and
briefs are kept as found (CRLF stays CRLF).
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
from plan import FRONTEND_HOLDS  # noqa: E402
from seatgen import AUTHORING_MARK, compose_derive, compose_merge  # noqa: E402
from teamlib import (ALWAYS, MERGES, ROSTER_RE, SEATS_SRC, SKILL, catalogue, coverage, covers_frontend,  # noqa: E402
                     load_lock, merge_members, project_name, roster, roster_cells, roster_problems, roster_row,
                     save_lock)
if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252; seat marks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

TEMPLATES = SKILL / "templates"
PUSH_RULE = "a seat asks the owner before each push and pushes on the owner's yes."
CEO_KEEPS = "**Kept by the 🧭 CEO while no 🛎️ Chief of Staff is seated.**"
RETIRED = Path("docs") / "team" / "retired"
VS16 = "️"
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


def today() -> str:
    return datetime.date.today().isoformat()


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


def read_doc(path: Path) -> tuple[str, str]:
    """A text file's content with LF line endings, and the ending it was written with ("\\r\\n" or "\\n")."""
    raw = path.read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n"), ("\r\n" if "\r\n" in raw else "\n")


def write_doc(path: Path, text: str, newline: str) -> None:
    """Write LF text back with the file's own line ending."""
    path.write_bytes((text.replace("\n", newline) if newline != "\n" else text).encode("utf-8"))


def tree_hash(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in d.rglob("*") if p.is_file()):
        h.update(f.relative_to(d).as_posix().encode()); h.update(f.read_bytes())  # the same hash on every system
    return h.hexdigest()


def text_hash(text: str) -> str:
    """tree_hash of a folder holding only SKILL.md with this text."""
    return hashlib.sha256(b"SKILL.md" + text.encode()).hexdigest()


def rel(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


def seat_name(team: str, known: dict[str, dict], cat: dict) -> str:
    """A seat in plain words, mark first ("📐 Design"), from the roster or plan, the catalogue, or MERGES."""
    r = known.get(team) or cat.get(team) or MERGES.get(team)
    return f"{r['mark']} {r['seat']}" if r else team


def names(teams: list[str], known: dict[str, dict], cat: dict) -> str:
    return ", ".join(seat_name(t, known, cat) for t in teams)


# ---------------------------------------------------------------------------- seat specs → rows, rulebooks

def validate_specs(seats: list[dict], cat: dict) -> list[str]:
    """Every problem with the plan's seat specs, in plain words; empty when all can be seated."""
    problems, teams = [], []
    for s in seats:
        team, t = s.get("team"), s.get("type", "catalogue")
        if not team:
            problems.append(f"a seat spec names no team: {json.dumps(s, ensure_ascii=False)}")
            continue
        teams.append(team)
        if t == "catalogue":
            if team not in cat:
                problems.append(f"not in the catalogue: {team} (scaffold.py --list)")
        elif t in ("merge", "derive"):
            need = ("seat", "mark", "of") if t == "merge" else ("seat", "mark", "base")
            missing = [k for k in need if not s.get(k)]
            if missing:
                problems.append(f"{team}: a {t} spec needs {', '.join(missing)}")
            elif t == "merge":
                unknown = [m for m in s["of"] if m not in cat]
                if unknown:
                    problems.append(f"{team}: merges seats not in the catalogue: {', '.join(unknown)} (scaffold.py --list)")
                elif len(set(s["of"])) < 2:
                    problems.append(f"{team}: a merge holds at least two seats")
            elif not (SEATS_SRC / s["base"] / "SKILL.md").is_file():
                problems.append(f"{team}: derive base {s['base']} is not a seat rulebook in this setup skill")
        else:
            problems.append(f"{team}: unknown seat type {t!r} (catalogue, merge or derive)")
    twice = sorted({t for t in teams if teams.count(t) > 1})
    if twice:
        problems.append(f"named twice in the plan: {', '.join(twice)}")
    return problems


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


def spec_origin(spec: dict) -> str:
    t = spec.get("type", "catalogue")
    if t == "merge":
        return "merge:" + "+".join(spec["of"])
    if t == "derive":
        return f"derive:{spec['base']}"
    return "catalogue"


def rulebook_text(spec: dict) -> str | None:
    t = spec.get("type", "catalogue")
    if t == "merge":
        return compose_merge(spec["team"], spec["seat"], spec["mark"], spec["of"])
    if t == "derive":
        return compose_derive(spec["team"], spec["seat"], spec["mark"], spec["base"], spec.get("kind", "implementation"),
                              spec.get("reports_to", "CEO"), spec.get("scope", ""), spec.get("register", ""),
                              spec.get("sibling", ""))
    return None


def archives(root: Path, skill: str) -> list[Path]:
    """A skill's archived copies under docs/team/retired/, oldest first (`<skill>`, then `<skill>-<date>[-n]`)."""
    d = root / RETIRED
    rx = re.compile(rf"^{re.escape(skill)}(?:-(\d{{4}}-\d{{2}}-\d{{2}})(?:-(\d+))?)?$")
    found = []
    for p in (d.iterdir() if d.is_dir() else []):
        m = rx.match(p.name)
        if m and p.is_dir():
            found.append(((m.group(1) or "", int(m.group(2) or 1)), p))
    return [p for _, p in sorted(found)]


def archive_path(root: Path, skill: str) -> Path:
    """A free docs/team/retired/<skill>-<date> path, with -2, -3 … when taken."""
    base = root / RETIRED / f"{skill}-{today()}"
    p, n = base, 2
    while p.exists():
        p, n = base.with_name(f"{base.name}-{n}"), n + 1
    return p


def vendor(root: Path, spec: dict, cat: dict, lock: dict, report: list[str]) -> None:
    """Put one seat's rulebook into <root>/.claude/skills and record its origin in the lock (teamlib).

    A folder that already holds a SKILL.md is kept. With a lock entry it keeps that entry and its seated
    date; without one it is recorded with this version's origin when byte-identical to what this version
    would write, else as origin "project" (the project's own: --sync never touches it). A folder that
    already exists with no SKILL.md and no lock entry is the project's too: its files stay, this version's
    rulebook is added beside them, and it is recorded as "project", so --sync never replaces it and a
    retire archives it. A missing folder whose
    lock entry is still there (a repair) is written again and keeps the entry's seated date. A derived seat
    that was retired comes back from its newest archived copy. Nothing is written before the text is composed."""
    t = spec.get("type", "catalogue")
    skill = cat[spec["team"]]["skill"] if t == "catalogue" else f"seat-{spec['team']}"
    dst = root / ".claude" / "skills" / skill
    extra = {} if t == "catalogue" else {"seat": spec["seat"], "mark": spec["mark"]}
    if (dst / "SKILL.md").is_file():
        entry = lock.get(skill)
        if entry:
            report.append(f"kept (exists): .claude/skills/{skill}")
            return
        expected = tree_hash(SEATS_SRC / skill) if t == "catalogue" else text_hash(rulebook_text(spec))
        cur = tree_hash(dst)
        if cur == expected:
            lock[skill] = {"hash": cur, "origin": spec_origin(spec), "seated": today(), **extra}
            report.append(f"kept (exists, same as this version's): .claude/skills/{skill}")
        else:
            lock[skill] = {"hash": cur, "origin": "project", "seated": today(), **extra}
            if t == "merge":
                lock[skill]["of"] = list(spec["of"])
            report.append(f"kept (exists, the project's own; never synced or overwritten): .claude/skills/{skill}")
        return
    if dst.exists() and skill not in lock:  # the project's own folder, without a rulebook: never ours to replace
        own = rulebook_text(spec)
        if own is None:
            for f in sorted(p for p in (SEATS_SRC / skill).rglob("*") if p.is_file()):
                target = dst / f.relative_to(SEATS_SRC / skill)
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, target)
        else:
            (dst / "SKILL.md").write_bytes(own.encode("utf-8"))
        lock[skill] = {"hash": tree_hash(dst), "origin": "project", "seated": today(), **extra}
        if t == "merge":
            lock[skill]["of"] = list(spec["of"])
        report.append(f"kept (exists, the project's own; its files stay, this version's rulebook added beside "
                      f"them; never synced or overwritten): .claude/skills/{skill}")
        return
    seated = (lock.get(skill) or {}).get("seated") or today()  # a repaired seat keeps its seated date
    prior = archives(root, skill)
    if t == "derive" and prior:
        shutil.copytree(prior[-1], dst, dirs_exist_ok=True)
        lock[skill] = {"hash": tree_hash(dst), "origin": spec_origin(spec), "seated": seated, **extra}
        still = AUTHORING_MARK in (dst / "SKILL.md").read_text(encoding="utf-8") if (dst / "SKILL.md").is_file() else False
        report.append(f"restored: .claude/skills/{skill} from {rel(root, prior[-1])} (its newest archived copy"
                      + ("; it still NEEDS AUTHORING)" if still else ")"))
        return
    if t == "catalogue":
        shutil.copytree(SEATS_SRC / skill, dst, dirs_exist_ok=True)
        report.append(f"copied: .claude/skills/{skill}")
    else:
        text = rulebook_text(spec)
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "SKILL.md").write_bytes(text.encode("utf-8"))  # LF everywhere, so tree_hash == text_hash
        if t == "merge":
            report.append(f"composed: .claude/skills/{skill} (holds {', '.join(spec['of'])})")
        else:
            report.append(f"derived: .claude/skills/{skill} from {spec['base']} — NEEDS AUTHORING for its role")
    lock[skill] = {"hash": tree_hash(dst), "origin": spec_origin(spec), "seated": seated, **extra}
    if prior:
        report.append(f"note: an earlier copy of {skill} is archived at {rel(root, prior[-1])}; compare it by hand")


def sync_one(root: Path, skill: str, entry: dict, cat: dict, report: list[str]) -> str:
    """Refresh one seated rulebook. Returns "compared", "own" (derived or the project's own, never synced)
    or "skipped" (reported)."""
    dst = root / ".claude" / "skills" / skill
    origin = entry.get("origin") or "catalogue"
    text = None
    if origin == "catalogue":
        src = SEATS_SRC / skill
        if not src.is_dir():
            report.append(f"not in this version's catalogue: {skill}")
            return "skipped"
        fresh = tree_hash(src)
    elif origin.startswith("merge:"):
        members = [m for m in origin[len("merge:"):].split("+") if m]
        missing = [m for m in members if m not in cat]
        if missing or len(members) < 2:
            report.append(f"not synced: .claude/skills/{skill} (its lock origin {origin} names "
                          f"{', '.join(missing) or 'fewer than two seats'}, not this version's catalogue seats)")
            return "skipped"
        team = skill[len("seat-"):]
        known = MERGES.get(team, {})
        text = compose_merge(team, entry.get("seat") or known.get("seat", team), entry.get("mark") or known.get("mark", "🔗"),
                             members)
        fresh = text_hash(text)
    else:
        if (dst / "SKILL.md").is_file() and AUTHORING_MARK in (dst / "SKILL.md").read_text(encoding="utf-8"):
            report.append(f"still needs authoring: .claude/skills/{skill}")
        return "own"
    if not dst.exists():
        report.append(f"missing, re-created: .claude/skills/{skill}")
    else:
        cur = tree_hash(dst)
        if cur == fresh:
            entry["hash"] = cur
            return "compared"
        if cur != entry.get("hash"):
            report.append(f"kept (edited in this project): .claude/skills/{skill}")
            return "compared"
        shutil.rmtree(dst)
        report.append(f"updated: .claude/skills/{skill}")
    if text is None:
        shutil.copytree(SEATS_SRC / skill, dst)
    else:
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "SKILL.md").write_bytes(text.encode("utf-8"))  # LF everywhere, so tree_hash == text_hash
    entry["hash"] = tree_hash(dst)
    return "compared"


def sync(root: Path, report: list[str]) -> None:
    """Refresh every seated catalogue and merged rulebook the project has not edited. A seated rulebook
    with no lock entry is reported as not tracked; a derived or project-own one is never touched; a bad
    entry is reported and skipped, never fatal. Ends with "all seat rulebooks current" only when every
    seated rulebook was compared and nothing changed."""
    lock = load_lock(root)
    cat = catalogue()
    seated = {r["skill"]: r for r in roster(root / "docs" / "TEAM.md")}
    bad = roster_problems(root / "docs" / "TEAM.md")
    if bad:  # a seat whose row does not parse would read as unseated and its rulebook be left out
        report.extend(["not synced: fix these roster rows in docs/TEAM.md first"] + bad)
        return
    status: dict[str, str] = {}
    for skill in sorted(seated):
        if skill not in lock:
            report.append(f"not tracked: .claude/skills/{skill} (no lock entry, so its edits are unknown; not synced)")
            status[skill] = "untracked"
    for skill, entry in sorted(lock.items()):
        if skill not in seated:
            report.append(f"left alone: {skill} has a lock entry but no roster row")
            continue
        try:
            status[skill] = sync_one(root, skill, entry, cat, report)
        except (OSError, KeyError, ValueError, AttributeError) as e:
            report.append(f"not synced: .claude/skills/{skill} ({e.__class__.__name__}: {e})")
            status[skill] = "skipped"
    save_lock(root, lock)
    compared = [s for s, v in status.items() if v == "compared"]
    own = sorted(s for s, v in status.items() if v == "own")
    if not report and len(compared) == len(seated):
        report.append("all seat rulebooks current")
    else:
        report.append(f"compared {len(compared)} of {len(seated)} seated rulebooks"
                      + (f"; the project's own, never synced: {', '.join(own)}" if own else ""))


# ---------------------------------------------------------------------------- roster edits

def add_rows(team_doc: Path, rows: list[dict[str, str]], report: list[str]) -> None:
    text, nl = read_doc(team_doc)
    present = {r["team"] for r in roster(team_doc)}
    new = [roster_row(r) for r in rows if r["team"] not in present]
    if new:
        text = text.replace("<!-- roster:end -->", "\n".join(new) + "\n<!-- roster:end -->")
        write_doc(team_doc, text, nl)
    report.append(f"roster: added {len(new)} seat(s)")


def drop_roster_row(text: str, team: str) -> tuple[str, bool]:
    """Remove the roster row(s) whose Team cell is `team`, parsed as teamlib.roster parses them."""
    m = ROSTER_RE.search(text)
    if not m:
        return text, False
    kept, removed = [], False
    for line in m.group(1).split("\n"):
        cells = roster_cells(line)
        if cells is not None and len(cells) == 7 and cells[3].strip("`") == team:
            removed = True
            continue
        kept.append(line)
    return text[:m.start(1)] + "\n".join(kept) + text[m.end(1):], removed


def archive_reason(entry: dict | None, skill_dir: Path) -> str | None:
    """Why a retired rulebook is archived rather than deleted; None for an unedited catalogue or merged copy."""
    if entry is None:
        return "not tracked in the lock"
    origin = entry.get("origin") or "catalogue"
    if origin.startswith("derive:"):
        return "derived"
    if origin == "project":
        return "the project's own"
    if tree_hash(skill_dir) != entry.get("hash"):
        return "edited in this project"
    return None


def retire(root: Path, teams: list[str], cat: dict, report: list[str]) -> list[dict[str, str]]:
    """Retire seated teams: roster row out, rulebook deleted or archived (archive_reason), lock entry out,
    brief kept and marked Retired. Returns the rows retired. The caller has already refused retires that
    would leave an ALWAYS role uncovered."""
    team_doc = root / "docs" / "TEAM.md"
    rows = {r["team"]: r for r in roster(team_doc)}
    text, nl = read_doc(team_doc)
    lock = load_lock(root)
    done = []
    for t in teams:
        r = rows.get(t)
        if not r:
            report.append(f"not seated: {seat_name(t, {}, cat)}")
            continue
        text, removed = drop_roster_row(text, t)
        if not removed:
            report.append(f"not retired: {r['mark']} {r['seat']} (its roster row could not be removed; edit docs/TEAM.md by hand)")
            continue
        skill_dir = root / ".claude" / "skills" / r["skill"]
        if skill_dir.exists():
            reason = archive_reason(lock.get(r["skill"]), skill_dir)
            if reason:
                dest = archive_path(root, r["skill"])
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(skill_dir), str(dest))
                report.append(f"archived ({reason}): {rel(root, dest)}")
            else:
                shutil.rmtree(skill_dir)
        lock.pop(r["skill"], None)
        brief = root / "docs" / "team" / f"{t}.md"
        if brief.exists():
            b, bnl = read_doc(brief)
            if not b.startswith("> **Retired"):
                write_doc(brief, f"> **Retired {today()}.** Kept for the record; its work moved as docs/DECISIONS.md says.\n\n" + b, bnl)
        report.append(f"retired: {r['mark']} {r['seat']}")
        done.append(r)
    write_doc(team_doc, text, nl)
    save_lock(root, lock)
    return done


def cell(s: str) -> str:
    """Text safe inside one Markdown table cell."""
    return re.sub(r"\s*\n\s*", " ", s).replace("|", "\\|").strip()


def record_decision(root: Path, question: str, source: str, changed: str, declined: list[str], words: str,
                    report: list[str]) -> str | None:
    """Append one decision row to docs/DECISIONS.md; returns its id ("DEC-n"), or None when there is no file."""
    p = root / "docs" / "DECISIONS.md"
    if not p.exists():
        report.append("not recorded: docs/DECISIONS.md is missing")
        return None
    text, nl = read_doc(p)
    n = max([int(x) for x in re.findall(r"\*\*DEC-(\d+)\*\*", text)] or [0]) + 1
    row = (f"| **DEC-{n}** | {cell(question)} | {cell(source)} | ✅ {today()}: {cell(changed)}. "
           f"Declined: {cell(', '.join(declined)) or 'nothing'}. Owner's words: \"{cell(words)}\" |")
    write_doc(p, text.rstrip() + "\n" + row + "\n", nl)
    report.append(f"recorded: DEC-{n}")
    return f"DEC-{n}"


def record_declined(root: Path, declined: list[dict], decision: str | None, report: list[str]) -> None:
    """Append each declined proposal to docs/team/declined.json (created if absent)."""
    p = root / "docs" / "team" / "declined.json"
    existing = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    for prop in declined:
        existing.append({"key": prop.get("key"), "title": prop.get("title") or prop.get("key"),
                         "action": prop.get("action") or str(prop.get("key", "")).split(":")[0],
                         "signals": list(prop.get("signals") or []), "date": today(), "decision": decision})
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report.append(f"declined: {', '.join(d.get('title') or d.get('key') for d in declined)} (docs/team/declined.json)")


def describe_changes(added: list[dict], retired: list[dict], specs: dict, held_before: dict[str, str],
                     known: dict[str, dict], cat: dict) -> str:
    """What a run changed, in seat names with marks: "seated …; retired …; merged … into …; split … into …"."""
    gone = {r["team"]: r for r in retired}
    used_new, used_old, parts = set(), set(), []
    for r in added:
        spec = specs.get(r["team"], {})
        members = [m for m in spec.get("of", []) if m in gone] if spec.get("type") == "merge" else []
        if members:
            parts.append(f"merged {names(members, known, cat)} into {r['mark']} {r['seat']}")
            used_new.add(r["team"]); used_old.update(members)
    for g in retired:
        parts_of = [r["team"] for r in added if held_before.get(r["team"]) == g["team"] and r["team"] not in used_new]
        if parts_of:
            parts.append(f"split {g['mark']} {g['seat']} into {names(parts_of, known, cat)}")
            used_old.add(g["team"]); used_new.update(parts_of)
    seated = [r["team"] for r in added if r["team"] not in used_new]
    dropped = [g["team"] for g in retired if g["team"] not in used_old]
    lead = []
    if seated:
        lead.append(f"seated {names(seated, known, cat)}")
    if dropped:
        lead.append(f"retired {names(dropped, known, cat)}")
    return "; ".join(lead + parts)


def strip_retired(brief: Path, report: list[str], root: Path) -> None:
    """A seat back in use: remove the `> **Retired …**` line its retirement put at the top of its brief."""
    if not brief.exists():
        return
    text, nl = read_doc(brief)
    new = re.sub(r"\A> \*\*Retired [^\n]*\n(?:\n)?", "", text)
    if new != text:
        write_doc(brief, new, nl)
        report.append(f"back in use, Retired line removed: {rel(root, brief)}")


def carried(root: Path, member: str) -> str | None:
    """A member's brief as a merged seat's brief carries it (Retired line dropped, headings demoted), or None."""
    mb = root / "docs" / "team" / f"{member}.md"
    if not mb.exists():
        return None
    text = re.sub(r"\A> \*\*Retired [^\n]*\n(?:\n)?", "", read_doc(mb)[0])
    return re.sub(r"^#", "###", text, flags=re.M).strip()


def write_briefs(root: Path, project: str, rows: list[dict[str, str]], specs: dict[str, dict], force: bool,
                 report: list[str]) -> None:
    """One brief per row. A merged seat's brief carries each member's brief; when the brief survives from an
    earlier retirement, the member briefs it does not already hold are appended to it. A brief marked
    Retired is never overwritten, even with --force: it is put back in use with its Retired line removed."""
    brief = (TEMPLATES / "seat-brief.md").read_text(encoding="utf-8")
    for r in rows:
        v = {"PROJECT": project, "MARK": r["mark"], "SEAT": r["seat"], "SKILL": r["skill"],
             "REGISTER": r["register"], "REPORTS_TO": r["reports_to"]}
        body = fill(brief, v)
        spec = specs.get(r["team"], {})
        carry = [(m, c) for m in (spec["of"] if spec.get("type") == "merge" else []) for c in [carried(root, m)] if c]
        for m, c in carry:  # carry the members' project facts into the merged seat's brief
            body += f"\n\n## Carried over from the {m} brief\n\n{c}\n"
        if spec.get("type") == "derive" and spec.get("scope"):
            body = body.replace("- **Paths:** _(", f"- **Scope:** {spec['scope']}\n- **Paths:** _(", 1)
        path = root / "docs" / "team" / f"{r['team']}.md"
        kept_for_record = path.exists() and read_doc(path)[0].startswith("> **Retired")
        if kept_for_record or not write(path, body, force, report):
            if kept_for_record:
                report.append(f"kept (retired brief, never overwritten): {rel(root, path)}")
            strip_retired(path, report, root)
            text, nl = read_doc(path)
            missing = [(m, c) for m, c in carry if c not in text]
            if missing:
                text = text.rstrip("\n") + "".join(f"\n\n## Carried over from the {m} brief ({today()})\n\n{c}\n"
                                                  for m, c in missing)
                write_doc(path, text, nl)
                report.append(f"carried into {rel(root, path)}: the {', '.join(m for m, _ in missing)} brief(s)")


def write_registers(root: Path, project: str, cos_seated: bool, report: list[str]) -> None:
    """docs/team/tracker.md and owner-questions.md, on every run, never overwritten (not even with --force):
    kept by the Chief of Staff, or by the CEO while no Chief of Staff is seated."""
    for name in ("tracker.md", "owner-questions.md"):
        body = fill((TEMPLATES / name).read_text(encoding="utf-8"), {"PROJECT": project})
        if not cos_seated:
            body = re.sub(r"\*\*Kept by the [^*\n]+\*\*", lambda _: CEO_KEEPS, body, count=1)
        path = root / "docs" / "team" / name
        if not path.exists():
            write(path, body, False, report)


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
    res = subprocess.run([sys.executable, str(gen_dst)], cwd=root, capture_output=True, text=True, encoding="utf-8")
    report.append((res.stdout + res.stderr).strip())
    pending = [p.parent.relative_to(root).as_posix() for p in (root / ".claude" / "skills").glob("seat-*/SKILL.md")
               if AUTHORING_MARK in p.read_text(encoding="utf-8")]
    for p in pending:
        report.append(f"NEEDS AUTHORING: {p}/SKILL.md (rewrite for its role per references/seat-contract.md)")
    return res.returncode


# ---------------------------------------------------------------------------- main

def choose_plan(plan_data: dict, only: str | None, ap: argparse.ArgumentParser) -> tuple[list, list, list]:
    """(seat specs, retire list, declined proposals) for this run. With --only, the named proposals' seats
    and retires and every other proposal declined; otherwise the plan's top-level seats and retire."""
    proposals = plan_data.get("proposals")
    if only is None:
        return list(plan_data.get("seats") or []), list(dict.fromkeys(plan_data.get("retire") or [])), []
    if not isinstance(proposals, list) or (not proposals and only.strip() != "none"):
        ap.error("--only needs a plan that carries proposals (a re-evaluation plan from reevaluate.py)")
    keys = [k.strip() for k in only.split(",") if k.strip()]
    if not keys:
        ap.error("--only names no proposal: pass proposal keys, or 'none' to apply nothing")
    keys = [] if keys == ["none"] else keys
    known = [p.get("key") for p in proposals]
    unknown = [k for k in keys if k not in known]
    if unknown:
        ap.error(f"not a proposal in this plan: {', '.join(unknown)} (its proposals: {', '.join(map(str, known))})")
    chosen = [p for p in proposals if p.get("key") in keys]
    seats, retire = [], []
    for p in chosen:
        for s in p.get("seats") or []:
            if s.get("team") not in {x.get("team") for x in seats}:
                seats.append(s)
        retire += [t for t in p.get("retire") or [] if t not in retire]
    return seats, retire, [p for p in proposals if p.get("key") not in keys]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path)
    ap.add_argument("--plan", type=Path, help="a plan from plan.py or reevaluate.py")
    ap.add_argument("--only", help="with --plan: apply only these proposal keys (comma-separated), or 'none'")
    ap.add_argument("--project")
    ap.add_argument("--seats", help="comma-separated catalogue teams (shorthand for a plan)")
    ap.add_argument("--add", help="comma-separated catalogue teams to add")
    ap.add_argument("--retire", help="comma-separated teams to retire")
    ap.add_argument("--sync", action="store_true", help="refresh every rulebook the project has not edited")
    ap.add_argument("--record", help="the owner's words approving this change; recorded as a decision")
    ap.add_argument("--question", help="the question the owner answered; the decision row's Question cell")
    ap.add_argument("--owner-acts", default="publishing, sending, spending, signing")
    ap.add_argument("--push-rule", default=PUSH_RULE)
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing files (never a retired brief, the tracker or owner questions), "
                         "and seat a role a seated seat already holds")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    cat = catalogue()
    if a.list:
        for r in cat.values():
            print(f"{r['mark']} {r['team']:<17} {r['seat']:<32} {r['kind']:<15} seat it when: {r['when']}")
        return 0
    if not a.root:
        ap.error("--root is required")
    if a.only is not None and not a.plan:
        ap.error("--only needs --plan")
    root = a.root.resolve()
    team_doc = root / "docs" / "TEAM.md"
    report: list[str] = []

    if a.sync:
        if not team_doc.is_file():
            ap.error("--sync needs an existing docs/TEAM.md")
        sync(root, report)
        print("\n".join(report))
        return 0

    plan_data: dict = json.loads(a.plan.read_text(encoding="utf-8")) if a.plan else {}
    seats, retiring, declined = choose_plan(plan_data, a.only, ap)
    for t in (a.seats or "").split(",") + (a.add or "").split(","):
        if t.strip() and t.strip() not in {s.get("team") for s in seats}:
            seats.append({"team": t.strip(), "type": "catalogue", "why": "named on the command line"})
    for t in (a.retire or "").split(","):
        if t.strip() and t.strip() not in retiring:
            retiring.append(t.strip())
    problems = validate_specs(seats, cat)
    declined_file = root / "docs" / "team" / "declined.json"
    if declined and declined_file.exists():
        try:
            if not isinstance(json.loads(declined_file.read_text(encoding="utf-8")), list):
                problems.append("docs/team/declined.json is not a JSON list")
        except ValueError as e:
            problems.append(f"docs/team/declined.json does not parse: {e}")
    if problems:
        ap.error("nothing was changed:\n" + "\n".join(problems))

    fresh = not team_doc.is_file()
    if not fresh:
        problems += roster_problems(team_doc)
    both = [t for t in retiring if t in {s.get("team") for s in seats}]
    if both:
        problems.append(f"named to seat and to retire in the same run: {names(both, {}, cat)}")
    if problems:
        ap.error("nothing was changed:\n" + "\n".join(problems))
    project = a.project or plan_data.get("project") or project_name(root)
    if fresh:
        if not seats:
            ap.error("a first setup needs --plan or --seats")
        teams = {s["team"] for s in seats} | {m for s in seats if s.get("type") == "merge" for m in s["of"]}
        for t in ALWAYS:
            if t not in teams:
                seats.insert(0, {"team": t, "type": "catalogue", "why": "every team keeps it"})
                report.append(f"added {cat[t]['mark']} {cat[t]['seat']}: every team keeps it")
    specs = {s["team"]: s for s in seats}
    order = list(cat)
    rows = sorted((spec_row(s, cat) for s in seats),
                  key=lambda r: (order.index(r["team"]) if r["team"] in order else len(order), r["team"]))

    # ------------------------------------------------ check the change against the seated team, before writing
    lock = load_lock(root)
    cur_rows = [] if fresh else roster(team_doc)
    seated_teams = {r["team"] for r in cur_rows}
    new_rows = [r for r in rows if r["team"] not in seated_teams]
    known = {**{r["team"]: r for r in cur_rows}, **{r["team"]: r for r in new_rows}}
    planned = dict(lock)
    for r in new_rows:
        planned[r["skill"]] = {"origin": spec_origin(specs[r["team"]])}
    cur_cov = coverage(root, cur_rows, lock)

    # The retire list first, by the rules retire() applies, so no check below counts a seat as gone
    # before its retire is known to go ahead: it must be seated (a row of its own), and it may not leave
    # the CEO or the Bar Raiser held by no seat. A refused retire keeps its seat, which only adds
    # coverage, so the ALWAYS rule is applied until nothing more is refused.
    retire_ok = []
    for t in retiring:
        if t in seated_teams:
            retire_ok.append(t)
        elif cur_cov.get(t):
            report.append(f"not seated on its own: {seat_name(t, known, cat)} (held by {seat_name(cur_cov[t], known, cat)})")
        else:
            report.append(f"not seated: {seat_name(t, known, cat)}")
    while True:
        post_cov = coverage(root, [r for r in cur_rows if r["team"] not in retire_ok] + new_rows, planned)
        lost_by = {t: [x for x in ALWAYS if cur_cov.get(x) == t and x not in post_cov] for t in retire_ok}
        refused = [t for t in retire_ok if lost_by[t]]
        if not refused:
            break
        for t in refused:
            retire_ok.remove(t)
            lost = lost_by[t]
            if t in ALWAYS:
                hint = ("; to retire it, seat a merged seat that holds it in the same plan"
                        if any(t in m["of"] for m in MERGES.values()) else "")
                report.append(f"not retired: {seat_name(t, known, cat)}: every team keeps one{hint}")
            else:
                report.append(f"not retired: {seat_name(t, known, cat)}: it holds {names(lost, known, cat)}, and "
                              f"every team keeps one; to retire it, seat {names(lost, known, cat)} in the same plan")
    gone = set(retire_ok)

    def holders(role: str) -> list[str]:
        """Every seated team holding `role` now: itself, a merged seat holding it, a frontend split."""
        return [x["team"] for x in cur_rows if x["team"] == role
                or role in merge_members(x["team"], x["skill"], lock)
                or (role == "frontend" and covers_frontend(x["team"], x["skill"], lock))]

    conflicts, claimed = [], {}
    for r in new_rows:
        for role in [r["team"]] + merge_members(r["team"], r["skill"], planned):
            live = [h for h in holders(role) if h != r["team"] and h not in gone]
            merged = [h for h in live if h != role and role in merge_members(h, known[h]["skill"], lock)]
            split = [h for h in live if h != role and h not in merged]
            if role in live:
                conflicts.append(f"{r['mark']} {r['seat']} would hold {seat_name(role, known, cat)}, which is "
                                 "seated on its own; retire it in the same plan, or pass --force")
            for h in merged:
                conflicts.append(f"{seat_name(role, known, cat)} is held by {seat_name(h, known, cat)}; "
                                 "unmerge it with a re-evaluation, or pass --force")
            overflow = (role == "frontend" and r["team"] == "frontend"
                        and str(specs.get("frontend", {}).get("why", "")).startswith(FRONTEND_HOLDS))
            if split and not overflow:  # the Frontend engineer may hold the UI apps no split holds
                conflicts.append(f"{seat_name(role, known, cat)} is covered by its split seats "
                                 f"{names(split, known, cat)}; retire them in the same plan, or pass --force")
            if claimed.get(role, r["team"]) != r["team"]:
                conflicts.append(f"{seat_name(role, known, cat)} would be held by both "
                                 f"{seat_name(claimed[role], known, cat)} and {r['mark']} {r['seat']}; pass --force to allow it")
            claimed.setdefault(role, r["team"])
    marks = {r["mark"].replace(VS16, ""): r for r in cur_rows if r["team"] not in gone}
    mark_clashes = []
    for r in new_rows:
        other = marks.get(r["mark"].replace(VS16, ""))
        if other:
            mark_clashes.append(f"{r['mark']} {r['seat']}: the mark {r['mark']} is already {other['mark']} "
                                f"{other['seat']}'s; give the new seat a mark no seated seat uses")
        marks[r["mark"].replace(VS16, "")] = r
    if mark_clashes or (conflicts and not a.force):
        refusals = [line for line in report if line.startswith("not retired: ")]  # why a seat is still held
        ap.error("nothing was changed:\n" + "\n".join(refusals + mark_clashes + ([] if a.force else conflicts)))

    held_before = {role: holder for role, holder in cur_cov.items() if role != holder}

    # ------------------------------------------------ write
    repair = [r for r in cur_rows if r["team"] in specs and r["team"] not in retiring and (
        not (root / ".claude" / "skills" / r["skill"] / "SKILL.md").is_file()
        or not (root / "docs" / "team" / f"{r['team']}.md").is_file() or r["skill"] not in lock)]
    for r in repair:
        report.append(f"repairing {r['mark']} {r['seat']}: seated, but its rulebook, brief or lock entry is missing")
    if fresh:
        values = {"PROJECT": project, "DATE": today(),
                  "ROSTER_ROWS": "\n".join(roster_row(r) for r in rows),
                  "OWNER_ACTS": plan_data.get("owner_acts", a.owner_acts),
                  "PUSH_RULE": plan_data.get("push_rule", a.push_rule)}
        values.update({f"TIER_{k.upper()}": v for k, v in TIER_LABELS.items()})
        write(team_doc, fill((TEMPLATES / "TEAM.md").read_text(encoding="utf-8"), values), a.force, report)
        write(root / "docs" / "DECISIONS.md", fill((TEMPLATES / "DECISIONS.md").read_text(encoding="utf-8"), values),
              a.force, report)
    else:
        add_rows(team_doc, new_rows, report)
    for r in new_rows + repair:
        vendor(root, specs.get(r["team"], {"team": r["team"], "type": "catalogue"}), cat, lock, report)
    save_lock(root, lock)
    write_briefs(root, project, new_rows + repair, specs, a.force, report)
    retired = retire(root, retire_ok, cat, report) if retire_ok else []
    write_registers(root, project, "chief-of-staff" in coverage(root), report)

    changed = describe_changes(new_rows, retired, specs, held_before, known, cat)
    decision = None
    if not changed and not declined:
        report.append("nothing changed; no decision recorded")
    elif a.record:
        plan_path = a.plan.resolve() if a.plan else None
        source = ("named by the owner" if plan_path is None else plan_path.relative_to(root).as_posix()
                  if root in plan_path.parents else plan_path.name)  # never a path outside the project
        question = a.question or ("Team change" if a.plan else "Team change named by the owner")
        decision = record_decision(root, question, source, changed or "nothing changed",
                                   [p.get("title") or p.get("key") for p in declined], a.record, report)
    if declined:
        record_declined(root, declined, decision, report)
    rc = finish(root, project, a.force, report)
    print("\n".join(report))
    return rc


if __name__ == "__main__":
    sys.exit(main())
