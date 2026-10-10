# Getting help

## Read first

Most questions are answered in the docs:

| If you want to know | Read |
|---|---|
| how to install, seat a team and re-evaluate it | [README.md](README.md) |
| how the team is sized, how seats work and talk, the model tiers | [docs/how-it-works.md](docs/how-it-works.md) |
| what you'll be asked and what the team decides itself | [docs/owner-touchpoints.md](docs/owner-touchpoints.md) |
| what each of the 29 seats does, and when it is seated | [docs/seats.md](docs/seats.md) |
| what a whole run looks like, prompt by prompt | [examples/walkthrough.md](examples/walkthrough.md) |
| what a seated project's files look like | [examples/tally/](examples/tally/) |

## Where to ask

| You have | Go to |
|---|---|
| a question: how something works, why the team did what it did, how to fit it to your project | [Discussions](https://github.com/fauzulkc/agent-team/discussions), in **Q&A** |
| an idea you'd like to talk through before it becomes a request | [Discussions](https://github.com/fauzulkc/agent-team/discussions), in **Ideas** |
| a team you've seated and want to show | [Discussions](https://github.com/fauzulkc/agent-team/discussions), in **Show and tell** |
| a bug: a script failed, a file was written wrong, a skill did something its docs say it won't | [Issues](https://github.com/fauzulkc/agent-team/issues/new/choose), with the **Bug report** form |
| a concrete change to request | [Issues](https://github.com/fauzulkc/agent-team/issues/new/choose), with the **Feature request** form |
| a role no seat covers | [Issues](https://github.com/fauzulkc/agent-team/issues/new/choose), with the **Seat proposal** form |
| a security vulnerability | never a public issue: follow [SECURITY.md](SECURITY.md) |
| a conduct concern | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), under Enforcement |

## What helps an answer arrive

- The plugin version: `claude plugin list` (or the commit of your clone for an `install.sh` install).
- The exact phrase or command you used, and what came back.
- The shape of your project, not its code: languages, rough size, which apps it has. If the team is
  seated, the `size` and `signals` blocks of `docs/team/scan.json` describe it well; check them for
  private names before you paste.

Please leave out private code, customer data and secrets. An invented project that shows the same
thing is always welcome.

## Out of scope here

- Installing, signing in to or billing for Claude Code: see Anthropic's Claude Code documentation.
- Work inside your own project that the team is doing for you: that conversation belongs with your
  seats. Bring it here when the toolkit itself is the cause.

One person maintains agent-team. Questions and bugs are read in Discussions and Issues and answered
there, so everyone with the same question finds the answer.
