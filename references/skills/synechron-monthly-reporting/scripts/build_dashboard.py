"""Build one month's column into the Synechron dashboard ("Slide 15 - RapDev" sheet).

No network access. Claude pulls QBO/BambooHR data and hands this script saved
JSON files plus the POC/Forecast xlsx files and the prior month's full dashboard
template. This script never overwrites a prior-period column and never touches
the BH:BM "Old Forecast" scratch block.

Usage:
    python build_dashboard.py \
        --template "RapDev Dashboard template_May'26.xlsx" \
        --month 2026-06 \
        --pnl-plain pnl_plain.json \
        --pnl-by-class pnl_by_class.json \
        --pnl-by-customer pnl_by_customer.json \
        --ar-aging ar_aging.json \
        --mwe-je-amount 29048.31 \
        --bamboohr bamboohr_228.json \
        --poc "POC Computation - RapDev - 202606.xlsx" \
        --out "RapDev Dashboard template_Jun'26.xlsx"

Forecast columns ("(F)") are a separate, optional step — pass --forecast only
when the human has told you new forecast numbers are needed.
"""
import argparse
import json
import sys
import datetime
import openpyxl

from column_utils import (
    business_days_in_month,
    dashboard_actuals_header_candidates,
    find_column_by_header,
    poc_utilization_column,
    poc_rate_row_column,
    month_end,
)

SHEET = "Slide 15 - RapDev"
HEADER_ROW = 5

ROW_REVENUE = 6
ROW_AVG_WORKING_DAYS = 7
ROW_GM = 11
ROW_ADJ_EBITDA = 14
ROW_AVG_BILLING_RATE = 21  # live template has always carried this in the "Onsite" row, not row 20 (label row) — confirmed with human 2026-07
ROW_UTILIZATION = 52
ROW_UNBILLED_AR = 54
ROW_TM = 55
ROW_TM_0_60 = 56
ROW_FP = 60
ROW_FP_0_60 = 61
ROW_OVERDUE_AR = 66


def load_json(path):
    with open(path) as f:
        return json.load(f)


def flatten_pnl(node, out=None):
    """Recursively flatten a QBO P&L report JSON into {label.lower(): amount}.
    Captures both leaf Data rows and Section Summary totals."""
    if out is None:
        out = {}
    rows = node.get("Rows", {}).get("Row", []) if isinstance(node, dict) else node
    for row in rows:
        if row.get("type") == "Data":
            cols = row["ColData"]
            label = cols[0].get("value", "").strip()
            try:
                amount = float(cols[-1].get("value", "0") or 0)
            except ValueError:
                amount = None
            if label and amount is not None:
                out[label.lower()] = amount
        if "Rows" in row:
            flatten_pnl(row, out)
        if "Summary" in row:
            cols = row["Summary"]["ColData"]
            label = cols[0].get("value", "").strip()
            try:
                amount = float(cols[-1].get("value", "0") or 0)
            except ValueError:
                amount = None
            if label and amount is not None:
                out[label.lower()] = amount
    return out


def get_amount(flat, *candidates):
    for c in candidates:
        if c.lower() in flat:
            return flat[c.lower()]
    return None


def compute_adjusted_ebitda(flat, mwe_je_amount):
    net_income = get_amount(flat, "Net Income")
    depr_equip = get_amount(flat, "Depr Exp- Equipment") or 0
    depr_ff = get_amount(flat, "Depr Exp- Furniture & Fixtures") or 0
    interest_rou = get_amount(flat, "Interest Expense - ROU Asset Office Lease") or 0
    taxes = get_amount(flat, "Taxes") or 0
    if net_income is None:
        raise ValueError("Net Income not found in P&L — flag, do not guess")
    return net_income + depr_equip + depr_ff + interest_rou + taxes + mwe_je_amount


def compute_overdue_ar(ar_aging_flat_total, ar_aging_flat_current):
    if ar_aging_flat_total in (None, 0):
        return None
    return (ar_aging_flat_total - ar_aging_flat_current) / ar_aging_flat_total


