#!/usr/bin/env python3
"""Re-evaluate a seated team: how it actually works, against what the repo needs now.

    reevaluate.py --root <project> [--days 30]                  print the report (markdown)
    reevaluate.py --root <project> --json                        print the measurements and proposals
    reevaluate.py --root <project> --out docs/team/reevaluation.json   also write the proposed plan

Measures, per seated team, over the window:
  commits   subjects starting with a seat's prefix (`design:`, `design(web):`). A prefix maps to the team
            of that name or rulebook name; then a member's name maps to the merged seat holding it
            (`design:` counts for Product & Design) unless the member has a roster row of its own; a seat
            name's slug or first word maps only when no other seated row shares it. A scope names a seat
            when `<prefix>-<scope>` is one: `frontend(web):` counts for `frontend-web` when it is seated.
  runs      worker run logs written under scratchpad/team/runs/<team>/
  inbox     lines waiting in scratchpad/team/inbox/<team>.md
  blocked   tracker lines saying BLOCKED, inside the window: a table row counts for the seat in its seat
            column, dated only by a date, status or updated column (a due date in "done when" does not
            make it old; an undated row is current); a dated log line ("<date> · <sender> → <receiver> ·
            … BLOCKED …") counts for its sender, a "(called by …)" note left out.
Re-scans the repo and diffs the signals against docs/team/scan.json, the setup baseline. With no
baseline, no signal counts as new or gone, and a note says to start one (`scan.py --root . --save`).

Then proposes, each with a unique `key` (`<action>:<team>`), a `title` in seat names with marks, `why`
in plain words and the `signals` it rests on:
  add      what the plan for the option recorded in docs/team/plan.json (else recommended) calls for
           that no seated seat covers (teamlib.coverage: a merged seat covers its members, a frontend
           split covers the Frontend engineer). A merge in that plan whose members are all missing is
           proposed as the one merged seat; one with a member already held is proposed member by member.
           A merge already seated has its missing members proposed one by one. A frontend split is left
           to the split step while the catalogue Frontend engineer is seated; splits already seated keep
           their names (plan.build's `held`), so a newer app with the same folder name never renames
           one or seats its app twice. The catalogue Frontend engineer is proposed beside the splits
           when the plan has it hold the apps they leave (a fifth app, or one at the repository root).
           The Chief of Staff and the Scope Trimmer by plan.coordination, counting the other seats after
           the adds. A seat the owner struck from docs/team/plan.json at setup (the plan for the recorded
           option has it, the plan file does not; never a coordination seat, which follows the seat count)
           is not proposed again unless one of its signals is new.
           A why names the new evidence when a signal new since setup brought the seat back.
  retire   a seat idle in the window that nothing calls for any more: not the CEO or the Bar Raiser; not
           a seat a signal still calls for (catalogue, derived role, or frontend split whose app folder
           still exists); not a coordination seat plan.coordination still gives the team
  merge    two or more quiet seats one session can hold (plan.merge_allowed with after_setup=True: never
           the CEO or the Bar Raiser, never Engineering & Platform past 2,000 source files). A merge
           claims its members: no two proposals share one; more members first, then MERGES order.
  unmerge  a merged seat whose work now dominates the team
  split    a frontend seat per UI app once the project is large and the catalogue seat is seated; the
           catalogue seat retires only when the splits hold every app (none past four, none at the root)
A seat seated inside the window (the lock's `seated` date, else the newest commit that added its
rulebook, else treated as old) is never proposed for retirement or a merge; a note names it. A retired
seat is not proposed again unless one of its signals is new since the baseline. A proposal the owner
declined (docs/team/declined.json, written by scaffold.py --only) is not proposed again unless one of its
signals is new since the baseline and was not already part of the declined proposal's evidence. A note
names each one skipped, in plain words that claim only what the script knows: with no baseline it says
so; a declined or retired Chief of Staff or Scope Trimmer (no signal of its own) waits for the owner to
ask. The report renders repo changes in plain sentences (plan.PLAIN_SIGNALS), never signal keys.

--out writes the re-evaluation plan scaffold.py --plan applies (with --only KEY,... for some of it):
  {"project", "option": "reevaluation", "source", "date",
   "proposals": [{"key", "action", "title", "why", "signals", "seats", "retire"}],
   "seats": [union of the proposals' seat specs, one per team], "retire": [union of their retire lists]}
`project` comes from docs/team/plan.json, else docs/TEAM.md's title line, else the folder name; `source`
is the --out path relative to the root.
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
from teamlib import (ALWAYS, MERGES, catalogue, coverage, load_lock, merge_members, project_name,  # noqa: E402
                     roster)
if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252; seat marks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

PREFIX_RE = re.compile(r"^([a-z][a-z0-9-]*)(?:\(([^)]*)\))?:\s")
ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
LOW_COMMITS, LOW_RUNS = 2, 2           # a seat at or under both is "quiet" in the window
DOMINANT_SHARE, DOMINANT_MIN = 0.30, 10  # a merged seat over both has outgrown the merge
OPTIONS = ("lean", "recommended", "full")


def git_subjects(root: Path, days: int) -> list[tuple[str, str]]:
    try:
        out = subprocess.run(["git", "-C", str(root), "log", f"--since={days} days ago", "--format=%as\t%s"],
                             capture_output=True, text=True, encoding="utf-8", timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [tuple(l.split("\t", 1)) for l in out.splitlines() if "\t" in l]


def strong_aliases(row: dict) -> set[str]:
    """Prefixes that always name this row: its team and its rulebook's name."""
    skill = row["skill"][len("seat-"):] if row["skill"].startswith("seat-") else row["skill"]
    return {a for a in (row["team"], skill) if a}


