#!/usr/bin/env python3
"""Generate docs/seats.md from the catalogue, the rulebooks, teamlib and the planner.

    python3 tools/gen_seats_md.py            write docs/seats.md
    python3 tools/gen_seats_md.py --check    exit 1 when docs/seats.md differs from what it would write

Every row and every number comes from the code, so the page cannot drift from it:
  the catalogue      skills/team-setup/references/seats.md (mark, seat, kind, reports to, seat it when) and
                     each rulebook's description up to "Use when" (what it does);
  merged seats       teamlib.MERGES, and which option forms which from plan.py (SMALL_MERGES, needs());
  new roles          teamlib.DERIVED_ROLES, raised by scan.py's DEP_SIGNALS and PATH_SIGNALS;
  splits             plan.SPLIT_MARKS and plan.MAX_SPLITS;
  starter shapes     measured: tests/repo_fixtures.py builds its `lib`, `saas` and `monorepo` projects in a
                     temporary folder (git with no user config), scan.py scans them, plan.py plans them. The
                     web product is also planned at small and medium size (the same scan, its size fields set),
                     and with an API framework added, which is what moves its numbers.
The prose beside the numbers states facts the generator asserts (Research joins once the project is past
tiny; Funding is never in the recommended team, so Money never forms there), so a planner change that
breaks a sentence fails here instead of leaving the sentence wrong. check.py runs `--check`.
Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "team-setup" / "scripts"
OUT = ROOT / "docs" / "seats.md"
for p in (SCRIPTS, ROOT / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import plan  # noqa: E402
import repo_fixtures  # noqa: E402
import scan as scanner  # noqa: E402
import teamlib  # noqa: E402


KEEP = "\x00"  # joins a mark to its seat name so a wrapped line never splits them; a space in the output


def job(skill: str, mark: str) -> str:
    """A rulebook's description from after its mark up to "Use when": what the seat does."""
    text = (teamlib.SEATS_SRC / skill / "SKILL.md").read_text(encoding="utf-8")
    fm = re.match(r"---\n(.*?)\n---\n", text, re.S).group(1)
    desc = re.search(r'^description:\s*"(.*)"\s*$', fm, re.M | re.S).group(1).replace('\\"', '"')
    assert desc.startswith(mark), f"{skill}: description does not open with {mark}"
    desc = desc[len(mark):].strip()
    m = re.search(r"\.\s+Use (when|for|on|in|before|whenever|to)\b", desc)
    out = desc[: m.start() + 1] if m else desc
    assert "|" not in out, f"{skill}: a pipe in the description would break the table"
    return out


def readable_dep(pattern: str) -> list[str]:
    """A dependency regex as the names it matches: '^pyqt[56]?$' gives pyqt, pyqt5, pyqt6."""
    body = pattern.lstrip("^").rstrip("$").replace("\\.", ".")
    m = re.search(r"(\[([^\]]+)\]|(.))\?", body)
    if not m:
        return [body]
    head, tail = body[: m.start()], body[m.end():]
    return [x for o in [""] + list(m.group(2) or m.group(3)) for x in readable_dep(head + o + tail)]


def raised_by(signal: str) -> str:
    deps = [f"`{n}`" for p in scanner.DEP_SIGNALS.get(signal, []) for n in readable_dep(p)]
    paths = []
    for p in scanner.PATH_SIGNALS.get(signal, []):
        if ":" in p and not p.startswith("*"):
            f, needle = p.split(":", 1)
            paths.append(f"`{f}` containing `{needle}`")
        else:
            paths.append(f"`{p}`")
    parts = (["files " + ", ".join(paths)] if paths else []) + (["dependencies such as " + ", ".join(deps[:3])] if deps else [])
    return "; ".join(parts)


def names(specs: list[dict], cat: dict) -> str:
    """Seat specs as '<mark> <seat>' joined with commas."""
    out = []
    for s in specs:
        row = cat.get(s["team"]) if s.get("type", "catalogue") == "catalogue" else None
        out.append(f"{row['mark']}{KEEP}{row['seat']}" if row else f"{s['mark']}{KEEP}{s['seat']}")
    return ", ".join(out)


