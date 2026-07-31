"""Brex feed-mode pipeline for the brex-import skill.

Replaces the CSV-export workflow with a direct Brex API pull. The orchestrator
(Claude) calls Brex/QBO MCP tools and writes JSON files. THIS SCRIPT HAS NO
NETWORK — it reads the staged JSON files and the cached qbo_rules.xlsx, then
produces categorized.json + a stdout summary.

In-scope (per spec):
    1. Brex pull        — orchestrator step
    2. Filter           — drop CANCELED/DRAFT/zero-amount
    3. Rule loader      — qbo_rules.xlsx (.xls converted by orchestrator)
    4. Match            — descriptor vs. budget.name (cardholder rules flagged)
    5. Fallback enrich  — MCC + Brex category hints

Out-of-scope — left as TODO for the next phase:
    - Reconciliation diff vs QBO posted transactions
    - Stamping Brex id into QBO memo
    - Writing the QBO upload / Transaction Import file
    - Bank-feed double-entry decision
    - Direct-write to QBO

Target QBO account for the future import half: 21140 Brex Credit Card.
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules_loader import load_rules, Rule
from resolver import (
    resolve_with_signals, merchant_from_desc,
    load_vendors, load_vendors_from_json,
)
from memory_loader import load_memory


# ---- Brex expense normalization ----

def _amount_dollars(exp: dict) -> float:
    """billing_amount is in cents (per Brex API). Returns dollars float."""
    ba = exp.get("billing_amount") or {}
    cents = ba.get("amount", 0) or 0
    return cents / 100.0


def _descriptor(exp: dict) -> str:
    merchant = exp.get("merchant") or {}
    return (merchant.get("raw_descriptor") or "").strip()


def _budget_name(exp: dict) -> str:
    """The 'cardholder' field from the prototype. Sometimes a person's name
    (e.g. 'Ayla Hourani'), sometimes a budget category ('Software & Licenses').
    Either way, the same haystack as the QBO bank-feed text used to be."""
    budget = exp.get("budget") or {}
    return (budget.get("name") or "").strip()


def _user_name(exp: dict) -> str:
    """The actual cardholder, from the Brex `user` expand. Distinct from budget.name,
    which can be a budget category ('Software & Licenses'). Populates the Card Name output
    column; budget_name stays untouched (load-bearing for cardholder-rule matching)."""
    u = exp.get("user") or {}
    return f"{(u.get('first_name') or '').strip()} {(u.get('last_name') or '').strip()}".strip()


def _mcc(exp: dict) -> str | None:
    merchant = exp.get("merchant") or {}
    code = merchant.get("mcc")
    return str(code) if code else None


def _brex_category(exp: dict) -> str | None:
    return exp.get("category")


# ---- Step 2: filter ----

def filter_expenses(expenses: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (kept, excluded). Excluded carry a reason field for the report.

    Per spec:
        - status in {CANCELED, DRAFT} → exclude
        - payment_status in {REFUNDED, REFUNDING, CREDITED} → exclude (refunds/credits, per Zayn 2026-06-15)
        - billing_amount.amount == 0  → exclude
        - payment_status != CLEARED   → KEEP (mark settlement_note), per user
          answer 2026-06-02 to "Include PROCESSING as postable"
    """
    kept: list[dict] = []
    excluded: list[dict] = []
    for e in expenses:
        if e.get("status") in ("CANCELED", "DRAFT"):
            excluded.append({**e, "_reason": f"status={e.get('status')}"})
            continue
        if e.get("payment_status") in ("REFUNDED", "REFUNDING", "CREDITED"):
            excluded.append({**e, "_reason": f"refund/credit (payment_status={e.get('payment_status')})"})
            continue
        ba = e.get("billing_amount") or {}
        if (ba.get("amount") or 0) == 0:
            excluded.append({**e, "_reason": "zero amount"})
            continue
        kept.append(e)
    return kept, excluded


