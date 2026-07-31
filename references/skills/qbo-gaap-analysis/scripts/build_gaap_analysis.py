#!/usr/bin/env python3
"""
Map a QuickBooks Online Profit & Loss-by-Class report onto the GAAP Analysis tab's
row/column scheme for one target month, and emit a write plan for Claude to apply
via google_sheets_update. No network access -- see SKILL.md for the full flow.

Usage:
    python build_gaap_analysis.py --pnl <saved P&L JSON> --month 2026-06 \
        --row-map ../reference/account-row-map.csv \
        --overrides ../reference/segment-overrides.csv \
        --out write_plan.json
"""
import argparse
import csv
import json
import sys
from collections import defaultdict

# Verified 2026-07-14 against the live "GAAP Analysis" tab -- see reference/tab-layout.md.
# Column C (0-based index 2) = Jan 2020. One column per month, in order, no gaps.
FIRST_MONTH_COL_INDEX = 2
FIRST_MONTH_YEAR = 2020

CLASS_TO_SEGMENT = {
    "100- Operations": "Operations",
    "200- Datadog": "DD",
    "300- ServiceNow": "SN",
    "400- Synechron": "Synechron",
    "Not Specified": "NOT_SPECIFIED",
}

# Fixed row numbers for leaf/detail cells this skill writes. "SYN_*" placeholders resolve
# to the new Synechron block (reference/synechron-block.md) since those rows don't pre-exist.
SEGMENT_ROWS = {
    ("DD", "Services"): 15, ("DD", "Software"): 16,
    ("DD", "Managed DD"): 17, ("DD", "Managed SOC"): 18,
    ("SN", "Services"): 20, ("SN", "Software"): 21, ("SN", "MSP"): 22,
    ("DD", "COGS Payroll"): 30, ("SN", "COGS Payroll"): 35,
    ("DD", "COGS Travel"): 40, ("SN", "COGS Travel"): 41,
    ("DD", "Marketplace Fees"): 42, ("ANY", "Contractor Fees"): 43,
    ("DD", "G&A"): 71, ("SN", "G&A"): 72, ("Operations", "G&A"): 73,
    ("Synechron", "G&A"): "SYN_301",
    ("DD", "Personnel"): 75, ("SN", "Personnel"): 76, ("Operations", "Personnel"): 77,
    ("Synechron", "Personnel"): "SYN_302",
    ("DD", "S&M"): 79, ("SN", "S&M"): 80, ("Operations", "S&M"): 81,
    ("Synechron", "S&M"): "SYN_303",
    ("Operations", "Other Expenses"): 84,
}

SYNECHRON_BLOCK_LABELS = {
    300: "Synechron",
    301: "   G&A",
    302: "   Personnel",
    303: "   Sales & Marketing",
}
SYNECHRON_TOTAL_ROW = 304


def col_letter(idx0):
    """0-based column index -> A1 letter(s)."""
    idx = idx0 + 1
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def month_col_letter(year, month):
    idx0 = FIRST_MONTH_COL_INDEX + (year - FIRST_MONTH_YEAR) * 12 + (month - 1)
    if idx0 < FIRST_MONTH_COL_INDEX:
        raise ValueError(f"{year}-{month:02d} is before the tab's first column (Jan {FIRST_MONTH_YEAR})")
    return col_letter(idx0)


def walk_pnl(rows_node, class_titles, path, index):
    """Yield (path_tuple, {class_title: amount}, is_leaf) for every leaf row AND every
    group's Summary row. is_leaf=False rows are rollup totals -- only leaves should be used
    for anomaly scans like Not Specified (a rollup just restates its leaves' totals)."""
    for r in rows_node.get("Row", []):
        if r.get("type") == "Data" and "ColData" in r:
            name = r["ColData"][0].get("value", "")
            amounts = {}
            for i, cell in enumerate(r["ColData"]):
                v = cell.get("value", "")
                if v not in ("", "0.00") and 0 < i < len(class_titles):
                    amounts[class_titles[i]] = float(v)
            yield path + (name,), amounts, True
        else:
            name = r.get("Header", {}).get("ColData", [{}])[0].get("value", "")
            if "Rows" in r:
                yield from walk_pnl(r["Rows"], class_titles, path + (name,), index)
            if "Summary" in r:
                amounts = {}
                for i, cell in enumerate(r["Summary"]["ColData"]):
                    v = cell.get("value", "")
                    if v not in ("", "0.00") and 0 < i < len(class_titles):
                        amounts[class_titles[i]] = float(v)
                yield path + (name,), amounts, False


