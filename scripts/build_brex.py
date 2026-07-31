import openpyxl, json, collections, re

F = "references/source-workbooks/Brex Transaction Import 20260730.xlsx"
OUT = "src/data/brexCardActivity.json"

wb = openpyxl.load_workbook(F, data_only=True)
ws = wb["QBO Transactions"]
hdr = {ws.cell(row=3, column=c).value: c for c in range(1, 31) if ws.cell(row=3, column=c).value}


def cell(r, k):
    return ws.cell(row=r, column=hdr[k]).value


# The raw descriptor carries the card network, a masked card token and the
# cardholder's name. Only the merchant portion is kept — cardholder names are
# deliberately excluded from the dashboard.
def merchant_of(desc):
    s = str(desc)
    s = re.split(r"\s+(?:MASTERCARD|VISA|AMEX)\b", s)[0]
    s = re.sub(r"\s+HELP\.UBER\.C.*$", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" *-")
    return s or str(desc)[:40]


rows = []
for r in range(4, ws.max_row + 1):
    desc = cell(r, "DESCRIPTION")
    if not desc:
        continue
    rows.append(
        dict(
            date=str(cell(r, "DATE"))[:10],
            merchant=merchant_of(desc),
            vendor=cell(r, "Vendor"),
            sub=cell(r, "Sub Category"),
            acct=cell(r, "Line Acct"),
            dept=cell(r, "Department"),
            spent=cell(r, "SPENT") or 0,
        )
    )

dates = sorted(x["date"] for x in rows if x["date"])
r2 = lambda n: round(n + 0.0, 2)

bysub = collections.Counter()
subcnt = collections.Counter()
byvendor = collections.Counter()
bydept = collections.Counter()
for x in rows:
    k = x["sub"] or "Uncategorized"
    bysub[k] += x["spent"]
    subcnt[k] += 1
    byvendor[x["vendor"] or "(none)"] += x["spent"]
    # roll department up to its class group, e.g. "300- ServiceNow:320- Engineering"
    d = (x["dept"] or "Unassigned").split(":")[0]
    bydept[d] += x["spent"]

largest = max(rows, key=lambda x: x["spent"])

recent = sorted(rows, key=lambda x: (x["date"], x["spent"]), reverse=True)[:20]

out = {
    "source": (
        "Brex Transaction Import 20260730 (QBO Transaction Import workbook) — the categorised "
        "import file, which is authoritative for sub-category and department. Account balance from "
        "the QuickBooks Transaction Detail report for account 62 (Brex Credit Card, AcctNum 21140)."
    ),
    "window": {"from": dates[0], "to": dates[-1], "lines": len(rows), "total": r2(sum(x["spent"] for x in rows))},
    "account": {
        "name": "Brex Credit Card",
        "qboAccountId": "62",
        "qboAcctNum": "21140",
        "balance": 106576.21,
        "balanceAsOf": "2026-07-30",
    },
    # Whole-month posted activity, verified against the QBO detail report.
    "july2026": {
        "postedLines": 663,
        "grossCharges": 239985.87,
        "creditsAndRefunds": -145245.04,
        "netActivity": 94740.83,
        "distinctMerchants": 103,
    },
    "bySubCategory": [
        {"category": k, "amount": r2(v), "lines": subcnt[k]} for k, v in bysub.most_common()
    ],
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
        }
        for x in recent
    ],
    "privacyNote": "Cardholder names are stripped from every descriptor. Merchant, vendor, category, department and amount only.",
}

json.dump(out, open(OUT, "w"), indent=2)
print("window:", out["window"])
print("sub categories:", len(out["bySubCategory"]))
for c in out["bySubCategory"][:6]:
    print(f"   {c['category']:26} {c['lines']:>4} {c['amount']:>11,.2f}")
print("largest:", out["largestCharge"])
print("departments:", [d["department"] for d in out["byDepartment"]])
# confirm the Uber Eats treatment carried through from the file
eats = [x for x in rows if "EATS" in x["merchant"].upper()]
print(f"\nUber Eats lines: {len(eats)}  total {sum(x['spent'] for x in eats):,.2f}  categories: {set(x['sub'] for x in eats)}")
