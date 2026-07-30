import KpiStrip from "./components/KpiStrip";
import RuleOf40 from "./components/RuleOf40";
import IncomeStatement from "./components/IncomeStatement";
import { RevenueEbitdaByMonth, YoyGrowth, RevenueByQuarter, ExpenseBase } from "./components/Charts";
import ArAging from "./components/ArAging";
import { Backlog, Attrition, FixedCostMix } from "./components/BacklogAttrition";
import CloseBoard from "./components/CloseBoard";
import WorkingFiles from "./components/WorkingFiles";
import metrics from "./data/dashboardMetrics.json";
import "./App.css";

export default function App() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Finance — RapDev</div>
          <h1>Operating dashboard</h1>
        </div>
        <div className="header-meta">
          <span>
            <strong>Closed through</strong> {metrics.meta.closedThrough}
          </span>
          <span>
            <strong>Units</strong> USD
          </span>
        </div>
      </header>

      <main className="page-body">
        <KpiStrip />
        <RuleOf40 />
        <div className="grid-2">
          <RevenueEbitdaByMonth />
          <RevenueByQuarter />
        </div>
        <div className="grid-2">
          <YoyGrowth />
          <ExpenseBase />
        </div>
        <IncomeStatement />
        <ArAging />
        <div className="grid-2">
          <Backlog />
          <Attrition />
        </div>
        <FixedCostMix />
        <CloseBoard />
        <WorkingFiles />
      </main>
    </div>
  );
}
