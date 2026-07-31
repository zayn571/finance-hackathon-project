"""Parse the user's memory.md markdown tables into Python data structures.

memory.md is the user's curated merchant → Payee Override mappings, organized
by section (hard-confirmed, this-month, historical specific, historical fallback,
inconsistent). Each section is a markdown table with columns like:

    | Description contains | Payee Override | ... |
    |---|---|---|
    | `wlv mobile app ecomm` | Travel Vendor | ... |

We parse those tables and return them as ordered lists of (pattern, target) tuples,
preserving the precedence: hard-confirmed > this-month > historical specific >
historical fallback. Inconsistent entries are returned separately (medium confidence).

This lives in the skill because the structure of memory.md is part of the workflow
contract. The data itself lives in the user's workspace and evolves over time —
this module just knows how to read it.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import NamedTuple


class MemoryEntry(NamedTuple):
    pattern: str         # lowercase substring to match against the merchant string
    target: str          # Payee Override value
    section: str         # which memory.md section it came from
    notes: str = ""      # the "reason" / "notes" column if present
    sub_cat: str = ""    # optional Sub Category Override; blank = use resolver default


def _extract_first_backticked_or_plain(cell: str) -> str:
    """Cell text may be `wrapped in backticks` or plain. Strip both."""
    m = re.match(r"\s*`([^`]+)`\s*$", cell)
    if m:
        return m.group(1).strip()
    return cell.strip()


_TARGET_HEADER_KEYWORDS = (
    "payee override",
    "fallback",
    "current default",
    "target",
)


def _find_target_col(header_cols: list[str]) -> int:
    """Identify which column holds the Payee Override target value.

    The various memory.md tables use different headers — "Payee Override",
    "Fallback", "Current default". We look for any of those (case-insensitive
    substring match). If none match, default to col 1 (the second column,
    which is what most tables use)."""
    for i, h in enumerate(header_cols):
        for kw in _TARGET_HEADER_KEYWORDS:
            if kw in h:
                return i
    return 1


def _find_sub_cat_col(header_cols: list[str]) -> int:
    """Find the Sub Category Override column if present. Returns -1 if absent."""
    for i, h in enumerate(header_cols):
        if "sub category" in h or "sub cat" in h:
            return i
    return -1


def _parse_table(lines: list[str], section_name: str) -> list[MemoryEntry]:
    """Parse markdown tables from a list of lines. Multiple tables in the same
    line list are all parsed (e.g. when find_sections merges several
    same-named sections — May + June "This month's confirmed"). Each table
    starts at the first `|` line after a gap and ends at the next gap.
    """
    rows = []
    in_table = False
    target_col = 1
    sub_cat_col = -1
    for line in lines:
        line = line.rstrip()
        if not line.startswith("|"):
            # End of current table — but DON'T break; keep scanning for the
            # next one (handles merged sections containing multiple tables).
            in_table = False
            target_col = 1
            sub_cat_col = -1
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not in_table:
            # header row
            header_cols = [c.lower() for c in cells]
            target_col = _find_target_col(header_cols)
            sub_cat_col = _find_sub_cat_col(header_cols)
            in_table = True
            continue
        if all(re.match(r"^[-: ]+$", c) for c in cells):
            continue  # separator row
        if len(cells) <= target_col:
            continue  # row too short — skip
        pattern = _extract_first_backticked_or_plain(cells[0]).lower()
        target = cells[target_col].strip()
        # Skip rows where target is clearly a count or numeric (defensive against
        # mis-detection)
        if not target or target.isdigit():
            continue
        sub_cat = ""
        if 0 <= sub_cat_col < len(cells):
            sub_cat = cells[sub_cat_col].strip()
        skip_cols = {0, target_col}
        if sub_cat_col >= 0:
            skip_cols.add(sub_cat_col)
        notes = " | ".join(c for i, c in enumerate(cells) if i not in skip_cols).strip()
        rows.append(MemoryEntry(pattern, target, section_name, notes, sub_cat))
    return rows


def load_memory(memory_path: str | Path) -> dict[str, list[MemoryEntry]]:
    """Parse memory.md and return entries grouped by precedence section.

    Returns dict with keys:
        - "hard_confirmed" (highest precedence)
        - "this_month"
        - "historical_specific"
        - "historical_fallback"
        - "inconsistent" (medium confidence, flag for review)
    """
    text = Path(memory_path).read_text()
    lines = text.split("\n")

    # Find section markers. Sections are H2 (##) headers.
    sections = {}
    current_section = None
    current_buf: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_section:
                sections[current_section] = current_buf
            current_section = line[3:].strip().lower()
            current_buf = []
        else:
            current_buf.append(line)
    if current_section:
        sections[current_section] = current_buf

    # Map section names to canonical keys. find_sections returns the
    # concatenated body of ALL sections whose header matches any keyword —
    # this matters for "This month's confirmed" because the user can have
    # multiple month-specific sections (May 2026, June 2026, etc.) and we
    # want entries from every one of them in the this_month bucket.
    def find_sections(keyword_list):
        merged: list[str] = []
        for key in sections:
            if any(kw in key for kw in keyword_list):
                merged.extend(sections[key])
        return merged

    result = {
        "hard_confirmed":      _parse_table(find_sections(["hard-confirmed", "hard confirmed"]), "hard_confirmed"),
        "this_month":          _parse_table(find_sections(["this month", "this-month"]), "this_month"),
        "historical_specific": _parse_table(find_sections(["historical specific"]), "historical_specific"),
        "historical_fallback": _parse_table(find_sections(["historical fallback"]), "historical_fallback"),
        "inconsistent":        _parse_table(find_sections(["inconsistent"]), "inconsistent"),
    }
    return result


def find_longest_match(merchant_lc: str, entries: list[MemoryEntry]) -> MemoryEntry | None:
    """Return the entry whose pattern is the longest substring of the merchant.
    Implements the 'longest pattern wins' rule from memory.md."""
    best = None
    for e in entries:
        if e.pattern in merchant_lc:
            if best is None or len(e.pattern) > len(best.pattern):
                best = e
    return best


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: memory_loader.py <path-to-memory.md>", file=sys.stderr)
        sys.exit(1)
    mem = load_memory(sys.argv[1])
    print(json.dumps({k: [(e.pattern, e.target) for e in v] for k, v in mem.items()}, indent=2))
