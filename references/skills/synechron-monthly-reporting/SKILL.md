---
name: synechron-monthly-reporting
description: >-
  Populate both monthly deliverables Synechron receives from RapDev: the
  RapDev Dashboard ("Slide 15 - RapDev" sheet — revenue, margin, EBITDA,
  headcount, AR, utilization) and the HR/Metrics report (bench, headcount mix,
  gender diversity, attrition, new-business metrics). One run produces both
  files. Sources: QuickBooks Online (actuals), BambooHR Report 228 (headcount),
  a human-attached POC Computation file (unbilled AR, utilization, billing
  rate — DLP-restricted from connector access), a human-attached Forecast file
  (forecast columns only, on request), Ashby (open positions), and a human-
  attached weekly KPI report (backlog). Trigger on: "run the Synechron
  reporting", "update the Synechron dashboard", "monthly Synechron report",
  "RapDev dashboard for {month}", or a request to update either file by name.
---

# Synechron Monthly Reporting

Builds **both** of Synechron's monthly deliverables in one run:

1. `RapDev Dashboard template_{Mon}'{YY}.xlsx` — the "Slide 15 - RapDev" matrix.
2. `HR Template_{Mon}'{YY}.xlsx` — the 5-sheet HR/Metrics workbook.

> Read `CLAUDE.md` (Drive rulebook) first. Hard stops apply: never edit a prior-period
> column, never invent data to close a gap, never treat a partial pull as complete, flag
> anomalies rather than reconcile them silently, and get approval before overwriting an
> existing file. QBO is the sole source of truth for actuals; forecasts are never actuals.

## Folder layout

```
skills/synechron-monthly-reporting/
├── SKILL.md                          <- this file
├── reference/
│   ├── dashboard-row-map.md          <- Slide 15 row/column map + never-write zones
│   ├── hr-metrics-row-map.md         <- HR/Metrics workbook sheet-by-sheet map
│   ├── qbo-account-map.md            <- exact QBO accounts for EBITDA, Salaries & Wages, etc.
│   └── poc-forecast-map.md           <- POC file & Forecast file cell locations
└── scripts/
    ├── column_utils.py               <- month<->column helpers (no network)
    ├── build_dashboard.py            <- builds the dashboard column (no network)
    └── build_hr_metrics.py           <- builds the HR/Metrics row (no network)
```

**Determinism rule.** The mapping logic lives in the reference files, not improvised per run.
If a tab is renamed, a column inserted, or an account restructured, **stop and flag — update
the reference file deliberately, don't patch around it in the moment.**

## 1. Inputs required each run

| Input | How to get it | Gate |
|---|---|---|
| QBO P&L (plain + by Class + by Customer) | `quickbooks_profit_and_loss` | Run anytime after month-end close |
| QBO AR Aging Summary | (load via ToolSearch — AR aging report tool) | Same |
| McDermott Will & Emery accrual JE | `quickbooks_transaction_detail_by_account` or `quickbooks_transaction_list`, grep Memo for "McDermott" — see `qbo-account-map.md` | Same |
| BambooHR Report 228 | `bamboohr_report_get`, `report_id: "228"`, `only_current_employees: false` | Same |
| Ashby open positions count | Ashby tools (job postings, status open) | Same |
| **POC Computation file** | **Ask the human to attach this month's copy** — DLP-restricted, connector can't read it | **Gate: on/after the 15th of the month following close.** If the file looks mid-edit or the human attaches it before the 15th, flag rather than proceed silently |
| **Forecast file** (`HOURSRATESREVENUE_FY26.xlsx` or successor) | **Ask the human to attach it — only when they tell you new forecast numbers are needed.** No auto-selection | On request only |
| **Weekly KPI report** (for HR Metrics Backlog) | Ask the human to attach it | On request, when building the HR Metrics report's Backlog row |
| Prior month's full dashboard + HR Metrics files | Ask the human, or find the most recent dated file in `outputs/Synechron Reporting/{YYYY}/{YYYYMM}/` | Always — this skill fills in one new column/row on top of the existing history, never rebuilds from scratch |

**Never treat a partial pull as complete.** If QBO, BambooHR, or Ashby returns an obviously thin
result for a period that should be fully posted, stop and flag it.

## 2. Target month

Always human-specified (e.g. "run it for June" or "for 2026-06") — no auto-detection of "this
month" vs. "last month." Confirm the target month out loud before pulling anything if it's
ambiguous from the request.

## 3. Build the dashboard

1. Pull QBO P&L (plain, by Class, by Customer) and AR Aging Summary for the target month; save
   each as JSON.
2. Find the McDermott JE for the target month (see `qbo-account-map.md`); note the dollar amount.
3. Pull BambooHR Report 228.
4. Get the POC Computation file from the human (gated — see table above).
5. Run:
   ```
   python scripts/build_dashboard.py \
     --template <prior month's full dashboard xlsx> \
     --month <YYYY-MM> \
     --pnl-plain <saved JSON> \
     --pnl-by-class <saved JSON> \
     --pnl-by-customer <saved JSON> \
     --ar-aging <saved JSON, with total_ar/current_ar keys extracted> \
     --mwe-je-amount <dollar amount from step 2> \
     --poc <path to POC file> \
     --out "RapDev Dashboard template_{Mon}'{YY}.xlsx"
   ```
   This writes Revenue, GM, Adjusted EBITDA, Avg. working days, % Sub-prime (0), Overdue AR,
   Unbilled AR (T&M/FP, all in the 0-60 bucket, net of unbilled asset vs. deferred revenue),
   Utilization, and Avg. Billing Rate (row 21 only — see `dashboard-row-map.md` correction).
