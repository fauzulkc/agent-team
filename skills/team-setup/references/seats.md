# The seat catalogue

Every seat the team can seat, with its mark, its global skill, its worker name, its kind, the
register it keeps by default, whom it reports to, and when a project needs it. `team-setup` picks
from this list; the project's `docs/TEAM.md` roster is the copy that binds.

**Kinds.** *Owner-side* seats speak for or to the owner. *Directors* own a register and rule inside
it. The *manager* runs a daily operation under directors. The *implementation* seat builds under a
director's scope. *Checks* challenge other seats' work and own no product register.

| Mark | Seat | Skill | Team | Kind | Default register | Reports to | Seat it when |
|---|---|---|---|---|---|---|---|
| 🧭 | CEO | `seat-ceo` | `ceo` | owner-side | docs/DECISIONS.md (the decision register, the queue, milestones) | the owner | **always** |
| 🛎️ | Chief of Staff | `seat-chief-of-staff` | `chief-of-staff` | owner-side | docs/team/tracker.md, docs/team/owner-questions.md | the owner | **always** when five or more other seats run (seven in the lean option) |
| 🎯 | Product | `seat-product` | `product` | director | docs/GOALS.md (goals, non-goals, scope) | CEO | there is a product with users |
| ⚙️ | Engineering | `seat-engineering` | `engineering` | director | engineering goals; what lands in code | CEO | **always** for a code project |
| 🖥️ | Frontend engineer | `seat-frontend` | `frontend` | implementation | the UI code paths | Engineering | there is a web or app UI |
| 🧪 | Testing | `seat-testing` | `testing` | director | docs/TEST-STANDARD.md (what counts as green) | CEO | there is a test suite worth guarding |
| 🛰️ | Platform | `seat-platform` | `platform` | director | docs/PLATFORM.md (environments, deploys, cost) | CEO | something is deployed or costs money to run |
| 🔬 | Research | `seat-research` | `research` | director | docs/HYPOTHESES.md, docs/LEARNINGS.md | CEO | claims rest on data, models or measurement |
| ⚖️ | Bar Raiser | `seat-bar-raiser` | `bar-raiser` | check | its findings, in docs/briefs/ | CEO | **always** — the independent check |
| ✂️ | Scope Trimmer | `seat-scope-trimmer` | `scope-trimmer` | check | its trim verdicts, in docs/briefs/ | CEO | ten or more other seats run: the queue outgrows the team |
| 📐 | Design | `seat-design` | `design` | director | docs/DESIGN.md (design rulings and patterns) | CEO | anything a person looks at |
| 🎬 | Motion & Production | `seat-motion` | `motion` | director | docs/MOTION.md, the render pipeline | CEO | video, animation or UI motion matters |
| 💼 | Sales & Marketing | `seat-sales` | `sales` | director | docs/PRICING.md, docs/POSITIONING.md, the outward copy source | CEO | it will be sold, or words go outward |
| 📣 | SEO & Publicity | `seat-seo` | `seo` | director | docs/REACH.md (funnel by source, angles, discoverability) | CEO | people must find it |
| 💬 | Social Media Manager | `seat-social` | `social` | manager | the posting-day packages and post log | SEO & Publicity (timing), Sales (words) | there are social channels to run |
| ♟️ | Competition & Market | `seat-competition` | `competition` | director | docs/research/market.md (competitors and alternatives) | CEO | there are buyers with alternatives |
| 🤝 | Customer Success | `seat-customer-success` | `customer-success` | director | docs/DEMAND.md (what people ask for) | CEO | there are users or testers |
| 🏦 | Funding, Revenue & Investment | `seat-funding` | `funding` | director | docs/FUNDING.md | CEO | money must be raised or runway matters |
| 💳 | Payments & Company Legal | `seat-payments` | `payments` | director | docs/PAYMENTS.md | CEO | it will take money |
| 🗂️ | Compliance & Audit | `seat-compliance` | `compliance` | director | docs/AUDIT.md, licence and data registers | CEO | third-party data, licences or personal data |
| 👤 | User | `seat-user` | `user` | check | its walk findings, in docs/research/ | CEO | there is something a person can use |
| 📱 | Mobile engineer | `seat-mobile` | `mobile` | implementation | the mobile app code | Engineering | there is an iOS, Android or cross-platform app |
| 🧠 | ML engineer | `seat-ml` | `ml` | director | models, training and evaluation code; the eval register | CEO | models are trained, evaluated or prompted |
| 🗄️ | Data engineer | `seat-data` | `data` | implementation | pipelines, schemas, the warehouse | Engineering | data pipelines or a warehouse exist |
| 🔐 | Security | `seat-security` | `security` | check | docs/SECURITY.md (threat model, findings) | CEO | there is auth, payments or personal data |
| 📚 | Docs writer | `seat-docs` | `docs` | implementation | the docs site, guides, API reference, changelog | Product | there is a docs site, a public API or a library |
| 🌱 | Community & DevRel | `seat-community` | `community` | director | CONTRIBUTING, issues and discussions, release notes | CEO | it is open source with outside contributors |
| 🎮 | Game designer | `seat-game-design` | `game-design` | director | the game design doc (loop, mechanics, economy, game rulings) | CEO | it is a game |
| 🌐 | Localization | `seat-i18n` | `i18n` | implementation | locale files and the string catalogue | Product | the product ships in more than one language |

**Other seats**, in the two coordination rows above, means every seat except the Chief of Staff and
the Scope Trimmer; a merged, split or derived seat counts as one. The planner and the re-evaluation
apply the same thresholds.

**Composed seats.** Setup and re-evaluation compose seats in exactly three ways (the scripts hold the
lists: `MERGES` and `DERIVED_ROLES` in `scripts/teamlib.py`, the splits in `scripts/plan.py`):
- **Merge**, for a small project: one session holds several roles. 📈 Growth (Sales & Marketing, SEO &
  Publicity, Social Media Manager); 🎨 Product & Design; 🔧 Engineering & Platform (not past 2,000 code
  files); 🛡️ Quality (Testing, Bar Raiser); 💰 Money (Funding, Payments); 📜 Legal & Compliance
  (Payments, Compliance); 🧮 Data & ML; 🫱 Customer (Customer Success, Community & DevRel). A merge needs
  two members present, and two merges never share a member. A check seat joins only a check merge
  (Quality, formed at setup); a merge proposed after setup never holds the CEO or the Bar Raiser.
- **Split**: the Frontend engineer becomes one seat per UI app (up to four) when the repo has two or
  more UI apps, in the full option or on a large project. Each split seat names its siblings.
- **Derive**: a role no catalogue row covers (🔌 Hardware & firmware engineer, ⛓️ Smart-contract
  engineer, 🖱️ Desktop engineer, 🧷 Browser-extension engineer) is copied from a base rulebook into the
  project's `.claude/skills/seat-<team>/` and authored from the seat contract before anyone acts under it.

**Starter sets.**
- **Solo build** (a tool, a library, a prototype): CEO, Engineering, Testing, Bar Raiser.
- **Product** (people use it): add Chief of Staff, Product, Design, User, Frontend engineer if there is a UI.
- **Startup** (it will be sold): add Sales & Marketing, Platform, Customer Success, Scope Trimmer;
  then Research, Competition & Market, SEO & Publicity, Payments & Company Legal, Funding and
  Compliance & Audit as the work appears.
- **Content** (it publishes): Motion & Production, Social Media Manager, SEO & Publicity, Sales & Marketing.

Seat the smallest set that covers the work. A seat with no work is overhead; add it the day its work appears.
