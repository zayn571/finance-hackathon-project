import { useState } from "react";
import { ACTUALS_ANALYSIS_SCHEMA, type SchemaRow } from "../data/gaapAnalysisSchema";
import actuals from "../data/incomeStatementActuals.json";
import { getByPath, formatDollars, formatPercent } from "../lib/period";
import {
  PROVENANCE,
  PROVENANCE_LABEL,
  PROVENANCE_TITLE,
  SUPPRESSED,
  VERIFIED_REFERENCE,
  type Provenance,
} from "../data/provenance";

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
  // A value that contradicts a verified source is withheld, not shown with a caveat.
  if (SUPPRESSED.has(row.key)) return null;
  return getByPath(data[period.key], row.dataKey);
}

function cellText(row: SchemaRow, period: PeriodCol): string {
  if (SUPPRESSED.has(row.key)) return "withheld";
  const v = rowValue(row, period);
  return row.isPercent ? formatPercent(v) : formatDollars(v);
}

function quoteCsv(v: string): string {
  return `"${v.replace(/"/g, '""')}"`;
}

function downloadCsv() {
  // The export carries the same provenance column the table shows, so a figure
  // pasted out of this file can still be traced back to its source.
  const lines: string[] = [
    ["Line item", ...PERIODS.map((p) => p.label), "Source"].map(quoteCsv).join(","),
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
    const prov = PROVENANCE[row.key];
    const note = SUPPRESSED.has(row.key)
      ? `Withheld — contradicts verified source${VERIFIED_REFERENCE[row.key] ? `; verified: ${VERIFIED_REFERENCE[row.key]}` : ""}`
      : prov
        ? PROVENANCE_LABEL[prov]
        : "";
    lines.push([quoteCsv(label), ...cells.map(quoteCsv), quoteCsv(note)].join(","));
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
            and operating expenses tie to the QuickBooks P&amp;L by class. Q3 and Q4 are Q2 scaled
            by a growth rate — not closed actuals, and every ratio in them is inherited from Q2.
          </p>
          <p className="hint warn">
            Not every row is a QuickBooks figure. Hover any marker to see where that number comes
            from. Rows marked <strong>unverified</strong> have no traceable source — bookings,
            project hours and bill rate among them, and the utilization and rate figures here
            disagree with the delivered Synechron workbook (Jun 2026: 72.35% utilization, 317.91
            blended rate). Treat those as placeholders, not actuals.
          </p>
        </div>
        <button className="btn btn-primary" onClick={downloadCsv}>
          Download CSV
        </button>
      </div>

      <div className="prov-legend">
        {(["qbo", "allocated", "mapped", "unverified"] as Provenance[]).map((p) => (
          <span key={p} className="prov-legend-item" title={PROVENANCE_TITLE[p]}>
            <span className={`prov-dot prov-${p}`} aria-hidden="true" />
            {PROVENANCE_LABEL[p]}
          </span>
        ))}
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
              const prov = PROVENANCE[row.key];
              return (
                <tr key={row.key} className={rowClass(row)}>
                  <td className="label-col" style={{ paddingLeft: 12 + row.indent * 16 }}>
                    {row.label}
                    {VERIFIED_REFERENCE[row.key] && (
                      <span className="verified-ref">verified: {VERIFIED_REFERENCE[row.key]}</span>
                    )}
                    {prov && prov !== "qbo" && (
                      <span
                        className={`prov-dot prov-${prov}`}
                        title={`${PROVENANCE_LABEL[prov]} — ${PROVENANCE_TITLE[prov]}`}
                      >
                        <span className="sr-only">{PROVENANCE_LABEL[prov]}</span>
                      </span>
                    )}
                  </td>
                  {PERIODS.map((p) => (
                    <td
                      key={p.key}
                      className={[
                        p.basis === "projected" ? "projected" : "",
                        prov === "unverified" ? "unverified" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
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
