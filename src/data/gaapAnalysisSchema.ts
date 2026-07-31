// Row schema mirrors "Mgmt_Reporting_4.xlsx" → GAAP Analysis tab, rows 1-141
// (everything above the "Forecast" section at row 142). Source of truth: that tab.
export type RowKind = "section" | "band" | "total" | "subtotal" | "line" | "spacer";

export interface SchemaRow {
  key: string;
  label: string;
  indent: number;
  kind: RowKind;
  /** Key into IncomeStatementPeriod used to look up the value. Absent for spacers/bands. */
  dataKey?: string;
  /** Render as a percentage rather than a dollar figure. */
  isPercent?: boolean;
}

export const ACTUALS_ANALYSIS_SCHEMA: SchemaRow[] = [
  { key: "band-actuals", label: "ACTUALS", indent: 0, kind: "band" },
  { key: "spacer-1", label: "", indent: 0, kind: "spacer" },

  { key: "bookings", label: "Bookings", indent: 0, kind: "total", dataKey: "bookings.total" },
  { key: "bookings-dd", label: "DD", indent: 1, kind: "line", dataKey: "bookings.dd" },
  { key: "bookings-sn", label: "SN", indent: 1, kind: "line", dataKey: "bookings.sn" },
  { key: "bookings-sw", label: "SW", indent: 1, kind: "line", dataKey: "bookings.sw" },
  { key: "bookings-msp", label: "MSP", indent: 1, kind: "line", dataKey: "bookings.msp" },
  { key: "spacer-2", label: "", indent: 0, kind: "spacer" },

  { key: "revenue", label: "Revenue", indent: 0, kind: "total", dataKey: "revenue.total" },
  { key: "revenue-dd", label: "DD", indent: 1, kind: "subtotal", dataKey: "revenue.dd.total" },
  { key: "revenue-dd-services", label: "Services", indent: 2, kind: "line", dataKey: "revenue.dd.services" },
  { key: "revenue-dd-software", label: "Software", indent: 2, kind: "line", dataKey: "revenue.dd.software" },
  { key: "revenue-dd-managedDd", label: "Managed DD", indent: 2, kind: "line", dataKey: "revenue.dd.managedDd" },
  { key: "revenue-dd-managedSoc", label: "Managed SOC", indent: 2, kind: "line", dataKey: "revenue.dd.managedSoc" },
  { key: "revenue-dd-intercompany", label: "Intercompany", indent: 2, kind: "line", dataKey: "revenue.dd.intercompany" },
  { key: "revenue-sn", label: "SN", indent: 1, kind: "subtotal", dataKey: "revenue.sn.total" },
  { key: "revenue-sn-services", label: "Services", indent: 2, kind: "line", dataKey: "revenue.sn.services" },
  { key: "revenue-sn-software", label: "Software", indent: 2, kind: "line", dataKey: "revenue.sn.software" },
  { key: "revenue-sn-msp", label: "MSP", indent: 2, kind: "line", dataKey: "revenue.sn.msp" },
  { key: "revenue-sn-intercompany", label: "Intercompany", indent: 2, kind: "line", dataKey: "revenue.sn.intercompany" },
  { key: "revenue-other", label: "Other revenue", indent: 1, kind: "line", dataKey: "revenue.other" },
  { key: "revenue-totalServices", label: "Total Services", indent: 1, kind: "subtotal", dataKey: "revenue.totalServices" },
  { key: "revenue-totalSw", label: "Total SW", indent: 1, kind: "subtotal", dataKey: "revenue.totalSw" },
  { key: "revenue-totalMsp", label: "Total MSP", indent: 1, kind: "subtotal", dataKey: "revenue.totalMsp" },
  { key: "spacer-3", label: "", indent: 0, kind: "spacer" },

  { key: "cogs", label: "COGS", indent: 0, kind: "total", dataKey: "cogs.total" },
  { key: "cogs-payroll", label: "COGS Payroll", indent: 1, kind: "subtotal", dataKey: "cogs.payroll.total" },
  { key: "cogs-payroll-dd", label: "DD", indent: 2, kind: "line", dataKey: "cogs.payroll.dd.total" },
  { key: "cogs-payroll-dd-services", label: "DD Services", indent: 3, kind: "line", dataKey: "cogs.payroll.dd.services" },
  { key: "cogs-payroll-dd-software", label: "DD Software", indent: 3, kind: "line", dataKey: "cogs.payroll.dd.software" },
  { key: "cogs-payroll-managedDd", label: "Managed DD", indent: 3, kind: "line", dataKey: "cogs.payroll.managedDd" },
  { key: "cogs-payroll-managedSecurity", label: "Managed Security", indent: 3, kind: "line", dataKey: "cogs.payroll.managedSecurity" },
  { key: "cogs-payroll-sn", label: "SN", indent: 2, kind: "line", dataKey: "cogs.payroll.sn.total" },
  { key: "cogs-payroll-sn-services", label: "SN Services", indent: 3, kind: "line", dataKey: "cogs.payroll.sn.services" },
  { key: "cogs-payroll-sn-software", label: "SN Software", indent: 3, kind: "line", dataKey: "cogs.payroll.sn.software" },
  { key: "cogs-payroll-sn-msp", label: "SN MSP", indent: 3, kind: "line", dataKey: "cogs.payroll.sn.msp" },
  { key: "cogs-travel", label: "COGS Travel", indent: 1, kind: "subtotal", dataKey: "cogs.travel.total" },
  { key: "cogs-travel-dd", label: "DD", indent: 2, kind: "line", dataKey: "cogs.travel.dd" },
  { key: "cogs-travel-sn", label: "SN", indent: 2, kind: "line", dataKey: "cogs.travel.sn" },
  { key: "cogs-marketplaceFees", label: "Marketplace Fees", indent: 1, kind: "line", dataKey: "cogs.marketplaceFees" },
  { key: "cogs-contractorFees", label: "Contractor Fees", indent: 1, kind: "line", dataKey: "cogs.contractorFees" },
  { key: "cogs-totalDd", label: "Total DD COGS", indent: 1, kind: "subtotal", dataKey: "cogs.totalDd" },
  { key: "cogs-totalSn", label: "Total SN COGS", indent: 1, kind: "subtotal", dataKey: "cogs.totalSn" },
  { key: "spacer-4", label: "", indent: 0, kind: "spacer" },

  { key: "gm-dollars", label: "Gross Margin $", indent: 0, kind: "total", dataKey: "grossMargin.total" },
  { key: "gm-dd", label: "DD", indent: 2, kind: "line", dataKey: "grossMargin.dd.total" },
  { key: "gm-dd-services", label: "DD Services", indent: 2, kind: "line", dataKey: "grossMargin.dd.services" },
  { key: "gm-dd-software", label: "DD Software", indent: 2, kind: "line", dataKey: "grossMargin.dd.software" },
  { key: "gm-managedDd", label: "Managed DD", indent: 2, kind: "line", dataKey: "grossMargin.managedDd" },
  { key: "gm-managedSecurity", label: "Managed Security", indent: 2, kind: "line", dataKey: "grossMargin.managedSecurity" },
  { key: "gm-sn", label: "SN", indent: 2, kind: "line", dataKey: "grossMargin.sn.total" },
  { key: "gm-sn-services", label: "SN Services", indent: 2, kind: "line", dataKey: "grossMargin.sn.services" },
  { key: "gm-sn-software", label: "SN Software", indent: 2, kind: "line", dataKey: "grossMargin.sn.software" },
  { key: "gm-sn-msp", label: "SN MSP", indent: 2, kind: "line", dataKey: "grossMargin.sn.msp" },

  { key: "gm-pct", label: "Gross Margin %", indent: 0, kind: "total", dataKey: "grossMarginPct.total", isPercent: true },
  { key: "gm-pct-dd", label: "DD", indent: 2, kind: "line", dataKey: "grossMarginPct.dd", isPercent: true },
  { key: "gm-pct-dd-services", label: "DD Services", indent: 2, kind: "line", dataKey: "grossMarginPct.ddServices", isPercent: true },
  { key: "gm-pct-dd-software", label: "DD Software", indent: 2, kind: "line", dataKey: "grossMarginPct.ddSoftware", isPercent: true },
  { key: "gm-pct-managedDd", label: "Managed DD", indent: 2, kind: "line", dataKey: "grossMarginPct.managedDd", isPercent: true },
  { key: "gm-pct-managedSecurity", label: "Managed Security", indent: 2, kind: "line", dataKey: "grossMarginPct.managedSecurity", isPercent: true },
  { key: "gm-pct-sn", label: "SN", indent: 2, kind: "line", dataKey: "grossMarginPct.sn", isPercent: true },
  { key: "gm-pct-sn-services", label: "SN Services", indent: 2, kind: "line", dataKey: "grossMarginPct.snServices", isPercent: true },
  { key: "gm-pct-sn-software", label: "SN Software", indent: 2, kind: "line", dataKey: "grossMarginPct.snSoftware", isPercent: true },
  { key: "gm-pct-sn-msp", label: "SN MSP", indent: 2, kind: "line", dataKey: "grossMarginPct.snMsp", isPercent: true },
  { key: "spacer-5", label: "", indent: 0, kind: "spacer" },

  { key: "opex", label: "Operating Expenses", indent: 0, kind: "total", dataKey: "opex.total" },
  { key: "opex-ga", label: "Total General & Administrative", indent: 1, kind: "subtotal", dataKey: "opex.ga.total" },
  { key: "opex-ga-dd", label: "DD", indent: 2, kind: "line", dataKey: "opex.ga.dd" },
  { key: "opex-ga-sn", label: "SN", indent: 2, kind: "line", dataKey: "opex.ga.sn" },
  { key: "opex-ga-ops", label: "Operations", indent: 2, kind: "line", dataKey: "opex.ga.ops" },
  { key: "opex-personnel", label: "Total Personnel Expenses", indent: 1, kind: "subtotal", dataKey: "opex.personnel.total" },
  { key: "opex-personnel-dd", label: "DD", indent: 2, kind: "line", dataKey: "opex.personnel.dd" },
  { key: "opex-personnel-sn", label: "SN", indent: 2, kind: "line", dataKey: "opex.personnel.sn" },
  { key: "opex-personnel-ops", label: "Operations", indent: 2, kind: "line", dataKey: "opex.personnel.ops" },
  { key: "opex-sm", label: "Total Sales & Marketing", indent: 1, kind: "subtotal", dataKey: "opex.sm.total" },
  { key: "opex-sm-dd", label: "DD", indent: 2, kind: "line", dataKey: "opex.sm.dd" },
  { key: "opex-sm-sn", label: "SN", indent: 2, kind: "line", dataKey: "opex.sm.sn" },
  { key: "opex-sm-ops", label: "Operations", indent: 2, kind: "line", dataKey: "opex.sm.ops" },
  { key: "spacer-6", label: "", indent: 0, kind: "spacer" },

  { key: "otherExpenses", label: "Other Expenses", indent: 0, kind: "total", dataKey: "otherExpenses.total" },
  { key: "otherExpenses-line", label: "Other Expenses", indent: 1, kind: "line", dataKey: "otherExpenses.total" },
  { key: "otherExpenses-addback", label: "Other Expenses - EBITDA Add Back", indent: 1, kind: "line", dataKey: "otherExpenses.ebitdaAddBack" },
  { key: "spacer-7", label: "", indent: 0, kind: "spacer" },

  { key: "ebitdaAdjustments", label: "EBITDA Adjustments", indent: 0, kind: "total", dataKey: "ebitdaAdjustments.total" },
  { key: "ebitdaAdjustments-mwe", label: "McDermott, Will & Emery", indent: 1, kind: "line", dataKey: "ebitdaAdjustments.mwe" },
  { key: "spacer-8", label: "", indent: 0, kind: "spacer" },
  { key: "spacer-9", label: "", indent: 0, kind: "spacer" },

  { key: "adjEbitda", label: "Adj EBITDA", indent: 0, kind: "total", dataKey: "adjEbitda" },
  { key: "ebitdaPct", label: "EBITDA %", indent: 0, kind: "total", dataKey: "ebitdaPct", isPercent: true },
  { key: "spacer-10", label: "", indent: 0, kind: "spacer" },

  { key: "band-analysis", label: "ANALYSIS", indent: 0, kind: "band" },
  { key: "spacer-11", label: "", indent: 0, kind: "spacer" },

  { key: "analysis-bookings", label: "Bookings", indent: 0, kind: "total", dataKey: "bookings.total" },
  { key: "analysis-bookings-dd-share", label: "DD Share of Bookings", indent: 1, kind: "line", dataKey: "bookingsShare.dd", isPercent: true },
  { key: "analysis-bookings-sn-share", label: "SN Share of Bookings", indent: 1, kind: "line", dataKey: "bookingsShare.sn", isPercent: true },
  { key: "spacer-12", label: "", indent: 0, kind: "spacer" },

  { key: "grossProfit", label: "Gross Profit", indent: 0, kind: "total", dataKey: "grossMargin.total" },
  { key: "grossProfit-dd", label: "DD Gross Profit", indent: 1, kind: "line", dataKey: "grossMargin.dd.total" },
  { key: "grossProfit-dd-pct", label: "DD Gross Profit %", indent: 1, kind: "line", dataKey: "grossMarginPct.dd", isPercent: true },
  { key: "grossProfit-sn", label: "SN Gross Profit", indent: 1, kind: "line", dataKey: "grossMargin.sn.total" },
  { key: "grossProfit-sn-pct", label: "SN Gross Profit %", indent: 1, kind: "line", dataKey: "grossMarginPct.sn", isPercent: true },
  { key: "grossProfit-total", label: "Total Gross Profit", indent: 0, kind: "subtotal", dataKey: "grossMargin.total" },
  { key: "grossProfit-total-pct", label: "Total Gross Profit %", indent: 0, kind: "subtotal", dataKey: "grossMarginPct.total", isPercent: true },
  { key: "spacer-13", label: "", indent: 0, kind: "spacer" },

  { key: "cogsOpex", label: "COGS + Opex", indent: 0, kind: "total", dataKey: "cogsPlusOpex.total" },
  { key: "cogsOpex-pctRevenue", label: "% Revenue", indent: 1, kind: "line", dataKey: "cogsPlusOpex.pctRevenue", isPercent: true },
  { key: "spacer-14", label: "", indent: 0, kind: "spacer" },

  { key: "opexNetIncome", label: "Opex & Net Income", indent: 0, kind: "band" },
  { key: "opexNetIncome-cogsPct", label: "COGS % of Revenue", indent: 1, kind: "line", dataKey: "ratios.cogsPctRevenue", isPercent: true },
  { key: "opexNetIncome-gaPct", label: "G&A % of Revenue", indent: 1, kind: "line", dataKey: "ratios.gaPctRevenue", isPercent: true },
  { key: "opexNetIncome-personnelPct", label: "Personnel % of Revenue", indent: 1, kind: "line", dataKey: "ratios.personnelPctRevenue", isPercent: true },
  { key: "opexNetIncome-smPct", label: "S&M % of Revenue", indent: 1, kind: "line", dataKey: "ratios.smPctRevenue", isPercent: true },
  { key: "opexNetIncome-netOpIncomeMargin", label: "Net Operating Income Margin", indent: 1, kind: "line", dataKey: "ratios.netOperatingIncomeMargin", isPercent: true },
  { key: "spacer-15", label: "", indent: 0, kind: "spacer" },

  { key: "projectHours", label: "Project Hours", indent: 0, kind: "band" },
  { key: "projectHours-nonBillableHc", label: "Non-Billable Headcount", indent: 1, kind: "line", dataKey: "projectHours.nonBillableHeadcount" },
  { key: "projectHours-billableHc", label: "Billable Headcount", indent: 1, kind: "line", dataKey: "projectHours.billableHeadcount" },
  { key: "projectHours-nonBillablePct", label: "Non-Billable %", indent: 1, kind: "line", dataKey: "projectHours.nonBillablePct", isPercent: true },
  { key: "projectHours-billablePct", label: "Billable %", indent: 1, kind: "line", dataKey: "projectHours.billablePct", isPercent: true },
  { key: "projectHours-available", label: "Hours available", indent: 1, kind: "line", dataKey: "projectHours.available" },
  { key: "projectHours-worked", label: "Hours worked", indent: 1, kind: "line", dataKey: "projectHours.worked" },
  { key: "projectHours-utilization", label: "Utilization", indent: 1, kind: "line", dataKey: "projectHours.utilization", isPercent: true },
  { key: "projectHours-billed", label: "Hours billed", indent: 1, kind: "line", dataKey: "projectHours.billed" },
  { key: "projectHours-billedPerHead", label: "Hours billed / head", indent: 1, kind: "line", dataKey: "projectHours.billedPerHead" },
  { key: "projectHours-padding", label: "Padding %", indent: 1, kind: "line", dataKey: "projectHours.paddingPct", isPercent: true },
  { key: "spacer-16", label: "", indent: 0, kind: "spacer" },

  { key: "billRate", label: "Bill Rate", indent: 0, kind: "band" },
  { key: "billRate-breakEven", label: "Break-even rate", indent: 1, kind: "line", dataKey: "billRate.breakEven" },
  { key: "billRate-perHourBilled", label: "Rate (per hour billed)", indent: 1, kind: "line", dataKey: "billRate.perHourBilled" },
  { key: "billRate-realRate", label: "'Real' rate (per hour worked)", indent: 1, kind: "line", dataKey: "billRate.realRate" },
  { key: "spacer-17", label: "", indent: 0, kind: "spacer" },

  { key: "servicesBillings", label: "Services Billings", indent: 0, kind: "total", dataKey: "revenue.totalServices" },
  { key: "spacer-18", label: "", indent: 0, kind: "spacer" },

  { key: "salesEfficiency", label: "Sales Efficiency", indent: 0, kind: "total", dataKey: "salesEfficiency" },
];
