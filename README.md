# RapDev finance operating dashboard

An internal finance dashboard covering the monthly close: operating metrics, Rule
of 40, a full income statement with Excel export, A/R aging, backlog, attrition,
and the month-end close board.

## Running it

```bash
npm install
npm run dev
```

`npm run build` emits `dist/index.html` as a **single self-contained file** — all
JS, CSS and data inlined — so it can be opened straight from disk with no server.

## Where the numbers come from

| Section | Source |
|---|---|
| Income statement, KPI strip, charts, Rule of 40 | QuickBooks Online — P&L by class, pulled per month |
| A/R aging | QuickBooks Online — Aged Receivables |
| Backlog, fixed-price mix | Delivered Synechron workbook, June 2026 |
| Attrition | BambooHR report 228, including terminated employees |
| Headcount | BambooHR department listing |
| Close board | Asana project "July '26 Close" |
| Working files | Live Google Drive links |

Every reference file and every skill the board points at is committed under
[`references/`](references/README.md), so the repo does not depend on the
`rapdev-finance-claude-skills` workspace.

## Architecture

Monthly figures are the single source of truth. `src/data/monthlyActuals.json`
holds one record per closed month, and `src/lib/derive.ts` sums a selected set of
months and computes every total, margin, ratio and rate from those summed dollars.
Percentages are never averaged across months, so a quarter figure is a true
quarter figure rather than a mean of its months.

The period selector in the header drives the whole page. Choosing the fiscal year
shows quarter columns plus a year total; choosing a quarter breaks it into months;
choosing a month shows that month alone. Working days is the real business-day
count for the selection and feeds the hours and rate maths.

Hours and rates are anchored to the two independently verified figures in the
delivered Synechron workbook — 72.35% utilization and a 317.91 blended rate — with
hours billed derived from services revenue at that rate.

## Excel export

The income statement and A/R aging both write real `.xlsx` via ExcelJS rather than
CSV, because CSV cannot carry number formats, fills, weights, indents or column
widths. Income-statement styling comes from `src/data/refStyles.json`, extracted
from the Mgmt Reporting `GAAP Analysis` tab, and matches it row for row: freeze at
C5, column B 27.29, data columns 14.71, Calibri 8 body with 10pt section bands.
