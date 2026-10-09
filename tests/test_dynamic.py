"""Dynamic seats, end to end: scan, plan, scaffold and re-evaluate on fixture repos.

    python3 -m unittest discover -s tests -v        (from the repo root; stdlib only, no network)

Each test builds its fixture repos (tests/repo_fixtures.py) in one temporary folder, runs the
team-setup scripts on them (in process for scan and plan, as commands for everything that writes),
and checks what the scripts promise in their docstrings. Git runs with a fixed identity and no user
config, and never climbs above the temporary folder; HOME points at an empty folder so no globally
installed skill can stand in for a project's rulebook.

A test marked `expectedFailure` pins a script defect: its comment starts with "BUG:" and says what
is wrong. When the script is fixed the test reports an unexpected success: delete the decorator.
"""
from __future__ import annotations

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
import teamlib  # noqa: E402

CAT = teamlib.catalogue()
GIT_KEYS = ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CEILING_DIRECTORIES", "GIT_TERMINAL_PROMPT")
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


def run(script: str, *args, scripts: Path = SCRIPTS, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run([sys.executable, str(scripts / script), *map(str, args)], capture_output=True,
                         text=True, env=ENV)
    if check and res.returncode != 0:
        raise AssertionError(f"{script} {' '.join(map(str, args))} exited {res.returncode}\n"
                             f"--- stdout\n{res.stdout}\n--- stderr\n{res.stderr}")
    return res


def gen_check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "scripts" / "gen-team-agents.py"), "--check"],
                          capture_output=True, text=True, env=ENV, cwd=root)


def seat_up(root: Path, option: str, record: str | None = None) -> tuple[dict, str]:
    """Setup as the team-setup skill runs it: save the scan baseline, write one option's plan, scaffold it."""
    run("scan.py", "--root", root, "--save")
    plan_file = root / "docs" / "team" / "plan.json"
    run("plan.py", "--scan", root / "docs" / "team" / "scan.json", "--option", option, "--out", plan_file,
        "--project", "Tally")
    args = ["--root", root, "--plan", plan_file] + (["--record", record] if record else [])
    out = run("scaffold.py", *args).stdout
    return json.loads(plan_file.read_text(encoding="utf-8")), out


def roster_teams(root: Path) -> list[str]:
    return [r["team"] for r in teamlib.roster(root / "docs" / "TEAM.md")]


def reevaluate(root: Path, *extra) -> dict:
    return json.loads(run("reevaluate.py", "--root", root, "--json", *extra).stdout)


def mark_of(spec: dict) -> str:
    return CAT[spec["team"]]["mark"] if spec.get("type", "catalogue") == "catalogue" else spec["mark"]


def strip_authoring_blocks(root: Path) -> list[Path]:
    """What the session does after rewriting a derived rulebook for its role: delete the block."""
    done = []
    for f in (root / ".claude" / "skills").glob("seat-*/SKILL.md"):
        text = f.read_text(encoding="utf-8")
        if "AUTHORING NEEDED" in text:
            f.write_text("".join(l for l in text.splitlines(keepends=True) if "AUTHORING NEEDED" not in l),
                         encoding="utf-8")
            done.append(f)
    return done