def roles_held(specs: list[dict]) -> int:
    return sum(len(s["of"]) if s.get("type") == "merge" else 1 for s in specs)


def measured_scans() -> dict[str, dict]:
    """Scan the test fixtures, built fresh in a temporary folder with an isolated git."""
    out = {}
    with tempfile.TemporaryDirectory(prefix="seats-md-") as tmp:
        tmp = Path(tmp)
        env = repo_fixtures.isolated_env(tmp, tmp)
        for name, build in (("lib", repo_fixtures.build_lib), ("saas", repo_fixtures.build_saas),
                            ("monorepo", repo_fixtures.build_monorepo)):
            root = tmp / name
            root.mkdir()
            build(root, env)
            out[name] = scanner.scan(root)
    return out


def resized(scan: dict, code_files: int, contributors: int) -> dict:
    return {**scan, "size": {**scan["size"], "code_files": code_files, "contributors": contributors}}


def render() -> str:
    cat = teamlib.catalogue()
    merges, derived = teamlib.MERGES, teamlib.DERIVED_ROLES
    scans = measured_scans()
    lib, saas, mono = scans["lib"], scans["saas"], scans["monorepo"]
    web = {"tiny": saas, "small": resized(saas, 300, 2), "medium": resized(saas, 661, 4)}
    web_api = {**web["medium"], "signals": {**web["medium"]["signals"], "api": ["dependency express"]}}
    opts = {k: plan.options(s) for k, s in (("lib", lib), ("mono", mono), *web.items())}
    full_api = plan.build(web_api, "full")
    for size, s in web.items():
        assert plan.size_class(s) == size, (size, plan.size_class(s))
    # the facts the prose states, checked
    rec_teams = {k: {x["team"] for x in o["recommended"]} for k, o in opts.items()}
    assert "research" not in rec_teams["tiny"] and "research" in rec_teams["small"] and "research" in rec_teams["medium"]
    core, optional, _ = plan.needs(saas)
    assert "funding" not in core and "funding" in optional, "the Money sentence assumes Funding is only ever optional"
    assert not any(x["team"] == "money" for o in opts.values() for k in ("lean", "recommended") for x in o[k])
    assert {x["team"] for x in full_api} - {x["team"] for x in opts["medium"]["full"]} == {"docs"}
    splits = [x for x in opts["mono"]["full"] if x["team"].startswith("frontend-")]
    assert len(splits) == 2 and plan.size_class(mono) == "small"
    hardware = derived["hardware"]
    assert all(any(x["team"] == hardware["team"] for x in opts["mono"][o]) for o in ("lean", "recommended", "full"))
    assert not any(x.get("type") == "merge" for x in opts["medium"]["recommended"])
    # the projects as the page describes them
    assert {"oss", "tests", "ci"} <= set(lib["signals"])
    assert {"payments", "auth", "email", "analytics", "landing", "content", "deploy", "personal_data"} <= set(saas["signals"])
    assert {"ui_web", "mobile", "ml", "data_pipelines", "i18n", "hardware"} <= set(mono["signals"])
    small_merges = [m for m in plan.SMALL_MERGES if m != "money"]
    words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    max_splits = words.get(plan.MAX_SPLITS, str(plan.MAX_SPLITS))
    split_marks = " ".join(plan.SPLIT_MARKS[:plan.MAX_SPLITS])
    seat = lambda t: f"{cat[t]['mark']}{KEEP}{cat[t]['seat']}"  # noqa: E731
    merged = lambda t: f"{merges[t]['mark']}{KEEP}{merges[t]['seat']}"  # noqa: E731
    n = {k: {o: len(v[o]) for o in ("lean", "recommended", "full")} for k, v in opts.items()}

    L: list[str] = []

    def para(text: str, bullet: bool = False) -> None:
        """One paragraph (or list item), wrapped at 100 columns."""
        L.append(textwrap.fill(" ".join(text.split()), width=100, break_long_words=False, break_on_hyphens=False,
                               initial_indent="- " if bullet else "", subsequent_indent="  " if bullet else ""))

    def table(header: list[str], rows: list[list[str]]) -> None:
        L.append("| " + " | ".join(header) + " |")
        L.append("|" + "---|" * len(header))
        L.extend("| " + " | ".join(r) + " |" for r in rows)

    L += ["# The seats", "",
          "<!-- GENERATED by tools/gen_seats_md.py from the catalogue, the rulebooks and the planner. "
          "Do not edit by hand. -->", ""]
    para(f"Every seat in the catalogue ({len(cat)}), then the {words[len(merges)]} merged seats a small team can "
         f"run as one session, then the {words[len(derived)]} new roles setup creates when no catalogue seat covers the work. "
         "Each row's job is the opening of that seat's rulebook description (the part before *Use when*); kinds, "
         "reporting lines and *seat it when* come from the catalogue (`skills/team-setup/references/seats.md`). "
         "Setup scans the repo and proposes seats with the evidence for each "
         "([how the team is sized](how-it-works.md#how-the-team-is-sized)). Add one by name later "
         "(*\"add Motion to the team\"*), or let a re-evaluation propose it.")
    L += ["", "## The catalogue", ""]
    table(["", "Seat", "Open with", "Kind", "Reports to", "What it does", "Seat it when"],
          [[r["mark"], f"**{r['seat']}**", f"`/{r['skill']}`", r["kind"], r["reports_to"],
            job(r["skill"], r["mark"]), r["when"]] for r in cat.values()])
    L.append("")
    para("**Kinds.** *Owner-side* seats speak for or to you. *Directors* own a register and rule inside it. The "
         "*manager* runs a daily operation under directors. *Implementation* seats build under a director's "
         "scope. *Checks* challenge other seats' work and own no product register.")
    L.append("")
    para(f"**Coordination seats.** *Other seats* means every seat except {seat('chief-of-staff')} and "
         f"{seat('scope-trimmer')}; a merged, split or new seat counts as one. The Chief of Staff joins once five "
         "or more other seats run (seven in the lean option), and the Scope Trimmer once ten or more do, in "
         "setup's options and in a re-evaluation alike.")
    L += ["", "## Merged seats", ""]
    para("One session holding several roles. Its rulebook is composed from its members' rulebooks: each "
         "member's opening and every section of each, kept under \"As <member>\", and recomposed when they "
         "improve (*\"sync the team's rulebooks\"*). Its brief carries its members' briefs.")
    L.append("")
    table(["", "Seat", "Open with", "Holds", "Kind", "Why one session can hold it"],
          [[m["mark"], f"**{m['seat']}**", f"`/seat-{t}`", " + ".join(seat(x) for x in m["of"]), m["kind"], m["why"]]
           for t, m in merges.items()])
    L.append("")
    para("**Which option merges what.** A merge needs two or more of its members in the team, and claims "
         "them: two merges never share a member. *Lean* takes every merge that fits. *Recommended* takes every "
         "merge for a tiny project; for a small one only "
         + ", ".join(merged(t) for t in small_merges[:-1]) + f" and {merged(small_merges[-1])}; none for a "
         "medium or large one. *Full* takes none.")
    L.append("")
    para(f"**{merged('money')} never forms at setup unless you edit the plan.** It needs {seat('funding')}, "
         "which only the full option seats, and the full option merges nothing; so at setup "
         f"{seat('payments')} goes to {merged('legal-compliance')}. A re-evaluation can propose "
         f"{merged('money')} later, when both its members are seated and quiet.")
    L.append("")
    para(f"**{merged('engineering-platform')} is never formed past 2,000 source files**, at setup or at a "
         f"re-evaluation. **A check seat ({seat('bar-raiser')}, {seat('scope-trimmer')}, {seat('user')}, "
         f"{seat('security')}) joins only a check merge**: {merged('quality')}, which setup forms when it merges. "
         f"No merge a re-evaluation proposes holds {seat('ceo')} or {seat('bar-raiser')}.")
    L += ["", "## New roles", ""]
    para("Roles no catalogue seat covers, raised by what the scan finds. Each is derived from the base "
         "rulebook named here and arrives with an `AUTHORING NEEDED` banner: the session that seats it rewrites "
         "it for the role (`skills/team-setup/references/seat-contract.md`) before the seat works. Until then "
         "the seat has no worker and `scripts/gen-team-agents.py --check` fails; after the rewrite, run "
         "`python3 scripts/gen-team-agents.py`, then `--check`.")
    L.append("")
    table(["", "Seat", "Open with", "Derived from", "Kind", "Reports to", "Scope", "Raised by"],
          [[d["mark"], f"**{d['seat']}**", f"`/seat-{d['team']}`", f"`{d['base']}`", d["kind"], d["reports_to"],
            d["scope"], raised_by(sig)] for sig, d in derived.items()])
    L.append("")
    para("**Splits.** A project with two or more web UI apps can run one frontend seat per app "
         f"(`Frontend engineer (<app>)`, marks {split_marks}, up to {max_splits}), each derived from "
         f"`seat-frontend` with its scope set to its own folder. Past {max_splits} apps, {seat('frontend')} "
         "stays and holds the rest. *Full* offers the split whenever there are two or more UI apps; "
         "*recommended* only once the project is large.")
    L += ["", "## Starter shapes", ""]
    para("What setup offers on the invented test projects in `tests/repo_fixtures.py`, measured by running "
         "`scan.py` and `plan.py` on them each time this page is regenerated. Your repo's own evidence decides "
         "your team.")
    L.append("")
    count = lambda k: [str(n[k]["lean"]), str(n[k]["recommended"]), str(n[k]["full"])]  # noqa: E731
    medium = count("medium")
    medium[2] += f" ({len(full_api)} when it serves an API)"
    table(["Project", "Size", "Lean", "Recommended", "Full"], [
        ["a small open-source library", opts["lib"]["size"], *count("lib")],
        ["a web product that takes sign-ups and payments", "tiny", *count("tiny")],
        ["the same web product", "small", *count("small")],
        ["the same web product", "medium", *medium],
        ["a monorepo: two web apps, a mobile app, models, a warehouse, locales, firmware", opts["mono"]["size"],
         *count("mono")]])
    L.append("")
    para(f"**The library** (tests, CI, a licence and a contributing guide): recommended is "
         f"{names(opts['lib']['recommended'], cat)}.", bullet=True)
    para("**The web product** (payments, sign-in, email, product analytics, a pricing page, a blog, customer "
         f"emails in its schema, deploy files): lean holds {roles_held(opts['tiny']['lean'])} roles in "
         f"{n['tiny']['lean']} sessions. Recommended while tiny is {names(opts['tiny']['recommended'], cat)}. "
         f"Past tiny, {seat('research')} joins (product analytics are in) and the merges thin out; at medium "
         f"every role has its own seat. Full adds {seat('competition')} and {seat('funding')}, and "
         f"{seat('docs')} when it serves an API.", bullet=True)
    para(f"**The monorepo**: {hardware['mark']} {hardware['seat']} joins as a new role in every option, and full "
         f"splits the frontend per app: {names(splits, cat)}.", bullet=True)
    return "\n".join(L).replace(KEEP, " ") + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 when docs/seats.md is stale; write nothing")
    a = ap.parse_args()
    text = render()
    if a.check:
        if OUT.read_text(encoding="utf-8") != text:
            print("docs/seats.md is stale: run python3 tools/gen_seats_md.py")
            return 1
        print("docs/seats.md current")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote docs/seats.md: {len(teamlib.catalogue())} catalogue rows, {len(teamlib.MERGES)} merged seats, "
          f"{len(teamlib.DERIVED_ROLES)} new roles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
