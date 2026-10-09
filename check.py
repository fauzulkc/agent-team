#!/usr/bin/env python3
"""Check the agent-team repo: every catalogue seat has a white-labeled skill in the right shape.

    python3 check.py            exit 1 on any problem
"""
import os
import re
import sys
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
    for n in range(7):
        if not re.search(rf"^## {n} ", s, re.M):
            p.append(f"no §{n}")
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

setup = ROOT / "skills" / "team-setup" / "SKILL.md"
if not setup.is_file():
    print("team-setup: MISSING"); bad += 1
sys.exit(1 if bad else 0)