# ---- Step 4: rule matching ----

def match_merchant_rule(rules: list[Rule], descriptor: str):
    """Return the longest-text rule whose text appears in the descriptor, or None.
    This is the high-confidence rule path — explicit merchant-string match."""
    desc_lc = descriptor.lower()
    for rule in rules:  # already sorted longest-text-first by rules_loader
        if rule.text_lc in desc_lc:
            return rule
    return None


def match_cardholder_rule(rules: list[Rule], budget_name: str):
    """Return the longest-text rule whose text appears in budget.name, or None.
    Cardholder rules blanket-match every purchase by a person — they're
    dangerous (one structurally-broken rule can miscategorize an entire person's
    spend), so the caller should only consult this AFTER memory.md and treat
    matches as Review/flag confidence, not High."""
    bud_lc = budget_name.lower()
    for rule in rules:
        if rule.text_lc in bud_lc:
            return rule
    return None


# Backwards-compat shim for any external callers — same signature as the
# pre-2026-06-02 single-step matcher.
def match_rule(rules: list[Rule], descriptor: str, budget_name: str):
    r = match_merchant_rule(rules, descriptor)
    if r:
        return r, "merchant"
    r = match_cardholder_rule(rules, budget_name)
    if r:
        return r, "cardholder"
    return None, None


# ---- Step 5: categorize one expense ----

def categorize_one(exp: dict, rules: list[Rule], vendors_lc: dict[str, str], memory: dict) -> dict:
    desc = _descriptor(exp)
    bud = _budget_name(exp)
    amt = _amount_dollars(exp)
    mcc = _mcc(exp)
    bcat = _brex_category(exp)
    pay_status = exp.get("payment_status")

    out = {
        "id": exp.get("id"),
        "date": (exp.get("payment_posted_at") or exp.get("purchased_at") or "")[:10],  # Brex POSTED date, not swipe (Zayn 2026-06-15)
        "descriptor": desc,
        "budget_name": bud,
        "card_name": _user_name(exp),
        "amount": amt,
        "currency": (exp.get("billing_amount") or {}).get("currency"),
        "mcc": mcc,
        "brex_category": bcat,
        "status": exp.get("status"),
        "payment_status": pay_status,
    }

    # Precedence (revised 2026-06-02):
    #   1. Merchant rule (descriptor match)        — High
    #   2. Resolver (memory.md / vendor exact)     — High if found
    #   3. Cardholder rule (budget.name match)     — Review/flag
    #   4. Resolver Medium/Low + MCC/category hint — Review/Low
    #
    # Memory.md hard-confirmed entries beat cardholder rules so that a single
    # structurally-broken cardholder rule (e.g. text="Ayla" matching every Ayla
    # Hourani purchase) can't override a user-curated mapping like
    # GOMOWORLD → Travel Vendor.
    merchant_rule = match_merchant_rule(rules, desc)
    if merchant_rule:
        out.update({
            "decision": "CATEGORIZED",
            "payee": merchant_rule.payee, "category": merchant_rule.category,
            "cls": merchant_rule.cls,
            "source": f"qbo-rule(merchant):{merchant_rule.name}",
            "confidence": "High",
            "matched_on": merchant_rule.text,
            "flag": False,
        })
    else:
        # Try the resolver — memory.md hard-confirmed entries are consulted here
        merchant = merchant_from_desc(desc) or desc
        res = resolve_with_signals(merchant, vendors_lc, memory,
                                   mcc=mcc, brex_category=bcat)
        if res["confidence"] == "High":
            # Memory hit or exact vendor match — these beat cardholder rules.
            # No QBO-rule category available, so leave "(needs review)" for GL.
            out.update({
                "decision": "CATEGORIZED",
                "payee": res["value"],
                "category": "(needs review)",
                "cls": None,
                "source": res["source"],
                "confidence": "High",
                "matched_on": res["reason"],
                "flag": False,
                "sub_category_override": res.get("memory_sub_cat"),
                "signals": res.get("signals", []),
            })
        else:
            # Resolver wasn't confident — now try cardholder rule
            cardholder_rule = match_cardholder_rule(rules, bud)
            if cardholder_rule:
                out.update({
                    "decision": "CATEGORIZED",
                    "payee": cardholder_rule.payee,
                    "category": cardholder_rule.category,
                    "cls": cardholder_rule.cls,
                    "source": f"qbo-rule(cardholder):{cardholder_rule.name}",
                    "confidence": "Review",
                    "matched_on": cardholder_rule.text,
                    "flag": True,
                    "flag_reason": (
                        "Cardholder-rule blanket match — rule text found in "
                        f"budget.name ({bud!r}) but NOT in descriptor "
                        f"({desc!r}), and memory.md had no entry. Verify."
                    ),
                })
            else:
                # No rule, no memory hit — accept resolver Medium/Low/Flag.
                # "Flag" = always-flag Brex category (UNCLASSIFIED) → treat as flagged.
                is_flag = res["confidence"] in ("Low", "Flag")
                out.update({
                    "decision": "FLAG" if is_flag else "CATEGORIZED",
                    "payee": res["value"],
                    "category": "(needs review)",
                    "cls": None,
                    "source": res["source"],
                    "confidence": res["confidence"],
                    "matched_on": res["reason"],
                    "flag": is_flag or res["confidence"] == "Review",
                    "sub_category_override": res.get("memory_sub_cat"),
                    "signals": res.get("signals", []),
                })

    # Settlement note (informational only; PROCESSING is still postable per user)
    if pay_status and pay_status != "CLEARED":
        out["settlement_note"] = f"not yet settled (payment_status={pay_status})"

    return out


