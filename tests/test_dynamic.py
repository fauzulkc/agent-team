"""Dynamic seats, end to end: scan, plan, scaffold and re-evaluate on fixture repos.

    python3 -m unittest discover -s tests -v        (from the repo root; stdlib only, no network)

Each test builds its fixture repos (tests/repo_fixtures.py) in one temporary folder, runs the
team-setup scripts on them (in process for scan and plan, as commands for everything that writes),
and checks what the scripts promise in their docstrings. Git runs with a fixed identity and no user
config, and never climbs above the temporary folder; HOME points at an empty folder so no globally
installed skill can stand in for a project's rulebook.

A class that needs a seated team seats it once in setUpClass; a test that changes it works on a
copy (`clone`). Re-evaluation holds back every retire and merge proposal for a seat seated inside its
window, so a test that expects one first moves the lock's `seated` dates out of the window (`backdate`).

No test is marked expectedFailure. A known defect is written as a plain test of the right behaviour
and fails until the script is fixed; a precondition is an assertion of its own, never hidden inside
an expected failure.
"""
from __future__ import annotations

import copy
import datetime
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SKILL = REPO / "skills" / "team-setup"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))

import plan as planner  # noqa: E402
import repo_fixtures as fx  # noqa: E402
import scan as scanner  # noqa: E402
import seatgen  # noqa: E402
import teamlib  # noqa: E402

CAT = teamlib.catalogue()
GIT_KEYS = ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CEILING_DIRECTORIES", "GIT_TERMINAL_PROMPT")
TODAY = datetime.date.today().isoformat()
LONG_AGO = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
_tmp: tempfile.TemporaryDirectory | None = None
_saved_env: dict[str, str | None] = {}
_counter = itertools.count()
BASE = Path()
ENV: dict[str, str] = {}


def setUpModule() -> None:  # noqa: N802 (unittest's name)
    global _tmp, BASE, ENV
    _tmp = tempfile.TemporaryDirectory(prefix="agent-team-tests-")
    BASE = Path(_tmp.name).resolve()
    (BASE / "home").mkdir()
    ENV = fx.isolated_env(BASE / "home", BASE)
    for k in GIT_KEYS:  # the in-process scan calls git too
        _saved_env[k] = os.environ.get(k)
        os.environ[k] = ENV[k]


def tearDownModule() -> None:  # noqa: N802
    for k, v in _saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    if _tmp is not None:
        _tmp.cleanup()


# ---------------------------------------------------------------------------- helpers

def new_dir(name: str) -> Path:
    d = BASE / f"{name}-{next(_counter)}"
    d.mkdir()
    return d


def clone(src: Path, name: str) -> Path:
    """A private copy of a seated fixture (git history included), for a test that changes it."""
    dst = new_dir(name)
    shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
    return dst


def run(script: str, *args, scripts: Path = SCRIPTS, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run([sys.executable, str(scripts / script), *map(str, args)], capture_output=True,
                         text=True, env=ENV)
    if check and res.returncode != 0:
        raise AssertionError(f"{script} {' '.join(map(str, args))} exited {res.returncode}\n"
                             f"--- stdout\n{res.stdout}\n--- stderr\n{res.stderr}")
    return res


def scaffold(root: Path, *args, check: bool = True) -> subprocess.CompletedProcess:
    return run("scaffold.py", "--root", root, *args, check=check)


def gen_check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "scripts" / "gen-team-agents.py"), "--check"],
                          capture_output=True, text=True, env=ENV, cwd=root)


def gen_write(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "scripts" / "gen-team-agents.py")],
                          capture_output=True, text=True, env=ENV, cwd=root, check=True)


def seat_up(root: Path, option: str, record: str | None = None) -> tuple[dict, str]:
    """Setup as the team-setup skill runs it: save the scan baseline, write one option's plan, scaffold it."""
    run("scan.py", "--root", root, "--save")
    plan_file = root / "docs" / "team" / "plan.json"
    run("plan.py", "--scan", root / "docs" / "team" / "scan.json", "--option", option, "--out", plan_file,
        "--project", "Tally")
    args = ["--plan", plan_file] + (["--record", record] if record else [])
    out = scaffold(root, *args).stdout
    return json.loads(plan_file.read_text(encoding="utf-8")), out


def roster_teams(root: Path) -> list[str]:
    return [r["team"] for r in teamlib.roster(root / "docs" / "TEAM.md")]


def reevaluate(root: Path, *extra) -> dict:
    return json.loads(run("reevaluate.py", "--root", root, "--json", *extra).stdout)


def keys(result: dict) -> list[str]:
    return [p["key"] for p in result["proposals"]]


def backdate(root: Path, date: str = LONG_AGO) -> None:
    """Move every lock entry's `seated` date out of the re-evaluation window."""
    lock_file = root / "docs" / "team" / "seat-skills.lock"
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    for entry in lock.values():
        entry["seated"] = date
    lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def commit_dated(root: Path, subject: str, days_ago: int) -> None:
    """An empty commit authored and committed `days_ago` days before today."""
    when = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat() + "T12:00:00"
    fx.git(root, "commit", "-q", "--allow-empty", "-m", subject,
           env={**ENV, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})


def name(team: str) -> str:
    """A catalogue or merged seat in plain words, mark first."""
    r = CAT.get(team) or teamlib.MERGES[team]
    return f"{r['mark']} {r['seat']}"


def mark_of(spec: dict) -> str:
    return CAT[spec["team"]]["mark"] if spec.get("type", "catalogue") == "catalogue" else spec["mark"]


def strip_authoring_blocks(root: Path) -> list[Path]:
    """What the session does after rewriting a derived rulebook for its role: delete the banner line."""
    done = []
    for f in (root / ".claude" / "skills").glob("seat-*/SKILL.md"):
        text = f.read_text(encoding="utf-8")
        if "AUTHORING NEEDED" in text:
            f.write_text("".join(l for l in text.splitlines(keepends=True) if "AUTHORING NEEDED" not in l),
                         encoding="utf-8")
            done.append(f)
    return done


def snapshot(*dirs: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for d in dirs if d.exists() for p in sorted(d.rglob("*")) if p.is_file()}


