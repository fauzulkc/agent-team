# The seats

Every seat in the catalogue, with its one-line job (from its rulebook's description), its kind,
whom it reports to, and when a project needs it. `team-setup` proposes the smallest set; add the
rest the day their work appears.

| | Seat | Open with | Kind | Reports to | What it does | Seat it when |
|---|---|---|---|---|---|---|
| 🧭 | **CEO** | `/seat-ceo` | owner-side | the owner | The CEO seat: the business decision taker who owns the decision register, the queue and the refusals. | **always** |
| 🛎️ | **Chief of Staff** | `/seat-chief-of-staff` | owner-side | the owner | The owner's chief of staff: the session the owner talks to, which advises, informs the CEO with evidence, relays the CEO's answer back, keeps the tracker and the owner-questions list, receives every seat's stop line and routes each unblock. | **always** when three or more seats run |
| 🎯 | **Product** | `/seat-product` | director | CEO | The Product director: keeps goals, scope and non-goals in sync with what the product does for its buyer, toward product-market fit. | there is a product with users |
| ⚙️ | **Engineering** | `/seat-engineering` | director | CEO | The Engineering director: sets engineering standards, dispatches workers on the critical path, reviews what returns, and rules whether work may land or a gate may be called green. | **always** for a code project |
| 🖥️ | **Frontend engineer** | `/seat-frontend` | implementation | Engineering | Frontend engineer: the implementation seat that builds the UI under Engineering's scope, Design's form, Motion's rulings and Sales's words. | there is a web or app UI |
| 🧪 | **Testing** | `/seat-testing` | director | CEO | The Testing director: owns whether a green line means exactly what it says, and the tests themselves. | there is a test suite worth guarding |
| 🛰️ | **Platform** | `/seat-platform` | director | CEO | Platform: owns environments, deploy and rollback mechanics, secrets by name, monitoring, logs, the error budget, cost and vendors, backups of what git does not carry, and the tools index. | something is deployed or costs money to run |
| 🔬 | **Research** | `/seat-research` | director | CEO | The Research director: probes claims against the running system, owns the hypothesis record, and corrects the record in both directions. | claims rest on data, models or measurement |
| ⚖️ | **Bar Raiser** | `/seat-bar-raiser` | check | CEO | The Bar Raiser: the independent check that holds the standard before work ships, by re-measuring claims, gates and "done" against the running system and premortem-ing a plan before dispatch. | **always** — the independent check |
| ✂️ | **Scope Trimmer** | `/seat-scope-trimmer` | check | CEO | The Scope Trimmer: a check seat that cuts everything not on the shortest measured path to a paying customer, and proposes each cut for the CEO to rule. | the queue outgrows the team |
| 📐 | **Design** | `/seat-design` | director | CEO | Design: the seat that owns form the way the voice rules own words, through numbered design rulings and citable patterns. | anything a person looks at |
| 🎬 | **Motion & Production** | `/seat-motion` | director | CEO | Motion & Production: governs how anything moves (numbered motion rulings) and makes the moving outward assets (product loop, demo and launch videos, explainers, social cuts, rendered stills, sound) and their render pipeline. | video, animation or UI motion matters |
| 💼 | **Sales & Marketing** | `/seat-sales` | director | CEO | Sales & Marketing: the seat that owns every outward word, the order true things are said in, positioning, the first buyers and the pricing case. | it will be sold, or words go outward |
| 📣 | **SEO & Publicity** | `/seat-seo` | director | CEO | The SEO & Publicity director: owns measured reach that turns into sign-ups: the funnel by source, the angle ledger, discoverability and bold bets. | people must find it |
| 💬 | **Social Media Manager** | `/seat-social` | manager | SEO & Publicity (timing), Sales (words) | The Social Media Manager: runs the social channels day to day under two directors (words: Sales; slot, cadence, angle ledger: SEO & Publicity). | there are social channels to run |
| ♟️ | **Competition & Market** | `/seat-competition` | director | CEO | The Competition & Market director: keeps the competitor and alternatives record, sizes the market bottom-up, gathers ICP evidence, scans for new data sources and checks every comparative claim. | there are buyers with alternatives |
| 🤝 | **Customer Success** | `/seat-customer-success` | director | CEO | The Customer Success director: the customer's champion inside the team, owning the journey after the first click (join, wait, invite, first session, follow-up, return), the demand ledger, member health and the time from join to first answer. | there are users or testers |
| 🏦 | **Funding, Revenue & Investment** | `/seat-funding` | director | CEO | Funding, Revenue & Investment: keeps the register of where money can come from (grants, programmes, prizes, credits, investors), the deadline calendar, the use-of-funds plan and the runway arithmetic. | money must be raised or runway matters |
| 💳 | **Payments & Company Legal** | `/seat-payments` | director | CEO | Payments & Company Legal: owns the payments register (which channel takes which price line, from which region, on what fees, limits and approval times), the compliance of receiving money in the founder's country, tax by buyer type, the legal pages a platform requires, and entity advice. | it will take money |
| 🗂️ | **Compliance & Audit** | `/seat-compliance` | director | CEO | The Compliance & Audit director: owns the internal record of what the product does not answer and why, the licence register, the credits licences require, the source-claim check and the personal-data rows. | third-party data, licences or personal data |
| 👤 | **User** | `/seat-user` | check | CEO | The User: the buyer, not the builder. | there is something a person can use |

**Kinds.** *Owner-side* seats speak for or to you. *Directors* own a register and rule inside it. The
*manager* runs a daily operation under directors. The *implementation* seat builds under a director's
scope. *Checks* challenge other seats' work and own no product register.

**Starter sets.** Solo build: CEO, Engineering, Testing, Bar Raiser. Product with users: add Chief of
Staff, Product, Design, User, and Frontend if there is a UI. Startup: add Sales, Platform, Customer
Success, Scope Trimmer, then Research, Competition, SEO, Payments, Funding and Compliance as the work
appears. Content: Motion, Social, SEO, Sales.