def rollup_by_segment(amounts_by_class_title):
    """Collapse QBO's per-subclass columns (e.g. 210- Delivery, 220- Engineering) into
    their parent segment using the 'Total 1XX- Y' column QBO already provides -- do not
    re-sum subclasses ourselves, the report gives us the rollup directly."""
    out = defaultdict(float)
    for title, amt in amounts_by_class_title.items():
        if title.startswith("Total "):
            class_name = title[len("Total "):]
            seg = CLASS_TO_SEGMENT.get(class_name)
            if seg:
                out[seg] += amt
        elif title in CLASS_TO_SEGMENT:
            # Not Specified and TOTAL columns have no "Total " prefix
            seg = CLASS_TO_SEGMENT.get(title)
            if seg:
                out[seg] += amt
    return out


def load_pnl(path):
    with open(path) as f:
        data = json.load(f)
    class_titles = [c.get("ColTitle") for c in data["Columns"]["Column"]]
    header = data["Header"]
    records = {}
    leaf_paths = set()
    for path_tuple, amounts, is_leaf in walk_pnl(data["Rows"], class_titles, (), 0):
        records[path_tuple] = amounts
        if is_leaf:
            leaf_paths.add(path_tuple)
    return header, records, leaf_paths


def find_by_leaf_name(records, name):
    """Find a record whose last path segment matches `name` (case-insensitive, exact)."""
    for path_tuple, amounts in records.items():
        if path_tuple and path_tuple[-1].strip().lower() == name.strip().lower():
            return path_tuple, amounts
    return None, {}


def load_overrides(path):
    overrides = {}
    with open(path) as f:
        for row in csv.DictReader(l for l in f if l.strip() and not l.lstrip().startswith("#")):
            key = (row["qbo_account"].strip(), row["qbo_subaccount"].strip())
            overrides[key] = row
    return overrides


