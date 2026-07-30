import IncomeStatement from "./components/IncomeStatement";
import "./App.css";

export default function App() {
  return (
    <div className="page">
      <header className="page-header">
        <div className="eyebrow">Finance — RapDev Hackathon</div>
        <h1>Operating dashboard</h1>
      </header>
      <main className="page-body">
        <IncomeStatement />
      </main>
    </div>
  );
}
