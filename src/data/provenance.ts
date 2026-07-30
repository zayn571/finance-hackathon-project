/**
 * Where each income-statement row's number actually comes from.
 *
 * This exists because a pro-rata allocation and a QuickBooks actual look
 * identical once they are both rendered as a number in a table. Anyone reading
 * a figure off this dashboard needs to know which one they are looking at.
 *
 * Verified against the QBO Profit & Loss pulled by class and by month:
 *  - QBO splits COGS-Personnel by payroll component (401k, Benefits, Bonuses,
 *    Commissions, Payroll Fees, Payroll Taxes, Salaries & Wages) and by class
 *    (Delivery / Engineering / Sales). It does NOT split by service line, so
 *    every "DD Services / DD Software / Managed DD / Managed Security" figure
 *    is an allocation of the QBO class total, not a sourced number.
 *  - opex.personnel ties exactly to G&A-Personnel + S&M-Personnel.
 *  - cogs.contractorFees is the COGS-Synechron Intercompany (Dreamix) line
 *    relabelled — a defensible mapping, but a mapping.
 */
export type Provenance =
  /** Read directly from the QuickBooks P&L, or computed purely from QBO figures. */
  | "qbo"
  /** A QBO total split across sub-streams pro-rata. The total is real; the split is assumed. */
  | "allocated"
  /** A QBO figure presented under a different label than the account it came from. */
  | "mapped"
  /** No source we can trace. Do not rely on this number. */
  | "unverified";

export const PROVENANCE: Record<string, Provenance> = {
  // --- Bookings: claimed to come from closed-won HubSpot deals, but not verified
  // here, and Q1 (14,213,362) disagrees with the reference income statement
  // (5,685k) by roughly 2.5x.
  bookings: "unverified",
  "bookings-dd": "unverified",
  "bookings-sn": "unverified",
  "bookings-sw": "unverified",
  "bookings-msp": "unverified",
  "analysis-bookings": "unverified",
  "analysis-bookings-dd-share": "unverified",
  "analysis-bookings-sn-share": "unverified",

  // --- Revenue: all QBO income accounts
  revenue: "qbo",
  "revenue-dd": "qbo",
  "revenue-dd-services": "qbo",
  "revenue-dd-software": "qbo",
  "revenue-dd-managedDd": "qbo",
  "revenue-dd-managedSoc": "qbo",
  "revenue-sn": "qbo",
  "revenue-sn-services": "qbo",
  "revenue-sn-software": "qbo",
  "revenue-sn-msp": "qbo",
  "revenue-totalServices": "qbo",
  "revenue-totalSw": "qbo",
  "revenue-totalMsp": "qbo",

  // --- COGS
  cogs: "qbo",
  "cogs-payroll": "qbo",
  "cogs-payroll-dd": "qbo",
  "cogs-payroll-sn": "qbo",
  "cogs-payroll-dd-services": "allocated",
  "cogs-payroll-dd-software": "allocated",
  "cogs-payroll-managedDd": "allocated",
  "cogs-payroll-managedSecurity": "allocated",
  "cogs-payroll-sn-services": "allocated",
  "cogs-payroll-sn-software": "allocated",
  "cogs-payroll-sn-msp": "allocated",
  "cogs-travel": "qbo",
  "cogs-travel-dd": "qbo",
  "cogs-travel-sn": "qbo",
  "cogs-marketplaceFees": "qbo",
  "cogs-contractorFees": "mapped",
  "cogs-totalDd": "qbo",
  "cogs-totalSn": "qbo",

  // --- Gross margin: practice-level ties to QBO; per-stream inherits the allocation
  "gm-dollars": "qbo",
  "gm-dd": "qbo",
  "gm-sn": "qbo",
  "gm-dd-services": "allocated",
  "gm-dd-software": "allocated",
  "gm-managedDd": "allocated",
  "gm-managedSecurity": "allocated",
  "gm-sn-services": "allocated",
  "gm-sn-software": "allocated",
  "gm-sn-msp": "allocated",
  "gm-pct": "qbo",
  "gm-pct-dd": "qbo",
  "gm-pct-sn": "qbo",
  "gm-pct-dd-services": "allocated",
  "gm-pct-dd-software": "allocated",
  "gm-pct-managedDd": "allocated",
  "gm-pct-managedSecurity": "allocated",
  "gm-pct-sn-services": "allocated",
  "gm-pct-sn-software": "allocated",
  "gm-pct-sn-msp": "allocated",

  // --- Operating expenses: all QBO
  opex: "qbo",
  "opex-ga": "qbo",
  "opex-ga-dd": "qbo",
  "opex-ga-sn": "qbo",
  "opex-ga-ops": "qbo",
  "opex-personnel": "qbo",
  "opex-personnel-dd": "qbo",
  "opex-personnel-sn": "qbo",
  "opex-personnel-ops": "qbo",
  "opex-sm": "qbo",
  "opex-sm-dd": "qbo",
  "opex-sm-sn": "qbo",
  "opex-sm-ops": "qbo",

  // --- Other expenses / EBITDA adjustments
  otherExpenses: "qbo",
  "otherExpenses-line": "qbo",
  "otherExpenses-addback": "unverified",
  ebitdaAdjustments: "unverified",
  "ebitdaAdjustments-mwe": "unverified",

  adjEbitda: "qbo",
  ebitdaPct: "qbo",

  // --- Analysis block
  grossProfit: "qbo",
  "grossProfit-dd": "qbo",
  "grossProfit-dd-pct": "qbo",
  "grossProfit-sn": "qbo",
  "grossProfit-sn-pct": "qbo",
  "grossProfit-total": "qbo",
  "grossProfit-total-pct": "qbo",
  cogsOpex: "qbo",
  "cogsOpex-pctRevenue": "qbo",
  "opexNetIncome-cogsPct": "qbo",
  "opexNetIncome-gaPct": "qbo",
  "opexNetIncome-personnelPct": "qbo",
  "opexNetIncome-smPct": "qbo",
  "opexNetIncome-netOpIncomeMargin": "qbo",
  servicesBillings: "qbo",

  // --- Project hours and bill rate: no traceable source, and both contradict the
  // only independently verified figures we have (delivered Synechron workbook,
  // Jun 2026: utilization 72.35%, blended bill rate 317.91).
  "projectHours-nonBillableHc": "mapped",
  "projectHours-billableHc": "mapped",
  "projectHours-nonBillablePct": "mapped",
  "projectHours-billablePct": "mapped",
  "projectHours-available": "unverified",
  "projectHours-worked": "unverified",
  "projectHours-utilization": "unverified",
  "projectHours-billed": "unverified",
  "projectHours-billedPerHead": "unverified",
  "projectHours-padding": "unverified",
  "billRate-breakEven": "unverified",
  "billRate-perHourBilled": "unverified",
  "billRate-realRate": "unverified",
  salesEfficiency: "unverified",
};

