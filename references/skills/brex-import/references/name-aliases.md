# Name Aliases

Confirmed Brex cardholder-name → Employee # (EE ID) mappings, for when the
Brex/Card-Mapping cardholder name differs from BambooHR's legal name in
Department Listing (e.g. a preferred first name: Brex "Zayn Moselhy" vs.
BambooHR "Zaynaldine Moselhy"). The `EE ID` column in the QBO Transactions
sheet looks up the cardholder name directly against Department Listing's
name-key column; a mismatch there resolves blank.

**Never auto-populated.** Every row here was confirmed by a human after
`runner.py finalize` surfaced it as an unmapped-EE-ID suggestion (single
unambiguous candidate: exact last name + Brex first name is a prefix of the
BambooHR first name) or as a flagged no-candidate case. Once confirmed,
`runner.py confirm-aliases` appends the row here and writes it into the
current run's "Name Aliases" tab so the deliverable resolves immediately —
future runs resolve automatically without asking again.

See `skills/brex-import/SKILL.md` → "Name reconciliation" for the full flow.

| Brex Name | EE ID | BambooHR Name | Confirmed | Note |
|---|---|---|---|---|
| Zayn Moselhy | 184 | Zaynaldine Moselhy | 2026-07-16 | Preferred first name vs BambooHR legal name; confirmed by Zayn |
| Michael Christinsen | 58 | Michael Christensen | 2026-07-16 | Spelling variant (Christinsen vs Christensen); confirmed by Zayn |
