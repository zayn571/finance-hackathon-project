"""
Build src/data/brexCardActivity.json from the Brex transaction import workbook.

Categorisation follows QuickBooks bank-rule priority first. QuickBooks has no
priority field — it evaluates bank rules in list order and the first match wins —
so the rules are applied in the order they were exported (see
scripts/build_bank_rules.py), and only when no rule matches does the category
already on the import file decide.

Matching semantics deliberately mirror src/lib/categorize.ts so the build-time
result and any live resolution agree: case-insensitive substring against the full
bank descriptor, all patterns required when isAndRule was set, with both sides
normalised first (whitespace runs collapsed, `*` treated as a space) so a pattern
authored as "Uber Eats" matches the real descriptor "UBER   *EATS".
"""

import collections
import json
import re

import openpyxl

SRC = "references/source-workbooks/Brex Transaction Import 20260730.xlsx"
RULES = "src/data/qboBankRules.json"
OUT = "src/data/brexCardActivity.json"

rules = json.load(open(RULES))["rules"]


def normalize(s):
    """Collapse card-network formatting so an authored pattern matches real bank text."""
    return re.sub(r"\s+", " ", str(s if s is not None else "").replace("*", " ")).strip().lower()


PREPARED = [(r, [normalize(p) for p in r["patterns"]]) for r in rules]


def resolve(descriptor, fallback_sub, fallback_acct):
    d = normalize(descriptor)
    for rule, pats in PREPARED:
        hit = all(p in d for p in pats) if rule["requireAll"] else any(p in d for p in pats)
        if hit:
            return {
                "subCategory": rule["subCategory"],
                "account": rule["account"],
                "source": "bank-rule",
                "rule": {"priority": rule["priority"], "name": rule["name"]},
            }
    return {"subCategory": fallback_sub, "account": fallback_acct, "source": "import-file", "rule": None}


# The descriptor carries the card network, a masked card token and the cardholder
# name. Only the merchant portion is kept for display — cardholder names are
# deliberately excluded from the dashboard.
def merchant_of(desc):
    s = re.split(r"\s+(?:MASTERCARD|VISA|AMEX)\b", str(desc))[0]
    s = re.sub(r"\s+HELP\.UBER\.C.*$", "", s)
    return re.sub(r"\s{2,}", " ", s).strip(" *-") or str(desc)[:40]


wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb["QBO Transactions"]
hdr = {ws.cell(row=3, column=c).value: c for c in range(1, 31) if ws.cell(row=3, column=c).value}

rows = []
for r in range(4, ws.max_row + 1):
    desc = ws.cell(row=r, column=hdr["DESCRIPTION"]).value
    if not desc:
        continue
    file_sub = ws.cell(row=r, column=hdr["Sub Category"]).value
    file_acct = ws.cell(row=r, column=hdr["Line Acct"]).value
    res = resolve(desc, file_sub, file_acct)
    rows.append(
        dict(
            date=str(ws.cell(row=r, column=hdr["DATE"]).value)[:10],
            merchant=merchant_of(desc),
            vendor=ws.cell(row=r, column=hdr["Vendor"]).value,
            sub=res["subCategory"] or "Uncategorized",
            acct=res["account"],
            source=res["source"],
            rule=res["rule"],
            fileSub=file_sub,
            dept=ws.cell(row=r, column=hdr["Department"]).value,
            spent=ws.cell(row=r, column=hdr["SPENT"]).value or 0,
        )
    )

r2 = lambda n: round(n + 0.0, 2)
dates = sorted(x["date"] for x in rows if x["date"])

bysub = collections.Counter()
subcnt = collections.Counter()
byvendor = collections.Counter()
bydept = collections.Counter()
byrule = collections.Counter()
for x in rows:
    bysub[x["sub"]] += x["spent"]
    subcnt[x["sub"]] += 1
    byvendor[x["vendor"] or "(none)"] += x["spent"]
    bydept[(x["dept"] or "Unassigned").split(":")[0]] += x["spent"]
    if x["rule"]:
        byrule[f"#{x['rule']['priority']} {x['rule']['name']}"] += 1

by_source = collections.Counter(x["source"] for x in rows)
largest = max(rows, key=lambda x: x["spent"])

out = {
    "source": (
        "Brex Transaction Import 20260730. Categories resolved by QuickBooks bank-rule priority "
        "first (first matching rule in QBO's own rule order wins); the category on the import file "
        "is used only where no rule matches. Account balance and whole-month totals from the "
        "QuickBooks Transaction Detail report for account 62 (Brex Credit Card, AcctNum 21140)."
    ),
    "window": {"from": dates[0], "to": dates[-1], "lines": len(rows), "total": r2(sum(x["spent"] for x in rows))},
    "categorization": {
        "rulesEvaluated": len(rules),
        "byBankRule": by_source.get("bank-rule", 0),
        "byImportFile": by_source.get("import-file", 0),
        "topRules": [{"rule": k, "lines": v} for k, v in byrule.most_common(6)],
    },
    "account": {
        "name": "Brex Credit Card",
        "qboAccountId": "62",
        "qboAcctNum": "21140",
        "balance": 106576.21,
        "balanceAsOf": "2026-07-30",
    },
    "july2026": {
        "postedLines": 663,
        "grossCharges": 239985.87,
        "creditsAndRefunds": -145245.04,
        "netActivity": 94740.83,
        "distinctMerchants": 103,
    },
    "bySubCategory": [{"category": k, "amount": r2(v), "lines": subcnt[k]} for k, v in bysub.most_common()],
    "byDepartment": [{"department": k, "amount": r2(v)} for k, v in bydept.most_common()],
    "topVendors": [{"vendor": k, "amount": r2(v)} for k, v in byvendor.most_common(8)],
    "largestCharge": {
        "merchant": largest["merchant"],
        "vendor": largest["vendor"],
        "amount": r2(largest["spent"]),
        "date": largest["date"],
        "category": largest["sub"],
    },
    "recent": [
        {
            "date": x["date"],
            "merchant": x["merchant"],
            "vendor": x["vendor"],
            "category": x["sub"],
            "department": (x["dept"] or "Unassigned"),
            "amount": r2(x["spent"]),
            "rule": (f"#{x['rule']['priority']} {x['rule']['name']}" if x["rule"] else "import file"),
        }
        for x in sorted(rows, key=lambda x: (x["date"], x["spent"]), reverse=True)[:20]
    ],
    "privacyNote": "Cardholder names are stripped from every descriptor. Merchant, vendor, category, department and amount only.",
}

json.dump(out, open(OUT, "w"), indent=2)
print("window:", out["window"])
print("categorization:", {k: v for k, v in out["categorization"].items() if k != "topRules"})
print("top rules:", out["categorization"]["topRules"])
for c in out["bySubCategory"][:6]:
    print(f"   {c['category']:26} {c['lines']:>4} {c['amount']:>11,.2f}")
diff = [x for x in rows if x["source"] == "bank-rule" and str(x["sub"]) != str(x["fileSub"])]
print(f"\nrule result differs from the import file on {len(diff)} of {by_source.get('bank-rule', 0)} rule-matched lines")
for x in diff:
    print(f"   {x['merchant'][:30]:32} rule#{x['rule']['priority']} {x['rule']['name']:8} -> {x['sub']:22} file had {x['fileSub']}")
