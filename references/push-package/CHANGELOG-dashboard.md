# Dashboard changelog — what changed and why

Built against `zayn571/finance-hackathon-project@claude/new-session-9z16n3`, with the four
reference workbooks (Mgmt Reporting (4), REFERENCE_RapDev_Department_Listing,
HR Template_June'26, RapDev Dashboard template_Jun26) and live pulls from Brex and QuickBooks.

## Data corrections

**Opex double-counted personnel.** `opex.total` equals G&A + S&M; `opex.personnel` is a subset
of those two, which `provenance.ts` states directly. Summing all three overstated opex by
roughly 60% and pushed EBITDA negative. Personnel is now a memo line. Q1 Adj. EBITDA
$2,168,798 / 17.2% and Q2 $2,285,148 / 16.7% now match the workbook.

**Revenue detail did not foot.** For Q2–Q4, the DD service lines fall about $120k short of
`revenue.dd.total`. A reconciling "Other revenue" line keeps quarter revenue equal to
`revenue.total` — Q2 lands on $13,710,065 instead of $13,533,000.

**EBITDA definition and basis.** `ebitda` is gross margin less opex; `adjEbitda` adds the MWE
adjustment and the other-expense add-back. The Rule of 40 and the YTD KPI use unadjusted EBITDA
so the score ties to the published 90.1; the forecast card and income statement use Adj. EBITDA.
Both are labelled explicitly so the two never read as the same number.

**Backlog and attrition.** June backlog is $17.15M (HR template New Metrics), an 11.4% decline
from May's $19.36M. TTM attrition is 17.3% with 29 separations.

**Headcount has three defensible answers** and the UI says which it means: 173 on the BambooHR
roster (115 billable per employee), 156 reported at the June close, 159 "onsite" on the
Synechron basis.

## Withheld figures

Per `provenance.ts`, project hours and all three bill rates contradict the delivered Synechron
workbook, so those rows render "—" and the verified June figures show instead: utilization
72.35%, blended bill rate $317.91. Bookings are labelled unverified — Q1 bookings of $14.2M
disagree with the reference statement by roughly 2.5x.

## Exports

**GAAP Analysis format** — row order, labels and row numbers taken from the tab itself
(r7 Bookings, r13 Revenue, r28 COGS, r57 Gross Margin %, r91 Adj EBITDA, r95 Analysis band,
r142 Forecast band, r178 EBITDA); fills FF434343 / FFCCCCCC / FFF3F3F3 / FFFFF2CC / FFD9D9D9 /
FFD9D2E9; money `"$"* #,##0`, accounting on Adj EBITDA, 0.00% on margins; Calibri 8 body, bold
10 bands; gridlines off, freeze C5, columns A 6.86 / B 27.29 / data 14.71. No Source column —
the reference tab has none.

**Department listing format** — 19 columns A–S at reference widths, header row height 30 with
Arial 10 bold white on FF666666, centred, wrapped, thin-bordered; frozen header; Employee # as
an integer; hire and status dates as serials with mm/dd/yyyy; body Arial 10 left/middle.

**Synechron cards** export real workbooks too, not HTML tables pretending to be `.xls`.

## Brex card activity

New card on the dashboard, under the close board: balance outstanding $106,576.21 (QBO account
21140, as of Jul 30), 994 July card transactions across 68 cardholders, month-to-date by
category, largest charge ($13,665.45, Barcelona South End, ServiceNow team), and a live feed of
the most recent transactions with cleared / pending / canceled status.

Cardholder names are masked to initials in the feed and omitted from the exported data. The
largest-charge tile credits a team, not a person.

The feed is a snapshot in the prototype. `src/lib/brexFeed.ts` has the server-side fetch,
pagination, rollup and merchant-total helpers needed to make it live; it wants an API route and
`BREX_API_TOKEN`. Brex returns ~32 card expenses a day and pages at 100, so a month is ~1,000
records — cache the route rather than fetching at page load.

## Chat panel

The sidebar is a working Claude session (Haiku 4.5 / Sonnet 4.5, switchable per message). Every
message carries the live dashboard as context: selected period and working days, revenue and
EBITDA by month, Q1/Q2 figures, Rule of 40, headcount by class with billable splits, AR aging,
backlog, attrition, verified June rates, new clients, close progress, and the Brex feed with its
coverage caveat. Merchant questions work against the loaded window; the system prompt tells the
model to state the window it summed rather than implying a full-month total.

## New data files

- `departmentListing.json` — the roster, 173 × 19, extracted from the reference workbook.
- `headcountByClass.json` — class totals plus per-employee billable counts, including the one
  record with no Teams value (kept as its own row so totals reconcile).
- `synechronTemplates.json` — June HR template rows, Slide 15 values, new clients won
  ($1,472,817 across five), backlog and CSAT series.
- `forecastMonthly.json` — placeholder monthly plan for forecast-vs-actual.
- `brexCardActivity.json` — Brex snapshot with the privacy and coverage notes attached.

## Open question

The forecast column is the only placeholder left. Everything else traces to QuickBooks, Brex,
BambooHR report 228, Asana project 1216426089593577, or one of the four workbooks.
