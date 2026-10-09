# Context pack: recurring invoices (cited by path in messages)

- Decision: DEC-2 (monthly and weekly only, no proration).
- Scope note: docs/team/product.md, "Recurring invoices".
- Schema: `invoices.recurrence` = `none | weekly | monthly`, `anchor_day` 1–31, clamped to month end.
- UI: list badge per P-3; schedule picker in the invoice form.
- Open: proration (reopen if a paying customer asks).
