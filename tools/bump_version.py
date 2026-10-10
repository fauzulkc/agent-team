#!/usr/bin/env python3
"""The plugin's version: one source, checked, and moved in one command.

    python3 tools/bump_version.py X.Y.Z [--date YYYY-MM-DD]   cut release X.Y.Z (date defaults to today)
    python3 tools/bump_version.py --check                     exit 1 when the versions disagree
    python3 tools/bump_version.py --current                   print plugin.json's version
    python3 tools/bump_version.py --notes X.Y.Z               print X.Y.Z's CHANGELOG section (release notes)

The version lives in .claude-plugin/plugin.json `version`. .claude-plugin/marketplace.json's entry for
the plugin must carry the same version, and so must the newest released heading in CHANGELOG.md and,
when the file exists, CITATION.cff's `version` (a bump sets its `date-released` too).
CHANGELOG.md opens with `## Unreleased` (body `Nothing yet.` when empty), then one `## X.Y.Z` heading per
release, newest first, each optionally followed by ` — YYYY-MM-DD`.

A bump moves the Unreleased body under a new `## X.Y.Z — date` heading, leaves `## Unreleased` with
`Nothing yet.`, sets both JSON versions and regenerates docs/facts.json (it carries the version). It
names any README or docs/how-it-works.md line that still says "version <old>". It refuses a version that is not greater than the current
one, an Unreleased section with nothing in it, and a repo whose versions already disagree.
check.py calls problems(); the release workflow calls --current and --notes. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = Path(".claude-plugin") / "plugin.json"
MARKETPLACE = Path(".claude-plugin") / "marketplace.json"
CHANGELOG = Path("CHANGELOG.md")
CITATION = Path("CITATION.cff")  # optional: when present, its version and date-released follow the release
CITATION_VERSION = re.compile(r'^version:[ \t]*"?([^"\s]*)"?[ \t]*$', re.M)
CITATION_DATE = re.compile(r'^date-released:[ \t]*"?([^"\s]*)"?[ \t]*$', re.M)

EMPTY = "Nothing yet."
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
HEADING = re.compile(r"^## (.*?)\s*$", re.M)
VERSION_HEADING = re.compile(r"^(\d+\.\d+\.\d+)(?: — (\d{4}-\d{2}-\d{2}))?$")


class Refusal(Exception):
    """A bump the tool will not make, with the reason in plain words."""


def parse(version: str) -> Tuple[int, int, int]:
    m = SEMVER.match(version)
    if not m:
        raise Refusal(f"{version!r} is not a version of the form X.Y.Z")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def sections(text: str) -> List[Tuple[str, int, int]]:
    """Every `## ` heading as (title, start of the heading line, end of its section)."""
    heads = list(HEADING.finditer(text))
    return [(h.group(1), h.start(), heads[i + 1].start() if i + 1 < len(heads) else len(text))
            for i, h in enumerate(heads)]


def body(text: str, start: int, end: int) -> str:
    """A section's text below its heading line, without the surrounding blank lines."""
    newline = text.find("\n", start, end)
    return "" if newline < 0 else text[newline + 1:end].strip("\n")


def marketplace_entry(marketplace: dict, name: str) -> Optional[dict]:
    plugins = marketplace.get("plugins") or []
    return next((p for p in plugins if p.get("name") == name), plugins[0] if plugins else None)


def read(root: Path) -> Dict[str, object]:
    """The three places the version is written, as found."""
    plugin = json.loads((root / PLUGIN).read_text(encoding="utf-8"))
    marketplace = json.loads((root / MARKETPLACE).read_text(encoding="utf-8"))
    changelog = (root / CHANGELOG).read_text(encoding="utf-8")
    entry = marketplace_entry(marketplace, plugin.get("name", ""))
    return {"plugin": plugin, "marketplace": marketplace, "entry": entry, "changelog": changelog}


