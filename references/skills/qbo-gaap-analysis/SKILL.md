---
name: qbo-gaap-analysis
description: |
  Update the RapDev GAAP Analysis tab (in the Mgmt Reporting workbook) for one target month,
  sourced from QuickBooks Online's Profit & Loss report split by Class. Use whenever the user
  asks to "update the GAAP analysis", "run the GAAP analysis for {month}", "actualize GAAP
  analysis", "fill in {month} on the mgmt reporting workbook", or "pull the P&L by class into
  mgmt reporting". Replaces manually running QBO's report builder and copy-pasting into the
  tab. Pulls the QBO P&L by Class for the target month, maps it into the tab's existing
  row/segment structure (Datadog / ServiceNow / Operations, plus a new self-contained
  Synechron block), flags anything it can't confidently place (Not Specified class, unmapped
  intercompany revenue, ambiguous Other Expenses), and delivers a full copy of the workbook
  with that month written in (so charts recompute) for human review. On-demand only, no
  recurring trigger. Does NOT write to QuickBooks and does NOT send anything externally.
---

# QBO GAAP Analysis Update

> **Rules precedence:** runs under the finance-drive root rulebook (`CLAUDE.md`); the root
> wins on any conflict. Reference data lives in `reference/` — read it, don't hardcode.
> Outputs go to `outputs/qbo-gaap-analysis/{YYYY}/{YYYYMM}/`.

Pulls QuickBooks Online's Profit & Loss report (Accrual, `summarize_column_by=Classes`) for
one target month, maps every account onto the **GAAP Analysis** tab's row/segment scheme, and
delivers a **new dated copy** of the Mgmt Reporting workbook with that month's column filled
in — so the workbook's existing charts recompute against real data, not a hand-typed table
the user has to paste in. QBO is the sole source for actuals. Run mode: **on-demand**, the
user names the target month each time (no auto-detection).

**Determinism rule — do not improvise.** The mapping logic lives in `scripts/build_gaap_analysis.py`
and the two reference CSVs below. If a QBO account shows up that neither the script nor the
CSVs know how to place, **flag it — do not write an ad hoc rule into the script for one run.**
Add the rule to the CSV (a human, deliberate change), then re-run.

## Folder layout

```
skills/qbo-gaap-analysis/
├── SKILL.md                              <- this file
├── reference/
│   ├── tab-layout.md                     <- verified row numbers / column scheme for the tab
│   ├── account-row-map.csv               <- QBO account/group -> tab row, by segment
│   ├── segment-overrides.csv             <- human-maintained exceptions (see SS3)
│   └── synechron-block.md                <- why/where the new Synechron rows live (SS2)
└── scripts/
    └── build_gaap_analysis.py            <- the mapping + write-plan builder (no network access)
```

## 0. Before every run — confirm the target file

File IDs and copy names churn in this Drive (there were three "Mgmt Reporting" variants and
two "GAAP Analysis"-named tabs found during this skill's design). **Ask the user which file is
the current canonical Mgmt Reporting workbook if it isn't already established in the
conversation — do not guess from a Drive search.** `reference/tab-layout.md` documents the
row/column scheme verified against one specific file id; re-verify row 3's headers and the
`GAAP Analysis` tab's row labels against the *current* file before trusting that layout blindly,
since a human may have edited the tab since this skill was built.

## 1. Parameters

- `month` — target month, e.g. `2026-06`. **Always user-specified — no default/auto-detect.**
- Must be a month with QBO actuals fully posted (a mid-month pull under-reports — QBO only
  shows posted transactions, not a bug, but flag it if the row counts look thin for a
  supposedly-complete month).
- **Never target a prior-period column that's already filled**, and never edit the Forecast
  block (root CLAUDE.md: never edit a prior-period report).

## 2. Pull from QBO

Call `quickbooks_profit_and_loss` with `accounting_method=Accrual`, `summarize_column_by=Classes`,
`start_date`/`end_date` spanning the target month only. The response is large and will persist
to a tool-results file — this is expected, don't try to inline it. Confirm the header's
`AccountingStandard: GAAP` and that `StartPeriod`/`EndPeriod` actually cover the target month.

**Completeness gate:** if the pull returns `NoReportData` or an obviously empty class column
that should have activity, stop and flag — never treat a partial pull as complete (root SS7).

## 3. Run the build script

```
python scripts/build_gaap_analysis.py \
  --pnl <saved P&L JSON file path from step 2> \
  --month <YYYY-MM> \
  --overrides reference/segment-overrides.csv \
  --out write_plan.json
```

This does the mapping (see `reference/account-row-map.csv` for the full rule set) and prints a
summary: target column, cells to write + total $, and flags raised + total $. It writes
`write_plan.json` with three things Claude (not the script — it has no network access) then
acts on:

1. `cell_writes` — `{row, col, amount}` entries for the Actuals block's leaf/detail rows only.
   Never a bolded total row — those already carry `SUM`-style formulas over the rows this
   skill fills and should recompute on their own.
2. `synechron_label_writes_run_once` — the Synechron block's row labels (rows 300-303,
   `reference/synechron-block.md`). Only needs writing the first time this skill ever runs
   against a given workbook copy; harmless to send every time (idempotent).
