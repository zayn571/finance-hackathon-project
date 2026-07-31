import monthlyData from "../data/monthlyActuals.json";

/**
 * One derive pass over a set of months.
 *
 * Every percentage and rate is recomputed from the summed dollars for the
 * selected period — never averaged across months — so switching period gives a
 * true period figure rather than a mean of monthly ratios.
 */

export interface ClassSplit {
  dd: number;
  sn: number;
  ops: number;
  syn: number;
}

interface MonthRow {
  month: string;
  monthIndex: number;
  quarter: string;
  workingDays: number;
  billableHeadcount: number;
  nonBillableHeadcount: number;
  revenue: {
    services: ClassSplit;
    software: ClassSplit;
    msp: ClassSplit;
    managedDd: number;
    managedSoc: number;
    synIntercompany: ClassSplit;
  };
  cogs: {
    personnel: ClassSplit;
    travel: ClassSplit;
    intercompany: ClassSplit;
    other: ClassSplit;
  };
  opex: {
    ga: ClassSplit;
    sm: ClassSplit;
    gaPersonnel: ClassSplit;
    smPersonnel: ClassSplit;
  };
  otherExpenses: number;
  otherExpensesAddBack: number;
  bookings: { total: number; dd: number; sn: number; sw: number; msp: number };
  ebitdaAdjustments: { mwe: number };
}

export const MONTHLY = (monthlyData as { monthly: MonthRow[] }).monthly;
export const META = (monthlyData as { meta: { verifiedAnchors: { utilization: number; blendedRate: number; source: string } } }).meta;

const UTILIZATION = META.verifiedAnchors.utilization;
const BLENDED_RATE = META.verifiedAnchors.blendedRate;
const HOURS_PER_DAY = 8;

const r2 = (n: number) => Math.round(n * 100) / 100;
const pct = (a: number, b: number) => (b ? r2((a / b) * 100) : 0);
const sum = <T>(arr: T[], f: (x: T) => number) => arr.reduce((a, x) => a + f(x), 0);

export interface Period {
  key: string;
  label: string;
  months: number[];
}

export const PERIODS: Period[] = [
  { key: "FY26", label: "FY26 year to date", months: [0, 1, 2, 3, 4, 5] },
  { key: "Q1", label: "Q1 FY26", months: [0, 1, 2] },
  { key: "Q2", label: "Q2 FY26", months: [3, 4, 5] },
  ...MONTHLY.map((m) => ({ key: m.month, label: `${m.month} FY26`, months: [m.monthIndex] })),
];

