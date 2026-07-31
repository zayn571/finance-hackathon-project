# Handoff: RapDev finance operating dashboard

## Overview
An internal finance dashboard for RapDev covering the monthly/quarterly close: operating goals vs
plan, Rule of 40, weekly team KPIs, a fully expandable income statement with CSV/Excel export,
bookings split by practice, headcount by class, new business, backlog, attrition, realized rates,
Synechron report exports, links to source workbooks, and an Asana-style month-end close task board
with agent delegation. A narrow AI chat rail sits on the right.

The design exists today as sample data hardcoded in one HTML file. The point of this handoff is to
rebuild it as a real application wired to live systems (QuickBooks Online, BambooHR, Brex, Asana,
Google Drive/Sheets).

## About the design files
`Finance Dashboard.dc.html` is a **design reference written in HTML** — a prototype of the intended
look, structure and behavior. It is not production code to copy. Recreate it in the target
codebase's environment (React + TypeScript is the natural fit; the prototype's logic is already
React-shaped) using that codebase's established patterns, data layer and component library.
If no app exists yet, start a new React + TypeScript project (Vite or Next.js) and implement there.

The file is a "Design Component": a single HTML document whose template is plain markup with
`{{ value }}` holes and whose logic is a React-like class (`renderVals()` returns everything the
template renders). Read the class first — it contains the whole data model.

## Fidelity
**High fidelity.** Colors, type, spacing, radii, hover/focus behavior and copy are final and follow
the RapDev design system (navy/teal, flat, no shadows or gradients). Recreate the UI faithfully. Use
the design-system components rather than reimplementing them: the prototype mounts
`RapDevDesignSystem_e4f7f6.Button` (primary / secondary / ghost, sm / md) and `.Badge`
(navy / teal / tint / outline / metric) from the bundle, and those should map to the same library
(or its React package) in the target app.

## Screens / views
One long scrolling page, one right-hand rail. Content column max-width 1720px, 32px page padding,
24px gap between sections. Page background `#F1F6F8`; every panel is a white card, 1px `#E4E9EE`
border, 12px radius, 32px padding, no shadow.

### 1. Header bar
Full-bleed navy (`#0B2D4C`) strip, 24px/32px padding, flex, space-between.
- Left: eyebrow "Finance — sample data" (12px, 500, 0.12em tracking, uppercase, teal) over
  "Operating dashboard" (28px, 600, white).
- Right: **Period** `<select>` (white field, navy text, 6px radius, 44px min-height) with 17 options —
  FY2026, Q1–Q4 2026, and each month of 2026; then a 1px `#1E4568` divider; then **Working days**
  (sum of working days in the selected period); then **Units** ("USD thousands").
- Selecting a period recomputes working days and the Rule of 40 card. In production it should filter
  the whole page.

### 2. Q4 operating goals + unit goals (grid `minmax(0,3fr) minmax(0,2fr)`)
- **Operating goals table**: columns Millions | Actuals 4Q24 | Actuals 4Q25 | Target 4Q26 |
  Actuals 4Q26 | Achievement. Rows: Revenue (bold, `#F1F6F8` row), "from deposits" and
  "from billable work" (indented 16px), Bookings, Adj. EBITDA. Achievement teal when ≥100%, navy
  otherwise. Header cells: 12px, 500, uppercase, 0.12em, `#6B7A8A`, 2px navy bottom border.
  Wrapped in `overflow-x: auto`.
- **Monthly run-rate targets**: four goal rows (billable hours per resource, bookings per AE,
  utilization, gross margin). Each row = label + actual (18px, 700) + "of {goal}" + achievement %,
  then a 10px progress bar on `#F1F6F8`. Rows must wrap (`flex-wrap: wrap`, `min-width: 0`).

