---
name: end-of-month-cc-report
description: |
  RapDev end-of-month credit card spend report, sourced from QuickBooks Online. Use whenever the user asks to "run the end-of-month report", "do the monthly credit card report", "do the monthly Amex/Brex report", "generate manager spend files", "build the monthly master", "run the month-end CC report for {month}", or "kick off the monthly spend rollup." Pulls the four RapDev credit-card accounts from QBO (no manual uploads), routes spend to 8 manager buckets, builds pivot-formatted per-manager files + a master with a YTD-by-month view, delivers them into per-manager Google Drive folders, and (after user approval) posts group Slack DMs. Does NOT trigger for the brex-import (QBO categorization) skill.
---

# End-of-Month Credit Card Report (QBO-sourced)

> **Rules precedence:** runs under the finance-drive root rulebook (`/RapDev Finance - Claude/CLAUDE.md`); the root wins on any conflict. Reference data lives in this skill's `references/` folder — read it rather than hardcoding. Outputs go to `outputs/End of Month CC Manager Report/YYYYMM/`.

Automates RapDev's monthly process: pull the four company credit cards from QuickBooks, split spend into 8 per-manager Excel files (plus a master), deliver to each manager's Drive folder, and — after the user reviews and approves — post group Slack DMs. QBO is the single source of truth. This replaces the older raw-Amex/Brex-export workflow entirely; there is no raw-file path.

Run mode: **on-demand**. Distribution: **present drafts and require explicit user approval before BOTH Drive delivery and Slack** (see §8–§9).

**Determinism rule — do not improvise scripts.** Every step below runs a script that already exists in `scripts/`. Never write, generate, or improvise a one-off transform — if a step needs something the existing scripts don't do, stop and flag it rather than inventing a new helper (same rule `brex-import` follows, for the same reason: ad hoc scripts don't get the regression coverage the real ones did).

## Reference files (read these; don't hardcode)
- `references/qbo-account-ids.md` — the 4 QBO `account_id`s.
- `references/manager-mapping.md` — the two-source manager mapping (Manager Mapping sheet + realized fallback), the rollup teams, and where the Amex Plat/Plat 2 card-mapping fallback fits in.
- `references/routing-overrides.md` — the extraction regex, nickname normalization, surname guardrails, manual aliases, the name-consolidation rule, the 8 buckets + Kevin rule.
- `references/card-mapping.tsv` — last-4 → Card Name / Department / EE ID, for Amex Plat \*12006 and Amex Plat 2 \*51005 only (their transaction memo carries no name at all — see `manager-mapping.md` §3).
- `references/manager-file-template.xlsx` — a real prior per-manager workbook with an intact native PivotTable; `scripts/build_pivot.py` templates off this.
- `references/drive-folders.md` — per-manager + finance-only Drive folder IDs (delivery gated).
- `references/slack-groups.md` — group DM membership, the message template, Ayaan no-send rule (Slack gated).

## Scripts (`scripts/`)
- `runner.py` — CLI entrypoint, three subcommands: `parse`, `resolve`, `build`. Run in that order.
- `extract.py` — cardholder/merchant/category/last-4 extraction from a QBO memo (Unicode-safe).
- `resolve.py` — the manager-mapping merge, rollups, manual overrides, fuzzy matching, and name consolidation.
- `build_pivot.py` — the zipfile XML surgery that produces the native-pivot xlsx files.
- `deliver.py` — delivery-plan helper (folder IDs + base64 staging). Has no network access itself — see §8.

---

## 0. Parameters
- `month` — target report month (e.g. `2026-05`). Default = the most recent complete calendar month.
- Pull window = **Jan 1 of the target year → last day of the target month** (YTD), so the pivot shows month-by-month. (Single-month window only if the user explicitly asks.)

## 1. Pull from QBO (by internal Id, NOT account number)
Call `quickbooks_transaction_detail_by_account` once per account, using the `account_id`s in `references/qbo-account-ids.md`. **Passing the account number instead of the internal Id returns `NoReportData` (empty) — the #1 trap.** Pass `start_date` (YTD start) and `end_date` (month end). Responses are large and persist to a tool-results file — this is expected; do not try to inline them. Run `scripts/runner.py parse --report "<Account Label>" "<saved report path>" ...` (repeatable, one `--report` per account) `--out parsed.json`. It parses straight from the saved files, classifies (§3), extracts (§4), and prints the pull half of the completeness gate.