def decision_rows(root: Path) -> dict[int, str]:
    text = (root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    return {int(m.group(1)): line for line in text.splitlines() for m in [re.match(r"\| \*\*DEC-(\d+)\*\* \|", line)] if m}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------- scan

class ScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lib = scanner.scan(fx.build_lib(new_dir("lib"), ENV))
        cls.saas = scanner.scan(fx.build_saas(new_dir("saas"), ENV))
        cls.mono = scanner.scan(fx.build_monorepo(new_dir("mono"), ENV))
        cls.three_d = scanner.scan(fx.build_three_d(new_dir("three-d")))

    def assertSignals(self, result: dict, expected: set[str], absent: set[str]) -> None:  # noqa: N802
        got = set(result["signals"])
        self.assertLessEqual(expected, got, f"missing {sorted(expected - got)}; got {sorted(got)}")
        self.assertFalse(absent & got, f"unexpected {sorted(absent & got)}")

    def test_library_signals(self):
        self.assertEqual(sorted(self.lib["signals"]), ["ci", "code", "oss", "tests"])
        self.assertIn("LICENSE", self.lib["signals"]["oss"])
        self.assertEqual(self.lib["size"]["ui_apps"], [])

    def test_saas_signals(self):
        self.assertEqual(sorted(self.saas["signals"]),
                         ["analytics", "auth", "code", "content", "db", "deploy", "email", "landing", "migrations",
                          "payments", "personal_data", "tests", "ui_web"])
        self.assertIn("prisma/schema.prisma", self.saas["signals"]["personal_data"])
        self.assertIn("app/pricing/page.tsx", self.saas["signals"]["landing"])
        self.assertEqual(self.saas["size"]["ui_apps"], ["."])

    def test_monorepo_signals_and_ui_apps(self):
        self.assertEqual(sorted(self.mono["signals"]),
                         ["ci", "code", "data_pipelines", "deploy", "hardware", "i18n", "ml", "mobile", "monorepo",
                          "tests", "ui_web"])
        self.assertIn("dependency torch", self.mono["signals"]["ml"])
        self.assertIn("firmware/platformio.ini", self.mono["signals"]["hardware"])
        ui_apps = self.mono["size"]["ui_apps"]
        self.assertEqual(ui_apps, ["apps/admin", "apps/web"])
        self.assertEqual(self.mono["size"]["ui_app_count"], 2)
        self.assertNotIn("apps/mobile", ui_apps, "a react-native app is mobile, not a web UI app")

    def test_every_signal_carries_evidence(self):
        for result in (self.lib, self.saas, self.mono, self.three_d):
            for sig, evidence in result["signals"].items():
                self.assertTrue(evidence and all(isinstance(e, str) and e for e in evidence), f"{sig}: {evidence}")

    def test_a_3d_library_alone_is_not_a_game(self):
        self.assertIn("ui_web", self.three_d["signals"])
        self.assertNotIn("game", self.three_d["signals"], self.three_d["signals"].get("game"))

    def test_scan_of_a_non_git_folder(self):
        root = fx.build_three_d(new_dir("not-git"))
        self.assertFalse((root / ".git").exists())
        out = json.loads(run("scan.py", "--root", root, "--save").stdout)
        self.assertEqual((out["size"]["commits"], out["size"]["contributors"], out["size"]["first_commit"]),
                         (0, 0, None))
        self.assertEqual(out["size"]["files"], 3)
        saved = read_json(root / "docs" / "team" / "scan.json")
        self.assertEqual(saved["signals"], out["signals"])

    def test_size_counts_the_history(self):
        self.assertEqual(self.lib["size"]["commits"], 1)
        self.assertEqual(self.lib["size"]["contributors"], 1)
        self.assertGreaterEqual(self.mono["size"]["code_files"], 80)


class ScanGuardTests(unittest.TestCase):
    """Files that look like a signal and are not one: each would seat a wrong role."""

    def test_installed_packages_raise_no_signal(self):
        root = fx.build_lib(new_dir("scan-node-modules"), ENV)
        fx.put_json(root, "node_modules/left-pad/package.json",
                    {"name": "left-pad", "dependencies": {"react-dom": "18.3.1", "stripe": "15.8.0"}})
        got = scanner.scan(root)["signals"]
        self.assertEqual(sorted(got), ["ci", "code", "oss", "tests"], "node_modules is never read")

    def test_a_web_app_manifest_is_not_a_browser_extension(self):
        root = fx.build_lib(new_dir("scan-manifest"), ENV)
        fx.put_json(root, "public/manifest.json", {"name": "Tally", "display": "standalone"})
        self.assertNotIn("extension", scanner.scan(root)["signals"])
        fx.put_json(root, "extension/manifest.json", {"manifest_version": 3, "name": "Tally clipper"})
        self.assertEqual(scanner.scan(root)["signals"].get("extension"), ["extension/manifest.json"])

    def test_a_closed_licence_alone_is_not_open_source(self):
        root = fx.build_saas(new_dir("scan-licence"), ENV)
        fx.put(root, "LICENSE", "Copyright Tally. All rights reserved.\n")
        self.assertNotIn("oss", scanner.scan(root)["signals"])

    def test_personal_data_ignores_data_and_vendor_folders(self):
        root = fx.build_lib(new_dir("scan-personal"), ENV)
        fx.put(root, "data/models.py", "email = 'a column in a sample dataset'\n")
        self.assertNotIn("personal_data", scanner.scan(root)["signals"])
        fx.put(root, "src/tally_totals/models.py", "class Customer:\n    email: str\n")
        self.assertEqual(scanner.scan(root)["signals"].get("personal_data"), ["src/tally_totals/models.py"])

    def test_a_plain_gradle_build_is_not_a_mobile_app(self):
        root = fx.build_lib(new_dir("scan-gradle"), ENV)
        fx.put(root, "jvm/build.gradle", "plugins { id 'java' }\n")
        self.assertNotIn("mobile", scanner.scan(root)["signals"])
        fx.put(root, "app/build.gradle", "plugins { id 'com.android.application' }\n")
        self.assertEqual(scanner.scan(root)["signals"].get("mobile"), ["app/build.gradle"])

    def test_the_teams_own_files_raise_no_signal(self):
        root = fx.build_lib(new_dir("scan-team-files"), ENV)
        before = scanner.scan(root)
        fx.put(root, "docs/team/blog/launch.md", "# a seat's notes\n")
        fx.put(root, "docs/TEAM.md", "# Team\n")
        fx.put(root, "scripts/gen-team-agents.py", "print('generated')\n")
        after = scanner.scan(root)
        self.assertEqual(after["signals"], before["signals"])
        self.assertEqual(after["size"]["code_files"], before["size"]["code_files"])


# ---------------------------------------------------------------------------- plan

def scaled(scan: dict, code_files: int, commits: int = 0, contributors: int = 1, **size) -> dict:
    """A copy of `scan` with its size facts replaced."""
    s = copy.deepcopy(scan)
    s["size"].update(code_files=code_files, commits=commits, contributors=contributors, **size)
    return s


class PlanTests(unittest.TestCase):
    # what each fixture's options seat, in order: pinned, so adding or dropping a rule shows here
    GOLDEN = {
        "lib": {"lean": ["ceo", "engineering", "docs", "community", "quality"],
                "recommended": ["ceo", "chief-of-staff", "engineering", "docs", "community", "quality"],
                "full": ["ceo", "chief-of-staff", "engineering", "testing", "bar-raiser", "docs", "community"]},
        "saas": {"lean": ["ceo", "chief-of-staff", "frontend", "customer-success", "security", "growth",
                          "product-design", "engineering-platform", "quality", "legal-compliance"],
                 "recommended": ["ceo", "chief-of-staff", "frontend", "scope-trimmer", "customer-success", "user",
                                 "security", "growth", "product-design", "engineering-platform", "quality",
                                 "legal-compliance"],
                 "full": ["ceo", "chief-of-staff", "product", "engineering", "frontend", "testing", "platform",
                          "research", "bar-raiser", "scope-trimmer", "design", "sales", "seo", "social",
                          "competition", "customer-success", "funding", "payments", "compliance", "user", "security"]},
        "mono": {"lean": ["ceo", "chief-of-staff", "frontend", "mobile", "i18n", "product-design",
                          "engineering-platform", "quality", "data-ml", "hardware"],
                 "recommended": ["ceo", "chief-of-staff", "product", "engineering", "frontend", "testing", "platform",
                                 "research", "bar-raiser", "scope-trimmer", "design", "mobile", "i18n", "data-ml",
                                 "hardware"],
                 "full": ["ceo", "chief-of-staff", "product", "engineering", "testing", "platform", "research",
                          "bar-raiser", "scope-trimmer", "design", "customer-success", "user", "mobile", "ml", "data",
                          "i18n", "frontend-admin", "frontend-web", "hardware"]},
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.scans = {"lib": scanner.scan(fx.build_lib(new_dir("lib"), ENV)),
                     "saas": scanner.scan(fx.build_saas(new_dir("saas"), ENV)),
                     "mono": scanner.scan(fx.build_monorepo(new_dir("mono"), ENV))}
        cls.opts = {name: planner.options(s) for name, s in cls.scans.items()}

    def each_option(self):
        for name, opts in self.opts.items():
            for option in ("lean", "recommended", "full"):
                yield name, option, opts[option]

    def test_size_classes(self):
        self.assertEqual({n: o["size"] for n, o in self.opts.items()}, {"lib": "tiny", "saas": "tiny", "mono": "small"})

    def test_size_class_boundaries(self):
        mono = self.scans["mono"]
        cases = [((59, 0, 1), "tiny"), ((60, 0, 1), "small"), ((10, 50, 1), "small"), ((599, 60, 3), "small"),
                 ((599, 60, 4), "medium"), ((600, 60, 3), "medium"), ((2999, 60, 12), "medium"),
                 ((3000, 60, 1), "large")]
        for (code, commits, people), expected in cases:
            self.assertEqual(planner.size_class(scaled(mono, code, commits, people)), expected,
                             f"{code} source files, {commits} commits, {people} people")

    def test_needs_per_fixture(self):
        expected = {
            "lib": ({"ceo", "bar-raiser", "engineering", "testing", "docs", "community"}, set(), []),
            "saas": ({"ceo", "bar-raiser", "engineering", "testing", "frontend", "design", "user", "product",
                      "platform", "research", "payments", "sales", "seo", "social", "customer-success", "compliance",
                      "security"}, {"competition", "funding"}, []),
            "mono": ({"ceo", "bar-raiser", "engineering", "testing", "frontend", "mobile", "design", "product",
                      "platform", "ml", "data", "research", "i18n"}, {"customer-success", "user"}, ["hardware"]),
        }
        for name, (core, opt, derived) in expected.items():
            got_core, got_opt, got_derived = planner.needs(self.scans[name])
            self.assertEqual(set(got_core), core, name)
            self.assertEqual(set(got_opt), opt, name)
            self.assertEqual([d["team"] for d in got_derived], derived, name)
            for why in list(got_core.values()) + list(got_opt.values()):
                self.assertTrue(why.strip(), name)

    def test_options_seat_exactly_these_teams(self):
        for name, option, seats in self.each_option():
            self.assertEqual([s["team"] for s in seats], self.GOLDEN[name][option], f"{name}/{option}")

    def test_option_shapes(self):
        saas = {k: [s["team"] for s in v] for k, v in self.opts["saas"].items() if k != "size"}
        self.assertLess(len(saas["lean"]), len(saas["recommended"]))
        self.assertFalse({"user", "scope-trimmer"} & set(saas["lean"]), "lean drops the optional check seats")
        self.assertIn("engineering-platform", saas["lean"])
        _, opt, _ = planner.needs(self.scans["saas"])
        self.assertLessEqual(set(opt), set(saas["full"]), "full adds every optional seat")
        self.assertNotIn("chief-of-staff", [s["team"] for s in self.opts["lib"]["lean"]])
        small = {s["team"] for s in self.opts["mono"]["recommended"] if s["type"] == "merge"}
        self.assertEqual(small, {"data-ml"}, "a small project merges only its commercial and data seats")

    def test_lean_is_smallest_and_full_largest(self):
        for name, o in self.opts.items():
            sizes = [len(o[k]) for k in ("lean", "recommended", "full")]
            self.assertEqual(sizes, sorted(sizes), f"{name}: lean/recommended/full = {sizes}")
            self.assertLess(sizes[0], sizes[2], f"{name}: lean should seat fewer than full")

    def test_every_seat_has_a_why(self):
        for name, option, seats in self.each_option():
            for s in seats:
                self.assertTrue(str(s.get("why", "")).strip(), f"{name}/{option}: {s['team']} has no why")

    def test_lean_library_merges_quality(self):
        lean = self.opts["lib"]["lean"]
        quality = [s for s in lean if s["team"] == "quality"]
        self.assertEqual(len(quality), 1, [s["team"] for s in lean])
        self.assertEqual(quality[0]["type"], "merge")
        self.assertEqual(sorted(quality[0]["of"]), ["bar-raiser", "testing"])
        self.assertEqual(quality[0]["kind"], "check")
        self.assertIn("(holds Testing and Bar Raiser)", quality[0]["why"])
        self.assertFalse({"testing", "bar-raiser"} & {s["team"] for s in lean}, "merged members are not also seated")

    def test_no_merge_joins_a_check_seat_with_a_builder(self):
        for name, option, seats in self.each_option():
            for s in seats:
                if s["type"] != "merge":
                    continue
                checks = [m for m in s["of"] if m in teamlib.CHECK_SEATS]
                if not checks:
                    continue
                # a merge holding a check seat is itself a check, and holds nothing that builds:
                # only other check seats and the testing director (whose job is the test standard)
                self.assertEqual(teamlib.MERGES[s["team"]]["kind"], "check", f"{name}/{option}: {s}")
                builders = [m for m in s["of"] if m not in teamlib.CHECK_SEATS and m != "testing"]
                self.assertEqual(builders, [], f"{name}/{option}: {s['team']} joins {checks} with {builders}")

    def test_merge_rules(self):
        lib = self.scans["lib"]
        self.assertTrue(planner.merge_allowed("quality", ["testing", "bar-raiser"], lib))
        self.assertFalse(planner.merge_allowed("quality", ["testing", "bar-raiser"], lib, after_setup=True),
                         "after setup no merge holds the Bar Raiser")
        self.assertFalse(planner.merge_allowed("growth", ["sales"], lib), "a merge needs two members")
        self.assertFalse(planner.merge_allowed("growth", ["sales", "user"], lib), "a check seat joins only a check merge")
        self.assertTrue(planner.merge_allowed("engineering-platform", ["engineering", "platform"], scaled(lib, 2000)))
        self.assertFalse(planner.merge_allowed("engineering-platform", ["engineering", "platform"], scaled(lib, 2001)))
        lean = [s["team"] for s in planner.build(scaled(self.scans["saas"], 2500, 60, 12), "lean")]
        self.assertNotIn("engineering-platform", lean)
        self.assertLessEqual({"engineering", "platform"}, set(lean))

    def test_merged_members_are_not_seated_twice(self):
        for name, option, seats in self.each_option():
            teams = [s["team"] for s in seats]
            held = [m for s in seats if s["type"] == "merge" for m in s["of"]]
            self.assertEqual(len(held), len(set(held)), f"{name}/{option}: a member sits in two merges: {held}")
            self.assertFalse(set(teams) & set(held), f"{name}/{option}: {set(teams) & set(held)} seated and merged")

    def test_marks_are_unique_within_every_option(self):
        for name, option, seats in self.each_option():
            marks = [planner.norm_mark(mark_of(s)) for s in seats]
            dupes = sorted({m for m in marks if marks.count(m) > 1})
            self.assertEqual(dupes, [], f"{name}/{option}: duplicate marks {dupes}")
            teams = [s["team"] for s in seats]
            self.assertEqual(len(teams), len(set(teams)), f"{name}/{option}: duplicate teams")

    def test_coordination_thresholds(self):
        self.assertEqual(planner.coordination(4, "recommended"), {})
        self.assertEqual(list(planner.coordination(5, "recommended")), ["chief-of-staff"])
        self.assertEqual(planner.coordination(6, "lean"), {})
        self.assertEqual(list(planner.coordination(7, "lean")), ["chief-of-staff"])
        self.assertEqual(list(planner.coordination(9, "full")), ["chief-of-staff"])
        self.assertEqual(list(planner.coordination(10, "lean")), ["chief-of-staff", "scope-trimmer"])
        self.assertIn("10 other seats", planner.coordination(10, "full")["scope-trimmer"])
        for name, option, seats in self.each_option():
            teams = [s["team"] for s in seats]
            n_other = len([t for t in teams if t not in planner.COORDINATION])
            self.assertEqual("chief-of-staff" in teams, n_other >= (7 if option == "lean" else 5),
                             f"{name}/{option}: {n_other} other seats")
            self.assertEqual("scope-trimmer" in teams, n_other >= 10, f"{name}/{option}: {n_other} other seats")

    def test_full_monorepo_splits_frontend_and_derives_hardware(self):
        full = self.opts["mono"]["full"]
        splits = [s for s in full if s["type"] == "derive" and s.get("base") == "seat-frontend"]
        self.assertEqual([(s["team"], s["mark"], s["seat"]) for s in splits],
                         [("frontend-admin", "💻", "Frontend engineer (admin)"),
                          ("frontend-web", "🪟", "Frontend engineer (web)")])
        self.assertNotIn("frontend", [s["team"] for s in full], "the splits replace the single frontend seat")
        self.assertEqual([s["scope"] for s in splits], ["only apps/admin/; each other UI app has its own frontend seat",
                                                        "only apps/web/; each other UI app has its own frontend seat"])
        hardware = [s for s in full if s["team"] == "hardware"]
        self.assertEqual(len(hardware), 1)
        self.assertEqual((hardware[0]["type"], hardware[0]["mark"], hardware[0]["base"]), ("derive", "🔌", "seat-mobile"))
        self.assertIn("platformio.ini", hardware[0]["why"])

    def test_recommended_scales_with_size(self):
        mono = self.scans["mono"]
        tiny = self.opts["saas"]["recommended"]
        self.assertTrue(any(s["type"] == "merge" for s in tiny), "a tiny project takes the merges")
        medium = planner.build(scaled(mono, 700, 300, 5), "recommended")
        self.assertEqual([s for s in medium if s["type"] == "merge"], [], "a medium project keeps seats separate")
        self.assertEqual([s["team"] for s in medium if s["type"] == "derive"], ["hardware"], "and splits nothing")
        self.assertLessEqual({"frontend", "data", "ml", "engineering", "platform"}, {s["team"] for s in medium})
        large = [s["team"] for s in planner.build(scaled(mono, 5000, 900, 12), "recommended")]
        self.assertNotIn("frontend", large)
        self.assertIn("frontend-admin", large)
        self.assertIn("frontend-web", large)

    def test_more_ui_apps_than_split_seats_keeps_the_frontend_seat(self):
        apps = [f"apps/{c}" for c in "abcdefgh"]
        scan = scaled(self.scans["mono"], 5000, 900, 12, ui_apps=apps, ui_app_count=10)
        seats = planner.build(scan, "recommended")
        splits = [s["team"] for s in seats if s.get("base") == "seat-frontend"]
        self.assertEqual(splits, ["frontend-a", "frontend-b", "frontend-c", "frontend-d"], "at most MAX_SPLITS")
        frontend = [s for s in seats if s["team"] == "frontend"]
        self.assertEqual(len(frontend), 1, "the catalogue seat holds the rest")
        self.assertEqual(frontend[0]["why"], "holds the UI apps without a frontend seat of their own: "
                                             "apps/e, apps/f, apps/g, apps/h and 2 more")
        for s in seats:
            if s.get("base") == "seat-frontend":
                self.assertIn("sit with the Frontend engineer", s["scope"])

    def test_split_slugs_are_unique(self):
        scan = scaled(self.scans["mono"], 5000, 900, 12, ui_apps=["apps/web", "sites/web", "tools/My_Admin.v2"],
                      ui_app_count=3)
        teams = [s["team"] for s in planner.ui_splits(scan)]
        self.assertEqual(teams, ["frontend-apps-web", "frontend-sites-web", "frontend-my-admin-v2"])
        marks = [s["mark"] for s in planner.ui_splits(scan, taken_marks=["💻"])]
        self.assertNotIn("💻", marks)
        self.assertEqual(len(set(marks)), 3)

    def test_spec_signals(self):
        saas = self.scans["saas"]
        self.assertEqual(planner.spec_signals({"team": "security", "type": "catalogue"}, saas),
                         ["auth", "payments", "personal_data"])
        growth = planner.merge_spec("growth", ["sales", "seo", "social"])
        self.assertEqual(planner.spec_signals(growth, saas), ["content", "landing", "payments"])
        mono = self.scans["mono"]
        hardware = next(s for s in self.opts["mono"]["full"] if s["team"] == "hardware")
        self.assertEqual(planner.spec_signals(hardware, mono), ["hardware"])

    def test_cli_writes_the_chosen_option(self):
        root = new_dir("plan-cli")
        scan_file = root / "scan.json"
        scan_file.write_text(json.dumps(self.scans["saas"]), encoding="utf-8")
        out = root / "docs" / "team" / "plan.json"
        run("plan.py", "--scan", scan_file, "--option", "recommended", "--out", out, "--project", "Tally")
        plan = read_json(out)
        self.assertEqual((plan["project"], plan["option"], plan["retire"]), ("Tally", "recommended", []))
        self.assertEqual([s["team"] for s in plan["seats"]], [s["team"] for s in self.opts["saas"]["recommended"]])
        md = run("plan.py", "--scan", scan_file, "--markdown").stdout
        heads = [md.index(f"### {option}: ") for option in ("Recommended", "Lean", "Full")]
        self.assertEqual(heads, sorted(heads), "Recommended first, then Lean and Full")
        self.assertIn("### Recommended: 12 seats", md)
        self.assertIn("| Seat | How | Why |", md)
        self.assertIn(f"| {name('security')} | its own seat |", md)
        for slug in ("ui_web", "personal_data", "engineering-platform", "legal-compliance"):
            self.assertNotIn(slug, md, "the owner reads seat names and plain sentences, never keys or slugs")


# ---------------------------------------------------------------------------- scaffold

HAT_RULES = ("**Name the hat.**", "**When the roles pull against each other, say so.**",
             "**Checks stay independent.**", "**Grow out of it.**")


class ScaffoldTests(unittest.TestCase):
    def test_lean_setup_composes_merged_rulebooks_and_passes_the_check(self):
        root = fx.build_saas(new_dir("saas-lean"), ENV)
        plan, _ = seat_up(root, "lean")
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        merges = [s for s in plan["seats"] if s["type"] == "merge"]
        self.assertEqual([m["team"] for m in merges],
                         ["growth", "product-design", "engineering-platform", "quality", "legal-compliance"])
        self.assertEqual(sorted(roster_teams(root)), sorted(s["team"] for s in plan["seats"]))
        lock = teamlib.load_lock(root)
        self.assertEqual(sorted(lock), sorted(f"seat-{s['team']}" if s["type"] != "catalogue" else CAT[s["team"]]["skill"]
                                              for s in plan["seats"]))
        for skill, entry in lock.items():
            self.assertEqual(entry["seated"], TODAY, skill)
        for s in plan["seats"]:
            if s["type"] == "catalogue":
                self.assertEqual(lock[CAT[s["team"]]["skill"]]["origin"], "catalogue")
        for m in merges:
            text = (root / ".claude" / "skills" / f"seat-{m['team']}" / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(text, rf"(?m)^name: seat-{re.escape(m['team'])}$")
            self.assertRegex(text, rf"(?m)^# {re.escape(m['mark'])} {re.escape(m['seat'])}$")
            self.assertIn("**Single loyalty: each role below, held honestly at once.**", text)
            for rule in HAT_RULES:
                self.assertEqual(text.count(rule), 1, f"{m['team']}: {rule}")
            for member in m["of"]:
                row = CAT[member]
                self.assertIn(f"### As {row['mark']} {row['seat']}", text, f"{m['team']} lost {member}")
                self.assertEqual(text.count(f"*As {row['mark']} {row['seat']}:*"), 1,
                                 f"{m['team']}: one preamble line for {member}")
            for n in range(7):
                self.assertRegex(text, rf"(?m)^## {n} · ", f"{m['team']} has no section {n}")
            entry = lock[f"seat-{m['team']}"]
            self.assertEqual((entry["origin"], entry["seat"], entry["mark"]),
                             ("merge:" + "+".join(m["of"]), m["seat"], m["mark"]))
            self.assertTrue((root / ".claude" / "agents" / f"{m['team']}-worker.md").is_file())
        # the Chief of Staff is seated, so its two files are written
        for f in ("tracker.md", "owner-questions.md"):
            self.assertTrue((root / "docs" / "team" / f).is_file(), f)

    def test_add_then_retire_a_seat(self):
        root = fx.build_lib(new_dir("lib-add"), ENV)
        seat_up(root, "full")
        self.assertNotIn("design", roster_teams(root))
        scaffold(root, "--add", "design")
        self.assertIn("design", roster_teams(root))
        worker = root / ".claude" / "agents" / "design-worker.md"
        skill = root / ".claude" / "skills" / "seat-design" / "SKILL.md"
        brief = root / "docs" / "team" / "design.md"
        for f in (worker, skill, brief):
            self.assertTrue(f.is_file(), f)
        self.assertEqual(gen_check(root).returncode, 0)

        out = scaffold(root, "--retire", "design").stdout
        self.assertIn(f"retired: {name('design')}", out)
        self.assertNotIn("archived", out, "an unedited catalogue copy is deleted, not archived")
        self.assertNotIn("design", roster_teams(root))
        self.assertTrue(brief.read_text(encoding="utf-8").startswith("> **Retired "), "the brief is kept, marked retired")
        self.assertFalse(worker.exists(), "the retired seat's worker is removed")
        self.assertFalse(skill.parent.exists(), "the retired catalogue rulebook is removed")
        self.assertNotIn("seat-design", teamlib.load_lock(root))
        self.assertEqual(gen_check(root).returncode, 0)

        out = scaffold(root, "--add", "design").stdout
        self.assertIn("back in use, Retired line removed: docs/team/design.md", out)
        self.assertFalse(brief.read_text(encoding="utf-8").startswith("> **Retired"))
        self.assertEqual(teamlib.load_lock(root)["seat-design"]["seated"], TODAY)

    def test_unmerge_through_a_plan(self):
        root = fx.build_saas(new_dir("saas-unmerge"), ENV)
        seat_up(root, "lean")
        self.assertIn("growth", roster_teams(root))
        members = ["sales", "seo", "social"]
        plan = {"project": "Tally", "seats": [{"team": t, "type": "catalogue", "why": "split out of growth"}
                                              for t in members], "retire": ["growth"]}
        plan_file = root / "docs" / "team" / "unmerge.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        scaffold(root, "--plan", plan_file, "--record", "split growth", "--question", "Split 📈 Growth?")
        teams = roster_teams(root)
        self.assertNotIn("growth", teams)
        for t in members:
            self.assertIn(t, teams)
            self.assertTrue((root / ".claude" / "skills" / CAT[t]["skill"] / "SKILL.md").is_file())
            self.assertTrue((root / "docs" / "team" / f"{t}.md").is_file())
        self.assertFalse((root / ".claude" / "skills" / "seat-growth").exists())
        self.assertFalse((root / ".claude" / "agents" / "growth-worker.md").exists())
        self.assertTrue((root / "docs" / "team" / "growth.md").read_text(encoding="utf-8").startswith("> **Retired"))
        self.assertNotIn("seat-growth", teamlib.load_lock(root))
        self.assertEqual(decision_rows(root)[2],
                         f"| **DEC-2** | Split 📈 Growth? | docs/team/unmerge.json | ✅ {TODAY}: split {name('growth')} into "
                         f"{name('sales')}, {name('seo')}, {name('social')}. Declined: nothing. "
                         "Owner's words: \"split growth\" |")
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_a_merge_carries_its_members_briefs_and_retires_them(self):
        root = fx.build_saas(new_dir("saas-merge"), ENV)
        seat_up(root, "full")
        fact = "- The pricing page copy is signed off by the owner before it ships."
        with (root / "docs" / "team" / "sales.md").open("a", encoding="utf-8") as f:
            f.write(fact + "\n")
        plan = {"project": "Tally", "seats": [planner.merge_spec("growth", ["sales", "seo", "social"])],
                "retire": ["sales", "seo", "social"]}
        plan_file = root / "docs" / "team" / "merge.json"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        scaffold(root, "--plan", plan_file, "--record", "merge them")
        brief = (root / "docs" / "team" / "growth.md").read_text(encoding="utf-8")
        for m in ("sales", "seo", "social"):
            self.assertIn(f"## Carried over from the {m} brief", brief)
        self.assertIn(fact, brief)
        self.assertEqual(sorted(set(roster_teams(root)) & {"growth", "sales", "seo", "social"}), ["growth"])
        self.assertIn(f"✅ {TODAY}: merged {name('sales')}, {name('seo')}, {name('social')} into {name('growth')}. "
                      "Declined: nothing.", decision_rows(root)[2])
        self.assertEqual(gen_check(root).returncode, 0)

    def test_sync_refreshes_unedited_copies_and_keeps_edited_ones(self):
        # a private copy of the setup skill stands in for "this version" and then "a newer version"
        skill_copy = new_dir("skill-copy") / "team-setup"
        shutil.copytree(SKILL, skill_copy, ignore=shutil.ignore_patterns("__pycache__"))
        scripts = skill_copy / "scripts"
        root = new_dir("sync")
        fx.commit_all(root, "initial", ENV)
        plan = {"project": "Tally", "seats": [
            {"team": "engineering", "type": "catalogue", "why": "code"},
            {"team": "testing", "type": "catalogue", "why": "tests"},
            {"team": "growth", "type": "merge", "of": ["sales", "seo", "social"], "seat": "Growth", "mark": "📈",
             "kind": "director", "why": "small"}]}
        plan_file = root / "plan.json"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        run("scaffold.py", "--root", root, "--plan", plan_file, scripts=scripts)
        skills = root / ".claude" / "skills"
        lock_file = root / "docs" / "team" / "seat-skills.lock"
        ceo_before = (skills / "seat-ceo" / "SKILL.md").read_bytes()

        self.assertIn("all seat rulebooks current", run("scaffold.py", "--root", root, "--sync", scripts=scripts).stdout)

        with (skills / "seat-testing" / "SKILL.md").open("a", encoding="utf-8") as f:
            f.write("\n- Project rule: run the suite twice before calling it green.\n")
        newer = "\n- A newer catalogue line.\n"
        for seat in ("seat-engineering", "seat-testing", "seat-sales"):
            with (skill_copy / "seats" / seat / "SKILL.md").open("a", encoding="utf-8") as f:
                f.write(newer)

        out = run("scaffold.py", "--root", root, "--sync", scripts=scripts).stdout
        self.assertIn("updated: .claude/skills/seat-engineering", out)
        self.assertIn("updated: .claude/skills/seat-growth", out)
        self.assertIn("kept (edited in this project): .claude/skills/seat-testing", out)
        self.assertNotIn("seat-ceo", out)
        self.assertEqual((skills / "seat-engineering" / "SKILL.md").read_text(encoding="utf-8"),
                         (skill_copy / "seats" / "seat-engineering" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn(newer.strip(), (skills / "seat-growth" / "SKILL.md").read_text(encoding="utf-8"))
        testing = (skills / "seat-testing" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Project rule: run the suite twice", testing)
        self.assertNotIn(newer.strip(), testing)
        self.assertEqual((skills / "seat-ceo" / "SKILL.md").read_bytes(), ceo_before)

        before = snapshot(skills, lock_file.parent)
        out = run("scaffold.py", "--root", root, "--sync", scripts=scripts).stdout
        self.assertNotIn("updated:", out)
        self.assertEqual(snapshot(skills, lock_file.parent), before, "a second sync changes nothing")

    def test_existing_files_are_never_overwritten_without_force(self):
        root = fx.build_lib(new_dir("lib-existing"), ENV)
        decisions = "# Decisions\n\n| Decision | Question | Evidence | Decided |\n|---|---|---|---|\n" \
                    "| **DEC-7** | keep the API stable | `src/` | ✅ 2026-01-05: yes |\n"
        claude = "# tally-totals\n\nHouse rules: run the suite before every commit.\n"
        brief = "# Engineering, our own brief\n\n- The release script is scripts/release.sh.\n"
        fx.put(root, "docs/DECISIONS.md", decisions)
        fx.put(root, "CLAUDE.md", claude)
        fx.put(root, "docs/team/engineering.md", brief)
        _, out = seat_up(root, "lean", record="seat the lean team")
        self.assertIn(f"skipped (exists): {root / 'docs' / 'DECISIONS.md'}", out)
        self.assertIn(f"skipped (exists): {root / 'docs' / 'team' / 'engineering.md'}", out)
        text = (root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith(decisions.rstrip()), "the project's own register is kept")
        self.assertEqual(sorted(decision_rows(root)), [7, 8], "the decision is appended to it, numbered after DEC-7")
        self.assertEqual((root / "docs" / "team" / "engineering.md").read_text(encoding="utf-8"), brief)
        cm = (root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(cm.startswith(claude.rstrip()), "CLAUDE.md only gains the pointer")
        self.assertIn("docs/TEAM.md", cm)

        forced = fx.build_lib(new_dir("lib-existing-force"), ENV)
        fx.put(forced, "docs/DECISIONS.md", decisions)
        fx.put(forced, "docs/team/engineering.md", brief)
        run("scan.py", "--root", forced, "--save")
        plan_file = forced / "docs" / "team" / "plan.json"
        run("plan.py", "--scan", forced / "docs" / "team" / "scan.json", "--option", "lean", "--out", plan_file)
        out = scaffold(forced, "--plan", plan_file, "--force").stdout
        self.assertIn(f"wrote: {forced / 'docs' / 'DECISIONS.md'}", out)
        self.assertNotIn("DEC-7", (forced / "docs" / "DECISIONS.md").read_text(encoding="utf-8"), "--force overwrites")
        self.assertTrue((forced / "docs" / "team" / "engineering.md").read_text(encoding="utf-8")
                        .startswith(f"# {name('engineering')}: the project brief for "))

    def test_a_rulebook_the_project_already_had_is_its_own(self):
        root = fx.build_lib(new_dir("lib-own"), ENV)
        own = "---\nname: seat-testing\ndescription: \"our own testing seat\"\n---\n# 🧪 Testing\n\nOur rules.\n"
        fx.put(root, ".claude/skills/seat-testing/SKILL.md", own)
        shutil.copytree(SKILL / "seats" / "seat-docs", root / ".claude" / "skills" / "seat-docs")
        _, out = seat_up(root, "full")
        self.assertIn("kept (exists, the project's own; never synced or overwritten): .claude/skills/seat-testing", out)
        self.assertIn("kept (exists, same as this version's): .claude/skills/seat-docs", out)
        lock = teamlib.load_lock(root)
        self.assertEqual((lock["seat-testing"]["origin"], lock["seat-docs"]["origin"]), ("project", "catalogue"))
        out = scaffold(root, "--sync").stdout
        self.assertIn("the project's own, never synced: seat-testing", out)
        skill = root / ".claude" / "skills" / "seat-testing" / "SKILL.md"
        self.assertEqual(skill.read_text(encoding="utf-8"), own)
        out = scaffold(root, "--retire", "testing").stdout
        self.assertIn(f"archived (the project's own): docs/team/retired/seat-testing-{TODAY}", out)
        self.assertEqual((root / "docs" / "team" / "retired" / f"seat-testing-{TODAY}" / "SKILL.md")
                         .read_text(encoding="utf-8"), own)
        self.assertFalse(skill.exists())

    def test_reapplying_a_plan_keeps_edits_and_their_hashes(self):
        root = fx.build_lib(new_dir("lib-reapply"), ENV)
        seat_up(root, "full")
        backdate(root)
        skill = root / ".claude" / "skills" / "seat-testing" / "SKILL.md"
        rule = "- Project rule: run the suite twice before calling it green."
        with skill.open("a", encoding="utf-8") as f:
            f.write("\n" + rule + "\n")
        lock_file = root / "docs" / "team" / "seat-skills.lock"
        lock_before = lock_file.read_bytes()
        out = scaffold(root, "--plan", root / "docs" / "team" / "plan.json", "--record", "again").stdout
        self.assertIn("nothing changed; no decision recorded", out)
        self.assertEqual(lock_file.read_bytes(), lock_before, "re-applying a plan rewrites no hash or seated date")
        out = scaffold(root, "--sync").stdout
        self.assertIn("kept (edited in this project): .claude/skills/seat-testing", out)
        self.assertIn(rule, skill.read_text(encoding="utf-8"))
        out = scaffold(root, "--retire", "testing").stdout
        self.assertIn(f"archived (edited in this project): docs/team/retired/seat-testing-{TODAY}", out)
        self.assertIn(rule, (root / "docs" / "team" / "retired" / f"seat-testing-{TODAY}" / "SKILL.md")
                      .read_text(encoding="utf-8"))

    def test_a_repaired_seat_keeps_its_seated_date(self):
        root = fx.build_lib(new_dir("lib-repair"), ENV)
        seat_up(root, "full")
        backdate(root)
        shutil.rmtree(root / ".claude" / "skills" / "seat-testing")
        out = scaffold(root, "--plan", root / "docs" / "team" / "plan.json").stdout
        self.assertIn(f"repairing {name('testing')}: seated, but its rulebook, brief or lock entry is missing", out)
        self.assertTrue((root / ".claude" / "skills" / "seat-testing" / "SKILL.md").is_file())
        self.assertEqual(teamlib.load_lock(root)["seat-testing"]["seated"], LONG_AGO)

    def test_repairing_a_missing_brief_keeps_an_edited_rulebooks_hash(self):
        root = fx.build_lib(new_dir("lib-repair-edited"), ENV)
        seat_up(root, "full")
        skill = root / ".claude" / "skills" / "seat-testing" / "SKILL.md"
        rule = "- Project rule: run the suite twice before calling it green."
        with skill.open("a", encoding="utf-8") as f:
            f.write("\n" + rule + "\n")
        (root / "docs" / "team" / "testing.md").unlink()
        entry_before = json.dumps(teamlib.load_lock(root)["seat-testing"], sort_keys=True)
        out = scaffold(root, "--plan", root / "docs" / "team" / "plan.json").stdout
        self.assertIn(f"repairing {name('testing')}", out)
        self.assertTrue((root / "docs" / "team" / "testing.md").is_file())
        self.assertEqual(json.dumps(teamlib.load_lock(root)["seat-testing"], sort_keys=True), entry_before,
                         "a repair must not re-hash an edited rulebook, or the next sync overwrites the edit")
        out = scaffold(root, "--sync").stdout
        self.assertIn("kept (edited in this project): .claude/skills/seat-testing", out)
        self.assertIn(rule, skill.read_text(encoding="utf-8"))

    def test_an_untracked_rulebook_is_neither_synced_nor_deleted(self):
        root = fx.build_lib(new_dir("lib-untracked"), ENV)
        seat_up(root, "full")
        lock = teamlib.load_lock(root)
        del lock["seat-community"]
        teamlib.save_lock(root, lock)
        out = scaffold(root, "--sync").stdout
        self.assertIn("not tracked: .claude/skills/seat-community (no lock entry, so its edits are unknown; not synced)", out)
        self.assertNotIn("all seat rulebooks current", out)
        out = scaffold(root, "--retire", "community").stdout
        self.assertIn(f"archived (not tracked in the lock): docs/team/retired/seat-community-{TODAY}", out)


class LockTests(unittest.TestCase):
    def test_load_lock_normalizes_older_entries(self):
        root = new_dir("lock")
        fx.put_json(root, "docs/team/seat-skills.lock", {
            "seat-ceo": "abc",
            "seat-growth": {"hash": "h1", "origin": "merge:project"},
            "seat-web": {"hash": "h2", "origin": "derive:project", "seated": "2026-01-02"},
            "seat-testing": {"hash": "h3", "origin": "catalogue", "seated": "2026-03-04"}})
        lock = teamlib.load_lock(root)
        self.assertEqual(lock["seat-ceo"], {"hash": "abc", "origin": "catalogue", "seated": None})
        self.assertEqual(lock["seat-growth"], {"hash": "h1", "origin": "project", "seated": None})
        self.assertEqual(lock["seat-web"]["origin"], "project")
        self.assertEqual(lock["seat-testing"]["seated"], "2026-03-04")

    def test_coverage(self):
        rows = [{"team": "ceo", "skill": "seat-ceo"}, {"team": "growth", "skill": "seat-growth"},
                {"team": "sales", "skill": "seat-sales"}, {"team": "frontend-web", "skill": "seat-frontend-web"},
                {"team": "ours", "skill": "seat-ours"}]
        lock = {"seat-growth": {"origin": "merge:sales+seo"}, "seat-frontend-web": {"origin": "derive:seat-frontend"},
                "seat-ours": {"origin": "project", "of": ["product", "design"]}}
        cov = teamlib.coverage(new_dir("cov"), rows, lock)
        self.assertEqual(cov, {"ceo": "ceo", "growth": "growth", "sales": "sales", "seo": "growth",
                               "frontend-web": "frontend-web", "frontend": "frontend-web", "ours": "ours",
                               "product": "ours", "design": "ours"})
        self.assertEqual(teamlib.members_covered(lock), {"sales", "seo", "product", "design"})


class LibraryTeamTests(unittest.TestCase):
    """Changes to a seated library team: decisions, refusals and the seats every team keeps."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.lean = fx.build_lib(new_dir("lib-lean"), ENV)
        seat_up(cls.lean, "lean", record="yes, seat the lean team")
        cls.full = fx.build_lib(new_dir("lib-full"), ENV)
        seat_up(cls.full, "full")

    def test_record_appends_numbered_decisions(self):
        root = clone(self.lean, "lib-record")
        scaffold(root, "--add", "design", "--record", "add design for the docs pages")
        scaffold(root, "--retire", "design", "--record", "retire design, nobody needs it yet")
        rows = decision_rows(root)
        self.assertEqual(sorted(rows), [1, 2, 3, 4])
        lean = ", ".join(name(t) for t in ("ceo", "engineering", "docs", "community", "quality"))
        self.assertEqual(rows[2], f"| **DEC-2** | Team change | docs/team/plan.json | ✅ {TODAY}: seated {lean}. "
                                  "Declined: nothing. Owner's words: \"yes, seat the lean team\" |")
        self.assertEqual(rows[3], f"| **DEC-3** | Team change named by the owner | named by the owner | ✅ {TODAY}: "
                                  f"seated {name('design')}. Declined: nothing. "
                                  "Owner's words: \"add design for the docs pages\" |")
        self.assertEqual(rows[4], f"| **DEC-4** | Team change named by the owner | named by the owner | ✅ {TODAY}: "
                                  f"retired {name('design')}. Declined: nothing. "
                                  "Owner's words: \"retire design, nobody needs it yet\" |")
        scaffold(root, "--add", "design", "--record", "yes | design after all", "--question", "Seat 📐 Design again?")
        self.assertEqual(decision_rows(root)[5],
                         f"| **DEC-5** | Seat 📐 Design again? | named by the owner | ✅ {TODAY}: seated {name('design')}. "
                         "Declined: nothing. Owner's words: \"yes \\| design after all\" |")

    def test_a_change_that_changes_nothing_records_nothing(self):
        root = clone(self.lean, "lib-nothing")
        before = (root / "docs" / "DECISIONS.md").read_bytes()
        out = scaffold(root, "--retire", "motion", "--record", "retire motion").stdout
        self.assertIn(f"not seated: {name('motion')}", out)
        self.assertIn("nothing changed; no decision recorded", out)
        out = scaffold(root, "--add", "engineering", "--record", "add engineering").stdout
        self.assertIn("nothing changed; no decision recorded", out)
        self.assertEqual((root / "docs" / "DECISIONS.md").read_bytes(), before)
        self.assertFalse((root / "docs" / "team" / "declined.json").exists())

    def test_the_tracker_and_owner_questions_are_written_with_or_without_a_chief_of_staff(self):
        self.assertNotIn("chief-of-staff", roster_teams(self.lean))
        for f in ("tracker.md", "owner-questions.md"):
            text = (self.lean / "docs" / "team" / f).read_text(encoding="utf-8")
            self.assertIn("Kept by the 🧭 CEO", text, f)
            self.assertNotIn("Kept by the 🛎️ Chief of Staff.", text, f)
        self.assertIn("chief-of-staff", roster_teams(self.full))
        for f in ("tracker.md", "owner-questions.md"):
            self.assertIn("Kept by the 🛎️ Chief of Staff.", (self.full / "docs" / "team" / f).read_text(encoding="utf-8"), f)

    def test_ceo_and_bar_raiser_refuse_to_retire(self):
        root = clone(self.full, "lib-keep")
        out = scaffold(root, "--retire", "ceo,bar-raiser").stdout
        self.assertIn(f"not retired: {name('ceo')}: every team keeps one", out)
        self.assertIn(f"not retired: {name('bar-raiser')}: every team keeps one; to retire it, seat a merged seat "
                      "that holds it in the same plan", out)
        teams = roster_teams(root)
        self.assertIn("ceo", teams)
        self.assertIn("bar-raiser", teams)
        for t in ("ceo", "bar-raiser"):
            self.assertTrue((root / ".claude" / "agents" / f"{t}-worker.md").is_file())
            self.assertFalse((root / "docs" / "team" / f"{t}.md").read_text(encoding="utf-8").startswith("> **Retired"))
        self.assertEqual(gen_check(root).returncode, 0)

    def test_a_merged_seat_holding_the_bar_raiser_stays(self):
        root = clone(self.lean, "lib-keep-quality")
        out = scaffold(root, "--retire", "quality,bar-raiser").stdout
        self.assertIn(f"not retired: {name('quality')}: it holds {name('bar-raiser')}, and every team keeps one; "
                      f"to retire it, seat {name('bar-raiser')} in the same plan", out)
        self.assertIn(f"not seated on its own: {name('bar-raiser')} (held by {name('quality')})", out)
        self.assertIn("quality", roster_teams(root))

    def test_the_bar_raiser_moves_into_a_merge_in_one_plan(self):
        root = clone(self.full, "lib-into-quality")
        plan = {"project": "Tally", "seats": [planner.merge_spec("quality", ["testing", "bar-raiser"])],
                "retire": ["testing", "bar-raiser"]}
        plan_file = root / "docs" / "team" / "quality.json"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        scaffold(root, "--plan", plan_file, "--record", "merge the checks")
        teams = roster_teams(root)
        self.assertIn("quality", teams)
        self.assertFalse({"testing", "bar-raiser"} & set(teams))
        self.assertEqual(teamlib.coverage(root)["bar-raiser"], "quality")
        self.assertIn(f"merged {name('testing')}, {name('bar-raiser')} into {name('quality')}.", decision_rows(root)[2])
        self.assertEqual(gen_check(root).returncode, 0)

    def test_a_merge_splits_back_in_one_plan(self):
        root = clone(self.lean, "lib-out-of-quality")
        plan = {"project": "Tally", "seats": [{"team": "testing", "type": "catalogue", "why": "x"},
                                              {"team": "bar-raiser", "type": "catalogue", "why": "x"}],
                "retire": ["quality"]}
        plan_file = root / "docs" / "team" / "split.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        scaffold(root, "--plan", plan_file, "--record", "split the checks")
        self.assertLessEqual({"testing", "bar-raiser"}, set(roster_teams(root)))
        self.assertNotIn("quality", roster_teams(root))
        self.assertIn(f"split {name('quality')} into {name('testing')}, {name('bar-raiser')}.", decision_rows(root)[3])

    def assertRefused(self, root: Path, args: list, *messages: str) -> None:  # noqa: N802
        before = snapshot(root / "docs", root / ".claude")
        res = scaffold(root, *args, check=False)
        self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
        self.assertIn("nothing was changed:", res.stderr)
        for m in messages:
            self.assertIn(m, res.stderr)
        self.assertEqual(snapshot(root / "docs", root / ".claude"), before, "a refusal writes nothing")

    def test_a_role_held_by_a_merged_seat_is_refused(self):
        root = clone(self.lean, "lib-held")
        self.assertRefused(root, ["--add", "testing"],
                           f"{name('testing')} is held by {name('quality')}; unmerge it with a re-evaluation, or pass --force")
        scaffold(root, "--add", "testing", "--force")
        self.assertIn("testing", roster_teams(root))

    def test_a_merge_over_a_seated_role_is_refused(self):
        root = clone(self.full, "lib-merge-over")
        plan_file = root / "docs" / "team" / "quality.json"
        plan_file.write_text(json.dumps({"seats": [planner.merge_spec("quality", ["testing", "bar-raiser"])]},
                                        ensure_ascii=False), encoding="utf-8")
        self.assertRefused(root, ["--plan", plan_file],
                           f"{name('quality')} would hold {name('testing')}, which is seated on its own; "
                           "retire it in the same plan, or pass --force")

    def test_a_seated_mark_is_refused_even_with_force(self):
        root = clone(self.full, "lib-mark")
        spec = {"team": "tooling", "type": "derive", "base": "seat-engineering", "seat": "Tooling engineer",
                "mark": name("ceo").split()[0], "scope": "the build tools", "why": "x"}
        plan_file = root / "docs" / "team" / "mark.json"
        plan_file.write_text(json.dumps({"seats": [spec]}, ensure_ascii=False), encoding="utf-8")
        self.assertRefused(root, ["--plan", plan_file, "--force"],
                           f"🧭 Tooling engineer: the mark 🧭 is already {name('ceo')}'s")

    def test_a_bad_seat_spec_is_refused(self):
        root = clone(self.full, "lib-bad")
        self.assertRefused(root, ["--add", "astrologer"], "not in the catalogue: astrologer")


class MonorepoFullTests(unittest.TestCase):
    """The full option on the monorepo: two frontend splits and a derived hardware seat, unauthored."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = fx.build_monorepo(new_dir("mono-full"), ENV)
        cls.plan, cls.out = seat_up(cls.root, "full")
        cls.derived = [s for s in cls.plan["seats"] if s["type"] == "derive"]

    def authored(self, label: str) -> Path:
        root = clone(self.root, label)
        self.assertEqual(len(strip_authoring_blocks(root)), len(self.derived))
        gen_write(root)
        return root

    def test_derived_seats_are_unauthored_and_have_no_worker(self):
        self.assertEqual(sorted(s["team"] for s in self.derived), ["frontend-admin", "frontend-web", "hardware"])
        lock = teamlib.load_lock(self.root)
        for s in self.derived:
            self.assertIn(f"NEEDS AUTHORING: .claude/skills/seat-{s['team']}/SKILL.md", self.out)
            text = (self.root / ".claude" / "skills" / f"seat-{s['team']}" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("**Scope of this seat:**", text)
            self.assertRegex(text, rf"(?m)^# {re.escape(s['mark'])} {re.escape(s['seat'])}$")
            self.assertIn(f'description: "{s["mark"]} {s["seat"]}: {s["scope"]}. Derived from', text)
            self.assertFalse((self.root / ".claude" / "agents" / f"{s['team']}-worker.md").exists(),
                             f"no worker for {s['team']} until its rulebook is authored")
            entry = lock[f"seat-{s['team']}"]
            self.assertEqual((entry["origin"], entry["seated"], entry["mark"]), (f"derive:{s['base']}", TODAY, s["mark"]))
        self.assertTrue((self.root / ".claude" / "agents" / "mobile-worker.md").is_file())
        res = gen_check(self.root)
        self.assertEqual(res.returncode, 1, "the check must fail while a rulebook needs authoring")
        self.assertEqual(res.stderr.count("AUTHORING NEEDED"), len(self.derived), res.stderr)

    def test_the_check_passes_once_the_rulebooks_are_authored_and_workers_written(self):
        root = clone(self.root, "mono-authored")
        strip_authoring_blocks(root)
        res = gen_check(root)
        self.assertEqual(res.returncode, 1, "authoring alone leaves the workers to write")
        self.assertIn("stale or missing: .claude/agents/hardware-worker.md", res.stderr)
        gen_write(root)
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        for s in self.derived:
            self.assertTrue((root / ".claude" / "agents" / f"{s['team']}-worker.md").is_file())

    def test_a_derived_rulebook_points_at_its_own_paths(self):
        text = (self.root / ".claude" / "skills" / "seat-hardware" / "SKILL.md").read_text(encoding="utf-8")
        banner = [l for l in text.splitlines() if "AUTHORING NEEDED" in l]
        self.assertEqual(len(banner), 1)
        self.assertTrue(banner[0].startswith(f"> **AUTHORING NEEDED. Do not act under this rulebook:** it was copied "
                                             f"from {name('mobile')} (`seat-mobile`)"), banner[0])
        self.assertIn("tell the CEO and stop", banner[0])
        self.assertRegex(text, r"(?m)^name: seat-hardware$")
        for own in ("docs/team/hardware.md", "scratchpad/team/inbox/hardware.md", "hardware-worker"):
            self.assertIn(own, text)
        for base in ("docs/team/mobile.md", "scratchpad/team/inbox/mobile.md", "scratchpad/team/runs/mobile/",
                     "mobile-worker"):
            self.assertNotIn(base, text)
        self.assertNotIn("seat-mobile", text.replace(banner[0], ""), "only the banner names the base rulebook")

    def test_a_derived_seats_brief_carries_its_scope(self):
        brief = (self.root / "docs" / "team" / "frontend-web.md").read_text(encoding="utf-8")
        self.assertIn("- **Scope:** only apps/web/; each other UI app has its own frontend seat\n- **Paths:**", brief)

    def test_the_frontend_seat_cannot_be_added_beside_its_splits(self):
        root = clone(self.root, "mono-split-cover")
        before = snapshot(root / "docs", root / ".claude")
        res = scaffold(root, "--add", "frontend", check=False)
        self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
        self.assertIn(f"{name('frontend')} is covered by its split seats 💻 Frontend engineer (admin), "
                      "🪟 Frontend engineer (web); retire them in the same plan, or pass --force", res.stderr)
        self.assertEqual(snapshot(root / "docs", root / ".claude"), before)

    def test_sync_never_touches_derived_rulebooks(self):
        root = clone(self.root, "mono-sync-unauthored")
        out = scaffold(root, "--sync").stdout
        self.assertIn("still needs authoring: .claude/skills/seat-hardware", out)
        root = self.authored("mono-sync")
        derived = [root / ".claude" / "skills" / f"seat-{s['team']}" for s in self.derived]
        before = snapshot(*derived)
        out = scaffold(root, "--sync").stdout
        self.assertEqual(snapshot(*derived), before)
        n = len(roster_teams(root))
        self.assertIn(f"compared {n - 3} of {n} seated rulebooks; the project's own, never synced: "
                      "seat-frontend-admin, seat-frontend-web, seat-hardware", out)
        self.assertEqual(gen_check(root).returncode, 0)

    def test_retiring_a_derived_seat_archives_it_and_re_adding_restores_it(self):
        root = self.authored("mono-retire-derived")
        skill = root / ".claude" / "skills" / "seat-hardware" / "SKILL.md"
        marker = "- Project rule: flash the test bench before every release."
        with skill.open("a", encoding="utf-8") as f:
            f.write(marker + "\n")
        out = scaffold(root, "--retire", "hardware", "--record", "no device this year").stdout
        archive = root / "docs" / "team" / "retired" / f"seat-hardware-{TODAY}"
        self.assertIn(f"archived (derived): docs/team/retired/seat-hardware-{TODAY}", out)
        self.assertIn(marker, (archive / "SKILL.md").read_text(encoding="utf-8"))
        self.assertFalse(skill.exists())
        self.assertNotIn("hardware", roster_teams(root))
        self.assertFalse((root / ".claude" / "agents" / "hardware-worker.md").exists())
        self.assertEqual(gen_check(root).returncode, 0)

        spec = next(s for s in self.derived if s["team"] == "hardware")
        plan_file = root / "docs" / "team" / "hardware.json"
        plan_file.write_text(json.dumps({"seats": [spec]}, ensure_ascii=False), encoding="utf-8")
        out = scaffold(root, "--plan", plan_file).stdout
        self.assertIn(f"restored: .claude/skills/seat-hardware from docs/team/retired/seat-hardware-{TODAY} "
                      "(its newest archived copy)", out)
        self.assertIn("back in use, Retired line removed: docs/team/hardware.md", out)
        self.assertIn(marker, skill.read_text(encoding="utf-8"))
        self.assertNotIn("AUTHORING NEEDED", skill.read_text(encoding="utf-8"))
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


# ---------------------------------------------------------------------------- reevaluate

class ReevaluateTests(unittest.TestCase):
    def test_commits_are_attributed_by_subject_prefix(self):
        root = fx.build_saas(new_dir("re-attr"), ENV)
        scaffold(root, "--project", "Tally", "--seats", "engineering,sales,design")
        fx.empty_commits(root, ["sales: pricing page copy", "sales(pricing): the plan ladder",
                                "engineering: checkout route", "chore: bump versions"], ENV)
        stats = reevaluate(root)["activity"]
        self.assertEqual(stats["stats"]["sales"]["commits"], 2)
        self.assertEqual(stats["stats"]["engineering"]["commits"], 1)
        self.assertEqual(stats["stats"]["design"]["commits"], 0)
        self.assertEqual(stats["attributed"], 3)
        self.assertEqual(stats["unattributed"], 2, "the initial commit and the chore commit")

    def test_a_team_without_a_baseline_counts_nothing_as_new_and_gets_a_chief_of_staff(self):
        root = fx.build_lib(new_dir("re-coord-add"), ENV)
        scaffold(root, "--project", "Tally", "--seats", "engineering,testing,docs,community")
        self.assertEqual(sorted(roster_teams(root)), ["bar-raiser", "ceo", "community", "docs", "engineering", "testing"])
        result = reevaluate(root)
        self.assertFalse(result["baseline"])
        self.assertEqual((result["new_signals"], result["gone_signals"]), ([], []))
        self.assertTrue(result["notes"][0].startswith("There is no setup baseline (docs/team/scan.json)"), result["notes"])
        self.assertEqual(keys(result), ["add:chief-of-staff"])
        self.assertEqual(result["proposals"][0]["why"],
                         "With 6 other seats, one seat talks to you and keeps the tracker.")

    def test_the_add_step_follows_the_recorded_option(self):
        root = fx.build_lib(new_dir("re-option"), ENV)
        seat_up(root, "lean")
        result = reevaluate(root)
        self.assertEqual(result["option"], "lean")
        self.assertEqual(keys(result), [], "five seats in lean: no Chief of Staff yet")
        plan_file = root / "docs" / "team" / "plan.json"
        plan = read_json(plan_file)
        plan["option"] = "recommended"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(keys(reevaluate(root)), ["add:chief-of-staff"])

    def test_a_new_model_dependency_proposes_ml_new_since_setup(self):
        root = fx.build_saas(new_dir("re-ml"), ENV)
        seat_up(root, "recommended")
        fx.put(root, "requirements.txt", "torch==2.3.0\n")
        fx.commit_all(root, "engineering: late-payment risk model", ENV)
        result = reevaluate(root)
        self.assertEqual(result["new_signals"], ["ml"])
        adds = [p for p in result["proposals"] if p["key"] == "add:ml"]
        self.assertEqual(len(adds), 1, result["proposals"])
        self.assertEqual((adds[0]["title"], adds[0]["signals"]), (f"Add {name('ml')}", ["ml"]))
        self.assertIn("new since setup", adds[0]["why"])
        self.assertIn("torch", adds[0]["why"])

    def test_a_retired_seat_is_not_proposed_again_while_its_signal_is_unchanged(self):
        root = fx.build_saas(new_dir("re-retired"), ENV)
        seat_up(root, "full")
        scaffold(root, "--retire", "social")
        result = reevaluate(root)
        self.assertEqual(result["new_signals"], [])
        self.assertNotIn("add:social", keys(result), "a retired seat comes back only on a new signal")
        notes = [n for n in result["notes"] if "Social Media Manager" in n]
        self.assertEqual(len(notes), 1, result["notes"])
        self.assertIn("not proposed again", notes[0])

    def test_a_retired_seat_comes_back_on_a_signal_new_since_setup(self):
        root = fx.build_saas(new_dir("re-return"), ENV)
        seat_up(root, "recommended")  # the baseline has no model signal
        scaffold(root, "--add", "ml")
        scaffold(root, "--retire", "ml")
        self.assertTrue((root / "docs" / "team" / "ml.md").read_text(encoding="utf-8").startswith("> **Retired"))
        fx.put(root, "requirements.txt", "torch==2.3.0\n")
        fx.commit_all(root, "engineering: late-payment risk model", ENV)
        result = reevaluate(root)
        adds = [p for p in result["proposals"] if p["key"] == "add:ml"]
        self.assertEqual(len(adds), 1, result["proposals"])
        self.assertIn("new since setup", adds[0]["why"])
        self.assertFalse([n for n in result["notes"] if "ML engineer" in n], result["notes"])

    def test_a_dominant_merged_seat_is_unmerged_and_the_plan_applies(self):
        root = fx.build_saas(new_dir("re-unmerge"), ENV)
        seat_up(root, "lean")
        self.assertIn("growth", roster_teams(root))
        fx.empty_commits(root, [f"growth: post {i}" for i in range(9)] + ["frontend: pricing table"] * 3, ENV)
        result = reevaluate(root)
        self.assertEqual(result["activity"]["stats"]["growth"]["commits"], 9)
        self.assertFalse([p for p in result["proposals"] if p["action"] == "unmerge"], "9 commits is under the floor")

        fx.empty_commits(root, ["growth(social): post 9"], ENV)
        out_plan = root / "docs" / "team" / "reevaluation.json"
        result = reevaluate(root, "--out", out_plan)
        unmerges = [p for p in result["proposals"] if p["action"] == "unmerge"]
        self.assertEqual(len(unmerges), 1, result["proposals"])
        self.assertEqual((unmerges[0]["key"], unmerges[0]["team"]), ("unmerge:growth", "growth"))
        self.assertEqual(sorted(s["team"] for s in unmerges[0]["seats"]), ["sales", "seo", "social"])
        self.assertIn("10 of 13", unmerges[0]["why"])

        plan = read_json(out_plan)
        self.assertEqual((plan["project"], plan["option"], plan["source"]),
                         ("Tally", "reevaluation", "docs/team/reevaluation.json"))
        self.assertIn("growth", plan["retire"])
        scaffold(root, "--plan", out_plan)
        teams = roster_teams(root)
        self.assertNotIn("growth", teams)
        for t in ("sales", "seo", "social"):
            self.assertIn(t, teams)
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_a_merged_seat_under_the_share_stays_merged(self):
        root = fx.build_saas(new_dir("re-share"), ENV)
        seat_up(root, "lean")
        fx.empty_commits(root, [f"growth: post {i}" for i in range(10)] + ["frontend: polish"] * 25, ENV)
        result = reevaluate(root)
        self.assertEqual(result["activity"]["stats"]["growth"]["commits"], 10)
        self.assertFalse([p for p in result["proposals"] if p["action"] == "unmerge"], "10 of 35 is under 30%")

    def test_coordination_seats_stay_while_the_team_is_large_enough(self):
        root = fx.build_saas(new_dir("re-coord"), ENV)
        plan, _ = seat_up(root, "recommended")
        self.assertEqual(len(plan["seats"]), 12)
        self.assertLessEqual({"chief-of-staff", "scope-trimmer"}, set(roster_teams(root)))
        backdate(root)
        result = reevaluate(root)
        self.assertEqual(keys(result), [], "a freshly seated recommended team fits the work; nothing to retire")
        self.assertEqual(result["notes"], [])

    def test_young_seats_are_held_back(self):
        root = fx.build_saas(new_dir("re-young"), ENV)
        seat_up(root, "recommended")
        scaffold(root, "--add", "motion")
        result = reevaluate(root)
        self.assertEqual(keys(result), [])
        self.assertIn(f"Seated inside the last 30 days, so not proposed for retirement or a merge yet: {name('motion')}.",
                      result["notes"])

    def test_markdown_report_names_every_seat(self):
        root = fx.build_lib(new_dir("re-md"), ENV)
        seat_up(root, "lean")
        md = run("reevaluate.py", "--root", root).stdout
        self.assertIn("## Team re-evaluation: Tally", md)
        for r in teamlib.roster(root / "docs" / "TEAM.md"):
            self.assertIn(f"| {r['mark']} {r['seat']} |", md)

    def test_refuses_a_project_without_a_team(self):
        root = fx.build_lib(new_dir("re-none"), ENV)
        res = run("reevaluate.py", "--root", root, check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("no docs/TEAM.md", res.stderr)


class ReevaluateActivityTests(unittest.TestCase):
    """What a re-evaluation measures besides commit subjects: run logs, inbox lines, BLOCKED, the window."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = root = fx.build_saas(new_dir("re-activity"), ENV)
        seat_up(root, "recommended")
        runs = root / "scratchpad" / "team" / "runs" / "growth"
        for i in range(3):
            fx.put(root, f"scratchpad/team/runs/growth/2026-run-{i}.md", "a worker's log\n")
        old = fx.put(root, "scratchpad/team/runs/growth/old-run.md", "an old log\n")
        stamp = (datetime.datetime.now() - datetime.timedelta(days=60)).timestamp()
        os.utime(old, (stamp, stamp))
        assert runs.is_dir()
        fx.put(root, "scratchpad/team/inbox/security.md", "2026 · ⚙️ Engineering · a task · done · log\n\n"
                                                         "2026 · ⚙️ Engineering · a second task · done · log\n")
        recent = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        stale = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
        with (root / "docs" / "team" / "tracker.md").open("a", encoding="utf-8") as f:
            f.write(f"\n| # | task | seat | done when | status | stop reason · unblock |\n|---|---|---|---|---|---|\n"
                    f"| 1 | release checks | {name('quality')} | the suite is green | BLOCKED (on {name('ceo')}) | waits |\n"
                    f"| 2 | old checks | {name('quality')} | done | BLOCKED since {stale} | long ago |\n"
                    f"| 3 | pricing | {name('growth')} | live | IN PROGRESS | - |\n\n"
                    f"{recent} · {name('quality')} → {name('ceo')} · STOP · BLOCKED on the release date\n"
                    f"{stale} · {name('growth')} → {name('ceo')} · STOP · BLOCKED long ago\n")
        commit_dated(root, "frontend: pricing table", 60)
        cls.result = reevaluate(root)
        cls.wide = reevaluate(root, "--days", "90")

    def test_run_logs_inbox_lines_and_blocked_rows_are_counted(self):
        stats = self.result["activity"]["stats"]
        self.assertEqual(stats["growth"], {"commits": 0, "runs": 3, "inbox": 0, "blocked": 0, "last": TODAY})
        self.assertEqual(stats["security"], {"commits": 0, "runs": 0, "inbox": 2, "blocked": 0, "last": None})
        self.assertEqual(stats["quality"]["blocked"], 2, "the open table row and the recent log line")
        self.assertEqual(stats["frontend"]["commits"], 0, "a commit outside the window is not counted")

    def test_the_window_follows_days(self):
        stats = self.wide["activity"]["stats"]
        self.assertEqual(stats["frontend"]["commits"], 1)
        self.assertEqual(stats["growth"]["runs"], 4)
        self.assertEqual(stats["growth"]["blocked"], 1, "the old log line is inside 90 days")
        self.assertEqual(stats["quality"]["blocked"], 3)

    def test_a_deleted_folder_is_a_gone_signal(self):
        root = clone(self.root, "re-gone")
        shutil.rmtree(root / "blog")
        fx.commit_all(root, "chore: drop the blog", ENV)
        result = reevaluate(root)
        self.assertEqual((result["new_signals"], result["gone_signals"]), ([], ["content"]))


class ReevaluateRetireTests(unittest.TestCase):
    """The retire rule both ways, on a recommended SaaS team plus a 🎬 Motion & Production seat nothing calls for."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = fx.build_saas(new_dir("re-retire"), ENV)
        seat_up(cls.root, "recommended")
        scaffold(cls.root, "--add", "motion")
        backdate(cls.root)

    def test_an_idle_seat_nothing_calls_for_is_proposed_for_retirement(self):
        result = reevaluate(self.root)
        self.assertEqual(keys(result), ["retire:motion"])
        p = result["proposals"][0]
        self.assertEqual((p["title"], p["retire"], p["seats"], p["signals"]), (f"Retire {name('motion')}", ["motion"], [], []))
        self.assertEqual(p["why"], "No commits, worker runs or inbox lines in 30 days, and nothing in the repository calls for it.")

    def test_any_activity_keeps_a_seat(self):
        for label, act in (("commit", lambda r: fx.empty_commits(r, ["motion: launch cut"], ENV)),
                           ("run", lambda r: fx.put(r, "scratchpad/team/runs/motion/2026-cut.md", "log\n")),
                           ("inbox", lambda r: fx.put(r, "scratchpad/team/inbox/motion.md", "a line\n"))):
            root = clone(self.root, f"re-retire-{label}")
            act(root)
            self.assertEqual(keys(reevaluate(root)), [], f"a seat with a {label} is not idle")

    def test_a_seat_whose_signal_stands_is_never_retired(self):
        root = fx.build_lib(new_dir("re-lib-full"), ENV)
        seat_up(root, "full")
        backdate(root)
        result = reevaluate(root)
        self.assertEqual(result["activity"]["attributed"], 0, "every seat is idle")
        self.assertEqual(keys(result), [], "code, tests, a licence and a contributing guide still call for every seat")


class ReevaluateComposedSeatsTests(unittest.TestCase):
    """Re-evaluation of a full monorepo seated a while ago: two frontend splits and a derived hardware seat."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = fx.build_monorepo(new_dir("re-mono"), ENV)
        seat_up(cls.root, "full")
        strip_authoring_blocks(cls.root)
        backdate(cls.root)
        cls.result = reevaluate(cls.root)

    def test_the_seated_team_is_measured(self):
        self.assertEqual(sorted(self.result["seated"]), sorted(roster_teams(self.root)))
        self.assertIn("hardware", self.result["seated"])
        self.assertEqual(self.result["new_signals"], [])

    def test_frontend_splits_cover_the_frontend_seat(self):
        self.assertNotIn("add:frontend", keys(self.result))

    def test_derived_and_split_seats_are_not_retired_while_their_signal_stands(self):
        retires = [p["key"] for p in self.result["proposals"] if p["action"] == "retire"]
        self.assertEqual(retires, [])

    def test_derived_and_split_seats_are_retired_once_their_signal_is_gone(self):
        root = clone(self.root, "re-mono-gone")
        shutil.rmtree(root / "apps" / "admin")
        shutil.rmtree(root / "firmware")
        fx.commit_all(root, "chore: drop the admin app and the device", ENV)
        result = reevaluate(root)
        self.assertEqual(result["gone_signals"], ["hardware"])
        retires = sorted(p["key"] for p in result["proposals"] if p["action"] == "retire")
        self.assertEqual(retires, ["retire:frontend-admin", "retire:hardware"])
        self.assertNotIn("add:frontend", keys(result), "the web split still covers the Frontend engineer")


class ReevaluateMergeTests(unittest.TestCase):
    """Quiet seats on a full SaaS team seated a while ago: merges, declines, and applying the plan."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = fx.build_saas(new_dir("re-merge"), ENV)
        seat_up(cls.root, "full")
        backdate(cls.root)
        cls.plan_file = cls.root / "docs" / "team" / "reevaluation.json"
        cls.result = reevaluate(cls.root, "--out", cls.plan_file)
        cls.plan = read_json(cls.plan_file)

    def test_quiet_seats_are_proposed_as_merges_that_never_share_a_member(self):
        self.assertEqual(keys(self.result), ["merge:growth", "merge:product-design", "merge:engineering-platform",
                                             "merge:money"])
        self.assertEqual([p["retire"] for p in self.result["proposals"]],
                         [["sales", "seo", "social"], ["product", "design"], ["engineering", "platform"],
                          ["funding", "payments"]])
        held = [m for p in self.result["proposals"] for m in p["retire"]]
        self.assertEqual(len(held), len(set(held)), "a merge claims its members")
        self.assertEqual(self.result["proposals"][0]["title"],
                         f"Merge {name('sales')}, {name('seo')} and {name('social')} into {name('growth')}")

    def test_no_merge_holds_the_ceo_or_the_bar_raiser(self):
        self.assertNotIn("merge:quality", keys(self.result))
        for p in self.result["proposals"]:
            self.assertFalse({"ceo", "bar-raiser"} & set(p["retire"]), p)
            for s in p["seats"]:
                self.assertFalse({"ceo", "bar-raiser"} & set(s.get("of", [])), s)

    def test_the_plan_carries_every_proposal_and_the_unions(self):
        self.assertEqual((self.plan["project"], self.plan["option"], self.plan["source"], self.plan["date"]),
                         ("Tally", "reevaluation", "docs/team/reevaluation.json", TODAY))
        self.assertEqual([p["key"] for p in self.plan["proposals"]], keys(self.result))
        self.assertEqual([s["team"] for s in self.plan["seats"]], ["growth", "product-design", "engineering-platform", "money"])
        self.assertEqual(self.plan["retire"], ["sales", "seo", "social", "product", "design", "engineering", "platform",
                                               "funding", "payments"])
        md = run("reevaluate.py", "--root", self.root).stdout
        self.assertIn("### Keys, for `scaffold.py --plan <plan> --only KEY,...`", md)
        for p in self.result["proposals"]:
            self.assertIn(f"- **{p['title']}**: {p['why']}", md)
            self.assertIn(f"- `{p['key']}`: {p['title']}", md)

    def test_a_busy_or_blocked_member_keeps_its_merge_from_being_proposed(self):
        busy = clone(self.root, "re-merge-busy")
        for i in range(3):
            fx.put(busy, f"scratchpad/team/runs/sales/run-{i}.md", "log\n")
        self.assertNotIn("merge:growth", keys(reevaluate(busy)), "three runs is not quiet")
        blocked = clone(self.root, "re-merge-blocked")
        with (blocked / "docs" / "team" / "tracker.md").open("a", encoding="utf-8") as f:
            f.write(f"\n| # | task | seat | done when | status | stop reason · unblock |\n|---|---|---|---|---|---|\n"
                    f"| 1 | pricing | {name('sales')} | live | BLOCKED (on {name('ceo')}) | waits |\n")
        result = reevaluate(blocked)
        self.assertEqual(result["activity"]["stats"]["sales"]["blocked"], 1)
        self.assertNotIn("merge:growth", keys(result), "a blocked seat is not quiet")
        self.assertIn("merge:product-design", keys(result))

    def test_applying_the_whole_plan_never_seats_a_role_twice(self):
        root = clone(self.root, "re-merge-apply")
        scaffold(root, "--plan", root / "docs" / "team" / "reevaluation.json")
        teams = set(roster_teams(root))
        self.assertLessEqual({"growth", "product-design", "engineering-platform", "money"}, teams)
        self.assertEqual(teams & teamlib.members_covered(teamlib.load_lock(root)), set(),
                         "a role held by a merged seat is also seated on its own")
        cov = teamlib.coverage(root)
        self.assertEqual((cov["sales"], cov["payments"], cov["bar-raiser"]), ("growth", "money", "bar-raiser"))
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_only_applies_the_chosen_proposals_and_records_the_declines(self):
        root = clone(self.root, "re-merge-only")
        scaffold(root, "--plan", root / "docs" / "team" / "reevaluation.json", "--only", "merge:growth", "--record", "merge growth only",
                 "--question", "Merge the quiet seats?")
        teams = roster_teams(root)
        self.assertIn("growth", teams)
        self.assertLessEqual({"product", "design", "engineering", "platform", "funding", "payments"}, set(teams))
        declined_titles = ", ".join(p["title"] for p in self.result["proposals"][1:])
        self.assertEqual(decision_rows(root)[2],
                         f"| **DEC-2** | Merge the quiet seats? | docs/team/reevaluation.json | ✅ {TODAY}: merged "
                         f"{name('sales')}, {name('seo')}, {name('social')} into {name('growth')}. "
                         f"Declined: {declined_titles}. Owner's words: \"merge growth only\" |")
        declined = read_json(root / "docs" / "team" / "declined.json")
        self.assertEqual([(d["key"], d["action"], d["signals"], d["date"], d["decision"]) for d in declined],
                         [(k, "merge", [], TODAY, "DEC-2") for k in keys(self.result)[1:]])
        self.assertEqual(gen_check(root).returncode, 0)
        result = reevaluate(root)
        self.assertFalse(set(keys(self.result)[1:]) & set(keys(result)), "a decline is not proposed again")
        for p in self.result["proposals"][1:]:
            self.assertIn(f"{p['title']} was declined on {TODAY}; its evidence has not changed, so it is not proposed "
                          "again.", result["notes"])

    def test_only_none_declines_everything(self):
        root = clone(self.root, "re-merge-none")
        teams = roster_teams(root)
        out = scaffold(root, "--plan", root / "docs" / "team" / "reevaluation.json", "--only", "none", "--record", "not now").stdout
        self.assertIn("declined: " + ", ".join(p["title"] for p in self.result["proposals"]), out)
        self.assertEqual(roster_teams(root), teams)
        row = decision_rows(root)[2]
        self.assertIn(f"✅ {TODAY}: nothing changed. Declined: {self.result['proposals'][0]['title']}, ", row)
        self.assertEqual(len(read_json(root / "docs" / "team" / "declined.json")), 4)

    def test_only_refuses_a_key_the_plan_does_not_carry(self):
        root = clone(self.root, "re-merge-bad-key")
        res = scaffold(root, "--plan", root / "docs" / "team" / "reevaluation.json", "--only", "merge:nothing", check=False)
        self.assertEqual(res.returncode, 2)
        self.assertIn("not a proposal in this plan: merge:nothing (its proposals: " + ", ".join(keys(self.result)),
                      res.stderr)
        res = scaffold(root, "--plan", root / "docs" / "team" / "plan.json", "--only", "add:ml", check=False)
        self.assertEqual(res.returncode, 2)
        self.assertIn("--only needs a plan that carries proposals", res.stderr)
        self.assertFalse((root / "docs" / "team" / "declined.json").exists())


class ReevaluateDeclineTests(unittest.TestCase):
    def test_a_declined_add_returns_only_on_a_signal_it_did_not_rest_on(self):
        root = fx.build_saas(new_dir("re-decline"), ENV)
        seat_up(root, "recommended")
        fx.put(root, "requirements.txt", "torch==2.3.0\n")
        fx.commit_all(root, "engineering: late-payment risk model", ENV)
        plan_file = root / "docs" / "team" / "reevaluation.json"
        self.assertIn("add:ml", keys(reevaluate(root, "--out", plan_file)))
        scaffold(root, "--plan", plan_file, "--only", "none", "--record", "not now")
        declined_file = root / "docs" / "team" / "declined.json"
        declined = read_json(declined_file)
        ml = [d for d in declined if d["key"] == "add:ml"]
        self.assertEqual([(d["signals"], d["decision"]) for d in ml], [(["ml"], "DEC-2")])
        result = reevaluate(root)
        self.assertNotIn("add:ml", keys(result), "the signal was already part of the declined proposal")
        self.assertIn(f"Add {name('ml')} was declined on {TODAY}; its evidence has not changed, so it is not proposed "
                      "again.", result["notes"])
        for d in declined:  # declined before the model arrived: the signal is new to the decline
            d["signals"] = []
        declined_file.write_text(json.dumps(declined, ensure_ascii=False), encoding="utf-8")
        self.assertIn("add:ml", keys(reevaluate(root)))


class ReevaluateLargeTests(unittest.TestCase):
    def test_a_large_project_splits_the_frontend_seat(self):
        root = fx.build_monorepo(new_dir("re-large"), ENV)
        seat_up(root, "recommended")
        self.assertIn("frontend", roster_teams(root))
        for i in range(3000):
            fx.put(root, f"apps/web/src/generated/Row{i}.ts", f"export const row{i} = {i}\n")
        fx.commit_all(root, "chore: generated rows", ENV)
        backdate(root)
        plan_file = root / "docs" / "team" / "reevaluation.json"
        result = reevaluate(root, "--out", plan_file)
        self.assertEqual(result["size"], "large")
        self.assertNotIn("merge:engineering-platform", keys(result), "never past 2,000 source files")
        split = [p for p in result["proposals"] if p["key"] == "split:frontend"]
        self.assertEqual(len(split), 1, keys(result))
        self.assertEqual([(s["team"], s["mark"], s["scope"]) for s in split[0]["seats"]],
                         [("frontend-admin", "💻", "only apps/admin/; each other UI app has its own frontend seat"),
                          ("frontend-web", "🪟", "only apps/web/; each other UI app has its own frontend seat")])
        self.assertEqual((split[0]["retire"], split[0]["signals"]), (["frontend"], ["ui_web"]))
        self.assertEqual(split[0]["title"], f"Split {name('frontend')} into one seat per web app: "
                                            "💻 Frontend engineer (admin) and 🪟 Frontend engineer (web)")
        out = scaffold(root, "--plan", plan_file, "--only", "split:frontend").stdout
        self.assertIn("NEEDS AUTHORING: .claude/skills/seat-frontend-web/SKILL.md", out)
        teams = roster_teams(root)
        self.assertNotIn("frontend", teams)
        self.assertLessEqual({"frontend-admin", "frontend-web"}, set(teams))


class WalkthroughMeasureTests(unittest.TestCase):
    def test_a_job_wide_git_identity_does_not_merge_the_contributors(self):
        """CI sets GIT_AUTHOR_*/GIT_COMMITTER_*; the walkthrough's four contributors must still measure four."""
        env = dict(os.environ, GIT_AUTHOR_NAME="CI", GIT_AUTHOR_EMAIL="ci@example.invalid",
                   GIT_COMMITTER_NAME="CI", GIT_COMMITTER_EMAIL="ci@example.invalid")
        res = subprocess.run([sys.executable, str(REPO / "tools" / "measure_tally.py"), "--check"],
                             env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("every measured figure holds", res.stdout)


if __name__ == "__main__":
    unittest.main()
