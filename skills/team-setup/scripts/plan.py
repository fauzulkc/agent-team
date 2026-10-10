#!/usr/bin/env python3
"""Turn a repo scan into three team options: lean, recommended and full.

    plan.py --scan scan.json                       print all three options as JSON
    plan.py --scan scan.json --markdown            print them for the owner: Recommended first, then Lean and
                                                   Full, seat names with marks, every reason a plain sentence
    plan.py --scan scan.json --option lean --out docs/team/plan.json --project "Name"
                                                   write one option as the plan scaffold.py applies:
                                                   {"project", "option", "size", "owner_acts", "push_rule",
                                                    "seats", "retire": []}; reevaluate.py compares against
                                                   the recorded "option". --push-rule defaults to setup's
                                                   recommendation: "a seat asks the owner before each push
                                                   and pushes on the owner's yes."

How the options differ:
  lean         the fewest sessions: every allowed merge, optional seats dropped
  recommended  what the evidence calls for, scaled to the project's size: a tiny project takes every
               merge, a small one merges the commercial seats, a medium one keeps seats separate, a
               large one also splits a frontend seat per UI app
  full         every seat separate, the optional seats added, splits applied

A split makes one frontend seat per web UI app in a folder, for up to four apps (MAX_SPLITS). The
catalogue Frontend engineer stays beside the splits and holds the rest when there are more apps than
split seats, or a web app at the repository root (frontend_holds). A split's team is
`frontend-<slug>`, the slug built from the app folder's name (its whole path when two apps share a
name, or when a seated split already uses the name), lower-case [a-z0-9-], unique; its mark comes
from SPLIT_MARKS, which no catalogue, merge or derived seat uses. `ui_splits(scan, held=...)` and
`build(scan, option, held=...)` take the splits already seated ({app folder: (slug, mark)}): a held app
keeps its seat's name and comes first, so a seated split is never renamed by a newer app.

Rules reevaluate.py shares (one rule decides both):
  coordination(n_other, option)   the Chief of Staff at 5 or more other seats (7 in lean), the Scope
                                  Trimmer at 10 or more; "other" leaves out those two seats
  merge_allowed(team, present, scan, after_setup=False)
                                  two or more members present; never Engineering & Platform past 2,000
                                  source files; a check seat joins only a check merge; after setup, no
                                  merge holds the CEO or the Bar Raiser
  spec_signals(spec, scan)        the signal keys a seat spec rests on

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
import re  # noqa: E402

from teamlib import ALWAYS, CHECK_SEATS, DERIVED_ROLES, MERGES, catalogue  # noqa: E402
if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252; seat marks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

# marks for frontend split seats: none is used by a catalogue, merge or derived seat (split_marks checks)
SPLIT_MARKS = ["💻", "🪟", "📟", "🧩", "🔲", "🪄"]
MAX_SPLITS = 4
COORDINATION = ("chief-of-staff", "scope-trimmer")
# merges a small project takes even in the recommended option: the commercial and money seats
SMALL_MERGES = ("growth", "money", "legal-compliance", "customer", "data-ml")
# seats lean drops when present, because another seat covers their job well enough while small
LEAN_DROPS = ("user", "scope-trimmer", "competition", "funding", "research")
# the push rule a plan carries when the owner did not answer the upload question: setup's recommendation
DEFAULT_PUSH_RULE = "a seat asks the owner before each push and pushes on the owner's yes."
# the start of the catalogue Frontend engineer's why when it stays beside the frontend splits
FRONTEND_HOLDS = "holds the UI apps without a frontend seat of their own: "


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


# the signal keys each catalogue seat's rule in needs() reads; spec_signals() reports them so a proposal
# can say what it rests on, and a declined one can come back when one of them is new
TEAM_SIGNALS = {
    "engineering": ("code",), "testing": ("tests", "ci"), "frontend": ("ui_web",), "mobile": ("mobile",),
    "design": ("ui_web", "mobile", "game", "desktop", "extension"),
    "user": ("auth", "personal_data", "email", "payments", "landing", "ui_web", "mobile", "game", "desktop", "extension"),
    "product": ("payments", "auth", "landing", "personal_data", "email", "ui_web", "mobile"),
    "platform": ("deploy",), "ml": ("ml",), "data": ("data_pipelines",),
    "research": ("data_pipelines", "analytics", "ml"), "payments": ("payments",),
    "sales": ("payments", "landing"), "competition": ("payments", "landing"), "funding": ("payments", "landing"),
    "seo": ("landing", "content"), "social": ("content",), "motion": ("video",),
    "customer-success": ("auth", "email"), "compliance": ("personal_data", "licence_data"),
    "security": ("auth", "payments", "personal_data", "security_policy"), "docs": ("docs_site", "oss", "api"),
    "community": ("oss",), "game-design": ("game",), "i18n": ("i18n",),
}


def spec_signals(spec: dict, scan: dict) -> list[str]:
    """The repo signal keys present in `scan` that a seat spec rests on (empty for size-based seats)."""
    s = scan.get("signals", {})
    kind = spec.get("type", "catalogue")
    if kind == "merge":
        keys = [k for m in spec["of"] for k in TEAM_SIGNALS.get(m, ())]
    elif kind == "derive":
        keys = ["ui_web"] if spec.get("base") == "seat-frontend" and spec["team"].startswith("frontend-") else \
            [sig for sig, role in DERIVED_ROLES.items() if role["team"] == spec["team"]]
    else:
        keys = list(TEAM_SIGNALS.get(spec["team"], ()))
    return sorted({k for k in keys if s.get(k)})


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


def coordination(n_other: int, option: str) -> dict[str, str]:
    """The coordination seats a team of `n_other` other seats earns (others leave out the Chief of Staff and
    the Scope Trimmer), each with why: the Chief of Staff at 5 or more (7 or more in lean), the Scope
    Trimmer at 10 or more. plan.build seats them; reevaluate.py proposes and keeps them by the same rule."""
    out: dict[str, str] = {}
    if n_other >= (7 if option == "lean" else 5):
        out["chief-of-staff"] = f"{n_other} other seats: one seat talks to you and keeps the tracker"
    if n_other >= 10:
        out["scope-trimmer"] = f"{n_other} other seats: someone cuts the queue to the shortest path to a customer"
    return out


def merge_allowed(team: str, present: list[str], scan: dict, after_setup: bool = False) -> bool:
    """Whether the members `present` may sit in MERGES[team]: two or more of them; never Engineering &
    Platform past 2,000 source files; a check seat only in a check merge; and, for a merge proposed after
    setup (`after_setup`), no ALWAYS seat (the CEO, the Bar Raiser) among them."""
    m = MERGES[team]
    if len(present) < 2:
        return False
    if team == "engineering-platform" and scan.get("size", {}).get("code_files", 0) > 2000:
        return False
    if any(t in CHECK_SEATS for t in present) and m["kind"] != "check":
        return False
    if after_setup and any(t in ALWAYS for t in present):
        return False
    return True


def seat_names(teams, marks: bool = True) -> str:
    """Catalogue teams as seat names joined in words: "🧪 Testing and ⚖️ Bar Raiser"."""
    cat = catalogue()
    names = [(f"{cat[t]['mark']} {cat[t]['seat']}" if marks else cat[t]["seat"]) if t in cat else t for t in teams]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""


def merge_spec(team: str, present: list[str]) -> dict:
    m = MERGES[team]
    return {"team": team, "type": "merge", "of": list(present), "seat": m["seat"], "mark": m["mark"],
            "kind": m["kind"], "why": f"{m['why']} (holds {seat_names(present, marks=False)})"}


def apply_merges(seats: dict[str, str], groups, scan: dict) -> list[dict]:
    """Replace members by merged seats, in place; return the merge specs. A member taken by one merge
    is gone from `seats`, so no later merge can claim it."""
    out = []
    for team in groups:
        present = [t for t in MERGES[team]["of"] if t in seats]
        if not merge_allowed(team, present, scan):
            continue
        for t in present:
            seats.pop(t)
        out.append(merge_spec(team, present))
    return out


def norm_mark(mark: str) -> str:
    """A mark compared without the U+FE0F variation selector."""
    return mark.replace("\ufe0f", "")


def split_marks(taken=()) -> list[str]:
    """SPLIT_MARKS left after every catalogue, merge and derived mark and the marks in `taken`."""
    used = {norm_mark(r["mark"]) for r in catalogue().values()} | {norm_mark(m["mark"]) for m in MERGES.values()}
    used |= {norm_mark(d["mark"]) for d in DERIVED_ROLES.values()} | {norm_mark(m) for m in taken}
    return [m for m in SPLIT_MARKS if norm_mark(m) not in used]


def ui_apps(scan: dict) -> tuple[list[str], int]:
    """(the web UI app folders scan.py listed, the full count, which may run past the list)."""
    size = scan.get("size", {})
    apps = [a for a in size.get("ui_apps", []) if a != "."]
    return apps, max(len(apps), size.get("ui_app_count", 0) - (1 if "." in size.get("ui_apps", []) else 0))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "app"


def app_slugs(apps: list[str], held: dict | None = None) -> list[str]:
    """One unique [a-z0-9-] slug per app folder: the seated slug for an app in `held` ({folder: slug or
    (slug, mark)}); else its last name, or its whole path when another app shares that name or a held seat
    already uses it."""
    kept = {a: (v[0] if isinstance(v, (tuple, list)) else v) for a, v in (held or {}).items()}
    last = [slugify(a.rstrip("/").split("/")[-1]) for a in apps]
    reserved = {kept[a] for a in apps if a in kept}
    slugs = [kept[a] if a in kept else slugify(a) if last.count(s) > 1 or s in reserved else s
             for a, s in zip(apps, last)]
    out: list[str] = []
    for a, s in zip(apps, slugs):
        base, n = s, 2
        while s in out or (a not in kept and s in reserved):
            s, n = f"{base}-{n}", n + 1
        out.append(s)
    return out


def frontend_holds(scan: dict, splits: list[dict]) -> str:
    """Why the catalogue Frontend engineer stays beside the frontend splits: the web app at the repository
    root and the UI apps no split holds, else "" (the splits hold every app)."""
    apps, count = ui_apps(scan)
    split_apps = {s.get("register", "").replace("the UI code under ", "", 1).rstrip("/") for s in splits}
    parts = (["the app at the repository root"] if "." in scan.get("size", {}).get("ui_apps", []) else [])
    parts += [a for a in apps if a not in split_apps]
    more = count - len(apps)
    if not parts and more <= 0:
        return ""
    listing = ", ".join(parts)
    if more > 0:
        listing = f"{listing} and {more} more" if listing else f"{more} more"
    return FRONTEND_HOLDS + listing


def ui_splits(scan: dict, taken_marks=(), held: dict | None = None) -> list[dict]:
    """One frontend seat per web UI app in a folder once there are two or more, for MAX_SPLITS apps; past
    that, or beside a web app at the repository root, the catalogue Frontend engineer holds the rest
    (build keeps it). `held` ({app folder: (slug, mark)}) names the splits already seated: those apps come
    first and keep their slug and mark. New marks avoid `taken_marks`."""
    apps, count = ui_apps(scan)
    if count < 2 or len(apps) < 2:
        return []
    held = {a: (v if isinstance(v, (tuple, list)) else (v, "")) for a, v in (held or {}).items()}
    kept = [a for a in apps if a in held]
    marks = split_marks(taken_marks)
    limit = max(len(kept), min(MAX_SPLITS, len(kept) + len(marks)))
    chosen = set(kept + [a for a in apps if a not in held][:limit - len(kept)])
    split = [a for a in apps if a in chosen]
    rest = count - len(split) + (1 if "." in scan.get("size", {}).get("ui_apps", []) else 0)
    free = iter(marks)
    out = []
    for app, slug in zip(split, app_slugs(split, {a: held[a][0] for a in kept})):
        mark = held[app][1] if app in held and held[app][1] else next(free, "")
        scope = (f"only {app}/; each other UI app has its own frontend seat" if not rest else
                 f"only {app}/; the other UI apps have their own frontend seats or sit with the Frontend engineer")
        out.append({"team": f"frontend-{slug}", "type": "derive", "base": "seat-frontend",
                    "seat": f"Frontend engineer ({slug})", "mark": mark, "kind": "implementation",
                    "register": f"the UI code under {app}/", "reports_to": "Engineering", "scope": scope,
                    "why": f"separate: {count} UI apps ({', '.join(apps)}{', …' if count > len(apps) else ''})"})
    assert len({s["team"] for s in out}) == len(out), "split slugs must be unique"
    return out


def build(scan: dict, option: str, held: dict | None = None) -> list[dict]:
    """One option's seat specs. `held` names the frontend splits already seated (see ui_splits)."""
    core, opt, derived = needs(scan)
    seats = dict(core)
    size = size_class(scan)
    merges: list[dict] = []
    splits: list[dict] = []
    if option == "full":
        seats.update({k: v for k, v in opt.items() if k not in seats})
        splits = ui_splits(scan, held=held)
    elif option == "recommended":
        if size == "tiny":
            for t in ("scope-trimmer", "competition", "funding", "research"):
                if not (t == "research" and scan.get("signals", {}).get("data_pipelines")):
                    seats.pop(t, None)
            merges = apply_merges(seats, list(MERGES), scan)
        elif size == "small":
            merges = apply_merges(seats, SMALL_MERGES, scan)
        elif size == "large":
            splits = ui_splits(scan, held=held)
    else:  # lean
        for t in LEAN_DROPS:
            if t not in ALWAYS:
                seats.pop(t, None)
        merges = apply_merges(seats, list(MERGES), scan)
    if splits:
        holds = frontend_holds(scan, splits)  # more UI apps than split seats, or one at the root
        if holds:
            seats["frontend"] = holds
        else:
            seats.pop("frontend", None)
    n = len(seats) + len(merges) + len(splits) + len(derived)
    for team, why in coordination(n, option).items():
        seats.setdefault(team, why)
    cat = catalogue()
    ordered = [{"team": t, "type": "catalogue", "why": seats[t]} for t in cat if t in seats]
    return ordered + merges + splits + derived


