"""Name-alias reconciliation for the EE ID lookup in the Brex import xlsx.

The workbook's `EE ID` column (QBO Transactions!P) looks up the Brex cardholder
name (Card Name, derived from the DESCRIPTION's last hyphen-segment) against
Department Listing's name-key column (First+Last from BambooHR). When Brex's
name differs from BambooHR's legal name (e.g. a preferred first name), the
lookup misses and EE ID goes blank.

This module never guesses silently. It:
  - loads/saves the human-curated alias table in references/name-aliases.md
  - finds cardholder names in a run's xlsx that resolve to neither Department
    Listing nor the alias table
  - for each, looks for exactly ONE narrow, explainable candidate (exact last
    name + Brex first name is a case-insensitive prefix of the BambooHR first
    name) -- anything less certain is flagged with no guess, for a human to
    pick via AskUserQuestion.

No fuzzy string-distance matching on purpose: this company's own roster has
name-variant collisions (Daniel Roy / Daniel Roy Jr, Dan Hennessy / Daniel
Hennessy) where a looser matcher could silently attach the wrong EE ID.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import NamedTuple


class Alias(NamedTuple):
    brex_name: str
    ee_id: str
    bamboo_name: str
    confirmed: str = ""
    note: str = ""


def cardholder_from_description(desc: str | None) -> str:
    """Mirror the workbook's Card Name formula: text after the LAST '-' in DESCRIPTION."""
    if not desc:
        return ""
    return desc.rsplit("-", 1)[-1].strip()


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def load_aliases(path: Path) -> list[Alias]:
    """Parse the single markdown table in name-aliases.md into Alias rows."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    in_table = False
    for line in lines:
        if re.match(r"^\s*\|\s*Brex Name\s*\|", line):
            in_table = True
            continue
        if not in_table:
            continue
        if re.match(r"^\s*\|[-\s|]+\|\s*$", line):
            continue
        if not line.strip().startswith("|"):
            break
        cols = _split_row(line)
        if len(cols) < 3 or not cols[0]:
            continue
        out.append(Alias(
            brex_name=cols[0], ee_id=cols[1] if len(cols) > 1 else "",
            bamboo_name=cols[2] if len(cols) > 2 else "",
            confirmed=cols[3] if len(cols) > 3 else "",
            note=cols[4] if len(cols) > 4 else "",
        ))
    return out


def append_aliases(path: Path, new_entries: list[Alias]) -> int:
    """Append confirmed aliases not already present (dedup by lowercase brex_name). Returns count added."""
    existing = {a.brex_name.strip().lower() for a in load_aliases(path)}
    to_add = [a for a in new_entries if a.brex_name.strip().lower() not in existing]
    if not to_add:
        return 0
    with path.open("a", encoding="utf-8") as f:
        for a in to_add:
            f.write(f"| {a.brex_name} | {a.ee_id} | {a.bamboo_name} | {a.confirmed} | {a.note} |\n")
    return len(to_add)


def suggest_matches(unmapped_names: list[str], dept_rows: list[dict]) -> tuple[list[dict], list[str]]:
    """dept_rows: [{ee, first, last}]. Returns (suggestions, no_candidate).

    suggestions: [{brex_name, candidate_ee, candidate_name, reason}] -- exactly
    one qualifying Department Listing row per suggestion.
    no_candidate: brex names with zero or multiple (ambiguous) candidates -- flagged, not guessed.
    """
    suggestions, no_candidate = [], []
    for name in unmapped_names:
        parts = name.split()
        if len(parts) < 2:
            no_candidate.append(name)
            continue
        brex_first, brex_last = parts[0].lower(), parts[-1].lower()
        candidates = [
            d for d in dept_rows
            if str(d.get("last", "")).strip().lower() == brex_last
            and str(d.get("first", "")).strip().lower().startswith(brex_first)
        ]
        if len(candidates) == 1:
            d = candidates[0]
            suggestions.append({
                "brex_name": name,
                "candidate_ee": str(d["ee"]),
                "candidate_name": f"{d['first']} {d['last']}".strip(),
                "reason": f"exact last name + Brex first name '{parts[0]}' is a prefix of BambooHR first name '{d['first']}'",
            })
        else:
            no_candidate.append(name)
    return suggestions, no_candidate
