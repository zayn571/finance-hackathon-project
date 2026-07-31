import ExcelJS from "exceljs";
import departmentListing from "../data/departmentListing.json";
import { downloadBlob } from "./exportXlsx";

/**
 * Writes the BambooHR department listing in the exact format of
 * REFERENCE_RapDev_Department_Listing().xlsx, sheet "Department Listing".
 *
 * Everything here was read out of that file's XML rather than guessed:
 *  - 19 columns A–S, widths 12.63 / 11.75 (B–C) / 17.88 / 10.38 / 11.25 / 14.25 /
 *    14.88 / 12.13 / 15.63 / 10.63 / 32.38 / 11.88 / 11.13 / 9.13 / 29.88 / 32.25 /
 *    28.38 / 45.38
 *  - header row height 30, Arial 10 bold white on solid FF666666, centred + middle +
 *    wrapText, thin black border on all four sides
 *  - frozen header (pane ySplit 1)
 *  - Employee # as an integer (numFmt "0"), Hire Date and Employment Status: Date as
 *    date serials with numFmt mm/dd/yyyy, every other cell text, Arial 10, left/middle
 */

const WIDTHS = [12.63, 11.75, 11.75, 17.88, 10.38, 11.25, 14.25, 14.88, 12.13, 15.63,
  10.63, 32.38, 11.88, 11.13, 9.13, 29.88, 32.25, 28.38, 45.38];
const DATE_COLS = [5, 7]; // zero-based: Hire Date, Employment Status: Date
const THIN = { style: "thin" as const, color: { argb: "FF000000" } };

interface Roster {
  header: string[];
  rows: (string | number)[][];
}

export async function buildDeptListingXlsx(roster: Roster = departmentListing as Roster): Promise<Blob> {
  const wb = new ExcelJS.Workbook();
  wb.creator = "RapDev Finance";
  wb.created = new Date();
  const ws = wb.addWorksheet("Department Listing", { views: [{ state: "frozen", ySplit: 1 }] });

  WIDTHS.forEach((w, i) => { ws.getColumn(i + 1).width = w; });

  const head = ws.getRow(1);
  head.height = 30;
  roster.header.forEach((label, i) => {
    const c = head.getCell(i + 1);
    c.value = label;
    c.font = { name: "Arial", size: 10, bold: true, color: { argb: "FFFFFFFF" } };
    c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF666666" } };
    c.alignment = { horizontal: "center", vertical: "middle", wrapText: true };
    c.border = { top: THIN, left: THIN, bottom: THIN, right: THIN };
  });

  roster.rows.forEach((row, ri) => {
    const r = ws.getRow(ri + 2);
    row.forEach((v, i) => {
      const c = r.getCell(i + 1);
      if (i === 0) {
        if (v !== "") c.value = Number(v);
        c.numFmt = "0";
      } else if (DATE_COLS.includes(i)) {
        if (v !== "") c.value = Number(v);
        c.numFmt = "mm/dd/yyyy";
      } else if (v !== "") {
        c.value = v;
      }
      c.font = { name: "Arial", size: 10, color: { argb: "FF000000" } };
      c.alignment = { horizontal: "left", vertical: "middle" };
    });
  });

  const buf = await wb.xlsx.writeBuffer();
  return new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

/** Convenience wrapper: build the workbook and hand it to the browser. */
export async function downloadDeptListingXlsx(filename = "RapDev Department Listing.xlsx") {
  const blob = await buildDeptListingXlsx();
  downloadBlob(blob, filename);
}