## 2. Completeness gate (mandatory — before resolving/building)
`runner.py parse` fails loudly (non-zero exit) if any account returned zero rows — stop and report (root §7: never treat a partial pull as complete). It also prints: `Uncategorized`/`Ask My Accountant` count in `Split` (should be 0 or near it), and blank-descriptor row count (should be 0 — warn if not). QBO only shows **posted** transactions, so a mid-close month under-reports; a low row count for the days-elapsed isn't necessarily a bug, but call it out.

**Second gate, after `runner.py resolve`:** Brex name-match rate. Verified baseline is ~95%+ on live data; the runner fails loudly below 80% because that's the signature of the extraction regex breaking against a new descriptor format (it's happened once already — see `routing-overrides.md`). Don't build on top of a failed gate; stop and report.

## 3. Classify
- Drop `Credit Card Payment` (statement payments) and `Journal Entry` (not card charges).
- Keep `Expense` (charges) and `Credit Card Credit` (refunds, negative).
- Refunds route by the cardholder name in their own descriptor (no cross-transaction tracing); no name → exceptions.

(Handled by `runner.py parse` — this section is here for reference, not a manual step.)

## 4. Cardholder extraction — two different mechanisms, not one
- **Brex Credit Card:** the descriptor carries the cardholder's name directly, after the last hyphen. `scripts/extract.py extract_name()` — Unicode-safe, verified 2026-07-01 against live data (96.6% match on Brex; the naive ASCII/digit-token version only got 23.8%, see `routing-overrides.md` for why).
- **Amex Plat \*12006 / Amex Plat 2 \*51005:** the memo carries **no cardholder name at all**, confirmed by direct inspection — not an extraction failure to try to fix with a better regex. `extract.py extract_last4()` pulls the physical card's last-4 digits instead; `references/card-mapping.tsv` resolves that to a person (see `manager-mapping.md` §3).
- **Amex Centurion \*01008:** needs neither — it's functionally a single dedicated card (currently Tameem Hourani).

Merchant = text before `MASTERCARD`/`XXXX`. QBO Category = last segment of `Split` after the final `:`. Both handled by `extract.py`.

## 5. Resolve cardholder → canonical name → manager
`scripts/runner.py resolve --rows parsed.json --manager-mapping-workbook <latest master or per-manager file> --card-mapping references/card-mapping.tsv --out resolved.json`

Order of resolution (see `manager-mapping.md` + `routing-overrides.md` for the full detail on each):
1. Manual overrides (`routing-overrides.md`) — always win.
2. Manager Mapping sheet + realized-master fallback, merged (a realized `UNMAPPED` never overrides a real Manager Mapping sheet answer).
3. Rollup teams — Tameem Hourani's team → Ayaan Israni, Matthew Keyes' team → Kevin Ebert.
4. Fuzzy match (edit-distance ≤2, unique surname only).
5. For Amex Plat/Plat 2 rows still unresolved: last-4 → `card-mapping.tsv` → back through steps 1–4.
6. Still nothing → exceptions. Never guess.

**Then** `resolve.py`'s `consolidate_names()` runs a second pass across the whole resolved set, merging spelling variants within the same manager bucket (e.g. `Connor Bracket`/`Connor Brackett`) — but only when `card-mapping.tsv` or the Manager Mapping sheet actually confirms the winning spelling. If neither does, it's left unmerged and flagged for a human, never guessed by string length. Read the printed "consolidated" and "flagged" lists every run.

## 6. Manager buckets (8) + Kevin combined
Buckets and nickname/guardrail rules are in `references/routing-overrides.md`. Kevin's file = his own reports + the full Connor/JT team + the full Jesse/Scott team **+ Matthew Keyes' team** (this last one only shows up via the rollup in §5, not directly in the Manager Mapping sheet — easy to miss). The same row legitimately appears in an underlying manager's file and Kevin's — never dedupe it away, never sum across files.

## 7. Build files (preserve the native PivotTable)
`scripts/runner.py build --rows resolved.json --template references/manager-file-template.xlsx --out-dir <path> --period "Jan-Jun 2026"`

