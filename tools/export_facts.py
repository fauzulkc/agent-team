#!/usr/bin/env python3
"""Generate docs/facts.json, the fact sheet a website or a post reads, from the repo's own sources.

    python3 tools/export_facts.py            write docs/facts.json
    python3 tools/export_facts.py --check    exit 1 when docs/facts.json differs from what it would write

Every value comes from code or config, never from a hand-kept list:
  name, version, licence    .claude-plugin/plugin.json (repository and homepage too, when it names them)
  description               .claude-plugin/marketplace.json, the plugin's entry
  install                   the commands for the repository, marketplace and plugin names above
  skills                    skills/*/SKILL.md (team-setup first): the mark and the description up to "Use when"
  seats                     teamlib.catalogue() (the catalogue table), and each rulebook's description up
                            to "Use when" for `what`, the same text docs/seats.md shows
  merged_seats              teamlib.MERGES
  derived_roles             teamlib.DERIVED_ROLES (keyed by the scan signal that raises each)
  tiers                     TIERS in skills/team-setup/scripts/gen-team-agents.py, cheapest first
  counts                    the lengths of the lists above
Keys are stable: adding a key is fine; renaming or removing one breaks whatever reads the file, so it
is a major change. The file carries no timestamp, so it is byte-stable and --check can compare it.
check.py runs --check. Standard library only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "facts.json"
SCRIPTS = ROOT / "skills" / "team-setup" / "scripts"
for p in (SCRIPTS, ROOT / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import gen_seats_md  # noqa: E402  (job(): a rulebook's description up to "Use when")
import teamlib  # noqa: E402

# The published home of the repo. plugin.json's `repository` and `homepage` win when it carries them.
REPOSITORY = "https://github.com/fauzulkc/agent-team"
HOMEPAGE = "https://fauzul.com/agent-team"
BLOG = "https://fauzul.com/blog/agent-team"
# The tiers' order on the climb: edits go quick, execution, build; reading goes scout, check, research, deep.
TIER_ORDER = ("quick", "scout", "check", "execution", "build", "research", "deep")


def load_tiers() -> dict:
    spec = importlib.util.spec_from_file_location("gen_team_agents", SCRIPTS / "gen-team-agents.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # the script's main() is guarded; importing it writes nothing
    return module.TIERS


def plain(cell: str) -> str:
    """A catalogue cell as plain text: no bold markers or code ticks."""
    return re.sub(r"\*\*|`", "", cell).strip()


def url(value, fallback: str) -> str:
    """plugin.json's repository may be a string or {"url": ...}."""
    if isinstance(value, dict):
        value = value.get("url")
    return value.rstrip("/").removesuffix(".git") if isinstance(value, str) and value else fallback


def skill_summary(skill_md: Path) -> tuple[str, str]:
    """(mark, what it does) from a top-level skill's description."""
    text = skill_md.read_text(encoding="utf-8")
    fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
    desc = re.search(r'^description:\s*"(.*)"\s*$', fm.group(1), re.M | re.S).group(1).replace('\\"', '"')
    mark, _, rest = desc.partition(" ")
    m = re.search(r"\.\s+Use (when|for|on|in|before|whenever|to)\b", rest)
    return mark, (rest[: m.start() + 1] if m else rest).strip()


def facts() -> dict:
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    name = plugin["name"]
    entry = next((p for p in marketplace.get("plugins", []) if p.get("name") == name), marketplace["plugins"][0])
    repository = url(plugin.get("repository"), REPOSITORY)
    slug = repository.split("github.com/", 1)[-1]
    clone_dir = slug.rsplit("/", 1)[-1]

    skills = []
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md"), key=lambda f: (f.parent.name != "team-setup", f.parent.name)):
        mark, summary = skill_summary(skill_md)
        skills.append({"name": skill_md.parent.name, "mark": mark, "summary": summary})

    seats = [{"team": row["team"], "mark": row["mark"], "seat": row["seat"], "skill": row["skill"],
              "kind": row["kind"], "reports_to": plain(row["reports_to"]), "register": plain(row["register"]),
              "what": gen_seats_md.job(row["skill"], row["mark"]), "when": plain(row["when"])}
             for row in teamlib.catalogue().values()]
    merged = [{"team": team, "mark": m["mark"], "seat": m["seat"], "kind": m["kind"], "holds": list(m["of"]),
               "why": m["why"]} for team, m in teamlib.MERGES.items()]
    derived = [{"signal": signal, "team": d["team"], "mark": d["mark"], "seat": d["seat"], "kind": d["kind"],
                "base": d["base"], "reports_to": d["reports_to"], "scope": d["scope"]}
               for signal, d in teamlib.DERIVED_ROLES.items()]
    tiers_src = load_tiers()
    order = [t for t in TIER_ORDER if t in tiers_src] + [t for t in tiers_src if t not in TIER_ORDER]
    tiers = [{"tier": t, "model": tiers_src[t]["model"], "effort": tiers_src[t]["effort"],
              "agent": "<team>-worker" if t == "execution" else f"team-{t}"} for t in order]

    return {
        "name": name,
        "version": plugin["version"],
        "license": plugin.get("license", "MIT"),
        "repository": repository,
        "homepage": plugin.get("homepage") or HOMEPAGE,
        "blog": BLOG,
        "description": entry.get("description", plugin.get("description", "")),
        "install": {
            "one_line": [f"claude plugin install {name} --marketplace {slug}"],
            "plugin": [f"claude plugin marketplace add {slug}",
                       f"claude plugin install {name}@{marketplace['name']}"],
            "in_session": [f"/plugin marketplace add {slug}", f"/plugin install {name}@{marketplace['name']}"],
            "manual": [f"git clone {repository}", f"./{clone_dir}/install.sh"],
            "update": [f"claude plugin marketplace update {marketplace['name']}",
                       f"claude plugin update {name}@{marketplace['name']}"],
        },
        "skills": skills,
        "seats": seats,
        "merged_seats": merged,
        "derived_roles": derived,
        "tiers": tiers,
        "counts": {"catalogue_seats": len(seats), "merged_seats": len(merged), "derived_roles": len(derived),
                   "skills": len(skills), "tiers": len(tiers)},
    }


def render() -> str:
    return json.dumps(facts(), indent=2, ensure_ascii=False) + "\n"


def stale() -> bool:
    return not OUT.is_file() or OUT.read_text(encoding="utf-8") != render()


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate docs/facts.json from the repo's own sources.")
    ap.add_argument("--check", action="store_true", help="exit 1 when docs/facts.json is stale")
    args = ap.parse_args()
    if args.check:
        if stale():
            print("docs/facts.json: stale; run python3 tools/export_facts.py")
            return 1
        print("docs/facts.json: current")
        return 0
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
