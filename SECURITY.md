# Security policy

agent-team runs inside other people's projects. Its scripts write files into a user's repository,
and its rulebooks steer AI sessions that can run commands there. A flaw in either can cost a user
their work or put words in public they never approved, so those reports come first.

## What counts as a vulnerability

**The scripts write into a user's project.** `scan.py`, `plan.py`, `scaffold.py`, `seatgen.py`,
`reevaluate.py` and the copied `scripts/gen-team-agents.py` read a repository and write `docs/`,
`.claude/skills/`, `.claude/agents/` and `scratchpad/team/` inside it. `install.sh` writes links into
the user's global skills folders. Report anything where they:

- **write outside the place they were pointed at**: a seat name, team key, app folder, plan file,
  roster row or symlink that sends a write, copy or link outside the project root (or, for
  `install.sh`, outside `~/.agents/skills/` and `~/.claude/skills/`);
- **overwrite or delete a user's files** they promise to keep: a project's own `seat-<team>` rulebook
  (never synced, overwritten or deleted), a retired seat's rulebook that was derived, edited,
  untracked or the project's own (archived to `docs/team/retired/`, never deleted), the owner's
  recorded decisions in `docs/DECISIONS.md`, or a real skill folder that `install.sh` should skip;
- **turn text into something else**: content from a repository, a scan, a plan or a roster row that
  reaches a generated file as more than text, such as an extra frontmatter field or a wider tool list
  in a generated agent, or that ends up in a command the scripts run.

**A rulebook that could steer an agent to an outward act without the owner.** Every seat rulebook
and the shared protocol in `skills/team-setup/templates/TEAM.md` keep publishing, posting, emailing
people, spending, signing, legal determinations, irreversible acts and pushes the owner has not
cleared behind the owner's yes. Wording in a shipped rulebook, template or generated file that lets a
seat or its workers take one of those steps on their own is a vulnerability, even when it reads as
an ordinary sentence.

## What does not

- **Claude Code itself**: report it to Anthropic through its own disclosure process.
- **Rulebooks a project wrote or edited** after setup: they belong to that project, and the scripts
  keep them as they are by design.
- **An action the owner told a seat to take.** The owner's word is the decision, recorded as such.
- **A seat's judgement inside its reversible scope** (a poor plan, a weak review). Open a bug or a
  discussion for those.

## Supported versions

| Version | Supported |
|---|---|
| The latest minor release (the newest `## X.Y.Z` heading in [CHANGELOG.md](CHANGELOG.md)) | Yes |
| Any older minor release | No |

Fixes ship as a patch on the latest minor line. Update an installed plugin with
`claude plugin marketplace update agent-team`, then `claude plugin update agent-team@agent-team`;
with an `install.sh` install, `git pull` in your clone. A seated project keeps its own copy of
`scripts/gen-team-agents.py`, so a fix to that file names the copy step in its release notes.

## How to report

Report privately through GitHub's private vulnerability reporting: open the repository's
**Security** tab and choose **Report a vulnerability**
([direct link](https://github.com/fauzulkc/agent-team/security/advisories/new)). Please do not open a
public issue, discussion or pull request for a vulnerability.

A useful report holds:

- the plugin version (`claude plugin list`), or the commit of your clone;
- the command you ran or the phrase you said to Claude Code (*"set up the team"*, *"retire Design"*);
- the smallest project shape that shows it: file and folder names, a manifest, a roster row (an
  invented project is ideal; never send private code or secrets);
- what was written, overwritten, deleted or done, and where;
- what someone would need, and what they would gain, to use it against a user.

If the **Report a vulnerability** button is missing, open an issue that says only that you have a
security report and would like a private channel, with no details, and the maintainer will set one up.

## What happens next

1. The maintainer acknowledges the report in the private advisory and works with you there.
2. The maintainer reproduces it on an invented project and agrees the impact with you. A report that
   turns out not to be a vulnerability is closed in the advisory with the reason, and you are welcome
   to open it as a public issue.
3. The fix is built in the advisory's private fork, with a test in `tests/` that fails without it,
   and every check passes before it lands.
4. A patch release ships with a `CHANGELOG.md` entry, and the advisory is published with the
   affected and fixed versions, a CVE where one is warranted, and credit to you unless you ask to stay
   anonymous.

Please keep the details private until the advisory is published. The maintainer is one person and
handles reports as they arrive, most severe first.