def weak_aliases(row: dict) -> set[str]:
    """Prefixes that name this row only when no other row claims them: its seat name's slug and first word."""
    seat = row["seat"].lower()
    first = seat.split()[0].strip("&,") if seat.split() else ""
    return {a for a in (planner.slugify(seat), first) if a}


def alias_map(rows: list[dict], merged: dict[str, list[str]] | None = None) -> dict[str, str]:
    """prefix -> team. Strong aliases first (first row wins); then each member of a merged seat (`merged`:
    {merged team: members}) names that seat unless the member has a row of its own; a weak alias only when
    exactly one row has it."""
    out: dict[str, str] = {}
    for r in rows:
        for a in strong_aliases(r):
            out.setdefault(a, r["team"])
    own = {r["team"] for r in rows}
    for team, members in (merged or {}).items():
        for m in members:
            if m not in own:
                out.setdefault(m, team)
    weak_count: dict[str, int] = {}
    for r in rows:
        for a in weak_aliases(r) - strong_aliases(r):
            weak_count[a] = weak_count.get(a, 0) + 1
    for r in rows:
        for a in weak_aliases(r):
            if a not in out and weak_count.get(a) == 1:
                out[a] = r["team"]
    return out


def attribute(subject: str, by_alias: dict[str, str]) -> str | None:
    """The team a commit subject's prefix names; `frontend(web):` tries `frontend-web` before `frontend`."""
    m = PREFIX_RE.match(subject)
    if not m:
        return None
    if m.group(2):
        team = by_alias.get(f"{m.group(1)}-{planner.slugify(m.group(2))}")
        if team:
            return team
    return by_alias.get(m.group(1))


def seat_in(text: str, rows: list[dict]) -> str | None:
    """The seated team `text` names: the longest seat name found in it, else a mark (without U+FE0F)."""
    norm = planner.norm_mark(text)
    by_name = [r for r in rows if r["seat"] and r["seat"] in text]
    if by_name:
        return max(by_name, key=lambda r: len(r["seat"]))["team"]
    by_mark = [r for r in rows if r["mark"] and planner.norm_mark(r["mark"]) in norm]
    return by_mark[0]["team"] if by_mark else None


