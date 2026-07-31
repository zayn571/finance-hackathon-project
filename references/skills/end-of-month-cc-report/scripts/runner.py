#!/usr/bin/env python3
"""End-of-month CC report orchestration. Architecture mirrors brex-import:
Python scripts have NO network access - the orchestrator (Claude) calls the
quickbooks_transaction_detail_by_account MCP tool, the report JSON persists
to a tool-results file, and this runner parses/resolves/builds from disk.

Subcommands:
  parse    <QBO report JSON files, one per account> -> parsed.json
  resolve  parsed.json -> resolved.json (+ prints the completeness gate)
  build    resolved.json -> master + 8 manager xlsx files
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract
import resolve as resolve_mod
import build_pivot
import deliver as deliver_mod

DROP_TYPES = {"Credit Card Payment", "Journal Entry"}
KEEP_TYPES = {"Expense", "Credit Card Credit"}
BREX_ACCOUNT_LABEL = "Brex Credit Card"

MANAGERS = [
    "Jay Barker", "Connor/JT", "Jesse/Scott", "Elias Kapetanopoulos",
    "Ayaan Israni", "Elyse Neumeier", "Toni Manning", "Kevin Ebert",
]
KEVIN_INCLUDES = {"Kevin Ebert", "Connor/JT", "Jesse/Scott"}

# short manager labels for filenames, matching the pre-existing "Amex Spend
# {period} - {label}.xlsx" deliverables in Drive (confirmed by Zayn 2026-07-01)
MANAGER_FILE_LABEL = {
    "Jay Barker": "Jay", "Connor/JT": "Connor-JT", "Jesse/Scott": "Jesse-Scott",
    "Elias Kapetanopoulos": "Eli", "Ayaan Israni": "Ayaan",
    "Elyse Neumeier": "Elyse", "Toni Manning": "Toni", "Kevin Ebert": "Kevin",
}


def _walk_rows(rownode, account_label):
    for row in rownode.get("Row", []):
        if "ColData" in row and "Rows" not in row:
            cd = row["ColData"]
            yield {
                "account": account_label,
                "date": cd[0].get("value", ""),
                "txn_type": cd[1].get("value", ""),
                "name": cd[3].get("value", ""),
                "memo": cd[5].get("value", ""),
                "split": cd[6].get("value", ""),
                "amount": cd[7].get("value", ""),
            }
        elif "Rows" in row:
            yield from _walk_rows(row["Rows"], account_label)


def _load_report(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list) and data and "text" in data[0]:
        return json.loads(data[0]["text"])
    return data


def cmd_parse(args):
    all_rows = []
    account_counts = {}
    for account_label, path in args.report:
        report = _load_report(path)
        rows = list(_walk_rows(report.get("Rows", {}), account_label))
        account_counts[account_label] = len(rows)
        all_rows.extend(rows)

    classified = [r for r in all_rows if r["txn_type"] in KEEP_TYPES]
    dropped = len(all_rows) - len(classified)
    unexpected = [r for r in classified if r["txn_type"] not in KEEP_TYPES]

    out_rows = []
    for r in classified:
        raw_name = extract.extract_name(r["memo"])
        out_rows.append({
            **r,
            "amount": float(r["amount"]) if r["amount"] not in ("", None) else 0.0,
            "card_member_raw": raw_name,
            "description": extract.extract_merchant(r["memo"]),
            "category": extract.extract_category(r["split"]),
            "last4": extract.extract_last4(r["memo"]),
        })

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    json.dump(out_rows, open(args.out, "w"), indent=1)

    print("=== Pull ===")
    for label, cnt in account_counts.items():
        print(f"  {label}: {cnt} raw rows")
    print(f"Kept (Expense/Credit Card Credit): {len(classified)}  (dropped {dropped} payments/JEs)")
    uncategorized = [r for r in classified if "uncategorized" in r["split"].lower()
                      or "ask my accountant" in r["split"].lower()]
    blank_memo = [r for r in classified if not r["memo"].strip()]
    print(f"Uncategorized/Ask My Accountant: {len(uncategorized)}")
    print(f"Blank-descriptor rows: {len(blank_memo)}")
    if not all(v > 0 for v in account_counts.values()):
        print("GATE FAILED: at least one account returned zero rows - stop and report (root §7).")
        sys.exit(1)
    if blank_memo:
        print("GATE WARNING: blank-descriptor rows present - review before proceeding.")
    print(f"Wrote {len(out_rows)} rows -> {args.out}")


def cmd_resolve(args):
    rows = json.load(open(args.rows))
    mgr_mapping = resolve_mod.load_manager_mapping_sheet(args.manager_mapping_workbook)
    realized = resolve_mod.load_realized_mapping(args.realized_mapping_workbook or args.manager_mapping_workbook)
    card_mapping = resolve_mod.load_card_mapping(args.card_mapping) if args.card_mapping else {}
    resolver = resolve_mod.Resolver(mgr_mapping, realized, card_mapping)

    for r in rows:
        canon, mgr, method = resolver.resolve(r["card_member_raw"])
        if mgr is None and r["account"] != BREX_ACCOUNT_LABEL and r.get("last4"):
            canon, mgr, method = resolver.resolve_amex_by_last4(r["last4"])
            if method != "unmapped":
                method = f"card-mapping(last4={r['last4']})/{method}"
        r["card_member"] = canon
        r["manager"] = mgr
        r["resolve_method"] = method

    card_mapping_names = set(card_mapping.values())
    manager_mapping_names = {row["name"].title() if row["name"].isupper() else row["name"]
                              for row in mgr_mapping}
    rename_log, flagged = resolve_mod.consolidate_names(rows, card_mapping_names, manager_mapping_names)

    total = len(rows)
    mapped = [r for r in rows if r["manager"]]
    unmapped = [r for r in rows if not r["manager"]]
    name_matched = [r for r in rows if r["card_member_raw"]]

    print("=== Resolve ===")
    print(f"Name extracted: {len(name_matched)}/{total} ({100 * len(name_matched) / total:.1f}%)")
    print(f"Resolved to a manager: {len(mapped)}/{total} ({100 * len(mapped) / total:.1f}%)  "
          f"${sum(r['amount'] for r in mapped):,.2f}")
    print(f"Unresolved (exceptions): {len(unmapped)}  ${sum(r['amount'] for r in unmapped):,.2f}")
    if rename_log:
        print(f"\nName variants consolidated ({len(rename_log)}):")
        for old, new, source in rename_log:
            print(f"  {old!r} -> {new!r}  (per {source})")
    if flagged:
        print(f"\nFLAGGED - ambiguous spelling variants, left unmerged, needs a human call:")
        for members in flagged:
            print(f"  {members}")

    # gate: name-match must not collapse silently - if it's far below what
    # Brex alone should give (see routing-overrides.md: ~96% verified), stop.
    brex_rows = [r for r in rows if r["account"] == BREX_ACCOUNT_LABEL]
    brex_matched = [r for r in brex_rows if r["card_member_raw"]]
    if brex_rows:
        brex_pct = 100 * len(brex_matched) / len(brex_rows)
        print(f"\nBrex name-match %: {brex_pct:.1f}% (expect ~95%+; if far lower, the descriptor "
              f"format may have changed again - stop and report, don't build on top of it)")
        if brex_pct < 80:
            print("GATE FAILED: Brex name-match rate has regressed well below the verified baseline.")
            sys.exit(1)

    json.dump(rows, open(args.out, "w"), indent=1)
    print(f"\nWrote {len(rows)} resolved rows -> {args.out}")


def cmd_build(args):
    rows = json.load(open(args.rows))
    for r in rows:
        if "date_str" not in r:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
            r["date_str"] = d.strftime("%m/%d/%Y")
            r["month"], r["year"] = d.month, d.year
        r.setdefault("account_label", r.get("account"))

    os.makedirs(args.out_dir, exist_ok=True)
    results = []

    master_path = os.path.join(args.out_dir, f"Amex Spend {args.period} - MASTER.xlsx")
    build_pivot.build_workbook(rows, args.template, master_path)
    build_pivot.validate_workbook(master_path)
    results.append(("MASTER", master_path))

    for mgr in MANAGERS:
        if mgr == "Kevin Ebert":
            mgr_rows = [r for r in rows if r["manager"] in KEVIN_INCLUDES]
        else:
            mgr_rows = [r for r in rows if r["manager"] == mgr]
        path = os.path.join(args.out_dir, f"Amex Spend {args.period} - {MANAGER_FILE_LABEL[mgr]}.xlsx")
        build_pivot.build_workbook(mgr_rows, args.template, path)
        build_pivot.validate_workbook(path)
        results.append((mgr, path))

    exc_rows = [r for r in rows if not r["manager"]]
    exc_path = os.path.join(args.out_dir, f"Amex Spend {args.period} - Exceptions.xlsx")
    build_pivot.build_workbook(exc_rows, args.template, exc_path)
    build_pivot.validate_workbook(exc_path)
    results.append(("Exceptions", exc_path))

    print("=== Build ===")
    for label, path in results:
        print(f"  {label}: {path}")

    total = sum(r["amount"] for r in rows)
    routed = sum(r["amount"] for r in rows if r["manager"])
    exc_total = sum(r["amount"] for r in exc_rows)
    print(f"\nReconciliation: total=${total:,.2f}  routed=${routed:,.2f}  "
          f"exceptions=${exc_total:,.2f}  matches={'YES' if abs(routed + exc_total - total) < 0.01 else 'NO - INVESTIGATE'}")


def cmd_deliver(args):
    plan = deliver_mod.build_delivery_plan(args.out_dir, args.period)
    os.makedirs(os.path.dirname(args.manifest_out) or ".", exist_ok=True)
    json.dump(plan, open(args.manifest_out, "w"), indent=1)

    print("=== Delivery manifest ===")
    for entry in plan:
        print(f"  {entry['label']}: {entry['filename']} -> folder {entry['folder_id']}")
    print(f"\nWrote {len(plan)} entries -> {args.manifest_out}")
    print("\nPresent this manifest for approval (root CLAUDE.md §3, SKILL.md §8) before "
          "uploading anything. On approval, upload each entry using its 'filename' field "
          "verbatim - never retype it - with disable_conversion_to_google_type=True.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_parse = sub.add_parser("parse", help="parse saved QBO report JSON files into classified rows")
    p_parse.add_argument("--report", nargs=2, action="append", metavar=("ACCOUNT_LABEL", "PATH"),
                          required=True, help="repeatable: one per account, e.g. --report 'Brex Credit Card' path.json")
    p_parse.add_argument("--out", required=True)
    p_parse.set_defaults(func=cmd_parse)

    p_resolve = sub.add_parser("resolve", help="resolve cardholder -> manager")
    p_resolve.add_argument("--rows", required=True)
    p_resolve.add_argument("--manager-mapping-workbook", required=True,
                            help="latest master or any per-manager workbook - reads its Manager Mapping + Amex Txn Details tabs")
    p_resolve.add_argument("--realized-mapping-workbook", help="defaults to --manager-mapping-workbook")
    p_resolve.add_argument("--card-mapping", help="references/card-mapping.tsv")
    p_resolve.add_argument("--out", required=True)
    p_resolve.set_defaults(func=cmd_resolve)

    p_build = sub.add_parser("build", help="build master + 8 manager xlsx files")
    p_build.add_argument("--rows", required=True)
    p_build.add_argument("--template", required=True, help="references/manager-file-template.xlsx")
    p_build.add_argument("--out-dir", required=True)
    p_build.add_argument("--period", required=True,
                          help="display period for filenames, e.g. 'Jan-Jun 2026' (per SKILL.md naming)")
    p_build.set_defaults(func=cmd_build)

    p_deliver = sub.add_parser("deliver", help="build the Drive delivery manifest from an out-dir + period")
    p_deliver.add_argument("--out-dir", required=True, help="same --out-dir passed to `build`")
    p_deliver.add_argument("--period", required=True, help="same --period passed to `build`, e.g. 'Jan-Jun 2026'")
    p_deliver.add_argument("--manifest-out", required=True)
    p_deliver.set_defaults(func=cmd_deliver)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
