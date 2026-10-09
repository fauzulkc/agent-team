#!/usr/bin/env python3
"""Re-evaluate a seated team: how it actually works, against what the repo needs now.

    reevaluate.py --root <project> [--days 30]                  print the report (markdown)
    reevaluate.py --root <project> --json                        print the measurements and proposals
    reevaluate.py --root <project> --out docs/team/reevaluation.json   also write the proposed plan

Measures, per seated team, over the window: commits whose subject starts with the seat's prefix
(`design:`, `design(web):`), worker run logs written, inbox lines waiting, and tracker lines where the
seat is BLOCKED. Re-scans the repo and diffs the signals against docs/team/scan.json (the setup
baseline). Then proposes, each with its evidence:
  add     a seat the evidence now calls for that no seated seat covers
  retire  a seat with no activity in the window and no signal that calls for it
  merge   two or more quiet seats that one session can hold
  unmerge a merged seat whose work now dominates the team
  split   a frontend seat per UI app once the project is large
The proposed plan (`seats` to add, `retire`) is what `scaffold.py --plan` applies after the owner says yes.
Nothing here changes the project. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan as planner  # noqa: E402
from scan import scan as run_scan  # noqa: E402
from teamlib import ALWAYS, CHECK_SEATS, MERGES, catalogue, load_lock, roster  # noqa: E402

PREFIX_RE = re.compile(r"^([a-z][a-z0-9-]*)(?:\([^)]*\))?:\s")
LOW_COMMITS, LOW_RUNS = 2, 2           # a seat at or under both is "quiet" in the window
DOMINANT_SHARE, DOMINANT_MIN = 0.30, 10  # a merged seat over both has outgrown the merge


def git_subjects(root: Path, days: int) -> list[tuple[str, str]]:
    try:
        out = subprocess.run(["git", "-C", str(root), "log", f"--since={days} days ago", "--format=%as\t%s"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [tuple(l.split("\t", 1)) for l in out.splitlines() if "\t" in l]


def aliases(row: dict) -> set[str]:
    seat = row["seat"].lower()
    out = {row["team"], row["skill"][len("seat-"):] if row["skill"].startswith("seat-") else row["skill"],
           re.sub(r"[^a-z0-9]+", "-", seat).strip("-"), seat.split()[0].strip("&,")}
    return {a for a in out if a}


def measure(root: Path, rows: list[dict], days: int) -> dict:
    since = datetime.date.today() - datetime.timedelta(days=days)
    by_alias = {}
    for r in rows:
        for a in aliases(r):
            by_alias.setdefault(a, r["team"])
    stats = {r["team"]: {"commits": 0, "runs": 0, "inbox": 0, "blocked": 0, "last": None} for r in rows}
    unattributed = 0
    for date, subject in git_subjects(root, days):
        m = PREFIX_RE.match(subject)
        team = by_alias.get(m.group(1)) if m else None
        if team:
            st = stats[team]
            st["commits"] += 1
            st["last"] = max(st["last"] or date, date)
        else:
            unattributed += 1
    for r in rows:
        st = stats[r["team"]]
        runs = root / "scratchpad" / "team" / "runs" / r["team"]
        if runs.is_dir():
            for f in runs.rglob("*"):
                if f.is_file() and datetime.date.fromtimestamp(f.stat().st_mtime) >= since:
                    st["runs"] += 1
                    d = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
                    st["last"] = max(st["last"] or d, d)
        inbox = root / "scratchpad" / "team" / "inbox" / f"{r['team']}.md"
        if inbox.is_file():
            st["inbox"] = sum(1 for l in inbox.read_text(encoding="utf-8").splitlines() if l.strip())
    tracker = root / "docs" / "team" / "tracker.md"
    if tracker.is_file():
        for line in tracker.read_text(encoding="utf-8").splitlines():
            if "BLOCKED" not in line:
                continue
            for r in rows:
                if r["seat"] in line or r["mark"] in line:
                    stats[r["team"]]["blocked"] += 1
    total = sum(s["commits"] for s in stats.values())
    return {"days": days, "stats": stats, "attributed": total, "unattributed": unattributed}


def evaluate(root: Path, days: int) -> dict:
    team_doc = root / "docs" / "TEAM.md"
    rows = roster(team_doc)
    seated = {r["team"] for r in rows}
    lock = load_lock(root)
    merged_members = {}
    for r in rows:
        origin = lock.get(r["skill"], {}).get("origin", "")
        if origin.startswith("merge:"):
            merged_members[r["team"]] = origin[len("merge:"):].split("+")
        elif r["team"] in MERGES and r["skill"] == f"seat-{r['team']}":
            merged_members[r["team"]] = MERGES[r["team"]]["of"]
    covered = seated | {m for ms in merged_members.values() for m in ms}

    fresh = run_scan(root)
    base_path = root / "docs" / "team" / "scan.json"
    baseline = json.loads(base_path.read_text(encoding="utf-8")) if base_path.is_file() else {"signals": {}}
    new_signals = sorted(set(fresh["signals"]) - set(baseline.get("signals", {})))
    gone_signals = sorted(set(baseline.get("signals", {})) - set(fresh["signals"])) if base_path.is_file() else []
    core, opt, derived = planner.needs(fresh)
    activity = measure(root, rows, days)
    stats = activity["stats"]
    cat = catalogue()
    proposals: list[dict] = []
    notes: list[str] = []
    retired = {p.stem for p in (root / "docs" / "team").glob("*.md")
               if p.read_text(encoding="utf-8").startswith("> **Retired")}

    # add: what the size-scaled recommendation calls for that nothing seated covers
    recommended = planner.build(fresh, "recommended")
    for spec in recommended:
        teams = spec["of"] if spec.get("type") == "merge" else [spec["team"]]
        for t in teams:
            if t in covered or t in ("chief-of-staff", "scope-trimmer"):
                continue
            why = core.get(t) or spec.get("why", "")
            sig = why.split(":")[0]
            if t in retired and sig not in new_signals:
                notes.append(f"{cat.get(t, {}).get('seat', t)} was retired; its signal ({why}) is unchanged since "
                             "setup, so it is not proposed again")
                continue
            add = {"team": t, "type": "catalogue", "why": why} if t in cat else spec
            proposals.append({"action": "add", "spec": add,
                              "why": why + (" (new since setup)" if sig in new_signals else "")})
            covered.add(t)
    n_after = len(rows) + sum(1 for p in proposals if p["action"] == "add")
    for t, threshold in (("chief-of-staff", 5), ("scope-trimmer", 10)):
        if t not in covered and n_after >= threshold and t not in retired:
            proposals.append({"action": "add", "spec": {"team": t, "type": "catalogue", "why": f"{n_after} seats"},
                              "why": f"the team would have {n_after} seats"})

    # retire: idle in the window, and nothing calls for it any more
    needed = set(core) | set(opt)
    for r in rows:
        t, st = r["team"], stats[r["team"]]
        if t in ALWAYS or st["commits"] or st["runs"] or st["inbox"]:
            continue
        members = merged_members.get(t, [t])
        if any(m in needed for m in members):
            continue
        if t == "chief-of-staff" and len(rows) >= 5:
            continue
        proposals.append({"action": "retire", "team": t,
                          "why": f"no commits, runs or inbox traffic in {days} days, and no repo signal calls for it"})

    # merge: two or more quiet seats one session can hold
    quiet = {t for t, st in stats.items() if st["commits"] <= LOW_COMMITS and st["runs"] <= LOW_RUNS and not st["blocked"]}
    retiring = {p["team"] for p in proposals if p["action"] == "retire"}
    for team, m in MERGES.items():
        present = [t for t in m["of"] if t in seated and t not in merged_members and t not in retiring]
        if team in seated or len(present) < 2 or not all(t in quiet for t in present):
            continue
        if any(t in CHECK_SEATS for t in present) and m["kind"] != "check":
            continue
        proposals.append({"action": "merge", "spec": {"team": team, "type": "merge", "of": present, "seat": m["seat"],
                                                     "mark": m["mark"], "kind": m["kind"], "why": m["why"]},
                          "retire": present,
                          "why": f"{', '.join(present)} were all quiet ({days} days: " +
                                 "; ".join(f"{t} {stats[t]['commits']} commits, {stats[t]['runs']} runs" for t in present) + ")"})

    # unmerge: a merged seat that now carries the team
    total = max(activity["attributed"], 1)
    for t, members in merged_members.items():
        st = stats.get(t, {"commits": 0})
        if st["commits"] >= DOMINANT_MIN and st["commits"] / total >= DOMINANT_SHARE:
            proposals.append({"action": "unmerge", "team": t,
                              "spec": [{"team": m, "type": "catalogue", "why": f"split out of {t}"} for m in members if m in cat],
                              "why": f"{st['commits']} of {total} attributed commits ({st['commits'] / total:.0%}) in {days} days"})

    # split: one frontend seat per UI app when the project is large
    if planner.size_class(fresh) == "large" and "frontend" in seated:
        splits = planner.ui_splits(fresh)
        if splits:
            proposals.append({"action": "split", "team": "frontend", "spec": splits,
                              "why": splits[0]["why"] + "; the project is large"})

    return {"project": root.name, "date": datetime.date.today().isoformat(), "days": days,
            "size": planner.size_class(fresh), "seated": [r["team"] for r in rows],
            "names": {r["team"]: f"{r['mark']} {r['seat']}" for r in rows}, "notes": notes,
            "new_signals": new_signals, "gone_signals": gone_signals, "activity": activity,
            "proposals": proposals, "fresh_scan": fresh}


def to_plan(result: dict) -> dict:
    seats, retire = [], []
    for p in result["proposals"]:
        if p["action"] == "add":
            seats.append(p["spec"])
        elif p["action"] == "retire":
            retire.append(p["team"])
        elif p["action"] == "merge":
            seats.append(p["spec"]); retire += p["retire"]
        elif p["action"] in ("unmerge", "split"):
            seats += p["spec"]; retire.append(p["team"])
    return {"project": result["project"], "option": "reevaluation", "seats": seats, "retire": sorted(set(retire))}


def to_markdown(result: dict) -> str:
    cat = catalogue()
    a = result["activity"]
    lines = [f"## Team re-evaluation: {result['project']} ({result['date']}, last {result['days']} days)", "",
             f"Project size: **{result['size']}**. Seated: {len(result['seated'])}. "
             f"Commits attributed to a seat: {a['attributed']} (unattributed: {a['unattributed']}).", ""]
    if result["new_signals"] or result["gone_signals"]:
        lines.append(f"Repo changes since setup: new {', '.join(result['new_signals']) or 'none'}; "
                     f"gone {', '.join(result['gone_signals']) or 'none'}.\n")
    lines += ["| Seat | Commits | Runs | Inbox | Blocked | Last active |", "|---|---|---|---|---|---|"]
    for t, st in sorted(a["stats"].items(), key=lambda kv: -kv[1]["commits"]):
        name = result["names"].get(t, t)
        lines.append(f"| {name} | {st['commits']} | {st['runs']} | {st['inbox']} | {st['blocked']} | {st['last'] or '-'} |")
    lines += ["", "### Proposed changes", ""]
    if not result["proposals"]:
        lines.append("None: the team fits the work.")
    for p in result["proposals"]:
        if p["action"] == "add":
            s = p["spec"]
            name = cat[s["team"]]["seat"] if s.get("type") == "catalogue" else s["seat"]
            lines.append(f"- **Add {name}**: {p['why']}")
        elif p["action"] == "retire":
            lines.append(f"- **Retire {result['names'].get(p['team'], p['team'])}**: {p['why']}")
        elif p["action"] == "merge":
            lines.append(f"- **Merge into {p['spec']['seat']}** ({', '.join(p['retire'])}): {p['why']}")
        elif p["action"] == "unmerge":
            lines.append(f"- **Split {result['names'].get(p['team'], p['team'])} back into its seats**: {p['why']}")
        else:
            lines.append(f"- **Split frontend per UI app**: {p['why']}")
    if result.get("notes"):
        lines += ["", "### Noted, not proposed", ""] + [f"- {n}" for n in result["notes"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", type=Path, help="write the proposed plan (seats to add, retire) for scaffold.py --plan")
    a = ap.parse_args()
    root = a.root.resolve()
    if not (root / "docs" / "TEAM.md").is_file():
        ap.error("no docs/TEAM.md: seat a team first (team-setup)")
    result = evaluate(root, a.days)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(to_plan(result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.json:
        out = dict(result); out.pop("fresh_scan")
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(to_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
