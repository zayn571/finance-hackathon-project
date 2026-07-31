import ExcelJS from "exceljs";
import { ACTUALS_ANALYSIS_SCHEMA, type SchemaRow } from "../data/gaapAnalysisSchema";
import refStyles from "../data/refStyles.json";

/**
 * Writes a real .xlsx that matches the "Mgmt Reporting" GAAP Analysis tab.
 *
 * The styling is not hand-authored: `refStyles.json` was extracted directly from
 * that tab (per-row bold / fill / font colour / size / number format / indent,
 * keyed by our schema row key, each carrying the reference row it came from), so
 * a cell here wears the same format its counterpart wears in the workbook.
 *
 * Reference-derived sheet geometry: freeze at C5, column A 6.86, column B 27.29,
 * data columns 14.71, body font Calibri 8 (section bands 10).
 */

interface RefStyle {
  bold: boolean;
  fill: string | null;
  fontColor: string | null;
  size: number | null;
  numFmt: string | null;
  indent: number;
  refRow?: number;
}

const STYLES = refStyles as Record<string, RefStyle>;

const COL_A_WIDTH = 6.86;
const COL_B_WIDTH = 27.29;
const DATA_COL_WIDTH = 14.71;
const DEFAULT_FONT = "Calibri";

export interface XlsxPeriod {
  key: string;
  label: string;
  /** Appended to the header cell, e.g. "(projected)". */
  note?: string;
}

export interface XlsxOptions {
  sheetName: string;
  periods: XlsxPeriod[];
  /** Returns the numeric value for a row/period, or null to leave the cell empty. */
  value: (row: SchemaRow, periodKey: string) => number | null;
  /** Per-row note placed in the trailing Source column. */
  note?: (row: SchemaRow) => string;
  /** Title placed above the table. */
  title: string;
  subtitle?: string;
}

function applyRowStyle(cell: ExcelJS.Cell, s: RefStyle | undefined, isLabel: boolean) {
  const size = s?.size ?? 8;
  cell.font = {
    name: DEFAULT_FONT,
    size,
    bold: s?.bold ?? false,
    color: { argb: s?.fontColor ?? "FF000000" },
  };
  if (s?.fill) {
    cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: s.fill } };
  }
  if (isLabel) {
    cell.alignment = { indent: s?.indent ?? 0, vertical: "middle" };
  } else {
    cell.alignment = { horizontal: "right", vertical: "middle" };
    if (s?.numFmt) cell.numFmt = s.numFmt;
  }
}

export async function buildIncomeStatementXlsx(opts: XlsxOptions): Promise<Blob> {
  const wb = new ExcelJS.Workbook();
  wb.creator = "RapDev Finance";
  wb.created = new Date();
  const ws = wb.addWorksheet(opts.sheetName, {
    views: [{ state: "frozen", xSplit: 2, ySplit: 4 }],
  });

  const dataColCount = opts.periods.length;
  // The trailing note column only exists when the caller supplies notes.
  const hasNotes = typeof opts.note === "function";
  ws.getColumn(1).width = COL_A_WIDTH;
  ws.getColumn(2).width = COL_B_WIDTH;
  for (let i = 0; i < dataColCount; i++) ws.getColumn(3 + i).width = DATA_COL_WIDTH;
  if (hasNotes) ws.getColumn(3 + dataColCount).width = 30;

  // Rows 1-4 are the reference's header band; row 4 carries the period labels so
  // the freeze at C5 lands exactly where it does in the workbook.
  const titleCell = ws.getCell(1, 2);
  titleCell.value = opts.title;
  titleCell.font = { name: DEFAULT_FONT, size: 12, bold: true };
  if (opts.subtitle) {
    const sub = ws.getCell(2, 2);
    sub.value = opts.subtitle;
    sub.font = { name: DEFAULT_FONT, size: 8, italic: false, color: { argb: "FF6B7A8A" } };
  }

  const headerRow = ws.getRow(4);
  opts.periods.forEach((p, i) => {
    const c = headerRow.getCell(3 + i);
    c.value = p.note ? `${p.label} ${p.note}` : p.label;
    c.font = { name: DEFAULT_FONT, size: 8, bold: true };
    c.alignment = { horizontal: "right" };
    c.border = { bottom: { style: "medium", color: { argb: "FF000000" } } };
  });
  if (hasNotes) {
    const srcHeader = headerRow.getCell(3 + dataColCount);
    srcHeader.value = "Source";
    srcHeader.font = { name: DEFAULT_FONT, size: 8, bold: true };
    srcHeader.border = { bottom: { style: "medium", color: { argb: "FF000000" } } };
  }

  let r = 5;
  for (const row of ACTUALS_ANALYSIS_SCHEMA) {
    const s = STYLES[row.key];

    if (row.kind === "spacer") {
      ws.getRow(r).height = 4;
      r++;
      continue;
    }

    const excelRow = ws.getRow(r);

    if (row.kind === "band") {
      // Band spans the full width, matching the reference's dark section header.
      const label = excelRow.getCell(2);
      label.value = row.label;
      applyRowStyle(label, s, true);
      for (let i = 0; i < dataColCount + (hasNotes ? 1 : 0); i++) {
        const c = excelRow.getCell(3 + i);
        applyRowStyle(c, s, false);
      }
      r++;
      continue;
    }

    const label = excelRow.getCell(2);
    label.value = row.label;
    applyRowStyle(label, s, true);

    opts.periods.forEach((p, i) => {
      const c = excelRow.getCell(3 + i);
      const v = opts.value(row, p.key);
      // Percentages are stored as a fraction so Excel's own % format renders them.
      if (v != null) c.value = row.isPercent ? v / 100 : v;
      applyRowStyle(c, s, false);
    });

    if (hasNotes) {
      const noteCell = excelRow.getCell(3 + dataColCount);
      noteCell.value = opts.note!(row);
      noteCell.font = { name: DEFAULT_FONT, size: 8, color: { argb: "FF6B7A8A" } };
      noteCell.alignment = { horizontal: "left" };
    }

    r++;
  }

  const buf = await wb.xlsx.writeBuffer();
  return new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