def problems(root: Path = ROOT) -> List[str]:
    """Everything that keeps the version from being one fact: empty when plugin.json, marketplace.json and
    the newest released CHANGELOG heading agree and `## Unreleased` opens the changelog."""
    found = read(root)
    plugin, entry, changelog = found["plugin"], found["entry"], found["changelog"]
    out = []
    version = plugin.get("version")
    if not isinstance(version, str) or not SEMVER.match(version):
        out.append(f"{PLUGIN}: version {version!r} is not X.Y.Z")
    if entry is None:
        out.append(f"{MARKETPLACE}: no plugins entry")
    elif entry.get("version") != version:
        out.append(f"{MARKETPLACE}: version {entry.get('version')!r} differs from {PLUGIN} {version!r}")
    titles = [t for t, _, _ in sections(changelog)]
    released = []
    for title in titles:
        if title == "Unreleased":
            continue
        m = VERSION_HEADING.match(title)
        if not m:
            out.append(f"{CHANGELOG}: heading '## {title}' is neither '## Unreleased' nor '## X.Y.Z [— YYYY-MM-DD]'")
            continue
        if m.group(2):
            try:
                datetime.date.fromisoformat(m.group(2))
            except ValueError:
                out.append(f"{CHANGELOG}: '## {title}' carries no real date")
        released.append(m.group(1))
    if "Unreleased" not in titles:
        out.append(f"{CHANGELOG}: no '## Unreleased' heading (it opens the changelog, '{EMPTY}' when empty)")
    elif titles[0] != "Unreleased" or titles.count("Unreleased") > 1:
        out.append(f"{CHANGELOG}: '## Unreleased' must be the first '## ' heading, once")
    citation = root / CITATION
    if citation.is_file():
        m = CITATION_VERSION.search(citation.read_text(encoding="utf-8"))
        if not m or m.group(1) != version:
            out.append(f"{CITATION}: version {m.group(1) if m else None!r} differs from {PLUGIN} {version!r}")
    if not released:
        out.append(f"{CHANGELOG}: no released '## X.Y.Z' heading")
    else:
        if released[0] != version:
            out.append(f"{CHANGELOG}: newest released heading is {released[0]}, {PLUGIN} says {version}")
        keys = [parse(v) for v in released if SEMVER.match(v)]
        if keys != sorted(set(keys), reverse=True):
            out.append(f"{CHANGELOG}: release headings are not newest first, each once: {', '.join(released)}")
    return out


def notes(root: Path, version: str) -> str:
    """The CHANGELOG section for `version`: everything under its heading up to the next `## ` heading."""
    changelog = (root / CHANGELOG).read_text(encoding="utf-8")
    for title, start, end in sections(changelog):
        m = VERSION_HEADING.match(title)
        if m and m.group(1) == version:
            text = body(changelog, start, end)
            if not text.strip():
                raise Refusal(f"{CHANGELOG}: the {version} section is empty")
            return text + "\n"
    raise Refusal(f"{CHANGELOG}: no '## {version}' heading")


def set_version(path: Path, data: dict, old: str, new: str, expected: dict) -> None:
    """Write `expected` (data with the version changed) keeping the file's own layout: replace the old
    version string where it sits and confirm the result parses to exactly `expected`; reformat only if not."""
    text = path.read_text(encoding="utf-8")
    edited = re.sub(r'("version"\s*:\s*)"' + re.escape(old) + '"', lambda m: m.group(1) + json.dumps(new), text)
    if json.loads(edited) != expected:
        edited = json.dumps(expected, indent=2, ensure_ascii=False) + "\n"
    path.write_text(edited, encoding="utf-8")


