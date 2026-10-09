#!/usr/bin/env bash
# why: install team-setup without the plugin system, by linking it into the global skills folders (the plugin is the preferred install: see README)
# owner: the owner
# writes: local (~/.agents/skills/team-setup and ~/.claude/skills/team-setup symlinks; removes stale seat-* links this script made before 1.1.0)
# cost: $0
# never: overwrite a real (non-symlink) skill folder of the same name
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
for target in "$HOME/.agents/skills/team-setup" "$HOME/.claude/skills/team-setup"; do
  if [ -e "$target" ] && [ ! -L "$target" ]; then echo "skip: $target exists and is not a link"; continue; fi
  if [ "$target" = "$HOME/.claude/skills/team-setup" ]; then ln -sfn "../../.agents/skills/team-setup" "$target"
  else ln -sfn "$REPO/skills/team-setup" "$target"; fi
done
# Seats are copied into each project by team-setup since 1.1.0; global seat links would duplicate them.
for l in "$HOME"/.agents/skills/seat-* "$HOME"/.claude/skills/seat-*; do
  [ -L "$l" ] && rm "$l" && echo "removed stale link: $l"
done
echo "team-setup linked. Open a new session, then say \"set up the team\" in any project."
