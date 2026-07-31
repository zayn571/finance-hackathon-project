# Push: dashboard data, reference exports, Brex feed

Everything here is repo-shaped — drop it into `zayn571/finance-hackathon-project` on branch
`claude/new-session-9z16n3` (or a branch off it) and commit. Nothing depends on the design
prototype; the JSON and TS drop straight into `src/`.

## What to copy

| From this folder | To the repo | Why |
|---|---|---|
| `src/data/departmentListing.json` | same path (new) | The real BambooHR roster, 173 employees × the 19 reference columns. Drives headcount by class and the department-listing export. |
| `src/data/headcountByClass.json` | same path (new) | Per-class totals **and** per-employee billable counts derived from the roster. |
| `src/data/synechronTemplates.json` | same path (new) | June '26 HR template and Slide 15 dashboard template values, new clients won, backlog and CSAT series. |
| `src/data/forecastMonthly.json` | same path (new) | Monthly plan placeholders for forecast-vs-actual. Replace with 4.2.1_RapDev - Detailed Projection Model.xlsx — same shape. |
| `src/data/brexCardActivity.json` | same path (new) | Brex card snapshot: balance, July counts, MTD by category, last two days of transactions. |
| `src/lib/brexFeed.ts` | same path (new) | Server-side Brex fetch + pagination, feed shaping, category rollup, and the merchant-total helper the chat panel needs. |
| `src/lib/exportDeptListingXlsx.ts` | same path (new) | ExcelJS writer reproducing the department-listing reference exactly. |
| `src/data/dashboardMetrics.patch.md` | apply by hand | Two corrections to the existing metrics file (backlog June, attrition headline). |
| `src/lib/exportXlsx.patch.md` | apply by hand | Removes the trailing Source column from the GAAP Analysis export. |
| `CHANGELOG-dashboard.md` | repo root or PR body | The reasoning behind each change. |

## The one thing that needs a decision

**Brex has to be fetched server-side.** The dashboard currently ships a snapshot because the
browser cannot call Brex — the API needs a secret and CORS blocks it. `src/lib/brexFeed.ts` is
the whole implementation; it needs an API route around it:

```ts
// app/api/brex/route.ts
import { fetchBrexExpenses, toFeed, toCategoryTotals } from "@/lib/brexFeed";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const after = searchParams.get("after") ?? new Date(Date.now() - 2 * 864e5).toISOString();
  const before = searchParams.get("before") ?? new Date().toISOString();

  const expenses = await fetchBrexExpenses(process.env.BREX_API_TOKEN!, after, before);
  const feed = toFeed(expenses);
  return Response.json({ feed, categories: toCategoryTotals(feed) });
}
```

Needs `BREX_API_TOKEN` in the environment. Cache for a few minutes — Brex returns ~32 card
expenses a day and pages at 100, so a full month is ~1,000 records across ~10 round trips.
That is fine behind a cached route and far too slow at page load.

Once that route exists, the chat panel can answer any window ("what did we spend on Uber in
the past two days") instead of only the two days baked into the snapshot. `merchantTotal()`
already handles the descriptor variance — UBER *TRIP, UBER *EATS and UBR* PENDING.UBER.COM
all resolve to Uber.

## Corrections worth reading before you commit

1. **Opex double-counted personnel.** `opex.total` equals G&A + S&M; `opex.personnel` is a
   subset of those two (as `provenance.ts` notes). Summing all three overstates opex ~60% and
   turns EBITDA negative. Treat personnel as a memo line. With that, Q1 Adj. EBITDA =
   $2,168,798 (17.2%) and Q2 = $2,285,148 (16.7%), matching the workbook.
2. **Revenue detail does not foot to the reported total.** For Q2–Q4 the DD service-line parts
   sum ~$120k short of `revenue.dd.total`. A reconciling "Other revenue" line keeps quarter
   revenue tied to `revenue.total` (Q2 $13,710,065).
3. **Backlog June is $17.15M**, from the HR template's New Metrics block — the current series
   stops at May ($19.36M). June is an 11.4% decline, which matters for the Synechron read.
4. **Attrition TTM is 17.3%**; anything showing 11.4% is stale.
5. **Headcount has three valid answers.** 173 on the BambooHR roster (115 billable), 156
   reported at the June close, 159 "onsite" on the Synechron basis. Label which one you mean.
6. **EBITDA basis.** The Rule of 40 and the YTD KPI run on unadjusted EBITDA (15.1% margin,
   score 90.1) to match the published figures. Adj. EBITDA (16.9%) is used in the forecast card
   and the income statement. Keep the two labelled distinctly.

## Privacy note

Cardholder names are excluded from `brexCardActivity.json` and from `toFeed()`. The dashboard
renders initials only and attributes the largest charge to a team rather than a person. Keep
that property if you extend the feed.
