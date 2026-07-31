import bankRules from "../data/qboBankRules.json";

/**
 * Categorisation follows QuickBooks bank-rule priority first.
 *
 * QuickBooks has no priority field — it evaluates bank rules in list order and
 * the first match wins. That order is preserved in qboBankRules.json as
 * `priority` (1 = evaluated first), so resolving here reproduces what QBO itself
 * would assign rather than applying our own preference.
 *
 * Only when no rule matches does anything else decide the category, and the
 * caller supplies that fallback explicitly.
 */

export interface BankRule {
  priority: number;
  name: string;
  patterns: string[];
  requireAll: boolean;
  account: string;
  subCategory: string;
  department: string | null;
  payee: string | null;
}

export const RULES = (bankRules as { rules: BankRule[] }).rules;

// Pre-lowered once; every descriptor comparison is case-insensitive.
const PREPARED = RULES.map((r) => ({ rule: r, pats: r.patterns.map((p) => p.toLowerCase()) }));

export type CategorySource = "bank-rule" | "fallback" | "unmatched";

export interface Resolution {
  subCategory: string | null;
  account: string | null;
  department: string | null;
  payee: string | null;
  source: CategorySource;
  rule?: { priority: number; name: string; pattern: string };
}

/**
 * Resolve one descriptor against the rule set in priority order.
 *
 * `fallback` is used only when no rule matches — typically the category already
 * carried on the transaction import file.
 */
export function resolveCategory(
  descriptor: string,
  fallback?: { subCategory?: string | null; account?: string | null; department?: string | null }
): Resolution {
  const d = (descriptor || "").toLowerCase();

  for (const { rule, pats } of PREPARED) {
    const matched = rule.requireAll ? pats.every((p) => d.includes(p)) : pats.find((p) => d.includes(p));
    if (!matched) continue;
    return {
      subCategory: rule.subCategory,
      account: rule.account,
      department: rule.department,
      payee: rule.payee,
      source: "bank-rule",
      rule: {
        priority: rule.priority,
        name: rule.name,
        pattern: typeof matched === "string" ? matched : rule.patterns.join(" + "),
      },
    };
  }

  if (fallback?.subCategory || fallback?.account) {
    return {
      subCategory: fallback.subCategory ?? null,
      account: fallback.account ?? null,
      department: fallback.department ?? null,
      payee: null,
      source: "fallback",
    };
  }

  return { subCategory: null, account: null, department: null, payee: null, source: "unmatched" };
}

/**
 * Every rule whose pattern appears in the descriptor, in priority order. The
 * first entry is the one that wins; the rest are shadowed. Useful for spotting a
 * broad rule sitting above a narrower one.
 */
export function matchingRules(descriptor: string): BankRule[] {
  const d = (descriptor || "").toLowerCase();
  return PREPARED.filter(({ rule, pats }) =>
    rule.requireAll ? pats.every((p) => d.includes(p)) : pats.some((p) => d.includes(p))
  ).map(({ rule }) => rule);
}
