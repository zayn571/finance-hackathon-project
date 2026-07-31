# Dashboard row/column map — "Slide 15 - RapDev" sheet

Verified against `RapDev_Dashboard_template_Jun_26.xlsx` (the file the finance team last sent
Synechron). **Re-verify row 5's month headers and the row-3/row-84 labels against the current
template before trusting this blindly** — a human may reorder columns or insert a row since this
was written.

## Layout

- Row 5 = month/quarter column headers, `Apr'23 (A)` → present, with a quarterly rollup column
  every 4th column (formula-driven `SUM`/`AVERAGE` over the 3 months — never write to those).
- Columns **BH:BM** are a separate "Old Forecast" scratch block to the right of the live matrix.
  **Never write to BH:BM** — it's deprecated, left untouched every run.
- The live "(F)" forecast columns are embedded in the main matrix (e.g. `BC:BF` for Jul–Sep '26 +
  Q2'27 rollup) — these are the ones the Forecast file feeds.
- Target column for a given month = the column whose row-5 header matches `"{Mon}' {YY} (A)"`
  (actuals) — resolve by scanning row 5 for the label, don't hardcode a fixed offset, since the
  matrix grows by one column every month.

## Row map

| Row | Metric | Source | Notes |
|---|---|---|---|
| 6 | Revenue | QBO P&L, Total Income | Amount in $M — template stores `raw/(10^6)` |
| 7 | Avg. working days | Calendar calc | Business days in the month (Mon–Fri minus company holidays) |
| 8 | Revenue Growth CC (YoY) | Formula off row 6 | Already in template, don't overwrite |
| 9 | Revenue Growth CC (YTD) | Formula off row 6 | Already in template, don't overwrite |
| 11 | Gross Margin $ | QBO P&L, Gross Profit | |
| 12 | GM% | Formula (row11/row6) | Already in template |
| 14 | Adjusted EBITDA | QBO P&L + JE lookup | See `qbo-account-map.md` §Adjusted EBITDA |
| 15 | Adj. EBITDA % | Formula (row14/row6) | Already in template |
| 17 | Revenue Per Day | Formula (row6/row7) | Already in template |
| 18 | Revenue Per Employee | Formula (row6/row43) | Already in template |
| 20 | (label row only — "Average Billing rate") | — | Always blank in the live template; never write here |
| 21 | Avg. Billing Rate (single blended rate, labeled "Onsite") | POC file, `SOW level`!574 | **Correction (2026-07 live run):** the live template has always stored the single blended rate in row 21, not row 20 — write here |
| 22-23 | Offshore/Nearshore sub-rows | — | Leave blank — do not populate (human-confirmed) |
| 26-37 | Headcount by region × COR/S&M/G&A | BambooHR Report 228 | **Correction (2026-07 live run):** roster is no longer ~100% Onsite — Report 228's `location` field now shows `Boylston`/`Remote` (→ Onsite) vs. `Non-US` (→ Offshore/Nearshore). Nearshore = `Non-US` with a Canadian province in `state` (ON/AB/BC/QC/MB/SK/NS/NB/NL/PE/NT/YT/NU); everything else `Non-US` = Offshore. This is Claude's judgment call (no confirmed country field exists) — re-confirm with a human. `department` → COR/S&M/G&A: COR = Engineering/Project Management/MSOC/MDD; S&M = Sales/Marketing; G&A = Operations/People Operations/Strategy/Finance. Exclude `employmentHistoryStatus` in (Terminated, Paid Intern). |
| 38-48 | Totals, Contractors, Net HC Change | Formula off BambooHR-sourced cells | Already in template |
| 50 | Contractor Mix | Formula | Already in template |
| 52 | Utilization | POC file, `Employee Utilization`!197 | Column aligned to month, see `poc-forecast-map.md` |
| 54-64 | Unbilled AR + T&M/FP aging buckets | POC file, `SOW level`!CU:DL | 100% bucketed to 0-60 days (rows 56 & 61); 61-90/91-180/>181 always 0 |
| 66 | Overdue AR | QBO AR Aging Summary | (Total AR − Current column) ÷ Total AR |
| 68-75 | Average Salary (by region) | QBO P&L "Salaries & Wages" accounts ÷ BambooHR regional headcount | See `qbo-account-map.md` §Salaries & Wages |
| 77 | % Sub-prime of billable count | Hardcoded `0` | Confirmed always 0 |
| 79-80 | T&M% / FP% | QBO P&L by Class/Customer | Same split mechanism as Revenue by Services |
| 82-84 | Y-o-Y Growth: Top 5 Accounts | QBO P&L summarized by Customer | |
| 85-88 | Revenue by Services (ServiceNow / Datadog / Total) | QBO P&L summarized by Class or Customer | Matches existing table structure exactly |

## Never write to

- Any bolded/summary row carrying a `SUM`/`AVERAGE`/`IFERROR` formula over cells this skill fills
  — those recompute on their own.
- Columns BH:BM (Old Forecast block).
- Any column to the left of the current target month (never edit a prior-period column —
  root `CLAUDE.md` hard stop).
