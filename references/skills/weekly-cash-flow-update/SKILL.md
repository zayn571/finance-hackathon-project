---
name: weekly-cash-flow-update
description: >
  Actualize the RapDev Weekly Cash Flow workbook from the bank statements. Pulls the
  BOA Checking 4855 and Northern Bank Checking 3097 statement transactions, classifies
  each into the Cash In / Cash Out buckets on the "Wkly Cash Flow" tab using reference/mapping.csv,
  writes the actual ending bank balance for each week-ending Friday into rows 30 (BOA)
  and 31 (NB), and reconciles every week to the bank (Variance row 33 must be ~0). Saves
  a new dated workbook for human review. Trigger on: "run the weekly cash flow",
  "update the cash flow", "actualize the cash flow", "fill the weekly cash flow",
  "backfill the cash flow weeks", or any reference to the Weekly Cash Flow statement.
  Writes ONLY a local .xlsx. Never writes to QBO and never sends anything externally.
---

# Weekly Cash Flow Update

## Folder layout

```
skills/Weekly Cash Flow Update/
    SKILL.md                       <- this file
    reference/mapping.csv          <- the rule set (edit here to change categorization)
    scripts/update_weekly_cash_flow.py
    output/                        <- dated workbooks are delivered here for review
```

## What this does

Converts forecast weeks on the **Wkly Cash Flow** tab into actuals. For each completed
week (Saturday–Friday, labelled by its week-ending Friday in row 2) it:

1. Buckets the real bank transactions into the Cash In / Cash Out lines (rows 6–21).
2. Writes the actual ending bank balance into **row 30 (BOA)** and **row 31 (NB)**.
3. Lets the workbook's own formulas compute Ending Cash (row 23), Total Bank (row 32)
   and **Variance (row 33)** — which must be ~0 when the week is correctly captured.

## Source of truth

