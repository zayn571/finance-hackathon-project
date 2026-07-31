"""Payee Override resolver for the brex-import skill.

Decides what to write in the Payee Override column for each row where the
CSV's Payee column is blank. Implements the precedence order from the user's
workflow rules (see references/workflow-rules.md and the user's memory.md):

    1. memory.md hard-confirmed mappings (longest substring wins)
    2. memory.md this-month confirmed
    3. memory.md historical specific mappings
    4. Industry-knowledge mappings (well-known brands bundled in this resolver)
    5. memory.md inconsistent merchants (medium confidence — flag for review)
    6. memory.md historical fallback patterns
    7. Vendor list exact match (case-insensitive)
    8. Vendor list whole-word substring match
    9. Property literal-match rule (Venetian/Palazzo → The Venetian, Wynn → Wynn Las Vegas)
   10. Description-based keyword fallback (taxi/hotel/airline/food/office)
   11. Junk pattern guard (pure card numbers) → Travel Vendor (low)
   12. Last-resort guess → Food Vendor (low, flag for review)

Feed-mode (Brex direct pull) adds a thirteenth layer via `resolve_with_signals`
— when the base resolver returns a Low/guess, MCC and Brex-category hints are
applied before accepting the guess. Existing `resolve()` signature is unchanged
so the CSV path is untouched.

A complete 48-category Brex-category layer (`BREX_CATEGORY_MAP` + the
`ALWAYS_FLAG_CATEGORIES` set) runs once the base is Low: the always-flag check
fires first (before MCC, so it can't be pre-empted), then MCC, then the complete
map (before the legacy partial `BREX_CAT_TO_PAYEE` hint, so the full map wins),
then the web-search fallback.

Confidence levels:
    High   = memory hit, exact vendor list match
    Medium = industry mapping, vendor substring, inconsistent, keyword fallback,
             property rule, historical fallback, complete Brex-category map
    Review = MCC-hint or brex-category-hint (feed-mode enrichment)
    Low    = junk-pattern guess, last-resort guess
    Flag   = always-flag Brex category (sensitive/non-business — never auto-categorized)
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

# Make the resolver work whether imported as a module or run directly
sys.path.insert(0, str(Path(__file__).parent))
from memory_loader import load_memory, find_longest_match, MemoryEntry

from openpyxl import load_workbook

FALLBACKS = {"Food Vendor", "Hotel Vendor", "Travel Vendor", "Office Vendor", "Taxi Vendor"}

# Industry-knowledge mappings — well-known brands that should categorize
# consistently. If the user corrects any of these, promote to memory.md and
# remove from here.
INDUSTRY = [
    ("checkr",                "Office Vendor",   "Background-check SaaS"),
    ("beautiful.ai",          "Office Vendor",   "Presentation SaaS"),
    ("rocketmiles",           "Travel Vendor",   "Hotel-booking-for-miles"),
    ("wizz air",              "Travel Vendor",   "Wizz Air"),
    ("ryanair",               "Travel Vendor",   "Ryanair (low-cost airline)"),
    ("zazzle",                "Office Vendor",   "Print-on-demand"),
    ("ipsparking",            "Travel Vendor",   "UK parking service"),
    ("ukvi",                  "Office Vendor",   "UK Visas & Immigration — gov fee"),
    ("ministry of home affairs", "Office Vendor", "Gov immigration fee"),
    ("philip morris",         "Travel Vendor",   "Per user history — incidental fees"),
    ("culver",                "Food Vendor",     "Culver's restaurant"),
    ("heytea",                "Food Vendor",     "Tea chain"),
    ("cvent",                 "Office Vendor",   "Event-management SaaS"),
    ("translayte",            "Office Vendor",   "Translation SaaS"),
]

# Property names — for the literal-match step
PROPERTY_TRIGGERS = [
    ("venetian", "The Venetian"),
    ("palazzo", "The Venetian"),
    ("wynn", "Wynn Las Vegas"),
]


# ---- MCC → Payee map (feed-mode enrichment) ----
# Small, targeted map for the most common signals seen on real Brex data.
# Source: ISO 18245 Merchant Category Codes. Spec calls for ranges + a few
# specific codes; we expand to a flat dict for O(1) lookup.
def _mcc_range(lo, hi, payee, note):
    return [(str(c), payee, note) for c in range(lo, hi + 1)]

_MCC_ROWS: list[tuple[str, str, str]] = (
    _mcc_range(3000, 3299, "Travel Vendor", "airline (3000-3299)")
    + [("4511", "Travel Vendor", "airline (4511)")]
    + [("4111", "Taxi Vendor", "transit (4111)"),
       ("4112", "Taxi Vendor", "passenger rail (4112)"),
       ("4121", "Taxi Vendor", "taxi/limo (4121)"),
       ("4131", "Taxi Vendor", "bus (4131)")]
    + _mcc_range(5811, 5814, "Food Vendor", "restaurant (5811-5814)")
    + [("5411", "Food Vendor", "grocery (5411)"),
       ("5499", "Food Vendor", "misc food (5499)"),
       ("5734", "Office Vendor", "computer software stores (5734)"),
       ("5817", "Office Vendor", "digital goods — software (5817)"),
       ("5942", "Office Vendor", "bookstores (5942)"),
       ("5912", "Office Vendor", "drug stores / pharmacies (5912)"),
       ("5921", "Office Vendor", "package stores (5921)"),
       ("5943", "Office Vendor", "stationery / office supplies (5943)"),
       ("7011", "Hotel Vendor", "lodging (7011)"),
       ("7523", "Travel Vendor", "parking lots/garages (7523)"),
       ("7512", "Travel Vendor", "car rental (7512)"),
       ("4789", "Travel Vendor", "transportation services NEC (4789)")]
)
MCC_TO_PAYEE: dict[str, tuple[str, str]] = {code: (payee, note) for code, payee, note in _MCC_ROWS}


# ---- Brex category → Payee map (secondary hint when MCC doesn't fire) ----
# Brex's `category` field on the expense object is a coarse classification.
# Used only as a tiebreaker after MCC.
BREX_CAT_TO_PAYEE: dict[str, str] = {
    "MEALS": "Food Vendor",
    "RESTAURANT": "Food Vendor",
    "FOOD_DELIVERY": "Food Vendor",
    "GROCERIES": "Food Vendor",
    "TRAVEL": "Travel Vendor",
    "AIRFARE": "Travel Vendor",
    "LODGING": "Hotel Vendor",
    "GROUND_TRANSPORTATION": "Taxi Vendor",
    "TAXI": "Taxi Vendor",
    "RIDESHARE": "Taxi Vendor",
    "PARKING": "Travel Vendor",
    "SHIPPING": "Office Vendor",
    "MEDICAL": "Office Vendor",
    "SOFTWARE": "Office Vendor",
    "SAAS": "Office Vendor",
    "OFFICE_SUPPLIES": "Office Vendor",
    "PROFESSIONAL_SERVICES": "Office Vendor",
    "MARKETING": "Office Vendor",
    "ENTERTAINMENT": "Food Vendor",
}


# ---- Complete Brex category → (Payee bucket, Sub Category) map ----
# Full 48-category feed-mode classification layer. Fires only after the
# bank-rule / vendor-list / memory layers have all missed; takes precedence over
# the partial BREX_CAT_TO_PAYEE hint above so it cannot be pre-empted. Categories
# not present here fall through to the web-search fallback.
BREX_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "RESTAURANTS": ("Food Vendor", "Meals & Entertainment"),
    "FOOD_DELIVERY": ("Food Vendor", "Meals & Entertainment"),
    "GROCERY": ("Food Vendor", "Meals & Entertainment"),
    "BARS_AND_NIGHTLIFE": ("Food Vendor", "Meals & Entertainment"),
    "RIDESHARE_AND_TAXI": ("Taxi Vendor", "Ground Transportation"),
    "PUBLIC_TRANSPORTATION": ("Taxi Vendor", "Ground Transportation"),
    "AIRLINE_EXPENSES": ("Travel Vendor", "Airfare"),
    "PRIVATE_AIR_TRAVEL": ("Travel Vendor", "Airfare"),
    "CAR_RENTAL": ("Travel Vendor", "Ground Transportation"),
    "GAS_AND_FUEL": ("Travel Vendor", "Ground Transportation"),
    "PARKING_EXPENSES": ("Travel Vendor", "Ground Transportation"),
    "VEHICLE_EXPENSES": ("Travel Vendor", "Ground Transportation"),
    "TOLL_AND_BRIDGE_FEES": ("Travel Vendor", "Ground Transportation"),
    "OTHER_TRAVEL_EXPENSES": ("Travel Vendor", "Other Travel Expenses"),
    "TRAVEL_WIFI": ("Travel Vendor", "Other Travel Expenses"),
    "LAUNDRY": ("Travel Vendor", "Other Travel Expenses"),
    "EVENT_EXPENSES": ("Travel Vendor", "Meals & Entertainment"),
    "LODGING": ("Hotel Vendor", "Lodging"),
    "RECURRING_SOFTWARE_AND_SAAS": ("Office Vendor", "Software Licenses"),
    "SOFTWARE_NON_RECURRING": ("Office Vendor", "Software Licenses"),
    "SERVERS": ("Office Vendor", "Software Licenses"),
    "DIGITAL_GOODS": ("Office Vendor", "Software Licenses"),
    "OFFICE_SUPPLIES": ("Office Vendor", "Office Supplies"),
    "CLOTHING": ("Office Vendor", "Office Supplies"),
    "FURNITURE": ("Office Vendor", "Office Supplies"),
    "GENERAL_MERCHANDISE": ("Office Vendor", "Office Supplies"),
    "ELECTRONICS": ("Office Vendor", "Hardware & Peripherals"),
    "SHIPPING": ("Office Vendor", "Shipping Expense"),
    "TELEPHONY": ("Office Vendor", "Utilities"),
    "UTILITIES": ("Office Vendor", "Utilities"),
    "BOOKS_AND_NEWSPAPERS": ("Office Vendor", "Dues & Subscriptions"),
    "MEMBERSHIPS_AND_CLUBS": ("Office Vendor", "Dues & Subscriptions"),
    "TRAINING_AND_EDUCATION": ("Office Vendor", "Dues & Subscriptions"),
    "RENT": ("Office Vendor", "Rent & Lease"),
    "FACILITIES_EXPENSES": ("Office Vendor", "Rent & Lease"),
    "CONSULTANT_AND_CONTRACTOR": ("Office Vendor", "Legal & Professional Services"),
    "LEGAL_SERVICES": ("Office Vendor", "Legal & Professional Services"),
    "CORPORATE_INSURANCE": ("Office Vendor", "Insurance"),
    "FEES_AND_LICENSES_AND_TAXES": ("Office Vendor", "Misc. Taxes & Licenses"),
    "CONFERENCES": ("Office Vendor", "Conferences & Events"),
    "CHARITY": ("Office Vendor", "Charitable Contributions"),
    "BANK_AND_FINANCIAL_FEES": ("Office Vendor", "Other Business Expenses"),
    "OTHER_BUSINESS_EXPENSES": ("Office Vendor", "Other Business Expenses"),
    "ADVERTISING_AND_MARKETING": ("Office Vendor", "Other Marketing Expenses"),
}
# Sensitive / non-business categories — always surfaced for human review,
# never auto-categorized (checked before the MCC hint so MCC can't pre-empt).
ALWAYS_FLAG_CATEGORIES = {"GAMBLING", "POLITICAL_DONATIONS", "MEDICAL", "FLOWERS"}


def whole_word_in(needle: str, haystack: str) -> bool:
    """Whole-word case-insensitive match. Per CLAUDE.md Rule 4 — the vendor
    name should appear as a whole word, not as a substring of a longer word.
    This prevents 'Mobil' from matching 'wlv mobile app ecomm'."""
    pat = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
    return re.search(pat, haystack, re.IGNORECASE) is not None


def merchant_from_desc(desc: str) -> str:
    """Pull the merchant string out of a Brex description.

    Brex format: '<MERCHANT> MASTERCARD-XXXXXX-<cardholder>'
    We split on 'MASTERCARD' and return everything before. Some descriptions
    end with a trailing hyphen from the split — strip that too."""
    if "MASTERCARD" in desc:
        m = desc.split("MASTERCARD")[0]
    else:
        m = desc
    return m.strip().rstrip("-").strip()


def load_vendors(vendors_path: str | Path) -> dict[str, str]:
    """Load the QBO vendor list from a one-column .xlsx of DisplayNames.

    Returns a dict mapping lowercased name → canonical name. Uses `iter_rows`
    — the previous `ws.cell(r, c)` loop was O(n^2) on read-only workbooks and
    took ~35s for 856 vendors. iter_rows does the same in <0.1s.
    """
    wb = load_workbook(vendors_path, data_only=True, read_only=True)
    ws = wb.active
    vendors: dict[str, str] = {}
    for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
        v = row[0]
        if v and isinstance(v, str):
            vendors[v.strip().lower()] = v.strip()
    wb.close()
    return vendors


def load_vendors_from_json(vendors_json_path: str | Path) -> dict[str, str]:
    """Load the QBO vendor list from a live MCP pull cached to JSON.

    Expected payload shape (from `quickbooks_query` SELECT Id, DisplayName,
    CompanyName, Active FROM Vendor): a list of dicts with DisplayName and
    optional CompanyName. Per spec we match on BOTH — so both get registered
    in the returned dict (CompanyName-only rows get only that entry; rows with
    both get two entries pointing to the canonical DisplayName for downstream
    consistency).
    """
    import json
    payload = json.loads(Path(vendors_json_path).read_text())
    if isinstance(payload, dict) and "Vendor" in payload:
        payload = payload["Vendor"]  # tolerate raw QueryResponse envelope
    vendors: dict[str, str] = {}
    for v in payload:
        if not isinstance(v, dict):
            continue
        display = (v.get("DisplayName") or "").strip()
        company = (v.get("CompanyName") or "").strip()
        canonical = display or company
        if not canonical:
            continue
        if display:
            vendors[display.lower()] = canonical
        if company and company.lower() not in vendors:
            vendors[company.lower()] = canonical
    return vendors


def _fallback_keyword(merchant_lc: str) -> tuple[str, str] | None:
    """Description-based keyword fallback. Order matters — taxi/transit checked
    before generic 'metro' which could be 'metro airport'."""
    # Airport parking is travel, not taxi — check before transit
    if "airport parking" in merchant_lc:
        return "Travel Vendor", "keyword:airport-parking"
    # Taxi/transit
    if re.search(r"\b(taxi|cab|rideshare|bus|transit|tram|subway|metro|tube)\b", merchant_lc):
        return "Taxi Vendor", "keyword:transit"
    # Hotel
    if re.search(r"\b(hotel|inn|resort|motel|suites|lodge|hostel)\b", merchant_lc):
        return "Hotel Vendor", "keyword:hotel"
    # Travel
    if re.search(r"\b(airline|airfare|airways|airport|flight|amtrak|rail|railway|aviation)\b", merchant_lc):
        return "Travel Vendor", "keyword:travel"
    if "car rental" in merchant_lc or "rental car" in merchant_lc:
        return "Travel Vendor", "keyword:travel"
    # Food
    food_kws = r"\b(restaurant|cafe|café|bar|grill|kitchen|lounge|cocktail|bakery|pizza|tavern|coffee|tea|sushi|burger|deli|bistro|pub|brasserie|eatery|food|ristorante|steakhouse)\b"
    if re.search(food_kws, merchant_lc):
        return "Food Vendor", "keyword:food"
    # Office / SaaS
    if re.search(r"\b(software|license|subscription|saas|supply|supplies|office|hr|payroll|background|screening|stationery)\b", merchant_lc):
        return "Office Vendor", "keyword:office"
    return None


def resolve(merchant: str, vendors_lc: dict[str, str], memory: dict) -> dict:
    """Resolve a merchant string to a Payee Override value with confidence + reason.

    Memory hits may also carry a Sub Category Override (when the memory entry has
    one). When present, it surfaces in the returned dict as 'memory_sub_cat'; the
    runner uses it to override fill_col_L's default derivation."""
    merch_lc = merchant.lower()

    def hit(value, source, confidence, reason, memory_sub_cat=""):
        d = dict(merchant=merchant, value=value, source=source,
                 confidence=confidence, reason=reason)
        if memory_sub_cat:
            d["memory_sub_cat"] = memory_sub_cat
        return d

    # 1. Hard-confirmed
    m = find_longest_match(merch_lc, memory.get("hard_confirmed", []))
    if m:
        return hit(m.target, "memory:hard", "High",
                   f"memory.md hard-confirmed via {m.pattern!r}",
                   memory_sub_cat=getattr(m, "sub_cat", ""))

    # 2. This-month confirmed
    m = find_longest_match(merch_lc, memory.get("this_month", []))
    if m:
        return hit(m.target, "memory:this-month", "High",
                   f"memory.md this-month via {m.pattern!r}",
                   memory_sub_cat=getattr(m, "sub_cat", ""))

    # 3. Historical specific
    m = find_longest_match(merch_lc, memory.get("historical_specific", []))
    if m:
        return hit(m.target, "memory:historical", "High",
                   f"memory.md historical specific via {m.pattern!r}",
                   memory_sub_cat=getattr(m, "sub_cat", ""))

    # 4. Industry-knowledge
    best_industry = None
    for pat, target, note in INDUSTRY:
        if pat in merch_lc:
            if best_industry is None or len(pat) > len(best_industry[0]):
                best_industry = (pat, target, note)
    if best_industry:
        pat, target, note = best_industry
        return hit(target, "industry", "Medium", f"industry knowledge: {note}")

    # 5. Inconsistent (medium)
    m = find_longest_match(merch_lc, memory.get("inconsistent", []))
    if m:
        return hit(m.target, "memory:inconsistent", "Medium",
                   f"memory.md inconsistent — using majority default for {m.pattern!r}; flag")

    # 6. Historical fallback
    m = find_longest_match(merch_lc, memory.get("historical_fallback", []))
    if m:
        return hit(m.target, "memory:fallback", "Medium", f"memory.md historical fallback via {m.pattern!r}")

    # 7. Vendor list exact match
    if merch_lc in vendors_lc:
        return hit(vendors_lc[merch_lc], "vendor:exact", "High", "exact vendor list match")

    # 8. Vendor list whole-word substring (longest first)
    for vlc, v in sorted(vendors_lc.items(), key=lambda kv: -len(kv[0])):
        if len(vlc) < 5:
            continue  # ignore very short vendor names — too prone to false positives
        if v in FALLBACKS:
            continue
        if whole_word_in(v, merchant):
            return hit(v, "vendor:substring", "Medium", f"vendor list whole-word match {v!r}")

    # 9. Property literal-match
    for kw, prop in PROPERTY_TRIGGERS:
        if whole_word_in(kw, merchant):
            return hit(prop, "rule:property", "Medium",
                       f"description contains {kw!r} → {prop} (property rule)")

    # 10. Keyword fallback
    fb = _fallback_keyword(merch_lc)
    if fb:
        return hit(fb[0], "rule:keyword", "Medium", fb[1])

    # 11. Junk patterns
    if re.fullmatch(r"[\W\d\s]*", merchant):
        return hit("Travel Vendor", "rule:junk", "Low",
                   "pure junk / non-alpha — guess Travel Vendor")

    # 12. Last-resort guess
    return hit("Food Vendor", "guess", "Low",
               "no rule matched — best guess Food Vendor (review)")


