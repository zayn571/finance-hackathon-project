# GAAP Analysis tab layout (verified 2026-07-14)

Workbook: "Mgmt Reporting" (as of this skill's creation, confirmed against file id
`1_ACAu0JSelms58OwMX0LH3NEVV6zKpTlP4Uu0rgG8Ig`, titled "Copy of Mgmt Reporting" -- **confirm
the current canonical file with the user before every run; file IDs and copy/duplicate names
churn.** Tab name: `GAAP Analysis`, sheetId `1984089228` as of that read.

There is also a `Copy of GAAP Analysis` tab in the same workbook with a slightly different
row order -- treat that as a stale draft, not the live tab, unless told otherwise.

## Columns

Row 3 holds the column headers. Monthly columns run `Jan 2020` (column C) through `Dec 2026`,
one column per month, in order -- **compute the target column by matching the target month's
"Mon YYYY" string against row 3, do not hardcode a column letter/offset.** Past that monthly
run, the sheet has TTM / quarterly / annual rollup columns, then a second repeated monthly
block further right (purpose not yet confirmed -- the build script never writes there).

## Rows -- Actuals block (this skill only writes here)

Row 5 starts the `Actuals` block. Verified labels (1-indexed row numbers, column B):

```
7   Bookings                       28  COGS                          69  Operating Expenses
8      DD                          29     COGS Payroll                70     Total General & Administrative
9      SN                          30        DD                      71        DD
10     SW                          31        DD Services              72        SN
11     MSP                         32        DD Software               73        Operations
12     Data Label                  33        Managed DD               74     Total Personnel Expenses
13  Revenue                        34        Managed Security         75        DD
14     DD                          35        SN                       76        SN
15        Services                 36        SN Services               77        Operations
16        Software                 37        SN Software              78     Total Sales & Marketing
17     Managed DD                  38        SN MSP                    79        DD
18     Managed SOC                 39     COGS Travel                  80        SN
19     SN                          40        DD                        81        Operations
20        Services                 41        SN
21        Software                 42     Marketplace Fees             83  Other Expenses
22        MSP                      43     Contractor Fees              84  Other Expenses
23     Total Services              44  Total DD COGS                  85  Other Expenses - EBITDA Add Back
24     Total SW                    45  Total SN COGS                  87  EBITDA Adjustments
25     Total MSP                                                       88  McDermott, Will & Emery
                                    47  Gross Margin $                 91  Adj EBITDA
                                    57  Gross Margin %                 92  EBITDA %
```

Rows 95-119 are an `Analysis` section (ratios -- Bookings share, Gross Profit %, COGS+Opex %
of Revenue, Net Operating Income Margin, etc). **All formula-driven from the rows above --
this skill never writes there.**

Rows 121-140ish cover Project Hours / Bill Rate / Services Billings / Sales Efficiency
(headcount and utilization metrics, not QBO-sourced -- out of scope for this skill).

Row 142 starts a `Forecast` block that mirrors the Actuals row schema. **This skill never
writes to the Forecast block** -- it only fills completed-actual months in the Actuals block.

Rows 162-786 are unused/blank except one stray conditional-format rule at row 201 (columns
AY:BG and BK:CH-ish) -- avoid that row. The Synechron block (see `synechron-block.md`) uses
rows 300-304, well clear of it.

## What this skill writes vs. leaves alone

- **Writes:** leaf/detail cells only -- rows 15-18, 20-22 (Revenue), 30, 35, 40-43 (COGS),
  71-73/75-77/79-81 (Opex sub-rows), 84 (Other Expenses, Operations-only), and the new
  Synechron block 300-304 -- for the single target month's column.
- **Never writes:** any bolded/total row that already has a `SUM`-style formula over the
  rows above it (7, 13, 14, 19, 23-25, 28-29, 44-45, 47-67, 69-70, 74, 78, 83, 87-92, 95-119)
  -- these should already recompute once the leaf cells are filled. **If a run's printed
  reconciliation shows a total row NOT moving, that formula may be broken or hardcoded --
  flag it, do not overwrite the total cell to force a match.**
- **Never touches:** the Forecast block, any column other than the target month, any other tab.
