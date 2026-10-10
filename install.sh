#!/usr/bin/env bash
# why: install team-setup and team-reevaluate without the plugin system, by linking both from this clone into the global skills folders (the plugin is the preferred install: see README)
# owner: the maintainer
# writes: local (~/.claude/skills/{team-setup,team-reevaluate} and ~/.agents/skills/{team-setup,team-reevaluate} symlinks into this clone; removes seat-* links an install before 1.1.0 made into this clone)
# cost: $0
# never: overwrite a real (non-symlink) folder of the same name; remove a link that points anywhere but this clone
#
#     git clone https://github.com/fauzulkc/agent-team && ./agent-team/install.sh
#
# Run it from anywhere: every path is taken from this script's own folder. Run it again after moving the
# clone; updating is `git pull` in the clone, since the links point at it.
# team-reevaluate runs team-setup's scripts from ${CLAUDE_SKILL_DIR}/../team-setup, so both are linked side by side.
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -euo pipefail

REPO="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SKILLS=(team-setup team-reevaluate)
home_relative() { case "$1" in "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;; *) printf '%s' "$1" ;; esac; }

for skill in "${SKILLS[@]}"; do
  if [ ! -f "$REPO/skills/$skill/SKILL.md" ]; then
    echo "error: $REPO/skills/$skill/SKILL.md not found; run install.sh from inside an agent-team clone" >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "note: python3 was not found; the skills' scripts need Python 3.9 or newer"
elif ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  echo "note: $(python3 --version 2>&1) found; the skills' scripts need Python 3.9 or newer"
fi

mkdir -p "$HOME/.claude/skills" "$HOME/.agents/skills"
linked=()
skipped=()
for skill in "${SKILLS[@]}"; do
  made=0
  for target in "$HOME/.claude/skills/$skill" "$HOME/.agents/skills/$skill"; do
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      echo "skip: $(home_relative "$target") exists and is not a link; move it aside and run install.sh again to link $skill there"
      continue
    fi
    ln -sfn "$REPO/skills/$skill" "$target"
    echo "linked: $(home_relative "$target")"
    made=1
  done
  if [ "$made" = 1 ]; then linked+=("$skill"); else skipped+=("$skill"); fi
done

# Before 1.1.0 the seats were linked globally; since then team-setup copies them into each project, so a
# global seat link would duplicate them. Removed: a ~/.agents link into this clone, then the relative
# ~/.claude link those installs made beside it once it points at nothing. Any other seat link is kept.
for link in "$HOME"/.agents/skills/seat-* "$HOME"/.claude/skills/seat-*; do
  [ -L "$link" ] || continue
  case "$(readlink "$link")" in
    "$REPO/skills/seat-"*) ;;
    "../../.agents/skills/seat-"*) [ -e "$link" ] && continue ;;
    *) continue ;;
  esac
  rm "$link"
  echo "removed stale link: $(home_relative "$link")"
done

echo
if [ "${#linked[@]}" -gt 0 ]; then
  printf -v names '%s, ' "${linked[@]}"
  echo "Linked ${#linked[@]} skill(s) from $REPO: ${names%, }"
fi
if [ "${#skipped[@]}" -gt 0 ]; then
  printf -v names '%s, ' "${skipped[@]}"
  echo "Not linked, a real folder is in the way: ${names%, }"
  exit 1
fi
echo "Open a new Claude Code session, then say \"set up the team\" in any project."
