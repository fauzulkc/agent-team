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
| 🛎️ | Chief of Staff | `seat-chief-of-staff` | `chief-of-staff` | owner-side | docs/team/tracker.md, docs/team/owner-questions.md | the owner | **always** when three or more seats run |
| 🎯 | Product | `seat-product` | `product` | director | docs/GOALS.md (goals, non-goals, scope) | CEO | there is a product with users |
| ⚙️ | Engineering | `seat-engineering` | `engineering` | director | engineering goals; what lands in code | CEO | **always** for a code project |
| 🖥️ | Frontend engineer | `seat-frontend` | `frontend` | implementation | the UI code paths | Engineering | there is a web or app UI |
| 🧪 | Testing | `seat-testing` | `testing` | director | docs/TEST-STANDARD.md (what counts as green) | CEO | there is a test suite worth guarding |
| 🛰️ | Platform | `seat-platform` | `platform` | director | docs/PLATFORM.md (environments, deploys, cost) | CEO | something is deployed or costs money to run |
| 🔬 | Research | `seat-research` | `research` | director | docs/HYPOTHESES.md, docs/LEARNINGS.md | CEO | claims rest on data, models or measurement |
| ⚖️ | Bar Raiser | `seat-bar-raiser` | `bar-raiser` | check | its findings, in docs/briefs/ | CEO | **always** — the independent check |
| ✂️ | Scope Trimmer | `seat-scope-trimmer` | `scope-trimmer` | check | its trim verdicts, in docs/briefs/ | CEO | the queue outgrows the team |
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

**Starter sets.**
- **Solo build** (a tool, a library, a prototype): CEO, Engineering, Testing, Bar Raiser.
- **Product** (people use it): add Chief of Staff, Product, Design, User, Frontend engineer if there is a UI.
- **Startup** (it will be sold): add Sales & Marketing, Platform, Customer Success, Scope Trimmer;
  then Research, Competition & Market, SEO & Publicity, Payments & Company Legal, Funding and
  Compliance & Audit as the work appears.
- **Content** (it publishes): Motion & Production, Social Media Manager, SEO & Publicity, Sales & Marketing.

Seat the smallest set that covers the work. A seat with no work is overhead; add it the day its work appears.
