#!/usr/bin/env python3
"""
Build the RapDev Department Listing workbook from a BambooHR report-228 pull.

WHAT IT DOES
  - Reads a saved JSON pull of BambooHR custom report 228 ("Department Listing",
    pulled with only_current_employees = false).
  - Keeps ACTIVE + FUTURE-hire employees only (drops anyone whose Employment
    Status is "Terminated", and drops the exclusion list below).
  - Starts from the reference workbook (reference/REFERENCE_RapDev_Department_Listing.xlsx)
    so the HC by Month and Key sheets carry over unchanged, then rebuilds the
    Department Listing sheet from the report in the agreed layout:

        A Employee #            H Employment Status: Date   O Employee Level
        B First Name            I Division                  P State
        C Last Name             J Department                Q QBO Department  = M
        D Last name, First name K Location                  R Prefix- Travel  (formula)
        E Gender                L Job Title                 S Prefix- Payroll (formula)
        F Hire Date             M Teams  (full QBO text)
        G Employment Status     N Billable Status

    QBO Department (Q) is literally "=M{row}" (the Teams cell). Q/R/S formulas
    look the QBO value up in the reference Key sheet for the prefixes.
  - Saves a new dated workbook into outputs/bamboohr-department-listing/{YYYY}/{YYYYMM}/.

WHAT IT DOES NOT DO
  - It does not call BambooHR. A human/agent with the BKPK connector pulls report
    228 first and passes the saved JSON path to this script (see SKILL.md).
  - It does not edit the reference workbook, write to QuickBooks, or send anything.
  - It does not auto-refresh the HC by Month sheet (carried from the reference as-is).

USAGE
  python build_department_listing.py <report_228.json> [output_xlsx_path]
    <report_228.json>   path to the saved report-228 JSON pull (required)
    [output_xlsx_path]  optional explicit output path (used for test runs).
                        If omitted, writes the dated file under the outputs tree.

REQUIRES: Python 3.9+, openpyxl  (pip install openpyxl)
"""
import sys
import json
import re
import zipfile
import shutil
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

# ---- Employee #s to drop on every run (test accounts, etc.) ----
# Adding to this list is a deliberate human change. #129 = "Test4 McTester".
EXCLUDE = {129}

# ---- Paths resolved relative to this script, so it is portable across machines ----
HERE = Path(__file__).resolve().parent              # .../bamboohr-department-listing/scripts
SKILL_DIR = HERE.parent                             # .../bamboohr-department-listing
REFERENCE = SKILL_DIR / "reference" / "REFERENCE_RapDev_Department_Listing.xlsx"
DRIVE_ROOT = SKILL_DIR.parent.parent                # .../RapDev Finance - Claude
OUT_ROOT = DRIVE_ROOT / "outputs" / "bamboohr-department-listing"

# ---- OOXML namespaces ----
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("", _NS_MAIN)
ET.register_namespace("r", _NS_REL)

_EPOCH = datetime.date(1899, 12, 30)   # Excel date serial origin

# Regex to extract (cell-ref, style-id) pairs from a single <row …>…</row> snippet
_CELL_STYLE_RE = re.compile(r'<c\s[^>]*\br="([A-Z]+\d+)"[^>]*\bs="(\d+)"')


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------

def _col_letter(n):
    """1-indexed column number → letter(s), e.g. 1→'A', 26→'Z', 27→'AA'."""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell_ref(row, col):
    return _col_letter(col) + str(row)


def _excel_serial(dt):
    """Python datetime/date → Excel serial number (days since 1899-12-30)."""
    if dt is None:
        return None
    d = dt.date() if isinstance(dt, datetime.datetime) else dt
    if not isinstance(d, datetime.date):
        return None
    return (d - _EPOCH).days


def _esc(s):
    """XML-escape a plain string value."""
    if s is None:
        return ""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def parse_date(s):
    if s in (None, ""):
        return None
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except (ValueError, TypeError):
        return s  # leave as-is if not an ISO date


def prefix_travel(r):
    return ('IF($N{r}="Yes","Cost of Goods Sold:COGS- Travel Expenses:",'
            'IF($N{r}="No",XLOOKUP($Q{r},Key!$I:$I,Key!$J:$J),"Review Billable Status"))'.format(r=r))


