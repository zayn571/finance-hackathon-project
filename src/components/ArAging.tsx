import metrics from "../data/dashboardMetrics.json";
import { SERIES } from "../lib/chartTokens";

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
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "RapDev AR Aging.csv";
    a.click();
    URL.revokeObjectURL(url);
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
        <button className="btn btn-primary" onClick={downloadCsv}>Download CSV</button>
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
