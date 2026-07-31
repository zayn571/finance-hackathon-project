# Dashboard changelog — what changed and why

Built against `zayn571/finance-hackathon-project@claude/new-session-9z16n3`, with the four
reference workbooks (Mgmt Reporting (4), REFERENCE_RapDev_Department_Listing,
HR Template_June'26, RapDev Dashboard template_Jun26).

## Data corrections

**Opex double-counted personnel.** `opex.total` equals G&A + S&M; `opex.personnel` is a
subset of those two, which `provenance.ts` states directly ("opex.personnel ties exactly to
G&A-Personnel + S&M-Personnel"). Summing all three overstated opex by roughly 60% and pushed
EBITDA negative. Personnel is now a memo line. Q1 Adj. EBITDA $2,168,798 / 17.2% and Q2
$2,285,148 / 16.7% now match the workbook.

**Revenue detail did not foot.** For Q2–Q4, `revenue.dd.services + software + managedDd +
managedSoc` falls about $120k short of `revenue.dd.total`. A reconciling "Other revenue" line
keeps quarter revenue equal to `revenue.total` — Q2 lands on $13,710,065 instead of
$13,533,000.

**EBITDA definition.** `ebitda` in the JSON is gross margin less opex; `adjEbitda` adds the MWE
adjustment and the other-expense add-back; `ebitdaPct` is the *adjusted* margin. The dashboard
follows that convention and labels the percentage row "Adj. EBITDA %".

**Backlog and attrition.** June backlog is $17.15M (HR template New Metrics), an 11.4% decline
from May's $19.36M. TTM attrition is 17.3% with 29 separations.

**Headcount has three defensible answers** and the UI now says which it means: 173 on the
BambooHR roster (115 billable per employee), 156 reported at the June close, 159 "onsite" on the
Synechron basis (excludes interns, contractors, signed-not-joined).

## Withheld figures

Per `provenance.ts`, project hours and all three bill rates contradict the delivered Synechron
workbook, so those rows render "—" rather than a number, and the verified June figures show
instead: utilization 72.35%, blended bill rate $317.91. Bookings are labeled unverified — Q1
bookings of $14.2M disagree with the reference statement by roughly 2.5x.

## Exports

**GAAP Analysis format** — row order, labels and row numbers taken from the tab itself
(r7 Bookings, r13 Revenue, r28 COGS, r57 Gross Margin %, r91 Adj EBITDA, r95 Analysis band,
r142 Forecast band, r178 EBITDA); fills FF434343 / FFCCCCCC / FFF3F3F3 / FFFFF2CC / FFD9D9D9 /
FFD9D2E9; money `"$"* #,##0\ _€`, accounting on Adj EBITDA, 0.00% on margins; Calibri 8 body,
bold 10 bands; gridlines off, freeze C5, columns A 6.86 / B 27.29 / data 14.71. No Source column.

**Department listing format** — 19 columns A–S at reference widths, header row height 30 with
Arial 10 bold white on FF666666, centred, wrapped, thin-bordered; frozen header; Employee # as
an integer; hire and status dates as serials with mm/dd/yyyy; body Arial 10 left/middle.
See `src/lib/exportDeptListingXlsx.ts`.

## New data files

- `departmentListing.json` — the roster, 173 × 19, extracted from the reference workbook.
- `headcountByClass.json` — class totals plus per-employee billable counts, including the one
  record with no Teams value (kept as its own row rather than dropped, so totals reconcile).
- `synechronTemplates.json` — June HR template rows, Slide 15 values, new clients won
  ($1,472,817 across five), backlog and CSAT series.
- `forecastMonthly.json` — placeholder monthly plan for forecast-vs-actual. Swap in
  4.2.1_RapDev - Detailed Projection Model.xlsx; the shape is already right.

## Open question

The forecast column is the only placeholder left in the dashboard. Everything else traces to
QuickBooks, BambooHR report 228, Asana project 1216426089593577, or one of the four workbooks.
