#!/usr/bin/env bash
# why: install team-setup and team-reevaluate without the plugin system, by linking both into the global skills folders (the plugin is the preferred install: see README)
# owner: the owner
# writes: local (~/.agents/skills/{team-setup,team-reevaluate} and ~/.claude/skills/{team-setup,team-reevaluate} symlinks; removes stale seat-* links this script made before 1.1.0)
# cost: $0
# never: overwrite a real (non-symlink) skill folder of the same name
# team-reevaluate runs team-setup's scripts from ${CLAUDE_SKILL_DIR}/../team-setup, so both are linked side by side.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
for skill in team-setup team-reevaluate; do
  for target in "$HOME/.agents/skills/$skill" "$HOME/.claude/skills/$skill"; do
    if [ -e "$target" ] && [ ! -L "$target" ]; then echo "skip: $target exists and is not a link"; continue; fi
    if [ "$target" = "$HOME/.claude/skills/$skill" ]; then ln -sfn "../../.agents/skills/$skill" "$target"
    else ln -sfn "$REPO/skills/$skill" "$target"; fi
    echo "linked: $target"
  done
done
# Seats are copied into each project by team-setup since 1.1.0; global seat links would duplicate them.
for l in "$HOME"/.agents/skills/seat-* "$HOME"/.claude/skills/seat-*; do
  if [ -L "$l" ]; then rm "$l"; echo "removed stale link: $l"; fi
done
echo "team-setup and team-reevaluate linked. Open a new session, then say \"set up the team\" in any project."