def tracker_blocked(text: str, rows: list[dict], since: datetime.date) -> dict[str, int]:
    """BLOCKED lines per team, inside the window. A table row counts for the seat in its `seat` column; only
    a date in a date, status or updated column dates it (an undated row is the current state and counts).
    Any other line needs a date in the window and counts for its sender, the text before `→` without a
    "(called by …)" note."""
    out: dict[str, int] = {}
    seat_col, date_cols = None, []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            lowered = [c.lower() for c in cells]
            if "seat" in lowered:
                seat_col = lowered.index("seat")
                date_cols = [i for i, c in enumerate(lowered)
                             if any(w in c for w in ("date", "status", "updated")) and not any(w in c for w in ("due", "when"))]
                continue
            if "BLOCKED" not in line or seat_col is None or seat_col >= len(cells):
                continue
            date = next((m for i in date_cols if i < len(cells) for m in [ISO_DATE.search(cells[i])] if m), None)
            if date and date.group(1) < since.isoformat():
                continue
            team = seat_in(cells[seat_col], rows)
        else:
            if "BLOCKED" not in line or "→" not in line:
                continue
            date = ISO_DATE.search(line)
            if not date or date.group(1) < since.isoformat():
                continue
            sender = re.sub(r"\(called by[^)]*\)", "", line.split("→", 1)[0])
            team = seat_in(sender, rows)
        if team:
            out[team] = out.get(team, 0) + 1
    return out


def measure(root: Path, rows: list[dict], days: int, merged: dict[str, list[str]] | None = None) -> dict:
    since = datetime.date.today() - datetime.timedelta(days=days)
    by_alias = alias_map(rows, merged)
    stats = {r["team"]: {"commits": 0, "runs": 0, "inbox": 0, "blocked": 0, "last": None} for r in rows}
    unattributed = 0
    for date, subject in git_subjects(root, days):
        team = attribute(subject, by_alias)
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
        for team, n in tracker_blocked(tracker.read_text(encoding="utf-8"), rows, since).items():
            stats[team]["blocked"] += n
    total = sum(s["commits"] for s in stats.values())
    return {"days": days, "stats": stats, "attributed": total, "unattributed": unattributed}


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default
    except (OSError, ValueError):
        return default


def recorded_option(root: Path) -> str:
    """The option the owner chose at setup (docs/team/plan.json `option`), else recommended."""
    plan = read_json(root / "docs" / "team" / "plan.json", {})
    option = plan.get("option") if isinstance(plan, dict) else None
    return option if option in OPTIONS else "recommended"


def load_declined(root: Path) -> dict[str, dict]:
    """docs/team/declined.json as {key: the latest entry for it}."""
    out: dict[str, dict] = {}
    entries = read_json(root / "docs" / "team" / "declined.json", [])
    for e in entries if isinstance(entries, list) else []:
        if isinstance(e, dict) and e.get("key"):
            out[e["key"]] = e
    return out


def seated_dates(root: Path, rows: list[dict], lock: dict[str, dict]) -> dict[str, str | None]:
    """team -> ISO date it was seated: the lock's `seated`, else the date of the newest commit that added its
    rulebook, else None (treated as seated long ago)."""
    out: dict[str, str | None] = {}
    for r in rows:
        date = (lock.get(r["skill"]) or {}).get("seated")
        if not date:
            try:
                log = subprocess.run(["git", "-C", str(root), "log", "--diff-filter=A", "--format=%cs", "--",
                                      f".claude/skills/{r['skill']}/SKILL.md"],
                                     capture_output=True, text=True, encoding="utf-8", timeout=20).stdout.split()
            except (OSError, subprocess.TimeoutExpired):
                log = []
            date = log[0] if log else None
        out[r["team"]] = date
    return out


def app_folder(row: dict) -> str | None:
    """The app folder a frontend split seat holds, from its register ("the UI code under apps/web/")."""
    m = re.search(r"under\s+(\S+?)/?\s*$", row.get("register", ""))
    return m.group(1) if m else None


def plural(n: int, word: str) -> str:
    """"1 commit", "2 commits"."""
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def plain_signals(keys: list[str]) -> str:
    """Signal keys as the owner reads them: "it has a web interface; it publishes posts or other content"."""
    return "; ".join(lower_first(planner.PLAIN_SIGNALS.get(k, k.replace("_", " "))) for k in keys)


