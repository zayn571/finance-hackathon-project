#!/usr/bin/env python3
"""Stage the Brex accumulator to Brex_expenses.json.

Reads %TEMP%/brex_acc.json (written by brex_page.py) and writes
the accumulated expenses list to the given output path.

Usage:
    python acc_stage.py <output_path>
"""
import json, os, sys

ACC_PATH = os.path.join(os.environ.get("TEMP", "/tmp"), "brex_acc.json")

if len(sys.argv) < 2:
    sys.exit("acc_stage.py: output path required -- python acc_stage.py <output_path>")

out_path = sys.argv[1]

if not os.path.exists(ACC_PATH):
    sys.exit(f"acc_stage.py ABORT: accumulator not found at {ACC_PATH}. Run brex_page.py first.")

with open(ACC_PATH, encoding="utf-8") as f:
    acc = json.load(f)

exps = acc.get("exps", [])
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(exps, f, indent=2)

print(json.dumps({"out": out_path, "count": len(exps)}))
