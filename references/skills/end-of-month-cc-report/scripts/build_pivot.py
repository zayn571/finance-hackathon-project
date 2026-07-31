"""Build a per-manager or master workbook by templating off a real prior
workbook and editing its XML parts directly (openpyxl destroys the native
PivotTable on save - do NOT round-trip through it for writing).

Verified 2026-07-01: this approach produces a valid xlsx (zip/XML well-formed,
data reads back with exact totals via openpyxl) off the real per-manager
template. NOT verified: an actual pivot-recalc in a real spreadsheet engine
(headless LibreOffice was broken in the dev sandbox, even for a blank file) -
open one output by hand after the first real run and confirm the Summary
pivot rebuilds on open before trusting this unattended.
"""
import re
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

DETAIL_HEADERS = [
    "Date", "Receipt", "Description", "Card Member", "Account #", "Amount",
    "Extended Details", "Appears On Your Statement As", "Address", "City/State",
    "Zip Code", "Country", "Reference", "Category", "Month", "Year", "Manager",
]

ACCT_LABEL = {
    "Brex Credit Card": "21140 Brex Credit Card",
    "Amex Plat *12006": "21120 Amex Plat *12006",
    "Amex Plat 2 *51005": "21130 Amex Plat 2 *51005",
    "Amex Centurion *01008": "21150 Amex Centurion *01008",
}


def _rows_to_sheet2_xml(rows, sheet2_xml, shared_xml):
    m = re.search(r'(<sheetData>.*?<row r="2">.*?</row>)(.*)</sheetData>', sheet2_xml, re.S)
    if not m:
        raise RuntimeError("template sheet2.xml doesn't match the expected row1/row2 shape")
    head = m.group(1)
    tail_after_sheetdata = sheet2_xml[m.end():]
    before_sheetdata = sheet2_xml[:m.start()]

    new_strings = []
    m2 = re.search(r'<sst[^>]*count="(\d+)"[^>]*uniqueCount="(\d+)"', shared_xml)
    count, unique_count = int(m2.group(1)), int(m2.group(2))

    def sidx(text):
        new_strings.append(text)
        return unique_count + len(new_strings) - 1

    out_rows = []
    r_i = 3
    for row in rows:
        date_s = row["date_str"]
        i_date = sidx(date_s)
        i_desc = sidx(row.get("description", ""))
        i_member = sidx(row.get("card_member") or "(no name)")
        i_acct = sidx(ACCT_LABEL.get(row.get("account_label"), row.get("account_label", "")))
        i_cat = sidx(row.get("category", ""))
        i_mgr = sidx(row.get("manager") or "UNMAPPED")
        amount = row["amount"]
        month, year = int(row["month"]), int(row["year"])

        out_rows.append(
            f'<row r="{r_i}">'
            f'<c r="A{r_i}" s="7" t="s"><v>{i_date}</v></c>'
            f'<c r="B{r_i}" s="7"/>'
            f'<c r="C{r_i}" s="7" t="s"><v>{i_desc}</v></c>'
            f'<c r="D{r_i}" s="7" t="s"><v>{i_member}</v></c>'
            f'<c r="E{r_i}" s="7" t="s"><v>{i_acct}</v></c>'
            f'<c r="F{r_i}" s="8"><v>{amount}</v></c>'
            f'<c r="G{r_i}" s="9"/><c r="H{r_i}" s="9"/><c r="I{r_i}" s="9"/>'
            f'<c r="J{r_i}" s="9"/><c r="K{r_i}" s="9"/><c r="L{r_i}" s="9"/><c r="M{r_i}" s="9"/>'
            f'<c r="N{r_i}" s="7" t="s"><v>{i_cat}</v></c>'
            f'<c r="O{r_i}" s="10"><v>{month}</v></c>'
            f'<c r="P{r_i}" s="10"><v>{year}</v></c>'
            f'<c r="Q{r_i}" s="7" t="s"><v>{i_mgr}</v></c>'
            f'</row>'
        )
        r_i += 1

    last_row = r_i - 1
    new_sheet2 = before_sheetdata + head + "".join(out_rows) + "</sheetData>" + tail_after_sheetdata

    new_si = "".join(f"<si><t>{escape(s)}</t></si>" for s in new_strings)
    new_shared = shared_xml.replace("</sst>", new_si + "</sst>")
    new_shared = re.sub(
        r'(<sst[^>]*count=")(\d+)("[^>]*uniqueCount=")(\d+)(")',
        lambda mm: f'{mm.group(1)}{count + len(new_strings)}{mm.group(3)}{unique_count + len(new_strings)}{mm.group(5)}',
        new_shared, count=1,
    )
    return new_sheet2, new_shared, last_row


def build_workbook(rows, template_path, out_path):
    """rows: list of dicts with date_str, description, card_member,
    account_label, amount, category, month, year, manager.
    Returns (out_path, row_count, last_row)."""
    with zipfile.ZipFile(template_path) as z:
        names = z.namelist()
        contents = {n: z.read(n) for n in names}

    sheet2_xml = contents["xl/worksheets/sheet2.xml"].decode("utf-8")
    shared_xml = contents["xl/sharedStrings.xml"].decode("utf-8")
    pivot_xml = contents["xl/pivotCache/pivotCacheDefinition1.xml"].decode("utf-8")

    new_sheet2, new_shared, last_row = _rows_to_sheet2_xml(rows, sheet2_xml, shared_xml)
    new_pivot = re.sub(r'worksheetSource ref="A2:Q\d+"', f'worksheetSource ref="A2:Q{last_row}"', pivot_xml)

    contents["xl/worksheets/sheet2.xml"] = new_sheet2.encode("utf-8")
    contents["xl/sharedStrings.xml"] = new_shared.encode("utf-8")
    contents["xl/pivotCache/pivotCacheDefinition1.xml"] = new_pivot.encode("utf-8")

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, contents[n])
    return out_path, len(rows), last_row


def validate_workbook(path):
    """Zip integrity + XML well-formedness check. Does NOT verify the pivot
    actually recalculates in a real spreadsheet engine - see module docstring."""
    from xml.dom import minidom
    z = zipfile.ZipFile(path)
    bad = z.testzip()
    if bad:
        raise RuntimeError(f"corrupt zip member: {bad}")
    for name in ("xl/worksheets/sheet2.xml", "xl/sharedStrings.xml",
                 "xl/pivotCache/pivotCacheDefinition1.xml"):
        minidom.parseString(z.read(name))
    return True