openpyxl destroys pivots on save — `build_pivot.py` does NOT round-trip through it. It templates off `references/manager-file-template.xlsx` and edits the XML parts directly: rewrites `xl/worksheets/sheet2.xml` rows 3+ (keeping row 1 title/total and row 2's 17 headers), appends new `sharedStrings.xml` entries, and updates the pivotCache `worksheetSource ref` to `A2:Q{last_row}`. `refreshOnLoad="1"` is already set in the template, so the Summary pivot (rows: Manager + Card Member; cols: Month + Year; values: Sum of Amount) is meant to rebuild on open.

**Verified:** the output is valid (zip/XML well-formed — `build_pivot.validate_workbook()` checks this every run) and the data reads back with exact totals. **Not yet verified:** an actual pivot recalculation in a real spreadsheet engine — do this by hand the first few times a file goes out, before trusting it unattended.

Also builds an `Exceptions` workbook (unresolved rows) off the same template.

**Output location + naming (root §4, confirmed by Zayn 2026-07-01 to match the pre-existing Drive deliverables):** write to `outputs/End of Month CC Manager Report/YYYYMM/` (YYYYMM = target report month, for internal folder organization only). Files themselves follow the legacy `Amex Spend {period} - {label}.xlsx` convention, where `{period}` is a display range like `Jan-Jun 2026` (Jan 1 of the target year through the target month) — e.g. `Amex Spend Jan-Jun 2026 - Jay.xlsx`. Manager labels are the short forms already used in Drive: `Jay, Connor-JT, Jesse-Scott, Eli, Ayaan, Elyse, Toni, Kevin` (see `MANAGER_FILE_LABEL` in `runner.py`). Master is `Amex Spend {period} - MASTER.xlsx`, exceptions `Amex Spend {period} - Exceptions.xlsx` (Exceptions didn't exist in the legacy set — this is new). One file per deliverable per period; overwriting an existing file is a root §3 approval gate.

## 8. Deliver to Drive — REVIEW & APPROVE BEFORE DELIVERING
Run `scripts/runner.py deliver --out-dir <same out-dir as build> --period "<same period as build>" --manifest-out delivery_manifest.json`. This reconstructs the exact filenames `build` wrote (same `MANAGER_FILE_LABEL`, same naming pattern) and pairs each with its Drive folder — it fails loudly if an expected file is missing rather than planning around it. **Scripts have no network access** (same architecture as `brex-import`) — the manifest just tells the orchestrator (Claude) what to upload where; Claude makes the actual `mcp__BKPK__google_drive_create` calls, one per manifest entry, using each entry's `filename` **verbatim — never retyped by hand** (a hand-typed filename is exactly what produced `ConnorJT.xlsx` and a missing " - " on the first real delivery), with the auto-convert-to-Google-Sheets behavior **disabled** (a Sheets conversion would silently destroy the native PivotTable — this is the whole reason §7 exists).

**Drive delivery is gated (root §3/§4):** present the manifest (per-manager file→folder plan) and wait for explicit approval before uploading anything. This gate stays in place even for repeat/test runs of this skill — it is not a one-time bootstrapping step to remove once the pivot-table risk in §7 above is verified.

**Unverified as of 2026-07-01 — treat the first real delivery as a test, not routine.** BKPK's Drive-write schema was never confirmed against a live connection during development (the server kept disconnecting). On the first real run: upload to the finance-only folder first, open the result, and confirm the native PivotTable survived the upload intact before uploading into any of the 8 manager folders. If it doesn't survive, fall back to presenting the files for the human to save manually (the `brex-import` pattern) rather than guessing at a fix.

(One-time per-folder sharing with each manager is a manual human step — no Drive sharing scope in the tooling.)

## 9. Distribute via Slack — REVIEW & APPROVE BEFORE SENDING
Group membership + message template in `references/slack-groups.md`. **Do NOT auto-send (root §3).** Present the group DMs (members + the file each links to) and the exact message text; wait for explicit approval ("send") before posting. On approval, post one group DM per bucket via `slack_open_group_dm`. **Ayaan Israni: build the file, do NOT send a DM.** Link each group's own file; Kevin links the combined view.

## 10. Summary
Report: per-account row counts + gate results (§2); total/gross/refund/net; per-manager counts & totals; Kevin combined check; reconciliation (master == routed + exceptions, zero loss, no payments leaked — `runner.py build` prints this); exceptions (no-name + any unmapped people, split out by "genuinely not personal" like SaaS subscriptions vs. "needs a human to route"); name-consolidation results from §5; files/links delivered; and — after approval — which group DMs were sent.

## Number formatting (root §6)
Accounting/comma format, no currency symbol; negatives in parentheses; never use color to convey meaning. Match the reference workbook's layout exactly.
