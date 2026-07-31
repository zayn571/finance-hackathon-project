import { useMemo, useState } from "react";
import { ACTUALS_ANALYSIS_SCHEMA, type SchemaRow } from "../data/gaapAnalysisSchema";
import { getByPath, formatDollars, formatPercent } from "../lib/period";
import { derive, MONTHLY, type Period } from "../lib/derive";
import { buildIncomeStatementXlsx, downloadBlob } from "../lib/exportXlsx";

/**
 * Columns shown for the selected period. Picking the fiscal year shows the two
 * closed quarters plus a year column; picking a quarter breaks it into its
 * months plus a quarter total; picking a month shows that month alone.
 */
function columnsFor(period: Period): { key: string; label: string; months: number[]; emphasis?: boolean }[] {
  if (period.key === "FY26") {
    return [
      { key: "Q1", label: "Q1", months: [0, 1, 2] },
      { key: "Q2", label: "Q2", months: [3, 4, 5] },
      { key: "FY26", label: "FY26", months: [0, 1, 2, 3, 4, 5], emphasis: true },
    ];
  }
  if (period.key === "Q1" || period.key === "Q2") {
    const cols = period.months.map((mi) => ({
      key: MONTHLY[mi].month,
      label: MONTHLY[mi].month,
      months: [mi],
    }));
    return [...cols, { key: period.key, label: period.key, months: period.months, emphasis: true }];
  }
  return [{ key: period.key, label: period.label.replace(" FY26", ""), months: period.months, emphasis: true }];
}

const rowClass = (row: SchemaRow) => {
  if (row.kind === "band") return "is-row is-band";
  if (row.kind === "total") return "is-row is-total";
  if (row.kind === "subtotal") return "is-row is-subtotal";
  if (row.kind === "spacer") return "is-row is-spacer";
  return "is-row";
};

function quoteCsv(v: string): string {
  return `"${v.replace(/"/g, '""')}"`;
}

export default function IncomeStatement({ period }: { period: Period }) {
  const [sections, setSections] = useState({ Actuals: true, Analysis: true });

  const columns = useMemo(() => columnsFor(period), [period]);
  const derived = useMemo(
    () => Object.fromEntries(columns.map((c) => [c.key, derive(c.months)])),
    [columns]
  );

  const analysisIdx = ACTUALS_ANALYSIS_SCHEMA.findIndex((r) => r.key === "band-analysis");
  const visibleRows = ACTUALS_ANALYSIS_SCHEMA.filter((row) => {
    if (row.key === "band-actuals" || row.key === "band-analysis") return true;
    const inAnalysis = ACTUALS_ANALYSIS_SCHEMA.indexOf(row) > analysisIdx;
    return inAnalysis ? sections.Analysis : sections.Actuals;
  });

  const value = (row: SchemaRow, colKey: string): number | null =>
    row.dataKey ? getByPath(derived[colKey], row.dataKey) : null;

  const cellText = (row: SchemaRow, colKey: string) => {
    const v = value(row, colKey);
    return row.isPercent ? formatPercent(v) : formatDollars(v);
  };

  function downloadCsv() {
    const lines: string[] = [["Line item", ...columns.map((c) => c.label)].map(quoteCsv).join(",")];
    for (const row of ACTUALS_ANALYSIS_SCHEMA) {
      if (row.kind === "spacer") {
        lines.push("");
        continue;
      }
      if (row.kind === "band") {
        lines.push(quoteCsv(row.label.toUpperCase()));
        continue;
      }
      const label = "  ".repeat(row.indent) + row.label;
      const cells = columns.map((c) => {
        const v = value(row, c.key);
        if (v == null) return "";
        return row.isPercent ? (Math.round(v * 10) / 10).toString() : Math.round(v).toString();
      });
      lines.push([quoteCsv(label), ...cells.map(quoteCsv)].join(","));
    }
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    downloadBlob(blob, `RapDev Income Statement ${period.key}.csv`);
  }

  async function downloadXlsx() {
    const blob = await buildIncomeStatementXlsx({
      sheetName: "GAAP Analysis",
      title: `RapDev LLC — Income Statement ${period.label}`,
      subtitle:
        "Structure and formatting follow the Mgmt Reporting GAAP Analysis tab. Sourced from QuickBooks Online.",
      periods: columns.map((c) => ({ key: c.key, label: c.label })),
      value: (row, colKey) => value(row, colKey),
    });
    downloadBlob(blob, `RapDev Income Statement ${period.key}.xlsx`);
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Income statement</h2>
          <p className="hint">
            {period.label} · structure follows the Mgmt Reporting GAAP Analysis tab. Sourced from
            QuickBooks Online. Click a section band to collapse it.
          </p>
        </div>
        <div className="btn-row">
          <button className="btn btn-primary" onClick={downloadXlsx}>
            Download Excel
          </button>
          <button className="btn btn-secondary" onClick={downloadCsv}>
            Download CSV
          </button>
        </div>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th className="label-col">Line item</th>
              {columns.map((c) => (
                <th key={c.key} className={c.emphasis ? "col-emphasis" : ""}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              if (row.kind === "spacer") {
                return (
                  <tr key={row.key} className={rowClass(row)}>
                    <td colSpan={columns.length + 1} />
                  </tr>
                );
              }
              if (row.kind === "band") {
                const sectionKey = row.label === "ACTUALS" ? "Actuals" : "Analysis";
                return (
                  <tr key={row.key} className={rowClass(row)}>
                    <td
                      colSpan={columns.length + 1}
                      onClick={() =>
                        setSections((s) => ({ ...s, [sectionKey]: !s[sectionKey as keyof typeof s] }))
                      }
                    >
                      {row.label}
                    </td>
                  </tr>
                );
              }
              return (
                <tr key={row.key} className={rowClass(row)}>
                  <td className="label-col" style={{ paddingLeft: 12 + row.indent * 16 }}>
                    {row.label}
                  </td>
                  {columns.map((c) => (
                    <td key={c.key} className={c.emphasis ? "col-emphasis" : ""}>
                      {cellText(row, c.key)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