def build_plan(records, leaf_paths, overrides, month_col):
    cells = {}     # (row, col_letter) -> amount (accumulated)
    flags = []

    def add(row, amt, note):
        if row is None or amt == 0:
            return
        key = (row, month_col)
        cells[key] = cells.get(key, 0.0) + amt

    # --- Revenue: MSP leaf accounts (Managed Datadog / Managed Security) ---
    for leaf, row in (("Managed Datadog", 17), ("Managed Security", 18)):
        _, amounts = find_by_leaf_name(records, leaf)
        seg_amounts = rollup_by_segment(amounts)
        for seg, amt in seg_amounts.items():
            if seg == "DD":
                add(row, amt, leaf)
            else:
                flags.append({"account": leaf, "segment": seg, "amount": amt,
                              "reason": f"{leaf} expected under DD only; got {seg}"})

    # --- Revenue: Software Revenue leaves, each already segment-pure in practice ---
    for leaf, expect_seg, row in (("Datadog Marketplace", "DD", 16), ("Other Software Revenue", "SN", 21)):
        _, amounts = find_by_leaf_name(records, leaf)
        seg_amounts = rollup_by_segment(amounts)
        for seg, amt in seg_amounts.items():
            if seg == expect_seg:
                add(row, amt, leaf)
            else:
                flags.append({"account": leaf, "segment": seg, "amount": amt,
                              "reason": f"{leaf} expected under {expect_seg} only; got {seg}"})

    # --- Revenue: Services Revenue group total (Fixed Fee + Time & Materials), split by segment ---
    _, amounts = find_by_leaf_name(records, "Services Revenue")
    for seg, amt in rollup_by_segment(amounts).items():
        row = SEGMENT_ROWS.get((seg, "Services"))
        if row:
            add(row, amt, "Services Revenue")
        else:
            flags.append({"account": "Services Revenue", "segment": seg, "amount": amt,
                          "reason": "No Revenue row exists for this segment"})

    # --- Revenue: Synechron Intercompany -- never auto-placed, always via overrides or flag ---
    _, ic_amounts = find_by_leaf_name(records, "Revenue- Synechron Intercompany")
    for path_tuple, sub_amounts in records.items():
        if len(path_tuple) >= 2 and path_tuple[-2] == "Revenue- Synechron Intercompany":
            subacct = path_tuple[-1]
            key = ("Revenue- Synechron Intercompany", subacct)
            if key in overrides:
                ov = overrides[key]
                add(int(ov["tab_row"]), sum(sub_amounts.values()), subacct)
            else:
                for seg, amt in rollup_by_segment(sub_amounts).items():
                    flags.append({"account": "Revenue- Synechron Intercompany", "subaccount": subacct,
                                  "segment": seg, "amount": amt,
                                  "reason": "No segment-overrides.csv entry for this subaccount -- add one or route manually"})

    # --- COGS: Personnel Expense + Synechron Intercompany lumped into COGS Payroll DD/SN ---
    for account in ("COGS- Personnel Expense", "COGS- Synechron Intercompany"):
        _, amounts = find_by_leaf_name(records, account)
        for seg, amt in rollup_by_segment(amounts).items():
            row = SEGMENT_ROWS.get((seg, "COGS Payroll"))
            if row:
                add(row, amt, account)
            else:
                flags.append({"account": account, "segment": seg, "amount": amt,
                              "reason": "No COGS Payroll row for this segment (Operations/Synechron have no COGS rows)"})

    # --- COGS: Travel ---
    _, amounts = find_by_leaf_name(records, "COGS- Travel Expenses")
    for seg, amt in rollup_by_segment(amounts).items():
        row = SEGMENT_ROWS.get((seg, "COGS Travel"))
        if row:
            add(row, amt, "COGS- Travel Expenses")
        else:
            flags.append({"account": "COGS- Travel Expenses", "segment": seg, "amount": amt,
                          "reason": "No COGS Travel row for this segment"})

    # --- COGS: Other COGS -- Marketplace Fees named row, anything else -> Contractor Fees or flag ---
    for path_tuple, sub_amounts in records.items():
        if len(path_tuple) >= 2 and path_tuple[-2] == "Other COGS":
            subacct = path_tuple[-1]
            for seg, amt in rollup_by_segment(sub_amounts).items():
                if subacct.strip().lower() == "marketplace fees":
                    if seg == "DD":
                        add(42, amt, subacct)
                    else:
                        flags.append({"account": subacct, "segment": seg, "amount": amt,
                                      "reason": "Marketplace Fees expected under DD only"})
                else:
                    flags.append({"account": subacct, "segment": seg, "amount": amt,
                                  "reason": "Unrecognized Other COGS subaccount -- confirm before assuming Contractor Fees"})

    # --- Opex: Personnel = G&A-Personnel + S&M-Personnel, combined ---
    _, gna_personnel = find_by_leaf_name(records, "G&A- Personnel Expenses")
    _, sm_personnel = find_by_leaf_name(records, "Sales & Marketing- Personnel Expenses")
    personnel_by_seg = defaultdict(float)
    for seg, amt in rollup_by_segment(gna_personnel).items():
        personnel_by_seg[seg] += amt
    for seg, amt in rollup_by_segment(sm_personnel).items():
        personnel_by_seg[seg] += amt
    for seg, amt in personnel_by_seg.items():
        row = SEGMENT_ROWS.get((seg, "Personnel"))
        add(row, amt, "Personnel (G&A + S&M)")

    # --- Opex: G&A excl. Personnel = Total G&A - G&A-Personnel ---
    _, total_gna = find_by_leaf_name(records, "General & Administrative")
    gna_total_by_seg = rollup_by_segment(total_gna)
    gna_personnel_by_seg = rollup_by_segment(gna_personnel)
    for seg, amt in gna_total_by_seg.items():
        net = amt - gna_personnel_by_seg.get(seg, 0.0)
        row = SEGMENT_ROWS.get((seg, "G&A"))
        add(row, net, "G&A excl. Personnel")

    # --- Opex: S&M excl. Personnel = Total S&M - S&M-Personnel ---
    _, total_sm = find_by_leaf_name(records, "Sales & Marketing")
    sm_total_by_seg = rollup_by_segment(total_sm)
    sm_personnel_by_seg = rollup_by_segment(sm_personnel)
    for seg, amt in sm_total_by_seg.items():
        net = amt - sm_personnel_by_seg.get(seg, 0.0)
        row = SEGMENT_ROWS.get((seg, "S&M"))
        add(row, net, "S&M excl. Personnel")

    # --- Not Specified anywhere -- always flagged, never written. Leaf rows only: a rollup
    # total's Not Specified column just restates its leaves' totals, so scanning it too would
    # multiply-count the same dollars once per ancestor group.
    for path_tuple in leaf_paths:
        ns = records[path_tuple].get("Not Specified")
        if ns:
            flags.append({"account": " > ".join(path_tuple), "segment": "Not Specified",
                          "amount": ns, "reason": "Not Specified class -- needs manual classification in QBO"})

    # --- Other Expenses (Operations only; DD/SN/Synechron dollars here are flagged) ---
    _, other_exp = find_by_leaf_name(records, "Other Expenses")
    for seg, amt in rollup_by_segment(other_exp).items():
        if seg == "Operations":
            add(84, amt, "Other Expenses")
        else:
            flags.append({"account": "Other Expenses", "segment": seg, "amount": amt,
                          "reason": "Other Expenses row has no DD/SN/Synechron split"})

    return cells, flags