# Airline descriptor → specific airline payee. Gated on Brex AIRLINE_EXPENSES
# category at the call site, so short/ambiguous keys (AMERICAN, UNITED) can't
# collide with non-airlines (American Express, etc.). Added Zayn 2026-06-15.
AIRLINE_ALIASES = [
    ("UA INFLT","United Airlines"),("UNITED","United Airlines"),("UAL","United Airlines"),
    ("SOUTHWES","Southwest Air"),("SWA","Southwest Air"),
    ("AMERICAN","American Airlines"),("AA INFLT","American Airlines"),
    ("DELTA","Delta"),("JETBLUE","JetBlue"),("ALASKA","Alaska Air"),
    ("FRONTIER","Frontier Air"),("SPIRIT","Spirit Airlines"),
    ("AIR CANADA","Air Canada"),("AIRCANADA","Air Canada"),("PORTER","Porter Airlines"),
    ("KLM","KLM"),("VUELING","Vueling"),("EASYJET","easyJet"),
    ("VIR ","Virgin Atlantic"),("VIRGIN","Virgin Atlantic"),("QANTAS","Qantas"),
]

def airline_from_descriptor(merchant: str) -> str | None:
    """Map a (truncated) Brex airline descriptor to the specific airline payee.
    Only call when Brex category == AIRLINE_EXPENSES."""
    mu = (merchant or "").upper().strip()
    for key, payee in AIRLINE_ALIASES:
        if mu.startswith(key):
            return payee
    return None


