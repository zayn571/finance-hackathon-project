import { useState } from "react";
import KpiStrip from "./components/KpiStrip";
import PeriodSelector from "./components/PeriodSelector";
import RuleOf40 from "./components/RuleOf40";
import IncomeStatement from "./components/IncomeStatement";
import { RevenueEbitdaByMonth, YoyGrowth, RevenueByQuarter, ExpenseBase } from "./components/Charts";
import ArAging from "./components/ArAging";
import { Backlog, Attrition, FixedCostMix } from "./components/BacklogAttrition";
import Headcount, { NewClients } from "./components/Headcount";
import BrexActivity from "./components/BrexActivity";
import CloseBoard from "./components/CloseBoard";
import WorkingFiles from "./components/WorkingFiles";
import { PERIODS } from "./lib/derive";
import "./App.css";

export default function App() {
  // Period drives the KPI strip, Rule of 40, the income statement columns and
  // which months read as active in the trend charts.
  const [period, setPeriod] = useState(PERIODS[0]);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <div className="eyebrow">Finance — RapDev</div>
          <h1>Operating dashboard</h1>
        </div>
        <PeriodSelector period={period} onChange={setPeriod} />
      </header>

      <main className="page-body">
        <KpiStrip period={period} />
        <RuleOf40 period={period} />
        <div className="grid-2">
          <RevenueEbitdaByMonth period={period} />
          <RevenueByQuarter />
        </div>
        <div className="grid-2">
          <YoyGrowth period={period} />
          <ExpenseBase />
        </div>
        <IncomeStatement period={period} />
        <ArAging />
        <div className="grid-2">
          <Backlog />
          <Attrition />
        </div>
        <BrexActivity />
        <Headcount />
        <div className="grid-2">
          <NewClients />
          <FixedCostMix />
        </div>
        <CloseBoard />
        <WorkingFiles />
      </main>
    </div>
  );
}
