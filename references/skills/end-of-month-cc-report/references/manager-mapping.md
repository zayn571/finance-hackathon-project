# Cardholder → manager mapping (source of truth)

**Do not freeze a copy here.** Per root CLAUDE.md §2, the authoritative source is the **BambooHR Department Listing report** (not yet connected). Until it is, the working source is the **Manager Mapping sheet** — the 3rd tab of every per-manager workbook and the master (tab order: `Amex Spend Summary` / `Amex Txn Details` / `Manager Mapping`). Columns: `Card Name → Lead / Department / EE ID`. ~115 rows. **Don't confuse this with `card-mapping.tsv`** (§3 below), which is a different table keyed by physical card last-4 digits, not by name.

## 1. Two-source merge (verified 2026-07-01 against real Jan–Jun data)

The Manager Mapping sheet alone resolves only ~52% of a fresh QBO pull — it lags the roster. Merge two sources, in this priority order:

1. **Manager Mapping sheet** (the tab above) — read fresh every run, ask a human to confirm it's current (root §2).
2. **Realized fallback** — the `Manager` column already baked into the *latest* master's `Amex Txn Details` tab (Card Member → Manager, built by scanning every row). This has broader coverage (~165 people) because it reflects whoever actually got attributed historically, including people newer than the Manager Mapping sheet.

**Merge rule — realized source wins on a genuine answer, but never on a non-answer.** If the realized fallback says `UNMAPPED` for someone the Manager Mapping sheet *does* have an answer for, keep the Manager Mapping sheet's answer — a stale "we never figured it out" must not clobber a real one. (Caught in production: `Henri Hatch` sat in the historical master's own UNMAPPED bucket for 3 transactions despite the Manager Mapping sheet clearly saying `Jay Barker` the whole time. Silently letting the realized source overwrite by default would keep re-losing him every month.)

## 2. Rollup teams — a Manager Mapping sheet "Lead" is not always one of the 8 buckets

Some `Lead` values in the Manager Mapping sheet are themselves individual cardholders, not one of the 8 final buckets, and roll up one more hop:

- **Tameem Hourani** (+ his team: Alexandra Hourani, Ayla Hourani, Canaan Hourani, Jon Lawer, Sami Ulla, Scott Lane, Allison Schwenn, Mickenzi Krpec) → **Ayaan Israni**
- **Matthew Keyes** (+ his team: Daniel Mooney, Matt Keyes, Richard Upshall) → **Kevin Ebert**

Confirmed by Zayn 2026-07-01. Verify against `references/routing-overrides.md` §Manager buckets before assuming this list is exhaustive — a Lead value that isn't one of the 8 buckets and isn't Tameem/Matthew above means a new rollup exists that hasn't been documented yet; flag it, don't guess.

## 3. Amex Plat / Plat 2 need a *different* lookup entirely — `card-mapping.tsv`

Two of the four accounts (`Amex Plat *12006`, `Amex Plat 2 *51005`) are control accounts with dozens of individual sub-cards attached, and **the QBO transaction memo carries zero cardholder-name text for these** — confirmed by direct inspection, not an extraction failure. What the memo *does* carry is the physical card's last-4 digits (e.g. `...XXXX2006`). `references/card-mapping.tsv` maps `last-4 → Card Name / Department / EE ID` for exactly these two programs. When descriptor-based name extraction (`routing-overrides.md`) comes up empty on a Plat/Plat 2 row, pull the last-4 out of the memo and look it up there instead — then resolve that name through §1 same as any other cardholder.

- `Amex Centurion *01008` needs neither lookup — it's functionally a single dedicated card (Tameem Hourani), confirmed by his name appearing in its refund memos and >99% of its spend attributing to him.
- `Brex Credit Card` needs neither lookup — the descriptor carries the cardholder's name directly (see `routing-overrides.md` extraction regex).

Every run:
1. Read the Manager Mapping sheet fresh from the latest master workbook; merge with the realized fallback per §1.
2. **Ask a human to confirm the mapping is current** before relying on it to build or deliver files (root §2).
3. Apply the rollups (§2), then the overrides/guardrails/nicknames in `routing-overrides.md` on top.
4. For Amex Plat / Plat 2 rows with no name in the descriptor, fall back to `card-mapping.tsv` (§3) before giving up and routing to exceptions.
