#!/usr/bin/env python3
"""Turn a repo scan into team options: lean (merged, reduced), recommended, full (separate seats).

    plan.py --scan scan.json                       print all three options as JSON
    plan.py --scan scan.json --markdown            print them as a table the owner can read
    plan.py --scan scan.json --option lean --out docs/team/plan.json --project "Name"
                                                   write one option as the plan scaffold.py applies

Every seat carries `why`: the signal and evidence that put it there. Seat specs:
  {"team": "design", "type": "catalogue"}
  {"team": "growth", "type": "merge", "of": ["sales", "seo", "social"], "seat": "Growth", "mark": "📈"}
  {"team": "web", "type": "derive", "base": "seat-frontend", "seat": "...", "mark": "...", "scope": "..."}
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


def ev(signals: dict, *names: str) -> str:
    for n in names:
        if signals.get(n):
            return f"{n}: {signals[n][0]}"
    return ""


def recommended(scan: dict) -> tuple[dict[str, str], list[dict]]:
    """team -> why, for catalogue seats; plus derived seats for roles no catalogue row covers."""
    s = scan.get("signals", {})
    size = scan.get("size", {})
    has = lambda *n: any(s.get(x) for x in n)  # noqa: E731
    seats: dict[str, str] = {
        "ceo": "every team keeps one decision register",
        "bar-raiser": "every team keeps one independent check",
    }
    users = has("auth", "personal_data", "email", "payments", "landing")
    if has("code"):
        seats["engineering"] = ev(s, "code")
    if has("tests", "ci"):
        seats["testing"] = ev(s, "tests", "ci")
    if has("ui_web"):
        seats["frontend"] = ev(s, "ui_web")
    if has("mobile"):
        seats["mobile"] = ev(s, "mobile")
    if has("ui_web", "mobile", "game", "desktop", "extension"):
        seats["design"] = ev(s, "ui_web", "mobile", "game", "desktop", "extension")
        if users:
            seats["user"] = "people sign up or pay: someone walks the product as a customer would"
    if users or has("ui_web", "mobile"):
        seats["product"] = ev(s, "auth", "personal_data", "payments", "landing", "ui_web", "mobile") or "people use it"
    if has("deploy"):
        seats["platform"] = ev(s, "deploy")
    if has("ml"):
        seats["ml"] = ev(s, "ml")
    if has("data_pipelines"):
        seats["data"] = ev(s, "data_pipelines")
    if has("data_pipelines", "analytics"):
        seats["research"] = ev(s, "data_pipelines", "analytics")
    if has("payments"):
        seats["payments"] = ev(s, "payments")
    if has("payments", "landing"):
        seats["sales"] = ev(s, "payments", "landing")
    if has("landing", "content", "docs_site") and (users or has("content")):
        seats["seo"] = ev(s, "landing", "content", "docs_site")
    if has("content"):
        seats["social"] = ev(s, "content")
    if has("video"):
        seats["motion"] = ev(s, "video")
    if has("auth", "email") and users:
        seats["customer-success"] = ev(s, "auth", "email")
    if has("personal_data", "licence_data"):
        seats["compliance"] = ev(s, "personal_data", "licence_data")
    if has("payments", "personal_data") and has("auth", "payments"):
        seats["security"] = ev(s, "auth", "payments", "personal_data")
    if has("docs_site") or (has("oss") and has("code")):
        seats["docs"] = ev(s, "docs_site", "oss")
    if has("oss"):
        seats["community"] = ev(s, "oss")
    if has("game"):
        seats["game-design"] = ev(s, "game")
    if has("i18n"):
        seats["i18n"] = ev(s, "i18n")
    if len(seats) >= 5:
        seats["chief-of-staff"] = "five or more seats: one seat talks to you and keeps the tracker"
    if len(seats) >= 10:
        seats["scope-trimmer"] = "ten or more seats: someone cuts the queue to the shortest path to a customer"
    derived = [dict(DERIVED_ROLES[sig], type="derive", why=ev(s, sig))
               for sig in DERIVED_ROLES if s.get(sig)]
    if size.get("code_files", 0) == 0:
        for t in ("engineering", "testing"):
            seats.pop(t, None)
    return seats, derived


def spec(team: str, why: str) -> dict:
    return {"team": team, "type": "catalogue", "why": why}


def option_recommended(scan: dict) -> list[dict]:
    seats, derived = recommended(scan)
    cat = catalogue()
    return [spec(t, seats[t]) for t in cat if t in seats] + derived


def option_lean(scan: dict) -> list[dict]:
    seats, derived = recommended(scan)
    for t in ("user", "scope-trimmer", "competition", "funding", "research"):
        if t in seats and t not in ALWAYS:
            seats.pop(t)
    out: list[dict] = []
    used: set[str] = set()
    for team, m in MERGES.items():
        present = [t for t in m["of"] if t in seats and t not in used]
        if len(present) < 2:
            continue
        if team == "engineering-platform" and scan.get("size", {}).get("code_files", 0) > 2000:
            continue
        if team == "quality" and "testing" not in present:
            continue
        if any(t in CHECK_SEATS for t in present) and m["kind"] != "check":
            continue
        used |= set(present)
        why = f"lean: {m['why']} (holds {', '.join(present)})"
        out.append({"team": team, "type": "merge", "of": present, "seat": m["seat"], "mark": m["mark"],
                    "kind": m["kind"], "why": why})
    remaining = {t: w for t, w in seats.items() if t not in used}
    if "chief-of-staff" in remaining and len(remaining) + len(out) <= 6:
        remaining.pop("chief-of-staff")
    cat = catalogue()
    return [spec(t, remaining[t]) for t in cat if t in remaining] + out + derived


def option_full(scan: dict) -> list[dict]:
    seats, derived = recommended(scan)
    s = scan.get("signals", {})
    extra = {
        "user": "someone walks the product as a customer would",
        "research": "claims rest on measurement: someone owns hypotheses and audits",
        "scope-trimmer": "someone cuts the queue to the shortest path to a customer",
        "chief-of-staff": "one seat talks to you and keeps the tracker",
    }
    if seats.get("sales"):
        extra["competition"] = "it will be sold: someone keeps the alternatives and checks comparative claims"
        extra["funding"] = "it will be sold: someone keeps the runway and funding options"
    if s.get("auth"):
        extra["security"] = ev(s, "auth")
    if seats.get("product"):
        extra["customer-success"] = "people use it: someone owns the path from sign-up to first value"
    if s.get("api") and not seats.get("docs"):
        extra["docs"] = ev(s, "api")
    for t, w in extra.items():
        if t == "user" and not (s.get("ui_web") or s.get("mobile")):
            continue
        if t == "research" and not (s.get("ml") or s.get("analytics") or s.get("data_pipelines")):
            continue
        seats.setdefault(t, w)
    cat = catalogue()
    out = [spec(t, seats[t]) for t in cat if t in seats]
    # separate: one frontend seat per UI app in a monorepo
    ui_apps = sorted({m.split("/package.json")[0] for m in scan.get("size", {}).get("manifests", [])
                      if m.endswith("package.json") and "/" in m and any(k in m for k in ("web", "site", "app", "admin", "dashboard", "frontend"))})
    if seats.get("frontend") and len(ui_apps) >= 2:
        out = [x for x in out if x["team"] != "frontend"]
        for i, app in enumerate(ui_apps[:4]):
            slug = app.rstrip("/").split("/")[-1].lower().replace("_", "-")
            out.append({"team": f"frontend-{slug}", "type": "derive", "base": "seat-frontend",
                        "seat": f"Frontend engineer ({slug})", "mark": SPLIT_MARKS[i], "kind": "implementation",
                        "register": f"the UI code under {app}/", "reports_to": "Engineering",
                        "scope": f"only {app}/; the other UI apps have their own frontend seat",
                        "why": f"separate: {len(ui_apps)} UI apps ({', '.join(ui_apps[:4])})"})
    return out + derived


def to_markdown(options: dict) -> str:
    cat = catalogue()
    lines = []
    for name in ("lean", "recommended", "full"):
        seats = options[name]
        lines.append(f"### {name.capitalize()}: {len(seats)} seats\n")
        lines.append("| | Seat | How | Why |")
        lines.append("|---|---|---|---|")
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
    options = {"lean": option_lean(scan), "recommended": option_recommended(scan), "full": option_full(scan)}
    if a.option:
        plan = {"project": a.project or scan.get("root"), "option": a.option, "owner_acts": a.owner_acts,
                "push_rule": a.push_rule, "seats": options[a.option]}
        text = json.dumps(plan, indent=2, ensure_ascii=False)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(text + "\n", encoding="utf-8")
        print(text)
    elif a.markdown:
        print(to_markdown(options))
    else:
        print(json.dumps(options, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