### 3. KPI stat strip
`grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))`, 16px gap, six cards (24px padding,
`min-width: 0; overflow: hidden`): FY26 revenue, Q4 revenue, Adj. EBITDA margin, FY26 bookings,
Backlog, Headcount. Each = uppercase label (12px `#6B7A8A`), value (28px, 700, navy), delta line
(14px; teal when favorable, `#6B7A8A`/navy otherwise).

### 4. Rule of 40 (grid `minmax(0,1fr) minmax(0,2fr)`, 24px padding/gap)
- Left: eyebrow "Rule of 40", period label, score (36px, 700) + verdict ("Above/Below the 40 line",
  teal/gray), a 12px stacked bar (navy = growth, teal = margin), then three rows: revenue growth YoY,
  Adj. EBITDA margin, threshold 40.0.
- Right: score by quarter — 150px stacked bars (teal margin on top of navy growth) with a 2px
  `#C9D2DA` horizontal line at the 40 mark, value labels above, quarter labels below.
- Score = revenue growth % (vs same months prior year) + Adj. EBITDA margin %, for the selected period.

### 5. Weekly KPIs
Toggle chips (DS Button, `primary` when on / `secondary` when off) for RapDev, ServiceNow, Datadog,
Managed Datadog, Managed SOC. RapDev and ServiceNow default on. Each selected group renders a table:
teal uppercase group title, right-aligned columns Name | W26 (6/21) | W27 (6/28) | W28 (7/5) |
W29 (7/12) | W30 (7/19) | Change %; zebra rows (`#F1F6F8` on odd); name and change columns 600 weight;
change reads `#6B7A8A` when 0.0%. Values are weekly snapshots (debt hours/$, runway, backlog,
utilization, bill rate, capacity delta, attrition, project count, fixed-cost %, billable/free hours;
MD and MSOC groups use customers/hours/cases/MRR/rate).

### 6. Income statement
Header: title, hint copy, DS Buttons "Expand all" / "Collapse all" (secondary) and "Export"
(primary) opening a menu with "Download CSV" and "Download Excel (.xls)".
Body: `overflow: auto; max-height: 720px`, 13px table, sticky header, tabular numerals.
- Columns: Q1..Q4 plus FY26. Clicking a quarter header expands it into its three months
  (month columns tinted `#F1F6F8`, marker "−"/"+" in teal). Q4 expanded by default.
- Rows: three collapsible sections, each a navy band (white uppercase label, click to collapse;
  Forecast starts collapsed):
  - **Actuals** — Bookings (DD, SN, SW, MSP); Revenue (DD → Services, Software, Managed DD,
    Managed SOC; SN → Services, Software, MSP), Total services, Total SW, Total MSP; COGS
    (COGS payroll → DD + four sub-lines, SN + three sub-lines; COGS travel → DD, SN; Marketplace
    fees; Contractor fees), Total DD COGS, Total SN COGS; Gross margin $ and Gross margin % (both
    broken out DD/SN and per stream); Operating expenses (Total G&A, Total personnel, Total sales &
    marketing, each split DD / SN / Operations); Other expenses (+ EBITDA add back); EBITDA
    adjustments (McDermott, Will & Emery); EBITDA, Adj. EBITDA, EBITDA %.
  - **Analysis** — bookings share by practice; gross profit and % by practice; COGS + opex and % of
    revenue; COGS/G&A/personnel/S&M % of revenue and net operating income margin; project hours
    block (billable/non-billable headcount and %, hours available/worked/billed, utilization, hours
    per head, padding %); bill rate block (break-even, per hour billed, "real" rate per hour worked);
    services billings; sales efficiency.
  - **Forecast** — bookings, revenue tree, COGS, gross profit, opex (personnel, G&A, S&M → marketing,
    travel), other expenses, EBITDA adjustments, EBITDA.
- Row styles: totals 700 weight on `#F1F6F8`; sub-totals 600; lines 400; indent = depth × 16px;
  spacer rows are 4px with no border. Negative values render in parentheses, `#6B7A8A`.
