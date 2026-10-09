#!/usr/bin/env python3
"""Turn a repo scan into three team options: lean, recommended and full.

    plan.py --scan scan.json                       print all three options as JSON
    plan.py --scan scan.json --markdown            print them as tables the owner can read
    plan.py --scan scan.json --option lean --out docs/team/plan.json --project "Name"
                                                   write one option as the plan scaffold.py applies

How the options differ:
  lean         the fewest sessions: every allowed merge, optional seats dropped
  recommended  what the evidence calls for, scaled to the project's size: a tiny project takes every
               merge, a small one merges the commercial seats, a medium one keeps seats separate, a
               large one also splits a frontend seat per UI app
  full         every seat separate, the optional seats added, splits applied

Every seat carries `why`: the signal and the evidence that put it there. Seat specs:
  {"team": "design", "type": "catalogue"}
  {"team": "growth", "type": "merge", "of": ["sales", "seo", "social"], "seat": "Growth", "mark": "📈"}
  {"team": "frontend-web", "type": "derive", "base": "seat-frontend", "seat": "...", "mark": "...", "scope": "..."}
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teamlib import ALWAYS, CHECK_SEATS, DERIVED_ROLES, MERGES, catalogue  # noqa: E402

SPLIT_MARKS = ["🖥️", "💻", "🪟", "📟"]
# merges a small project takes even in the recommended option: the commercial and money seats
SMALL_MERGES = ("growth", "money", "legal-compliance", "customer", "data-ml")
# seats lean drops when present, because another seat covers their job well enough while small
LEAN_DROPS = ("user", "scope-trimmer", "competition", "funding", "research")


def ev(signals: dict, *names: str) -> str:
    for n in names:
        if signals.get(n):
            return f"{n}: {signals[n][0]}"
    return ""


def size_class(scan: dict) -> str:
    size = scan.get("size", {})
    code, commits, people = size.get("code_files", 0), size.get("commits", 0), size.get("contributors", 0)
    if code < 60 and commits < 50:
        return "tiny"
    if code < 600 and people <= 3:
        return "small"
    if code < 3000:
        return "medium"
    return "large"


def needs(scan: dict) -> tuple[dict[str, str], dict[str, str], list[dict]]:
    """(core seats the evidence calls for, optional seats worth offering, derived roles), each with why."""
    s = scan.get("signals", {})
    has = lambda *n: any(s.get(x) for x in n)  # noqa: E731
    users = has("auth", "personal_data", "email", "payments", "landing")
    core: dict[str, str] = {"ceo": "every team keeps one decision register",
                            "bar-raiser": "every team keeps one independent check"}
    opt: dict[str, str] = {}
    if has("code"):
        core["engineering"] = ev(s, "code")
    if has("tests", "ci") and has("code"):
        core["testing"] = ev(s, "tests", "ci")
    if has("ui_web"):
        core["frontend"] = ev(s, "ui_web")
    if has("mobile"):
        core["mobile"] = ev(s, "mobile")
    if has("ui_web", "mobile", "game", "desktop", "extension"):
        core["design"] = ev(s, "ui_web", "mobile", "game", "desktop", "extension")
        (core if users else opt)["user"] = ("people sign up or pay: someone walks the product as a customer would"
                                           if users else "someone walks the product as a customer would")
    if users or has("ui_web", "mobile"):
        core["product"] = ev(s, "payments", "auth", "landing", "personal_data", "ui_web", "mobile") or "people use it"
    if has("deploy"):
        core["platform"] = ev(s, "deploy")
    if has("ml"):
        core["ml"] = ev(s, "ml")
    if has("data_pipelines"):
        core["data"] = ev(s, "data_pipelines")
    if has("data_pipelines", "analytics"):
        core["research"] = ev(s, "data_pipelines", "analytics")
    elif has("ml"):
        opt["research"] = "claims rest on a model: someone owns hypotheses and audits"
    if has("payments"):
        core["payments"] = ev(s, "payments")
    if has("payments", "landing"):
        core["sales"] = ev(s, "payments", "landing")
        opt["competition"] = "it will be sold: someone keeps the alternatives and checks comparative claims"
        opt["funding"] = "it will be sold: someone keeps the runway and funding options"
    if has("landing", "content") and (users or has("content")):
        core["seo"] = ev(s, "landing", "content")
    if has("content"):
        core["social"] = ev(s, "content")
    if has("video"):
        core["motion"] = ev(s, "video")
    if has("auth", "email") and users:
        core["customer-success"] = ev(s, "auth", "email")
    elif core.get("product"):
        opt["customer-success"] = "people use it: someone owns the path from sign-up to first value"
    if has("personal_data", "licence_data"):
        core["compliance"] = ev(s, "personal_data", "licence_data")
    if has("auth") and has("payments", "personal_data"):
        core["security"] = ev(s, "auth", "payments", "personal_data")
    elif has("auth", "security_policy"):
        opt["security"] = ev(s, "auth", "security_policy")
    if has("docs_site") or (has("oss") and has("code")):
        core["docs"] = ev(s, "docs_site", "oss")
    elif has("api"):
        opt["docs"] = ev(s, "api")
    if has("oss"):
        core["community"] = ev(s, "oss")
    if has("game"):
        core["game-design"] = ev(s, "game")
    if has("i18n"):
        core["i18n"] = ev(s, "i18n")
    derived = [dict(DERIVED_ROLES[sig], type="derive", why=ev(s, sig)) for sig in DERIVED_ROLES if s.get(sig)]
    return core, opt, derived


def with_coordination(seats: dict[str, str], n_sessions: int) -> None:
    """The Chief of Staff and the Scope Trimmer earn their seat by the number of sessions they coordinate."""
    if n_sessions >= 5:
        seats.setdefault("chief-of-staff", f"{n_sessions} other seats: one seat talks to you and keeps the tracker")
    if n_sessions >= 10:
        seats.setdefault("scope-trimmer", f"{n_sessions} other seats: someone cuts the queue to the shortest path to a customer")


def apply_merges(seats: dict[str, str], groups, scan: dict) -> list[dict]:
    """Replace members by merged seats, in place; return the merge specs."""
    out = []
    for team in groups:
        m = MERGES[team]
        present = [t for t in m["of"] if t in seats]
        if len(present) < 2:
            continue
        if team == "engineering-platform" and scan.get("size", {}).get("code_files", 0) > 2000:
            continue
        if any(t in CHECK_SEATS for t in present) and m["kind"] != "check":
            continue
        for t in present:
            seats.pop(t)
        out.append({"team": team, "type": "merge", "of": present, "seat": m["seat"], "mark": m["mark"],
                    "kind": m["kind"], "why": f"{m['why']} (holds {', '.join(present)})"})
    return out


def ui_splits(scan: dict) -> list[dict]:
    apps = [a for a in scan.get("size", {}).get("ui_apps", []) if a != "."]
    if len(apps) < 2:
        return []
    out = []
    for i, app in enumerate(apps[:4]):
        slug = app.rstrip("/").split("/")[-1].lower().replace("_", "-")
        out.append({"team": f"frontend-{slug}", "type": "derive", "base": "seat-frontend",
                    "seat": f"Frontend engineer ({slug})", "mark": SPLIT_MARKS[i], "kind": "implementation",
                    "register": f"the UI code under {app}/", "reports_to": "Engineering",
                    "scope": f"only {app}/; each other UI app has its own frontend seat",
                    "why": f"separate: {len(apps)} UI apps ({', '.join(apps[:4])})"})
    return out


def build(scan: dict, option: str) -> list[dict]:
    core, opt, derived = needs(scan)
    seats = dict(core)
    size = size_class(scan)
    merges: list[dict] = []
    splits: list[dict] = []
    if option == "full":
        seats.update({k: v for k, v in opt.items() if k not in seats})
        splits = ui_splits(scan)
    elif option == "recommended":
        if size == "tiny":
            for t in ("scope-trimmer", "competition", "funding", "research"):
                if not (t == "research" and scan.get("signals", {}).get("data_pipelines")):
                    seats.pop(t, None)
            merges = apply_merges(seats, list(MERGES), scan)
        elif size == "small":
            merges = apply_merges(seats, SMALL_MERGES, scan)
        elif size == "large":
            splits = ui_splits(scan)
    else:  # lean
        for t in LEAN_DROPS:
            if t not in ALWAYS:
                seats.pop(t, None)
        merges = apply_merges(seats, list(MERGES), scan)
    if splits:
        seats.pop("frontend", None)
    n = len(seats) + len(merges) + len(splits) + len(derived)
    if option != "lean" or n >= 7:
        with_coordination(seats, n)
    cat = catalogue()
    ordered = [{"team": t, "type": "catalogue", "why": seats[t]} for t in cat if t in seats]
    return ordered + merges + splits + derived


def options(scan: dict) -> dict:
    return {"size": size_class(scan), "lean": build(scan, "lean"), "recommended": build(scan, "recommended"),
            "full": build(scan, "full")}


def to_markdown(opts: dict) -> str:
    cat = catalogue()
    lines = [f"Project size: **{opts['size']}**\n"]
    for name in ("lean", "recommended", "full"):
        seats = opts[name]
        lines += [f"### {name.capitalize()}: {len(seats)} seats\n", "| | Seat | How | Why |", "|---|---|---|---|"]
        for x in seats:
            if x["type"] == "catalogue":
                row = cat[x["team"]]
                lines.append(f"| {row['mark']} | {row['seat']} | catalogue | {x['why']} |")
            elif x["type"] == "merge":
                held = " + ".join(cat[t]["seat"] for t in x["of"])
                lines.append(f"| {x['mark']} | {x['seat']} | merged: {held} | {x['why']} |")
            else:
                lines.append(f"| {x['mark']} | {x['seat']} | new, from {x['base']} | {x['why']} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", type=Path, required=True)
    ap.add_argument("--option", choices=("lean", "recommended", "full"))
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--project")
    ap.add_argument("--owner-acts", default="publishing, sending, spending, signing")
    ap.add_argument("--push-rule", default="the owner pushes; a seat never pushes unless DECISIONS.md says otherwise.")
    a = ap.parse_args()
    scan = json.loads(a.scan.read_text(encoding="utf-8"))
    opts = options(scan)
    if a.option:
        plan = {"project": a.project or scan.get("root"), "option": a.option, "size": opts["size"],
                "owner_acts": a.owner_acts, "push_rule": a.push_rule, "seats": opts[a.option], "retire": []}
        text = json.dumps(plan, indent=2, ensure_ascii=False)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(text + "\n", encoding="utf-8")
        print(text)
    elif a.markdown:
        print(to_markdown(opts))
    else:
        print(json.dumps(opts, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
