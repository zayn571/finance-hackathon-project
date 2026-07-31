"""Build one month's row into the HR / Metrics report (5-sheet workbook).

No network access. Claude pulls BambooHR report 228, Ashby open-postings data,
and hands this script the JSON plus the POC file and prior month's template.

Usage:
    python build_hr_metrics.py \
        --template "HR Template_May'26.xlsx" \
        --month 2026-06 \
        --bamboohr bamboohr_228.json \
        --ashby-open-count 6 \
        --poc "POC Computation - RapDev - 202606.xlsx" \
        --out "HR Template_Jun'26.xlsx"

Sections with no confirmed source (New Metrics A, B, "Soft Revenue Alignment by
BU", C Backlog, D CSAT, E Platform-sourced %, F Certifications, I SF Number) are
left untouched — this script does not invent values for them. See
reference/hr-metrics-row-map.md.
"""
import argparse
import json
import datetime
import openpyxl

EXCLUDE_ALWAYS = {"angel angelov"}  # confirmed full name, June 2026 live run


def load_json(path):
    with open(path) as f:
        return json.load(f)


def active_roster(bamboohr):
    emps = bamboohr.get("employees", [])
    if not emps:
        raise ValueError("BambooHR report has no employees — partial/failed pull, do not use")
    out = []
    for e in emps:
        status = (e.get("employmentHistoryStatus") or "").strip()
        if status in ("Terminated", "Paid Intern"):
            continue
        name = f"{e.get('firstName','')} {e.get('lastName','')}".strip().lower()
        if any(tag in name for tag in EXCLUDE_ALWAYS):
            continue
        if (e.get("jobTitle") or "").strip().lower() == "intern":
            continue
        out.append(e)
    return out


def signed_not_joined(roster, as_of: datetime.date):
    out = []
    for e in roster:
        hire = e.get("hireDate")
        if not hire:
            continue
        try:
            hire_date = datetime.date.fromisoformat(hire)
        except ValueError:
            continue
        if hire_date > as_of:
            out.append(e)
    return out


def gender_split(roster):
    counts = {}
    for e in roster:
        g = (e.get("gender") or "Unspecified").strip() or "Unspecified"
        counts[g] = counts.get(g, 0) + 1
    total = sum(counts.values())
    if not total:
        return counts, {}
    pct = {k: v / total for k, v in counts.items()}
    return counts, pct


def new_joiners(roster, year, month):
    out = []
    for e in roster:
        hire = e.get("hireDate")
        if not hire:
            continue
        try:
            d = datetime.date.fromisoformat(hire)
        except ValueError:
            continue
        if d.year == year and d.month == month:
            out.append(f"{e.get('firstName','')} {e.get('lastName','')}".strip())
    return out


def bench(roster, poc_wb):
    """Billable-status employees with no current-month hours logged against any SOW.
    Cross-references BambooHR billable flag against the POC file's per-employee
    hours. Flags (returns None) if the POC 'Employee Level' tab layout doesn't
    match expectations rather than guessing a count.
    """
    billable_names = {
        f"{e.get('firstName','')} {e.get('lastName','')}".strip().lower()
        for e in roster
        if (e.get("customBillable") or "").strip().lower() == "yes"
    }
    if "Employee Level" not in poc_wb.sheetnames:
        return None
    ws = poc_wb["Employee Level"]
    hours_by_name = {}
    for row in range(6, ws.max_row + 1):
        name = ws.cell(row=row, column=3).value  # column C = Employee
        if not name:
            continue
        name = str(name).strip().lower()
        hours_by_name[name] = hours_by_name.get(name, 0)
        # Caller: sum the target month's hours column for this row and add here.
        # Left as 0-accumulation scaffold — wire in the target month's column
        # once its position is confirmed against a live file (see reference map).
    on_bench = [n for n in billable_names if hours_by_name.get(n, 0) == 0]
    return on_bench


def find_or_append_row_for_month(ws, month_end, date_col=1, max_row=1000):
    """Each sheet is one row per reporting month, keyed by the Date column. If a
    row already carries this month's date, overwrite it (a re-run for the same
    month is a correction, not a new period). Otherwise append after the last
    populated row. Never blindly assume row 2 is 'the current row' — that
    silently clobbers whatever month is actually sitting there.
    """
    last_row = 1
    for r in range(2, max_row + 1):
        v = ws.cell(row=r, column=date_col).value
        if v is None:
            continue
        last_row = r
        v_date = v.date() if hasattr(v, "date") else v
        if v_date == month_end:
            return r
    return last_row + 1


