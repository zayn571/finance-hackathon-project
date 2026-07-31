import { useMemo } from "react";
import metrics from "../data/dashboardMetrics.json";
import { derive, MONTHLY, type Period } from "../lib/derive";

const money = (v: number) => (Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${Math.round(v / 1000)}k`);

/**
 * Prior-year revenue for the same calendar months, so the growth figure on the
 * strip tracks whatever period is selected rather than a fixed year-to-date.
 */
const FY25_MONTHLY = [
  2035901.72, 2864948.3, 2608085.67, 2443046.97, 2118994.85, 2946624.05,
];

export default function KpiStrip({ period }: { period: Period }) {
  const d = useMemo(() => derive(period.months), [period]);

  const priorRevenue = period.months.reduce((a, mi) => a + (FY25_MONTHLY[mi] ?? 0), 0);
  const growthPct = priorRevenue ? ((d.revenue.total - priorRevenue) / priorRevenue) * 100 : 0;
  const label = period.key === "FY26" ? "year to date" : period.label.replace(" FY26", "");

  const tiles = [
    { label: "Revenue", value: money(d.revenue.total), delta: `${growthPct.toFixed(1)}% vs FY25`, favorable: growthPct > 0 },
    { label: "Adj. EBITDA", value: money(d.adjEbitda), delta: `${d.ebitdaPct.toFixed(1)}% margin` },
    { label: "Gross margin", value: `${d.grossMarginPct.total.toFixed(1)}%`, delta: money(d.grossMargin.total) },
    { label: "Bookings", value: money(d.bookings.total), delta: `${d.bookings.dealCount} deals closed won` },
    { label: "Backlog", value: `$${metrics.backlog.series[metrics.backlog.series.length - 1].value.toFixed(2)}M`, delta: "sold, not delivered" },
    { label: "Headcount", value: String(d.projectHours.billableHeadcount + d.projectHours.nonBillableHeadcount), delta: `${d.projectHours.billablePct.toFixed(0)}% billable`, favorable: true },
  ];

  return (
    <>
      <div className="section-caption">Showing {label}</div>
      <div className="kpi-strip">
        {tiles.map((t) => (
          <div key={t.label} className="kpi-card">
            <div className="kpi-label">{t.label}</div>
            <div className="kpi-value">{t.value}</div>
            <div className={t.favorable ? "kpi-delta favorable" : "kpi-delta"}>{t.delta}</div>
          </div>
        ))}
      </div>
    </>
  );
}

export { FY25_MONTHLY };
export const MONTH_LABELS = MONTHLY.map((m) => m.month);
