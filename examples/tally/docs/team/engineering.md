# ⚙️ Engineering: the project brief for Tally

**This seat's rulebook is the skill `seat-engineering`** (how the role thinks and works). **This file
is what the role needs to know about Tally.** A decision in [DECISIONS.md](../DECISIONS.md) outranks both.

## Owns here
- **Register:** engineering goals in `docs/GOALS.md` under `E-n`; what lands in code.
- **Paths:** `server/` (Node + Express API), `db/migrations/`, `scripts/`, `.github/workflows/`.

## Does not own here
- `web/` UI code: 🖥️ Frontend lands it (Engineering sets its queue).
- What counts as green: 🧪 Testing (`docs/TEST-STANDARD.md`).
- Deploys: the owner deploys until a decision says otherwise.

## Reports to
CEO

## Decisions that bind this seat
- DEC-2: recurring invoices are monthly and weekly only, no proration.
- DEC-3: the recurring-invoices switch is on for everyone; never remove the switch without a decision.

## Project facts this seat relies on
- Test: `npm test` (server, uncached: `npm test -- --no-cache`), `npm run test:web` (Frontend's leg).
- Local app: `npm run dev` → `http://localhost:3000`, health at `/healthz` (measured 2026-03-02).
- Database: Postgres 16 in Docker (`docker compose up db`); migrations with `npm run migrate`.
- CI: `.github/workflows/ci.yml` runs lint, server tests and web tests on every push.

## Traps paid for
- A health check 200 does not mean the new build is serving: the dev server keeps the old process
  after a failed reload. Probe the behaviour the change made (2026-03-04, the scheduler fix).
- Dates: "the 31st of every month" must clamp to the month's last day; a test pins February
  (`server/test/schedule.test.ts`, 2026-03-04, Bar Raiser finding).

## Done means here
Server and web tests green uncached; Bar Raiser PASS on the running app; behind a switch if it is
customer-facing; the owner told, in words, what changed for customers.