def resolve_row(row_key):
    """Translate SYN_301/302/303 placeholders to their real (currently-empty) row numbers."""
    mapping = {"SYN_301": 301, "SYN_302": 302, "SYN_303": 303}
    return mapping.get(row_key, row_key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pnl", required=True, help="Path to the saved QBO P&L-by-Class JSON")
    ap.add_argument("--month", required=True, help="Target month, YYYY-MM")
    ap.add_argument("--overrides", required=True, help="Path to segment-overrides.csv")
    ap.add_argument("--out", required=True, help="Path to write the write-plan JSON")
    args = ap.parse_args()

    year, month = (int(x) for x in args.month.split("-"))
    col = month_col_letter(year, month)

    header, records, leaf_paths = load_pnl(args.pnl)
    overrides = load_overrides(args.overrides)
    cells, flags = build_plan(records, leaf_paths, overrides, col)

    write_entries = []
    for (row_key, col_letter_), amount in sorted(cells.items(), key=lambda kv: str(kv[0])):
        row = resolve_row(row_key)
        write_entries.append({"row": row, "col": col_letter_, "amount": round(amount, 2)})

    synechron_label_writes = [
        {"row": r, "col": "B", "value": label} for r, label in SYNECHRON_BLOCK_LABELS.items()
    ]
    synechron_total_formula = {
        "row": SYNECHRON_TOTAL_ROW, "col": col,
        "formula": f"=SUM({col}301:{col}303)"
    }

    plan = {
        "target_month": args.month,
        "target_col": col,
        "pnl_period": {"start": header.get("StartPeriod"), "end": header.get("EndPeriod")},
        "cell_writes": write_entries,
        "synechron_label_writes_run_once": synechron_label_writes,
        "synechron_total_formula": synechron_total_formula,
        "flags": flags,
        "flagged_total": round(sum(f["amount"] for f in flags), 2),
        "written_total": round(sum(e["amount"] for e in write_entries), 2),
    }

    with open(args.out, "w") as f:
        json.dump(plan, f, indent=2)

    print(f"Target column for {args.month}: {col}")
    print(f"Cells to write: {len(write_entries)}  (total ${plan['written_total']:,.2f})")
    print(f"Flags raised: {len(flags)}  (total ${plan['flagged_total']:,.2f})")
    if flags:
        print("!! Flagged amounts require human placement -- see write_plan.json 'flags'. !!")


if __name__ == "__main__":
    main()
