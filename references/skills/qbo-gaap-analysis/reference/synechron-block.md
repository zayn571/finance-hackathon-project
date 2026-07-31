# Synechron block placement (GAAP Analysis tab)

Decided 2026-07-14: Synechron (QBO class `400- Synechron`) gets its own line items, but
**the skill cannot insert spreadsheet rows** (only cell-value read/write tools are available;
inserting rows by hand-shifting ~700 rows of values risks corrupting formulas, merges, and the
chart-source ranges already wired into this 786-row sheet). Inserting new rows into the packed
71-81 range (between the existing DD/SN/Operations sub-rows) was ruled out for the same reason.

Instead, Synechron gets a **self-contained block in the tab's existing unused row space**
(rows 162-786 were empty on the 2026-07-14 read, aside from one stray conditional-format
rule at row 201 which this block avoids). No existing row, formula, merge, or chart is touched.

## Rows (Actuals block; column scheme matches the rest of the sheet -- see `tab-layout.md`)

| Row | Label | Source |
|-----|-------|--------|
| 300 | `Synechron` (section header) | static label, written once |
| 301 | `   G&A` | Expenses:General & Administrative (excl. G&A- Personnel Expenses), class rollup `400- Synechron` |
| 302 | `   Personnel` | Expenses:(G&A- Personnel Expenses + Sales & Marketing- Personnel Expenses), class rollup `400- Synechron` |
| 303 | `   Sales & Marketing` | Expenses:Sales & Marketing (excl. S&M- Personnel Expenses), class rollup `400- Synechron` |
| 304 | `Total Synechron Opex` | `=SUM(301:303)` for the written column -- written once as a formula, not a value |

Synechron currently has **no Revenue and no COGS activity** in QBO (confirmed on the
2026-07-14 P&L-by-Class pull -- the `400- Synechron` column had zero dollars in the Income
or COGS groups). This block is Opex-only for that reason. If Synechron ever books direct
revenue or COGS, extend this block (e.g. rows 305+) rather than retrofitting the DD/SN
Revenue/COGS rows -- raise it as a new mapping decision first.

## First-run behavior

On a skill run where rows 300-304 don't yet carry their labels (column B), the build script
writes the labels (and the row-304 SUM formula for the target month's column) once,
idempotently -- safe to run every month without re-checking.

## If this block is later promoted into the "real" structure

If the team eventually does a deliberate, human-driven row-insert to give Synechron proper
peer rows next to DD/SN (i.e. the originally-preferred layout), this block is superseded --
update this file, `account-row-map.csv`, and the build script's `SYN_*` row constants together.
