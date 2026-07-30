import metrics from "../data/dashboardMetrics.json";
import { SERIES } from "../lib/chartTokens";

const S = SERIES.light;

const MONTH_NAMES: Record<string, string> = {
  "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun",
  "07": "Jul", "08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
};

/** Backlog — sold work not yet delivered. From the delivered Synechron HR Template. */
export function Backlog() {
  const rows = metrics.backlog.series;
  const max = Math.max(...rows.map((r) => r.value));
  const latest = rows[rows.length - 1];
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Backlog</h2>
          <p className="hint">
            Sold work not yet delivered, in USD millions. Source: {metrics.backlog.source}.
          </p>
        </div>
        <div className="stat-inline">
          <span className="stat-value">{latest.value.toFixed(2)}M</span>
          <span className="stat-label">as of {latest.month}</span>
        </div>
      </div>
      <div className="bars-grouped">
        {rows.map((r) => (
          <div key={r.month} className="bar-group">
            <span className="bar-label">{r.value.toFixed(2)}</span>
            <div className="bar" style={{ height: `${(r.value / max) * 140}px`, background: S[0] }} />
            <span className="bar-tick">{r.month}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Attrition calculated from BambooHR report 228 including terminated employees:
 * separations in a month over active headcount at that month end. The delivered
 * Synechron quarterly figures are shown alongside as a reconciliation check —
 * they are close but not identical, and the difference is not reconciled here.
 */
export function Attrition() {
  const a = metrics.attrition;
  const rows = a.byMonth;
  const maxSep = Math.max(...rows.map((r) => r.separations), 1);
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Attrition</h2>
          <p className="hint">
            Separations over active headcount, calculated from BambooHR report 228 including
            terminated employees. TTM through {a.asOf}: {a.ttmSeparations} separations on{" "}
            {a.headcountJun} headcount.
          </p>
        </div>
        <div className="stat-inline">
          <span className="stat-value">{a.ttmAttritionPct}%</span>
          <span className="stat-label">TTM</span>
        </div>
      </div>

      <div className="bars-grouped">
        {rows.map((r) => (
          <div key={r.month} className="bar-group">
            <span className="bar-label">
              {r.separations} · {(r.monthlyAttritionPct ?? 0).toFixed(1)}%
            </span>
            <div
              className="bar"
              style={{ height: `${(r.separations / maxSep) * 120}px`, background: S[1], minHeight: 2 }}
            />
            <span className="bar-tick">{MONTH_NAMES[r.month] ?? r.month}</span>
          </div>
        ))}
      </div>
      <p className="footnote">
        Bars show separations per month. Synechron's delivered figures for the same periods read{" "}
        {a.synechron.thisQuarterAttritionPct}% this quarter and {a.synechron.lastQuarterAttritionPct}%
        last quarter; this calculation gives 3.6% and 2.5%. The gap is unreconciled — Synechron's
        definition of the denominator may differ.
      </p>
    </div>
  );
}

/** Share of projects on fixed price rather than time and materials. */
export function FixedCostMix() {
  const rows = metrics.fixedCostMix.series;
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Fixed price vs time &amp; materials</h2>
          <p className="hint">
            Share of projects on fixed price. Source: {metrics.fixedCostMix.source}.
          </p>
        </div>
      </div>
      <div className="table-scroll short">
        <table>
          <thead>
            <tr><th className="label-col">Month</th><th>ServiceNow</th><th>Datadog</th><th>Total</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.month} className="is-row">
                <td className="label-col">{r.month}</td>
                <td>{r.sn}%</td>
                <td>{r.dd}%</td>
                <td className="strong">{r.total}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