def snapshot(*dirs: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for d in dirs for p in sorted(d.rglob("*")) if p.is_file()}


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
        self.assertSignals(self.lib, {"code", "tests", "ci", "oss"},
                           {"ui_web", "payments", "auth", "mobile", "deploy", "monorepo", "game"})
        self.assertIn("LICENSE", self.lib["signals"]["oss"])
        self.assertEqual(self.lib["size"]["ui_apps"], [])

    def test_saas_signals(self):
        self.assertSignals(self.saas, {"ui_web", "db", "payments", "auth", "email", "analytics", "landing", "content",
                                       "deploy", "migrations", "personal_data", "tests", "code"},
                           {"oss", "mobile", "ml", "hardware", "game", "monorepo"})
        self.assertIn("prisma/schema.prisma", self.saas["signals"]["personal_data"])
        self.assertIn("app/pricing/page.tsx", self.saas["signals"]["landing"])
        self.assertEqual(self.saas["size"]["ui_apps"], ["."])

    def test_monorepo_signals_and_ui_apps(self):
        self.assertSignals(self.mono, {"ui_web", "mobile", "ml", "data_pipelines", "i18n", "hardware", "tests", "ci",
                                       "deploy", "code", "monorepo"}, {"payments", "game", "oss"})
        self.assertIn("dependency torch", self.mono["signals"]["ml"])
        self.assertIn("firmware/platformio.ini", self.mono["signals"]["hardware"])
        ui_apps = self.mono["size"]["ui_apps"]
        self.assertEqual(ui_apps, ["apps/admin", "apps/web"])
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
        saved = json.loads((root / "docs" / "team" / "scan.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["signals"], out["signals"])

    def test_size_counts_the_history(self):
        self.assertEqual(self.lib["size"]["commits"], 1)
        self.assertEqual(self.lib["size"]["contributors"], 1)
        self.assertGreaterEqual(self.mono["size"]["code_files"], 80)


# ---------------------------------------------------------------------------- plan

class PlanTests(unittest.TestCase):
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

    def test_merged_members_are_not_seated_twice(self):
        for name, option, seats in self.each_option():
            teams = [s["team"] for s in seats]
            held = [m for s in seats if s["type"] == "merge" for m in s["of"]]
            self.assertEqual(len(held), len(set(held)), f"{name}/{option}: a member sits in two merges: {held}")
            self.assertFalse(set(teams) & set(held), f"{name}/{option}: {set(teams) & set(held)} seated and merged")

    def test_marks_are_unique_within_every_option(self):
        for name, option, seats in self.each_option():
            marks = [mark_of(s) for s in seats]
            dupes = sorted({m for m in marks if marks.count(m) > 1})
            self.assertEqual(dupes, [], f"{name}/{option}: duplicate marks {dupes}")
            teams = [s["team"] for s in seats]
            self.assertEqual(len(teams), len(set(teams)), f"{name}/{option}: duplicate teams")

    def test_full_monorepo_splits_frontend_and_derives_hardware(self):
        full = self.opts["mono"]["full"]
        splits = [s for s in full if s["type"] == "derive" and s.get("base") == "seat-frontend"]
        self.assertEqual(sorted(s["team"] for s in splits), ["frontend-admin", "frontend-web"])
        self.assertEqual(len({s["mark"] for s in splits}), len(splits), "split seats need distinct marks")
        self.assertNotIn("frontend", [s["team"] for s in full], "the splits replace the single frontend seat")
        for s in splits:
            self.assertIn(s["team"].split("-", 1)[1], s["scope"])
        hardware = [s for s in full if s["team"] == "hardware"]
        self.assertEqual(len(hardware), 1)
        self.assertEqual((hardware[0]["type"], hardware[0]["mark"]), ("derive", "🔌"))
        self.assertIn("platformio.ini", hardware[0]["why"])

    def test_recommended_scales_with_size(self):
        tiny = self.opts["saas"]["recommended"]
        self.assertTrue(any(s["type"] == "merge" for s in tiny), "a tiny project takes the merges")
        small = self.opts["mono"]["recommended"]
        small_merges = {s["team"] for s in small if s["type"] == "merge"}
        self.assertLessEqual(small_merges, set(planner.SMALL_MERGES), "a small project merges only commercial seats")
        self.assertIn("engineering", [s["team"] for s in small])

    def test_cli_writes_the_chosen_option(self):
        root = new_dir("plan-cli")
        scan_file = root / "scan.json"
        scan_file.write_text(json.dumps(self.scans["saas"]), encoding="utf-8")
        out = root / "docs" / "team" / "plan.json"
        run("plan.py", "--scan", scan_file, "--option", "recommended", "--out", out, "--project", "Tally")
        plan = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual((plan["project"], plan["option"], plan["retire"]), ("Tally", "recommended", []))
        self.assertEqual([s["team"] for s in plan["seats"]], [s["team"] for s in self.opts["saas"]["recommended"]])
        md = run("plan.py", "--scan", scan_file, "--markdown").stdout
        for option in ("Lean", "Recommended", "Full"):
            self.assertIn(f"### {option}: ", md)


# ---------------------------------------------------------------------------- scaffold

class ScaffoldTests(unittest.TestCase):
    def test_lean_setup_composes_merged_rulebooks_and_passes_the_check(self):
        root = fx.build_saas(new_dir("saas-lean"), ENV)
        plan, _ = seat_up(root, "lean")
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        merges = [s for s in plan["seats"] if s["type"] == "merge"]
        self.assertTrue(merges, "the lean option for a tiny product merges seats")
        self.assertEqual(sorted(roster_teams(root)), sorted(s["team"] for s in plan["seats"]))
        lock = teamlib.load_lock(root)
        for m in merges:
            text = (root / ".claude" / "skills" / f"seat-{m['team']}" / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(text, rf"(?m)^name: seat-{re.escape(m['team'])}$")
            self.assertRegex(text, rf"(?m)^# {re.escape(m['mark'])} {re.escape(m['seat'])}$")
            for member in m["of"]:
                row = CAT[member]
                self.assertIn(f"### As {row['mark']} {row['seat']}", text, f"{m['team']} lost {member}")
            for n in range(7):
                self.assertRegex(text, rf"(?m)^## {n} · ", f"{m['team']} has no section {n}")
            self.assertEqual(lock[f"seat-{m['team']}"]["origin"], "merge:" + "+".join(m["of"]))
            self.assertTrue((root / ".claude" / "agents" / f"{m['team']}-worker.md").is_file())

    def test_full_setup_fails_the_check_until_derived_rulebooks_are_authored(self):
        root = fx.build_monorepo(new_dir("mono-full"), ENV)
        plan, out = seat_up(root, "full")
        derived = [s for s in plan["seats"] if s["type"] == "derive"]
        self.assertEqual(sorted(s["team"] for s in derived), ["frontend-admin", "frontend-web", "hardware"])
        for s in derived:
            self.assertIn(f"NEEDS AUTHORING: .claude/skills/seat-{s['team']}/SKILL.md", out)
            text = (root / ".claude" / "skills" / f"seat-{s['team']}" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("**Scope of this seat:**", text)
            self.assertRegex(text, rf"(?m)^# {re.escape(s['mark'])} {re.escape(s['seat'])}$")
        res = gen_check(root)
        self.assertEqual(res.returncode, 1, "the check must fail while a rulebook needs authoring")
        self.assertEqual(res.stderr.count("AUTHORING NEEDED"), len(derived), res.stderr)
        self.assertEqual(len(strip_authoring_blocks(root)), len(derived))
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_add_then_retire_a_seat(self):
        root = fx.build_lib(new_dir("lib-add"), ENV)
        seat_up(root, "full")
        self.assertNotIn("design", roster_teams(root))
        run("scaffold.py", "--root", root, "--add", "design")
        self.assertIn("design", roster_teams(root))
        worker = root / ".claude" / "agents" / "design-worker.md"
        skill = root / ".claude" / "skills" / "seat-design" / "SKILL.md"
        brief = root / "docs" / "team" / "design.md"
        for f in (worker, skill, brief):
            self.assertTrue(f.is_file(), f)
        self.assertEqual(gen_check(root).returncode, 0)

        out = run("scaffold.py", "--root", root, "--retire", "design").stdout
        self.assertIn("retired: 📐 Design", out)
        self.assertNotIn("design", roster_teams(root))
        self.assertTrue(brief.read_text(encoding="utf-8").startswith("> **Retired "), "the brief is kept, marked retired")
        self.assertFalse(worker.exists(), "the retired seat's worker is removed")
        self.assertFalse(skill.parent.exists(), "the retired catalogue rulebook is removed")
        self.assertNotIn("seat-design", teamlib.load_lock(root))
        self.assertEqual(gen_check(root).returncode, 0)

    def test_ceo_and_bar_raiser_refuse_to_retire(self):
        root = fx.build_lib(new_dir("lib-keep"), ENV)
        seat_up(root, "full")
        out = run("scaffold.py", "--root", root, "--retire", "ceo,bar-raiser").stdout
        self.assertIn("not retired: ceo", out)
        self.assertIn("not retired: bar-raiser", out)
        teams = roster_teams(root)
        self.assertIn("ceo", teams)
        self.assertIn("bar-raiser", teams)
        for t in ("ceo", "bar-raiser"):
            self.assertTrue((root / ".claude" / "agents" / f"{t}-worker.md").is_file())
            self.assertFalse((root / "docs" / "team" / f"{t}.md").read_text(encoding="utf-8").startswith("> **Retired"))
        self.assertEqual(gen_check(root).returncode, 0)

    def test_unmerge_through_a_plan(self):
        root = fx.build_saas(new_dir("saas-unmerge"), ENV)
        seat_up(root, "lean")
        self.assertIn("growth", roster_teams(root))
        members = ["sales", "seo", "social"]
        plan = {"project": "Tally", "seats": [{"team": t, "type": "catalogue", "why": "split out of growth"}
                                              for t in members], "retire": ["growth"]}
        plan_file = root / "docs" / "team" / "unmerge.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        run("scaffold.py", "--root", root, "--plan", plan_file)
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
        res = gen_check(root)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_record_appends_numbered_decisions(self):
        root = fx.build_lib(new_dir("lib-record"), ENV)
        seat_up(root, "lean", record="yes, seat the lean team")
        run("scaffold.py", "--root", root, "--add", "design", "--record", "add design for the docs pages")
        run("scaffold.py", "--root", root, "--retire", "design", "--record", "retire design, nobody needs it yet")
        text = (root / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
        numbers = [int(n) for n in re.findall(r"\*\*DEC-(\d+)\*\*", text)]
        self.assertEqual(numbers, [1, 2, 3, 4])
        rows = {n: line for line in text.splitlines() for n in numbers if line.startswith(f"| **DEC-{n}** |")}
        self.assertIn("The team: seat", rows[2])
        self.assertIn('*"yes, seat the lean team"*', rows[2])
        self.assertIn("Team change: seat 📐 Design", rows[3])
        self.assertIn("Team change: retire design", rows[4])
        self.assertIn('*"retire design, nobody needs it yet"*', rows[4])

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


# ---------------------------------------------------------------------------- reevaluate

class ReevaluateTests(unittest.TestCase):
    def test_commits_are_attributed_by_subject_prefix(self):
        root = fx.build_saas(new_dir("re-attr"), ENV)
        run("scaffold.py", "--root", root, "--project", "Tally", "--seats", "engineering,sales,design")
        fx.empty_commits(root, ["sales: pricing page copy", "sales(pricing): the plan ladder",
                                "engineering: checkout route", "chore: bump versions"], ENV)
        stats = reevaluate(root)["activity"]
        self.assertEqual(stats["stats"]["sales"]["commits"], 2)
        self.assertEqual(stats["stats"]["engineering"]["commits"], 1)
        self.assertEqual(stats["stats"]["design"]["commits"], 0)
        self.assertEqual(stats["attributed"], 3)
        self.assertEqual(stats["unattributed"], 2, "the initial commit and the chore commit")

    def test_a_new_model_dependency_proposes_ml_new_since_setup(self):
        root = fx.build_saas(new_dir("re-ml"), ENV)
        seat_up(root, "recommended")
        fx.put(root, "requirements.txt", "torch==2.3.0\n")
        fx.commit_all(root, "engineering: late-payment risk model", ENV)
        result = reevaluate(root)
        self.assertIn("ml", result["new_signals"])
        adds = [p for p in result["proposals"] if p["action"] == "add" and p["spec"]["team"] == "ml"]
        self.assertEqual(len(adds), 1, result["proposals"])
        self.assertIn("new since setup", adds[0]["why"])
        self.assertIn("torch", adds[0]["why"])

    def test_a_retired_seat_is_not_proposed_again_while_its_signal_is_unchanged(self):
        root = fx.build_saas(new_dir("re-retired"), ENV)
        seat_up(root, "full")
        run("scaffold.py", "--root", root, "--retire", "social")
        result = reevaluate(root)
        self.assertEqual(result["new_signals"], [])
        readds = [p for p in result["proposals"] if p["action"] == "add" and p["spec"]["team"] == "social"]
        self.assertEqual(readds, [], "a retired seat comes back only on a new signal")
        notes = [n for n in result["notes"] if "Social Media Manager" in n]
        self.assertEqual(len(notes), 1, result["notes"])
        self.assertIn("not proposed again", notes[0])

    def test_a_retired_seat_comes_back_on_a_signal_new_since_setup(self):
        root = fx.build_saas(new_dir("re-return"), ENV)
        seat_up(root, "recommended")  # the baseline has no model signal
        run("scaffold.py", "--root", root, "--add", "ml")
        run("scaffold.py", "--root", root, "--retire", "ml")
        self.assertTrue((root / "docs" / "team" / "ml.md").read_text(encoding="utf-8").startswith("> **Retired"))
        fx.put(root, "requirements.txt", "torch==2.3.0\n")
        fx.commit_all(root, "engineering: late-payment risk model", ENV)
        result = reevaluate(root)
        adds = [p for p in result["proposals"] if p["action"] == "add" and p["spec"]["team"] == "ml"]
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
        self.assertEqual(unmerges[0]["team"], "growth")
        self.assertEqual(sorted(s["team"] for s in unmerges[0]["spec"]), ["sales", "seo", "social"])
        self.assertIn("10 of 13", unmerges[0]["why"])

        plan = json.loads(out_plan.read_text(encoding="utf-8"))
        self.assertIn("growth", plan["retire"])
        run("scaffold.py", "--root", root, "--plan", out_plan)
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

    # BUG: reevaluate.py's retire step exempts the Chief of Staff while the team has 5+ seats, but has no
    # matching exemption for the Scope Trimmer at 10+, the size at which plan.py seats it and the add step
    # proposes it. A freshly seated recommended team of 12 is told at once to retire the Scope Trimmer.
    @unittest.expectedFailure
    def test_coordination_seats_stay_while_the_team_is_large_enough(self):
        root = fx.build_saas(new_dir("re-coord"), ENV)
        plan, _ = seat_up(root, "recommended")
        self.assertGreaterEqual(len(plan["seats"]), 10)
        self.assertIn("scope-trimmer", roster_teams(root))
        retires = [p["team"] for p in reevaluate(root)["proposals"] if p["action"] == "retire"]
        self.assertEqual([t for t in retires if t in ("chief-of-staff", "scope-trimmer")], [])

    def test_markdown_report_names_every_seat(self):
        root = fx.build_lib(new_dir("re-md"), ENV)
        seat_up(root, "lean")
        md = run("reevaluate.py", "--root", root).stdout
        self.assertIn("## Team re-evaluation:", md)
        for r in teamlib.roster(root / "docs" / "TEAM.md"):
            self.assertIn(f"| {r['mark']} {r['seat']} |", md)

    def test_refuses_a_project_without_a_team(self):
        root = fx.build_lib(new_dir("re-none"), ENV)
        res = run("reevaluate.py", "--root", root, check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("no docs/TEAM.md", res.stderr)


class ReevaluateComposedSeatsTests(unittest.TestCase):
    """Re-evaluation of a freshly seated full monorepo: two frontend splits and a derived hardware seat."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = fx.build_monorepo(new_dir("re-mono"), ENV)
        seat_up(cls.root, "full")
        strip_authoring_blocks(cls.root)
        cls.result = reevaluate(cls.root)

    def test_the_seated_team_is_measured(self):
        self.assertEqual(sorted(self.result["seated"]), sorted(roster_teams(self.root)))
        self.assertIn("hardware", self.result["seated"])
        self.assertEqual(self.result["new_signals"], [])

    # BUG: reevaluate.py's add step counts only seated teams and merge members as covered; the frontend
    # split seats (frontend-admin, frontend-web, made by plan.py's ui_splits) do not cover "frontend", so a
    # re-evaluation right after a full setup proposes "Add Frontend engineer" next to the two splits.
    @unittest.expectedFailure
    def test_frontend_splits_cover_the_frontend_seat(self):
        adds = [p["spec"]["team"] for p in self.result["proposals"] if p["action"] == "add"]
        self.assertNotIn("frontend", adds)

    # BUG: reevaluate.py's retire step treats a seat as needed only if its team is in plan.needs()'s core or
    # optional seats; derived seats (hardware from platformio.ini) and frontend splits are never there, so
    # each is proposed for retirement "with no repo signal that calls for it" while its signal stands.
    @unittest.expectedFailure
    def test_derived_and_split_seats_are_not_retired_while_their_signal_stands(self):
        retires = [p["team"] for p in self.result["proposals"] if p["action"] == "retire"]
        self.assertEqual([t for t in retires if t in ("hardware", "frontend-admin", "frontend-web")], [])


class ReevaluateMergeAppliesTests(unittest.TestCase):
    # BUG: reevaluate.py proposes merging quiet testing and bar-raiser into Quality and lists bar-raiser in
    # the plan's retire list, but scaffold.py refuses to retire bar-raiser (teamlib.ALWAYS). Applying the
    # plan seats Quality (which holds the Bar Raiser role) next to the separate Bar Raiser: one role, two seats.
    @unittest.expectedFailure
    def test_an_applied_merge_never_seats_a_role_twice(self):
        root = fx.build_lib(new_dir("re-quality"), ENV)
        seat_up(root, "full")
        out_plan = root / "docs" / "team" / "reevaluation.json"
        result = reevaluate(root, "--out", out_plan)
        merges = [p for p in result["proposals"] if p["action"] == "merge"]
        self.assertIn("quality", [p["spec"]["team"] for p in merges])
        run("scaffold.py", "--root", root, "--plan", out_plan)
        teams = set(roster_teams(root))
        held = {m for m in teamlib.members_covered(teamlib.load_lock(root))}
        self.assertEqual(teams & held, set(), "a role held by a merged seat is also seated on its own")


if __name__ == "__main__":
    unittest.main()
