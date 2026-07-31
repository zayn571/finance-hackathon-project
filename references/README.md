# References

Everything the dashboard is built from lives here, so the repo stands on its own
and does not depend on the `rapdev-finance-claude-skills` workspace being present.

## `skills/`

The finance skills the month-end close board points at. Each task on the board
that has a suggested-skill badge names one of these directories, and every badge
resolves to a real `SKILL.md` here:

| Skill | What it covers |
|---|---|
| `brex-import` | Brex card transaction categorisation into the QBO import file |
| `bamboohr-department-listing` | Department listing / headcount-by-month refresh from BambooHR report 228 |
| `synechron-monthly-reporting` | The Synechron dashboard + HR template monthly deliverables |
| `qbo-gaap-analysis` | Populating the Mgmt Reporting GAAP Analysis tab from QBO |
| `end-of-month-cc-report` | Per-manager credit-card spend files and the master rollup |
| `weekly-cash-flow-update` | Weekly cash-flow forecast, A/R aging and bookings tabs |

## `source-workbooks/`

The actual files the numbers and formatting were taken from.

- **`Mgmt Reporting (4).xlsx`** — the format authority for the income statement.
  `src/data/refStyles.json` was extracted from its `GAAP Analysis` tab: per-row
  bold, fill, font colour, size, number format and indent, each entry recording
  the reference row it came from. The Excel export applies that spec verbatim, so
  a generated cell wears the same format as its counterpart in this workbook.
- **`synechron-202606/`** — the delivered June 2026 Synechron workbooks. Source of
  the backlog series, the fixed-price mix, and the utilization (72.35%) and
  blended bill rate (317.91) that the hours and rate maths is anchored to.
- **`REFERENCE_RapDev_Department_Listing.xlsx`** — department listing structure and
  the `HC by Month` layout.
- **`rapdev-department-listing-202612.csv`** — headcount by class.
- **`rapdev-income-statement-202612.csv`** — the income statement row structure this
  dashboard mirrors.

## `design-handoff/`

The original design specification (`Finance Dashboard.dc.html` plus its README and
design-system bundle) describing the intended layout, tokens and behaviour.

## Live systems

Figures are pulled from QuickBooks Online (P&L by class and by month, Aged
Receivables), BambooHR (report 228, including terminated employees, for
attrition), and Asana (project "July '26 Close" for the task board). Regenerating
the data files requires access to those connectors.