- Export emits exactly the columns currently on screen, with the row label indented by two spaces
  per level and a section name in caps as its own row.

### 7. Revenue and EBITDA by month / Revenue by quarter (grid `3fr / 2fr`)
Both bespoke CSS bar charts, flat navy/teal bars, no axes, value labels above bars, month/quarter
labels below a 1px `#E4E9EE` baseline. The monthly chart sits in an `overflow-x: auto` wrapper with a
560px min-width track. Quarter chart compares FY25 (`#C9D2DA`) against FY26 (navy).

### 8. YoY growth / Expense base trend (grid `2fr / 3fr`)
- YoY growth: 12 rows of `40px | 1fr | 60px` — month, 14px bar (teal at ≥18%, navy below), percent.
- Expense base: eight quarters (FY25 + FY26) stacked COGS (navy) / S&M (teal) / G&A (`#9FB3C4`),
  totals above.

### 9. Bookings
Header with FY26 bookings and book-to-bill. Left: 12 stacked monthly bars (navy ServiceNow, teal
Datadog). Right: a 40px share bar (ServiceNow % / Datadog %) plus four rows — ServiceNow bookings,
Datadog bookings, average deal size, Q4 bookings vs target. All bookings figures derive from one
monthly series; Q4 must tie to the operating-goals table.

### 10. Headcount by class (grid `3fr / 2fr` with T&M and rate cards)
Header: title, DS "Export" Button (department listing CSV / Excel), and three stats — Total,
Billable (teal), Billable mix. Header wraps.
Table rows follow the RapDev class taxonomy, group rows bold on `#F1F6F8` with an `outline` Badge
reading "Group", children indented 20px with a `teal` (Billable) or `tint` (Non-billable) Badge and a
120px share bar:
- 100 Operations → 110 G&A (13, non-billable), 120 Marketing (5, non-billable)
- 200 Datadog → 210 Delivery (38, billable), 220 Engineering (15, billable), 230 Sales (7, non-billable)
- 300 ServiceNow → 310 Delivery (46, billable), 320 Engineering (12, billable), 330 Sales (8, non-billable)
- 400 Synechron → 410 Digital Platforms (12, billable)
Totals: 156 headcount, 123 billable.
Beside it: **T&M vs fixed price** (40px split bar 68/32 plus four stats) and **Average realized rate**
(ServiceNow, Datadog, Blended — value plus a 12px bar).

### 11. New clients won / Backlog / Attrition (three equal columns)
- New clients: total initial contract value, then five rows, each a 40×40 logo slot (drag-and-drop
  placeholder in the prototype — in production, the client logo), name, engagement meta, amount.
- Backlog: total plus four bars (ServiceNow contracted, Datadog contracted, Managed SOC
  subscription, deposits not yet earned) and a footer "Coverage of next-quarter plan 86%".
- Attrition: TTM total, four stat tiles on `#F1F6F8` (`repeat(auto-fit, minmax(120px, 1fr))`), and a
  70px sparkline of separations by month.

### 12. Synechron reports (two equal cards)
"Headcount — December 2026" and "RapDev dashboard template — December 2026". Each: teal eyebrow
"Synechron report", title, subtitle, DS "Export" Button top-right (CSV / Excel), a zebra table, and a
footer total above a 1px navy rule. The dashboard-template card compares actual / plan / variance for
ten metrics; variance is teal when favorable.

### 13. Working files
Light-blue (`#F1F6F8`) panel, two groups (Excel, Google Sheets), each
`repeat(auto-fit, minmax(260px, 1fr))` of link cards: Lucide file icon (navy for Excel, teal for
Sheets), name, "source · cadence · owner", external-link icon. Hrefs are placeholders — wire to real
SharePoint / Drive URLs.

