#!/usr/bin/env python3
"""Check the agent-team repo: every catalogue seat has a white-labeled skill in the right shape.

    python3 check.py            exit 1 on any problem

Per seat rulebook: frontmatter name and a description of at most 700 characters, the mark on the
description and the H1, the seven `## n · ` sections once each and in order, 130 to 200 lines (both
limits from skills/team-setup/references/seat-contract.md), every "From … → …" shift in section 2
naming its source in brackets, every mark written before a catalogue seat's name matching the
catalogue (`🧠 ML engineer`, never another emoji), short names included (`🌱 Community`, `📣 SEO`: a
name's first word, or the part before " & " or ","), no model names, no project words.
Then the private leak-word sweep over every text file, and the top-level skills (team-setup, and
team-reevaluate when it exists): name, description, no model names.
Then the generated docs, which must match what their generators write now (a few seconds: both build
small throwaway projects): docs/seats.md (tools/gen_seats_md.py, from the catalogue, the rulebooks and
the planner run on the test fixtures) and the generated files of examples/tally/
(tools/build_tally_example.py, from a fresh scaffold run), and docs/facts.json (tools/export_facts.py, the
fact sheet a website reads). A stale one fails with the command that fixes it.
Last, the version is one fact (tools/bump_version.py): .claude-plugin/plugin.json, marketplace.json and the
newest released CHANGELOG.md heading carry the same version, and '## Unreleased' opens the changelog.
The behaviour of the scripts is tested separately: `python3 -m unittest discover -s tests -v`.
"""
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAT = ROOT / "skills" / "team-setup" / "references" / "seats.md"
# Register codes and the like that only make sense inside one project. Project-identifying words
# (names, places, vendors) go in a PRIVATE, uncommitted file listed one per line: the path in
# $AGENT_TEAM_LEAK_WORDS, or .private/leak-words.txt (gitignored). Never commit that list. In CI the
# workflow writes it from the AGENT_TEAM_LEAK_WORDS secret; a path named there that is missing fails.
GENERIC_LEAK = r"DEC-[0-9]|DD-[0-9]|MD-[0-9]|TD-[0-9]|\bT-[0-9]|\bG-[0-9]|\bE-[0-9]|\bR-[0-9]"
_words_env = os.environ.get("AGENT_TEAM_LEAK_WORDS", "")
_words_file = Path(_words_env) if _words_env else ROOT / ".private" / "leak-words.txt"
_private = [w.strip() for w in _words_file.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.startswith("#")] if _words_file.is_file() else []
LEAK = re.compile("|".join([GENERIC_LEAK] + [r"\b" + re.escape(w) + r"\b" for w in _private]), re.I)
MODEL = re.compile(r"\b(Sonnet|Opus|Haiku)\b")

rows = []
for line in CAT.read_text(encoding="utf-8").splitlines():
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) == 8 and c[0] != "Mark" and not set(c[0]) <= {"-"}:
        rows.append((c[0], c[1], c[2].strip("`")))

# A seat's mark, wherever a rulebook writes it before the seat's name, is the catalogue's mark. Composed
# seat names (merges, derived roles) are matched too, so "Product & Design" is never read as "Product".
sys.path.insert(0, str(ROOT / "skills" / "team-setup" / "scripts"))
from teamlib import DERIVED_ROLES, MERGES  # noqa: E402
if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252; seat marks need UTF-8
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")

SEAT_MARK = {seat: mark for mark, seat, _ in rows}
_composed = {m["seat"] for m in MERGES.values()} | {d["seat"] for d in DERIVED_ROLES.values()}


def short_forms(seat: str) -> set[str]:
    """The shortened names a rulebook writes for a seat: 'Community' for 'Community & DevRel', 'Funding'
    for 'Funding, Revenue & Investment', 'Mobile' for 'Mobile engineer'."""
    return {seat.split(" & ")[0].split(",")[0].strip(), seat.split()[0].rstrip(",")} - {seat}


# Short name -> the catalogue seat it stands for. A short form that is itself a seat's name (the merged
# 'Customer' seat is not 'Customer Success') or that two seats share stands for nothing and is not checked.
_shorts: dict[str, set[str]] = {}
for _seat in SEAT_MARK:
    for _short in short_forms(_seat):
        _shorts.setdefault(_short, set()).add(_seat)
SHORT_NAME = {k: next(iter(v)) for k, v in _shorts.items() if len(v) == 1 and k not in SEAT_MARK and k not in _composed}
_names = sorted(set(SEAT_MARK) | _composed | set(SHORT_NAME), key=len, reverse=True)
MARKED_NAME = re.compile(r"(\S+)[ \u00a0]\**(" + "|".join(re.escape(n) for n in _names) + r")(?![\w])")
LINES = (130, 200)  # a rulebook's length, from references/seat-contract.md
DESCRIPTION_MAX = 700  # a rulebook's description, from references/seat-contract.md