6. **Claude writes the remaining rows directly** (not scripted, since these need judgment/mapping
   beyond a fixed cell lookup):
   - Headcount by region × COR/S&M/G&A (rows 26-37) from BambooHR — RapDev headcount has
     historically been ~100% Onsite; flag rather than guess if a future roster shows non-US
     locations, since there's no confirmed Onsite/Offshore/Nearshore field yet.
   - Average Salary (rows 68-75) — Salaries & Wages accounts (see `qbo-account-map.md`) ÷
     regional headcount.
   - T&M% / FP% (rows 79-80) and Revenue by Services (rows 85-88) — QBO by Class/Customer.
   - Top 5 Accounts (rows 82-84) — QBO by Customer.
7. If the human has flagged that new forecast numbers are needed, pull the Forecast file and
   write only the "(F)" columns embedded in the main matrix (never BH:BM) from the `FY26 Plan`
   tab — see `poc-forecast-map.md`. Label these clearly as RapDev's own projection.

## 4. Build the HR / Metrics report

1. Reuse the same BambooHR pull from step 3 above.
2. Pull Ashby open positions count.
3. Get the weekly KPI report from the human if updating New Metrics section C (Backlog).
4. Run:
   ```
   python scripts/build_hr_metrics.py \
     --template <prior month's HR Template xlsx> \
     --month <YYYY-MM> \
     --bamboohr <saved JSON> \
     --ashby-open-count <int> \
     --poc <path to POC file> \
     --out "HR Template_{Mon}'{YY}.xlsx"
   ```
   Writes Gender Diversity, Open Hired (+ new-joiner names), HCMIX, Bench-AO, and New Metrics
   section G (fixed-cost % — count-weighted placeholder, re-confirm weighting with a human before
   trusting this for real).
5. **Leave untouched, always** (see `hr-metrics-row-map.md` for full detail): New Metrics A
   (New clients — source unconfirmed), B (Synergy Revenue), "Soft Revenue Alignment by BU", C
   (Backlog — needs the weekly KPI report, not yet wired into the script), D (CSAT), E (Platform-
   sourced %), F (Certifications), I (SF Number — waiting on Vincent Planz). Section H (Attrition)
   needs a termination-reason field not confirmed present in Report 228 — flag rather than guess
   voluntary vs. involuntary.
6. Gender Diversity's "Target" column and HCMIX's exclusion list (Angel, Interns, signed-not-
   joined) are carried forward / applied per `hr-metrics-row-map.md` — don't recompute the Target.

## 5. Deliver

Both files land together in:
```
outputs/Synechron Reporting/{YYYY}/{YYYYMM}/RapDev Dashboard template_{Mon}'{YY}.xlsx
outputs/Synechron Reporting/{YYYY}/{YYYYMM}/HR Template_{Mon}'{YY}.xlsx
```

- **Full history carried forward** — each delivery is the complete workbook (Apr'23 → present
  for the dashboard), not a slice. This skill fills in one new column/row on top of the prior
  month's file, never rebuilds from scratch.
- **One final draft, no WIP files** — edit the same delivered file in place if the human asks
  for changes; don't create a second dated copy for the same month.
- **Discard raw source exports** after a successful build (QBO JSON pulls, BambooHR JSON) — the
  POC/Forecast/KPI files the human attached are theirs, not this skill's to retain either.
- **Archival snapshot** — after a successful POC/Forecast/KPI pull, note in your summary that the
  attached file was used for this run (mirrors the audit-trail pattern in
  `bamboohr-department-listing`); no separate snapshot copy is required since the human already
  owns the source file.
- Overwriting an existing same-month output file requires human approval first (root
  `CLAUDE.md` SS3) — this skill does not auto-overwrite.

## 6. Summary to report

- Target month + which columns/rows were written in each file.
- Every dollar figure written for Revenue, GM, Adjusted EBITDA (with the McDermott JE amount
  and reference), Unbilled AR split, Utilization, Avg. Billing Rate.
- Any row left "Please Update" and why (Tier 3 items, unconfirmed sources, gated POC file not
  yet available, etc.) — never silently skip a row without saying so.
- Whether the Forecast columns were touched this run.
- Links to both delivered files.

## Never do (root CLAUDE.md, restated for this skill)

- Never write to QuickBooks or send anything externally.
- Never edit a prior-period column/row, or the BH:BM "Old Forecast" block.
- Never invent a placement or value for a flagged item (SF Number, Backlog without the KPI
  report, Attrition without a confirmed voluntary/involuntary field, etc.) — ask, or leave it
  flagged.
- Never treat a partial/thin QBO, BambooHR, or Ashby pull as complete.
- Never attempt to read the POC Computation file via a Drive/BKPK connector — it's DLP-
  restricted; always ask the human to attach it.
- Never populate dashboard rows 22-23 (Offshore/Nearshore Avg. Billing Rate) — row 21
  only, per human decision (see `dashboard-row-map.md` correction, 2026-07).