def bump(root: Path, new: str, date: str) -> str:
    """Cut release `new` dated `date`. Returns the old version. Writes nothing when it refuses."""
    existing = problems(root)
    if existing:
        raise Refusal("the versions disagree already; fix these first:\n  " + "\n  ".join(existing))
    try:
        if datetime.date.fromisoformat(date).isoformat() != date:
            raise ValueError
    except ValueError:
        raise Refusal(f"{date!r} is not a date of the form YYYY-MM-DD") from None
    found = read(root)
    plugin, marketplace, entry, changelog = found["plugin"], found["marketplace"], found["entry"], found["changelog"]
    old = plugin["version"]
    if parse(new) <= parse(old):
        raise Refusal(f"{new} is not greater than the current version {old}")
    title, start, end = sections(changelog)[0]
    # A "Nothing yet." line left above real entries is dropped with the move.
    entries = "\n".join(l for l in body(changelog, start, end).split("\n") if l.strip() != EMPTY).strip("\n")
    if not any(l.strip() and not l.lstrip().startswith("#") for l in entries.split("\n")):  # headings alone are not notes
        raise Refusal(f"{CHANGELOG}: '## Unreleased' has nothing in it; write the release's entries there first")
    heading_line_end = changelog.find("\n", start, end) + 1
    gap = "\n" if heading_line_end and changelog[heading_line_end:heading_line_end + 1] == "\n" else ""
    rest = changelog[end:]
    new_changelog = (changelog[:start] + f"## Unreleased\n{gap}{EMPTY}\n\n## {new} — {date}\n{gap}{entries}\n\n"
                     + rest)

    new_plugin = dict(plugin, version=new)
    new_marketplace = json.loads(json.dumps(marketplace))
    marketplace_entry(new_marketplace, plugin.get("name", ""))["version"] = new
    set_version(root / PLUGIN, plugin, old, new, new_plugin)
    set_version(root / MARKETPLACE, marketplace, old, new, new_marketplace)
    (root / CHANGELOG).write_text(new_changelog, encoding="utf-8")
    citation = root / CITATION
    if citation.is_file():
        text = CITATION_VERSION.sub(f"version: {new}", citation.read_text(encoding="utf-8"), count=1)
        citation.write_text(CITATION_DATE.sub(f"date-released: {date}", text, count=1), encoding="utf-8")
    after = problems(root)
    if after:  # cannot happen when the edits above are right; say so loudly if it does
        raise Refusal("the bump left the versions disagreeing:\n  " + "\n  ".join(after))
    return old


def refresh_facts(root: Path) -> Optional[str]:
    """Rewrite docs/facts.json, which carries the version, so check.py stays green after a bump."""
    if root != ROOT:  # export_facts reads the repo it lives in; a bump of another tree leaves it to the caller
        return None
    sys.path.insert(0, str(ROOT / "tools"))
    import export_facts  # noqa: E402
    export_facts.OUT.write_text(export_facts.render(), encoding="utf-8")
    return str(export_facts.OUT.relative_to(ROOT))


def still_naming(root: Path, old: str) -> List[str]:
    """Hand-written lines that still state the old version as the current one ("version 1.3.0",
    "version-1.3.0" in a badge URL): a reminder to update them, never edited by this tool."""
    pattern = re.compile(r"\bversion[ -]" + re.escape(old) + r"\b", re.I)
    out = []
    for path in ("README.md", "docs/how-it-works.md"):
        f = root / path
        if f.is_file():
            out += [f"{path}:{n}" for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
                    if pattern.search(line)]
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", nargs="?", help="the release to cut, X.Y.Z")
    ap.add_argument("--date", help="the release date, YYYY-MM-DD (default: today)")
    ap.add_argument("--check", action="store_true", help="exit 1 when the versions disagree")
    ap.add_argument("--current", action="store_true", help="print plugin.json's version")
    ap.add_argument("--notes", metavar="X.Y.Z", help="print that version's CHANGELOG section")
    ap.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    modes = sum([bool(args.version), args.check, args.current, bool(args.notes)])
    if modes != 1:
        ap.error("give exactly one of: a version, --check, --current, --notes X.Y.Z")
    if args.date and not args.version:
        ap.error("--date goes with a version to cut")
    root = args.root.resolve()
    try:
        if args.check:
            found = problems(root)
            for p in found:
                print(f"version: {p}")
            if not found:
                print(f"version: {read(root)['plugin']['version']} everywhere")
            return 1 if found else 0
        if args.current:
            print(read(root)["plugin"]["version"])
            return 0
        if args.notes:
            parse(args.notes)
            sys.stdout.write(notes(root, args.notes))
            return 0
        date = args.date or datetime.date.today().isoformat()
        old = bump(root, args.version, date)
    except Refusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    facts = refresh_facts(root)
    print(f"{old} -> {args.version} ({date}): {PLUGIN}, {MARKETPLACE}, {CHANGELOG}"
          + (f", {CITATION}" if (root / CITATION).is_file() else "")
          + (f" and {facts}" if facts else "") + " updated.")
    for where in still_naming(root, old):
        print(f"  still says version {old}: {where}")
    print(f"Next: python3 check.py, then commit 'release: {args.version}' and tag v{args.version}"
          " (docs/maintaining.md, Cutting a release).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
