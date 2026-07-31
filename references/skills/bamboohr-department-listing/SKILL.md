---
name: bamboohr-department-listing
description: >-
  Rebuild the RapDev Department Listing workbook each period from the live
  BambooHR "Department Listing" report (report_id 228). Produces the ACTIVE +
  FUTURE-hire roster in the standard format: QBO Department is driven by each
  employee's BambooHR Teams field, and the QBO prefixes/classification are
  computed from the editable reference Key sheet. Reads people data from
  BambooHR and writes only inside this Drive. Never writes to QuickBooks and
  never sends anything externally. Trigger on: "run the department listing",
  "update the department listing", "refresh the department listing", "monthly
  department listing / headcount", or any reference to BambooHR report 228 /
  Department Listing.
---

# BambooHR Department Listing

Rebuilds the RapDev **Department Listing** workbook from BambooHR. It keeps only
**active and future-hire** employees, sources each person's **QBO Department from
their BambooHR `Teams` field**, and computes the QBO prefixes and SYNE
classification from the **reference Key sheet**. It reads people data from
BambooHR and writes only inside this Drive. It never touches QuickBooks and never
sends anything externally.

> Read `G:\Shared drives\RapDev Finance - Claude\CLAUDE.md` first. The hard stops
> there apply here: never edit source data, never invent data to close a gap,
> never treat a partial/failed pull as complete, flag anomalies (don't silently
> reconcile), and get approval before overwriting an existing file.

This skill folder is **self-contained** so anyone on the finance team can open it
from the Drive and run it:

```
Skills/bamboohr-department-listing/
├── SKILL.md                                       <- this file
├── reference/
│   └── REFERENCE_RapDev_Department_Listing.xlsx   <- editable master (see section 3)
└── scripts/
    └── build_department_listing.py                <- the build script
```

---

## 1. Inputs & systems

| What | Source | Notes |
|------|--------|-------|
| Roster | BambooHR connector — `bamboohr_report_get`, `report_id: "228"`, **`only_current_employees: false`** | `false` is required so terminations are visible and can be excluded. |
| QBO Department | Each employee's **`Teams`** field in report 228 | Teams now carries the full QBO path (e.g. `300- ServiceNow:320- Engineering`). Maintained in BambooHR. |
| Prefix / classification mappings | The **`Key`** sheet inside the reference workbook | This is what a human edits when mappings change (see section 3). |
| Base workbook / structure | `reference/REFERENCE_RapDev_Department_Listing.xlsx` | Provides the sheet structure plus the carried-over HC by Month and Key sheets. **Never edited by the skill.** |

**Outputs land here**, organized by year/month:
`G:\Shared drives\RapDev Finance - Claude\outputs\bamboohr-department-listing\{YYYY}\{YYYYMM}\RapDev_Department_Listing_{YYYYMMDD}.xlsx`

---

## 2. Column layout (Department Listing sheet)

Data starts row 2. **QBO Department literally equals the Teams cell**, and the
prefix columns are formulas that look that value up in the Key sheet.

| Col | Header | Source |
|-----|--------|--------|
| A | Employee # | BambooHR `employeeNumber` |
| B | First Name | `firstName` |
| C | Last Name | `lastName` |
| D | Last name, First name | `fullName2` |
| E | Gender | `gender` |
| F | Hire Date | `hireDate` |
| G | Employment Status | `employmentHistoryStatus` |
| H | Employment Status: Date | `employeeStatusDate` |
| I | Division | `division` |
| J | Department | `department` |
| K | Location | `location` |
| L | Job Title | `jobTitle` |
| **M** | **Teams** | `teams` (full QBO path) |
| N | Billable Status | `customBillable` (Yes/No) |
| O | Employee Level | `customEmployeeLevel` |
| P | State | `state` |
| Q | QBO Department | **Formula** `=M{row}` (the Teams cell) |
| R | Prefix- Travel | **Formula** — `=IF($N="Yes","Cost of Goods Sold:COGS- Travel Expenses:",IF($N="No",XLOOKUP($Q,Key!$I:$I,Key!$J:$J),"Review Billable Status"))` |
| S | Prefix- Payroll | **Formula** — same shape, `Key!$K:$K` (Personnel) |

`R`/`S` read Billable from `N` and the QBO value from `Q`, and look the prefixes
up in the **Key** sheet (`Key!$I:$I` then `J`/`K`). Keep the formulas in columns
Q/R/S — only column M (Teams) and the A–P data come from BambooHR.

