"""Shared date/column helpers for the Synechron monthly reporting build scripts.

No network access, no Drive/QBO calls — pure functions over already-pulled data
and local workbook files. Claude (the calling agent) is responsible for pulling
QBO/BambooHR/POC/Forecast data and handing paths/JSON to these scripts.
"""
import datetime
import calendar


MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def month_end(year: int, month: int) -> datetime.date:
    return datetime.date(year, month, calendar.monthrange(year, month)[1])


def business_days_in_month(year: int, month: int, holidays=None) -> int:
    """Row 7 'Avg. working days' — Mon-Fri count minus company holidays.

    holidays: iterable of datetime.date within the month to exclude. Pass an
    empty list/None if there are none that month; never invent a holiday list
    if the caller hasn't supplied one.
    """
    holidays = set(holidays or [])
    _, days_in_month = calendar.monthrange(year, month)
    count = 0
    for day in range(1, days_in_month + 1):
        d = datetime.date(year, month, day)
        if d.weekday() < 5 and d not in holidays:
            count += 1
    return count


MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]


def _normalize(s: str) -> str:
    """Collapse whitespace and lowercase, so 'June' 26 (A)' and 'Jun'26 (A)' compare equal.
    Header formatting in this template has been observed to drift (e.g. full vs. abbreviated
    month name, inconsistent spacing around the apostrophe) — never assume one clean format.
    """
    return "".join(s.lower().split())


def dashboard_actuals_header_candidates(year: int, month: int):
    """Possible row-5 header strings for a target month's actuals column — the
    template has used both abbreviated ('Jun') and full ('June') month names.
    Returns normalized (whitespace-stripped, lowercased) candidates to compare
    against a normalized cell value, since exact spacing isn't reliable.
    """
    yy = str(year)[2:]
    candidates = []
    for name in (MONTH_ABBR[month - 1], MONTH_FULL[month - 1]):
        candidates.append(f"{name}'{yy} (A)")
        candidates.append(f"{name}' {yy} (A)")
    return [_normalize(c) for c in candidates]


def find_column_by_header(ws, header_row: int, target_text_or_candidates, max_col: int = 200):
    """Scan a row for a header matching target_text_or_candidates (a string or a
    list of normalized candidate strings), return the 1-indexed column, or None
    if not found (caller should flag, not guess)."""
    if isinstance(target_text_or_candidates, str):
        candidates = {_normalize(target_text_or_candidates)}
    else:
        candidates = set(target_text_or_candidates)
    for col in range(1, max_col + 1):
        v = ws.cell(row=header_row, column=col).value
        if isinstance(v, str) and _normalize(v) in candidates:
            return col
    return None


def poc_utilization_column(year: int, month: int) -> int:
    """`Employee Utilization` tab, row 197. Column D (index 4) = Jan 2022 anchor."""
    return 4 + (year - 2022) * 12 + (month - 1)


def poc_rate_row_column(ws, year: int, month: int, date_header_row: int = 4, max_col: int = 200):
    """`SOW level` tab, row 574 ('Rate'). Column position isn't a fixed offset like
    the utilization tab — row 4 carries an actual date header above the block.
    Scan for the matching month-end date instead of computing an offset.
    """
    target = month_end(year, month)
    for col in range(1, max_col + 1):
        v = ws.cell(row=date_header_row, column=col).value
        if isinstance(v, datetime.datetime) and v.date() == target:
            return col
        if isinstance(v, datetime.date) and v == target:
            return col
    return None