def options(scan: dict) -> dict:
    return {"size": size_class(scan), "lean": build(scan, "lean"), "recommended": build(scan, "recommended"),
            "full": build(scan, "full")}


# plain sentences for the owner, one per scan signal key
PLAIN_SIGNALS = {
    "ui_web": "It has a web interface", "mobile": "It has a mobile app", "api": "It serves an API",
    "db": "It keeps a database", "ml": "It trains or calls machine-learning models",
    "data_pipelines": "It runs data pipelines", "payments": "It takes payments", "auth": "People sign in to it",
    "analytics": "It measures how people use it", "i18n": "It is translated into other languages",
    "email": "It sends email", "game": "It is a game", "video": "It makes video", "desktop": "It has a desktop app",
    "blockchain": "It deploys smart contracts", "docs_site": "It publishes a documentation site",
    "deploy": "It is deployed", "ci": "Every change runs automated checks", "tests": "It has tests",
    "content": "It publishes posts or other content", "landing": "It has a public landing or pricing page",
    "migrations": "Its database schema changes over time", "security_policy": "It has a security policy",
    "hardware": "It runs on a device with firmware", "extension": "It is a browser extension",
    "oss": "It is open source and takes contributions", "licence_data": "It uses third-party data under licence",
    "personal_data": "It stores personal data", "code": "It has source code",
    "monorepo": "Several packages live in one repository",
}
OPTION_LINES = {
    "recommended": "What the evidence calls for, scaled to the project's size.",
    "lean": "The fewest sessions: every merge that fits, the optional seats left out.",
    "full": "Every seat separate, the optional seats added.",
}


