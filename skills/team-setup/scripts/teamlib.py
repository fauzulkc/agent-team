"""Shared definitions for team-setup's scripts: the catalogue, the merge groups, and roles to derive.

Standard library only. Imported by plan.py, seatgen.py, scaffold.py and reevaluate.py.

The lock, docs/team/seat-skills.lock, is JSON: {skill: {"hash", "origin", "seated", ...}}. `origin` is
`catalogue`, `merge:<a>+<b>[+<c>]`, `derive:<base skill>` or `project` (the folder existed before scaffold
seated it: the project's own copy, never synced, archived on retire). `seated` is the ISO date the row was
first seated. Merged and derived entries also carry `seat` and `mark`; a `project` entry for a merged seat
carries `of`, the teams it holds. coverage() answers which seated team holds each role.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CATALOGUE = SKILL / "references" / "seats.md"
SEATS_SRC = SKILL / "seats"

ALWAYS = ("ceo", "bar-raiser")
CHECK_SEATS = {"bar-raiser", "scope-trimmer", "user", "security"}

# A merge puts several seats in one session for a small project. Members that are not in the set are
# simply absent; a merge needs at least two members present. Check seats never merge with a builder.
MERGES = {
    "growth": {"seat": "Growth", "mark": "📈", "of": ["sales", "seo", "social"], "kind": "director",
               "why": "one seat owns words, reach and the channels while the audience is small"},
    "product-design": {"seat": "Product & Design", "mark": "🎨", "of": ["product", "design"], "kind": "director",
                       "why": "one seat decides what to build and how it looks while the surface is small"},
    "engineering-platform": {"seat": "Engineering & Platform", "mark": "🔧", "of": ["engineering", "platform"],
                             "kind": "director", "why": "one seat builds and ships while there is one deploy target"},
    "quality": {"seat": "Quality", "mark": "🛡️", "of": ["testing", "bar-raiser"], "kind": "check",
                "why": "one independent check owns the test standard and re-measures finished work"},
    "money": {"seat": "Money", "mark": "💰", "of": ["funding", "payments"], "kind": "director",
              "why": "one seat tracks where money comes from and how it is received"},
    "legal-compliance": {"seat": "Legal & Compliance", "mark": "📜", "of": ["payments", "compliance"],
                         "kind": "director", "why": "one seat holds the legal pages, licences and personal data"},
    "data-ml": {"seat": "Data & ML", "mark": "🧮", "of": ["data", "ml"], "kind": "director",
                "why": "one seat owns the pipelines and the models built on them while both are young"},
    "customer": {"seat": "Customer", "mark": "🫱", "of": ["customer-success", "community"], "kind": "director",
                 "why": "one seat champions users and contributors while there are few of either"},
}

# Roles no catalogue seat covers, raised by scan signals. Each is derived from a base rulebook and
# then authored for its role (seat-contract.md); never shipped unauthored.
DERIVED_ROLES = {
    "hardware": {"team": "hardware", "seat": "Hardware & firmware engineer", "mark": "🔌", "kind": "implementation",
                 "base": "seat-mobile", "register": "firmware, board files and the device test bench",
                 "reports_to": "Engineering",
                 "scope": "firmware and board design: a shipped device can't be patched like a web page"},
    "blockchain": {"team": "contracts", "seat": "Smart-contract engineer", "mark": "⛓️", "kind": "implementation",
                   "base": "seat-security", "register": "contracts, deploy scripts and audits",
                   "reports_to": "Engineering",
                   "scope": "on-chain code: every deployment is a one-way door, audits before mainnet"},
    "desktop": {"team": "desktop", "seat": "Desktop engineer", "mark": "🖱️", "kind": "implementation",
                "base": "seat-mobile", "register": "the desktop app code, installers and auto-update",
                "reports_to": "Engineering",
                "scope": "the desktop app: signed installers and auto-update are one-way doors"},
    "extension": {"team": "extension", "seat": "Browser-extension engineer", "mark": "🧷", "kind": "implementation",
                  "base": "seat-frontend", "register": "the extension code, manifest and store listing",
                  "reports_to": "Engineering",
                  "scope": "the browser extension: permissions and store review decide what ships"},
}

MARK_RE = re.compile(r"^\S+")


def catalogue() -> dict[str, dict[str, str]]:
    """team -> row (mark, seat, skill, team, kind, register, reports_to, when), in catalogue order."""
    rows: dict[str, dict[str, str]] = {}
    for line in CATALOGUE.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 8 or cells[0] in ("Mark", "") or set(cells[0]) <= {"-"}:
            continue
        mark, seat, skill, team, kind, register, reports_to, when = cells
        team = team.strip("`")
        rows[team] = dict(mark=mark, seat=seat, skill=skill.strip("`"), team=team, kind=kind,
                          register=register, reports_to=reports_to, when=when)
    return rows


ROSTER_RE = re.compile(r"<!-- roster:start -->(.*?)<!-- roster:end -->", re.S)
CELL_SPLIT = re.compile(r"(?<!\\)\|")


def roster_cells(line: str) -> list[str] | None:
    """The stripped cells of one table line, split on unescaped pipes only (an escaped `\\|` stays in its
    cell). None for a line that is not a table row, the header row, or the separator row."""
    body = line.strip()
    if not body.startswith("|"):
        return None
    body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells = [c.strip() for c in CELL_SPLIT.split(body)]
    if not cells or cells[0] in ("Mark",) or all(set(c) <= set("-: ") for c in cells):
        return None
    return cells


def roster_problems(team_doc: Path) -> list[str]:
    """Lines between the roster markers that look like table rows but do not parse to seven cells."""
    text = team_doc.read_text(encoding="utf-8")
    m = ROSTER_RE.search(text)
    out = []
    for line in (m.group(1) if m else "").strip().splitlines():
        cells = roster_cells(line)
        if cells is not None and len(cells) != 7:
            out.append(f"roster row has {len(cells)} cells, not 7: {line.strip()}")
    return out


def roster(team_doc: Path) -> list[dict[str, str]]:
    """The roster rows of a project's docs/TEAM.md. Cells split on unescaped pipes; a row that does not
    parse to seven cells is left out here and named by roster_problems()."""
    text = team_doc.read_text(encoding="utf-8")
    m = ROSTER_RE.search(text)
    rows = []
    for line in (m.group(1) if m else "").strip().splitlines():
        cells = roster_cells(line)
        if cells is None or len(cells) != 7 or cells[0] == "":
            continue
        mark, seat, skill, team, kind, register, reports_to = cells
        rows.append(dict(mark=mark, seat=seat, skill=skill.strip("`"), team=team.strip("`"), kind=kind,
                         register=register, reports_to=reports_to))
    return rows


def roster_row(r: dict[str, str]) -> str:
    return (f"| {r['mark']} | {r['seat']} | `{r['skill']}` | `{r['team']}` | {r['kind']} | "
            f"{r['register']} | {r['reports_to']} |")


def load_lock(root: Path) -> dict[str, dict]:
    """docs/team/seat-skills.lock as {skill: {"hash", "origin", "seated"}}. A legacy bare-hash entry reads as
    a catalogue copy with no seated date; an entry with no `seated` key gets `seated: None`; an earlier
    build's `merge:project` or `derive:project` origin reads as `project`."""
    p = root / "docs" / "team" / "seat-skills.lock"
    raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    out: dict[str, dict] = {}
    for k, v in raw.items():
        entry = dict(v) if isinstance(v, dict) else {"hash": v, "origin": "catalogue"}
        entry.setdefault("origin", "catalogue")
        if str(entry["origin"]).endswith(":project"):  # an earlier build's `merge:project` / `derive:project`
            entry["origin"] = "project"
        entry.setdefault("seated", None)
        out[k] = entry
    return out


