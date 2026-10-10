#!/usr/bin/env python3
"""Quick repo scan: the signals team-setup and team-reevaluate plan seats from.

    scan.py --root <project>             print the signals as JSON
    scan.py --root <project> --save      also write docs/team/scan.json (the baseline re-evaluation diffs against)

Reads file names, manifests and dependency lists only (no file bodies beyond manifests, nothing
sent anywhere). Each signal carries the evidence that raised it, so a proposal can say why.

What it leaves out: vendored, build and hidden folders, and the team's own files (docs/TEAM.md,
docs/DECISIONS.md, docs/team/, scripts/gen-team-agents.py), so seating a team changes no signal.
Dependencies come from the dependency lists only: package.json's dependency maps, requirements*.txt,
pyproject.toml's [project] dependencies and optional-dependencies, [dependency-groups] and Poetry's
dependency tables (read with tomllib on Python 3.11+, a section-aware reader before that), go.mod,
Cargo.toml, Gemfile, composer.json. `mobile` needs Android or iOS evidence (an android/ or ios/
folder at the root, one folder down outside asset folders, or in an app under apps/ or packages/;
AndroidManifest.xml, a Gradle file applying a com.android plugin, pubspec.yaml, an Expo app.json, an
Xcode project's project.pbxproj or a Podfile); a plain Gradle build is not a mobile app, and icon
folders named android/ or ios/ under public/ or assets/ are not one either. `monorepo` means
package manifests in two or more different folders below the root, or a workspace config.
`size.ui_apps` lists up to 8 web UI app folders; `size.ui_app_count` is the full count.
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
if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252; seat marks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "out", ".next", ".venv", "venv",
             "__pycache__", "target", ".cache", "coverage", ".turbo", ".claude", "scratchpad", "Pods"}
MAX_FILES = 60000
# the team's own files: seating or changing a team must not move a signal
TEAM_FILES = {"docs/TEAM.md", "docs/DECISIONS.md", "scripts/gen-team-agents.py"}
TEAM_DIRS = {"docs/team"}

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
    "mobile": ["ios/", "android/", "pubspec.yaml", "app.json:expo", "project.pbxproj", "Podfile", "AndroidManifest.xml",
               "build.gradle:com.android", "build.gradle.kts:com.android"],
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
# folders that count for `mobile` only where a mobile project keeps them, never under an asset folder
MOBILE_DIRS = {"ios", "android"}
ASSET_DIRS = {"public", "static", "assets", "icons", "images", "img", "res", "resources", "www"}
CONTENT_EXTS = (".md", ".mdx", ".markdown", ".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".gif")
PERSONAL_DATA_WORDS = re.compile(r"\b(email|phone|address|date_of_birth|dob|password|ssn|passport|"
                                 r"first_name|last_name|full_name|ip_address)\b", re.I)


def walk(root: Path) -> list[str]:
    """Repo-relative paths (posix strings), skipping vendored, build and hidden folders and the team's own files."""
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
                        if e.name not in SKIP_DIRS and (not e.name.startswith(".") or e.name in keep_hidden) \
                                and rel not in TEAM_DIRS:
                            stack.append(rel)
                    elif e.is_file(follow_symlinks=False) and rel not in TEAM_FILES:
                        out.append(rel)
                except OSError:
                    continue
    return out


MANIFESTS = {"package.json", "pyproject.toml", "go.mod", "Cargo.toml", "Gemfile", "pubspec.yaml", "composer.json"}

try:
    import tomllib  # Python 3.11+
except ImportError:  # older Pythons use the section-aware reader below
    tomllib = None

REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)")
TOML_TABLE = re.compile(r"^\s*\[\[?\s*([^\[\]]+?)\s*\]\]?\s*(?:#.*)?$")
TOML_KEY = re.compile(r"""^\s*("[^"]+"|'[^']+'|[A-Za-z0-9_.\-]+)\s*=\s*(.*)$""")
POETRY_TABLE = re.compile(r"^tool\.poetry\.(dependencies|dev-dependencies|group\.[^.]+\.dependencies)$")
POETRY_SUBTABLE = re.compile(r"^tool\.poetry\.(?:dependencies|dev-dependencies|group\.[^.]+\.dependencies)\.([^.]+)$")


