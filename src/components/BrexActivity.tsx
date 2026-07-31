import brex from "../data/brexCardActivity.json";
import { SERIES } from "../lib/chartTokens";

const S = SERIES.light;
const fmt = (v: number) => Math.round(v).toLocaleString();
const money = (v: number) => (Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${fmt(v)}`);

/**
 * Brex card activity.
 *
 * Categories follow QuickBooks bank-rule priority: the first matching rule in
 * QBO's own rule order wins, exactly as QBO itself would assign it. Where no rule
 * matches, the category already on the transaction import file is used. There is
 * no mapping of our own in this component — one would only diverge from what
 * actually posts.
 *
 * Whole-month figures come from the QuickBooks detail report for account 62.
 * Cardholder names are stripped from every descriptor upstream.
 */
export default function BrexActivity() {
  const j = brex.july2026;
  const w = brex.window;
  const cats = brex.bySubCategory;
  const maxCat = Math.max(...cats.map((c) => c.amount));
  const maxVendor = Math.max(...brex.topVendors.map((v) => v.amount));
  const deptTotal = brex.byDepartment.reduce((a, d) => a + d.amount, 0);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="eyebrow eyebrow-teal">Card activity</div>
          <h2>Brex</h2>
          <p className="hint">
            {j.postedLines} posted lines across {j.distinctMerchants} merchants in July, from the
            QuickBooks detail for account {brex.account.qboAcctNum}. The {w.lines} lines from{" "}
            {w.from} to {w.to} ({money(w.total)}) are categorised by QuickBooks bank-rule priority
            across {brex.categorization.rulesEvaluated} rules — {brex.categorization.byBankRule} matched
            a rule, {brex.categorization.byImportFile} fell back to the import file.
          </p>
        </div>
        <div className="stat-inline">
          <span className="stat-value">{money(brex.account.balance)}</span>
          <span className="stat-label">balance at {brex.account.balanceAsOf}</span>
        </div>
      </div>

      <div className="brex-stats">
        <div className="brex-stat">
          <span className="brex-stat-label">Gross charges, July</span>
          <span className="brex-stat-value">{fmt(j.grossCharges)}</span>
        </div>
        <div className="brex-stat">
          <span className="brex-stat-label">Credits &amp; refunds</span>
          <span className="brex-stat-value">({fmt(Math.abs(j.creditsAndRefunds))})</span>
        </div>
        <div className="brex-stat">
          <span className="brex-stat-label">Net activity</span>
          <span className="brex-stat-value">{fmt(j.netActivity)}</span>
        </div>
        <div className="brex-stat">
          <span className="brex-stat-label">Largest charge</span>
          <span className="brex-stat-value">{fmt(brex.largestCharge.amount)}</span>
          <span className="brex-stat-sub">
            {brex.largestCharge.vendor} · {brex.largestCharge.date}
          </span>
        </div>
      </div>

      <div className="grid-2 brex-panels">
        <div>
          <h3 className="sub-head">
            Spend by sub category, {w.from.slice(5)} to {w.to.slice(5)}
          </h3>
          <div className="hbar-rows">
            {cats.map((c) => (
              <div key={c.category} className="hbar-row">
                <span className="hbar-label" title={c.category}>
                  {c.category}
                </span>
                <span className="hbar-track">
                  <span
                    className="hbar-fill"
                    style={{ width: `${(c.amount / maxCat) * 100}%`, background: S[0] }}
                  />
                </span>
                <span className="hbar-val">{fmt(c.amount)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="sub-head">Top vendors</h3>
          <div className="hbar-rows">
            {brex.topVendors.map((v) => (
              <div key={v.vendor} className="hbar-row">
                <span className="hbar-label" title={v.vendor}>
                  {v.vendor}
                </span>
                <span className="hbar-track">
                  <span
                    className="hbar-fill"
                    style={{ width: `${(v.amount / maxVendor) * 100}%`, background: S[1] }}
                  />
                </span>
                <span className="hbar-val">{fmt(v.amount)}</span>
              </div>
            ))}
          </div>

          <h3 className="sub-head">By department</h3>
          <div className="dept-bar">
            {brex.byDepartment.map((d, i) => (
              <span
                key={d.department}
                className="dept-seg"
                title={`${d.department} — ${fmt(d.amount)}`}
                style={{
                  flexGrow: d.amount,
                  background: [S[0], S[1], S[2], "#9FB3C4"][i % 4],
                }}
              />
            ))}
          </div>
          <div className="legend">
            {brex.byDepartment.map((d, i) => (
              <span key={d.department} className="legend-item">
                <span
                  className="legend-swatch"
                  style={{ background: [S[0], S[1], S[2], "#9FB3C4"][i % 4] }}
                />
                {d.department.replace(/^\d+-\s*/, "")} {Math.round((d.amount / deptTotal) * 100)}%
              </span>
            ))}
          </div>
        </div>
      </div>

      <h3 className="sub-head">Rules doing the most work</h3>
      <div className="rule-chips">
        {brex.categorization.topRules.map((r) => (
          <span key={r.rule} className="rule-chip">
            <span className="rule-chip-name">{r.rule}</span>
            <span className="rule-chip-n">{r.lines} lines</span>
          </span>
        ))}
      </div>

      <h3 className="sub-head">Largest charges in the window</h3>
      <div className="table-scroll short">
        <table>
          <thead>
            <tr>
              <th className="label-col">Merchant</th>
              <th className="left">Category</th>
              <th className="left">Department</th>
              <th className="left">Rule</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {brex.recent.map((t, i) => (
              <tr key={`${t.date}-${t.merchant}-${i}`} className="is-row">
                <td className="label-col">
                  {t.merchant}
                  <span className="txn-time">
                    {t.vendor} · {t.date}
                  </span>
                </td>
                <td className="left">{t.category}</td>
                <td className="left">{t.department.replace(/^\d+-\s*/, "")}</td>
                <td className="left mono-sm">{t.rule}</td>
                <td className="strong">{t.amount.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