def save_lock(root: Path, lock: dict[str, dict]) -> None:
    p = root / "docs" / "team" / "seat-skills.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_members(team: str, skill: str, lock: dict[str, dict]) -> list[str]:
    """The catalogue teams a seated merged seat holds: from its lock origin `merge:a+b`; for a merged seat
    the project already had (origin `project`), from the entry's `of` list when scaffold recorded one;
    else from MERGES[team]["of"] when its skill is `seat-<team>`. Empty for a seat that is not a merge."""
    entry = lock.get(skill) or {}
    origin = entry.get("origin") or ""
    if origin.startswith("merge:"):
        return [m for m in origin[len("merge:"):].split("+") if m]
    if isinstance(entry.get("of"), list) and entry["of"]:
        return [str(m) for m in entry["of"]]
    if team in MERGES and skill == f"seat-{team}":
        return list(MERGES[team]["of"])
    return []


def covers_frontend(team: str, skill: str, lock: dict[str, dict]) -> bool:
    """A seated derive whose base is seat-frontend (lock `derive:seat-frontend`, or a `frontend-*` team)."""
    origin = (lock.get(skill) or {}).get("origin") or ""
    return origin == "derive:seat-frontend" or team.startswith("frontend-")


def coverage(root: Path, rows: list[dict[str, str]] | None = None,
             lock: dict[str, dict] | None = None) -> dict[str, str]:
    """Every role team that is held, mapped to the seated team holding it. A seated team maps to itself;
    each member of a seated merged seat maps to the merged team (merge_members); a seated derive of
    seat-frontend also covers `frontend`. A team seated in its own right wins over a merge holding it.
    `rows` and `lock` default to the project's roster and lock."""
    root = Path(root)
    if rows is None:
        doc = root / "docs" / "TEAM.md"
        rows = roster(doc) if doc.exists() else []
    if lock is None:
        lock = load_lock(root)
    out: dict[str, str] = {}
    for r in rows:
        for member in merge_members(r["team"], r["skill"], lock):
            out.setdefault(member, r["team"])
        if covers_frontend(r["team"], r["skill"], lock):
            out.setdefault("frontend", r["team"])
    for r in rows:
        out[r["team"]] = r["team"]
    return out


def members_covered(lock: dict[str, dict]) -> set[str]:
    """Catalogue teams already held inside a merged seat, from the lock alone (`merge:` origins, and the
    `of` list of a merged seat the project already had). coverage() is the full answer, roster included."""
    out: set[str] = set()
    for v in lock.values():
        origin = v.get("origin", "")
        if origin.startswith("merge:"):
            out |= set(origin[len("merge:"):].split("+"))
        elif isinstance(v.get("of"), list):
            out |= set(v["of"])
    return out


def project_name(root: Path) -> str:
    """docs/team/plan.json's project, else docs/TEAM.md's title line, else the folder name."""
    try:
        plan = json.loads((root / "docs" / "team" / "plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        plan = {}
    if isinstance(plan, dict) and isinstance(plan.get("project"), str) and plan["project"].strip():
        return plan["project"].strip()
    doc = root / "docs" / "TEAM.md"
    text = doc.read_text(encoding="utf-8") if doc.is_file() else ""
    for rx in (r"^#\s*Team:\s*(.+?)\s*$", r"^#\s*(.+?)\s+team\s*$", r"Internal working instrument for (.+?)\.\*\*"):
        m = re.search(rx, text, re.M | re.I)
        if m and "{{" not in m.group(1):
            return m.group(1).strip()
    return root.name
