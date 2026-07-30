import metrics from "../data/dashboardMetrics.json";

const k = metrics.kpis;
const money = (v: number) => (Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${Math.round(v / 1000)}k`);

interface Tile {
  label: string;
  value: string;
  delta: string;
  favorable?: boolean;
}

const TILES: Tile[] = [
  { label: "Revenue YTD", value: money(k.revenueYtd), delta: `${k.revenueYtdGrowthPct?.toFixed(1)}% vs FY25`, favorable: true },
  { label: "EBITDA YTD", value: money(k.ebitdaYtd), delta: `${k.ebitdaMarginPct?.toFixed(1)}% margin` },
  { label: "Gross margin", value: `${k.grossMarginPct?.toFixed(1)}%`, delta: "closed months" },
  { label: "A/R outstanding", value: money(k.arTotal), delta: `${money(k.arOver60)} over 60 days` },
  { label: "Headcount", value: String(k.headcount), delta: `${k.headcountBillable} billable`, favorable: true },
  { label: "Billable mix", value: `${Math.round((k.headcountBillable / k.headcount) * 100)}%`, delta: "of headcount" },
];

export default function KpiStrip() {
  return (
    <div className="kpi-strip">
      {TILES.map((t) => (
        <div key={t.label} className="kpi-card">
          <div className="kpi-label">{t.label}</div>
          <div className="kpi-value">{t.value}</div>
          <div className={t.favorable ? "kpi-delta favorable" : "kpi-delta"}>{t.delta}</div>
        </div>
      ))}
    </div>
  );
}
