import metrics from "../data/dashboardMetrics.json";
import { SERIES } from "../lib/chartTokens";

const S = SERIES.light;
const r40 = metrics.rule40;

/**
 * Rule of 40 = revenue growth % year over year + Adj EBITDA margin %.
 * Both components come from the QuickBooks P&L over matched periods, so the
 * score moves only when QBO does.
 */
export default function RuleOf40() {
  const { score, growthPct, marginPct, threshold } = r40.h1;
  const above = score >= threshold;
  const byQuarter = r40.byQuarter;
  const max = Math.max(...byQuarter.map((q) => q.score), threshold) * 1.15;

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Rule of 40</h2>
          <p className="hint">
            Revenue growth year over year plus Adj EBITDA margin, both from the QuickBooks P&amp;L.
            Measured over FY26 closed months ({metrics.meta.closedThrough}) against the same months
            of FY25.
          </p>
        </div>
      </div>

      <div className="r40-grid">
        <div>
          <div className="r40-score">{score.toFixed(1)}</div>
          <div className={above ? "r40-verdict pass" : "r40-verdict fail"}>
            {above ? "Above the 40 line" : "Below the 40 line"}
          </div>
          <div className="r40-bar">
            <div className="seg" style={{ flexGrow: growthPct ?? 0, background: S[0] }} />
            <div className="seg" style={{ flexGrow: marginPct ?? 0, background: S[1] }} />
          </div>
          <div className="legend">
            <span className="legend-item"><span className="legend-swatch" style={{ background: S[0] }} />Growth</span>
            <span className="legend-item"><span className="legend-swatch" style={{ background: S[1] }} />Margin</span>
          </div>
          <dl className="r40-rows">
            <div><dt>Revenue growth YoY</dt><dd>{growthPct?.toFixed(1)}%</dd></div>
            <div><dt>Adj EBITDA margin</dt><dd>{marginPct?.toFixed(1)}%</dd></div>
            <div><dt>Threshold</dt><dd>{threshold.toFixed(1)}</dd></div>
          </dl>
        </div>

        <div>
          <div className="r40-chart">
            {byQuarter.map((q) => (
              <div key={q.quarter} className="bar-group">
                <span className="bar-label">{q.score.toFixed(1)}</span>
                <div className="stack" style={{ height: `${(q.score / max) * 150}px` }}>
                  <div className="seg" style={{ flexGrow: q.marginPct ?? 0, background: S[1] }} />
                  <div className="seg" style={{ flexGrow: q.growthPct ?? 0, background: S[0] }} />
                </div>
                <span className="bar-tick">{q.quarter}</span>
              </div>
            ))}
            <div className="r40-threshold" style={{ bottom: `${(threshold / max) * 150 + 22}px` }}>
              <span>40</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