export function derive(monthIdxs: number[]) {
  const ms = MONTHLY.filter((m) => monthIdxs.includes(m.monthIndex));
  if (!ms.length) throw new Error("derive() called with no months");

  // --- Revenue
  const servicesDd = sum(ms, (m) => m.revenue.services.dd);
  const servicesSn = sum(ms, (m) => m.revenue.services.sn);
  const softwareDd = sum(ms, (m) => m.revenue.software.dd);
  const softwareSn = sum(ms, (m) => m.revenue.software.sn);
  const managedDd = sum(ms, (m) => m.revenue.managedDd);
  const managedSoc = sum(ms, (m) => m.revenue.managedSoc);
  const mspSn = sum(ms, (m) => m.revenue.msp.sn);
  const synDd = sum(ms, (m) => m.revenue.synIntercompany.dd);
  const synSn = sum(ms, (m) => m.revenue.synIntercompany.sn);
  const synOther = sum(ms, (m) => m.revenue.synIntercompany.ops + m.revenue.synIntercompany.syn);

  const revenueDd = servicesDd + softwareDd + managedDd + managedSoc + synDd;
  const revenueSn = servicesSn + softwareSn + mspSn + synSn;
  const revenueTotal = revenueDd + revenueSn + synOther;

  // --- COGS
  const payrollDd = sum(ms, (m) => m.cogs.personnel.dd);
  const payrollSn = sum(ms, (m) => m.cogs.personnel.sn);
  const travelDd = sum(ms, (m) => m.cogs.travel.dd);
  const travelSn = sum(ms, (m) => m.cogs.travel.sn);
  const interDd = sum(ms, (m) => m.cogs.intercompany.dd);
  const interSn = sum(ms, (m) => m.cogs.intercompany.sn);
  const marketplaceFees = sum(ms, (m) => m.cogs.other.dd);
  const contractorFees = interDd + interSn;

  const cogsDd = payrollDd + travelDd + marketplaceFees + interDd;
  const cogsSn = payrollSn + travelSn + interSn;
  const cogsTotal = cogsDd + cogsSn;

  // Sub-stream COGS follows each stream's share of its practice revenue.
  const ddStreams = { services: servicesDd, software: softwareDd, managedDd, managedSoc };
  const ddRevExSyn = ddStreams.services + ddStreams.software + ddStreams.managedDd + ddStreams.managedSoc;
  const allocDd = (streamRev: number) => (ddRevExSyn ? (payrollDd * streamRev) / ddRevExSyn : 0);
  const snStreams = { services: servicesSn, software: softwareSn, msp: mspSn };
  const snRevExSyn = snStreams.services + snStreams.software + snStreams.msp;
  const allocSn = (streamRev: number) => (snRevExSyn ? (payrollSn * streamRev) / snRevExSyn : 0);

  const gmDd = revenueDd - cogsDd;
  const gmSn = revenueSn - cogsSn;
  const gmTotal = gmDd + gmSn + synOther;

  // --- Operating expenses. Personnel is lifted out of G&A and S&M so the three
  // buckets read the way the GAAP Analysis tab presents them.
  const gaPersDd = sum(ms, (m) => m.opex.gaPersonnel.dd);
  const gaPersSn = sum(ms, (m) => m.opex.gaPersonnel.sn);
  const gaPersOps = sum(ms, (m) => m.opex.gaPersonnel.ops + m.opex.gaPersonnel.syn);
  const smPersDd = sum(ms, (m) => m.opex.smPersonnel.dd);
  const smPersSn = sum(ms, (m) => m.opex.smPersonnel.sn);
  const smPersOps = sum(ms, (m) => m.opex.smPersonnel.ops + m.opex.smPersonnel.syn);

  const personnelDd = gaPersDd + smPersDd;
  const personnelSn = gaPersSn + smPersSn;
  const personnelOps = gaPersOps + smPersOps;
  const personnelTotal = personnelDd + personnelSn + personnelOps;

  const gaDd = sum(ms, (m) => m.opex.ga.dd) - gaPersDd;
  const gaSn = sum(ms, (m) => m.opex.ga.sn) - gaPersSn;
  const gaOps = sum(ms, (m) => m.opex.ga.ops + m.opex.ga.syn) - gaPersOps;
  const gaTotal = gaDd + gaSn + gaOps;

  const smDd = sum(ms, (m) => m.opex.sm.dd) - smPersDd;
  const smSn = sum(ms, (m) => m.opex.sm.sn) - smPersSn;
  const smOps = sum(ms, (m) => m.opex.sm.ops + m.opex.sm.syn) - smPersOps;
  const smTotal = smDd + smSn + smOps;

  const opexTotal = gaTotal + personnelTotal + smTotal;

  const otherExpenses = sum(ms, (m) => m.otherExpenses);
  const otherAddBack = sum(ms, (m) => m.otherExpensesAddBack);
  const mwe = sum(ms, (m) => m.ebitdaAdjustments.mwe);

  const ebitda = gmTotal - opexTotal;
  const adjEbitda = ebitda + mwe + otherAddBack;

  // --- Bookings
  const bookingsTotal = sum(ms, (m) => m.bookings.total);
  const bookingsDd = sum(ms, (m) => m.bookings.dd);
  const bookingsSn = sum(ms, (m) => m.bookings.sn);

  // --- Hours and rates, anchored on the verified utilization and blended rate.
  const billableHc = ms[0].billableHeadcount;
  const nonBillableHc = ms[0].nonBillableHeadcount;
  const workDays = sum(ms, (m) => m.workingDays);
  const hoursAvailable = billableHc * workDays * HOURS_PER_DAY;
  const hoursWorked = hoursAvailable * UTILIZATION;
  const servicesRevenue = servicesDd + servicesSn;
  const hoursBilled = servicesRevenue / BLENDED_RATE;
  const paddingPct = hoursWorked ? pct(hoursWorked - hoursBilled, hoursWorked) : 0;
  const breakEven = hoursBilled ? (cogsTotal + opexTotal) / hoursBilled : 0;
  const realRate = hoursWorked ? servicesRevenue / hoursWorked : 0;

  return {
    bookings: {
      total: r2(bookingsTotal),
      dd: r2(bookingsDd),
      sn: r2(bookingsSn),
      sw: r2(sum(ms, (m) => m.bookings.sw)),
      msp: r2(sum(ms, (m) => m.bookings.msp)),
    },
    bookingsShare: { dd: pct(bookingsDd, bookingsTotal), sn: pct(bookingsSn, bookingsTotal) },
    revenue: {
      total: r2(revenueTotal),
      dd: {
        total: r2(revenueDd),
        services: r2(servicesDd),
        software: r2(softwareDd),
        managedDd: r2(managedDd),
        managedSoc: r2(managedSoc),
      },
      sn: { total: r2(revenueSn), services: r2(servicesSn), software: r2(softwareSn), msp: r2(mspSn) },
      totalServices: r2(servicesRevenue),
      totalSw: r2(softwareDd + softwareSn),
      totalMsp: r2(managedDd + managedSoc + mspSn),
    },
    cogs: {
      total: r2(cogsTotal),
      payroll: {
        total: r2(payrollDd + payrollSn),
        dd: {
          total: r2(payrollDd),
          services: r2(allocDd(ddStreams.services)),
          software: r2(allocDd(ddStreams.software)),
        },
        managedDd: r2(allocDd(ddStreams.managedDd)),
        managedSecurity: r2(allocDd(ddStreams.managedSoc)),
        sn: {
          total: r2(payrollSn),
          services: r2(allocSn(snStreams.services)),
          software: r2(allocSn(snStreams.software)),
          msp: r2(allocSn(snStreams.msp)),
        },
      },
      travel: { total: r2(travelDd + travelSn), dd: r2(travelDd), sn: r2(travelSn) },
      marketplaceFees: r2(marketplaceFees),
      contractorFees: r2(contractorFees),
      totalDd: r2(cogsDd),
      totalSn: r2(cogsSn),
    },
    grossMargin: {
      total: r2(gmTotal),
      dd: {
        total: r2(gmDd),
        services: r2(servicesDd - allocDd(ddStreams.services)),
        software: r2(softwareDd - allocDd(ddStreams.software)),
      },
      managedDd: r2(managedDd - allocDd(ddStreams.managedDd)),
      managedSecurity: r2(managedSoc - allocDd(ddStreams.managedSoc)),
      sn: {
        total: r2(gmSn),
        services: r2(servicesSn - allocSn(snStreams.services)),
        software: r2(softwareSn - allocSn(snStreams.software)),
        msp: r2(mspSn - allocSn(snStreams.msp)),
      },
    },
    grossMarginPct: {
      total: pct(gmTotal, revenueTotal),
      dd: pct(gmDd, revenueDd),
      ddServices: pct(servicesDd - allocDd(ddStreams.services), servicesDd),
      ddSoftware: pct(softwareDd - allocDd(ddStreams.software), softwareDd),
      managedDd: pct(managedDd - allocDd(ddStreams.managedDd), managedDd),
      managedSecurity: pct(managedSoc - allocDd(ddStreams.managedSoc), managedSoc),
      sn: pct(gmSn, revenueSn),
      snServices: pct(servicesSn - allocSn(snStreams.services), servicesSn),
      snSoftware: pct(softwareSn - allocSn(snStreams.software), softwareSn),
      snMsp: pct(mspSn - allocSn(snStreams.msp), mspSn),
    },
    opex: {
      total: r2(opexTotal),
      ga: { total: r2(gaTotal), dd: r2(gaDd), sn: r2(gaSn), ops: r2(gaOps) },
      personnel: { total: r2(personnelTotal), dd: r2(personnelDd), sn: r2(personnelSn), ops: r2(personnelOps) },
      sm: { total: r2(smTotal), dd: r2(smDd), sn: r2(smSn), ops: r2(smOps) },
    },
    otherExpenses: { total: r2(otherExpenses), ebitdaAddBack: r2(otherAddBack) },
    ebitdaAdjustments: { total: r2(mwe), mwe: r2(mwe) },
    ebitda: r2(ebitda),
    adjEbitda: r2(adjEbitda),
    ebitdaPct: pct(adjEbitda, revenueTotal),
    cogsPlusOpex: { total: r2(cogsTotal + opexTotal), pctRevenue: pct(cogsTotal + opexTotal, revenueTotal) },
    ratios: {
      cogsPctRevenue: pct(cogsTotal, revenueTotal),
      gaPctRevenue: pct(gaTotal, revenueTotal),
      personnelPctRevenue: pct(personnelTotal, revenueTotal),
      smPctRevenue: pct(smTotal, revenueTotal),
      netOperatingIncomeMargin: pct(ebitda, revenueTotal),
    },
    projectHours: {
      nonBillableHeadcount: nonBillableHc,
      billableHeadcount: billableHc,
      nonBillablePct: pct(nonBillableHc, billableHc + nonBillableHc),
      billablePct: pct(billableHc, billableHc + nonBillableHc),
      available: Math.round(hoursAvailable),
      worked: Math.round(hoursWorked),
      utilization: r2(UTILIZATION * 100),
      billed: Math.round(hoursBilled),
      billedPerHead: billableHc ? r2(hoursBilled / billableHc) : 0,
      paddingPct,
    },
    billRate: {
      breakEven: r2(breakEven),
      perHourBilled: r2(BLENDED_RATE),
      realRate: r2(realRate),
    },
    salesEfficiency: smTotal ? r2(bookingsTotal / smTotal) : 0,
  };
}

export type Derived = ReturnType<typeof derive>;