3. `synechron_total_formula` — the one formula cell for row 304, written once per column.
4. `flags` — dollar amounts the script would NOT place. **Never write these anywhere.**
   Report them to the human. Common causes:
   - **"Not Specified" class** — needs manual classification in QBO first; this is exactly
     the anomaly root CLAUDE.md SS1 warned about — flag it, don't reconcile it away.
   - **Synechron-Intercompany revenue with no `segment-overrides.csv` entry** — the QBO class
     tag alone doesn't tell you the real business segment for these (see SS4). Ask the human
     which segment it belongs to; if they give you a durable answer, add a row to
     `segment-overrides.csv` (with `added_by`/`added_date`/`notes` per its header) so future
     runs resolve it automatically. A one-off answer that won't recur doesn't need a CSV row —
     just place it by hand in the delivered file and say so in your summary.
   - **DD/SN/Synechron-classed dollars inside "Other Expenses"** — the tab's Other Expenses
     row has no segment split; ask the human where (if anywhere) that should go.

## 4. Known mapping assumption — Personnel Expenses regrouping

QBO nests `G&A- Personnel Expenses` inside `General & Administrative` and
`Sales & Marketing- Personnel Expenses` inside `Sales & Marketing`. The tab instead has a
**separate combined "Total Personnel Expenses" bucket** alongside G&A and S&M. This skill
therefore computes:
- Tab **G&A** row = QBO G&A total **minus** G&A-Personnel Expenses
- Tab **Personnel** row = QBO G&A-Personnel Expenses **plus** S&M-Personnel Expenses
- Tab **S&M** row = QBO S&M total **minus** S&M-Personnel Expenses

This was inferred from the tab's existing row labels, not confirmed line-by-line with a human
against a real historical month. **The first time this skill runs for real, sanity-check the
G&A/Personnel/S&M split against whatever the tab already shows for the prior actual month** —
if the ratios look wrong, this assumption is the first thing to revisit.

## 5. Deliver

1. `google_drive_copy` the canonical Mgmt Reporting workbook into
   `outputs/qbo-gaap-analysis/{YYYY}/{YYYYMM}/GAAP Analysis {Month YYYY} {YYYYMMDD}` (no dashes
   in the date, per root CLAUDE.md SS4 naming convention).
2. `google_sheets_update` the copy's `GAAP Analysis` tab with every entry in `cell_writes`,
   the one-time `synechron_label_writes_run_once` (safe to always include), and
   `synechron_total_formula`.
3. Do **not** touch the live/canonical workbook — this delivers a draft copy only. The user
   promotes it manually after review (root CLAUDE.md SS4: Claude never promotes its own work).
4. **One final draft, no WIP versions** — if the user asks for changes, edit this same copy in
   place; don't create a second dated file for the same month.
5. Discard the saved raw QBO pull once the build is verified (root CLAUDE.md SS4).

No approval gate applies to this delivery itself (it's a new file inside the outputs folder,
not a QBO write, external send, or overwrite of an existing file) — but overwriting that same
dated output file on a same-day re-run does require approval per root CLAUDE.md SS3.

## 6. Summary to report

- Target month + column written.
- Cells written: count + total $, broken out by Revenue / COGS / Opex / Synechron block.
- Flags: full list with account, segment, amount, reason — and the flagged total $, so the
  human can see at a glance how much of the period's activity needed a manual decision.
- Whether this was the first run to populate the Synechron block labels.
- Link to the delivered file.
- A reminder that Synechron currently only has Opex data in QBO (see
  `reference/synechron-block.md`) — if this run's pull shows Synechron Revenue or COGS for the
  first time, that's a new mapping decision, not something to force into the existing block.

## Never do (root CLAUDE.md SS7, restated for this skill)

- Never write to QuickBooks.
- Never send anything externally.
- Never edit a prior-period column or the Forecast block.
- Never invent a placement for a flagged dollar amount — ask, or leave it flagged.
- Never treat a partial/empty QBO pull as complete.
- Never insert or delete spreadsheet rows/columns — this skill only has cell-value read/write
  access. Any structural change to the tab (e.g. eventually giving Synechron peer rows next to
  DD/SN) is a deliberate human-driven edit, done outside this skill, with `tab-layout.md` and
  `synechron-block.md` updated to match afterward.
