"""Fixture repos for the dynamic-seat tests, built on disk in a temporary folder.

Three invented projects, all about the example app "Tally" (invoicing for freelancers):
  lib        a tiny open-source library
  saas       a tiny web product that takes money and stores customer emails
  monorepo   a small monorepo: two web UI apps, a mobile app, a model service, a warehouse,
             locale files, firmware, CI and a container
plus `three_d`, a folder (never a git repo) with a 3D rendering library and no game.
Standard library only; git runs with a fixed identity and no user or system config.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

GIT_IDENTITY = ["-c", "user.email=tests@example.invalid", "-c", "user.name=Tally Tests",
                "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def isolated_env(home: Path, ceiling: Path) -> dict[str, str]:
    """An environment for the scripts: no user git config, no global skills, git never climbs above `ceiling`."""
    env = dict(os.environ)
    env.update({"HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CEILING_DIRECTORIES": str(ceiling), "GIT_TERMINAL_PROMPT": "0",
                "PYTHONDONTWRITEBYTECODE": "1"})
    env.pop("AGENT_TEAM_LEAK_WORDS", None)
    return env


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    res = subprocess.run(["git", *GIT_IDENTITY, "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8",
                         env=env, check=True)
    return res.stdout


def put(root: Path, rel: str, text: str = "") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def put_json(root: Path, rel: str, obj: dict) -> Path:
    return put(root, rel, json.dumps(obj, indent=2) + "\n")


def commit_all(root: Path, message: str, env: dict[str, str] | None = None) -> None:
    if not (root / ".git").is_dir():
        git(root, "init", "-q", env=env)
    git(root, "add", "-A", env=env)
    git(root, "commit", "-q", "--allow-empty", "-m", message, env=env)


def empty_commits(root: Path, subjects: list[str], env: dict[str, str] | None = None) -> None:
    for s in subjects:
        git(root, "commit", "-q", "--allow-empty", "-m", s, env=env)


CI_YML = "name: ci\non: [push]\njobs: {}\n"


def build_lib(root: Path, env: dict[str, str] | None = None) -> Path:
    """(a) A tiny open-source library: pyproject with pytest, tests/, LICENSE, CONTRIBUTING.md, CI."""
    put(root, "pyproject.toml", '[project]\nname = "tally-totals"\nversion = "0.1.0"\ndependencies = []\n\n'
                                '[project.optional-dependencies]\ntest = ["pytest>=8.0"]\n')
    put(root, "src/tally_totals/__init__.py", "from .core import total\n")
    put(root, "src/tally_totals/core.py", "def total(lines):\n    return sum(q * p for q, p in lines)\n")
    put(root, "tests/test_core.py", "from tally_totals import total\n\n\ndef test_total():\n"
                                    "    assert total([(2, 5)]) == 10\n")
    put(root, "LICENSE", "Permissive licence text.\n")
    put(root, "CONTRIBUTING.md", "# Contributing\n\nOpen an issue first.\n")
    put(root, "README.md", "# tally-totals\n\nInvoice totals for freelancers.\n")
    put(root, ".github/workflows/ci.yml", CI_YML)
    commit_all(root, "initial", env)
    return root


def build_saas(root: Path, env: dict[str, str] | None = None) -> Path:
    """(b) A tiny web product: Next with payments, auth, email, analytics, a pricing page, a blog, deploy files."""
    put_json(root, "package.json", {
        "name": "tally", "private": True,
        "dependencies": {"next": "14.2.3", "react": "18.3.1", "stripe": "15.8.0", "@prisma/client": "5.14.0",
                         "next-auth": "4.24.7", "resend": "3.2.0", "posthog-js": "1.136.0"},
        "devDependencies": {"vitest": "1.6.0"}})
    put(root, "prisma/schema.prisma",
        "model Customer {\n  id    String @id\n  email String @unique\n  name  String?\n}\n\n"
        "model Invoice {\n  id          String @id\n  amountCents Int\n  customerId  String\n}\n")
    put(root, "app/page.tsx", "export default function Home() { return <main>Tally</main> }\n")
    put(root, "app/pricing/page.tsx", "export default function Pricing() { return <main>Plans</main> }\n")
    put(root, "app/pricing/page.test.tsx", "import { test } from 'vitest'\ntest('renders', () => {})\n")
    put(root, "app/api/checkout/route.ts", "export async function POST() { return new Response('ok') }\n")
    put(root, "blog/launch.md", "# Tally is live\n\nInvoices in a minute.\n")
    put(root, "Dockerfile", "FROM scratch\nCOPY . /app\n")
    put(root, "fly.toml", 'app = "tally"\n')
    put(root, "README.md", "# Tally\n\nInvoicing for freelancers.\n")
    commit_all(root, "initial", env)
    return root


def build_monorepo(root: Path, env: dict[str, str] | None = None) -> Path:
    """(c) A small monorepo: apps/web and apps/admin (web UI), apps/mobile (react-native + expo),
    services/ml (torch), a dbt warehouse, locale files, firmware, 40 components with tests, CI, Dockerfile."""
    put_json(root, "package.json", {"name": "tally-mono", "private": True, "workspaces": ["apps/*"],
                                    "devDependencies": {"turbo": "2.0.4"}})
    put_json(root, "apps/web/package.json", {"name": "web", "dependencies": {"react": "18.3.1", "react-dom": "18.3.1"},
                                             "devDependencies": {"vitest": "1.6.0"}})
    put_json(root, "apps/admin/package.json", {"name": "admin", "dependencies": {"react-dom": "18.3.1"}})
    # a cross-platform app carries react-dom for its web build; it is still the mobile app, not a web UI app
    put_json(root, "apps/mobile/package.json", {"name": "mobile", "dependencies": {
        "react": "18.2.0", "react-dom": "18.2.0", "react-native": "0.74.1", "react-native-web": "0.19.12",
        "expo": "51.0.8"}})
    put(root, "apps/mobile/App.tsx", "export default function App() { return null }\n")
    for i in range(20):
        put(root, f"apps/web/src/components/Widget{i}.tsx", f"export const Widget{i} = () => <div>{i}</div>\n")
        put(root, f"apps/web/src/components/Widget{i}.test.tsx", f"import {{ test }} from 'vitest'\ntest('w{i}', () => {{}})\n")
        put(root, f"apps/admin/src/components/Panel{i}.tsx", f"export const Panel{i} = () => <div>{i}</div>\n")
        put(root, f"apps/admin/src/components/Panel{i}.test.tsx", f"import {{ test }} from 'vitest'\ntest('p{i}', () => {{}})\n")
    put(root, "services/ml/pyproject.toml", '[project]\nname = "tally-ml"\nversion = "0.1.0"\n'
                                            'dependencies = ["torch>=2.3", "numpy>=1.26"]\n')
    put(root, "services/ml/train.py", "import torch\n\n\ndef train():\n    return torch.zeros(1)\n")
    put(root, "warehouse/dbt_project.yml", "name: tally\nversion: '1.0.0'\nprofile: tally\n")
    put(root, "warehouse/models/invoices.sql", "select * from raw_invoices\n")
    put_json(root, "locales/fr/common.json", {"invoice": "facture"})
    put(root, "firmware/platformio.ini", "[env:receipt-printer]\nplatform = native\n")
    put(root, "firmware/src/main.cpp", "void setup() {}\nvoid loop() {}\n")
    put(root, ".github/workflows/ci.yml", CI_YML)
    put(root, "Dockerfile", "FROM scratch\nCOPY . /app\n")
    put(root, "README.md", "# Tally monorepo\n")
    commit_all(root, "initial", env)
    return root


def build_three_d(root: Path) -> Path:
    """A web page with a 3D rendering library and model assets, and no game; never a git repo."""
    put_json(root, "package.json", {"name": "tally-3d-receipt", "dependencies": {
        "three": "0.165.0", "@react-three/fiber": "8.16.6", "@react-three/drei": "9.105.6",
        "react": "18.3.1", "react-dom": "18.3.1"}})
    put(root, "src/Receipt3D.tsx", "export const Receipt3D = () => null\n")
    put(root, "public/assets/receipt.glb", "glTF")
    return root
