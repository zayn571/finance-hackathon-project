import metrics from "../data/dashboardMetrics.json";
import { SERIES } from "../lib/chartTokens";
import ExcelJS from "exceljs";
import { downloadBlob } from "../lib/exportXlsx";

const S = SERIES.light;
const ar = metrics.ar;
const fmt = (v: number) => Math.round(v).toLocaleString();

/**
 * A/R aging straight from the QuickBooks Aged Receivables report. Buckets are
 * QBO's own (Current / 1-30 / 31-60 / 61-90 / 91+) — not re-bucketed here.
 */
export default function ArAging() {
  const max = Math.max(...ar.buckets.map((b) => b.amount));
  const overdue = ar.buckets.slice(1).reduce((a, b) => a + b.amount, 0);

  function downloadCsv() {
    const lines = [
      ['"Customer"', '"Current"', '"1-30"', '"31-60"', '"61-90"', '"91 and over"', '"Total"'].join(","),
      ...ar.topCustomers.map((c) =>
        [`"${c.name.replace(/"/g, '""')}"`, c.current, c.d1_30, c.d31_60, c.d61_90, c.d91_plus, c.total].join(",")
      ),
    ];
    const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    downloadBlob(blob, "RapDev AR Aging.csv");
  }

  /**
   * Formatted A/R aging workbook. Number format and geometry follow the same
   * conventions as the Mgmt Reporting workbook: accounting format with negatives
   * in parentheses, Calibri 8 body, header row bold with a medium bottom rule,
   * bold total row, frozen header and label column.
   */
  async function downloadXlsx() {
    const ACCOUNTING = '_("$"* #,##0_);_("$"* \\(#,##0\\);_("$"* "-"??_);_(@_)';
    const wb = new ExcelJS.Workbook();
    wb.creator = "RapDev Finance";
    const ws = wb.addWorksheet("AR Aging", {
      views: [{ state: "frozen", xSplit: 1, ySplit: 4 }],
    });
    ws.getColumn(1).width = 42;
    for (let i = 2; i <= 7; i++) ws.getColumn(i).width = 14.71;

    const title = ws.getCell(1, 1);
    title.value = "RapDev LLC — A/R Aging";
    title.font = { name: "Calibri", size: 12, bold: true };
    const sub = ws.getCell(2, 1);
    sub.value = `QuickBooks Aged Receivables as of ${metrics.meta.arAsOf}. ${ar.customerCount} customers, ${fmt(ar.total)} outstanding.`;
    sub.font = { name: "Calibri", size: 8, color: { argb: "FF6B7A8A" } };

    const heads = ["Customer", "Current", "1-30", "31-60", "61-90", "91 and over", "Total"];
    const hr = ws.getRow(4);
    heads.forEach((h, i) => {
      const cell = hr.getCell(i + 1);
      cell.value = h;
      cell.font = { name: "Calibri", size: 8, bold: true };
      cell.alignment = { horizontal: i === 0 ? "left" : "right" };
      cell.border = { bottom: { style: "medium", color: { argb: "FF000000" } } };
    });

    ar.topCustomers.forEach((cust, idx) => {
      const row = ws.getRow(5 + idx);
      const cells: (string | number)[] = [
        cust.name, cust.current, cust.d1_30, cust.d31_60, cust.d61_90, cust.d91_plus, cust.total,
      ];
      cells.forEach((v, i) => {
        const cell = row.getCell(i + 1);
        cell.value = v;
        cell.font = { name: "Calibri", size: 8, bold: i === 6 };
        cell.alignment = { horizontal: i === 0 ? "left" : "right" };
        if (i > 0) cell.numFmt = ACCOUNTING;
        // zebra banding, matching the reference workbook's F3F3F3
        if (idx % 2 === 1) {
          cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFF3F3F3" } };
        }
      });
    });

    // Total row, bold with a rule above, summing only the rows written.
    const totalRow = ws.getRow(5 + ar.topCustomers.length);
    const sums = ar.topCustomers.reduce(
      (a, c) => [
        a[0] + c.current, a[1] + c.d1_30, a[2] + c.d31_60, a[3] + c.d61_90, a[4] + c.d91_plus, a[5] + c.total,
      ],
      [0, 0, 0, 0, 0, 0]
    );
    ["Total (largest balances shown)", ...sums].forEach((v, i) => {
      const cell = totalRow.getCell(i + 1);
      cell.value = v as string | number;
      cell.font = { name: "Calibri", size: 8, bold: true };
      cell.alignment = { horizontal: i === 0 ? "left" : "right" };
      if (i > 0) cell.numFmt = ACCOUNTING;
      cell.border = { top: { style: "thin", color: { argb: "FF000000" } } };
    });

    const buf = await wb.xlsx.writeBuffer();
    downloadBlob(
      new Blob([buf], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      }),
      "RapDev AR Aging.xlsx"
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>A/R aging</h2>
          <p className="hint">
            QuickBooks Aged Receivables as of {metrics.meta.arAsOf}. {ar.customerCount} customers,{" "}
            {fmt(ar.total)} outstanding, of which {fmt(overdue)} is past due.
          </p>
        </div>
        <div className="btn-row">
          <button className="btn btn-primary" onClick={downloadXlsx}>Download Excel</button>
          <button className="btn btn-secondary" onClick={downloadCsv}>Download CSV</button>
        </div>
      </div>

      <div className="ar-buckets">
        {ar.buckets.map((b, i) => (
          <div key={b.label} className="bar-group">
            <span className="bar-label">{fmt(b.amount)}</span>
            <div
              className="bar"
              style={{ height: `${(b.amount / max) * 140}px`, background: i === 0 ? S[0] : i >= 3 ? S[2] : S[1] }}
            />
            <span className="bar-tick">{b.label}</span>
          </div>
        ))}
      </div>
      <div className="legend">
        <span className="legend-item"><span className="legend-swatch" style={{ background: S[0] }} />Current</span>
        <span className="legend-item"><span className="legend-swatch" style={{ background: S[1] }} />1–60 days</span>
        <span className="legend-item"><span className="legend-swatch" style={{ background: S[2] }} />Over 60 days</span>
      </div>

      <h3 className="sub-head">Largest balances</h3>
      <div className="table-scroll short">
        <table>
          <thead>
            <tr>
              <th className="label-col">Customer</th>
              <th>Current</th><th>1–30</th><th>31–60</th><th>61–90</th><th>91+</th><th>Total</th>
            </tr>
          </thead>
          <tbody>
            {ar.topCustomers.map((c) => (
              <tr key={c.name} className="is-row">
                <td className="label-col">{c.name}</td>
                <td>{fmt(c.current)}</td>
                <td>{fmt(c.d1_30)}</td>
                <td>{fmt(c.d31_60)}</td>
                <td>{fmt(c.d61_90)}</td>
                <td>{fmt(c.d91_plus)}</td>
                <td className="strong">{fmt(c.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
