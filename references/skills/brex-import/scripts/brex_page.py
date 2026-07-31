#!/usr/bin/env python3
"""
brex_page.py - process ONE page of brex_expenses_list output for the feed pull.

Usage:
    python brex_page.py <path-to-saved-brex_expenses_list-result.txt>

Posted date = payment_posted_at[:10] (the UTC timestamp) = Brex's "Posted date (UTC)"
column, used VERBATIM. Never estimate/guess a clearing date. Expenses with no
payment_posted_at are not yet posted -> skipped.

Per page it:
  - robustly parses the saved result (leading text + JSON array + trailing cursor),
  - keeps expenses whose posted date is within [WIN_START, WIN_END],
  - accumulates them (dedupe by id) into TEMP/brex_acc.json,
  - prints a posted-date histogram, the next cursor, and whether to continue.

Loop: if it prints `continue? True`, call brex_expenses_list again with the printed
cursor, save the result, run this script on the new file. Stop at `continue? False`.
When done, TEMP/brex_acc.json holds the full in-window set -> use as Brex_expenses.json.
"""
import json, re, os, sys
from datetime import date, timedelta

# ---- Brex POSTED-date window (UTC), inclusive ----
# Window is REQUIRED and resolved from: argv 2 & 3  ->  env BREX_START/BREX_END.
# The orchestrator passes it as args so this script is NEVER edited per run:
#   python brex_page.py <PAGE_FILE> <START> <END>
# No hardcoded fallback -- fail loud rather than silently use a stale window.
LAG_DAYS  = 7   # settlement-lag buffer: keep paging until purchases predate WIN_START - LAG_DAYS
# ---------------------------------------------------

WIN_START = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BREX_START")
WIN_END   = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("BREX_END")
if not (WIN_START and WIN_END):
    sys.exit("brex_page.py ABORT: posted-date window required -- pass `python brex_page.py "
             "<PAGE_FILE> <START> <END>` or set BREX_START/BREX_END. Refusing a stale default window.")

FLOOR = (date.fromisoformat(WIN_START) - timedelta(days=LAG_DAYS)).isoformat()
TEMP = os.environ.get("TEMP", "/tmp")
ACC_PATH = os.path.join(TEMP, "brex_acc.json")

txt = open(sys.argv[1], encoding="utf-8").read()
exps, _ = json.JSONDecoder().raw_decode(txt, txt.index("["))   # robust parse
m = re.search(r"Pass cursor:\s*([A-Za-z0-9+/=_\-]+)", txt)
cursor = m.group(1) if m else None

def posted(e): return (e.get("payment_posted_at") or "")[:10]
def purch(e):  return (e.get("purchased_at") or "")[:10]

acc = json.load(open(ACC_PATH)) if os.path.exists(ACC_PATH) else {"ids": [], "exps": []}
ids = set(acc["ids"]); added = 0
for e in exps:
    if WIN_START <= posted(e) <= WIN_END and e.get("id") not in ids:
        ids.add(e.get("id")); acc["ids"].append(e.get("id")); acc["exps"].append(e); added += 1
json.dump(acc, open(ACC_PATH, "w"), indent=1)

pa = sorted(purch(e) for e in exps if purch(e))
pp = sorted(posted(e) for e in exps if posted(e))
page_max_purch = pa[-1] if pa else ""
cont = (added > 0) or (page_max_purch >= FLOOR)

print("page count:", len(exps))
print("purchased range:", (pa[0] if pa else None), "->", (pa[-1] if pa else None))
print("posted histogram:", {d: pp.count(d) for d in sorted(set(pp))})
print("added in-window:", added, "| accumulated total:", len(acc["exps"]))
print("cursor:", cursor)
print("continue?", cont, f"(stop when a page's newest purchase < {FLOOR} AND nothing added)")
open(os.path.join(TEMP, "brex_cursor.txt"), "w").write(cursor or "")