def prefix_payroll(r):
    return ('IF($N{r}="Yes","Cost of Goods Sold:COGS- Personnel Expense:",'
            'IF($N{r}="No",XLOOKUP($Q{r},Key!$I:$I,Key!$K:$K),"Review Billable Status"))'.format(r=r))


# ---------------------------------------------------------------------------
# Style-ID extraction  (pure XML — no openpyxl load; reads row 2 directly
#                       from the DL sheet XML bytes already in memory)
# ---------------------------------------------------------------------------

def _col_number(letters):
    """Column letters (e.g. 'A', 'AA') → 1-indexed integer."""
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def _get_style_ids_from_xml(dl_sheet_xml_bytes):
    """
    Return {col_number: style_id} for columns 1-19 read from row 2 of the
    DL worksheet XML.  No openpyxl involved — just a regex scan of the row.
    Falls back to 0 for any column whose style attribute is absent.
    """
    xml = dl_sheet_xml_bytes.decode("utf-8")

    # Locate row 2 text
    r2_start = xml.find('<row r="2"')
    if r2_start == -1:
        return {c: 0 for c in range(1, 20)}
    r2_end = xml.find("</row>", r2_start)
    if r2_end == -1:
        r2_end = len(xml)
    row2 = xml[r2_start:r2_end]

    ids = {c: 0 for c in range(1, 20)}
    for cell_ref, style_str in _CELL_STYLE_RE.findall(row2):
        # cell_ref like "A2", "B2", "AA2"
        col_letters = "".join(ch for ch in cell_ref if ch.isalpha())
        col_num = _col_number(col_letters)
        if 1 <= col_num <= 19:
            ids[col_num] = int(style_str)
    return ids


# ---------------------------------------------------------------------------
# Direct worksheet XML generation
# ---------------------------------------------------------------------------

def _find_dl_zip_entry(ref_path):
    """
    Return the zip-internal path (e.g. 'xl/worksheets/sheet1.xml') for the
    'Department Listing' sheet by parsing workbook.xml + its rels file.
    """
    with zipfile.ZipFile(ref_path) as zf:
        wb_root  = ET.fromstring(zf.read("xl/workbook.xml"))
        rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rid_to_target = {
        rel.get("Id"): rel.get("Target")
        for rel in rel_root
    }

    for sheet in wb_root.iter("{%s}sheet" % _NS_MAIN):
        if sheet.get("name") == "Department Listing":
            rid = sheet.get("{%s}id" % _NS_REL)
            target = rid_to_target.get(rid, "")
            if not target.startswith("xl/"):
                target = "xl/" + target
            return target

    raise RuntimeError("'Department Listing' sheet not found in workbook.xml")


