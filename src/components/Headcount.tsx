import hc from "../data/headcountByClass.json";
import syn from "../data/synechronTemplates.json";
import { downloadDeptListingXlsx } from "../lib/exportDeptListingXlsx";
import { SERIES } from "../lib/chartTokens";

const S = SERIES.light;

interface Child {
  code: string;
  name: string;
  headcount: number;
  billable: number;
}
interface Group {
  code: string;
  name: string;
  children: Child[];
}

const groups = hc.groups as Group[];

/**
 * Headcount by class, from the BambooHR department listing roster. Billable is
 * counted per employee off the Billable Status column rather than assumed from
 * the department, so a non-billable person in a delivery team is counted as such.
 */
export default function Headcount() {
  const total = hc.total;
  const billable = hc.billable;
  const maxChild = Math.max(...groups.flatMap((g) => g.children.map((c) => c.headcount)));

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Headcount by class</h2>
          <p className="hint">
            BambooHR department listing roster, billable counted per employee from the Billable
            Status column. Two other bases exist for the same month and are not wrong, just
            different: {hc.reconciliation.junCloseReported} reported at the June close, and{" "}
            {syn.dashboardTemplate.june.headcountOnsite} on the Synechron onsite basis, which
            excludes interns, contractors and signed-not-joined.
          </p>
        </div>
        <div className="hc-stats">
          <div className="hc-stat">
            <span className="hc-stat-value">{total}</span>
            <span className="hc-stat-label">Total</span>
          </div>
          <div className="hc-stat">
            <span className="hc-stat-value teal">{billable}</span>
            <span className="hc-stat-label">Billable</span>
          </div>
          <div className="hc-stat">
            <span className="hc-stat-value">{Math.round((billable / total) * 100)}%</span>
            <span className="hc-stat-label">Billable mix</span>
          </div>
          <button className="btn btn-primary" onClick={() => downloadDeptListingXlsx()}>
            Download Excel
          </button>
        </div>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th className="label-col">Class</th>
              <th>Headcount</th>
              <th>Billable</th>
              <th className="share-col">Share</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => {
              const gTotal = g.children.reduce((a, c) => a + c.headcount, 0);
              const gBillable = g.children.reduce((a, c) => a + c.billable, 0);
              return [
                <tr key={g.code} className="is-row is-total">
                  <td className="label-col">
                    {g.code} {g.name}
                    <span className="badge badge-outline">Group</span>
                  </td>
                  <td>{gTotal}</td>
                  <td>{gBillable}</td>
                  <td className="share-col" />
                </tr>,
                ...g.children.map((c) => (
                  <tr key={`${g.code}-${c.code}`} className="is-row">
                    <td className="label-col" style={{ paddingLeft: 32 }}>
                      {c.code} {c.name}
                      <span className={c.billable > 0 ? "badge badge-teal" : "badge badge-tint"}>
                        {c.billable > 0 ? "Billable" : "Non-billable"}
                      </span>
                    </td>
                    <td>{c.headcount}</td>
                    <td>{c.billable}</td>
                    <td className="share-col">
                      <span className="share-track">
                        <span
                          className="share-bar"
                          style={{ width: `${(c.headcount / maxChild) * 100}%`, background: S[0] }}
                        />
                      </span>
                    </td>
                  </tr>
                )),
              ];
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** New logos won, with the initial contract value from the closed-won deal. */
export function NewClients() {
  const clients = syn.newClientsWon as { name: string; initialContractValue: number }[];
  const total = clients.reduce((a, c) => a + c.initialContractValue, 0);
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="eyebrow eyebrow-teal">New business</div>
          <h2>New clients won</h2>
          <p className="hint">
            {clients.length} new logos, {syn.month}. Initial contract value from the closed-won
            deal in HubSpot.
          </p>
        </div>
        <div className="stat-inline">
          <span className="stat-value">${(total / 1e6).toFixed(2)}M</span>
          <span className="stat-label">initial contract value</span>
        </div>
      </div>
      <div className="table-scroll short">
        <table>
          <thead>
            <tr>
              <th className="label-col">Client</th>
              <th>Initial contract value</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((c) => (
              <tr key={c.name} className="is-row">
                <td className="label-col">{c.name}</td>
                <td className="strong">{Math.round(c.initialContractValue).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
