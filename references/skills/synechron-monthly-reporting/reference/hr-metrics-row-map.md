# HR / Metrics report map — "HR Template" workbook

Verified against `HR_Template_June26.xlsx`. Five sheets: `Bench-AO`, `Open Hired`,
`Gender Diversity`, `HCMIX`, `New Metrics`. Each sheet is a small dated table — one row of data
per month, appended/replaced (**confirm with the human whether each run appends a new row or
overwrites the current month's row** before the first real run; not yet confirmed).

## Bench-AO sheet

| Col | Field | Source |
|---|---|---|
| A | Date | Month-end date |
| B | Bench | BambooHR billable="Yes" active employees **not currently logging hours against any active SOW** in the POC file (`Employee Level`/`Employee Utilization` tabs) — i.e., signed/assigned but the customer hasn't onboarded them yet. Not a single ready-made source; a cross-reference. Legitimately 0 most months. |
| C | Awaiting Onboarding | Same SOW-based concept as Bench, from a different angle — human confirmed this can be left as **0/N/A for now**, not fully built out. |

## Open Hired sheet

| Col | Field | Source |
|---|---|---|
| A | Date | Month-end |
| B | Open Positions | Ashby — count of open job postings |
| C | New Joiners | BambooHR — hire date within the reporting month |
| (rows 7+) | "Joined since" name list | BambooHR — names of the New Joiners |

## Gender Diversity sheet

| Col | Field | Source |
|---|---|---|
| B | Gender Diversity % | BambooHR `gender` field, % of active headcount (Male / Female / Unspecified) |
| C | Target | **Static** — a company goal (e.g. "70% M \| 30% F"), not computed. Carry forward unchanged unless a human updates it. |

## HCMIX sheet

| Col | Field | Source |
|---|---|---|
| B-D | Onsite / Nearshore / Offshore Headcount | BambooHR Department Listing — same region classification as the main dashboard (rows 26-37). RapDev headcount has historically been ~100% Onsite. |
| E-G | Same, as % of total | Formula off B-D |
| — | "Excluded in count" | **Always exclude**: the person "Angel" (specific individual, confirm current full name/employee # before first real run), Interns, Contractors. Also exclude anyone "signed but not joined" — determine via BambooHR hire date being in the future relative to the report date. |

## New Metrics sheet (lettered sections A-I)

| # | Metric | Source | Status |
|---|---|---|---|
| A | New clients won this month + $ | Unconfirmed — column B in the source file shows `#VALUE!`, a broken formula reference from wherever this was previously copied from. Candidates: HubSpot closed-won deals, or QBO new customers with first invoice this month. | **Manual "Please Update" until a human confirms the source.** |
| B | Synergy Revenue (Hard/Soft credit, this Q vs. last Q) | No connected system tracks this. | Manual. |
| (unlabeled) "Soft Revenue Alignment by BU" | Breakdown by Synechron business unit (NY, Charlotte, UK, ME, ANZ, Paris, Asia, Insurance, India, Salesforce Platform, Dreamix) | Looks like Synechron-side org data RapDev likely doesn't have visibility into. | Manual/Synechron-supplied. |
| C | Backlog (sold, undelivered work $) by month | **RapDev's existing weekly KPI report** (human-supplied, same pattern as the POC file attachment). Exploring whether ServiceNow project data reaches this directly is a possible future enhancement — not a dependency for this skill's first version. | Manual attach for now. |
| D | CSAT scores (TTM) | No connected system. | Manual. |
| E | % new work sourced via Platform vs. direct (SN/DD/Total) | Unclear — source file shows all values as `1` (100%), looks like a placeholder/stub rather than real data. | Manual until a human gives a source. |
| F | New certifications (SN/DD) | No connected system (unless BambooHR has a custom field for this — not confirmed). | Manual. |
| G | % of projects fixed-cost vs. T&M (SN/DD/Total) | **POC file, `SOW level` — column G (Project Type) × column H (SN/DD)**. Same source columns as dashboard Unbilled AR. Confirm weighting (by $ or by count) with a human the first time this runs for real — not yet confirmed. | Buildable. |
| H | Attrition + % Voluntary (this Q vs. last Q) | BambooHR — termination records + termination reason field. | Buildable. |
| I | SF Number | **Unknown** — possibly total sales pipeline, possibly something else. Waiting on Vincent Planz to clarify. | **Never guess — leave "Please Update" until Vincent confirms.** |

## Delivery

Same run as the main dashboard — one skill invocation produces **both files**:
- `RapDev Dashboard template_{Mon}'{YY}.xlsx`
- `HR Template_{Mon}'{YY}.xlsx`

Both land in `outputs/Synechron Reporting/{YYYY}/{YYYYMM}/`.