def requirement_names(reqs) -> set[str]:
    """Package names from PEP 508 requirement strings ("SQLAlchemy[asyncio]~=2.0" -> "sqlalchemy")."""
    out = set()
    for r in reqs:
        m = REQ_NAME.match(r) if isinstance(r, str) else None
        if m:
            out.add(m.group(1).lower())
    return out


def array_strings(text: str) -> tuple[list[str], bool]:
    """The strings of a TOML value and whether it closed within `text`. For an array (`text` opens with
    `[`): its top-level strings, strings inside its inline tables skipped. For an inline table (`{`): the
    top-level strings of each array directly inside it (`{ ml = ["torch"] }`). Comments run to their
    line's end; a backslash escapes the next character inside a basic ("...") string."""
    out: list[str] = []
    stack: list[str] = []
    want = ["["] if text.lstrip().startswith("[") else ["{", "["]
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if ch == '"' and text[j] == "\\" else 1
            if j >= n:
                return out, False
            if stack == want:
                out.append(text[i + 1:j])
            i = j
        elif ch == "#":
            end = text.find("\n", i)
            if end < 0:
                return out, False
            i = end
        elif ch in "[{":
            stack.append(ch)
        elif ch in "]}":
            if stack:
                stack.pop()
            if not stack:
                return out, True
        i += 1
    return out, False


def pyproject_deps_fallback(text: str) -> set[str]:
    """Section-aware reader for Pythons without tomllib: only the dependency tables count."""
    reqs: list[str] = []
    names: set[str] = set()
    table, pending = "", None  # pending: the text of an array that has not closed yet
    for line in text.splitlines():
        if pending is not None:
            pending += "\n" + line
            got, done = array_strings(pending)
            if done:
                reqs += got
                pending = None
            continue
        m = TOML_TABLE.match(line)
        if m:
            table = m.group(1).replace('"', "").replace("'", "")
            sub = POETRY_SUBTABLE.match(table)  # [tool.poetry.dependencies.stripe]: one dependency
            if sub and sub.group(1).lower() != "python":
                names.add(sub.group(1).lower())
            continue
        k = TOML_KEY.match(line)
        if not k:
            continue
        key, value = k.group(1).strip("\"'"), k.group(2)
        full = f"{table}.{key}" if table else key  # a dotted key reads as its table: optional-dependencies.ml
        array_key = full == "project.dependencies" or full.startswith(("project.optional-dependencies.",
                                                                       "dependency-groups."))
        table_key = full in ("project.optional-dependencies", "dependency-groups")
        opener = value.lstrip()[:1]
        if (array_key and opener == "[") or (table_key and opener == "{"):
            got, done = array_strings(value)
            if done:
                reqs += got
            else:
                pending = value
        elif POETRY_TABLE.match(table) and key.split(".")[0].lower() != "python":
            names.add(key.split(".")[0].lower())
    return requirement_names(reqs) | names


def pyproject_deps(text: str) -> set[str]:
    """Dependency names from pyproject.toml's dependency tables only: [project] dependencies and
    optional-dependencies, [dependency-groups], and Poetry's dependencies, dev-dependencies and
    group.*.dependencies (python itself left out). Keywords, tool config and the project name never count."""
    if tomllib is None:
        return pyproject_deps_fallback(text)
    try:
        data = tomllib.loads(text)
    except ValueError:  # tomllib.TOMLDecodeError is a ValueError
        return pyproject_deps_fallback(text)
    as_dict = lambda v: v if isinstance(v, dict) else {}  # noqa: E731
    as_list = lambda v: v if isinstance(v, list) else []  # noqa: E731
    project = as_dict(data.get("project"))
    reqs = list(as_list(project.get("dependencies")))
    for v in as_dict(project.get("optional-dependencies")).values():
        reqs += as_list(v)
    for v in as_dict(data.get("dependency-groups")).values():
        reqs += as_list(v)  # an inline {include-group = ...} table is not a string and is skipped
    poetry = as_dict(as_dict(data.get("tool")).get("poetry"))
    names = set(as_dict(poetry.get("dependencies"))) | set(as_dict(poetry.get("dev-dependencies")))
    for g in as_dict(poetry.get("group")).values():
        names |= set(as_dict(as_dict(g).get("dependencies")))
    return requirement_names(reqs) | {n.lower() for n in names if n.lower() != "python"}


