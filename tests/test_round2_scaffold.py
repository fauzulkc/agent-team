"""Regression tests for the second fix round of scaffold.py, teamlib.py, seatgen.py and gen-team-agents.py.

    python3 -m unittest tests.test_round2_scaffold -v        (from the repo root; stdlib only)

Each test builds a small fixture repo (tests/repo_fixtures.py) in its own temporary folder and checks
one fixed behaviour: retires settled before the conflict and mark checks, every holder of a role
checked, merged rulebooks naming only the merged seat's own paths, escaped roster cells, the extension
engineer not counted as a frontend split, the owner registers on every run, unparsed roster rows
refused, the project's own folders kept, retired briefs never overwritten, members' facts carried into
a re-merged brief, an empty --only refused, the first H1 alone naming the project, line endings that
do not change a composed rulebook's hash, a plan outside the project cited by name, and duplicate or
contradictory retires.
"""
from __future__ import annotations

import json
import re
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

import repo_fixtures as fx  # noqa: E402
import seatgen  # noqa: E402
import teamlib  # noqa: E402

QUALITY = {"team": "quality", "type": "merge", "seat": "Quality", "mark": "🛡️", "of": ["testing", "bar-raiser"]}
PRODUCT_DESIGN = {"team": "product-design", "type": "merge", "seat": "Product & Design", "mark": "🎨",
                  "of": ["product", "design"]}
DECISION_ROW = re.compile(r"^\| \*\*DEC-\d+\*\* \|.*$", re.M)


def split(team: str, mark: str) -> dict:
    return {"team": f"frontend-{team}", "type": "derive", "base": "seat-frontend", "seat": f"Frontend engineer ({team})",
            "mark": mark, "scope": f"the UI code under apps/{team}/"}