def is_mark_char(ch: str) -> bool:
    """Emoji symbols, their variation selectors, joiners, keycaps and skin tones."""
    return (unicodedata.category(ch) == "So" or ch in "\ufe0e\ufe0f\u200d\u20e3"
            or "\U0001F3FB" <= ch <= "\U0001F3FF")


def trailing_mark(token: str) -> str:
    """The emoji a token ends with ('(🧭' gives '🧭', '—' gives ''), starting at a symbol."""
    i = len(token)
    while i and is_mark_char(token[i - 1]):
        i -= 1
    mark = token[i:]
    while mark and unicodedata.category(mark[0]) != "So":
        mark = mark[1:]
    return mark


# Seats written under skills/team-setup/references/seat-contract.md: each section 2 source carries a
# [read] or [found] tag. The original 21 cite by name without tags and need only a bracket.
CONTRACT_SEATS = {"seat-community", "seat-data", "seat-docs", "seat-game-design", "seat-i18n", "seat-ml",
                  "seat-mobile", "seat-security"}
SOURCE_TAG = re.compile(r"\[(?:[^\]]*[,;]\s*)?(?:read|found)\s*[\],;(]")


def unsourced_shifts(text: str, tagged: bool = False) -> list[str]:
    """Section 2's "From … → …" shifts that carry no bracketed source (the seat contract asks for one each).

    With `tagged`, a bracket counts only when it carries a `read` or `found` tag, so a bracket that
    names no page opened or found ("[practice from write-ups (secondary)]") is flagged too."""
    m = re.search(r"^## 2 · .*?(?=^## 3 · )", text, re.M | re.S)
    shifts = [re.sub(r"\s+", " ", sh.split("\n\n")[0])
              for sh in re.split(r"\n(?=- \*\*From |\d+\. \*\*From )", m.group(0) if m else "")[1:]]
    return [sh[:60] for sh in shifts if not (SOURCE_TAG.search(sh) if tagged else "[" in sh)]


def wrong_marks(text: str) -> list[str]:
    """Every `<mark> <seat name>` (full or short) whose mark is not the catalogue's mark for that seat."""
    out = set()
    for m in MARKED_NAME.finditer(text):
        name, mark = m.group(2), trailing_mark(m.group(1))
        seat = SHORT_NAME.get(name, name)
        if seat in SEAT_MARK and mark and mark != SEAT_MARK[seat]:
            out.add(f"{mark} {name} (catalogue: {SEAT_MARK[seat]} {seat})")
    return sorted(out)

bad = 0
for mark, seat, skill in rows:
    f = ROOT / "skills" / "team-setup" / "seats" / skill / "SKILL.md"
    p = []
    if not f.is_file():
        print(f"{mark} {skill}: MISSING"); bad += 1; continue
    s = f.read_text(encoding="utf-8")
    fm = re.match(r"---\n(.*?)\n---\n", s, re.S)
    if not fm:
        p.append("no frontmatter")
    else:
        name = re.search(r"^name:\s*(\S+)", fm.group(1), re.M)
        if not name or name.group(1) != skill:
            p.append("name mismatch")
        d = re.search(r'^description:\s*"(.*)"\s*$', fm.group(1), re.M | re.S)
        desc = d.group(1).replace('\\"', '"') if d else ""
        if not desc.startswith(mark):
            p.append("description does not open with the mark")
        if len(desc) > DESCRIPTION_MAX:
            p.append(f"description {len(desc)} chars, over {DESCRIPTION_MAX}")
    h1 = re.search(r"^# (.*)$", s[fm.end():] if fm else s, re.M)
    if not h1 or not h1.group(1).startswith(mark):
        p.append("H1 does not open with the mark")
    heads = [int(m.group(1)) for m in re.finditer(r"^## (\d+) · ", s, re.M)]
    for n in range(7):
        if heads.count(n) != 1:
            p.append(f"no '## {n} · ' section" if not heads.count(n) else f"'## {n} · ' {heads.count(n)} times")
    if [h for h in heads if h > 6]:
        p.append(f"sections beyond the seven: {sorted(h for h in heads if h > 6)}")
    elif heads != sorted(heads):
        p.append(f"sections out of order: {heads}")
    unsourced = unsourced_shifts(s, tagged=skill in CONTRACT_SEATS)
    if unsourced:
        p.append(f"section 2 shift with no source: {'; '.join(unsourced[:2])}")
    marks = wrong_marks(s)
    if marks:
        p.append(f"marks differ from the catalogue: {', '.join(marks[:4])}")
    if MODEL.search(s):
        p.append("names a model")
    leaks = sorted({m.group(0) for m in LEAK.finditer(s)})
    if leaks:
        generic = sorted({x for x in leaks if re.fullmatch(GENERIC_LEAK, x, re.I)})
        p.append(f"project words: {', '.join(generic[:6])}{' and private-list words' if len(generic) < len(leaks) else ''}")
    n = s.count("\n")
    if not LINES[0] <= n <= LINES[1]:
        p.append(f"{n} lines, outside {LINES[0]}-{LINES[1]}")
    bad += bool(p)
    print(f"{mark} {skill} ({n} lines): {'OK' if not p else '; '.join(p)}")

