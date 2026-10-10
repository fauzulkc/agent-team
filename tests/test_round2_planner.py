"""Regression tests for the second fix round of plan.py, scan.py and reevaluate.py.

    python3 -m unittest tests.test_round2_planner -v        (from the repo root; stdlib only)

One test per fixed behaviour: split seats keep their names when a newer app shares a folder name, a
fifth UI app or a web app at the repository root keeps the Frontend engineer, the owner-facing split
wording past four apps, the default push rule, the Python 3.9 pyproject reader, Xcode projects and icon
folders in the mobile signal, seats struck from the setup plan, a why that names the evidence new since
setup, plain-word notes and repo changes, a merged seat's members' commit prefixes, a merge member
missing beside a seated merge, singular counts, and the tracker's BLOCKED dates and senders.
"""
from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "team-setup" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import plan as planner  # noqa: E402
import reevaluate as reevaluator  # noqa: E402
import repo_fixtures as fx  # noqa: E402
import scan as scanner  # noqa: E402
import teamlib  # noqa: E402

CAT = teamlib.catalogue()
LONG_AGO = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
_tmp: tempfile.TemporaryDirectory | None = None
BASE = Path()
ENV: dict[str, str] = {}
_n = [0]


def setUpModule() -> None:  # noqa: N802
    global _tmp, BASE, ENV
    _tmp = tempfile.TemporaryDirectory(prefix="agent-team-r2p-")
    BASE = Path(_tmp.name).resolve()
    (BASE / "home").mkdir()
    ENV = fx.isolated_env(BASE / "home", BASE)


def tearDownModule() -> None:  # noqa: N802
    if _tmp is not None:
        _tmp.cleanup()


def new_dir(name: str) -> Path:
    _n[0] += 1
    d = BASE / f"{name}-{_n[0]}"
    d.mkdir()
    return d


def run(script: str, *args) -> str:
    res = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True, encoding="utf-8",
                         env=ENV)
    if res.returncode != 0:
        raise AssertionError(f"{script} {args} exited {res.returncode}\n{res.stdout}\n{res.stderr}")
    return res.stdout


def seat_up(root: Path, option: str, edit=None) -> None:
    """Setup as team-setup runs it; `edit(plan)` is the owner's edit of plan.json before scaffold applies it."""
    run("scan.py", "--root", root, "--save")
    plan_file = root / "docs" / "team" / "plan.json"
    run("plan.py", "--scan", root / "docs" / "team" / "scan.json", "--option", option, "--out", plan_file,
        "--project", "Tally")
    if edit:
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        edit(plan)
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    run("scaffold.py", "--root", root, "--plan", plan_file)


def reevaluate(root: Path) -> dict:
    return json.loads(run("reevaluate.py", "--root", root, "--json"))


def keys(result: dict) -> list[str]:
    return [p["key"] for p in result["proposals"]]


def proposal(result: dict, key: str) -> dict:
    found = [p for p in result["proposals"] if p["key"] == key]
    assert len(found) == 1, (key, keys(result))
    return found[0]


def backdate(root: Path) -> None:
    lock_file = root / "docs" / "team" / "seat-skills.lock"
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    for entry in lock.values():
        entry["seated"] = LONG_AGO
    lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def name(team: str) -> str:
    r = CAT.get(team) or teamlib.MERGES[team]
    return f"{r['mark']} {r['seat']}"


def app_scan(apps: list[str], code_files: int = 5000) -> dict:
    return {"size": {"code_files": code_files, "commits": 900, "contributors": 12, "ui_apps": apps,
                     "ui_app_count": len(apps)},
            "signals": {"code": [f"{code_files} source files"], "ui_web": ["dependency react-dom"]}}


