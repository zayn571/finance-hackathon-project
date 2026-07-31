"""Cardholder/merchant/category extraction from a QBO Transaction Detail by
Account memo string. See references/routing-overrides.md for why this regex
looks the way it does - it replaces a naive ASCII/digit-only version that
silently dropped or corrupted names on the majority of real Brex rows.
"""
import re

NAME_RE = re.compile(r"[^\W\d_](?:[^\W\d_]|[\s.'])*", re.UNICODE)
INVALID_NAME_RE = re.compile(r"\d|XXXX|MASTERCARD", re.I)
LAST4_RE = re.compile(r"XXXX(\d{4})(?:\s|$)")


def extract_name(memo):
    """Cardholder name from a Brex-style descriptor. Only reliable for Brex -
    Amex Plat/Plat 2 carry no name in the memo at all (see manager-mapping.md
    §3); use extract_last4() + the card-mapping table for those instead."""
    mm = re.sub(r"\s*\(#\d+\)\s*$", "", memo.strip())
    segs = mm.split("-")
    if len(segs) > 1:
        cand = segs[-1].strip()
        if cand and NAME_RE.fullmatch(cand) and not INVALID_NAME_RE.search(cand):
            return cand
    return None


def extract_merchant(memo):
    """Text before the MASTERCARD/XXXX masked-card token."""
    parts = re.split(r"(?:XXXX|MASTERCARD)", memo, flags=re.I)
    return parts[0].strip(" -") if parts else memo.strip()


def extract_last4(memo):
    """Trailing 4-digit card suffix, for the Amex Plat / Plat 2 card-mapping
    fallback. Confirmed these accounts hold many sub-cards (11 distinct
    suffixes seen under Amex Plat alone in a single 15-day window), not one
    shared card - the suffix is a real identifier, not a generic mask."""
    m = LAST4_RE.search(memo)
    return m.group(1) if m else None


def extract_category(split_path):
    """QBO Category = last segment of the Split account path after the final ':'."""
    return split_path.split(":")[-1].strip() if split_path else ""