def resolve_with_signals(merchant: str, vendors_lc: dict[str, str], memory: dict,
                         mcc: str | None = None, brex_category: str | None = None) -> dict:
    """Feed-mode resolver: call `resolve()` then, if the result is a Low guess,
    apply MCC and Brex-category hints before accepting the guess.

    Returns the same dict shape as `resolve()` with an additional `signals` key
    listing which hints fired (for audit-trail visibility). When a hint is used:
        - confidence is upgraded from Low to "Review"
        - source becomes "mcc-hint(<code>)" or "brex-category-hint(<cat>)"
        - reason mentions the hint

    Important: we DO NOT override a base resolver result that's already
    Medium/High. The hints only fire when the resolver gave up.
    """
    base = resolve(merchant, vendors_lc, memory)
    signals: list[str] = []

    # Airline category is authoritative: map the (often truncated) descriptor to
    # the specific airline payee, overriding a generic Travel Vendor / inconsistent
    # default. Gated on AIRLINE_EXPENSES so e.g. "AMERICAN" can't hit American Express.
    if (brex_category or "").upper() == "AIRLINE_EXPENSES":
        _air = airline_from_descriptor(merchant)
        if _air:
            base["value"] = _air
            base["confidence"] = "High"
            base["source"] = "airline-alias"
            base["reason"] = f"Brex AIRLINE_EXPENSES + descriptor → {_air}"
            base["signals"] = [f"brex_cat=AIRLINE_EXPENSES → airline {_air}"]
            return base

    if base["confidence"] != "Low":
        if mcc:
            signals.append(f"mcc={mcc} (not used — resolver confidence={base['confidence']})")
        if brex_category:
            signals.append(f"brex_cat={brex_category} (not used — resolver confidence={base['confidence']})")
        base["signals"] = signals
        return base

    # Base was Low. Uppercase the Brex category once for the layers below.
    _cat = (brex_category or "").upper()

    # ALWAYS-FLAG categories (sensitive / non-business) — checked BEFORE the MCC
    # hint so MCC can never pre-empt the flag (e.g. MEDICAL via MCC 5912 still flags).
    if _cat in ALWAYS_FLAG_CATEGORIES:
        base["value"] = "UNCLASSIFIED"
        base["confidence"] = "Flag"
        base["source"] = f"brex-category-flag({_cat})"
        base["reason"] = f"{_cat} — always review (non-business/sensitive)"
        signals.append(f"brex_cat={_cat} → ALWAYS FLAG")
        base["signals"] = signals
        return base

    # Base was Low — try MCC first
    if mcc and str(mcc) in MCC_TO_PAYEE:
        payee, note = MCC_TO_PAYEE[str(mcc)]
        signals.append(f"mcc={mcc} → {payee} ({note})")
        base["value"] = payee
        base["confidence"] = "Review"
        base["source"] = f"mcc-hint({mcc})"
        base["reason"] = f"MCC {mcc}: {note} — base resolver had no match"
        base["signals"] = signals
        return base

    # Complete Brex-category map — after MCC, BEFORE the partial BREX_CAT_TO_PAYEE
    # hint below, so the full map takes precedence and can't be pre-empted.
    # Unmapped categories fall through to the web-search fallback.
    if _cat in BREX_CATEGORY_MAP:
        payee, sub = BREX_CATEGORY_MAP[_cat]
        base["value"] = payee
        base["memory_sub_cat"] = sub
        base["confidence"] = "Medium"
        base["source"] = f"brex-category-map({_cat})"
        base["reason"] = f"Brex category: {_cat}"
        signals.append(f"brex_cat={_cat} → {payee} / {sub} (complete map)")
        base["signals"] = signals
        return base

    # Then Brex category
    if brex_category and brex_category in BREX_CAT_TO_PAYEE:
        payee = BREX_CAT_TO_PAYEE[brex_category]
        signals.append(f"brex_cat={brex_category} → {payee}")
        base["value"] = payee
        base["confidence"] = "Review"
        base["source"] = f"brex-category-hint({brex_category})"
        base["reason"] = f"Brex category {brex_category} → {payee} — base resolver had no match, no MCC hit"
        base["signals"] = signals
        return base

    # Neither hint fired — keep the Low guess but record what we tried
    if mcc:
        signals.append(f"mcc={mcc} (no map entry)")
    if brex_category:
        signals.append(f"brex_cat={brex_category} (no map entry)")
    base["signals"] = signals
    return base
