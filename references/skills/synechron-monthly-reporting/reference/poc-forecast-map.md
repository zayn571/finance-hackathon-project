# POC file & Forecast file cell map

## POC Computation file

**Not connector-readable.** This file (`POC Computation - RapDev - {YYYYMM}.xlsx`, Drive path
`RapDev LLC/RapDev LLC Accounting & Finance/Revenue/{YYYY}/{YYYYMM}/`) is DLP-flagged
"ineligible for generative AI contexts" — the Drive/BKPK connectors can find it by search but
cannot read its contents. **Ask the human to attach a copy of this month's file at the start of
each run.** Do not attempt to route around the restriction.

**Naming guardrail:** the Drive folder accumulates "- Copy" duplicates of this file with
identical or later modified timestamps (observed May–July 2026). When searching Drive (e.g. to
confirm the file exists, or for anything that doesn't require reading contents), match the exact
name `POC Computation - RapDev - {YYYYMM}.xlsx` — no "- Copy" suffix. Since the human attaches the
file directly, this mostly matters for sanity-checking what they sent you.

Verified tabs/cells (against the June 2026 file):

| Metric | Tab | Cell/range | Notes |
|---|---|---|---|
| Unbilled AR (total + T&M/FP split) | `SOW level` | Columns **CU:DL** = "Unbilled/Deferred Balance," one column per month-end (row 4 has the date header). Column **G** = Project Type (T&M / Fixed Fee) per SOW row. | Target column = the one whose row-4 date matches month-end. **Correction (2026-07 live run):** this column nets the unbilled-receivable ASSET against deferred revenue (a LIABILITY) per SOW — only sum rows with a **positive** value; negative rows are deferred revenue and belong to a different GL account, not this dashboard figure. Verified: summing only positive T&M/FP rows for June 2026 reproduces QBO's "Unbilled Receivables" account (AcctNum 12140, Id 83) JE `ContractAssetRC202606` amount ($3,832,064.83) to the penny — cross-check against that GL account's running balance each run (`quickbooks_transaction_detail_by_account`, account_id 83, from a date before the account's first activity through month-end; the last row's running "Balance" column is the month-end total). That account also picks up a small MSP-specific monthly reclass (`Unbill MSP RC {YYYYMM}`, e.g. $8,333.33 for June) that isn't in the SOW-level tab at all — fold it into the Fixed Price bucket (recurring/MSP revenue reads as fixed-fee-like) and flag it in the summary rather than silently dropping it. **100% of the total goes in the 0-60 day bucket** — 61-90/91-180/>181 are always 0 (human-confirmed methodology). |
| Utilization | `Employee Utilization` | Row **197** ("Total Utilization Rate"). Column anchor: column **D** = Jan 2022; target column index = `4 + (year-2022)*12 + (month-1)` (0-indexed from column D=4). June 2026 = column BE. | Verified: BE197 = 0.7235, matches dashboard's existing June placeholder (0.72). |
| Avg. Billing Rate | `SOW level` | Row **574** ("Rate" — single blended company-wide figure, not split by region). Column anchor: row 4 has a date header directly above this block (columns BH onward observed with 2026 dates) — match target column to month-end date in row 4. | Verified: BL574 = 317.9145... for June 2026. Human confirmed (2026-07 live run): **write to dashboard row 21** (the live template has always carried this value there, labeled "Onsite" — row 20 is a blank label row), leave rows 22-23 (Offshore/Nearshore) blank. |
| % Sub-prime of billable count | — | Not sourced from this file — always hardcoded 0 (human-confirmed). | |
| Bench (HR Metrics report) | `Employee Level` / `Employee Utilization` | Billable-status employees (BambooHR) with no current-month hours logged against any SOW. | Cross-reference BambooHR billable="Yes" active roster against this file's per-employee monthly hours; zero hours in the target month = bench. Not a single ready-made cell — this is a computed cross-reference. |
| % fixed-cost vs. T&M (HR Metrics report, section G) | `SOW level` | Column **G** (Project Type) × column **H** (SN/DD) | Same columns as Unbilled AR's T&M/FP split — weight by dollar amount or count, confirm which with a human the first time this runs for real. |

**If any of these tabs/cells don't match this map** (renamed tab, inserted column, moved block) —
**stop and flag, don't guess a new location.** This file is hand-edited by multiple people and is
exactly the drift risk the build spec called out.

## Forecast file

`HOURSRATESREVENUE_FY26.xlsx` (or successor — **ask the human for a new copy each time forecast
numbers are needed**; this file does not update on its own and there's no "most-recently-modified
in a folder" auto-selection since the human hands it to you directly).

| Metric | Tab | Notes |
|---|---|---|
| Forecast Revenue, COGS, Gross Profit, Adjusted EBITDA | `FY26 Plan` | Row labels in column B: `Service Revenue`/`Software Revenue`/`MSP Revenue` (row 8-10), `TOTAL REVENUE` (row 12), `COGS Payroll`/`COGS Contractors`/`COGS Travel`/`Marketplace Fees` (rows 15-18), `Gross Profit` (row 22), `Net Operating Income` (row 47), `EBITDA`/`Adjusted EBITDA` (rows 66-71). Monthly columns E:P = Jan–Dec, quarterly rollups in S:V. |

**Only feeds the "(F)" columns embedded in the main dashboard matrix** (e.g. `BC:BF`). Never
touches the POC-fed rows — confirmed no reconciliation logic needed between the two files.

This file's own "Adjusted EBITDA" methodology (Net Income + Interest + Depreciation + Taxes +
flat monthly "Adjustments" of $100k) is **different** from the actuals methodology in
`qbo-account-map.md` — that's expected, forecast and actual EBITDA bridges don't have to match
line-for-line. Don't try to reconcile them.

**Label forecast rows clearly as RapDev's own bottoms-up projection**, not a Synechron-agreed
number — per the original build spec, since it sits visually next to actuals in the same sheet.