def _build_sheetdata_xml(roster, style_ids, header_row_xml):
    """
    Build the full <sheetData> XML string for the Department Listing sheet.

    Uses inline strings (t="inlineStr") so the generated XML has no dependency
    on sharedStrings.xml — the reference copy's sharedStrings (used by HC by
    Month and Key) stays valid without modification.

    header_row_xml: the raw XML bytes of <row r="1" …>…</row> from the reference,
    preserved verbatim so column headers and their formatting carry over.
    """
    parts = ["<sheetData>", header_row_xml.decode("utf-8")]

    for row_idx, e in enumerate(roster, start=2):
        r = row_idx
        hire_serial   = _excel_serial(parse_date(e.get("hireDate")))
        status_serial = _excel_serial(parse_date(e.get("employeeStatusDate")))
        teams = e.get("teams") or ""

        def s_cell(col, val):
            """Inline-string cell."""
            ref = _cell_ref(r, col)
            sid = style_ids.get(col, 0)
            if val is None or val == "":
                return '<c r="%s" s="%d" t="inlineStr"><is><t /></is></c>' % (ref, sid)
            return '<c r="%s" s="%d" t="inlineStr"><is><t>%s</t></is></c>' % (ref, sid, _esc(val))

        def n_cell(col, val):
            """Numeric cell (integer or Excel date serial)."""
            ref = _cell_ref(r, col)
            sid = style_ids.get(col, 0)
            if val is None:
                return '<c r="%s" s="%d" t="n" />' % (ref, sid)
            return '<c r="%s" s="%d" t="n"><v>%s</v></c>' % (ref, sid, val)

        def f_cell(col, formula):
            """Plain formula cell (no leading =)."""
            ref = _cell_ref(r, col)
            sid = style_ids.get(col, 0)
            return '<c r="%s" s="%d"><f>%s</f><v /></c>' % (ref, sid, _esc(formula))

        def af_cell(col, formula):
            """Array formula cell (no leading =)."""
            ref = _cell_ref(r, col)
            sid = style_ids.get(col, 0)
            return ('<c r="%s" s="%d"><f t="array" ref="%s">%s</f><v /></c>'
                    % (ref, sid, ref, _esc(formula)))

        row_sid = style_ids.get(1, 0)  # row-level style (use col-A style as proxy)
        cells = "".join([
            n_cell(1,  int(e["employeeNumber"])),
            s_cell(2,  e.get("firstName")),
            s_cell(3,  e.get("lastName")),
            s_cell(4,  e.get("fullName2")),
            s_cell(5,  e.get("gender")),
            n_cell(6,  hire_serial),
            s_cell(7,  e.get("employmentHistoryStatus")),
            n_cell(8,  status_serial),
            s_cell(9,  e.get("division")),
            s_cell(10, e.get("department")),
            s_cell(11, e.get("location")),
            s_cell(12, e.get("jobTitle")),
            s_cell(13, teams),                              # M  Teams
            s_cell(14, e.get("customBillable")),            # N  Billable Status
            s_cell(15, e.get("customEmployeeLevel")),       # O  Employee Level
            s_cell(16, e.get("state")),                     # P  State
            f_cell(17, "M%d" % r),                          # Q  =M<r>
            af_cell(18, prefix_travel(r)),                  # R  array formula
            af_cell(19, prefix_payroll(r)),                 # S  array formula
        ])
        parts.append('<row r="%d" ht="12.75" customHeight="1" s="%d">%s</row>'
                     % (r, row_sid, cells))

    parts.append("</sheetData>")
    return "\n".join(parts)


def _extract_header_row_xml(dl_sheet_xml_bytes):
    """
    Extract the raw bytes for the <row r="1" …>…</row> element from the
    reference DL sheet XML.  Returns b"" if not found.
    """
    xml = dl_sheet_xml_bytes.decode("utf-8")
    start = xml.find('<row r="1"')
    if start == -1:
        return b""
    depth = 0
    i = start
    while i < len(xml):
        if xml[i] == "<":
            if xml[i:i+2] == "</":
                depth -= 1
                if depth == 0:
                    end = xml.index(">", i) + 1
                    return xml[start:end].encode("utf-8")
            elif xml[i:i+2] != "<!":
                depth += 1
                # self-closing?
                j = xml.index(">", i)
                if xml[j-1] == "/":
                    depth -= 1
                    if depth == 0:
                        return xml[start:j+1].encode("utf-8")
        i += 1
    return b""


def _replace_sheetdata(dl_sheet_xml_bytes, new_sheetdata_xml):
    """
    Replace the <sheetData>…</sheetData> block in the DL worksheet XML bytes
    with new_sheetdata_xml (a str).  Returns updated bytes.
    """
    xml = dl_sheet_xml_bytes.decode("utf-8")

    sd_open  = xml.find("<sheetData")
    sd_close = xml.find("</sheetData>")
    if sd_open == -1 or sd_close == -1:
        # Fallback: <sheetData /> empty element
        sd_self = xml.find("<sheetData")
        gt = xml.index(">", sd_self)
        replaced = xml[:sd_self] + new_sheetdata_xml + xml[gt + 1:]
    else:
        replaced = xml[:sd_open] + new_sheetdata_xml + xml[sd_close + len("</sheetData>"):]

    return replaced.encode("utf-8")


