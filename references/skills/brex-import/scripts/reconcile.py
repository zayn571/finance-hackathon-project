"""Reconciliation against QBO posted Purchases.

For each Brex expense in categorized.json, determine whether a matching QBO
Purchase already exists (i.e. the expense has already been posted to the
Brex Credit Card account). Matched expenses are marked ALREADY_POSTED and
should be excluded from the Transaction Import xlsx so we don't double-post.

Match logic (per user 2026-06-02):
    - DATE within ±N days (default 3 to cover settlement lag)
    - TOTAL AMOUNT exact to the cent (±$0.01)
    - DESCRIPTOR prefix appears in QBO PrivateNote (case-insensitive)

Tiers:
    ALREADY_POSTED (confident)  — all three match
    LIKELY_POSTED  (flag)        — date + amount match, descriptor does not
    NEW                          — no match

QBO Purchase shape (from `quickbooks_query` against Purchase entity):
    {Id, TxnDate, TotalAmt, AccountRef:{value, name}, PaymentType,
     EntityRef:{name}, PrivateNote, ...}

This script is pure-Python and has NO network. The orchestrator (Claude) pulls
QBO Purchases via `quickbooks_query` and writes the JSON file this consumes.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

BREX_CC_ACCOUNT_ID = "62"  # QBO Account.Id for Brex Credit Card (acct 21140)
DEFAULT_DATE_WINDOW_DAYS = 3
AMOUNT_TOLERANCE = 0.01


@dataclass
class MatchResult:
    status: str          # "ALREADY_POSTED" | "LIKELY_POSTED" | "NEW"
    qbo_id: str | None = None
    qbo_date: str | None = None
    qbo_amount: float | None = None
    qbo_private_note: str | None = None
    qbo_entity: str | None = None
    reason: str = ""


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s[:len(fmt) if 'T' not in fmt else len(s)], fmt)
        except ValueError:
            continue
    # Last resort: take first 10 chars as YYYY-MM-DD
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _qbo_descriptor_prefix(private_note: str | None) -> str:
    """Extract the merchant-name prefix from QBO PrivateNote.

    QBO PrivateNote shape (Brex CC charges):
        '<MERCHANT> MASTERCARD_544015XXXXXX9999 - <Cardholder>'
        '<MERCHANT> (refund) MASTERCARD_... - <Cardholder>'
    We split on 'MASTERCARD' (the underscore-prefixed variant QBO uses) and
    take everything before it. Strip '(refund)' annotation as well so we can
    match against the regular Brex descriptor.
    """
    if not private_note:
        return ""
    pn = private_note.split("MASTERCARD")[0]
    pn = pn.replace("(refund)", "").strip().rstrip("-").strip()
    return pn.lower()


def _is_brex_cc(p: dict) -> bool:
    """True if this Purchase is on the Brex Credit Card account."""
    return (p.get("PaymentType") == "CreditCard"
            and (p.get("AccountRef") or {}).get("value") == BREX_CC_ACCOUNT_ID)


def load_qbo_purchases(path: str | Path) -> list[dict]:
    """Load QBO Purchase records and filter to Brex CC only.

    Tolerates either a raw list, a dict with 'data'/'Purchase', or the
    QueryResponse envelope shape from quickbooks_query.
    """
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, dict):
        payload = (payload.get("Purchase") or payload.get("data")
                   or payload.get("rows") or list(payload.values()))
    return [p for p in payload if isinstance(p, dict) and _is_brex_cc(p)]


def _word_overlap(brex_descriptor: str, qbo_private_note: str | None) -> str | None:
    """Return the first ≥4-char alphanumeric word that appears in BOTH
    the Brex descriptor and the QBO PrivateNote (case-insensitive), or None.

    Catches cases where Brex's raw_descriptor and QBO's bank-feed text differ
    in formatting but share a meaningful brand token. Examples:
        Brex 'ANTHROPIC* CLAUDE SUB' vs QBO 'Claude MASTERCARD...'  -> 'claude'
        Brex 'TST* HATTIE B'S HOT CH' vs QBO 'Hattie B's...'         -> 'hattie'
        Brex 'UBER   *TRIP' vs QBO 'Uber HQ...'                      -> 'uber'
    """
    import re
    if not qbo_private_note:
        return None
    pn_lc = qbo_private_note.lower()
    # Strip MASTERCARD-card-cardholder tail before tokenizing PN
    pn_head = pn_lc.split("mastercard")[0]
    desc_words = {w for w in re.findall(r"[a-z0-9]{4,}", brex_descriptor.lower())
                  if not w.isdigit() and w not in {"mastercard", "trip", "ecom", "online", "payment"}}
    for w in desc_words:
        if w in pn_head:
            return w
    return None


def find_match(brex_descriptor: str, brex_date_str: str, brex_amount: float,
               qbo_index: dict, date_window_days: int,
               brex_budget_name: str = "") -> MatchResult:
    """Find a matching QBO Purchase for one Brex expense.

    Match tiers (per 2026-06-02 calibration against real QBO data):
        ALREADY_POSTED (confident)
            - date ±N + exact amount + descriptor word ≥4 chars in QBO PN, OR
            - date ±N + exact amount + budget_name (cardholder) appears in QBO PN, OR
            - date ±N + exact amount + only ONE QBO candidate matches (unambiguous)
        LIKELY_POSTED (flag)
            - date ±N + exact amount + multiple QBO candidates AND no name/word signal
        NEW
            - no QBO match by date+amount
    """
    brex_date = _parse_date(brex_date_str)
    if brex_date is None:
        return MatchResult("NEW", reason="Brex date unparseable")

    desc_lc = brex_descriptor.lower().strip()
    bud_lc = (brex_budget_name or "").lower().strip()

    candidates_amount_match: list[tuple[dict, int]] = []
    for offset in range(-date_window_days, date_window_days + 1):
        probe_date = (brex_date + timedelta(days=offset)).strftime("%Y-%m-%d")
        for p in qbo_index.get(probe_date, []):
            if abs(float(p.get("TotalAmt", 0)) - brex_amount) <= AMOUNT_TOLERANCE:
                candidates_amount_match.append((p, offset))

    if not candidates_amount_match:
        return MatchResult("NEW", reason="no QBO Purchase with matching amount in date window")

    # Tier 1a: descriptor prefix match (the cleanest signal)
    for p, offset in candidates_amount_match:
        qbo_prefix = _qbo_descriptor_prefix(p.get("PrivateNote"))
        if qbo_prefix and (qbo_prefix == desc_lc or
                           qbo_prefix in desc_lc or desc_lc in qbo_prefix):
            return MatchResult(
                status="ALREADY_POSTED", qbo_id=p.get("Id"),
                qbo_date=p.get("TxnDate"), qbo_amount=float(p.get("TotalAmt", 0)),
                qbo_private_note=p.get("PrivateNote"),
                qbo_entity=(p.get("EntityRef") or {}).get("name"),
                reason=f"exact match — date offset {offset:+d}d, descriptor prefix matches",
            )

    # Tier 1b: any ≥4-char descriptor word appears in QBO PrivateNote
    for p, offset in candidates_amount_match:
        overlap = _word_overlap(brex_descriptor, p.get("PrivateNote"))
        if overlap:
            return MatchResult(
                status="ALREADY_POSTED", qbo_id=p.get("Id"),
                qbo_date=p.get("TxnDate"), qbo_amount=float(p.get("TotalAmt", 0)),
                qbo_private_note=p.get("PrivateNote"),
                qbo_entity=(p.get("EntityRef") or {}).get("name"),
                reason=f"word overlap '{overlap}' (date offset {offset:+d}d)",
            )

    # Tier 1c: budget_name (cardholder) appears in QBO PrivateNote
    if bud_lc and " " in bud_lc:  # only useful for person names, not budget categories
        for p, offset in candidates_amount_match:
            pn = (p.get("PrivateNote") or "").lower()
            if bud_lc in pn:
                return MatchResult(
                    status="ALREADY_POSTED", qbo_id=p.get("Id"),
                    qbo_date=p.get("TxnDate"), qbo_amount=float(p.get("TotalAmt", 0)),
                    qbo_private_note=p.get("PrivateNote"),
                    qbo_entity=(p.get("EntityRef") or {}).get("name"),
                    reason=f"cardholder name {brex_budget_name!r} appears in PN (date offset {offset:+d}d)",
                )

    # Tier 1d: only one QBO candidate AND same exact date (offset=0).
    # Tightened 2026-06-02 — single-candidate matches at offset != 0 are too
    # risky (saw WWW.SWEETGREEN.COM @ Brex 06/01 wrongly match Life Alive @ QBO
    # 05/30 because they happened to share $16). Same-day-same-amount-lone
    # is much safer.
    if len(candidates_amount_match) == 1 and candidates_amount_match[0][1] == 0:
        p, offset = candidates_amount_match[0]
        return MatchResult(
            status="ALREADY_POSTED", qbo_id=p.get("Id"),
            qbo_date=p.get("TxnDate"), qbo_amount=float(p.get("TotalAmt", 0)),
            qbo_private_note=p.get("PrivateNote"),
            qbo_entity=(p.get("EntityRef") or {}).get("name"),
            reason="only QBO candidate at same date and exact amount",
        )

    # Tier 2: multiple candidates, no name/word signal — flag as ambiguous
    p, offset = candidates_amount_match[0]
    return MatchResult(
        status="LIKELY_POSTED", qbo_id=p.get("Id"),
        qbo_date=p.get("TxnDate"), qbo_amount=float(p.get("TotalAmt", 0)),
        qbo_private_note=p.get("PrivateNote"),
        qbo_entity=(p.get("EntityRef") or {}).get("name"),
        reason=(f"amount+date match ({len(candidates_amount_match)} QBO candidates) "
                f"but no descriptor/cardholder/word overlap — possible coincidence"),
    )


def build_qbo_index(qbo_purchases: list[dict]) -> dict[str, list[dict]]:
    """Bucket QBO purchases by TxnDate (YYYY-MM-DD string)."""
    idx: dict[str, list[dict]] = {}
    for p in qbo_purchases:
        d = (p.get("TxnDate") or "")[:10]
        if d:
            idx.setdefault(d, []).append(p)
    return idx


def reconcile(categorized_results: list[dict], qbo_purchases: list[dict],
              date_window_days: int = DEFAULT_DATE_WINDOW_DAYS) -> tuple[list[dict], dict]:
    """Walk every Brex expense; attach a reconcile field to each.

    Returns (augmented_results, summary) where each result gets:
        result['reconcile'] = {status, qbo_id, qbo_date, qbo_amount,
                                qbo_private_note, qbo_entity, reason}
    """
    qbo_index = build_qbo_index(qbo_purchases)

    augmented = []
    counts = {"ALREADY_POSTED": 0, "LIKELY_POSTED": 0, "NEW": 0, "SKIPPED_EXCLUDED": 0}
    for r in categorized_results:
        if r.get("decision") == "EXCLUDED":
            counts["SKIPPED_EXCLUDED"] += 1
            augmented.append({**r, "reconcile": {"status": "SKIPPED_EXCLUDED"}})
            continue
        m = find_match(
            brex_descriptor=r.get("descriptor", ""),
            brex_date_str=r.get("date", ""),
            brex_amount=float(r.get("amount", 0)),
            qbo_index=qbo_index,
            date_window_days=date_window_days,
            brex_budget_name=r.get("budget_name", ""),
        )
        counts[m.status] = counts.get(m.status, 0) + 1
        augmented.append({**r, "reconcile": {
            "status": m.status,
            "qbo_id": m.qbo_id,
            "qbo_date": m.qbo_date,
            "qbo_amount": m.qbo_amount,
            "qbo_private_note": m.qbo_private_note,
            "qbo_entity": m.qbo_entity,
            "reason": m.reason,
        }})

    summary = {
        "qbo_purchases_compared": len(qbo_purchases),
        "qbo_purchases_date_range_days": date_window_days,
        "reconcile_counts": counts,
    }
    return augmented, summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: reconcile.py <categorized.json> <qbo_purchases.json>", file=sys.stderr)
        sys.exit(2)
    cat = json.loads(Path(sys.argv[1]).read_text())
    results = cat.get("results", cat) if isinstance(cat, dict) else cat
    qbo = load_qbo_purchases(sys.argv[2])
    augmented, summary = reconcile(results, qbo)
    print(json.dumps(summary, indent=2))
    print()
    posted = [r for r in augmented if r.get("reconcile", {}).get("status") == "ALREADY_POSTED"]
    likely = [r for r in augmented if r.get("reconcile", {}).get("status") == "LIKELY_POSTED"]
    if posted:
        print(f"ALREADY_POSTED ({len(posted)}):")
        for r in posted:
            print(f"  {r['descriptor'][:30]:<31} ${r['amount']:>8.2f}  ->  QBO #{r['reconcile']['qbo_id']}")
    if likely:
        print(f"\nLIKELY_POSTED ({len(likely)}):")
        for r in likely:
            print(f"  {r['descriptor'][:30]:<31} ${r['amount']:>8.2f}  ?  QBO #{r['reconcile']['qbo_id']}  ({r['reconcile']['reason']})")
