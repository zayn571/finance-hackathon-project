# brex-import — canonical workflow rules

These are the categorization rules for the brex-import skill. They are **subordinate to** the finance-drive root rulebook (`/RapDev Finance - Claude/CLAUDE.md`); where this file and the root CLAUDE.md disagree, the root wins. Conflicts surfaced during migration (2026-06-11) have already been reconciled into this file — see "Reconciled with root CLAUDE.md" below.

**Precedence order (highest first):**
1. `references/brex-memory.md` — specific merchant mappings (always check first).
2. This file's hard rules.
3. Description-based fallback (in `brex-memory.md`).
4. Best guess (flag as low confidence).

---

## Reconciled with root CLAUDE.md (2026-06-11)

- **Discard raw source exports.** The skill no longer archives source CSVs in a `sources/` folder. Per root §4, the uploaded CSV is processed and discarded; the cell comments in the output xlsx are the audit trail.
- **One output file, no reasoning-notes sidecar.** This supersedes the old "always produce a per-row reasoning notes file" rule. Per root §6 + the 2026-06-11 decision, cell comments on flagged/low-confidence rows ARE the audit trail. Do **not** run the `notes` subcommand as part of the standard flow.
- **Output naming = root §4:** `Brex Transaction Import YYYYMMDD.xlsx` (no dashes; date = run date). No `-v2/-v3` auto-versioning.
- **Overwrite = approval gate.** Re-running a period overwrites the single file; the runner refuses unless `--allow-overwrite` is passed, which stands in for the root §3 human approval to overwrite an existing file.
- **QBO writes stay gated.** Any future feed-mode QBO write requires human approval per root §3.

## Paths (finance-drive layout)

- Read-time materials live in this skill's `references/` folder: `brex-memory.md`, `Vendors.xlsx`, `Brex Transaction Import File.xlsx` (template).
- Outputs go to `outputs/Brex Transaction Import/YYYYMM/` (orchestrator passes `--out-dir`).
- The runner resolves `references/` automatically; pass `--refs-dir` only to override.

---

## Feed mode — mandatory QBO reconciliation (don't skip)

**Every feed-mode run MUST reconcile against QBO posted transactions before producing the filled xlsx — not optional, even when the user doesn't ask.** The point is to know which Brex expenses still need posting vs. which are already booked, so we never double-post.

1. After staging `Brex_expenses.json`, pull QBO posted transactions for the run window **±3 days** (settlement lag) using the **`quickbooks_transaction_detail_by_account` tool** scoped to `account_id=62` (21140 Brex Credit Card). **Do NOT use the old `quickbooks_query ... FROM Purchase`** — it severely under-returns (4 lines where the report returned 221 for the same account/window). Transform report rows to the shape `reconcile.py` expects: `TxnDate`=Date, `TotalAmt`=abs(Amount), `PrivateNote`=Memo/Description, `EntityRef.name`=Name, and stamp `PaymentType="CreditCard"` + `AccountRef.value="62"` on every row. Stage to the run's `--out-dir` as `qbo_purchases.json`.
2. Always pass `--qbo-purchases <path>` to `runner.py categorize-brex`. A run without it is incomplete — redo it.
3. Reconciliation tiers (per `reconcile.py`): `ALREADY_POSTED` (date±3d + exact amount + descriptor in PrivateNote) → excluded from xlsx; `LIKELY_POSTED` (date+amount match, descriptor differs) → kept with a duplicate-warning cell comment; `NEW` → posted normally.
4. Report the reconcile counts (`ALREADY_POSTED` / `LIKELY_POSTED` / `NEW`) in the run summary.

---

## Hard rules (don't violate without asking)

1. **Property matching: check `brex-memory.md` first; otherwise use literal-description rule.**
   - **Step 1:** If the merchant has an explicit entry in `brex-memory.md`, that wins — even if the description doesn't contain the property name. Examples: `Canyon Ranch Cafe` → **The Venetian**, `Bouchon Bakery` → **The Venetian** (known-physical-location overrides).
   - **Step 2:** If no memory entry, fall back to literal-description matching. Trigger words: `Venetian`, `Palazzo`, `Wynn` (and any other parent-property name in the vendor list). Description CONTAINS one → match to the property (e.g., `Bouchon At The Venetian` → **The Venetian**, `Pro Shop at Wynn Golf Club` → **Wynn Las Vegas**).
   - **Watch for false positives:** a merchant name can contain a trigger word without being at that property. Example: `Poma Palazzo` → **Food Vendor**, not The Venetian. When in doubt, flag low confidence.
   - **Step 3:** If neither memory nor a literal property match applies, treat the merchant by what it is.

2. **Buses and ground transit → Taxi Vendor, NOT Travel Vendor.** Example: `Lothian Buses Central Depot` → **Taxi Vendor**. Anything "moving people around a city" (taxi, rideshare, bus, light rail, tram, subway) → Taxi Vendor. Travel Vendor is reserved for inter-city travel: airlines, Amtrak, long-distance rail, rental cars.

3. **Charitable donations → use the recipient's name directly.** Example: `Girls Who Code` → **Girls Who Code** (col J). QBO auto-creates the vendor on import. There is no "Charitable Contribution" fallback.