def compute_unbilled_ar(poc_wb, target_month_end):
    ws = poc_wb["SOW level"]
    # Row 4's date header repeats across multiple unrelated blocks (Rate, Hours, etc.) —
    # a blind row-4 scan can land on the wrong block. Anchor on the "Unbilled/Deferred
    # Balance" block label in row 3 first (only set on that block's leftmost column, per
    # poc-forecast-map.md's CU:DL range), then scan for the date match within that block only.
    block_start = None
    for col in range(1, 200):
        v = ws.cell(row=3, column=col).value
        if isinstance(v, str) and "unbilled/deferred balance" in v.lower():
            block_start = col
            break
    if block_start is None:
        raise ValueError(
            "Could not find 'Unbilled/Deferred Balance' block header in 'SOW level' row 3 — "
            "flag, tab layout may have drifted"
        )
    target_col = None
    for col in range(block_start, block_start + 60):
        v = ws.cell(row=4, column=col).value
        if isinstance(v, datetime.datetime) and v.date() == target_month_end:
            target_col = col
            break
        if isinstance(v, datetime.date) and v == target_month_end:
            target_col = col
            break
    if target_col is None:
        raise ValueError(
            f"Could not find Unbilled/Deferred Balance column for {target_month_end} "
            "in 'SOW level' row 4 — flag, tab layout may have drifted"
        )
    tm_total, fp_total = 0.0, 0.0
    for row in range(5, 568):  # 568 = 'Total' row per reference map
        project_type = ws.cell(row=row, column=7).value  # column G
        val = ws.cell(row=row, column=target_col).value
        if not isinstance(val, (int, float)) or val <= 0:
            # Column nets the unbilled asset against deferred revenue (a liability).
            # Only positive rows are the unbilled-receivable ASSET; negative rows are
            # deferred revenue sitting in a different GL account and don't belong in
            # this dashboard's Unbilled AR figure. Confirmed 2026-07: summing only
            # positive T&M/FP rows reproduces QBO's "Unbilled Receivables" (AcctNum
            # 12140) JE "ContractAssetRC{YYYYMM}" amount to the penny.
            continue
        if project_type == "T&M":
            tm_total += val
        elif project_type == "Fixed Fee":
            fp_total += val
    return tm_total, fp_total


def compute_utilization(poc_wb, year, month):
    ws = poc_wb["Employee Utilization"]
    col = poc_utilization_column(year, month)
    val = ws.cell(row=197, column=col).value
    if not isinstance(val, (int, float)):
        raise ValueError(
            f"Utilization row 197 col {col} did not resolve to a number ({val!r}) — "
            "flag, POC file layout may have drifted"
        )
    return val