# ---- Main pipeline ----

def run(brex_path: Path, rules_xlsx: Path, vendors_path: Path | None,
        memory_path: Path | None, out_path: Path) -> dict:
    expenses = json.loads(Path(brex_path).read_text())
    # Tolerate {"data": [...]} or [...]
    if isinstance(expenses, dict):
        expenses = expenses.get("data") or expenses.get("expenses") or list(expenses.values())

    rules, skipped = load_rules(Path(rules_xlsx))

    vendors_lc: dict[str, str] = {}
    if vendors_path:
        if str(vendors_path).endswith(".json"):
            vendors_lc = load_vendors_from_json(vendors_path)
        else:
            vendors_lc = load_vendors(vendors_path)

    memory: dict = {}
    if memory_path and Path(memory_path).exists():
        memory = load_memory(memory_path)

    kept, excluded = filter_expenses(expenses)
    results = [categorize_one(e, rules, vendors_lc, memory) for e in kept]
    excluded_recs = [{
        "id": e.get("id"),
        "date": (e.get("payment_posted_at") or e.get("purchased_at") or "")[:10],  # Brex POSTED date, not swipe
        "descriptor": _descriptor(e),
        "decision": "EXCLUDED",
        "reason": e["_reason"],
        "amount": _amount_dollars(e),
        "status": e.get("status"),
    } for e in excluded]

    # Summary buckets
    n_total = len(expenses)
    n_excluded = len(excluded)
    n_postable = len(results)
    n_merchant_rule = sum(1 for r in results if r["source"].startswith("qbo-rule(merchant)"))
    n_cardholder_flagged = sum(1 for r in results if r["source"].startswith("qbo-rule(cardholder)"))
    n_fallback = sum(1 for r in results if not r["source"].startswith("qbo-rule"))
    n_flagged_total = sum(1 for r in results if r.get("flag"))
    n_not_settled = sum(1 for r in results if r.get("settlement_note"))
    hit_rate_merchant = (n_merchant_rule / n_postable * 100) if n_postable else 0.0

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brex_expenses_path": str(brex_path),
        "qbo_rules_path": str(rules_xlsx),
        "vendors_path": str(vendors_path) if vendors_path else None,
        "rules_kept": len(rules),
        "rules_skipped": len(skipped),
        "totals": {
            "total_pulled": n_total,
            "excluded": n_excluded,
            "postable": n_postable,
            "merchant_rule": n_merchant_rule,
            "cardholder_rule_flagged": n_cardholder_flagged,
            "fallback": n_fallback,
            "flagged_total": n_flagged_total,
            "not_yet_settled": n_not_settled,
        },
        "merchant_rule_hit_rate_pct": round(hit_rate_merchant, 1),
    }

    payload = {
        "summary": summary,
        "results": results,
        "excluded": excluded_recs,
        "rules_skipped": [{"name": s.name, "reason": s.reason} for s in skipped],
    }
    Path(out_path).write_text(json.dumps(payload, indent=2, default=str))
    return summary


