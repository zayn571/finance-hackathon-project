import { useState } from "react";
import { ACTUALS_ANALYSIS_SCHEMA, type SchemaRow } from "../data/gaapAnalysisSchema";
import actuals from "../data/incomeStatementActuals.json";
import { getByPath, formatDollars, formatPercent } from "../lib/period";

const data = actuals as Record<string, unknown>;

interface PeriodCol {
  key: string;
  label: string;
  basis: "actual" | "projected";
}

const PERIODS: PeriodCol[] = [
  { key: "Q1", label: "Q1 FY26", basis: "actual" },
  { key: "Q2", label: "Q2 FY26", basis: "actual" },
  { key: "Q3", label: "Q3 FY26", basis: "projected" },
  { key: "Q4", label: "Q4 FY26", basis: "projected" },
];

const ANALYSIS_IDX = ACTUALS_ANALYSIS_SCHEMA.findIndex((r) => r.key === "band-analysis");

function rowValue(row: SchemaRow, period: PeriodCol): number | null {
  if (!row.dataKey) return null;
  return getByPath(data[period.key], row.dataKey);
}

function cellText(row: SchemaRow, period: PeriodCol): string {
  const v = rowValue(row, period);
  return row.isPercent ? formatPercent(v) : formatDollars(v);
}

function quoteCsv(v: string): string {
  return `"${v.replace(/"/g, '""')}"`;
}

function downloadCsv() {
  const lines: string[] = [
    ["Line item", ...PERIODS.map((p) => p.label)].map(quoteCsv).join(","),
  ];
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
    const cells = PERIODS.map((p) => {
      const v = rowValue(row, p);
      if (v == null) return "";
      return row.isPercent ? (Math.round(v * 10) / 10).toString() : Math.round(v).toString();
    });
    lines.push([quoteCsv(label), ...cells.map(quoteCsv)].join(","));
  }
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "RapDev Income Statement FY26.csv";
  a.click();
  URL.revokeObjectURL(url);
}

const rowClass = (row: SchemaRow) => {
  if (row.kind === "band") return "is-row is-band";
  if (row.kind === "total") return "is-row is-total";
  if (row.kind === "subtotal") return "is-row is-subtotal";
  if (row.kind === "spacer") return "is-row is-spacer";
  return "is-row";
};

export default function IncomeStatement() {
  const [sections, setSections] = useState({ Actuals: true, Analysis: true });

  const visibleRows = ACTUALS_ANALYSIS_SCHEMA.filter((row) => {
    if (row.key === "band-actuals" || row.key === "band-analysis") return true;
    const inAnalysis = ACTUALS_ANALYSIS_SCHEMA.indexOf(row) > ANALYSIS_IDX;
    return inAnalysis ? sections.Analysis : sections.Actuals;
  });

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Income statement</h2>
          <p className="hint">
            Structure mirrors the GAAP Analysis tab through the Analysis section. Revenue, COGS
            and operating expenses come from the QuickBooks P&amp;L by class; bookings from
            closed-won HubSpot deals; utilization and hours from ServiceNow time cards; headcount
            from the BambooHR department listing. Q3 and Q4 are projected off Q2 — not closed
            actuals.
          </p>
        </div>
        <button className="btn btn-primary" onClick={downloadCsv}>
          Download CSV
        </button>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th className="label-col">Line item</th>
              {PERIODS.map((p) => (
                <th key={p.key}>
                  {p.label}
                  {p.basis === "projected" && <span className="badge badge-tint">proj</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              if (row.kind === "spacer") {
                return (
                  <tr key={row.key} className={rowClass(row)}>
                    <td colSpan={PERIODS.length + 1} />
                  </tr>
                );
              }
              if (row.kind === "band") {
                const sectionKey = row.label === "ACTUALS" ? "Actuals" : "Analysis";
                return (
                  <tr key={row.key} className={rowClass(row)}>
                    <td
                      colSpan={PERIODS.length + 1}
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
                  {PERIODS.map((p) => (
                    <td key={p.key} className={p.basis === "projected" ? "projected" : ""}>
                      {cellText(row, p)}
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
