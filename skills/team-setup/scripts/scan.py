#!/usr/bin/env python3
"""Quick repo scan: the signals team-setup and team-reevaluate plan seats from.

    scan.py --root <project>             print the signals as JSON
    scan.py --root <project> --save      also write docs/team/scan.json (the baseline re-evaluation diffs against)

Reads file names, manifests and dependency lists only (no file bodies beyond manifests, nothing
sent anywhere). Each signal carries the evidence that raised it, so a proposal can say why.
Standard library only; finishes in seconds on large repos (it skips vendored and build folders).
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "out", ".next", ".venv", "venv",
             "__pycache__", "target", ".cache", "coverage", ".turbo", ".claude", "scratchpad", "Pods"}
MAX_FILES = 60000

# dependency name patterns (lower-case substrings or regexes) → signal
DEP_SIGNALS = {
    "ui_web": [r"^react$", r"^react-dom$", r"^vue$", r"^svelte", r"^next$", r"^nuxt", r"^@angular/core$",
               r"^solid-js$", r"^astro$", r"^@remix-run/", r"^preact$", r"^htmx", r"^flask$", r"^django$"],
    "mobile": [r"^react-native$", r"^expo$", r"^@capacitor/", r"^@ionic/", r"^flutter$", r"^nativescript"],
    "api": [r"^express$", r"^fastify$", r"^koa$", r"^@nestjs/", r"^hono$", r"^fastapi$", r"^flask$",
            r"^django$", r"^gin-gonic", r"^echo$", r"^actix-web$", r"^axum$", r"^rails$", r"^sinatra$",
            r"^graphql$", r"^@apollo/server$", r"^trpc", r"^grpc"],
    "db": [r"^prisma$", r"^@prisma/client$", r"^drizzle-orm$", r"^typeorm$", r"^sequelize$", r"^mongoose$",
           r"^pg$", r"^mysql2?$", r"^sqlalchemy$", r"^psycopg", r"^redis$", r"^ioredis$", r"^knex$",
           r"^gorm", r"^diesel$", r"^sqlx$", r"^activerecord$", r"^duckdb$", r"^sqlite3?$"],
    "ml": [r"^torch$", r"^tensorflow", r"^keras$", r"^scikit-learn$", r"^sklearn$", r"^xgboost$", r"^lightgbm$",
           r"^transformers$", r"^jax$", r"^@tensorflow/", r"^onnx", r"^mlflow$", r"^wandb$", r"^openai$",
           r"^anthropic$", r"^@anthropic-ai/sdk$", r"^langchain", r"^llama", r"^sentence-transformers$"],
    "data_pipelines": [r"^dbt", r"^apache-airflow$", r"^airflow$", r"^dagster", r"^prefect$", r"^pyspark$",
                       r"^luigi$", r"^great-expectations$", r"^polars$", r"^pandas$", r"^pyarrow$"],
    "payments": [r"^stripe$", r"^@stripe/", r"^braintree$", r"^@lemonsqueezy/",
                 r"^chargebee", r"^recurly$", r"^razorpay$", r"^adyen", r"^paypal"],
    "auth": [r"^next-auth$", r"^@auth/", r"^passport", r"^@clerk/", r"^@supabase/auth", r"^firebase-admin$",
             r"^firebase$", r"^lucia$", r"^jsonwebtoken$", r"^bcrypt", r"^argon2", r"^devise$", r"^authlib$",
             r"^django-allauth$", r"^@auth0/", r"^oauthlib$"],
    "analytics": [r"posthog", r"^mixpanel", r"^@segment/", r"^amplitude", r"^@vercel/analytics$", r"plausible",
                  r"^react-ga", r"^@google-analytics/"],
    "i18n": [r"^i18next$", r"^react-i18next$", r"^next-intl$", r"^vue-i18n$", r"^@formatjs/", r"^react-intl$",
             r"^babel$", r"^lingui", r"^gettext"],
    "email": [r"^nodemailer$", r"^resend$", r"^@sendgrid/", r"^postmark$", r"^mailgun", r"^@react-email/"],
    "game": [r"^phaser$", r"^pixi\.js$", r"^babylonjs$", r"^bevy$", r"^pygame$", r"^godot",
             r"^@dimforge/", r"^kaboom$", r"^excalibur$"],
    "video": [r"^remotion$", r"^@remotion/", r"^ffmpeg", r"^fluent-ffmpeg$", r"^moviepy$"],
    "desktop": [r"^electron$", r"^@tauri-apps/", r"^tauri$", r"^wails", r"^@neutralinojs/", r"^pyside6?$", r"^pyqt[56]?$"],
    "blockchain": [r"^hardhat$", r"^ethers$", r"^viem$", r"^web3$", r"^@solana/", r"^foundry", r"^anchor-lang$", r"^wagmi$"],
    "docs_site": [r"^@docusaurus/", r"^vitepress$", r"^mkdocs", r"^nextra", r"^sphinx$", r"^@mintlify/", r"^typedoc$"],
}
# path globs / names → signal
PATH_SIGNALS = {
    "mobile": ["ios/", "android/", "pubspec.yaml", "app.json:expo", "*.xcodeproj", "Podfile", "build.gradle"],
    "deploy": ["Dockerfile", "docker-compose.yml", "compose.yml", "fly.toml", "vercel.json", "netlify.toml",
               "render.yaml", "wrangler.toml", "Procfile", "serverless.yml", "*.tf", "k8s/", "helm/",
               "app.yaml", ".platform.app.yaml", "railway.json"],
    "ci": [".github/workflows/", ".gitlab-ci.yml", ".circleci/", "azure-pipelines.yml", "Jenkinsfile",
           ".buildkite/"],
    "tests": ["tests/", "test/", "__tests__/", "spec/", "*_test.go", "*.test.ts", "*.test.js", "*.spec.ts",
              "test_*.py", "*_test.py", "*_spec.rb", "*.test.tsx", "cypress/", "playwright.config.*",
              "vitest.config.*", "jest.config.*", "pytest.ini", "conftest.py"],
    "ml": ["*.ipynb", "notebooks/", "training/", "evals/", "*.onnx", "*.pt", "*.safetensors", "*.gguf",
           "*.tflite", "*.task", "*.ckpt"],
    "data_pipelines": ["dbt_project.yml", "dags/", "pipelines/", "etl/", "warehouse/"],
    "docs_site": ["mkdocs.yml", "docusaurus.config.*", ".vitepress/", "conf.py:sphinx", "mint.json",
                  "book.toml", "antora.yml"],
    "i18n": ["locales/", "locale/", "i18n/", "translations/", "*.po", "messages/*.json"],
    "game": ["*.unity", "ProjectSettings/", "project.godot", "*.uproject", "Assets/"],
    "content": ["posts/", "blog/", "content/", "videos/", "_posts/", "newsletter/"],
    "landing": ["landing/", "site/", "www/", "marketing/", "pages/pricing*", "app/pricing*", "src/pages/pricing*", "pricing.*"],
    "migrations": ["migrations/", "db/migrate/", "prisma/schema.prisma", "alembic/", "drizzle/"],
    "security_policy": ["SECURITY.md", ".github/SECURITY.md"],
    "hardware": ["platformio.ini", "*.ino", "*.kicad_pcb", "*.kicad_sch", "sdkconfig", "*.dts", "Kconfig"],
    "blockchain": ["*.sol", "hardhat.config.*", "foundry.toml", "Anchor.toml"],
    "extension": ["manifest.json:manifest_version"],
    "oss": ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", ".github/ISSUE_TEMPLATE/", ".github/PULL_REQUEST_TEMPLATE.md"],
    "licence_data": ["datasets/", "data/raw/", "data/external/", "LICENSES/", "THIRD_PARTY_NOTICES*",
                     "NOTICE", "ATTRIBUTION*"],
}
CONTENT_EXTS = (".md", ".mdx", ".markdown", ".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".gif")
PERSONAL_DATA_WORDS = re.compile(r"\b(email|phone|address|date_of_birth|dob|password|ssn|passport|"
                                 r"first_name|last_name|full_name|ip_address)\b", re.I)


def walk(root: Path) -> list[str]:
    """Repo-relative paths (posix strings), skipping vendored, build and hidden folders."""
    out: list[str] = []
    keep_hidden = {".github", ".circleci", ".buildkite", ".vitepress"}
    stack = [""]
    while stack and len(out) < MAX_FILES:
        rel_dir = stack.pop()
        try:
            it = os.scandir(root / rel_dir if rel_dir else root)
        except OSError:
            continue
        with it:
            for e in it:
                rel = f"{rel_dir}/{e.name}" if rel_dir else e.name
                try:
                    if e.is_dir(follow_symlinks=False):
                        if e.name not in SKIP_DIRS and (not e.name.startswith(".") or e.name in keep_hidden):
                            stack.append(rel)
                    elif e.is_file(follow_symlinks=False):
                        out.append(rel)
                except OSError:
                    continue
    return out


MANIFESTS = {"package.json", "pyproject.toml", "go.mod", "Cargo.toml", "Gemfile", "pubspec.yaml", "composer.json"}


def deps_from_manifests(root: Path, rels: list[str]) -> tuple[set[str], list[str]]:
    deps: set[str] = set()
    found: list[str] = []
    for rel in rels:
        name = rel.rsplit("/", 1)[-1]
        if name not in MANIFESTS and not (name.startswith("requirements") and name.endswith(".txt")):
            continue
        f = root / rel
        try:
            if name == "package.json":
                j = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                for k in ("dependencies", "devDependencies", "peerDependencies"):
                    deps |= {d.lower() for d in (j.get(k) or {})}
                found.append(rel)
            elif name in ("requirements.txt", "requirements-dev.txt") or (name.startswith("requirements") and name.endswith(".txt")):
                for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = re.match(r"\s*([A-Za-z0-9_.\-\[\]]+)", line)
                    if m and not line.strip().startswith("#"):
                        deps.add(re.sub(r"\[.*\]", "", m.group(1)).lower())
                found.append(rel)
            elif name == "pyproject.toml":
                t = f.read_text(encoding="utf-8", errors="replace")
                deps |= {m.lower() for m in re.findall(r'^\s*"?([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*[<>=~!^ ;,"]', t, re.M)}
                deps |= {m.lower() for m in re.findall(r'"([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(?:[<>=~!^][^"]*)?"', t)}
                found.append(rel)
            elif name == "go.mod":
                for m in re.findall(r"^\s*(?:require\s+)?([a-z0-9.\-]+/[^\s]+)\s+v", f.read_text(encoding="utf-8", errors="replace"), re.M):
                    deps.add(m.lower()); deps.add(m.lower().rsplit("/", 1)[-1])
                found.append(rel)
            elif name == "Cargo.toml":
                t = f.read_text(encoding="utf-8", errors="replace")
                deps |= {m.lower() for m in re.findall(r"^([a-z0-9_\-]+)\s*=", t, re.M)}
                found.append(rel)
            elif name == "Gemfile":
                deps |= {m.lower() for m in re.findall(r"^\s*gem\s+['\"]([^'\"]+)", f.read_text(encoding="utf-8", errors="replace"), re.M)}
                found.append(rel)
            elif name == "pubspec.yaml":
                deps.add("flutter"); found.append(rel)
            elif name == "composer.json":
                j = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                deps |= {d.lower().split("/")[-1] for d in (j.get("require") or {})}
                found.append(rel)
        except (OSError, ValueError):
            continue
    return deps, found


class PathMatcher:
    """Classifies PATH_SIGNALS once so each file costs a few set lookups, not dozens of regex scans."""

    def __init__(self) -> None:
        self.exact: dict[str, list[tuple[str, str | None]]] = {}      # basename -> [(signal, needle)]
        self.dirs: dict[str, list[str]] = {}                            # single folder name -> [signal]
        self.multi_dirs: list[tuple[str, str]] = []                    # "a/b/" -> signal
        name_globs: list[tuple[str, str]] = []
        self.rel_globs: list[tuple[re.Pattern, str]] = []
        for sig, pats in PATH_SIGNALS.items():
            for pat in pats:
                needle = None
                if ":" in pat and not pat.startswith("*"):
                    pat, needle = pat.split(":", 1)
                if pat.endswith("/"):
                    body = pat.rstrip("/")
                    if "/" in body:
                        self.multi_dirs.append((pat, sig))
                    else:
                        self.dirs.setdefault(body, []).append(sig)
                elif "/" in pat:
                    self.rel_globs.append((re.compile(r"(^|/)" + fnmatch.translate(pat)), sig))
                elif any(c in pat for c in "*?["):
                    name_globs.append((pat, sig))
                else:
                    self.exact.setdefault(pat, []).append((sig, needle))
        self.name_globs = [(re.compile(fnmatch.translate(p)), sig) for p, sig in name_globs]
        # a cheap prefilter over basenames for the glob patterns: their literal suffixes
        self.glob_suffixes = tuple({p.lstrip("*").split("*")[-1] for p, _ in name_globs if p.lstrip("*")})

    def signals_for(self, rel: str, name: str) -> list[tuple[str, str | None]]:
        out: list[tuple[str, str | None]] = list(self.exact.get(name, ()))
        parts = rel.split("/")[:-1]
        for part in parts:
            for sig in self.dirs.get(part, ()):
                out.append((sig, None))
        if parts:
            for pat, sig in self.multi_dirs:
                if rel.startswith(pat) or f"/{pat}" in rel:
                    out.append((sig, None))
        if name.endswith(self.glob_suffixes) or any(c in name for c in "._"):
            for rx, sig in self.name_globs:
                if rx.match(name):
                    out.append((sig, None))
        for rx, sig in self.rel_globs:
            if rx.search(rel):
                out.append((sig, None))
        return out


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def scan(root: Path) -> dict:
    paths = walk(root)
    rels = [(r, r.rsplit("/", 1)[-1]) for r in paths]
    deps, manifests = deps_from_manifests(root, paths)
    signals: dict[str, list[str]] = {}

    def hit(sig: str, evidence: str) -> None:
        lst = signals.setdefault(sig, [])
        if evidence not in lst and len(lst) < 5:
            lst.append(evidence)

    for sig, pats in DEP_SIGNALS.items():
        for d in sorted(deps):
            if any(re.search(p, d) for p in pats):
                hit(sig, f"dependency {d}")
    matcher = PathMatcher()
    for rel, name in rels:
        for sig, needle in matcher.signals_for(rel, name):
            if len(signals.get(sig, ())) >= 5:
                continue
            if sig == "content" and not name.lower().endswith(CONTENT_EXTS):
                continue
            if needle:
                try:
                    if needle not in (root / rel).read_text(encoding="utf-8", errors="replace")[:20000]:
                        continue
                except OSError:
                    continue
            hit(sig, rel)
    # personal data: column / field names in schema-ish files
    for rel, name in rels:
        if re.search(r"(schema\.prisma$|(^|/)models?\.py$|(^|/)schema\.(sql|rb|ts)$|(^|/)(db/)?migrations?/[^/]+\.(sql|py|rb|ts|js)$)", rel) \
                and not re.search(r"(^|/)(data|vendor|third_party|share)/", rel):
            try:
                if PERSONAL_DATA_WORDS.search((root / rel).read_text(encoding="utf-8", errors="replace")[:200000]):
                    hit("personal_data", rel)
            except OSError:
                pass
    code_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".rb", ".java", ".kt", ".swift", ".dart",
                 ".cs", ".cpp", ".c", ".php", ".vue", ".svelte", ".scala", ".ex", ".exs", ".gd"}
    code_files = [r for r, n in rels if Path(n).suffix in code_exts]
    if code_files:
        hit("code", f"{len(code_files)} source files")
    licence = next((r for r, n in rels if n.upper().startswith("LICENSE") or n.upper().startswith("LICENCE")), None)
    if licence and "oss" in signals:
        hit("oss", licence)
    if any(m.endswith("package.json") for m in manifests[1:]) or (root / "pnpm-workspace.yaml").exists() or (root / "turbo.json").exists():
        hit("monorepo", "several package manifests" if len(manifests) > 1 else "workspace config")

    authors = {a for a in git(root, "log", "--format=%ae", "-n", "2000").split() if a}
    commits = git(root, "rev-list", "--count", "HEAD").strip()
    first = git(root, "log", "--reverse", "--format=%as", "-n", "1").strip()
    return {
        "scanned": datetime.date.today().isoformat(),
        "root": root.name,
        "size": {"files": len(paths), "code_files": len(code_files), "manifests": manifests[:10],
                 "contributors": len(authors), "commits": int(commits) if commits.isdigit() else 0,
                 "first_commit": first or None},
        "signals": dict(sorted(signals.items())),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()
    root = a.root.resolve()
    result = scan(root)
    text = json.dumps(result, indent=2)
    if a.save:
        out = root / "docs" / "team" / "scan.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