class PlanRound2Tests(unittest.TestCase):
    def test_a_seated_split_keeps_its_name_when_a_newer_app_shares_it(self):
        scan = app_scan(["apps/admin", "apps/web", "sites/web"])
        held = {"apps/admin": ("admin", "💻"), "apps/web": ("web", "🪟")}
        splits = planner.ui_splits(scan, taken_marks=["💻", "🪟"], held=held)
        self.assertEqual([(s["team"], s["register"]) for s in splits],
                         [("frontend-admin", "the UI code under apps/admin/"), ("frontend-web", "the UI code under apps/web/"),
                          ("frontend-sites-web", "the UI code under sites/web/")])
        self.assertEqual([s["mark"] for s in splits][:2], ["💻", "🪟"])
        self.assertEqual([s["team"] for s in planner.ui_splits(scan)],
                         ["frontend-admin", "frontend-apps-web", "frontend-sites-web"], "no seated split: the longer names")

    def test_held_splits_come_first_and_a_fifth_app_sits_with_the_frontend_engineer(self):
        scan = app_scan(["apps/aaa", "apps/blog", "apps/shop", "apps/web", "apps/zoo"])
        held = {a: (a.split("/")[1], m) for a, m in zip(["apps/blog", "apps/shop", "apps/web", "apps/zoo"], "💻🪟📟🧩")}
        seats = planner.build(scan, "full", held=held)
        self.assertEqual([s["team"] for s in seats if s["team"].startswith("frontend-")],
                         ["frontend-blog", "frontend-shop", "frontend-web", "frontend-zoo"])
        holder = [s for s in seats if s["team"] == "frontend"]
        self.assertEqual(holder[0]["why"], planner.FRONTEND_HOLDS + "apps/aaa")

    def test_a_web_app_at_the_root_keeps_the_frontend_engineer(self):
        scan = app_scan([".", "admin", "docs"], code_files=100)
        seats = planner.build(scan, "full")
        holder = [s for s in seats if s["team"] == "frontend"]
        self.assertEqual(len(holder), 1, [s["team"] for s in seats])
        self.assertEqual(holder[0]["why"], planner.FRONTEND_HOLDS + "the app at the repository root")
        for s in seats:
            if s["team"].startswith("frontend-"):
                self.assertIn("sit with the Frontend engineer", s["scope"])

    def test_past_four_apps_the_owner_is_not_told_every_app_gets_a_seat(self):
        scan = app_scan([f"apps/{c}" for c in "abcdef"])
        md = planner.to_markdown(planner.options(scan), scan)
        self.assertNotIn("each gets its own frontend seat", md)
        self.assertNotIn("one frontend seat per web app", md)
        self.assertIn(f"this one gets its own frontend seat, and the {name('frontend')} holds the apps without one", md)

    def test_the_default_push_rule_is_setups_recommendation(self):
        root = fx.build_lib(new_dir("push"), ENV)
        run("scan.py", "--root", root, "--save")
        out = json.loads(run("plan.py", "--scan", root / "docs" / "team" / "scan.json", "--option", "recommended"))
        self.assertEqual(out["push_rule"], "a seat asks the owner before each push and pushes on the owner's yes.")


class ScanRound2Tests(unittest.TestCase):
    CASES = {
        "inline optional": ('[project]\ndependencies = ["FastAPI[all]"]\n'
                            'optional-dependencies = { ml = ["torch>=2"], dev = ["ruff"] }\n', {"fastapi", "torch", "ruff"}),
        "dotted optional": ('[project]\ndependencies = ["fastapi"]\noptional-dependencies.ml = ["torch>=2"]\n',
                            {"fastapi", "torch"}),
        "escaped quote": ('[project]\ndependencies = [\n  "fastapi",\n  "weird \\"x",\n'
                          '  "stripe",\n]\n', {"fastapi", "weird", "stripe"}),
        "poetry sub-table": ('[tool.poetry.dependencies]\npython = "^3.11"\n\n[tool.poetry.dependencies.stripe]\n'
                             'version = "^5"\n', {"stripe"}),
        "include-group": ('[dependency-groups]\ndev = ["pytest", {include-group = "x"}]\n', {"pytest"}),
    }

    def test_the_fallback_reader_matches_tomllib(self):
        for label, (text, want) in self.CASES.items():
            with self.subTest(label):
                self.assertEqual(scanner.pyproject_deps_fallback(text), want)
                if scanner.tomllib is not None:
                    self.assertEqual(scanner.pyproject_deps(text), want)

    def test_an_xcode_project_is_a_mobile_app(self):
        root = new_dir("ios")
        fx.put(root, "Tally.xcodeproj/project.pbxproj", "// !$*UTF8*$!\n")
        fx.put(root, "Tally/TallyApp.swift", "import SwiftUI\n")
        self.assertEqual(scanner.scan(root)["signals"].get("mobile"), ["Tally.xcodeproj/project.pbxproj"])

    def test_icon_folders_named_android_or_ios_are_not_a_mobile_app(self):
        root = new_dir("pwa")
        fx.put_json(root, "package.json", {"name": "tally", "dependencies": {"react": "18.3.1", "react-dom": "18.3.1"}})
        fx.put(root, "public/icons/android/launcher-192.png", "png")
        fx.put(root, "public/icons/ios/180.png", "png")
        fx.put(root, "assets/android/x.png", "png")
        self.assertNotIn("mobile", scanner.scan(root)["signals"])
        fx.put(root, "apps/mobile/ios/Podfile.lock", "lock")
        self.assertEqual(scanner.scan(root)["signals"].get("mobile"), ["apps/mobile/ios/Podfile.lock"])