WEB_UI = re.compile(r"^(react-dom|vue|svelte|@sveltejs/kit|next|nuxt|@angular/core|solid-js|astro|preact|@remix-run/react)$")
MOBILE_UI = re.compile(r"^(react-native|expo|@capacitor/core|@ionic/react|@ionic/vue|nativescript)$")
UI_APPS: list[str] = []  # folders whose package.json is a web UI app (not mobile), filled by deps_from_manifests


def deps_from_manifests(root: Path, rels: list[str]) -> tuple[set[str], list[str]]:
    deps: set[str] = set()
    found: list[str] = []
    UI_APPS.clear()
    for rel in rels:
        name = rel.rsplit("/", 1)[-1]
        if name not in MANIFESTS and not (name.startswith("requirements") and name.endswith(".txt")):
            continue
        f = root / rel
        try:
            if name == "package.json":
                j = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                own: set[str] = set()
                for k in ("dependencies", "devDependencies", "peerDependencies"):
                    own |= {d.lower() for d in (j.get(k) or {})}
                deps |= own
                if any(WEB_UI.match(d) for d in own) and not any(MOBILE_UI.match(d) for d in own):
                    UI_APPS.append(rel.rsplit("/", 1)[0] if "/" in rel else ".")
                found.append(rel)
            elif name in ("requirements.txt", "requirements-dev.txt") or (name.startswith("requirements") and name.endswith(".txt")):
                for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                    m = re.match(r"\s*([A-Za-z0-9_.\-\[\]]+)", line)
                    if m and not line.strip().startswith("#"):
                        deps.add(re.sub(r"\[.*\]", "", m.group(1)).lower())
                found.append(rel)
            elif name == "pyproject.toml":
                deps |= pyproject_deps(f.read_text(encoding="utf-8", errors="replace"))
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


def mobile_place(parents: list[str]) -> bool:
    """Whether an ios/ or android/ folder under `parents` is where a mobile project keeps it: the root, one
    folder down outside an asset folder (mobile/ios/), or inside an app under apps/ or packages/."""
    if len(parents) == 0:
        return True
    if len(parents) == 1:
        return parents[0].lower() not in ASSET_DIRS
    return len(parents) == 2 and parents[0] in ("apps", "packages") and parents[1].lower() not in ASSET_DIRS


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
        for i, part in enumerate(parts):
            if part in MOBILE_DIRS and not mobile_place(parts[:i]):
                continue
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
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", timeout=20).stdout
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
    # monorepo: package manifests in two or more different folders below the root (order-independent),
    # or a workspace config at the root
    manifest_dirs = sorted({m.rsplit("/", 1)[0] for m in manifests if "/" in m})
    workspace = next((n for n in ("pnpm-workspace.yaml", "turbo.json", "lerna.json", "nx.json") if (root / n).exists()), None)
    if not workspace and "package.json" in manifests:
        try:
            if json.loads((root / "package.json").read_text(encoding="utf-8", errors="replace")).get("workspaces"):
                workspace = "package.json workspaces"
        except (OSError, ValueError, AttributeError):
            pass
    if len(manifest_dirs) >= 2:
        hit("monorepo", f"package manifests in {len(manifest_dirs)} folders: {', '.join(manifest_dirs[:4])}")
    elif workspace:
        hit("monorepo", f"workspace config: {workspace}")

    authors = {a for a in git(root, "log", "--format=%ae", "-n", "2000").split() if a}
    commits = git(root, "rev-list", "--count", "HEAD").strip()
    first = git(root, "log", "--reverse", "--format=%as", "-n", "1").strip()
    return {
        "scanned": datetime.date.today().isoformat(),
        "root": root.name,
        "size": {"files": len(paths), "code_files": len(code_files), "manifests": manifests[:10],
                 "ui_apps": sorted(UI_APPS)[:8], "ui_app_count": len(UI_APPS),
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
