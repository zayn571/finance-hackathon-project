import brex from "../data/brexCardActivity.json";
import { SERIES } from "../lib/chartTokens";

const S = SERIES.light;
const fmt = (v: number) => Math.round(v).toLocaleString();
const money = (v: number) => (Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${fmt(v)}`);

/**
 * Brex card activity. Balance and month totals come from the QuickBooks
 * Transaction Detail report for account 62, which is authoritative for posted
 * activity; the live feed and its categories come from the Brex expenses API,
 * which also carries pending charges QBO has not seen yet.
 *
 * Cardholder names are deliberately absent — merchant, amount, category and
 * status only.
 */
export default function BrexActivity() {
  const j = brex.july2026;
  const cats = brex.feed.byCategory;
  const maxCat = Math.max(...cats.map((c) => c.amount));
  const maxMerchant = Math.max(...brex.topMerchants.map((m) => m.amount));

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="eyebrow eyebrow-teal">Card activity</div>
          <h2>Brex</h2>
          <p className="hint">
            {j.postedLines} posted lines across {j.distinctMerchants} merchants in July, from the
            QuickBooks detail for account {brex.account.qboAcctNum}. Live feed and categories from
            the Brex expenses API. Cardholder names are excluded by design.
          </p>
        </div>
        <div className="stat-inline">
          <span className="stat-value">{money(brex.account.balance)}</span>
          <span className="stat-label">balance at {brex.account.balanceAsOf}</span>
        </div>
      </div>

      <div className="brex-stats">
        <div className="brex-stat">
          <span className="brex-stat-label">Gross charges</span>
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
            {brex.largestCharge.merchant} · {brex.largestCharge.date}
          </span>
        </div>
      </div>

      <div className="grid-2 brex-panels">
        <div>
          <h3 className="sub-head">Top merchants, July</h3>
          <div className="hbar-rows">
            {brex.topMerchants.map((m) => (
              <div key={m.merchant} className="hbar-row">
                <span className="hbar-label">{m.merchant}</span>
                <span className="hbar-track">
                  <span
                    className="hbar-fill"
                    style={{ width: `${(m.amount / maxMerchant) * 100}%`, background: S[0] }}
                  />
                </span>
                <span className="hbar-val">{fmt(m.amount)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="sub-head">Feed by category, {brex.feed.window}</h3>
          <div className="hbar-rows">
            {cats.map((c) => (
              <div key={c.category} className="hbar-row">
                <span className="hbar-label">{c.category}</span>
                <span className="hbar-track">
                  <span
                    className="hbar-fill"
                    style={{ width: `${(c.amount / maxCat) * 100}%`, background: S[1] }}
                  />
                </span>
                <span className="hbar-val">{fmt(c.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <h3 className="sub-head">Latest transactions</h3>
      <div className="table-scroll short">
        <table>
          <thead>
            <tr>
              <th className="label-col">Merchant</th>
              <th className="left">Category</th>
              <th className="left">Status</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {brex.feed.recent.map((t, i) => (
              <tr key={`${t.date}-${t.time}-${i}`} className="is-row">
                <td className="label-col">
                  {t.merchant}
                  <span className="txn-time">
                    {t.date} {t.time}
                  </span>
                </td>
                <td className="left">{t.category}</td>
                <td className="left">{t.status}</td>
                <td className="strong">{t.amount.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
