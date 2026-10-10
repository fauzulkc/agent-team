"""tools/bump_version.py: the version check, the refusals and the CHANGELOG move, on a copy of the repo's
version-bearing files."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bump_version", REPO / "tools" / "bump_version.py")
bv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bv)

FILES = (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "CHANGELOG.md", "CITATION.cff")


class BumpVersionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for f in FILES:
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / f, self.root / f)
        self.current = json.loads((self.root / FILES[0]).read_text(encoding="utf-8"))["version"]

    def unreleased(self, body: str) -> None:
        log = self.root / "CHANGELOG.md"
        text = log.read_text(encoding="utf-8")
        start = text.index("## Unreleased")
        end = text.index("\n## ", start + 1)
        log.write_text(text[:start] + "## Unreleased\n\n" + body + "\n" + text[end:], encoding="utf-8")

    def next_patch(self) -> str:
        major, minor, patch = bv.parse(self.current)
        return f"{major}.{minor}.{patch + 1}"

    def test_the_repo_agrees_on_its_version(self):
        self.assertEqual(bv.problems(self.root), [])

    def test_a_bump_moves_unreleased_and_sets_every_version(self):
        self.unreleased("Nothing yet.\n- A fix a user can see.")
        new = self.next_patch()
        bv.bump(self.root, new, "2030-01-02")
        text = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {new} — 2030-01-02\n\n- A fix a user can see.", text)
        self.assertIn("## Unreleased\n\nNothing yet.", text)
        self.assertEqual(json.loads((self.root / FILES[0]).read_text(encoding="utf-8"))["version"], new)
        self.assertEqual(json.loads((self.root / FILES[1]).read_text(encoding="utf-8"))["plugins"][0]["version"], new)
        self.assertIn(f"version: {new}", (self.root / "CITATION.cff").read_text(encoding="utf-8"))
        self.assertEqual(bv.problems(self.root), [])

    def test_refusals_write_nothing(self):
        before = {f: (self.root / f).read_bytes() for f in FILES}
        cases = [("Nothing yet.", self.next_patch(), "2030-01-02"),          # empty Unreleased
                 ("### Added", self.next_patch(), "2030-01-02"),             # headings alone are not notes
                 ("- an entry", self.current, "2030-01-02"),                 # not greater
                 ("- an entry", "1.x", "2030-01-02"),                        # not a version
                 ("- an entry", self.next_patch(), "02/01/2030")]            # not a date
        for body, version, date in cases:
            with self.subTest(body=body, version=version, date=date):
                self.unreleased(body)
                staged = (self.root / "CHANGELOG.md").read_bytes()
                with self.assertRaises(bv.Refusal):
                    bv.bump(self.root, version, date)
                self.assertEqual((self.root / "CHANGELOG.md").read_bytes(), staged)
                for f in FILES[:2]:
                    self.assertEqual((self.root / f).read_bytes(), before[f])

    def test_a_disagreeing_version_is_a_problem(self):
        mp = self.root / FILES[1]
        data = json.loads(mp.read_text(encoding="utf-8"))
        data["plugins"][0]["version"] = "0.0.1"
        mp.write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(bv.problems(self.root))


if __name__ == "__main__":
    unittest.main()