# Every text file in the repo, against the private words only (register codes appear in examples on purpose).
if _private:
    PRIVATE = re.compile("|".join(r"\b" + re.escape(w) + r"\b" for w in _private), re.I)
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or ".git" in f.parts or ".private" in f.parts:
            continue
        try:  # every text file, whatever its name (CITATION.cff, CODEOWNERS, LICENSE ...); binaries are skipped
            text = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if PRIVATE.search(line):  # never print the word itself: CI logs are public
                print(f"leak: {f.relative_to(ROOT)}:{n}: a word from the private list"); bad += 1
elif _words_env:  # named on purpose (CI writes it from a secret) but unusable: the sweep would silently not run
    why = "which lists no words" if _words_file.is_file() else "which is not a file"
    print(f"leak words: AGENT_TEAM_LEAK_WORDS names {_words_env}, {why}"); bad += 1
else:
    print("note: no private leak-word list found; only generic checks ran")

# The top-level skills. team-reevaluate is optional here: it may not have landed yet.
for skill, required in (("team-setup", True), ("team-reevaluate", False)):
    f = ROOT / "skills" / skill / "SKILL.md"
    if not f.is_file():
        if required:
            print(f"{skill}: MISSING"); bad += 1
        else:
            print(f"note: skills/{skill}/SKILL.md not found; its check skipped")
        continue
    s = f.read_text(encoding="utf-8")
    p = []
    fm = re.match(r"---\n(.*?)\n---\n", s, re.S)
    name = re.search(r"^name:\s*(\S+)", fm.group(1), re.M) if fm else None
    if not name or name.group(1) != skill:
        p.append(f"name is not {skill}")
    d = re.search(r'^description:\s*"(.*)"\s*$', fm.group(1), re.M | re.S) if fm else None
    if not d or not d.group(1).strip():
        p.append("no description")
    elif len(d.group(1).replace('\\"', '"')) > 1024:
        p.append(f"description {len(d.group(1))} chars")
    if MODEL.search(s):
        p.append("names a model")
    bad += bool(p)
    print(f"{skill} ({s.count(chr(10))} lines): {'OK' if not p else '; '.join(p)}")
# The generated docs: docs/seats.md and the generated half of examples/tally/. A generator that fails (a planner
# change broke a sentence it asserts, or the scaffold failed) counts as a problem too, with its message.
sys.path.insert(0, str(ROOT / "tools"))
try:
    import gen_seats_md  # noqa: E402
    seats_md = ROOT / "docs" / "seats.md"
    if not seats_md.is_file() or seats_md.read_text(encoding="utf-8") != gen_seats_md.render():
        print("docs/seats.md: stale against the catalogue, the rulebooks or the planner; run python3 tools/gen_seats_md.py")
        bad += 1
    else:
        print("docs/seats.md: current")
except Exception as e:  # noqa: BLE001 - any generator failure (an asserted sentence broke) is a problem
    print(f"docs/seats.md: tools/gen_seats_md.py failed: {type(e).__name__}: {e}"); bad += 1
try:
    import build_tally_example  # noqa: E402
    stale = build_tally_example.stale(build_tally_example.generated())
    for rel in stale:
        print(f"examples/tally/{rel}: stale; run python3 tools/build_tally_example.py")
    bad += bool(stale)
    if not stale:
        print("examples/tally: generated files current")
except (SystemExit, Exception) as e:  # noqa: BLE001
    print(f"examples/tally: tools/build_tally_example.py failed: {type(e).__name__}: {e}"); bad += 1
# The fact sheet a website reads (docs/facts.json, from tools/export_facts.py), and the version: plugin.json,
# marketplace.json and the newest released CHANGELOG heading agree, under a '## Unreleased' heading.
try:
    import export_facts  # noqa: E402
    if export_facts.stale():
        print("docs/facts.json: stale against the catalogue, the skills, teamlib, the tiers or plugin.json; "
              "run python3 tools/export_facts.py")
        bad += 1
    else:
        print("docs/facts.json: current")
except Exception as e:  # noqa: BLE001
    print(f"docs/facts.json: tools/export_facts.py failed: {type(e).__name__}: {e}"); bad += 1
try:
    import bump_version  # noqa: E402
    version_problems = bump_version.problems(ROOT)
    for problem in version_problems:
        print(f"version: {problem}")
    bad += bool(version_problems)
    if not version_problems:
        print(f"version: {bump_version.read(ROOT)['plugin']['version']} everywhere it is written")
except Exception as e:  # noqa: BLE001
    print(f"version: tools/bump_version.py failed: {type(e).__name__}: {e}"); bad += 1
sys.exit(1 if bad else 0)
