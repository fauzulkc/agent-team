#!/usr/bin/env python3
"""Measure the walkthrough's numbers on a Tally-shaped project, built fresh in a temporary folder.

    python3 tools/measure_tally.py            print what setup and a re-evaluation give Tally
    python3 tools/measure_tally.py --check    exit 1 when a number examples/walkthrough.md states has moved

The project: a React web app (apps/web) with a pricing page and product analytics, a Node API on
Express (apps/api) with Postgres, card payments, sign-in and an email service, a customers table with
an email column, a blog, a Dockerfile and a hosting config, tests and CI: 661 source files, eight
commits by four people, so the scan sizes it medium (past 600 source files).

The story it runs, as the walkthrough tells it:
  1. scan.py --save, plan.py (all three options), then plan.py --option recommended --out and
     scaffold.py --plan --record "<the owner's words>": the team's decision is DEC-2.
  2. The CEO records recurring invoices (DEC-3) and the owner turns it on (DEC-4), appended by hand.
  3. A month on: every seat's lock date moved before the window, a mobile app in apps/mobile/, three
     prefixed commits for every seat but Sales & Marketing (1), SEO & Publicity (1) and Social (0).
  4. reevaluate.py --out, then scaffold.py --plan docs/team/reevaluation.json --record "apply all".
WALKTHROUGH holds the figures the walkthrough states; --check compares the run against them.
Standard library only; needs git.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "team-setup" / "scripts"
sys.path.insert(0, str(ROOT / "tests"))
from repo_fixtures import git, isolated_env, put, put_json  # noqa: E402

CODE_FILES, PEOPLE, COMMITS = 661, 4, 8
ACTIVE = ("ceo", "chief-of-staff", "product", "engineering", "frontend", "testing", "platform", "research",
          "bar-raiser", "scope-trimmer", "design", "customer-success", "payments", "compliance", "user", "security")
WALKTHROUGH = {
    "size": "medium", "code_files": 661, "contributors": 4,
    "lean": 10, "recommended": 19, "full": 22, "full_adds": ["competition", "docs", "funding"],
    "lean_holds": 16, "chief_of_staff_why": "17 other seats", "setup_decision": "DEC-2", "workers": 25,
    "proposals": ["add:mobile", "merge:growth"], "apply_decision": "DEC-5", "after_apply_seats": 18,
}


def run(env: dict, *args: str, cwd: Path) -> str:
    res = subprocess.run([sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"failed: {' '.join(args)}\n{res.stderr or res.stdout}")
    return res.stdout


def build(root: Path, env: dict) -> None:
    put_json(root, "apps/web/package.json", {"name": "web", "dependencies": {
        "react": "18.3.1", "react-dom": "18.3.1", "@stripe/stripe-js": "3.4.0", "posthog-js": "1.136.0"},
        "devDependencies": {"vitest": "1.6.0"}})
    put_json(root, "apps/api/package.json", {"name": "api", "dependencies": {
        "express": "4.19.2", "pg": "8.11.5", "stripe": "15.8.0", "passport": "0.7.0", "nodemailer": "6.9.13"},
        "devDependencies": {"vitest": "1.6.0"}})
    put(root, "apps/api/migrations/001_customers.sql", "create table customers (id serial primary key, email text not null);\n")
    put(root, "apps/web/src/pages/pricing.tsx", "export default function Pricing() { return null }\n")
    put(root, "blog/recurring-invoices.md", "# Recurring invoices\n")
    put(root, "Dockerfile", "FROM scratch\n")
    put(root, "fly.toml", 'app = "tally"\n')
    put(root, ".github/workflows/ci.yml", "name: ci\non: [push]\njobs: {}\n")
    tests = 12
    for i in range(tests):
        put(root, f"apps/api/src/m{i}.test.ts", "test('x', () => {})\n")
    for i in range(CODE_FILES - tests - 1):
        put(root, f"apps/web/src/c{i}.tsx" if i % 2 else f"apps/api/src/m{i}.ts", f"export const x{i} = {i}\n")
    git(root, "init", "-q", env=env)
    git(root, "add", "-A", env=env)
    for i in range(COMMITS):
        who = i % PEOPLE
        git(root, "-c", f"user.email=dev{who}@example.invalid", "-c", f"user.name=Dev {who}", "commit", "-q",
            "--allow-empty", "-m", "initial" if i == 0 else f"work {i}", env=env)


def commit(root: Path, env: dict, subject: str, add: bool = False) -> None:
    if add:
        git(root, "add", "-A", env=env)
    git(root, "-c", "user.email=dev1@example.invalid", "-c", "user.name=Dev 1", "commit", "-q", "--allow-empty",
        "-m", subject, env=env)


def measure() -> dict:
    out: dict = {}
    with tempfile.TemporaryDirectory(prefix="tally-measure-") as tmp:
        tmp = Path(tmp)
        env = isolated_env(tmp, tmp)
        root = tmp / "tally"
        root.mkdir()
        build(root, env)
        s = SCRIPTS
        scan = json.loads(run(env, str(s / "scan.py"), "--root", ".", "--save", cwd=root))
        out.update(size=None, code_files=scan["size"]["code_files"], contributors=scan["size"]["contributors"],
                   signals=sorted(scan["signals"]))
        opts = json.loads(run(env, str(s / "plan.py"), "--scan", "docs/team/scan.json", cwd=root))
        out["size"] = opts["size"]
        for o in ("lean", "recommended", "full"):
            out[o] = len(opts[o])
        out["recommended_seats"] = [x["team"] for x in opts["recommended"]]
        out["full_adds"] = sorted({x["team"] for x in opts["full"]} - set(out["recommended_seats"]))
        out["lean_holds"] = sum(len(x["of"]) if x["type"] == "merge" else 1 for x in opts["lean"])
        cos = next(x["why"] for x in opts["recommended"] if x["team"] == "chief-of-staff")
        out["chief_of_staff_why"] = cos.split(":")[0]
        run(env, str(s / "plan.py"), "--scan", "docs/team/scan.json", "--option", "recommended",
            "--out", "docs/team/plan.json", "--project", "Tally", cwd=root)
        said = run(env, str(s / "scaffold.py"), "--root", ".", "--plan", "docs/team/plan.json",
                   "--record", "recommended, and emailing customers is mine too", cwd=root)
        out["setup_decision"] = re.search(r"recorded: (DEC-\d+)", said).group(1)
        out["workers"] = len(list((root / ".claude" / "agents").glob("*.md")))
        # a month on
        decisions = root / "docs" / "DECISIONS.md"
        decisions.write_text(decisions.read_text(encoding="utf-8")
                             + "| **DEC-3** | Recurring invoices this milestone? | 9 support emails | ✅ (CEO) monthly and weekly only |\n"
                             + "| **DEC-4** | Turn recurring invoices on? | Bar Raiser PASS | ✅ the owner: \"turn it on\" |\n",
                             encoding="utf-8")
        lock_path = root / "docs" / "team" / "seat-skills.lock"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for entry in lock.values():
            entry["seated"] = "2026-01-01"
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        put_json(root, "apps/mobile/package.json", {"name": "mobile", "dependencies": {"react-native": "0.74.1", "expo": "51.0.8"}})
        put(root, "apps/mobile/App.tsx", "export default function App() { return null }\n")
        commit(root, env, "chore: the team's files; start apps/mobile", add=True)
        for team in ACTIVE:
            for i in range(3):
                commit(root, env, f"{team}: work {i}")
        commit(root, env, "sales: pricing case draft")
        commit(root, env, "seo: sitemap")
        run(env, str(s / "reevaluate.py"), "--root", ".", "--out", "docs/team/reevaluation.json", cwd=root)
        plan = json.loads((root / "docs" / "team" / "reevaluation.json").read_text(encoding="utf-8"))
        out["proposals"] = [p["key"] for p in plan["proposals"]]
        out["proposal_titles"] = [p["title"] for p in plan["proposals"]]
        said = run(env, str(s / "scaffold.py"), "--root", ".", "--plan", "docs/team/reevaluation.json",
                   "--record", "apply all", cwd=root)
        out["apply_decision"] = re.search(r"recorded: (DEC-\d+)", said).group(1)
        out["apply_row"] = decisions.read_text(encoding="utf-8").rstrip("\n").splitlines()[-1]
        team_doc = (root / "docs" / "TEAM.md").read_text(encoding="utf-8")
        out["after_apply_seats"] = len(re.findall(r"^\| \S+ \| [^|]+ \| `seat-", team_doc, re.M))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 when a walkthrough figure has moved")
    a = ap.parse_args()
    got = measure()
    if not a.check:
        print(json.dumps(got, indent=2, ensure_ascii=False))
        return 0
    moved = [f"{k}: the walkthrough says {v!r}, measured {got.get(k)!r}" for k, v in WALKTHROUGH.items() if got.get(k) != v]
    for m in moved:
        print(f"examples/walkthrough.md: {m}")
    if not moved:
        print("examples/walkthrough.md: every measured figure holds")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