class Round2(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="agent-team-r2-")
        self.base = Path(self._tmp.name).resolve()
        (self.base / "home").mkdir()
        self.env = fx.isolated_env(self.base / "home", self.base)
        self.root = fx.build_lib(self.base / "repo", self.env)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ helpers
    def run_script(self, *args, ok: bool | None = True, script: str = "scaffold.py") -> subprocess.CompletedProcess:
        res = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True,
                             text=True, encoding="utf-8", env=self.env)
        if ok is True:
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        elif ok is False:
            self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        return res

    def scaffold(self, *args, ok: bool | None = True) -> subprocess.CompletedProcess:
        return self.run_script("--root", self.root, *args, ok=ok)

    def plan(self, data: dict, name: str = "plan.json", where: Path | None = None) -> Path:
        p = (where or self.root / "docs" / "team") / name
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {**data, "seats": [{"team": x} if isinstance(x, str) else x for x in data.get("seats", [])]}
        p.write_text(json.dumps({"project": "Tally", **data}, ensure_ascii=False), encoding="utf-8")
        return p

    def seat(self, seats: list, retire: list | None = None, *extra, ok: bool | None = True) -> subprocess.CompletedProcess:
        return self.scaffold("--plan", self.plan({"seats": seats, "retire": retire or []}), *extra, ok=ok)

    def teams(self) -> list[str]:
        return [r["team"] for r in teamlib.roster(self.root / "docs" / "TEAM.md")]

    def text(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    # ------------------------------------------------------------------ the retire list is settled first
    def test_a_refused_retire_does_not_let_a_conflicting_seat_in(self):
        self.seat(["ceo", "engineering", QUALITY])
        before = (self.text("docs/TEAM.md"), self.text("docs/DECISIONS.md"))
        res = self.scaffold("--add", "testing", "--retire", "quality", "--record", "give Testing its own seat", ok=False)
        self.assertIn("not retired: 🛡️ Quality", res.stderr)
        self.assertIn("is held by 🛡️ Quality", res.stderr)
        self.assertEqual((self.text("docs/TEAM.md"), self.text("docs/DECISIONS.md")), before)

    def test_a_refused_retire_does_not_free_its_mark(self):
        self.seat(["ceo", "engineering"])
        desktop = {"team": "desktop", "type": "derive", "base": "seat-mobile", "seat": "Desktop engineer",
                   "mark": "🧭", "scope": "the desktop app"}
        res = self.seat([desktop], ["ceo"], ok=False)
        self.assertIn("the mark 🧭 is already", res.stderr)
        self.assertNotIn("desktop", self.teams())

    def test_every_split_must_be_retired_before_the_frontend_engineer_returns(self):
        self.seat(["ceo", "engineering", split("admin", "💻"), split("web", "🪟")])
        for one in ("frontend-admin", "frontend-web"):
            res = self.seat(["frontend"], [one], ok=False)
            self.assertIn("covered by its split seats", res.stderr)
        self.seat(["frontend"], ["frontend-admin", "frontend-web"])
        self.assertIn("frontend", self.teams())
        self.assertFalse({"frontend-admin", "frontend-web"} & set(self.teams()))

    def test_a_team_named_twice_to_retire_is_retired_once(self):
        self.seat(["ceo", "engineering", "docs"])
        out = self.seat([], ["docs", "docs"]).stdout
        self.assertEqual(out.count("retired: 📚"), 1, out)
        self.assertNotIn("not retired", out)

    def test_a_team_named_to_seat_and_to_retire_is_refused(self):
        self.seat(["ceo", "engineering"])
        res = self.seat(["docs"], ["docs"], ok=False)
        self.assertIn("named to seat and to retire", res.stderr)
        self.assertNotIn("docs", self.teams())

    # ------------------------------------------------------------------ merged rulebooks
    def test_a_merged_rulebook_names_only_its_own_paths(self):
        text = seatgen.compose_merge("quality", "Quality", "🛡️", ["testing", "bar-raiser"])
        body = text.split("-->", 1)[1]  # past the provenance comment, which names the member skills
        for member in ("testing", "bar-raiser"):
            for ref in (f"docs/team/{member}.md", f"scratchpad/team/inbox/{member}.md",
                        f"scratchpad/team/runs/{member}/", f"{member}-worker", f"seat-{member}"):
                self.assertNotIn(ref, body)
        self.assertIn("scratchpad/team/inbox/quality.md", body)
        self.assertIn("quality-worker", body)

    # ------------------------------------------------------------------ roster cells
    def test_a_pipe_in_a_register_stays_in_its_cell(self):
        self.seat(["ceo", "engineering"])
        desktop = {"team": "desktop", "type": "derive", "base": "seat-mobile", "seat": "Desktop engineer",
                   "mark": "🖱️", "register": "apps/desktop | installers", "scope": "the desktop app"}
        res = self.seat([desktop])
        self.assertNotIn("does not parse", res.stdout + res.stderr)
        self.assertIn("desktop", self.teams())
        out = self.seat([desktop]).stdout
        self.assertIn("roster: added 0 seat(s)", out)
        self.assertEqual(self.teams().count("desktop"), 1)

    # ------------------------------------------------------------------ coverage of the Frontend engineer
    def test_the_extension_engineer_is_not_a_frontend_split(self):
        lock = {"seat-extension": {"origin": "derive:seat-frontend"}, "seat-frontend-web": {"origin": "derive:seat-frontend"}}
        self.assertFalse(teamlib.covers_frontend("extension", "seat-extension", lock))
        self.assertTrue(teamlib.covers_frontend("frontend-web", "seat-frontend-web", lock))
        ext = dict(teamlib.DERIVED_ROLES["extension"], type="derive")
        self.seat(["ceo", "engineering", ext])
        self.assertNotIn("frontend", teamlib.coverage(self.root))
        self.scaffold("--add", "frontend")
        self.assertIn("frontend", self.teams())

    # ------------------------------------------------------------------ owner registers
    def test_a_team_with_no_chief_of_staff_gets_the_owner_registers_kept_by_the_ceo(self):
        self.seat(["ceo", "engineering"])
        for f in ("owner-questions.md", "tracker.md"):
            text = self.text(f"docs/team/{f}")
            self.assertIn("Kept by the 🧭 CEO", text, f)
        self.text("docs/team/owner-questions.md")
        p = self.root / "docs" / "team" / "owner-questions.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n- a question kept\n", encoding="utf-8")
        self.scaffold("--add", "docs", "--force")
        self.assertIn("a question kept", self.text("docs/team/owner-questions.md"))

    def test_a_chief_of_staff_keeps_the_owner_registers(self):
        self.seat(["ceo", "engineering", "chief-of-staff"])
        self.assertIn("Kept by the 🛎️ Chief of Staff", self.text("docs/team/owner-questions.md"))

    # ------------------------------------------------------------------ unparsed roster rows
    def test_an_unparsed_roster_row_stops_every_change(self):
        self.seat(["ceo", "engineering", "user"])
        doc = self.root / "docs" / "TEAM.md"
        doc.write_text(doc.read_text(encoding="utf-8").replace("| 👤 | User |", "| 👤 | User | stray |"),
                       encoding="utf-8")
        before = doc.read_text(encoding="utf-8")
        for args in (("--retire", "user"), ("--add", "user"), ("--add", "docs")):
            res = self.scaffold(*args, ok=False)
            self.assertIn("not 7", res.stderr)
        self.assertEqual(doc.read_text(encoding="utf-8"), before)
        self.assertIn("not synced", self.scaffold("--sync").stdout)
        worker = self.root / ".claude" / "agents" / "user-worker.md"
        self.assertTrue(worker.is_file())
        subprocess.run([sys.executable, str(self.root / "scripts" / "gen-team-agents.py")], cwd=self.root,
                       env=self.env, capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertTrue(worker.is_file(), "a worker whose row does not parse is kept until the row is fixed")

    # ------------------------------------------------------------------ the project's own folder
    def test_a_folder_the_project_already_had_keeps_its_files(self):
        notes = fx.put(self.root, ".claude/skills/seat-docs/NOTES.md", "Tally's own docs notes.\n")
        self.seat(["ceo", "engineering", "docs"])
        lock = teamlib.load_lock(self.root)
        self.assertEqual(lock["seat-docs"]["origin"], "project")
        self.assertTrue((notes.parent / "SKILL.md").is_file())
        self.scaffold("--sync")
        self.assertTrue(notes.is_file())
        self.scaffold("--retire", "docs")
        archived = list((self.root / "docs" / "team" / "retired").glob("seat-docs-*/NOTES.md"))
        self.assertEqual(len(archived), 1)

    # ------------------------------------------------------------------ briefs
    def test_force_never_overwrites_a_retired_brief(self):
        self.seat(["ceo", "engineering", PRODUCT_DESIGN])
        self.seat(["product", "design"], ["product-design"])
        p = self.root / "docs" / "team" / "product-design.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n- **Fact:** Tally's invoice PDF uses brand blue.\n",
                     encoding="utf-8")
        self.seat([PRODUCT_DESIGN], ["product", "design"], "--force")
        text = p.read_text(encoding="utf-8")
        self.assertIn("brand blue", text)
        self.assertFalse(text.startswith("> **Retired"))

    def test_a_remerged_brief_carries_facts_the_members_gained(self):
        self.seat(["ceo", "engineering", PRODUCT_DESIGN])
        self.seat(["product", "design"], ["product-design"])
        d = self.root / "docs" / "team" / "design.md"
        d.write_text(d.read_text(encoding="utf-8") + "\n- **Fact:** Tally's launch post goes out on a Monday.\n",
                     encoding="utf-8")
        self.seat([PRODUCT_DESIGN], ["product", "design"])
        self.assertIn("launch post goes out on a Monday", self.text("docs/team/product-design.md"))

    # ------------------------------------------------------------------ plans and decisions
    def test_an_empty_only_is_refused(self):
        self.seat(["ceo", "engineering"])
        plan = self.plan({"seats": [{"team": "docs"}], "retire": [], "proposals": [
            {"key": "add:docs", "action": "add", "title": "Add 📚 Docs writer", "signals": [],
             "seats": [{"team": "docs"}], "retire": []}]}, "reevaluation.json")
        for only in ("", ","):
            res = self.scaffold("--plan", plan, "--only", only, "--record", "yes", ok=False)
            self.assertIn("names no proposal", res.stderr)
        self.assertFalse((self.root / "docs" / "team" / "declined.json").exists())

    def test_a_plan_outside_the_project_is_cited_by_name(self):
        self.seat(["ceo", "engineering"])
        outside = self.plan({"seats": ["docs"], "retire": []}, "docs-plan.json", where=self.base / "elsewhere")
        self.scaffold("--plan", outside, "--record", "docs back")
        row = DECISION_ROW.findall(self.text("docs/DECISIONS.md"))[-1]
        self.assertIn("| docs-plan.json |", row)
        self.assertNotIn(str(self.base), row)

    def test_the_default_push_rule_asks_the_owner(self):
        self.seat(["ceo", "engineering"])
        self.assertIn("asks the owner before each push", self.text("docs/TEAM.md"))

    def test_only_the_first_heading_names_the_project(self):
        self.scaffold("--seats", "ceo,engineering", "--project", "Tally")
        (self.root / "docs" / "team" / "plan.json").unlink(missing_ok=True)
        doc = self.root / "docs" / "TEAM.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n## Notes from the whole team\n", encoding="utf-8")
        self.assertEqual(teamlib.project_name(self.root), "Tally")

    # ------------------------------------------------------------------ line endings
    def test_crlf_writes_do_not_make_sync_update_a_merged_rulebook(self):
        runner = self.base / "winrun.py"
        runner.write_text(
            "import pathlib, runpy, sys\n"
            "_orig = pathlib.Path.write_text\n"
            "def crlf(self, data, encoding=None, errors=None, newline=None):\n"
            "    return _orig(self, data.replace('\\n', '\\r\\n'), encoding=encoding, errors=errors)\n"
            "pathlib.Path.write_text = crlf\n"
            "sys.argv = sys.argv[1:]\n"
            "runpy.run_path(sys.argv[0], run_name='__main__')\n", encoding="utf-8")
        plan = self.plan({"seats": ["ceo", "engineering", PRODUCT_DESIGN], "retire": []})

        def win(*args):
            return subprocess.run([sys.executable, str(runner), str(SCRIPTS / "scaffold.py"), "--root",
                                   str(self.root), *map(str, args)], capture_output=True, text=True, encoding="utf-8", env=self.env)
        self.assertIn("composed", win("--plan", plan).stdout)
        out = win("--sync").stdout
        self.assertNotIn("updated: .claude/skills/seat-product-design", out)


if __name__ == "__main__":
    unittest.main()