class ReevaluateUnitTests(unittest.TestCase):
    ROWS = [{"mark": m, "seat": s, "skill": f"seat-{t}", "team": t, "kind": "", "register": "", "reports_to": ""}
            for m, s, t in (("⚙️", "Engineering", "engineering"), ("📐", "Design", "design"),
                            ("💼", "Sales & Marketing", "sales"), ("🎨", "Product & Design", "product-design"))]

    def test_a_due_date_does_not_age_a_blocked_row_and_a_team_line_counts_for_its_seat(self):
        text = ("| # | task | seat | done when | status | note |\n|---|---|---|---|---|---|\n"
                "| 1 | pricing copy | 💼 Sales & Marketing | the page reads right by 2026-01-01 | BLOCKED on 📐 Design | - |\n"
                "| 2 | icons | 📐 Design | done | BLOCKED since 2026-01-02 | - |\n\n"
                "2026-10-03 · 📐 Design team (called by ⚙️ Engineering) → ⚙️ Engineering · RESULT · BLOCKED on copy\n")
        got = reevaluator.tracker_blocked(text, self.ROWS[:3], datetime.date(2026, 9, 10))
        self.assertEqual(got, {"sales": 1, "design": 1})

    def test_a_members_prefix_counts_for_its_merged_seat(self):
        rows = [self.ROWS[0], self.ROWS[3]]
        aliases = reevaluator.alias_map(rows, {"product-design": ["product", "design"]})
        self.assertEqual((aliases["design"], aliases["product"]), ("product-design", "product-design"))
        self.assertEqual(reevaluator.attribute("design: invoice list", aliases), "product-design")
        aliases = reevaluator.alias_map(self.ROWS[:2] + [self.ROWS[3]], {"product-design": ["product", "design"]})
        self.assertEqual(aliases["design"], "design", "a member with a row of its own keeps its prefix")