---

## 3. The reference file (what a human maintains)

`reference/REFERENCE_RapDev_Department_Listing.xlsx` is the editable master. Two
things change over time and are maintained by a human — the skill reads them, it
does not invent them:

- **QBO Department per person** → maintained in **BambooHR** (the `Teams` field).
- **Prefix / SYNE-classification mappings** → maintained in the reference
  **`Key`** sheet (e.g. when a new department / QBO code appears, add its row so
  the `XLOOKUP`s in R/S resolve).

The reference also carries the **HC by Month** sheet, which the build copies into
each output unchanged (see section 6).

---

## 4. How a run works

> **The build script already exists — do not write new code.**
> Use `G:\Shared drives\RapDev Finance - Claude\skills\bamboohr-department-listing\scripts\build_department_listing.py`.

The build is split in two: an agent with the BambooHR connector pulls the report,
then a plain Python script does the workbook build (no connector needed).

1. **Read** `CLAUDE.md` (the Drive rulebook) and this `SKILL.md`.
2. **Pull report 228** — `bamboohr_report_get`, `report_id: "228"`,
   `only_current_employees: false`. If it errors or returns an obviously partial
   roster, **stop and flag** — never treat a partial pull as complete.
3. **Save the report JSON** to a file (any path), e.g. `report_228.json`.
4. **Run the build script**, passing that JSON path:
   ```
   python "G:\Shared drives\RapDev Finance - Claude\Skills\bamboohr-department-listing\scripts\build_department_listing.py" report_228.json
   ```
   (Install openpyxl first if needed: `pip install openpyxl`.)
   The script:
   - drops terminated employees and the exclusion list (#129),
   - starts from the reference workbook (HC by Month + Key carried unchanged),
   - rebuilds the Department Listing in the section-2 layout (active + future only),
   - saves `…\outputs\bamboohr-department-listing\{YYYY}\{YYYYMM}\RapDev_Department_Listing_{YYYYMMDD}.xlsx`,
   - refuses to overwrite an existing same-day file (overwrite guard),
   - prints a summary.
5. **Report** the script's summary to the human: counts of active+future written,
   terminated dropped, excluded Employee #s, and any flags (active employees with a
   short/blank Teams value → fix Teams in BambooHR).

> For a **test run** without colliding with the dated file, pass an explicit
> second argument: `... build_department_listing.py report_228.json "C:\path\TEST.xlsx"`.

---

## 5. Guardrails & edge cases

- **`only_current_employees: false`** is mandatory (so terminated employees are
  visible and can be excluded).
- **Active + future only.** Anyone with Employment Status `Terminated` is dropped.
  Future hires (blank status) are kept; their Teams/QBO stay blank until BambooHR
  is filled in.
- **Exclusion list** — drop these Employee #s every run (noted in the summary):
  **`129`** (Test4 McTester, a test account). Adding to this list is a deliberate
  human change — edit `EXCLUDE` in the script.
- **QBO Department = the Teams value.** If an **active** employee's Teams is still
  a short code (no `:`) or blank, the script **flags** it — fix the Teams field in
  BambooHR rather than patching the workbook.
- **Blank fields are written blank** — never invented.
- **Never edit the reference workbook** from a run; it is the human-maintained master.
- **Overwrite guard** — the script will not overwrite an existing dated file. A
  second run the same day needs human approval (per CLAUDE.md section 3).
- **Never invent data, never write to QBO, never send anything externally.**

---

## 6. Known limitation — HC by Month

The **HC by Month** sheet is **carried over from the reference unchanged** on each
run — it is **not** yet auto-refreshed from the report. It currently reflects the
active + future roster captured in the reference. Refreshing the HC by Month
month-grid (and restoring terminated employees for historical attrition, if
wanted) is a planned future enhancement. Until then, treat HC by Month in the
output as carried-forward, not freshly computed.

---

## 7. Approvals & boundaries

This skill writes a **new** dated file inside the Drive only. It does **not** write
to QuickBooks and does **not** send anything externally, so a normal run triggers
no approval gate. Exceptions:

- A run that would **overwrite** an existing file → stop and get human approval
  (the script enforces this).
- People data stays in this Drive — never copy or send it elsewhere without
  explicit human instruction (CLAUDE.md section 4).