### 14. July month-end close board
Header: teal eyebrow "Team board", title "July month-end close", "{n} of 16 tasks complete", three
member chips (32px circular avatars with initials — VP navy, ER `#09838D`, ZM teal — name + role),
DS "Add task" Button. Below: a 10px teal progress bar.
Left column (`overflow-x: auto`, 640px min track): header row `28px | 1fr | 130px | 70px | 90px`
(blank, Task, Assignee, BD due, Due date); three groups — Recurring month end tasks (9),
Reconciliations (4), Review and sign-off (3). Each task row: a 22px circular checkbox (teal fill +
white Lucide check when done, else white with `#C9D2DA` border), task name (line-through and
`#6B7A8A` when done), a suggested-skill Badge (`tint`, or `teal` when delegated), a DS Button
("Delegate to agent" ghost → "Agent assigned" secondary), assignee avatar + name, BD due (e.g. -5,
-2, +1), due date (navy for pre-close, teal for post-close).
Right column: **Notes** — three entries (avatar, name, relative time, body) from Vincent Planz
(admin), Eric Rabkin, Zayn Moselhy. **Suggested agents** — three `#F1F6F8` 12px-radius cards naming a
skill in mono type, what it does, how many open tasks it covers, and a DS Button that flips
"Delegate" → "Queued": `brex-import`, `end-of-month-cc-managers-report`,
`bamboohr-department-listing`.

### 15. Chat rail (right side)
Sticky, full height, `flex: 0 0 10%` with `min-width: 168px; max-width: 220px`, `#F1F6F8` with a 1px
left border. Top: "Chat" pill (navy) and "Activity" (navy text) with Lucide icons. Then scope block
(teal "Team" Badge + "Finance" + a teal dot and "Finance · Overview"), "SESSIONS · 1" with two icon
buttons (history, new), a white session row (title, elapsed, truncated last message, "Continue last"
link), an empty-state paragraph, a composer card (placeholder text, Attach button, teal 30px send
button), and a "Context: Finance · Overview" footer.

## Interactions & behavior
- **Period select** → recomputes working days, Rule of 40 score/verdict/bar. Should filter all
  sections in production.
- **Quarter column click** → expands/collapses that quarter into months; "Expand all" / "Collapse all"
  set all four.
- **Section band click** (Actuals / Analysis / Forecast) → collapse/expand that block of rows.
- **Export menus** — one menu open at a time (single `menu` state key: `is` | `hc` | `dash` | `dept`).
  Choosing a format builds a matrix and downloads it: CSV as a UTF-8 BOM + quoted fields; "Excel" as
  an HTML `<table>` Blob typed `application/vnd.ms-excel` with an `.xls` name. In production, emit a
  real XLSX server-side.
- **KPI chips** → independent booleans per group; hidden groups are unmounted.
- **Task checkbox** → toggles done (line-through + muted) and recomputes the progress bar.
- **Delegate to agent** (per task) and **Delegate** (per agent card) → toggle chip/label state. Wire to
  the real agent runner.
