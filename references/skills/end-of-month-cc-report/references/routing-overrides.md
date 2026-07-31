# Cardholder routing — overrides, guardrails, nicknames

Applied on top of the base mapping (see `manager-mapping.md`).

## Cardholder extraction (Brex only — Amex Plat/Plat 2 use `card-mapping.tsv` instead, see `manager-mapping.md` §3)

Name sits after the LAST hyphen in `Memo/Description`, once a trailing `(#123)` employee id is stripped. **Must be Unicode-aware** — an ASCII-only `[A-Za-z]` character class silently drops accented names (caught in production: `Anamaria Grămadă` was dropping to "no name" every run before this fix).
```python
import re
def extract_name(memo):
    mm = re.sub(r'\s*\(#\d+\)\s*$', '', memo.strip())
    segs = mm.split('-')
    if len(segs) > 1:
        cand = segs[-1].strip()
        if cand and re.fullmatch(r"[^\W\d_](?:[^\W\d_]|[\s.'])*", cand, re.UNICODE) and not re.search(r'\d|XXXX|MASTERCARD', cand, re.I):
            return cand
    return None
```
**Do not use a regex that assumes the masked-card token is pure digits/X** (e.g. `[\dX]+`) — live Brex tokens routinely mix in other letters (`MASTERCARD-XXXXXXQQ35VX-Jay Barker`), and that assumption silently drops or corrupts the name on ~75% of real rows. Verified 2026-07-01: the fix above recovers 96.6% of Brex rows vs. 23.8% for the naive version.

## Nickname normalization (collapse the same person to ONE canonical identity = ONE pivot line)
```python
NICK = {"matt":"matthew","mike":"michael","mick":"mickenzi","alex":"alexander","bob":"robert",
  "rob":"robert","kara":"karalyn","mitch":"mitchell","jim":"james","tom":"thomas",
  "chris":"christopher","dan":"daniel","danny":"daniel","nick":"nicholas","will":"william",
  "bill":"william","joe":"joseph","tony":"anthony","ben":"benjamin","sam":"samuel",
  "greg":"gregory","andy":"andrew","steve":"stephen","jon":"jonathan"}
# normkey: NFKD-ascii, strip non-alpha, lowercase tokens, map via NICK, join.
```
Resolution: exact normalized match → fuzzy (edit-distance ≤ 2 on a UNIQUE surname only) → else unresolved (exceptions). **Write the canonical display name into Card Member**, not the raw descriptor spelling, so variants merge.

**When two spellings both look "valid" and both independently exist in historical data** (e.g. `Connor Bracket` vs `Connor Brackett` — a Manager Mapping sheet entry can coexist with a differently-spelled entry baked into an old master), do not pick whichever is longer or whichever was processed last — that's a coin flip, not a resolution. Pick in this priority order: (1) `card-mapping.tsv`, (2) the Manager Mapping sheet, (3) if neither authoritative source picks a winner, leave the two spellings **unmerged** and flag it for a human rather than guess. (Caught in production: an earlier pass would have shipped "Connor Brackett" — the longer spelling — when the Manager Mapping sheet has always said "Connor Bracket," one T.)

## Surname guardrail — never first-name-merge across these (distinct people share a surname)
- Hourani: Alexandra, Ayla, Canaan, Tameem
- Whitehead: James, Shakara
- Kolosky: Ona vs Robert
- Sanderford: Austin, William (do NOT merge with "Sandford" below — different surname, different people)

If the active mapping ever has two different people sharing a surname not listed here, error loudly and stop.

## Manual routing overrides / aliases (confirmed by Zayn)
```
Luis Gallego           -> Jay Barker
Henri Hatch            -> Jay Barker
Alta Abel              -> Ayaan Israni   (NOT Elyse Neumeier — historical master had this wrong; Manager Mapping sheet + Zayn both confirm Ayaan)
Samantha Purpura       -> Ayaan Israni
Frederick Simpson      -> Ayaan Israni
Jacy Hennawy           -> Elyse Neumeier
Vivian Wu              -> Elyse Neumeier
Dwight Henderson       -> Jesse/Scott
Elias Kapetanopolous   -> Elias Kapetanopoulos   (QBO descriptor typo; also a display-merge)
Michael Button         -> Elias Kapetanopoulos
Marsha Whitman         -> Elias Kapetanopoulos
Brendan Nolan          -> Elias Kapetanopoulos
Gage Howell            -> Elias Kapetanopoulos   (added 2026-07-01)
John Fennell           -> Toni Manning           (added 2026-07-01)
William Sanderford     -> Elias Kapetanopoulos   (added 2026-07-01)
Anamaria Grămadă       -> Elias Kapetanopoulos   (added 2026-07-01)
Cody Sanderford        -> Cody Sandford, Elias Kapetanopoulos   (spelling correction, added 2026-07-01 — "Sandford" confirmed correct by Zayn; do not confuse with the distinct "Sanderford" family above)
Sakshi Sasalate        -> Elias Kapetanopoulos   (added 2026-07-01, confirmed by Zayn during June 2026 report run)
Samara McVey           -> Elias Kapetanopoulos   (added 2026-07-01, confirmed by Zayn during June 2026 report run)
Gary Passaglia         -> Connor/JT              (added 2026-07-01, confirmed by Zayn during June 2026 report run)
Daniel Mooney          -> Connor/JT              (added 2026-07-01, confirmed by Zayn during June 2026 report run — overrides the Matthew Keyes team rollup to Kevin Ebert in manager-mapping.md §2; he is being pulled onto Connor/JT specifically)
```
Unmapped or no-name rows → master + exceptions only (excluded from manager files); no-name rows are typically SaaS/subscriptions (verified 2026-07-01: Anthropic, Hubspot, GitHub, LastPass, Notion, BambooHR, FedEx shipping, and similar company-wide vendor charges account for nearly all of it). Unlike the legacy skill, **Tameem Hourani is NOT auto-excluded** — he routes per the mapping (see `manager-mapping.md` §2 for his team's rollup to Ayaan Israni).

## Manager buckets (8) + Kevin combined
`Jay Barker, Connor/JT, Jesse/Scott, Elias Kapetanopoulos, Ayaan Israni, Elyse Neumeier, Toni Manning, Kevin Ebert`. Kevin's file = his own reports + the full Connor/JT team + the full Jesse/Scott team + Matthew Keyes' team (see `manager-mapping.md` §2 — this last one isn't obvious from the Manager Mapping sheet alone). The same row legitimately appears in an underlying manager's file and Kevin's — never dedupe it away, never sum across files.