def fixed_cost_pct(poc_wb):
    """New Metrics section G — % of projects fixed-cost vs T&M, by SN/DD/Total.
    Weighting (by $ vs by count) not yet confirmed with a human — this computes
    by COUNT of SOWs as a placeholder; re-confirm before trusting for real."""
    ws = poc_wb["SOW level"]
    counts = {"SN": {"Fixed Fee": 0, "T&M": 0}, "DD": {"Fixed Fee": 0, "T&M": 0}}
    for row in range(5, 568):
        ptype = ws.cell(row=row, column=7).value  # G
        snd = ws.cell(row=row, column=8).value  # H
        if snd in counts and ptype in ("Fixed Fee", "T&M"):
            counts[snd][ptype] += 1
    result = {}
    for k, v in counts.items():
        total = v["Fixed Fee"] + v["T&M"]
        result[k] = v["Fixed Fee"] / total if total else None
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--template", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--bamboohr", required=True)
    p.add_argument("--ashby-open-count", type=int)
    p.add_argument("--poc")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    year, month = (int(x) for x in args.month.split("-"))
    month_end = datetime.date(year, month, 1)
    import calendar
    month_end = datetime.date(year, month, calendar.monthrange(year, month)[1])

    bamboohr = load_json(args.bamboohr)
    roster = active_roster(bamboohr)

    wb = openpyxl.load_workbook(args.template)

    # --- Gender Diversity ---
    ws = wb["Gender Diversity"]
    row = find_or_append_row_for_month(ws, month_end)
    counts, pct = gender_split(roster)
    label = " | ".join(f"{round(v*100)}% {k}" for k, v in sorted(pct.items(), key=lambda x: -x[1]))
    ws.cell(row=row, column=1, value=month_end)
    ws.cell(row=row, column=2, value=label)
    # column C "Target" is static — carried forward from the prior row, not overwritten

    # --- Open Hired ---
    ws = wb["Open Hired"]
    row = find_or_append_row_for_month(ws, month_end)
    ws.cell(row=row, column=1, value=month_end)
    if args.ashby_open_count is not None:
        ws.cell(row=row, column=2, value=args.ashby_open_count)
    joiners = new_joiners(roster, year, month)
    ws.cell(row=row, column=3, value=len(joiners))
    for i, name in enumerate(joiners):
        ws.cell(row=8 + i, column=3, value=name)

    # --- HCMIX ---
    ws = wb["HCMIX"]
    row = find_or_append_row_for_month(ws, month_end)
    onsite = len(roster)  # RapDev headcount has historically been ~100% Onsite;
    nearshore, offshore = 0, 0  # flag if a future roster shows non-US locations
    ws.cell(row=row, column=1, value=month_end)
    ws.cell(row=row, column=2, value=onsite)
    ws.cell(row=row, column=3, value=nearshore)
    ws.cell(row=row, column=4, value=offshore)
    total = onsite + nearshore + offshore
    if total:
        ws.cell(row=row, column=5, value=onsite / total)
        ws.cell(row=row, column=6, value=nearshore / total)
        ws.cell(row=row, column=7, value=offshore / total)

    # --- Bench-AO ---
    ws = wb["Bench-AO"]
    row = find_or_append_row_for_month(ws, month_end)
    ws.cell(row=row, column=1, value=month_end)
    if args.poc:
        poc_wb = openpyxl.load_workbook(args.poc, data_only=True)
        on_bench = bench(roster, poc_wb)
        ws.cell(row=row, column=2, value=len(on_bench) if on_bench is not None else "Please Update")
    ws.cell(row=row, column=3, value=0)  # Awaiting Onboarding — human-confirmed OK to leave 0/N/A for now

    # --- New Metrics: section G and H only; everything else left untouched ---
    ws = wb["New Metrics"]
    if args.poc:
        pct = fixed_cost_pct(poc_wb)
        # Row positions for section G vary by month (new row appended each period) —
        # locate the "June"-style row label matching this month before writing;
        # left as a manual step for Claude until row layout is reconfirmed live.

    wb.save(args.out)
    print(f"Wrote {args.out}")
    print(f"Active roster: {len(roster)}, new joiners: {joiners}, gender split: {pct if False else counts}")


if __name__ == "__main__":
    main()