/**
 * Rows whose stored value actively contradicts a source we verified. A wrong
 * number carrying a warning is still a wrong number, so these are withheld
 * rather than displayed, and VERIFIED_REFERENCE gives the figure we can stand
 * behind instead.
 *
 * The verified figures are June 2026 point-in-time from the delivered Synechron
 * workbook, so they cannot be restated as quarterly values — which is exactly
 * why the quarterly cells are blank rather than corrected.
 */
export const SUPPRESSED = new Set<string>([
  "projectHours-available",
  "projectHours-worked",
  "projectHours-utilization",
  "projectHours-billed",
  "projectHours-billedPerHead",
  "projectHours-padding",
  "billRate-breakEven",
  "billRate-perHourBilled",
  "billRate-realRate",
]);

export const VERIFIED_REFERENCE: Record<string, string> = {
  "projectHours-utilization": "72.35% (Jun 2026, Synechron workbook)",
  "billRate-perHourBilled": "317.91 blended (Jun 2026, Synechron workbook)",
};

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  qbo: "From QuickBooks",
  allocated: "Allocated pro-rata",
  mapped: "Mapped from another source",
  unverified: "Unverified",
};

export const PROVENANCE_TITLE: Record<Provenance, string> = {
  qbo: "Read from the QuickBooks P&L, or computed purely from QBO figures.",
  allocated:
    "The practice-level total is from QuickBooks, but QBO does not split COGS by service line — this sub-stream figure is that total apportioned pro-rata by revenue.",
  mapped:
    "A real figure from another system, presented under a different label than its source account.",
  unverified:
    "No source we can trace to. Utilization and bill rate here also disagree with the delivered Synechron workbook (Jun 2026: 72.35% utilization, 317.91 blended rate). Do not rely on these.",
};
