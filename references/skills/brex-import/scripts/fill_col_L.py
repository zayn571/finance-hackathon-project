"""Sub Category Override decision logic for the brex-import skill.

For each row with a Payee Override (either auto-filled by the resolver or from
the CSV's existing Payee), decide what to write in Sub Category Override.

Rules (canonical values pulled from the Category Mapping sheet — singular spellings):

| Payee Override                          | Sub Category Override |
|-----------------------------------------|-----------------------|
| Food Vendor                             | Meals & Entertainment |
| Hotel Vendor                            | Lodging               |
| Taxi Vendor                             | Ground Transportation |
| Travel Vendor + airport parking         | Ground Transportation |
| Travel Vendor + airline keyword         | Airfare               |
| Travel Vendor + hotel-brand merchant    | Lodging               |
| Travel Vendor (default)                 | Other Travel Expenses |
| Office Vendor + licensed-software brand | Software Licenses     |
| Office Vendor + SaaS pattern            | Dues & Subscriptions  |
| Office Vendor + gov/regulatory          | Office Supplies       |
| Office Vendor (default)                 | Office Supplies       |
| Named airline                           | Airfare               |
| Named hotel chain                       | Lodging               |
| Charity vendor (in/out of vendor list)  | Charitable Contribution |
| PayPal (clean)                          | None (let auto)       |
| Recipient name from charity rule        | Charitable Contribution |

The col W (Sub Category) is auto-derived from the CSV's "Category or Match"
account path (last segment after the final colon). We compare the expected
value above to that auto-derived value and write an override only when they
differ — except for Office Vendor where we always write defensively because
the auto-derivation is unreliable for Office expenses.
"""

from __future__ import annotations
import re

AIRLINE_KEYWORDS = [
    "airline", "airways", "air canada", "aeromexico", "american airlines",
    "delta", "united airlines", "southwest", "alaska airlines", "jetblue",
    "wizz", "ryanair", "spirit airlines", "frontier", "lufthansa",
    "british airways", "klm", "virgin atlantic", "emirates", "qatar",
    "etihad", "ana", "asiana", "korean air", "singapore air", "cathay",
    "turkish airlines", "air france", "iberia", "tap portugal", "aer lingus",
    "easyjet", "norwegian", "air india", "indigo", "vistara", "spicejet",
    "hawaiian airlines", "westjet", "porter airlines",
]

HOTEL_BRANDS = [
    "marriott", "hilton", "hyatt", "westin", "sheraton", "lenox hotel",
    "ritz-carlton", "four seasons", "courtyard", "renaissance", "fairmont",
    "intercontinental", "wynn las vegas", "the venetian", "bellagio",
    "holiday inn", "radisson",
]

LICENSED_SOFTWARE = [
    "beautiful.ai", "adobe", "microsoft 365", "office 365", "windows",
]

SAAS_RECURRING = [
    "checkr", "istore", "saas", "subscription", "dues", "membership",
    "monthly", "annual fee", "renewal", "github", "atlassian", "jira",
    "slack", "notion", "linear", "figma", "miro", "airtable", "asana",
    "monday.com", "zoom", "loom", "intercom", "datadog", "snowflake",
    "databricks", "vercel", "cloudflare", "netlify", "openai", "anthropic",
    "claude.ai", "webflow", "lastpass", "1password", "bitwarden", "okta",
    "auth0", "twilio", "sendgrid", "stripe", "rippling", "deel", "gusto",
    "bamboo hr", "google workspace", "google cloud", "aws", "azure",
    "cvent", "translayte",
]

REGULATORY_KEYWORDS = [
    "ukvi", "ministry of home affairs", "visa", "license fee",
    "registration fee",
]

# Charity vendor names — case-insensitive set. The skill extends this at runtime
# from memory.md if the user has marked any donations.
CHARITY_VENDORS_LC = {"childrens aid nyc", "girls who code"}


def is_airline(s: str) -> bool:
    return any(kw in s for kw in AIRLINE_KEYWORDS)


def is_airport_parking(s: str) -> bool:
    return "airport parking" in s


def is_bare_american(merchant_lc: str) -> bool:
    """A merchant string that's just 'American' (no other context) is almost
    always American Airlines, not American (department store)."""
    return merchant_lc.strip() == "american"


def is_licensed_software(s: str) -> bool:
    return any(kw in s for kw in LICENSED_SOFTWARE)


def is_saas_recurring(s: str) -> bool:
    return any(kw in s for kw in SAAS_RECURRING)


def is_regulatory(s: str) -> bool:
    return any(kw in s for kw in REGULATORY_KEYWORDS)


def expected_sub_cat(payee_override: str, merchant_lc: str,
                     known_charities: set[str] | None = None) -> str | None:
    """Return the expected Sub Category Override for this row, or None if no
    rule applies (leave Sub Cat Override blank in that case)."""
    if not payee_override:
        return None
    po = payee_override.strip()
    po_lc = po.lower()

    # Charity recipient — always Charitable Contribution
    charities = known_charities or CHARITY_VENDORS_LC
    if po_lc in {c.lower() for c in charities}:
        return "Charitable Contribution"

    # Fallback Payee values
    if po == "Food Vendor":
        return "Meals & Entertainment"
    if po == "Hotel Vendor":
        return "Lodging"
    if po == "Taxi Vendor":
        return "Ground Transportation"
    if po == "Travel Vendor":
        if is_airport_parking(merchant_lc):
            return "Ground Transportation"
        if is_airline(merchant_lc) or is_bare_american(merchant_lc):
            return "Airfare"
        if any(h in merchant_lc for h in HOTEL_BRANDS):
            return "Lodging"
        return "Other Travel Expenses"
    if po == "Office Vendor":
        # Most-specific first
        if is_licensed_software(merchant_lc):
            return "Software Licenses"
        if is_saas_recurring(merchant_lc):
            return "Dues & Subscriptions"
        if is_regulatory(merchant_lc):
            return "Office Supplies"
        # Default Office Vendor → Office Supplies
        return "Office Supplies"
    if po == "PayPal":
        return None  # let the auto-derived value stand

    # Named specific vendors (the Payee Override is the actual vendor name,
    # not a fallback)
    if is_airline(po_lc):
        return "Airfare"
    if any(h in po_lc for h in HOTEL_BRANDS):
        return "Lodging"

    # No rule applies — leave Sub Category Override blank, the auto value will
    # be used.
    return None


def should_write_override(expected: str | None, auto: str | None,
                          payee_override: str | None,
                          is_charity: bool = False,
                          is_manual: bool = False) -> bool:
    """Decide whether to write the Sub Category Override cell. The default is
    'fix-when-broken' — only write when the expected value differs from what
    the auto-derived Sub Category column will show. Exceptions:

    - Office Vendor is unreliable; always write defensively
    - Charity rows always get the explicit Charitable Contribution override
    - Manually-overridden rows always get the explicit sub-cat written
    """
    if expected is None:
        return False
    po = (payee_override or "").strip()
    if po == "Office Vendor" or is_charity or is_manual:
        return True
    return str(auto).strip() != expected