# ---- xlsx writer (v3 — produces the QBO Transaction Import deliverable) ----

def _leaf_of_path(gl_path: str | None) -> str | None:
    """Extract the leaf of a colon-separated GL path.

    'Sales & Marketing:Sales & Marketing- Travel Expenses:Ground Transportation'
        -> 'Ground Transportation'
    Returns None if input is None, empty, or '(needs review)'.
    """
    if not gl_path or gl_path == "(needs review)":
        return None
    return gl_path.split(":")[-1].strip()


def _synthesize_description(descriptor: str, cardholder: str, expense_id: str) -> str:
    """Build a CSV-mode-style description string from feed-mode fields.

    CSV mode has: '<MERCHANT> MASTERCARD-XXXXXX-<cardholder>'
    Feed mode has descriptor + budget_name separately. We synthesize the same
    shape so memory-md substring matching and any downstream tooling expecting
    the CSV format still work. Card number portion is left as a placeholder
    because the Brex API doesn't expose it on the expense object directly.
    """
    cardholder = cardholder or "Unknown"
    # Use the last 6 of the expense_id as a stable card-number-ish placeholder
    # so the description has a unique tail like CSV mode (XXXXXX-<name>).
    card_placeholder = (expense_id or "")[-6:].upper() if expense_id else "------"
    return f"{descriptor} MASTERCARD-XXXXXX{card_placeholder}-{cardholder}"


