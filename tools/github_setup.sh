#!/usr/bin/env bash
# why: set the GitHub repository up the way docs/maintaining.md describes, from files in this repo, so a
#      fresh repo and an existing one end in the same state
# writes: GitHub repository settings, labels and branch protection, only with --apply (the default prints)
# needs: gh, authenticated as an admin of the repo (gh auth login), and python3
#
#   tools/github_setup.sh                 print every call it would make; writes nothing
#   tools/github_setup.sh --apply         make those calls
#   tools/github_setup.sh --repo OWNER/NAME [--apply] [--no-homepage]   (--no-homepage until the project page is live)
#
# Safe to re-run: each call sets a value rather than adding one. It sets the description, homepage and
# topics; turns on issues, Discussions and private vulnerability reporting; creates or updates every
# label in .github/labels.json; and protects main: the check workflow's jobs must pass, no force pushes,
# no deletion. Admins may bypass, so a single maintainer is never locked out of their own repo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="fauzulkc/agent-team"
BRANCH="main"
APPLY=0
SET_HOMEPAGE=1
TOPICS=(claude-code claude-code-plugin ai-agents multi-agent agent-orchestration skills developer-tools)

usage() { sed -n '7,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --dry-run) APPLY=0 ;;
    --no-homepage) SET_HOMEPAGE=0 ;;  # until the project page is live
    --repo) [ $# -ge 2 ] || { echo "--repo needs OWNER/NAME" >&2; exit 2; }; REPO="$2"; shift ;;
    --repo=*) REPO="${1#--repo=}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
case "$REPO" in */*) ;; *) echo "--repo must be OWNER/NAME, got: $REPO" >&2; exit 2 ;; esac

# Print a call; make it only with --apply. With a second form, `run_input TEXT cmd...`, TEXT goes to stdin.
run() {
  printf '+'; printf ' %q' "$@"; printf '\n'
  if [ "$APPLY" = 1 ]; then "$@"; fi
}
run_input() {
  local input="$1"; shift
  printf '+'; printf ' %q' "$@"; printf ' <<JSON\n%s\nJSON\n' "$input"
  if [ "$APPLY" = 1 ]; then printf '%s' "$input" | "$@"; fi
}

# Everything below is read from the repo: the fact sheet (tools/export_facts.py writes it), the labels,
# and the check workflow's matrix, whose job names are the status checks main requires.
read_json() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d[sys.argv[2]])' "$@"; }
DESCRIPTION="$(read_json "$ROOT/docs/facts.json" description)"
HOMEPAGE="$(read_json "$ROOT/docs/facts.json" homepage)"
LABELS="$(python3 - "$ROOT/.github/labels.json" <<'PY'
import json, sys
for label in json.load(open(sys.argv[1], encoding="utf-8")):
    print("\t".join((label["name"], label["color"], label["description"])))
PY
)"
PROTECTION="$(python3 - "$ROOT/.github/workflows/check.yml" <<'PY'
import json, re, sys
text = open(sys.argv[1], encoding="utf-8").read()
versions = re.findall(r'"([^"]+)"', re.search(r"python-version:\s*\[([^\]]*)\]", text).group(1))
if not versions:
    sys.exit("no python-version matrix found in check.yml")
print(json.dumps({
    "required_status_checks": {"strict": False, "checks": [{"context": f"check ({v})"} for v in versions]},
    "enforce_admins": False,
    "required_pull_request_reviews": None,
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
}, indent=2))
PY
)"

if [ "$APPLY" = 1 ]; then
  command -v gh > /dev/null || { echo "gh is not installed: https://cli.github.com" >&2; exit 1; }
  gh auth status > /dev/null 2>&1 || { echo "gh is not signed in: run gh auth login" >&2; exit 1; }
  gh repo view "$REPO" > /dev/null || { echo "cannot see $REPO: create it and push main first" >&2; exit 1; }
  echo "Applying to $REPO."
else
  echo "Dry run for $REPO: printing every call, writing nothing. Re-run with --apply to make them."
fi

echo "# Description, homepage, topics, issues and Discussions"
topic_args=()
for topic in "${TOPICS[@]}"; do topic_args+=(--add-topic "$topic"); done
homepage_args=(); if [ "$SET_HOMEPAGE" = 1 ]; then homepage_args=(--homepage "$HOMEPAGE"); fi
run gh repo edit "$REPO" --description "$DESCRIPTION" "${homepage_args[@]}" "${topic_args[@]}" \
  --enable-issues --enable-discussions

echo "# Private vulnerability reporting (the Security tab's \"Report a vulnerability\")"
run gh api --method PUT "repos/$REPO/private-vulnerability-reporting" --silent

echo "# Labels from .github/labels.json (created, or updated when they exist)"
while IFS=$'\t' read -r name color description; do
  run gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force
done <<< "$LABELS"

echo "# Protect $BRANCH: the check jobs pass, no force pushes, no deletion; admins may bypass"
run_input "$PROTECTION" gh api --method PUT "repos/$REPO/branches/$BRANCH/protection" --input - --silent

if [ "$APPLY" = 1 ]; then
  echo "Done: $REPO has its description, homepage, ${#TOPICS[@]} topics, Discussions, private vulnerability reporting, $(printf '%s\n' "$LABELS" | wc -l | tr -d ' ') labels and a protected $BRANCH."
  echo "Still by hand: add the AGENT_TEAM_LEAK_WORDS secret (Settings > Secrets and variables > Actions)."
else
  echo "Dry run complete: nothing was written."
fi