def plain_evidence(evidence: str) -> str:
    if evidence.startswith("dependency "):
        return f"it uses {evidence[len('dependency '):]}"
    return evidence


def plain_why(why: str) -> str:
    """A spec's why as a sentence for the owner: a signal key becomes words ("ui_web: dependency react" ->
    "It has a web interface (it uses react)."); other reasons are capitalised and closed with a full stop."""
    m = re.match(r"^([a-z0-9_]+): (.+)$", why or "")
    if m and m.group(1) in PLAIN_SIGNALS:
        text = f"{PLAIN_SIGNALS[m.group(1)]} ({plain_evidence(m.group(2))})"
    else:
        m = re.match(r"^(\d+) other seats: (.+)$", why or "")
        text = f"With {m.group(1)} other seats, {m.group(2)}" if m else (why or "").strip()
    text = text[:1].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."


def describe(spec: dict, cat: dict) -> tuple[str, str, str]:
    """(seat name with mark, how it is seated, why) in plain words, for one seat spec."""
    if spec["type"] == "catalogue":
        row = cat[spec["team"]]
        return f"{row['mark']} {row['seat']}", "its own seat", plain_why(spec["why"])
    if spec["type"] == "merge":
        why = MERGES.get(spec["team"], {}).get("why") or spec["why"]
        return (f"{spec['mark']} {spec['seat']}", f"one seat holding {seat_names(spec['of'])}", plain_why(why))
    if spec.get("base") == "seat-frontend" and spec["team"].startswith("frontend-"):
        app = spec.get("register", "").replace("the UI code under ", "")
        apps = spec["why"].replace("separate: ", "", 1).replace(" UI apps (", " web apps (", 1)
        if "Frontend engineer" in spec.get("scope", ""):  # the catalogue seat holds the apps past the splits
            fe = cat.get("frontend", {})
            return (f"{spec['mark']} {spec['seat']}", f"a frontend seat of its own, for {app}",
                    f"The project has {apps}; this one gets its own frontend seat, and the "
                    f"{fe.get('mark', '')} {fe.get('seat', 'Frontend engineer')} holds the apps without one.")
        return (f"{spec['mark']} {spec['seat']}", f"one frontend seat per web app, this one for {app}",
                f"The project has {apps}; each gets its own frontend seat.")
    return (f"{spec['mark']} {spec['seat']}", "a new role: its rulebook is written for it before it starts work",
            plain_why(spec["why"]))


