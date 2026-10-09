#!/usr/bin/env python3
"""Check the agent-team repo: every catalogue seat has a white-labeled skill in the right shape.

    python3 check.py            exit 1 on any problem

Per seat rulebook: frontmatter name and description, the mark on the description and the H1, the
seven `## n · ` sections once each and in order, every mark written before a catalogue seat's name
matching the catalogue (`🧠 ML engineer`, never another emoji), no model names, no project words.
Then the private leak-word sweep over every text file, and the top-level skills (team-setup, and
team-reevaluate when it exists): name, description, no model names.
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
# $AGENT_TEAM_LEAK_WORDS, or .private/leak-words.txt (gitignored). Never commit that list.
GENERIC_LEAK = r"DEC-[0-9]|DD-[0-9]|MD-[0-9]|TD-[0-9]|\bT-[0-9]|\bG-[0-9]|\bE-[0-9]|\bR-[0-9]"
_words_file = Path(os.environ.get("AGENT_TEAM_LEAK_WORDS", ROOT / ".private" / "leak-words.txt"))
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

SEAT_MARK = {seat: mark for mark, seat, _ in rows}
_names = sorted(set(SEAT_MARK) | {m["seat"] for m in MERGES.values()} | {d["seat"] for d in DERIVED_ROLES.values()},
                key=len, reverse=True)
MARKED_NAME = re.compile(r"(\S+)[ \u00a0]\**(" + "|".join(re.escape(n) for n in _names) + r")(?![\w])")


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


def wrong_marks(text: str) -> list[str]:
    out = set()
    for m in MARKED_NAME.finditer(text):
        name, mark = m.group(2), trailing_mark(m.group(1))
        if name in SEAT_MARK and mark and mark != SEAT_MARK[name]:
            out.add(f"{mark} {name} (catalogue: {SEAT_MARK[name]})")
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
        if len(desc) > 1024:
            p.append(f"description {len(desc)} chars")
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
    marks = wrong_marks(s)
    if marks:
        p.append(f"marks differ from the catalogue: {', '.join(marks[:4])}")
    if MODEL.search(s):
        p.append("names a model")
    leaks = sorted({m.group(0) for m in LEAK.finditer(s)})
    if leaks:
        p.append(f"project words: {', '.join(leaks[:6])}")
    n = s.count("\n")
    bad += bool(p)
    print(f"{mark} {skill} ({n} lines): {'OK' if not p else '; '.join(p)}")

# Every text file in the repo, against the private words only (register codes appear in examples on purpose).
if _private:
    PRIVATE = re.compile("|".join(r"\b" + re.escape(w) + r"\b" for w in _private), re.I)
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or ".git" in f.parts or ".private" in f.parts or f.suffix not in {".md", ".py", ".json", ".yml", ".yaml", ".sh", ".txt", ".lock"}:
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = PRIVATE.search(line)
            if m:
                print(f"leak: {f.relative_to(ROOT)}:{n}: {m.group(0)}"); bad += 1
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
sys.exit(1 if bad else 0)
