#!/usr/bin/env python3
"""Compose seat rulebooks that the catalogue doesn't hold: merged seats and derived (new or split) seats.

    seatgen.py merge  --team growth --seat Growth --mark 📈 --of sales,seo,social --out <dir>
    seatgen.py derive --team web --seat "Web engineer" --mark 🖥️ --base seat-frontend \\
                      --kind implementation --reports-to Engineering --scope "only apps/web/" --out <dir>

A MERGE is deterministic and complete: every section of every member rulebook is kept under
"As <member>", with a short header on holding several roles at once. It can be recomposed from
newer member rulebooks at any time (`scaffold.py --sync` does).

A DERIVE copies a base rulebook under the new seat's name and mark, adds the seat's scope to §0,
and puts an AUTHORING NEEDED block at the top: the session that created it rewrites the rulebook
for the role (references/seat-contract.md), then deletes the block. Until then the generator's
check and `scaffold.py` report it.
Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teamlib import SEATS_SRC, catalogue  # noqa: E402

AUTHORING_MARK = "AUTHORING NEEDED"
SECTION_RE = re.compile(r"^## (\d) · (.+)$", re.M)


def parse(skill_text: str) -> dict:
    fm = re.match(r"---\n(.*?)\n---\n", skill_text, re.S)
    body = skill_text[fm.end():] if fm else skill_text
    desc = re.search(r'^description:\s*"(.*)"\s*$', fm.group(1), re.M).group(1) if fm else ""
    h1 = re.search(r"^# (.+)$", body, re.M)
    loyalty = re.search(r"Single loyalty:\s*(.+?)\*\*", body, re.S)
    sections: dict[int, tuple[str, str]] = {}
    matches = list(SECTION_RE.finditer(body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[int(m.group(1))] = (m.group(2).strip(), body[m.end():end].strip())
    return {"description": desc.replace('\\"', '"'), "h1": h1.group(1) if h1 else "",
            "loyalty": re.sub(r"\s+", " ", loyalty.group(1).replace("**", "")).strip() if loyalty else "", "sections": sections, "body": body}


def first_sentence(desc: str) -> str:
    d = re.sub(r"^\S+\s", "", desc, count=1)  # drop the mark
    return d.split(". ")[0].rstrip(".")


def quote(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def compose_merge(team: str, seat: str, mark: str, members: list[str]) -> str:
    cat = catalogue()
    parsed = []
    for m in members:
        row = cat[m]
        parsed.append((row, parse((SEATS_SRC / row["skill"] / "SKILL.md").read_text(encoding="utf-8"))))
    roles = [r["seat"] for r, _ in parsed]
    role_list = ", ".join(roles[:-1]) + " and " + roles[-1] if len(roles) > 1 else roles[0]
    desc = (f"{mark} {seat}: one seat holding the {role_list} roles. Use for anything those seats handle: "
            + "; ".join(first_sentence(p["description"]) for _, p in parsed)
            + ". Use in a project whose docs/TEAM.md seats this role.")
    if len(desc) > 1000:
        desc = desc[:996].rsplit(" ", 1)[0] + "…"
    out = [f'---\nname: seat-{team}\ndescription: "{quote(desc)}"\n---\n',
           f"# {mark} {seat}\n",
           "**Single loyalty: each role below, held honestly at once.** "
           + " · ".join(f"*As {r['seat']}:* {p['loyalty']}" for r, p in parsed if p["loyalty"]) + "\n",
           f"<!-- COMPOSED by agent-team seatgen from {', '.join(r['skill'] for r, _ in parsed)}. "
           "Recomposed by `scaffold.py --sync` while unedited; edit freely to make it this project's own. -->\n",
           "**This seat holds several roles in one session**, because the project is small enough that "
           "separate seats would be overhead. Four rules come with that:\n"
           "- **Name the hat.** Every message and report says which role is speaking "
           f"(`{mark} {seat} (as {roles[0]})`). A decision in one role's register is recorded there.\n"
           "- **When the roles pull against each other, say so.** Name the conflict in your report and "
           "take it to the CEO; never settle it silently in favour of the role you were wearing.\n"
           "- **Checks stay independent.** If a check seat (Bar Raiser, Testing, User, Security) is held "
           "here, it never signs off work this same seat built; ask another seat's team to check it.\n"
           "- **Grow out of it.** When one role's work dominates, ask for a split (`team-reevaluate`).\n"]
    for n in range(7):
        title = next((p["sections"][n][0] for _, p in parsed if n in p["sections"]), f"Section {n}")
        out.append(f"## {n} · {title}\n")
        for row, p in parsed:
            if n in p["sections"]:
                body = p["sections"][n][1]
                body = re.sub(r"^### ", "#### ", body, flags=re.M)
                out.append(f"### As {row['mark']} {row['seat']}\n\n{body}\n")
    return "\n".join(out).rstrip() + "\n"


def compose_derive(team: str, seat: str, mark: str, base: str, kind: str, reports_to: str, scope: str,
                   register: str = "", sibling: str = "") -> str:
    text = (SEATS_SRC / base / "SKILL.md").read_text(encoding="utf-8")
    p = parse(text)
    base_mark, _, base_name = p["h1"].partition(" ")
    desc = (f"{mark} {seat}: {scope}. Derived from the {base_name} rulebook. "
            f"Use for this seat's work in a project whose docs/TEAM.md seats this role.")
    body = p["body"]
    body = body.replace(f"# {p['h1']}", f"# {mark} {seat}", 1)
    banner = (f"\n> **{AUTHORING_MARK}.** This rulebook was derived from `{base}` for a role the catalogue "
              f"doesn't hold. Before the seat works: rewrite it for **{seat}** following "
              f"`references/seat-contract.md` in the team-setup skill (research the role, keep the seven "
              f"sections, cite sources, tier names only), then delete this block. Kind: {kind}. Reports to: "
              f"{reports_to}. Scope: {scope}."
              + (f" Register: {register}." if register else "")
              + (f" Sibling seat: {sibling} (split the work by the scope above; hand off with ASK/HANDOFF)." if sibling else "")
              + "\n")
    body = re.sub(r"^(# .+\n)", lambda m: m.group(1) + banner, body, count=1, flags=re.M)
    scope_line = (f"\n**Scope of this seat:** {scope}."
                  + (f" Everything else in this role belongs to {sibling}." if sibling else "") + "\n")
    body = re.sub(r"^(## 0 · .+\n)", lambda m: m.group(1) + scope_line, body, count=1, flags=re.M)
    return f'---\nname: seat-{team}\ndescription: "{quote(desc)}"\n---\n' + body


def needs_authoring(skill_file: Path) -> bool:
    return skill_file.is_file() and AUTHORING_MARK in skill_file.read_text(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--team", required=True); m.add_argument("--seat", required=True)
    m.add_argument("--mark", required=True); m.add_argument("--of", required=True)
    m.add_argument("--out", type=Path, required=True)
    d = sub.add_parser("derive")
    for k in ("--team", "--seat", "--mark", "--base", "--kind", "--reports-to", "--scope"):
        d.add_argument(k, required=True)
    d.add_argument("--register", default=""); d.add_argument("--sibling", default="")
    d.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "merge":
        text = compose_merge(a.team, a.seat, a.mark, [x.strip() for x in a.of.split(",") if x.strip()])
    else:
        text = compose_derive(a.team, a.seat, a.mark, a.base, a.kind, a.reports_to, a.scope, a.register, a.sibling)
    dst = a.out / f"seat-{a.team}" / "SKILL.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    print(f"wrote {dst} ({text.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