# ---------------------------------------------------------------------------
# Main build  (zipfile surgery — never re-parses or re-serializes HC by Month
#              or Key; only rewrites the DL sheet XML in-place in the zip)
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("ERROR: pass the path to the saved report-228 JSON.\n"
              "  python build_department_listing.py <report_228.json> [output_xlsx_path]")
        sys.exit(1)

    report_path = sys.argv[1]
    explicit_out = sys.argv[2] if len(sys.argv) > 2 else None

    if not REFERENCE.exists():
        print("ERROR: reference workbook not found at %s" % REFERENCE)
        sys.exit(1)

    with open(report_path, encoding="utf-8") as fh:
        data = json.load(fh)
    emps = data.get("employees", [])
    if not emps:
        print("ERROR: report JSON has no employees - treat as a failed/partial pull. Stopping.")
        sys.exit(1)

    # ---- filter to active + future, apply exclusion list ----
    roster = []
    skipped_excl = []
    dropped_term = 0
    for e in emps:
        num = e.get("employeeNumber")
        if num in (None, ""):
            continue
        num = int(num)
        if num in EXCLUDE:
            skipped_excl.append(num)
            continue
        status = (e.get("employmentHistoryStatus") or "").strip()
        if status == "Terminated":
            dropped_term += 1
            continue
        roster.append(e)
    roster.sort(key=lambda e: int(e["employeeNumber"]))

    # ---- resolve output path ----
    run = datetime.date.today()
    if explicit_out:
        outpath = Path(explicit_out)
        outpath.parent.mkdir(parents=True, exist_ok=True)
    else:
        outdir = OUT_ROOT / run.strftime("%Y") / run.strftime("%Y%m")
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / ("RapDev_Department_Listing_%s.xlsx" % run.strftime("%Y%m%d"))

    if outpath.exists():
        print("OVERWRITE GUARD: %s already exists. Stopping - a same-day re-run is an "
              "overwrite and needs human approval (per CLAUDE.md)." % outpath)
        sys.exit(2)

    # ---- Step 1: locate Department Listing sheet inside the reference zip ----
    dl_zip_entry = _find_dl_zip_entry(REFERENCE)

    # ---- Step 2: read the DL sheet XML once; extract styles and header row ----
    with zipfile.ZipFile(REFERENCE) as zf:
        dl_xml_bytes = zf.read(dl_zip_entry)

    style_ids = _get_style_ids_from_xml(dl_xml_bytes)

    header_row_xml = _extract_header_row_xml(dl_xml_bytes)

    # ---- Step 4: validate roster flags ----
    short_teams = []
    blank_teams = []
    for e in roster:
        num = int(e["employeeNumber"])
        teams = e.get("teams")
        status = (e.get("employmentHistoryStatus") or "").strip()
        if teams in (None, ""):
            blank_teams.append(num)
        elif ":" not in str(teams) and status not in ("", "Terminated"):
            short_teams.append(num)

    # ---- Step 5: build new sheetData XML ----
    new_sheetdata = _build_sheetdata_xml(roster, style_ids, header_row_xml)

    # ---- Step 6: patch the DL sheet XML ----
    new_dl_xml_bytes = _replace_sheetdata(dl_xml_bytes, new_sheetdata)

    # ---- Step 7: write output xlsx by copying reference zip, replacing DL sheet ----
    with zipfile.ZipFile(REFERENCE, "r") as src_zf, \
         zipfile.ZipFile(outpath, "w", compression=zipfile.ZIP_DEFLATED) as dst_zf:
        for item in src_zf.infolist():
            if item.filename == dl_zip_entry:
                dst_zf.writestr(item, new_dl_xml_bytes)
            else:
                dst_zf.writestr(item, src_zf.read(item.filename))

    # ---- run summary ----
    print("=== Department Listing build complete ===")
    print("Output: %s" % outpath)
    print("Active + future employees written: %d" % len(roster))
    print("Terminated dropped: %d" % dropped_term)
    print("Excluded (exclusion list): %s" % (skipped_excl or "none"))
    print("HC by Month + Key sheets: carried from reference unchanged.")
    if short_teams:
        print("FLAG - active employees with a short (non-full) Teams value -> fix Teams in BambooHR: %s" % short_teams)
    if blank_teams:
        print("FLAG - employees with blank Teams (future hires / not yet set), QBO will be blank: %s" % blank_teams)
    if not short_teams and not blank_teams:
        print("All employees have a full-path Teams value.")


if __name__ == "__main__":
    main()
