import { useMemo } from "react";
import { derive, PERIODS, type Period } from "../lib/derive";
import { FY25_MONTHLY } from "./KpiStrip";
import { SERIES } from "../lib/chartTokens";

const S = SERIES.light;
const THRESHOLD = 40;

/**
 * Rule of 40 = revenue growth year over year + Adj EBITDA margin, both computed
 * over the selected period against the same calendar months of the prior year.
 */
function score(months: number[]) {
  const d = derive(months);
  const prior = months.reduce((a, mi) => a + (FY25_MONTHLY[mi] ?? 0), 0);
  const growth = prior ? ((d.revenue.total - prior) / prior) * 100 : 0;
  const margin = d.ebitdaPct;
  return { growth, margin, total: growth + margin, revenue: d.revenue.total, prior };
}

export default function RuleOf40({ period }: { period: Period }) {
  const s = useMemo(() => score(period.months), [period]);
  const quarters = useMemo(
    () => PERIODS.filter((p) => p.key === "Q1" || p.key === "Q2").map((p) => ({ label: p.key, ...score(p.months) })),
    []
  );
  const above = s.total >= THRESHOLD;
  const max = Math.max(...quarters.map((q) => q.total), THRESHOLD) * 1.2;

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="eyebrow eyebrow-teal">Rule of 40</div>
          <h2>{period.label}</h2>
          <p className="hint">
            Revenue growth year over year plus Adj. EBITDA margin, against the same months of FY25.
          </p>
        </div>
      </div>

      <div className="r40-grid">
        <div>
          <div className="r40-score">{s.total.toFixed(1)}</div>
          <div className={above ? "r40-verdict pass" : "r40-verdict fail"}>
            {above ? "Above the 40 line" : "Below the 40 line"}
          </div>
          <div className="r40-bar">
            <div className="seg" style={{ flexGrow: Math.max(s.growth, 0), background: S[0] }} />
            <div className="seg" style={{ flexGrow: Math.max(s.margin, 0), background: S[1] }} />
          </div>
          <div className="legend">
            <span className="legend-item">
              <span className="legend-swatch" style={{ background: S[0] }} />
              Growth
            </span>
            <span className="legend-item">
              <span className="legend-swatch" style={{ background: S[1] }} />
              Margin
            </span>
          </div>
          <dl className="r40-rows">
            <div>
              <dt>Revenue growth YoY</dt>
              <dd>{s.growth.toFixed(1)}%</dd>
            </div>
            <div>
              <dt>Adj. EBITDA margin</dt>
              <dd>{s.margin.toFixed(1)}%</dd>
            </div>
            <div>
              <dt>Threshold</dt>
              <dd>{THRESHOLD.toFixed(1)}</dd>
            </div>
          </dl>
        </div>

        <div>
          <div className="r40-chart">
            {quarters.map((q) => (
              <div key={q.label} className="bar-group">
                <span className="bar-label">{q.total.toFixed(1)}</span>
                <div className="stack" style={{ height: `${(q.total / max) * 150}px` }}>
                  <div className="seg" style={{ flexGrow: Math.max(q.margin, 0), background: S[1] }} />
                  <div className="seg" style={{ flexGrow: Math.max(q.growth, 0), background: S[0] }} />
                </div>
                <span className="bar-tick">{q.label}</span>
              </div>
            ))}
            <div className="r40-threshold" style={{ bottom: `${(THRESHOLD / max) * 150 + 22}px` }}>
              <span>40</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
