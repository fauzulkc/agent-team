"""Shared definitions for team-setup's scripts: the catalogue, the merge groups, and roles to derive.

Standard library only. Imported by plan.py, seatgen.py, scaffold.py and reevaluate.py.
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


def roster(team_doc: Path) -> list[dict[str, str]]:
    """The roster rows of a project's docs/TEAM.md."""
    text = team_doc.read_text(encoding="utf-8")
    m = re.search(r"<!-- roster:start -->(.*?)<!-- roster:end -->", text, re.S)
    rows = []
    for line in (m.group(1) if m else "").strip().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0] in ("Mark", "") or set(cells[0]) <= {"-"}:
            continue
        mark, seat, skill, team, kind, register, reports_to = cells
        rows.append(dict(mark=mark, seat=seat, skill=skill.strip("`"), team=team.strip("`"), kind=kind,
                         register=register, reports_to=reports_to))
    return rows


def roster_row(r: dict[str, str]) -> str:
    return (f"| {r['mark']} | {r['seat']} | `{r['skill']}` | `{r['team']}` | {r['kind']} | "
            f"{r['register']} | {r['reports_to']} |")


def load_lock(root: Path) -> dict[str, dict]:
    p = root / "docs" / "team" / "seat-skills.lock"
    raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {k: (v if isinstance(v, dict) else {"hash": v, "origin": "catalogue"}) for k, v in raw.items()}


def save_lock(root: Path, lock: dict[str, dict]) -> None:
    p = root / "docs" / "team" / "seat-skills.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def members_covered(lock: dict[str, dict]) -> set[str]:
    """Catalogue teams already held inside a merged seat (from the lock's origins)."""
    out: set[str] = set()
    for v in lock.values():
        origin = v.get("origin", "")
        if origin.startswith("merge:"):
            out |= set(origin[len("merge:"):].split("+"))
    return out