- **Logo slots** on new clients accept a dropped image (persisted by the prototype's slot component).
- Hover: card borders `#E4E9EE` → `#C9D2DA`; CTA teal → `#09838D`; links underline. Focus: 2px teal
  outline, 2px offset — never remove it. Transitions 150ms micro / 240ms UI,
  `cubic-bezier(0.2, 0.8, 0.2, 1)`; respect `prefers-reduced-motion`.
- Every card must clip or wrap rather than spill: headers use `flex-wrap: wrap` + `min-width: 0`, stat
  grids use `minmax()` tracks, wide tables and the monthly chart use `overflow-x: auto`.

## State management
Prototype state (all client-side):
- `expanded`: `{ Q1..Q4: boolean }` — income statement month columns.
- `sections`: `{ Actuals, Analysis, Forecast: boolean }`.
- `menu`: `null | 'is' | 'hc' | 'dash' | 'dept'` — which export menu is open.
- `kpiOn`: `{ rapdev, sn, dd, md, msoc: boolean }`.
- `period`: `'FY26' | 'Q1'..'Q4' | 'M0'..'M11'`.
- `doneTasks`, `agentTasks`, `agentsRunning`: `Record<string, boolean>`.

Derived data comes from one function per month (`base(i)`) summed over a period (`sum(indices)`) and
then a single `derive()` that computes every total, margin, rate and forecast key. **Keep this shape.**
Percentages and rates are always recomputed from summed dollars — never averaged across months.

Production data requirements:
- QuickBooks Online — trial balance / P&L by class and month (income statement, expense trend,
  operating goals) and the four credit-card accounts for the manager spend report.
- BambooHR — saved "Department Listing" report (id 228) for headcount by class and attrition.
- Brex — card transactions for the reconciliation tasks.
- CRM or bookings source — signed contract value by practice and month, plus new clients and backlog.
- Time system — hours available / worked / billed, utilization, realized rates.
- Asana — the close project, task assignees, due dates and completion.
- Weekly KPI snapshots need a stored history (one row per metric per week) — the W26–W30 columns are
  point-in-time, not derivable from current state.

## Design tokens
Colors: navy `#0B2D4C`; teal `#00A5A2`; deep teal `#09838D`; white `#FFFFFF`; light blue `#F1F6F8`;
body gray `#333333`; muted `#6B7A8A`; hairline `#E4E9EE`; strong border / FY25 bars `#C9D2DA`;
chart tertiary `#9FB3C4`; header divider `#1E4568`. No gradients, no shadows (one
`0 1px 2px rgba(11,45,76,.06)` is permitted on modals/popovers only).
Type: Gilroy → Lato → system (`var(--font-sans)`); mono `var(--font-mono)` for skill names and the
scope chip. Sizes used: 56/36/28/22/18/16/15/14/13/12/11px. Weights 400 body, 500 UI/labels,
600 titles, 700 stats and totals. Uppercase labels: 12px, 500, `0.12em` tracking. Never italic,
never ExtraBold.
Spacing: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64. Radii: 6px controls, 12px cards, 0 table cells,
9999px avatars and pills. Numerals: `font-variant-numeric: tabular-nums` everywhere figures appear.
Formatting: values ≥ $1M render as `$X.XXM`, below that `$Nk`; the income statement is in USD
thousands; negatives in parentheses.

## Assets
- RapDev design system bundle and tokens: `_ds/rapdev-design-system-e4f7f627-3a22-443b-b856-66e236009546/`
  (`colors_and_type.css`, `styles.css`, `_ds_bundle.js` exposing `window.RapDevDesignSystem_e4f7f6`
  with Button, Badge, Card, Input). Use the same library in the app.
- Icons: inline Lucide paths (message-square, users, clock, plus, paperclip, search, list-checks,
  arrow-up, chevron-down, circle-dot, bot, check, file-spreadsheet, table, external-link). Use the
  Lucide package, 2px stroke, never below 16px, navy by default and teal only for active/CTA states.
- Client logos: empty drop slots in the prototype (`image-slot.js`) — supply real logo files.
- No photography, no illustrations, no emoji.

## Files
- `Finance Dashboard.dc.html` — the whole design: template markup plus the logic class holding the
  data model, formatting helpers and export code. Read the logic class first.
- `image-slot.js` — the drag-and-drop image placeholder used by the new-clients logos (prototype only).
- `_ds/rapdev-design-system-.../` — design-system tokens, stylesheet and component bundle.

## Suggested build order
1. Tokens and the design-system components in the target stack.
2. Page shell, header with the period selector, card primitives.
3. The financial data model (`base` → `sum` → `derive`) against a real P&L source; the income
   statement is the hardest piece and everything else reuses its output.
4. Charts, then the remaining metric cards.
5. Exports (real XLSX), then the weekly KPI history store.
6. Asana-backed close board and the agent hooks.
7. The chat rail last — it depends on whatever assistant backend you use.
