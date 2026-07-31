/**
 * Server-side Brex card feed for the finance dashboard.
 *
 * The dashboard cannot call Brex from the browser — the API needs a secret and
 * CORS blocks it. This module belongs in an API route (Next.js route handler,
 * Lambda, whatever the repo settles on); the page fetches the JSON it returns.
 *
 * Why paginate server-side: Brex returns ~32 CARD expenses per day for RapDev and
 * caps pages at 100, so July 2026 is roughly 1,000 records / 10 round trips. That
 * is fine in a request handler with a short cache, and far too slow on page load.
 */

const BREX_API = "https://platform.brexapis.com/v1/expenses/card";

export interface BrexExpense {
  id: string;
  purchased_at: string;
  merchant?: { raw_descriptor?: string; mcc?: string };
  billing_amount?: { amount: number; currency: string };
  status: string;
  payment_status: string;
  category?: string;
  department?: { name?: string };
}

export interface FeedTransaction {
  id: string;
  date: string;
  time: string;
  merchant: string;
  amount: number;
  status: "Cleared" | "Pending" | "Canceled";
  category: string;
  team: string | null;
}

function mapStatus(e: BrexExpense): FeedTransaction["status"] {
  if (e.payment_status === "CLEARED") return "Cleared";
  if (e.payment_status === "CANCELED" || e.status === "CANCELED") return "Canceled";
  return "Pending";
}

/** Fetch every CARD expense in a window, following Brex's cursor. */
export async function fetchBrexExpenses(
  token: string,
  purchasedAfter: string,
  purchasedBefore: string
): Promise<BrexExpense[]> {
  const out: BrexExpense[] = [];
  let cursor: string | undefined;

  do {
    const url = new URL(BREX_API);
    url.searchParams.set("limit", "100");
    url.searchParams.set("purchased_at_start", purchasedAfter);
    url.searchParams.set("purchased_at_end", purchasedBefore);
    url.searchParams.append("expand[]", "merchant");
    url.searchParams.append("expand[]", "department");
    if (cursor) url.searchParams.set("cursor", cursor);

    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`Brex ${res.status}: ${await res.text()}`);

    const page = (await res.json()) as { items: BrexExpense[]; next_cursor?: string };
    out.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);

  return out;
}

/**
 * Shape expenses for the dashboard card.
 * Cardholder identity is dropped on purpose — the card shows initials only, and
 * nothing downstream should need the name.
 */
export function toFeed(expenses: BrexExpense[]): FeedTransaction[] {
  return expenses
    .map((e) => {
      const at = new Date(e.purchased_at);
      return {
        id: e.id,
        date: at.toISOString().slice(0, 10),
        time: at.toISOString().slice(11, 16),
        merchant: e.merchant?.raw_descriptor ?? "Unknown merchant",
        amount: (e.billing_amount?.amount ?? 0) / 100,
        status: mapStatus(e),
        category: e.category ?? "UNCATEGORIZED",
        team: e.department?.name ?? null,
      };
    })
    .sort((a, b) => (a.date + a.time < b.date + b.time ? 1 : -1));
}

/** Roll a feed up into the card's category bars. */
export function toCategoryTotals(feed: FeedTransaction[]): { category: string; amount: number }[] {
  const buckets = new Map<string, number>();
  for (const t of feed) {
    if (t.status === "Canceled") continue;
    buckets.set(t.category, (buckets.get(t.category) ?? 0) + t.amount);
  }
  return [...buckets.entries()]
    .map(([category, amount]) => ({ category, amount }))
    .sort((a, b) => b.amount - a.amount);
}

/**
 * Answer merchant questions from the chat panel: "what did we spend on Uber in
 * the last two days". Descriptors vary (UBER *TRIP, UBER *EATS,
 * UBR* PENDING.UBER.COM), so match loosely and report what was matched.
 */
export function merchantTotal(
  feed: FeedTransaction[],
  needle: string
): { total: number; count: number; matched: string[] } {
  const n = needle.toLowerCase().replace(/[^a-z]/g, "");
  const hits = feed.filter(
    (t) => t.status !== "Canceled" && t.merchant.toLowerCase().replace(/[^a-z]/g, "").includes(n)
  );
  return {
    total: hits.reduce((a, t) => a + t.amount, 0),
    count: hits.length,
    matched: [...new Set(hits.map((t) => t.merchant))],
  };
}
