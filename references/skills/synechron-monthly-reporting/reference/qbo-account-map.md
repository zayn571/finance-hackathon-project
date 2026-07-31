# QBO account map

Verified against the live chart of accounts and June 2026 actuals (see conversation history —
Adjusted EBITDA validated to within $1 of the template's existing June placeholder).

## Adjusted EBITDA (dashboard row 14)

```
Adjusted EBITDA = Net Income
                 + "Depr Exp- Equipment"                        (Other Expenses > Depreciation Expense)
                 + "Depr Exp- Furniture & Fixtures"              (Other Expenses > Depreciation Expense)
                 + "Interest Expense - ROU Asset Office Lease"   (Other Expenses)
                 + Taxes                                         (Other Expenses > Taxes, if present — usually 0)
                 + McDermott Will & Emery monthly accrual JE     (see below)
```

**Do NOT include** "Depr Exp- ROU Asset- Office" — that's a sibling depreciation line that looks
similar but is excluded from the addback per human confirmation.

**Do NOT include** Stock Compensation Expense — it's a separate addback line item in RapDev's
existing EBITDA bridge model, not part of this monthly dashboard pull. If the bridge model's
addback logic changes, this list needs to be re-confirmed with a human, not inferred.

### McDermott Will & Emery accrual lookup

Each month there's a Journal Entry accruing legal fees, memo pattern:
`"McDermott, Will & Emery {Month} {YYYY} activity"`, JE Num pattern `"MWE Accr {YYYYMM}"`, posted
to Accrued Liabilities. Find it via `quickbooks_transaction_detail_by_account` (or
`quickbooks_transaction_list`) for the target month and grep the Memo/Description column for
"McDermott". June 2026 example: JE #83182, "MWE Accr 202606", **$29,048.31**.

**If no matching JE is found for the target month, flag it — do not assume $0 and do not carry
forward last month's amount.**

## Average Salary (dashboard rows 68-75)

Sum only the **"Salaries & Wages"** sub-account across the three personnel-expense groupings —
**exclude** 401k Match, Benefits, Bonuses, Commissions, Payroll Fees, and Payroll Taxes (those are
employer costs / variable comp, not base salary):

| Account (FullyQualifiedName) | June 2026 example |
|---|---|
| `Cost of Goods Sold:COGS- Personnel Expense:Salaries & Wages` | 1,419,770.54 |
| `General & Administrative:G&A- Personnel Expenses:Salaries & Wages` | 332,453.83 |
| `Sales & Marketing:Sales & Marketing- Personnel Expenses:Salaries & Wages` | 408,133.81 |

There is a 4th, orphaned top-level `Personnel Expenses:Salaries & Wages` account (Id 118) in the
chart of accounts. It had **zero activity** in June's actual P&L — treat as a dormant/legacy
account (likely pre-acquisition) and exclude, unless a future month shows real activity there, in
which case flag it rather than silently including or excluding it.

**Average Salary (region) = regional Salaries & Wages $ ÷ regional headcount (BambooHR).** RapDev's
headcount has historically been ~100% Onsite (Offshore/Nearshore rows are 0) — if that changes,
the Salaries & Wages split by region needs a real mapping (QBO doesn't tag these accounts by
region today), so flag rather than guess a split.

## Overdue AR (dashboard row 66)

```
Overdue AR % = (Total AR at month-end − "Current" column) ÷ Total AR at month-end
```

Pull via QBO **AR Aging Summary** report (not the POC file). "Overdue" = everything outside the
Current bucket at the time of the pull.

## Revenue, Gross Margin, T&M%/FP%, Revenue by Services, Top 5 Accounts

Standard `quickbooks_profit_and_loss` pulls:
- Revenue (row 6) / Gross Margin (row 11): plain P&L, `Total Income` / `Gross Profit`.
- T&M% / FP% (rows 79-80) and Revenue by Services (rows 85-88): `summarize_column_by: Classes`
  (or Customers where Class doesn't cleanly separate ServiceNow vs. Datadog — confirm against the
  existing table's historical split logic before assuming Class always works).
- Top 5 Accounts (rows 82-84): `summarize_column_by: Customers`.
