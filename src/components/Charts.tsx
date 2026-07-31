import metrics from "../data/dashboardMetrics.json";
import { SERIES } from "../lib/chartTokens";
import { MONTHLY, type Period } from "../lib/derive";

const S = SERIES.light;
const fmtM = (v: number) => (Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : `${Math.round(v / 1000)}k`);
const fmtPct = (v: number | null) => (v == null ? "—" : `${v.toFixed(1)}%`);

/** Shared legend. Present whenever a chart draws two or more series. */
function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="legend">
      {items.map((i) => (
        <span key={i.label} className="legend-item">
          <span className="legend-swatch" style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

/** Revenue and EBITDA by month — grouped bars, one axis, direct value labels. */
export function RevenueEbitdaByMonth({ period }: { period: Period }) {
  const active = new Set(period.months.map((mi) => MONTHLY[mi].month));
  const rows = metrics.revenueByMonth;
  const max = Math.max(...rows.map((r) => Math.max(r.revenue, r.ebitda)));
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Revenue and EBITDA by month</h2>
          <p className="hint">
            QuickBooks P&amp;L through {metrics.meta.closedThrough}. Months in the selected period
            are highlighted.
          </p>
        </div>
      </div>
      <Legend items={[{ label: "Revenue", color: S[0] }, { label: "EBITDA", color: S[1] }]} />
      <div className="chart-scroll">
        <div className="bars-grouped" role="img" aria-label="Revenue and EBITDA by month">
          {rows.map((r) => (
            <div key={r.month} className={active.has(r.month) ? "bar-group" : "bar-group dimmed"}>
              <div className="bar-pair">
                <div className="bar-col">
                  <span className="bar-label">{fmtM(r.revenue)}</span>
                  <div className="bar" style={{ height: `${(r.revenue / max) * 150}px`, background: S[0] }} />
                </div>
                <div className="bar-col">
                  <span className="bar-label">{fmtM(r.ebitda)}</span>
                  <div className="bar" style={{ height: `${(r.ebitda / max) * 150}px`, background: S[1] }} />
                </div>
              </div>
              <span className="bar-tick">{r.month}</span>
            </div>
          ))}
        </div>
      </div>
      <details className="table-view">
        <summary>Table view</summary>
        <table>
          <thead><tr><th className="label-col">Month</th><th>Revenue</th><th>EBITDA</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.month}>
                <td className="label-col">{r.month}</td>
                <td>{r.revenue.toLocaleString()}</td>
                <td>{r.ebitda.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

/** Year-over-year revenue growth by month. Single series → no legend box. */
export function YoyGrowth({ period }: { period: Period }) {
  const active = new Set(period.months.map((mi) => MONTHLY[mi].month));
  const rows = metrics.yoyGrowth;
  const max = Math.max(...rows.map((r) => r.growthPct ?? 0));
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Revenue growth year over year</h2>
          <p className="hint">FY26 closed months against the same month of FY25. QuickBooks P&amp;L.</p>
        </div>
      </div>
      <div className="yoy-rows">
        {rows.map((r) => (
          <div key={r.month} className={active.has(r.month) ? "yoy-row" : "yoy-row dimmed"}>
            <span className="yoy-month">{r.month}</span>
            <div className="yoy-track">
              <div className="yoy-bar" style={{ width: `${((r.growthPct ?? 0) / max) * 100}%`, background: S[0] }} />
            </div>
            <span className="yoy-val">{fmtPct(r.growthPct)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Revenue by quarter, FY25 against FY26. */
export function RevenueByQuarter() {
  const rows = metrics.revenueByQuarter;
  const max = Math.max(...rows.flatMap((r) => [r.fy25 ?? 0, r.fy26]));
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Revenue by quarter</h2>
          <p className="hint">FY25 against FY26. Only quarters with closed months are shown.</p>
        </div>
      </div>
      <Legend items={[{ label: "FY25", color: S[2] }, { label: "FY26", color: S[0] }]} />
      <div className="bars-grouped">
        {rows.map((r) => (
          <div key={r.quarter} className="bar-group">
            <div className="bar-pair">
              <div className="bar-col">
                <span className="bar-label">{r.fy25 == null ? "—" : fmtM(r.fy25)}</span>
                <div className="bar" style={{ height: `${((r.fy25 ?? 0) / max) * 150}px`, background: S[2] }} />
              </div>
              <div className="bar-col">
                <span className="bar-label">{fmtM(r.fy26)}</span>
                <div className="bar" style={{ height: `${(r.fy26 / max) * 150}px`, background: S[0] }} />
              </div>
            </div>
            <span className="bar-tick">{r.quarter}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Expense base by quarter — stacked COGS / S&M / G&A with 2px gaps between segments. */
export function ExpenseBase() {
  const rows = metrics.expenseBase;
  const max = Math.max(...rows.map((r) => r.cogs + r.sm + r.ga));
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Expense base by quarter</h2>
          <p className="hint">Cost of goods sold, sales &amp; marketing, and general &amp; administrative. QuickBooks P&amp;L.</p>
        </div>
      </div>
      <Legend
        items={[
          { label: "COGS", color: S[0] },
          { label: "Sales & marketing", color: S[1] },
          { label: "G&A", color: S[2] },
        ]}
      />
      <div className="chart-scroll">
        <div className="bars-stacked">
          {rows.map((r) => {
            const total = r.cogs + r.sm + r.ga;
            return (
              <div key={r.label} className="bar-group">
                <span className="bar-label">{fmtM(total)}</span>
                <div className="stack" style={{ height: `${(total / max) * 170}px` }}>
                  <div className="seg" style={{ flexGrow: r.ga, background: S[2] }} />
                  <div className="seg" style={{ flexGrow: r.sm, background: S[1] }} />
                  <div className="seg" style={{ flexGrow: r.cogs, background: S[0] }} />
                </div>
                <span className="bar-tick">{r.label}</span>
              </div>
            );
          })}
        </div>
      </div>
      <details className="table-view">
        <summary>Table view</summary>
        <table>
          <thead><tr><th className="label-col">Quarter</th><th>COGS</th><th>S&amp;M</th><th>G&amp;A</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <td className="label-col">{r.label}</td>
                <td>{r.cogs.toLocaleString()}</td>
                <td>{r.sm.toLocaleString()}</td>
                <td>{r.ga.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