def to_markdown(opts: dict, scan: dict | None = None) -> str:
    """The three options as the owner reads them: Recommended first, then Lean and Full; seat names with
    marks; every reason a plain sentence (no signal keys, no team slugs)."""
    cat = catalogue()
    size = (scan or {}).get("size", {})
    count = lambda n, one, many: f"{n} {one if n == 1 else many}"  # noqa: E731
    facts = [count(size.get("code_files", 0), "source file", "source files"), count(size.get("commits", 0), "commit", "commits"),
             count(size.get("contributors", 0), "person", "people")] if scan else []
    lines = [f"The project is **{opts['size']}**" + (f": {', '.join(facts)}." if facts else ".") + "\n"]
    for name in ("recommended", "lean", "full"):
        seats = opts[name]
        lines += [f"### {name.capitalize()}: {len(seats)} seats",
                  "", OPTION_LINES[name], "", "| Seat | How | Why |", "|---|---|---|"]
        for x in seats:
            lines.append("| " + " | ".join(describe(x, cat)) + " |")
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
    ap.add_argument("--push-rule", default=DEFAULT_PUSH_RULE)
    a = ap.parse_args()
    scan = json.loads(a.scan.read_text(encoding="utf-8"))
    opts = options(scan)
    if a.option:
        plan = {"project": a.project or scan.get("root"), "option": a.option, "size": opts["size"],
                "owner_acts": a.owner_acts, "push_rule": a.push_rule, "seats": opts[a.option], "retire": [],
                "offered": sorted({s["team"] for s in opts[a.option]} | {m for s in opts[a.option] for m in s.get("of", [])})}
        text = json.dumps(plan, indent=2, ensure_ascii=False)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(text + "\n", encoding="utf-8")
        print(text)
    elif a.markdown:
        print(to_markdown(opts, scan))
    else:
        print(json.dumps(opts, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