class ReevaluateRound2Tests(unittest.TestCase):
    def test_a_newer_app_with_the_same_name_never_seats_a_seated_app_twice(self):
        root = fx.build_monorepo(new_dir("mono-slug"), ENV)
        seat_up(root, "full")
        fx.put_json(root, "packages/web/package.json", {"name": "web2", "dependencies": {"react-dom": "18.3.1"}})
        fx.commit_all(root, "chore: a second web app", ENV)
        result = reevaluate(root)
        fronts = [k for k in keys(result) if k.startswith("add:frontend")]
        self.assertEqual(fronts, ["add:frontend-packages-web"])
        add = proposal(result, "add:frontend-packages-web")
        self.assertEqual(add["seats"][0]["register"], "the UI code under packages/web/")
        self.assertTrue(add["why"].startswith("The project has 3 web apps (apps/admin, apps/web, packages/web); "), add["why"])

    def test_a_fifth_app_beside_four_seated_splits_proposes_the_frontend_engineer(self):
        root = fx.build_monorepo(new_dir("mono-five"), ENV)
        for app in ("blog", "shop"):
            fx.put_json(root, f"apps/{app}/package.json", {"name": app, "dependencies": {"react-dom": "18.3.1"}})
        fx.commit_all(root, "chore: two more apps", ENV)
        seat_up(root, "full")
        self.assertNotIn("frontend", [r["team"] for r in teamlib.roster(root / "docs" / "TEAM.md")])
        fx.put_json(root, "apps/zoo/package.json", {"name": "zoo", "dependencies": {"react-dom": "18.3.1"}})
        fx.commit_all(root, "chore: a fifth app", ENV)
        result = reevaluate(root)
        self.assertEqual(proposal(result, "add:frontend")["why"],
                         "Holds the UI apps without a frontend seat of their own: apps/zoo.")
        self.assertFalse([k for k in keys(result) if k.startswith("add:frontend-")], keys(result))

    def test_seats_struck_from_the_setup_plan_are_not_proposed_again(self):
        root = fx.build_saas(new_dir("saas-struck"), ENV)
        seat_up(root, "recommended", edit=lambda p: p.update(seats=[s for s in p["seats"]
                                                                   if s["team"] not in ("security", "user")]))
        result = reevaluate(root)
        self.assertFalse({"add:security", "add:user"} & set(keys(result)), keys(result))
        self.assertIn(f"{name('security')} was left out of the team at setup and nothing new calls for it, so it is "
                      "not proposed again.", result["notes"])

    def test_a_returning_seat_names_the_evidence_that_is_new(self):
        root = fx.build_saas(new_dir("saas-new-ev"), ENV)
        seat_up(root, "recommended")
        run("scaffold.py", "--root", root, "--retire", "security")
        fx.put(root, "SECURITY.md", "# Reporting\n")
        fx.commit_all(root, "chore: a security policy", ENV)
        result = reevaluate(root)
        self.assertEqual(proposal(result, "add:security")["why"],
                         "People sign in to it (it uses next-auth). New since setup: it has a security policy (SECURITY.md).")
        md = run("reevaluate.py", "--root", root)
        self.assertIn("New since setup: it has a security policy.", md)
        self.assertNotIn("security_policy", md)

    def test_a_retired_coordination_seat_note_says_what_the_script_knows(self):
        root = fx.build_saas(new_dir("saas-st"), ENV)
        seat_up(root, "recommended")
        run("scaffold.py", "--root", root, "--retire", "scope-trimmer")
        notes = [n for n in reevaluate(root)["notes"] if "Scope Trimmer" in n]
        self.assertEqual(len(notes), 1, notes)
        self.assertNotIn("unchanged", notes[0])
        self.assertIn("was retired, so it is not proposed again. With 10 other seats the usual rule would seat it", notes[0])

    def test_without_a_baseline_notes_never_claim_unchanged_evidence(self):
        root = fx.build_saas(new_dir("saas-nobase"), ENV)
        seat_up(root, "full")
        run("scaffold.py", "--root", root, "--retire", "social")
        (root / "docs" / "team" / "scan.json").unlink()
        notes = [n for n in reevaluate(root)["notes"] if "Social Media Manager" in n]
        self.assertEqual(len(notes), 1, notes)
        self.assertIn("there is no setup baseline to tell whether its evidence changed", notes[0])
        lib = fx.build_lib(new_dir("lib-declined"), ENV)
        run("scaffold.py", "--root", lib, "--project", "Tally", "--seats", "engineering,testing,docs,community")
        (lib / "docs" / "team" / "declined.json").write_text(json.dumps([
            {"key": "add:chief-of-staff", "title": f"Add {name('chief-of-staff')}", "action": "add", "signals": [],
             "date": "2026-01-01", "decision": "DEC-2"}]), encoding="utf-8")
        result = reevaluate(lib)
        self.assertNotIn("add:chief-of-staff", keys(result))
        self.assertIn(f"Add {name('chief-of-staff')} was declined on 2026-01-01; it is not proposed again until you "
                      "ask for it.", result["notes"])

    def test_a_merge_member_missing_beside_its_seated_merge_is_proposed(self):
        root = fx.build_saas(new_dir("saas-noblog"), ENV)
        shutil.rmtree(root / "blog")
        fx.commit_all(root, "chore: no blog yet", ENV)
        seat_up(root, "lean")
        self.assertEqual(teamlib.coverage(root).get("sales"), "growth")
        fx.put(root, "blog/launch.md", "# Tally is live\n")
        fx.commit_all(root, "chore: the launch post", ENV)
        result = reevaluate(root)
        self.assertEqual(result["new_signals"], ["content"])
        self.assertIn("add:social", keys(result))
        self.assertIn("publishes posts or other content", proposal(result, "add:social")["why"])

    def test_merged_seat_commits_and_singular_counts(self):
        root = fx.build_saas(new_dir("saas-merged"), ENV)
        seat_up(root, "lean")
        fx.empty_commits(root, ["design: invoice list pass 1", "platform: fly config"], ENV)
        stats = reevaluate(root)["activity"]["stats"]
        self.assertEqual((stats["product-design"]["commits"], stats["engineering-platform"]["commits"]), (1, 1))
        full = fx.build_saas(new_dir("saas-one"), ENV)
        seat_up(full, "full")
        backdate(full)
        fx.empty_commits(full, ["design: colours"], ENV)
        why = proposal(reevaluate(full), "merge:product-design")["why"]
        self.assertIn(f"{name('design')} 1 commit, 0 runs", why)
        self.assertIn(f"{name('product')} 0 commits, 0 runs", why)


if __name__ == "__main__":
    unittest.main()
