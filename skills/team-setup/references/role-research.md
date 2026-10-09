# Role research: how the best operator of each seat works at a fast startup (2026-10-07)

Two research-tier sweeps (web). Tags: **[read]** the sweep opened the page; **[found]** the page
surfaced in search with its content summarised; **[secondary]** a third-party write-up, not the
original; **[unverified]** a claim or figure the sweep could not confirm. Cite [read]/[found] as
sources; label [unverified] or leave it out.

## Cross-cutting
- Bezos one-way vs two-way doors: reversible decisions fast, irreversible slowly. 2015 letter via https://fs.blog/reversible-irreversible-decisions/ [secondary]
- Bezos "disagree and commit"; decide at ~70% of the information you wish you had; escalate misalignment early; "resist proxies: the process can become the thing". 2016 letter https://www.aboutamazon.com/news/company-news/2016-letter-to-shareholders [read]
- "Good intentions don't work. Mechanisms do." (Bezos) https://www.cnbc.com/2022/10/06/how-this-popular-jeff-bezos-quote-drives-amazons-climate-goals.html [secondary]
- Shape Up: appetite not estimates (ch.3 https://basecamp.com/shapeup/1.2-chapter-03 [read]); no backlog, betting table, circuit breaker (ch.7 https://basecamp.com/shapeup/2.1-chapter-07 [read]); scope hammering, "~" nice-to-haves, compare to baseline not ideal, "cutting scope isn't lowering quality" (ch.14 https://basecamp.com/shapeup/3.5-chapter-14 [read])
- Paul Graham, Do Things That Don't Scale http://paulgraham.com/ds.html [found]; Default Alive or Default Dead http://www.paulgraham.com/aord.html [found]
- Linear Method: small scope, ship often, principles over playbooks https://linear.app/method [found]
- Doshi LNO (Leverage / Neutral / Overhead; do overhead deliberately cheaply) https://www.news.aakashg.com/p/lno-framework-for-product-managers [secondary; original unverified]

## CEO
- One-way/two-way doors; disagree and commit at ~70% info; default alive; SPADE (Setting, People, Alternatives, Decide, Explain; one named decider) — Gokul Rajaram https://review.firstround.com/square-defangs-difficult-decisions-with-this-system-heres-how [found]

## Chief of Staff
- CEO's proxy and communication arm; ensures the CEO has current information from every function before it is asked — GitLab handbook https://handbook.gitlab.com/job-families/chief-executive-officer/chief-of-staff/ [found]
- Escalate misalignment early (Bezos 2016 [read]); keep overhead cheap: terse status + stop reason, not narrative (Doshi LNO [secondary])
- "Honest intermediary / integrator" (McKinsey) [unverified]

## Product
- Superhuman PMF engine: "very disappointed" survey, 40% target; segment to the most demanding users; roadmap half on what they love, half on what blocks the "somewhat disappointed" — Vohra https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit/ [read]
- Appetite not estimates; "Interesting. Maybe some day." as the default answer to a raw idea — Shape Up ch.3 [read]
- Hold the problem tightly, the solution loosely; MVP ridiculously simple, in weeks — Seibel https://ycombinator.com/library/Io-how-to-build-an-mvp [found]
- Resist proxies (Bezos 2016 [read])

## Engineering
- Work on what matters: existential first; avoid snacking (easy, low-impact) and preening (visible, low-impact) — Larson https://lethain.com/work-on-what-matters/ [read]
- Choose boring technology; ~3 innovation tokens — McKinley https://boringtechnology.club/ [found]
- Done means deployed; compare to the buyer's current baseline, not the ideal — Shape Up ch.14 [read]
- Small scope completable in 1–3 weeks; many small launches — Linear [found]

## Frontend engineer
- "The more your tests resemble the way your software is used, the more confidence they can give you"; integration-weighted testing trophy — Kent C. Dodds https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications [found]
- prefers-reduced-motion hook — Josh Comeau https://joshwcomeau.com/react/prefers-reduced-motion/ [found]
- UI motion under 300 ms; never animate keyboard-initiated / high-frequency actions — Emil Kowalski https://emilkowal.ski/ui/you-dont-need-animations [found]
- Ship the smallest slice — Linear [found]

## Testing
- Quarantine non-deterministic tests; ignored flakes train people to ignore real failures — Fowler https://www.martinfowler.com/articles/nonDeterminism.html [found]
- Test Desiderata: deterministic, behavioural, predictive, among 12 properties that pull against each other — Kent Beck https://newsletter.kentbeck.com/p/desirable-unit-tests [found]
- Production is part of testing; observability — Charity Majors https://www.honeycomb.io/blog/yes-i-test-in-production-and-so-do-you [found]
- A test count or coverage % is a proxy (Bezos 2016 [read])

## Platform
- Error budgets: 100% is the wrong target; ship while budget remains, freeze when spent — Google SRE "Embracing Risk" https://sre.google/sre-book/embracing-risk/ [read]
- Boring technology, fewest moving parts — McKinley [found]
- Deploy is the start of watching; canaries; owners in production — Majors https://www.infoq.com/presentations/testing-production-2018 [found]
- Mechanisms over good intentions (Bezos [secondary])

## Research
- Twyman's law: any figure that looks interesting or different is usually wrong (Kohavi: ~9 in 10 striking results were bugs) https://en.wikipedia.org/wiki/Twyman%27s_law [secondary]; https://www.antoinebuteau.com/lessons-from-ronny-kohavi/ [secondary]
- Data science hierarchy of needs: collect, store, clean before analytics before ML — Monica Rogati 2017 [secondary; original not opened]
- Segment before concluding; declare the denominator first (Superhuman 22% → 32% by narrowing users) — Vohra [read]
- Do just enough; overhead deliberately cheap — Doshi LNO [secondary]

## Bar Raiser
- An objective third party "not associated with the team" — Amazon https://www.aboutamazon.com/news/workplace/how-amazon-hires [read] (Amazon's page does NOT mention a veto: [unverified])
- Premortem: assume the project failed; list why — Gary Klein, HBR 2007 https://en.wikipedia.org/wiki/Pre-mortem [secondary]
- A recurring objection becomes a mechanism (Bezos [secondary])
- Judge against the buyer's current baseline, not perfection — Shape Up ch.14 [read]

## Scope Trimmer
- Scope hammering with "~"; "cutting scope isn't lowering quality" — Shape Up ch.14 [read]
- No backlog; betting table; work not shipped in one cycle is cancelled by default, returns only if championed — Shape Up ch.7 [read]
- Do things that don't scale; manual first for the first buyer — Graham [found]
- MVP ridiculously simple — Seibel [found]

## Compliance & Audit
- Data-protection law: firms under 250 still document processing that is not occasional, risky or special-category — data-protection regulator guidance [found; jurisdiction-specific, source dropped]
- Four-step data-protection plan for small firms (register, sort, rights, secure), proportionate to data volume and sensitivity — regulator and business-bank small-firm guide [found; jurisdiction-specific, source dropped]
- National open-data licence: attribution names the source and the date of last update; must not imply endorsement — the licence text [found; jurisdiction-specific, source dropped]
- Sole traders and some partnerships are individuals for marketing rules: a small-business record can be personal data — data-protection regulator, business-to-business marketing guidance [found; jurisdiction-specific, source dropped]

## Sales & Marketing
- Recruit the first customers by hand — Graham http://paulgraham.com/ds.html [found]
- Positioning from competitive alternatives → unique attributes → value → best-fit segment → category — April Dunford, Obviously Awesome (template https://miro.com/miroverse/april-dunfords-positioning-template) [found]
- Price on value; most YC companies under-charge (Harris, quoted) — Kevin Hale, YC Startup Pricing 101 https://ycombinator.com/library/6h-startup-pricing-101 [found] — NOTE: the price is the owner's; Sales brings value evidence to the CEO as a pricing case, never moves a price.
- Trial shape is a pricing decision (reverse trial) — Kyle Poyar https://www.growthunhinged.com/p/your-guide-to-reverse-trials [found]

## Design
- Start with a feature, not the layout; hierarchy by weight and colour, not only size — Refactoring UI (Wathan & Schoger) [book; summary found]
- Principles over playbooks; ship smaller — Linear https://linear.app/method [found]
- Five users per round find most problems — Nielsen https://www.nngroup.com/articles/why-you-only-need-to-test-with-5-users/ [found via secondary]

## Motion & Production
- Every animation answers "what is its purpose?"; UI motion under 300 ms; never animate high-frequency actions — Kowalski [found]
- Interruptible motion; remove motion that frequency makes slow — Rauno Freiberg https://rauno.me/craft/interaction-design [found]
- Purposeful, brief, precise, optional; never the only carrier of information — Apple HIG Motion https://developer.apple.com/design/human-interface-guidelines/motion [found]
- Social cuts: hook in 3 s, sound-off, captions on — https://vidico.com/news/facebook-video-ad-best-practices-that-actually-work-2026/ [found; the "85% muted" figure unverified]
- Story Spine (once upon a time… every day… one day… because of that… until finally) — Pixar / Emma Coats https://www.openculture.com/2013/03/pixars_22_rules_of_good_storytelling.html [found]

## SEO & Publicity
- Product–channel fit: "channels do not mold to products" — Brian Balfour https://brianbalfour.com/four-fits-growth-framework [found]
- New sites win low-difficulty long-tail queries — Ahrefs https://ahrefs.com/blog/low-competition-keywords [found]
- AI answer engines cite the top of the page and fresh pages; visibility rarely transfers between engines — Kevin Indig [secondary; figures unverified]
- Earn off-site mentions — Indig [unverified]
- "How did you hear about us?" self-reported attribution; dark-social visits log as direct — SparkToro via https://getrecast.com/hdyhau/ [found]

## Social Media Manager
- Zero-click content: the post delivers the full value natively — Amanda Natividad (SparkToro) https://metadata.io/?p=41973 [found]
- Fixed daily time; reply to comments right after posting and again ~1 h later; links after posting — Justin Welsh via https://joshspector.com/justin-welsh-linkedin-system/ [found]
- Recycle winners with a new hook — Welsh [secondary]

## Competition & Market
- The real competitor is the alternative, including spreadsheets, gut feel and doing nothing — Dunford [found]
- Bottom-up sizing: customers × price × frequency — Pear VC https://pear.vc/market-sizing-guide/ [found]
- Evidence = commitments (time, intros, money), not compliments; ask about past specifics — Rob Fitzpatrick, The Mom Test (summary https://mtlynch.io/book-reports/the-mom-test/) [found]
- Define the ICP from who would be very disappointed — Vohra [read]

## Customer Success
- Desired Outcome = Required Outcome + Appropriate Experience — Lincoln Murphy https://sixteenventures.com/desired-outcome [found]
- Define the activation event; shorten time to it [unverified summary of Lenny's material]
- Over-serve the first users; set them up in person ("Collison installation") — Graham [found] — NOTE: invites and sends stay the owner's.

## Funding, Revenue & Investment
- Default alive: spend, revenue, growth, cash — Graham http://paulgraham.com/aord.html [found]
- Fundraise in one focused sprint, then stop — Graham "How to Raise Money" https://paulgraham.com/fr.html [found via summaries]
- Advance assurance for an investor tax-relief scheme takes weeks and needs a named investor; file early — startup-legal guide [found; jurisdiction-specific, source dropped]
- A government innovation grant scheme reported paused for a fiscal year with targeted programmes replacing it — secondary write-ups [found; jurisdiction-specific, source dropped; the seat must capture and verify at the funder before acting]

## Payments & Company Legal
- A merchant of record is the legal seller and carries sales-tax liability — a merchant-of-record provider's own help page [found; vendor-specific, source dropped]
- Check seller eligibility against the provider's supported-countries list first — the provider's own page [found; vendor-specific, source dropped]
- A tax authority may set no registration threshold for non-established businesses; B2B services usually reverse-charged — tax authority registration manual [found; jurisdiction-specific, source dropped]
- With a payment processor you remain merchant of record; a merchant-of-record provider is the legal seller [secondary]

## User (persona tester)
- A morning a month; think-aloud; small and frequent — Steve Krug, Rocket Surgery Made Easy [summary found]
- Replay past specifics ("the last time I chose a vendor…"), never "would you use this?" — Fitzpatrick [found]
- Judge by the buyer's required outcome, not whether a feature works — Murphy [found]
- After ~5 walks on one path, change the persona or the task — Nielsen [found via secondary]
