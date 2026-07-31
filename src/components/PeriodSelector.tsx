import { PERIODS, MONTHLY, type Period } from "../lib/derive";

/**
 * Drives the whole page. Working days is the real business-day count for the
 * selected months, which is what the bill-rate and utilization maths uses.
 */
export default function PeriodSelector({
  period,
  onChange,
}: {
  period: Period;
  onChange: (p: Period) => void;
}) {
  const workingDays = period.months.reduce((a, mi) => a + MONTHLY[mi].workingDays, 0);

  return (
    <div className="header-controls">
      <label className="period-field">
        <span className="period-label">Period</span>
        <select
          value={period.key}
          onChange={(e) => {
            const next = PERIODS.find((p) => p.key === e.target.value);
            if (next) onChange(next);
          }}
        >
          {PERIODS.map((p) => (
            <option key={p.key} value={p.key}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <div className="header-divider" />
      <div className="header-stat">
        <span className="header-stat-label">Working days</span>
        <span className="header-stat-value">{workingDays}</span>
      </div>
      <div className="header-stat">
        <span className="header-stat-label">Units</span>
        <span className="header-stat-value">USD</span>
      </div>
    </div>
  );
}