def listed(items: list[str]) -> str:
    """Names joined in words: "A", "A and B", "A, B and C"."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def setup_struck(root: Path, option: str, base_scan: dict) -> set[str]:
    """Teams the owner struck from the setup plan: the plan for `option` on the setup scan has them (as a seat
    or a merge member), docs/team/plan.json does not. The Chief of Staff and the Scope Trimmer are left out:
    they follow the seat count, not the plan. Empty without a setup plan file."""
    plan = read_json(root / "docs" / "team" / "plan.json", {})
    seats = plan.get("seats") if isinstance(plan, dict) and plan.get("option") in OPTIONS else None
    if not isinstance(seats, list):
        return set()
    flat = lambda specs: {s["team"] for s in specs} | {m for s in specs for m in s.get("of", [])}  # noqa: E731
    planned = flat([s for s in seats if isinstance(s, dict) and s.get("team")])
    offered = plan.get("offered")  # what setup put to the owner; a plan written before 1.3.0 lacks it
    base = set(offered) if isinstance(offered, list) else flat(planner.build(base_scan, option))
    return base - planned - set(planner.COORDINATION)


def evaluate(root: Path, days: int) -> dict:
    team_doc = root / "docs" / "TEAM.md"
    rows = roster(team_doc)
    seated = {r["team"] for r in rows}
    lock = load_lock(root)
    cov = coverage(root, rows, lock)  # role -> the seated team holding it
    merged_members: dict[str, list[str]] = {}
    for r in rows:
        members = merge_members(r["team"], r["skill"], lock)
        if members:
            merged_members[r["team"]] = members
    cat = catalogue()
    names = {r["team"]: f"{r['mark']} {r['seat']}" for r in rows}
    seated_marks = {planner.norm_mark(r["mark"]) for r in rows}
    # frontend splits already seated, by the app folder they hold: they keep their names
    held = {app_folder(r): (r["team"][len("frontend-"):], r["mark"]) for r in rows
            if r["team"].startswith("frontend-") and app_folder(r)}
    held_team = {folder: f"frontend-{slug}" for folder, (slug, _) in held.items()}

    def name_of(t: str) -> str:
        return names.get(t) or (f"{cat[t]['mark']} {cat[t]['seat']}" if t in cat else t)

    def spec_name(spec: dict) -> str:
        return name_of(spec["team"]) if spec.get("type", "catalogue") == "catalogue" else f"{spec['mark']} {spec['seat']}"

    def held_elsewhere(spec: dict) -> bool:
        """A split spec for an app a seated split already holds under another name."""
        folder = app_folder(spec) if spec["team"].startswith("frontend-") else None
        return bool(folder) and held_team.get(folder, spec["team"]) != spec["team"]

    fresh = run_scan(root)
    baseline = read_json(root / "docs" / "team" / "scan.json", None)
    has_baseline = isinstance(baseline, dict) and isinstance(baseline.get("signals"), dict)
    notes: list[str] = []
    if has_baseline:
        new_signals = sorted(set(fresh["signals"]) - set(baseline["signals"]))
        gone_signals = sorted(set(baseline["signals"]) - set(fresh["signals"]))
    else:
        new_signals, gone_signals = [], []
        notes.append("There is no setup baseline (docs/team/scan.json), so no signal counts as new or gone; "
                     "run `scan.py --root . --save` to start one from today.")
    core, opt, derived = planner.needs(fresh)
    option = recorded_option(root)
    struck = setup_struck(root, option, baseline if has_baseline else fresh)
    activity = measure(root, rows, days, merged_members)
    stats = activity["stats"]
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    young = {t for t, d in seated_dates(root, rows, lock).items() if d and d >= since}
    held_back: list[str] = []
    retired = {p.stem for p in (root / "docs" / "team").glob("*.md")
               if p.read_text(encoding="utf-8").startswith("> **Retired")}
    declined = load_declined(root)
    proposals: list[dict] = []
    proposed: set[str] = set()  # every team a proposal seats, across all steps

    def offer(p: dict) -> bool:
        """Keep a proposal unless its key is taken, or the owner declined it and nothing new calls for it."""
        if any(q["key"] == p["key"] for q in proposals):
            return False
        d = declined.get(p["key"])
        if d and not [s for s in p["signals"] if s in new_signals and s not in (d.get("signals") or [])]:
            when = d.get("date") or "an earlier date"
            if p["action"] == "add" and not p["signals"]:
                notes.append(f"{p['title']} was declined on {when}; it is not proposed again until you ask for it.")
            elif p["signals"] and not has_baseline:
                notes.append(f"{p['title']} was declined on {when}; there is no setup baseline to tell whether its "
                             "evidence changed, so it is not proposed again.")
            else:
                notes.append(f"{p['title']} was declined on {when}; its evidence has not changed, so it is not "
                             "proposed again.")
            return False
        proposals.append(p)
        proposed.update(s["team"] for s in p["seats"])
        return True

    def stays_retired(team: str, signals: list[str], why: str) -> bool:
        if team not in retired or any(s in new_signals for s in signals):
            return False
        if has_baseline:
            notes.append(f"{name_of(team)} was retired and its evidence is unchanged since setup, so it is not "
                         f"proposed again. {planner.plain_why(why)}")
        else:
            notes.append(f"{name_of(team)} was retired, and there is no setup baseline to tell whether its evidence "
                         f"changed, so it is not proposed again. {planner.plain_why(why)}")
        return True

    def add(spec: dict, why: str) -> None:
        sigs = planner.spec_signals(spec, fresh)
        new = [s for s in sigs if s in new_signals]
        if spec["team"] in struck and not new:
            notes.append(f"{spec_name(spec)} was left out of the team at setup"
                         + (" and nothing new calls for it" if has_baseline else "") + ", so it is not proposed again.")
            return
        text = planner.plain_why(why)
        if new:  # name the evidence that is new, not the seat's first evidence
            evidence = planner.ev(fresh["signals"], *new)
            text = (text.rstrip(".") + ", new since setup." if evidence == why
                    else f"{text} New since setup: {lower_first(planner.plain_why(evidence))}")
        offer({"key": f"add:{spec['team']}", "action": "add", "title": f"Add {spec_name(spec)}", "why": text,
               "signals": sigs, "spec": spec, "seats": [spec], "retire": []})

    # add: what the plan for the recorded option calls for that nothing seated covers
    splits_now = {s["team"]: s for s in planner.ui_splits(fresh, taken_marks=seated_marks, held=held)}
    for spec in planner.build(fresh, option, held=held):
        t, kind = spec["team"], spec.get("type", "catalogue")
        if t in planner.COORDINATION or t in proposed:
            continue
        # the catalogue Frontend engineer holding the apps the seated splits leave
        frontend_holder = (t == "frontend" and kind == "catalogue" and t not in seated
                           and spec["why"].startswith(planner.FRONTEND_HOLDS))
        if t in cov and kind != "merge" and not frontend_holder:
            continue
        if kind == "merge":
            why_of = lambda m: core.get(m) or opt.get(m) or spec["why"]  # noqa: E731
            missing = [m for m in spec["of"] if m not in cov and m not in proposed]
            keep = [m for m in missing if not stays_retired(m, planner.spec_signals({"team": m}, fresh), why_of(m))]
            if t not in cov and len(missing) == len(spec["of"]) and planner.merge_allowed(t, keep, fresh, after_setup=True):
                merged = planner.merge_spec(t, keep)
                evidence = next((why_of(m) for m in keep if core.get(m) or opt.get(m)), "")
                why = (planner.plain_why(evidence).rstrip(".") + "; " if evidence else "") + MERGES[t]["why"]
                if not stays_retired(t, planner.spec_signals(merged, fresh), why):
                    add(merged, why)
                continue
            for m in keep:  # a merge already seated, or one with a member held elsewhere: member by member
                add({"team": m, "type": "catalogue", "why": why_of(m)}, why_of(m))
        elif kind == "derive":
            is_split = spec.get("base") == "seat-frontend" and t.startswith("frontend-")
            if is_split and ("frontend" in seated or held_elsewhere(spec)):
                continue  # the split step proposes these, retiring the catalogue seat
            spec = splits_now.get(t, spec) if is_split else spec
            if not stays_retired(t, planner.spec_signals(spec, fresh), spec["why"]):
                add(spec, planner.describe(spec, cat)[2] if is_split else spec["why"])
        else:
            why = spec["why"] if frontend_holder else core.get(t) or opt.get(t) or spec["why"]
            if not stays_retired(t, planner.spec_signals(spec, fresh), why):
                add({"team": t, "type": "catalogue", "why": why}, why)

    # coordination: the rule plan.py seats them by, on the other seats after the adds
    n_other = (sum(1 for r in rows if r["team"] not in planner.COORDINATION)
               + sum(1 for p in proposals if p["spec"]["team"] not in planner.COORDINATION))
    coordination = planner.coordination(n_other, option)
    for t, why in coordination.items():
        if t in cov:
            continue
        if t in retired:  # no signal of its own: it waits for the owner to ask
            notes.append(f"{name_of(t)} was retired, so it is not proposed again. With {n_other} other seats the "
                         "usual rule would seat it; it comes back when you ask for it.")
            continue
        add({"team": t, "type": "catalogue", "why": why}, why)

    # retire: idle in the window, and nothing calls for it any more
    needed = set(core) | set(opt) | {d["team"] for d in derived} | set(splits_now) | set(coordination)
    for r in rows:
        t, st = r["team"], stats[r["team"]]
        if t in ALWAYS or st["commits"] or st["runs"] or st["inbox"]:
            continue
        if any(m in needed for m in merged_members.get(t, [t])):
            continue
        folder = app_folder(r) if t.startswith("frontend-") else None
        if folder and (root / folder).is_dir() and fresh["signals"].get("ui_web"):
            continue  # a frontend split whose app is still there
        if t in young:
            held_back.append(t)
            continue
        offer({"key": f"retire:{t}", "action": "retire", "team": t, "title": f"Retire {name_of(t)}",
               "why": f"No commits, worker runs or inbox lines in {days} days, and nothing in the repository calls for it.",
               "signals": [], "seats": [], "retire": [t]})

    # merge: two or more quiet seats one session can hold; a merge claims its members
    quiet = {t for t, st in stats.items() if st["commits"] <= LOW_COMMITS and st["runs"] <= LOW_RUNS and not st["blocked"]}
    retiring = {t for p in proposals for t in p["retire"]}
    candidates = []
    for i, (team, m) in enumerate(MERGES.items()):
        present = [t for t in m["of"] if t in seated and t not in merged_members and t not in retiring]
        if team in cov or len(present) < 2 or not all(t in quiet for t in present):
            continue
        if not planner.merge_allowed(team, present, fresh, after_setup=True):
            continue
        if any(t in young for t in present):
            held_back += [t for t in present if t in young]
            continue
        candidates.append((-len(present), i, team, present))
    claimed: set[str] = set()
    for _, _, team, present in sorted(candidates):
        present = [t for t in present if t not in claimed]
        if not planner.merge_allowed(team, present, fresh, after_setup=True):
            continue
        spec = planner.merge_spec(team, present)
        detail = "; ".join(f"{name_of(t)} {plural(stats[t]['commits'], 'commit')}, {plural(stats[t]['runs'], 'run')}"
                           for t in present)
        key = f"merge:{team}"
        if offer({"key": key, "action": "merge",
                  "title": f"Merge {listed([name_of(t) for t in present])} into {spec['mark']} {spec['seat']}",
                  "why": f"All of them were quiet over {days} days ({detail}).",
                  "signals": [], "spec": spec, "seats": [spec], "retire": list(present)}) or key in declined:
            claimed |= set(present)  # a declined merge keeps its members: the owner is not asked again in another shape

    # unmerge: a merged seat that now carries the team
    total = max(activity["attributed"], 1)
    for t, members in merged_members.items():
        st = stats.get(t, {"commits": 0})
        if st["commits"] >= DOMINANT_MIN and st["commits"] / total >= DOMINANT_SHARE:
            back = [{"team": m, "type": "catalogue", "why": f"split out of {name_of(t)}"} for m in members if m in cat]
            offer({"key": f"unmerge:{t}", "action": "unmerge", "team": t,
                   "title": f"Split {name_of(t)} back into {listed([name_of(m) for m in members])}",
                   "why": f"{st['commits']} of {total} attributed commits ({st['commits'] / total:.0%}) in {days} days.",
                   "signals": [], "spec": back, "seats": back, "retire": [t]})

    # split: one frontend seat per UI app when the project is large
    if planner.size_class(fresh) == "large" and "frontend" in seated:
        splits = [s for s in splits_now.values()
                  if s["team"] not in cov and s["team"] not in proposed and not held_elsewhere(s)]
        count = max(fresh.get("size", {}).get("ui_app_count", 0), len(splits_now))
        holds = planner.frontend_holds(fresh, list(splits_now.values()))
        retire = [] if holds else ["frontend"]  # the catalogue seat stays while it holds an app
        if splits and retire and "frontend" in young:
            held_back.append("frontend")
        elif splits:
            offer({"key": "split:frontend", "action": "split", "team": "frontend",
                   "title": f"Split {name_of('frontend')} into one seat per web app: {listed([spec_name(s) for s in splits])}",
                   "why": f"The project is large and has {count} web apps; "
                          + ("each gets its own frontend seat." if retire else
                             f"{listed([spec_name(s) for s in splits])} "
                             + ("gets its own seat" if len(splits) == 1 else "each get their own seat")
                             + f", and {name_of('frontend')} keeps the apps without one."),
                   "signals": ["ui_web"], "spec": splits, "seats": splits, "retire": retire})

    if held_back:
        notes.append(f"Seated inside the last {days} days, so not proposed for retirement or a merge yet: "
                     f"{listed([name_of(t) for t in dict.fromkeys(held_back)])}.")
    return {"project": project_name(root), "date": datetime.date.today().isoformat(), "days": days,
            "option": option, "baseline": has_baseline, "size": planner.size_class(fresh),
            "seated": [r["team"] for r in rows], "names": names, "notes": notes,
            "new_signals": new_signals, "gone_signals": gone_signals, "activity": activity,
            "proposals": proposals, "fresh_scan": fresh}


def to_plan(result: dict, source: str = "docs/team/reevaluation.json") -> dict:
    """The re-evaluation plan scaffold.py --plan applies: every proposal with its key, and the unions."""
    seats, seen, retire = [], set(), []
    for p in result["proposals"]:
        for s in p["seats"]:
            if s["team"] not in seen:
                seats.append(s)
                seen.add(s["team"])
        retire += p["retire"]
    props = [{k: p[k] for k in ("key", "action", "title", "why", "signals", "seats", "retire")} for p in result["proposals"]]
    return {"project": result["project"], "option": "reevaluation", "source": source, "date": result["date"],
            "proposals": props, "seats": seats, "retire": list(dict.fromkeys(retire))}


def to_markdown(result: dict) -> str:
    a = result["activity"]
    lines = [f"## Team re-evaluation: {result['project']} ({result['date']}, last {result['days']} days)", "",
             f"Project size: **{result['size']}**. Seated: {len(result['seated'])}. "
             f"Commits attributed to a seat: {a['attributed']} (unattributed: {a['unattributed']}).", ""]
    changes = ([f"New since setup: {plain_signals(result['new_signals'])}."] if result["new_signals"] else []) + \
              ([f"Gone since setup: {plain_signals(result['gone_signals'])}."] if result["gone_signals"] else [])
    if changes:
        lines.append(" ".join(changes) + "\n")
    lines += ["| Seat | Commits | Runs | Inbox | Blocked | Last active |", "|---|---|---|---|---|---|"]
    for t, st in sorted(a["stats"].items(), key=lambda kv: -kv[1]["commits"]):
        name = result["names"].get(t, t)
        lines.append(f"| {name} | {st['commits']} | {st['runs']} | {st['inbox']} | {st['blocked']} | {st['last'] or '-'} |")
    lines += ["", "### Proposed changes", ""]
    if not result["proposals"]:
        lines.append("None: the team fits the work.")
    for p in result["proposals"]:
        lines.append(f"- **{p['title']}**: {p['why']}")
    if result.get("notes"):
        lines += ["", "### Noted, not proposed", ""] + [f"- {n}" for n in result["notes"]]
    if result["proposals"]:
        lines += ["", "### Keys, for `scaffold.py --plan <plan> --only KEY,...`", ""]
        lines += [f"- `{p['key']}`: {p['title']}" for p in result["proposals"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", type=Path, help="write the re-evaluation plan (proposals, seats, retire) for scaffold.py --plan")
    a = ap.parse_args()
    root = a.root.resolve()
    if not (root / "docs" / "TEAM.md").is_file():
        ap.error("no docs/TEAM.md: seat a team first (team-setup)")
    result = evaluate(root, a.days)
    if a.out:
        out = a.out.resolve()
        try:
            source = out.relative_to(root).as_posix()
        except ValueError:
            source = str(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(to_plan(result, source), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.json:
        printed = dict(result)
        printed.pop("fresh_scan")
        print(json.dumps(printed, indent=2, ensure_ascii=False))
    else:
        print(to_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