def write_xlsx(results: list[dict], template_path: Path, out_dir: Path,
               base_filename: str = "Brex Transaction Import",
               allow_overwrite: bool = False) -> dict:
    """Write feed-mode results to a QBO Transaction Import xlsx.

    Reuses the same template as CSV mode. Skips records with decision='EXCLUDED'.
    Auto-versions filename to -v2, -v3 if today's file already exists.

    Column mapping (per user 2026-06-02):
        - col B (DATE) = payment_posted_at[:10] (Brex POSTED date, not swipe)
        - col C (DESCRIPTION) = synthesized "<descriptor> MASTERCARD-XXXX-<budget_name>"
        - col D (Payee) = blank — let override drive
        - col E (Category or Match) = full GL path from rule.category if confident; blank for fallback
        - col F (SPENT) = amount
        - col G (RECEIVED) = blank
        - col I/J (Payee Override) = result['payee']
        - col L/M (Sub Category Override) = leaf of GL path OR derived via fill_col_L
    Cell comments on cardholder-flagged + Low/Review rows.
    """
    import os, shutil
    from datetime import datetime as _dt
    from openpyxl import load_workbook
    from openpyxl.comments import Comment
    from fill_col_L import expected_sub_cat, CHARITY_VENDORS_LC

    out_dir.mkdir(parents=True, exist_ok=True)
    today = _dt.today().strftime("%Y%m%d")
    out_xlsx = out_dir / f"{base_filename} {today}.xlsx"
    # Overwrite requires BOTH --allow-overwrite AND an interactive session (BREX_INTERACTIVE=1).
    # The scheduled wrapper never sets that env var, so an UNATTENDED run can never overwrite an
    # existing deliverable even if --allow-overwrite is passed -- it auto-versions instead.
    interactive = os.environ.get("BREX_INTERACTIVE") == "1"
    if out_xlsx.exists() and not (allow_overwrite and interactive):
        n = 2
        while (out_dir / f"{base_filename} {today} ({n}).xlsx").exists():
            n += 1
        out_xlsx = out_dir / f"{base_filename} {today} ({n}).xlsx"

    shutil.copyfile(template_path, out_xlsx)
    wb = load_workbook(out_xlsx)
    ws = wb["QBO Transactions"]

    H = {ws.cell(3, c).value: c for c in range(1, ws.max_column + 1)}
    C = dict(
        date=H["DATE"], desc=H["DESCRIPTION"], payee=H["Payee"],
        cat=H["Category or Match"], spent=H["SPENT"], received=H["RECEIVED"],
        pov=H["Payee Override"], sub_ov=H["Sub Category Override"],
        card_no=H.get("Card #"),
    )

    # Card Mapping tab: cardholder name -> {last-4}, for reverse-look-up of the Card # column.
    name2last4: dict[str, set] = {}
    if "Card Mapping" in wb.sheetnames:
        cm = wb["Card Mapping"]
        for cr in range(1, cm.max_row + 1):
            l4 = cm.cell(cr, 2).value
            cn = cm.cell(cr, 3).value
            if l4 not in (None, "") and cn and not str(l4).startswith("Card Number"):
                name2last4.setdefault(str(cn).strip().lower(), set()).add(str(l4).strip())

    # Defensive: clear phantom data from rows 4+ (template may carry placeholder data)
    last_input_col = C['sub_ov']
    for r in range(4, ws.max_row + 1):
        for c in range(2, last_input_col + 1):
            if ws.cell(r, c).value is not None:
                ws.cell(r, c).value = None
            if ws.cell(r, c).comment is not None:
                ws.cell(r, c).comment = None

    # Exclude ALREADY_POSTED rows (already in QBO via reconciliation)
    def _is_postable(r):
        if r.get("decision") == "EXCLUDED":
            return False
        if r.get("reconcile", {}).get("status") == "ALREADY_POSTED":
            return False
        return True
    postable = [r for r in results if _is_postable(r)]
    rows_already_posted = sum(1 for r in results
                              if r.get("reconcile", {}).get("status") == "ALREADY_POSTED")

    for i, r in enumerate(postable):
        row_num = 4 + i

        # Date
        date_str = r.get("date") or ""
        try:
            ws.cell(row_num, C['date']).value = _dt.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            ws.cell(row_num, C['date']).value = date_str or None

        # Description (synthesized CSV-like) — cardholder tail = real user (card_name),
        # falling back to budget_name only if user is missing.
        ws.cell(row_num, C['desc']).value = _synthesize_description(
            r.get("descriptor", ""), (r.get("card_name") or r.get("budget_name") or ""), r.get("id", ""))
        # Card # (col 14): reverse-look-up the cardholder in the Card Mapping tab (name -> last-4).
        _holder = (r.get("card_name") or "").strip().lower()
        _l4 = name2last4.get(_holder)
        if C.get("card_no") and _l4 and len(_l4) == 1:
            ws.cell(row_num, C['card_no']).value = next(iter(_l4))

        # Payee left blank — Payee Override drives
        ws.cell(row_num, C['payee']).value = None

        # Category or Match — full GL path if confident (rule hit), blank otherwise
        gl_path = r.get("category")
        if gl_path and gl_path != "(needs review)":
            ws.cell(row_num, C['cat']).value = gl_path
        else:
            ws.cell(row_num, C['cat']).value = None

        # SPENT
        ws.cell(row_num, C['spent']).value = r.get("amount", 0)

        # Payee Override
        ws.cell(row_num, C['pov']).value = r.get("payee") or None

        # Sub Category Override.
        # Priority: GL-path leaf (bank-rule) -> resolver sub-cat (memory_sub_cat,
        # incl. the complete Brex-category map) -> fill_col_L default (unchanged).
        leaf = _leaf_of_path(gl_path)
        resolver_sub = r.get("sub_category_override")
        if leaf:
            sub_ov = leaf
        elif resolver_sub:
            sub_ov = resolver_sub
        else:
            # Fallback: derive from the resolver's payee category
            merch_lc = (r.get("descriptor") or "").lower()
            charity_set = {c.lower() for c in CHARITY_VENDORS_LC}
            payee = r.get("payee") or ""
            if payee.lower() in charity_set:
                sub_ov = "Charitable Contribution"
            else:
                sub_ov = expected_sub_cat(payee, merch_lc)
        # Airline charges → Airfare regardless of default (Brex category signal; Zayn 2026-06-15)
        if (r.get("brex_category") or "").upper() == "AIRLINE_EXPENSES":
            sub_ov = "Airfare"
        if sub_ov:
            ws.cell(row_num, C['sub_ov']).value = sub_ov

        # Cell comments on flagged rows
        is_likely_posted = r.get("reconcile", {}).get("status") == "LIKELY_POSTED"
        if r.get("flag") or r.get("confidence") in ("Low", "Review", "Flag") or is_likely_posted:
            src = r.get("source", "")
            conf = r.get("confidence", "")
            if is_likely_posted:
                prefix = "⚠️ POSSIBLE DUPLICATE — date+amount match a posted QBO Purchase"
            elif conf == "Flag":
                prefix = "⚠️ ALWAYS-FLAG CATEGORY — review (non-business/sensitive); not auto-categorized"
            elif src.startswith("qbo-rule(cardholder)"):
                prefix = "⚠️ CARDHOLDER-RULE MATCH — verify before posting"
            elif conf == "Low":
                prefix = "⚠️ LOW CONFIDENCE — review"
            elif conf == "Review":
                prefix = "Review (MCC/category fallback)"
            else:
                prefix = "Flagged"
            comment_text = (
                f"{prefix}\n\n"
                f"Source: {src}\n"
                f"Matched on: {r.get('matched_on','')}\n"
                f"Brex MCC: {r.get('mcc','-')} / category: {r.get('brex_category','-')}\n"
                f"Brex expense id: {r.get('id','')}"
            )
            if is_likely_posted:
                rec = r.get("reconcile", {})
                comment_text += (
                    f"\n\nPossible QBO duplicate: Purchase #{rec.get('qbo_id')} "
                    f"on {rec.get('qbo_date')} for ${rec.get('qbo_amount')} ({rec.get('qbo_entity')})"
                )
            if r.get("settlement_note"):
                comment_text += f"\nSettlement: {r['settlement_note']}"
            c = Comment(comment_text, "Brex Feed Skill")
            c.width = 380
            c.height = 160
            ws.cell(row_num, C['pov']).comment = c

    wb.save(out_xlsx)
    return {
        "out_xlsx": str(out_xlsx),
        "rows_written": len(postable),
        "rows_excluded": len(results) - len(postable),
        "rows_already_posted_skipped": rows_already_posted,
    }


def detect_month_year(results: list[dict]) -> tuple[str, str]:
    """Return (year, month_name) from the most common date in postable records."""
    from collections import Counter
    from datetime import datetime as _dt
    dates = []
    for r in results:
        if r.get("decision") == "EXCLUDED":
            continue
        d = r.get("date") or ""
        try:
            dt = _dt.strptime(d, "%Y-%m-%d")
            dates.append((dt.strftime("%Y"), dt.strftime("%B")))
        except (ValueError, TypeError):
            continue
    if not dates:
        today = _dt.today()
        return today.strftime("%Y"), today.strftime("%B")
    return Counter(dates).most_common(1)[0][0]


def main(argv=None):
    p = argparse.Argum