- **The bank statements are the cash source — for both the buckets and the balances.**
  RapDev's cash flow tracks *actual cash*, so the buckets come from what actually moved
  in the bank, not from QBO. (QBO carries non-cash entries — e.g. a "Portion of PMT from
  Qualcomm" journal entry — that never touch the bank; those must not appear here.)
- **QBO is the cross-check.** Use it to recover the payee on a cleared paper check
  (see "Cleared checks" below) and to spot-verify anything ambiguous. Per the workspace
  CLAUDE.md, if QBO and the bank disagree, **flag it — do not silently reconcile.**

## Inputs (provided by the user each run)

- **BOA Checking 4855** statement CSV — columns `Date, Description, Amount, Running Bal.`
  (Amount is signed; positive = credit/in.)
- **Northern Bank Checking 3097** account history — `AccountHistory*.xls/.csv` with
  `Account Number, Post Date, Check, Description, Debit, Credit, Status, Balance`.
  Reverse-chronological; only **Posted** rows carry a running balance (ignore Pending).
- The **prior Weekly Cash Flow workbook** (the most recent `Weekly Cash Flow YYYYMMDD.xlsx`).

The user pulls/automates these statement exports; the skill does not fetch from the banks.

## How transactions map to buckets

Rules live in **`reference/mapping.csv`** so they can change without editing code.
Each rule is `priority, match (lowercase substring of the description), direction
(credit/debit/any), bucket`. Resolution is by ascending priority, first match wins:

1. **Excludes (internal):** `CASHCON` sweeps between BOA↔NB, and internal `RAPDEV LLC`
   ACH/return movements. These net to zero across the two accounts.
2. **Any incoming credit → From Signed Contracts.** This is why customer receipts from
   names that are *also vendors* (Datadog, ServiceNow, BCBS) land correctly — direction
   decides before the vendor rules.
3. **Outgoing debits** match vendor / category keywords → their bucket. Notable learned cases:
   - `PERIS` (Principal 401k) → Health Insurance; other `PLIC` / `PRINCIPAL` → Other Benefits.
   - `WEX` / `BANCORPSV` → Other Benefits regardless of how QBO would split it.
   - `BCBS` / `BLUE CROSS` premium withdrawals → Health Insurance.
   - `DEEL` → International EE's; `419 BOYLSTON` → Office Rent; `BAMBOO` → Payroll.
   - `BREX INC` / `AMEX EPAYMENT` → Credit Cards.
   - `RETURNED CHECK` → From Signed Contracts (a customer reversal — a *contra* to cash in).
   - `JOSHUA` / `CRANK` (same payee) → Marketing; Datadog/ServiceNow **vendor bills** → Marketing.
4. **Cleared checks:** paper checks clear as `ECP INCLEARING CHECK` with **no payee** on the
   statement. The recurring **48,755.28** check is the 419 Boylston rent and is auto-mapped to
   Office Rent. **Any other inclearing check is FLAGGED** — recover its payee by matching the
   amount + date to the QBO bill payment, then add a rule to `reference/mapping.csv`.
5. **Online/phone transfers out** → Other Misc Expenses.
6. **No match → FLAG** (never guess). Flagged lines are written to the Flagged tab and will
   keep that week from reconciling until classified.

## Bank balances (rows 30 / 31)

Use the **statement running balance of the last posted transaction on/before the week-ending
Friday** (BOA file is chronological → last row of the day; NB is reverse-chron → first row of
the day). BOA is swept to a ~100k target via CASHCON, so its balance hovers near 100k — that
is correct; do not "fix" it from QBO (the QBO BOA register can read negative mid-sweep).

## Reconciliation

The skill is self-checking: because buckets and balances come from the same statements,
**every week's Variance (row 33) should be 0.00**. A non-zero variance means either a
flagged/unclassified line or a true bank-vs-books timing gap — investigate, don't plug it.
A residual variance equal to a single line almost always points at that line.

## Output & file handling

- Save a **new dated file**: `Weekly Cash Flow YYYYMMDD.xlsx` (no dashes) into the skill's
  **`output/` subfolder**. **Never overwrite** the prior workbook.
- **Grey out the actualized weeks.** After categorizing, shade rows 5–22 (the Cash In / Cash
  Out block) of each newly-filled week column with the same solid grey (`BFBFBF`) used by the
  prior actual weeks, so completed weeks read consistently against forecast weeks.
- Replace the forecast XLOOKUP in row 6 (From Signed Contracts) with the actual additive
  receipts; set From Bookings (row 7) to blank (all receipts route to Signed Contracts).
- Bucket cells are **additive formulas** (e.g. `=96838.29+55250.00`) so each component is
  traceable. Numbers use accounting format, **negatives in parentheses, no currency symbol,
  no color to convey meaning** (per CLAUDE.md).
- Three control tabs are appended: **Changes** (prior forecast → new actual, per cell),
  **Approval Log**, and **Flagged**.

## Approval gates (per CLAUDE.md)

- This skill writes **only a local Excel file**. It must **never** write to QuickBooks and
  **never** send anything externally (no Slack, no email) without explicit human approval.
- The output is a **draft for human review**. Claude never promotes it to the main shared
  drive. **Separation of duties:** the person who ran it cannot approve it — sign-off must
  come from a different RapDev Finance & Accounting team member (recorded on the Approval Log tab).

## Never do

- Never post to or edit a **closed/locked period**, and never edit a **prior-period** actual
  column. Only fill forecast weeks that are now complete.
- Never present a **forecast as an actual** or vice versa.
- Never **invent a number** to close a variance, and never treat a partial/failed statement
  pull as complete — flag it.
- Never assign a bucket the statement doesn't support — **flag for a human** instead of guessing.

## Run

```
python scripts/update_weekly_cash_flow.py \
  --boa "<BOA stmt csv>" --nb "<NB AccountHistory xls/csv>" \
  --workbook "<prior Weekly Cash Flow YYYYMMDD.xlsx>" \
  --out-dir "output"
```

The script auto-detects the last actual week (last column with a BOA balance in row 30) and
fills every completed week through the most recent Friday. Review the printed reconciliation
and the Flagged tab before sending for approval.

## Extending the rules

When a new vendor or customer appears (it will be FLAGGED), add a row to `reference/mapping.csv`:
`priority=30, match=<lowercase substring>, direction=debit (vendor) or credit (customer),
bucket=<one of the 13 buckets>`. Re-run; the week should drop to 0 variance.
