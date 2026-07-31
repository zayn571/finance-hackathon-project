# Push: dashboard data + reference-format exports

Everything in this folder is repo-shaped — drop it into `zayn571/finance-hackathon-project`
on branch `claude/new-session-9z16n3` (or a branch off it) and commit. Nothing here
depends on the design prototype; the JSON and TS drop straight into `src/`.

## What to copy

| From this folder | To the repo | Why |
|---|---|---|
| `src/data/departmentListing.json` | same path (new) | The real BambooHR roster, 173 employees × the 19 reference columns. Extracted from REFERENCE_RapDev_Department_Listing().xlsx. Drives headcount by class and the department-listing export. |
| `src/data/headcountByClass.json` | same path (new) | Per-class totals **and** per-employee billable counts derived from the roster. |
| `src/data/synechronTemplates.json` | same path (new) | June '26 HR template and Slide 15 dashboard template values, plus new clients won and the CSAT/backlog rows. |
| `src/data/forecastMonthly.json` | same path (new) | Monthly plan placeholders for the forecast-vs-actual view. Replace with 4.2.1_RapDev - Detailed Projection Model.xlsx when available — same shape. |
| `src/data/dashboardMetrics.patch.md` | apply by hand | Two corrections to the existing metrics file (backlog June, attrition headline). |
| `src/lib/exportDeptListingXlsx.ts` | same path (new) | ExcelJS writer that reproduces the department listing reference exactly. |
| `src/lib/exportXlsx.patch.md` | apply by hand | Removes the trailing Source column from the GAAP Analysis export. |
| `CHANGELOG-dashboard.md` | repo root or PR body | The reasoning behind each change. |

## Corrections worth reading before you commit

1. **Opex double-counted personnel.** `opex.total` in `incomeStatementActuals.json` equals
   G&A + S&M; `opex.personnel` is a subset of those two (as `provenance.ts` notes). Summing
   ga + personnel + sm overstates opex ~60% and turns EBITDA negative. Treat personnel as a
   memo line. With that, Q1 Adj. EBITDA = $2,168,798 (17.2%) and Q2 = $2,285,148 (16.7%),
   matching the workbook.
2. **Revenue detail does not foot to the reported total.** For Q2–Q4 the DD service-line parts
   sum ~$120k short of `revenue.dd.total`. A reconciling "Other revenue" line keeps quarter
   revenue tied to `revenue.total` (Q2 $13,710,065).
3. **Backlog June is $17.15M**, from the HR template's New Metrics block — the current series
   stops at May ($19.36M). June is a 11.4% decline, which matters for the Synechron read.
4. **Attrition TTM is 17.3%** (`attrition.ttmAttritionPct`); anything showing 11.4% is stale.
5. **Headcount has two valid answers.** 173 on the BambooHR roster (115 billable) versus 156
   reported at the June close, and 159 "onsite" on the Synechron basis. Label which one you mean.