def compute_avg_billing_rate(poc_wb, year, month):
    ws = poc_wb["SOW level"]
    col = poc_rate_row_column(ws, year, month)
    if col is None:
        raise ValueError("Could not find matching month-end date for Avg Billing Rate row 574")
    val = ws.cell(row=574, column=col).value
    if not isinstance(val, (int, float)):
        raise ValueError(f"Avg Billing Rate row 574 col {col} not numeric ({val!r})")
    return val


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--template", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--pnl-plain", required=True)
    p.add_argument("--pnl-by-class")
    p.add_argument("--pnl-by-customer")
    p.add_argument("--ar-aging")
    p.add_argument("--mwe-je-amount", type=float, required=True)
    p.add_argument("--poc", required=True)
    p.add_argument("--qbo-unbilled-ar-balance", type=float,
                    help="QBO 'Unbilled Receivables' GL account (AcctNum 12140) balance as of "
                         "month-end, for cross-checking the POC-derived T&M+FP total — flags, "
                         "does not block, on mismatch")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    year, month = (int(x) for x in args.month.split("-"))
    candidates = dashboard_actuals_header_candidates(year, month)

    wb = openpyxl.load_workbook(args.template)
    ws = wb[SHEET]
    col = find_column_by_header(ws, HEADER_ROW, candidates)
    if col is None:
        print(f"FLAG: could not find a column header matching {candidates} in row {HEADER_ROW} — "
              "refusing to write. Confirm the template already has this month's column added.",
              file=sys.stderr)
        sys.exit(1)
    target_header = ws.cell(row=HEADER_ROW, column=col).value

    flat = flatten_pnl(load_json(args.pnl_plain))
    revenue = get_amount(flat, "Total Income")
    gm = get_amount(flat, "Gross Profit")
    adj_ebitda = compute_adjusted_ebitda(flat, args.mwe_je_amount)

    ws.cell(row=ROW_REVENUE, column=col, value=revenue / 1_000_000 if revenue else None)
    ws.cell(row=ROW_GM, column=col, value=gm / 1_000_000 if gm else None)
    ws.cell(row=ROW_ADJ_EBITDA, column=col, value=adj_ebitda / 1_000_000)
    ws.cell(row=ROW_AVG_WORKING_DAYS, column=col, value=business_days_in_month(year, month))
    ws.cell(row=77, column=col, value=0)  # % Sub-prime, always 0

    if args.ar_aging:
        aging = load_json(args.ar_aging)
        # Caller is responsible for locating Total/Current from the AR Aging Summary
        # report shape and passing pre-extracted numbers; left as a flag if absent.
        total_ar = aging.get("total_ar")
        current_ar = aging.get("current_ar")
        overdue_pct = compute_overdue_ar(total_ar, current_ar)
        if overdue_pct is not None:
            ws.cell(row=ROW_OVERDUE_AR, column=col, value=overdue_pct)
        else:
            print("FLAG: Overdue AR not computed — total_ar/current_ar missing from --ar-aging JSON",
                  file=sys.stderr)

    poc_wb = openpyxl.load_workbook(args.poc, data_only=True)
    tme = month_end(year, month)
    tm_total, fp_total = compute_unbilled_ar(poc_wb, tme)
    if args.qbo_unbilled_ar_balance is not None:
        diff = (tm_total + fp_total) - args.qbo_unbilled_ar_balance
        if abs(diff) > 100:
            print(f"FLAG: POC-derived Unbilled AR (T&M {tm_total:.2f} + FP {fp_total:.2f} = "
                  f"{tm_total + fp_total:.2f}) differs from QBO Unbilled Receivables balance "
                  f"({args.qbo_unbilled_ar_balance:.2f}) by {diff:.2f} — reconcile before trusting.",
                  file=sys.stderr)
    ws.cell(row=ROW_TM_0_60, column=col, value=tm_total / 1_000_000)
    ws.cell(row=ROW_FP_0_60, column=col, value=fp_total / 1_000_000)
    # 61-90 / 91-180 / >181 rows (57-59, 62-64) intentionally left at 0 — always 0 per methodology
    for r in (57, 58, 59, 62, 63, 64):
        ws.cell(row=r, column=col, value=0)

    ws.cell(row=ROW_UTILIZATION, column=col, value=compute_utilization(poc_wb, year, month))
    ws.cell(row=ROW_AVG_BILLING_RATE, column=col, value=compute_avg_billing_rate(poc_wb, year, month))
    # rows 21-23 intentionally left blank — do not write

    # Headcount (26-37), Average Salary (68-75), T&M%/FP% (79-80), Top 5 Accounts (82-84),
    # Revenue by Services (85-88): left for Claude to write directly from the BambooHR pull
    # and pnl-by-class/pnl-by-customer JSON, since these need the region-classification and
    # customer/class mapping logic that isn't a fixed cell lookup. See SKILL.md steps 4-6.

    wb.save(args.out)
    print(f"Wrote column {col} ('{target_header}') to {args.out}")
    print(f"Revenue={revenue}, GM={gm}, Adj EBITDA={adj_ebitda}, "
          f"Unbilled AR T&M={tm_total}, FP={fp_total}")


if __name__ == "__main__":
    main()