4. **Don't false-match substrings inside other words.** Don't match "Mobil" inside "wlv **mobil**e app ecomm". Vendor-list matching must respect whole-word boundaries. `wlv mobile app ecomm` → **Travel Vendor**. (Verify the resolver reads `brex-memory.md` first and applies whole-word matching.)

5. **If a vendor exists in the vendor list, use the exact vendor name — don't fall back to a generic.** Search the QBO vendor list (case-insensitive, exact or whole-word match) before any fallback. Example: `AeroMexico` is in the list → use `AeroMexico`, not `Travel Vendor`. memory.md hard-confirmed entries still override.

6. **PayPal handling: write `PayPal` (clean name), assume QBO rename.** The vendor list currently has `Paypal_` (trailing underscore), to be renamed in QBO. Until then write `PayPal` in col J. **DO NOT use `Paypal_`.**

7. **Ignore column F (Category) when picking a fallback for col J.** Use the description (column C, before MASTERCARD) only. (Col F IS used for the Sub Category Override pass — but not for col J.)

8. **Government / immigration / regulatory fees → Office Vendor.** Examples: `UKVI`, `Ministry of Home Affairs`, visa application fees, business-license fees, EIN/state filing fees. Professional/regulatory, not travel — even when enabling a trip.

9. **Use SPENT amount (column G) as a tiebreaker when the merchant is ambiguous.**
   - Small (<~$20): **Food Vendor** most likely.
   - Medium ($20–$200): Food or Office; check description harder.
   - Large ($200–$2,000): lean **Travel Vendor**.
   - Very large ($2,000+) no other signal: lean **Office Vendor**.
   - Tiebreaker only — never override a memory hit or clear keyword match.
   - For payment-processor merchants (`MERPAGO*X`, `PAY*X`, `SQ*X`), look up the underlying merchant rather than guessing from the processor name.

10. **`Office Vendor / Legal & Professional Services` — verify the source before accepting it (Zayn 2026-07-01: some of these have been wrong).** This sub-category should only ever come from one of two traceable sources:
    - A genuine QBO bank-rule merchant match (`source` = `qbo-rule(merchant):<name>`) whose GL path really is Legal & Professional Services, or
    - The feed-mode Brex-category fallback firing on `CONSULTANT_AND_CONTRACTOR` or `LEGAL_SERVICES` (`source` = `brex-category-map(CONSULTANT_AND_CONTRACTOR)` / `brex-category-map(LEGAL_SERVICES)`) — i.e. the actual Brex `category` field on the expense, not a keyword guess or an MCC hint.
    - There is no keyword/description-based path to Legal & Professional Services (`fill_col_L.py`'s Office Vendor default is always Office Supplies) — so if a row lands on Legal & Professional Services and the source isn't one of the two above, treat it as a bug, not a valid categorization: flag the row instead of accepting it.

---

## Sub Category Override rules (column L)

Apply alongside the Payee Override work. **Always write the canonical override even when the auto-derived value is already correct** — fill defensively. Leave blank only when no rule below applies.

**By Payee Override value:**

| Payee Override | Sub Category Override |
|---|---|
| Food Vendor | Meals & Entertainment |
| Hotel Vendor | Lodging |
| Taxi Vendor | Ground Transportation |
| Travel Vendor (airline keyword) | Airfare |
| Travel Vendor (airport parking) | Ground Transportation |
| Travel Vendor (otherwise) | Other Travel Expenses |
| Office Vendor | See sub-rules below |

**Office Vendor sub-rules:**

| Merchant type | Sub Category Override | Examples |
|---|---|---|
| Perpetual/annual licensed software | Software Licenses | Beautiful.ai, Adobe (annual), Microsoft 365 |
| SaaS recurring/pay-per-use | Dues & Subscriptions | Checkr, iStore, most monthly SaaS, Apple iCloud |
| Physical goods / one-off services | Office Supplies | Zazzle, Custom Ink, office equipment |
| Gov / immigration / regulatory fees | Office Supplies | UKVI, Ministry of Home Affairs, business licenses |

**Named specific vendors** (when Payee Override is the exact vendor name):
- Airlines (American, Delta, United, AeroMexico, …) → **Airfare**
- Hotels (Marriott, Lenox Hotel, Hilton, …) → **Lodging**
- Charity recipient names (Rule 3) → leave Sub Category Override blank

**Canonical spellings:** `Meals & Entertainment`, `Lodging`, `Ground Transportation`, `Airfare`, `Other Travel Expenses`, `Software Licenses` (plural), `Office Supplies`, `Dues & Subscriptions`.

---

## Known column layout drift

- The Brex template gained a "Memo for Transaction Report" column at position D between April and May 2026. April files: Payee at D, Payee Override at I. May+ files: E and J. **Always detect columns by reading row 3 headers, not hardcoded letters.**

## Confidence reporting

- **High** = memory hit, this-month rule, or exact vendor-list match. No review needed.
- **Medium** = description-based fallback or vendor-list substring match. Skim.
- **Low** = no rule matched, a guess. **Flag prominently** (cell comment) for user review.
- Accuracy bound ~96% (12 corrections on the 325-row test). Never claim 100%.

## How to evolve this file

When Zayn edits a filled file, diff against the skill's version. Recurring pattern → add a hard rule here. One-off → add the merchant mapping to `brex-memory.md`. Never override a hard rule here without Zayn's explicit approval.
