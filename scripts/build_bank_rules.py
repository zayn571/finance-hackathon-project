"""
Extract the QuickBooks bank rules into src/data/qboBankRules.json, preserving
priority.

QuickBooks has no priority column — it applies bank rules in the order they
appear in the rule list, first match wins. The export preserves that order, so
the row index IS the priority, and it is carried through as `priority` (1 =
evaluated first).

Condition/action codes observed in the export:
  condition ruleType 10 -> account scope ("-1" = all accounts)
  condition ruleType  6 -> description contains
  condition ruleType  1 -> bank text contains (treated the same as 6)
  action    actionType 0 -> account / category
  action    actionType 2 -> class / department
  action    actionType 5 -> payee
"""

import json
import openpyxl

SRC = "references/skills/brex-import/references/qbo-bank-rules.xlsx"
OUT = "src/data/qboBankRules.json"

TEXT_CONDITION_TYPES = {1, 6}

wb = openpyxl.load_workbook(SRC, data_only=True)
rows = list(wb.active.iter_rows(values_only=True))[1:]

rules = []
for idx, r in enumerate(rows, start=1):
    name = r[0]
    conds = acts = None
    for c in r[1:]:
        if not isinstance(c, str):
            continue
        if '"ruleConditions"' in c:
            conds = json.loads(c)
        elif '"ruleActions"' in c:
            acts = json.loads(c)
    if not conds or not acts:
        continue

    patterns = [
        str(cc["value"])
        for cc in conds.get("ruleConditions", [])
        if cc.get("ruleType") in TEXT_CONDITION_TYPES and cc.get("value")
    ]
    if not patterns:
        continue

    a = {aa["actionType"]: aa["value"] for aa in acts.get("ruleActions", [])}
    account = a.get(0)
    if not account:
        continue

    rules.append(
        {
            "priority": idx,
            "name": name,
            "patterns": patterns,
            # every pattern must appear when isAndRule is set
            "requireAll": bool(conds.get("isAndRule")) and len(patterns) > 1,
            "account": account,
            "subCategory": str(account).split(":")[-1],
            "department": a.get(2),
            "payee": a.get(5),
        }
    )

json.dump(
    {
        "source": "QuickBooks Online bank rules export, order preserved as priority (1 = evaluated first)",
        "count": len(rules),
        "rules": rules,
    },
    open(OUT, "w"),
    indent=1,
)
print(f"wrote {len(rules)} rules to {OUT}")

# quick sanity: which rule wins for the Brex Uber Eats descriptor
desc = "UBER   *EATS MASTERCARD-XXXXXX6XYIJ8-Ryan Henrich".lower()
for rule in rules:
    pats = [p.lower() for p in rule["patterns"]]
    hit = all(p in desc for p in pats) if rule["requireAll"] else any(p in desc for p in pats)
    if hit:
        print(f"first match for Uber Eats descriptor: #{rule['priority']} {rule['name']!r} -> {rule['subCategory']}")
        break
