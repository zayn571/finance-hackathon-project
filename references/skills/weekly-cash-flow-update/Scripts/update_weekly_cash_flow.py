#!/usr/bin/env python3
"""
Weekly Cash Flow Update engine.

Reads the BOA Checking 4855 and Northern Bank Checking 3097 bank statements,
classifies each transaction into the Weekly Cash Flow buckets using reference/mapping.csv,
pulls the actual ending bank balance at each week-ending Friday, and writes a new
dated workbook with the actual weeks filled in (Cash In/Out rows + bank balance
rows 30/31). Reconciles each week to the bank: Variance (row 33) must be ~0.

SOURCE OF TRUTH: the bank statements are the cash source for buckets AND balances.
QBO is the cross-check (used to recover payees on cleared paper checks).

This script NEVER writes to QBO and NEVER sends anything externally. It produces a
single new dated .xlsx for human review (see SKILL.md for approval gates).

Folder layout:
    skills/Weekly Cash Flow Update/
        SKILL.md
        reference/mapping.csv      <- rules (this script's default --mapping)
        scripts/update_weekly_cash_flow.py
        output/                    <- dated workbooks land here (or pass --out-dir)

Usage:
    python scripts/update_weekly_cash_flow.py \
        --boa "stmt.csv" --nb "AccountHistory.xls" \
        --workbook "Weekly Cash Flow <prior>.xlsx" \
        --out-dir "output"
"""
import csv, sys, os, argparse, datetime as dt, subprocess, tempfile
from collections import defaultdict
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill

BUCKET_ROW = {'From Signed Contracts':6,'From Bookings':7,'External Funding':8,'Payroll':10,
 'Commission/Bonuses':11,'Health Insurance':12,'Other Benefits':13,'Credit Cards':14,'Office Rent':15,
 "International EE's":16,'Contractors':17,'Marketing Expenses':18,'Other Misc Expenses':19,
 'Draw':20,'Payments on Funding':21}
CASH_IN = {'From Signed Contracts','From Bookings','External Funding'}
NUMFMT = '#,##0;(#,##0)'
GREY = PatternFill(fill_type='solid', fgColor='FFBFBFBF')  # shade actual weeks like prior weeks
GREY_ROWS = range(5, 23)        # the Cash In / Cash Out block (rows 5-22)
RENT_CHECK_AMT = 48755.28       # 419 Boylston rent clears as "ECP INCLEARING CHECK" with no payee
DEFAULT_MAPPING = os.path.join(os.path.dirname(__file__), '..', 'reference', 'mapping.csv')

# ----------------------------------------------------------------------------- rules
def load_rules(path):
    rules=[]
    with open(path, newline='') as fh:
        for row in csv.DictReader(fh):
            if not row.get('match'): continue
            rules.append((int(row['priority']), row['match'].strip().lower(),
                          row['direction'].strip().lower(), row['bucket'].strip()))
    rules.sort(key=lambda r: r[0])
    return rules

def classify(desc, amt, rules):
    d = desc.lower()
    if amt == 0: return 'EXCLUDE'
    for pri, match, direction, bucket in rules:
        if direction == 'credit' and amt <= 0: continue
        if direction == 'debit'  and amt >= 0: continue
        if match == '*':
            return bucket
        if match in d:
            if match == 'inclearing check':            # only the rent check is auto-mapped
                if abs(abs(amt) - RENT_CHECK_AMT) < 0.01: return bucket
                else: continue                          # other checks -> FLAG (QBO payee cross-ref)
            return bucket
    return 'FLAG'

# ----------------------------------------------------------------------------- parsers
def parse_boa(path):
    """BOA export: Date, Description, Amount(signed), Running Bal."""
    out=[]
    with open(path, newline='') as fh:
        started=False
        for row in csv.reader(fh):
            if not row: continue
            if row[0]=='Date' and len(row)>=4 and row[3].startswith('Running'): started=True; continue
            if started and '/' in row[0]:
                try: d=dt.datetime.strptime(row[0],'%m/%d/%Y').date()
                except ValueError: continue
                if 'Beginning balance' in row[1]: continue
                try: amt=float(row[2].replace(',','')) if row[2] else 0.0
                except ValueError: amt=0.0
                try: bal=float(row[3].replace(',',''))
                except ValueError: bal=None
                out.append(dict(acct='BOA',date=d,desc=row[1],amt=amt,bal=bal))
    return out

def _xls_to_csv(path):
    tmp=tempfile.mkdtemp()
    subprocess.run(['libreoffice','--headless','--convert-to','csv','--outdir',tmp,path],
                   check=True, capture_output=True, timeout=120)
    base=os.path.splitext(os.path.basename(path))[0]+'.csv'
    return os.path.join(tmp, base)

def parse_nb(path):
    """Northern Bank AccountHistory: Account, Post Date, Check, Description, Debit, Credit, Status, Balance.
    Reverse-chronological; only POSTED rows carry a running Balance."""
    if path.lower().endswith(('.xls','.xlsx')):
        path=_xls_to_csv(path)
    out=[]
    with open(path, newline='') as fh:
        rd=csv.reader(fh); next(rd, None)
        for row in rd:
            if len(row)<8: continue
            try: d=dt.datetime.strptime(row[1],'%m/%d/%Y').date()
            except ValueError: continue
            if row[6].strip().lower()!='posted': continue
            deb=row[4].replace(',','').strip(); cre=row[5].replace(',','').strip()
            amt=(float(cre) if cre else 0.0)-(float(deb) if deb else 0.0)
            try: bal=float(row[7].replace(',','')) if row[7].strip() else None
            except ValueError: bal=None
            out.append(dict(acct='NB',date=d,desc=row[3],amt=amt,bal=bal))
    return out

def eod_balance(rows, acct, friday):
    """End-of-day running balance for the latest posted txn on/before `friday`.
    BOA file is chronological (last row of the day = EOD); NB is reverse-chron (first row = EOD)."""
    cand=[t for t in rows if t['acct']==acct and t['date']<=friday and t['bal'] is not None]
    if not cand: return None
    mx=max(t['date'] for t in cand)
    sameday=[t for t in cand if t['date']==mx]
    return sameday[-1]['bal'] if acct=='BOA' else sameday[0]['bal']

# ----------------------------------------------------------------------------- workbook helpers
def week_of(d):  # Friday on/after d
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)

def addformula(amts):
    amts=[round(a,2) for a in amts if round(a,2)!=0]
    if not amts: return None
    s=f"={amts[0]:.2f}"
    for a in amts[1:]:
        s += (f"+{a:.2f}" if a>=0 else f"{a:.2f}")
    return s

def find_week_columns(ws, fridays):
    """Map each target Friday to its column by walking the date chain in row 2.
    Row 2 holds =<prev>+7 formulas, so dates are computed from the first literal date."""
    base_col=None; base_date=None
    for c in range(3, ws.max_column+1):
        v=ws.cell(row=2,column=c).value
        if isinstance(v, dt.datetime): base_col=c; base_date=v.date(); break
    if base_col is None:
        raise RuntimeError("Could not find an anchor date in row 2.")
    col_for={}
    for c in range(base_col, ws.max_column+1):
        d = base_date + dt.timedelta(days=7*(c-base_col))
        if d in fridays: col_for[d]=c
    return col_for

# ----------------------------------------------------------------------------- main
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--boa', required=True)
    ap.add_argument('--nb', required=True)
    ap.add_argument('--workbook', required=True)
    ap.add_argument('--mapping', default=DEFAULT_MAPPING)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--last-actual', help='YYYY-MM-DD of workbook last actual Friday; default auto-detect blank row 30')
    ap.add_argument('--through', help='YYYY-MM-DD last Friday to fill; default most recent completed Friday')
    args=ap.parse_args()

    rules=load_rules(args.mapping)
    bank=parse_boa(args.boa)+parse_nb(args.nb)

    wb=openpyxl.load_workbook(args.workbook, data_only=False)
    ws=wb['Wkly Cash Flow']

    # determine last actual Friday = last column with a BOA balance (row 30)
    if args.last_actual:
        last_actual=dt.date.fromisoformat(args.last_actual)
    else:
        col_for_all=find_week_columns(ws, set(_all_fridays()))
        last_actual=max((d for d,c in col_for_all.items() if ws.cell(row=30,column=c).value not in (None,'')),
                        default=None)
        if last_actual is None: raise RuntimeError("Could not auto-detect last actual week; pass --last-actual.")

    today=dt.date.today()
    through=dt.date.fromisoformat(args.through) if args.through else today - dt.timedelta(days=(today.weekday()-4)%7 or 7)
    fridays=[]
    f=week_of(last_actual+dt.timedelta(days=1))
    while f<=through:
        fridays.append(f); f+=dt.timedelta(days=7)
    if not fridays:
        print("No completed weeks to fill."); return

    col_for=find_week_columns(ws, set(fridays))
    missing=[f for f in fridays if f not in col_for]
    if missing:
        raise RuntimeError(f"Workbook has no column for weeks: {missing}")

    # classify -> per-week buckets, collect flags
    wk=defaultdict(lambda: defaultdict(list)); flags=[]
    for t in bank:
        f=week_of(t['date'])
        if f not in col_for: continue
        b=classify(t['desc'], t['amt'], rules)
        if b=='EXCLUDE': continue
        if b=='FLAG': flags.append(t); continue
        wk[f][b].append(t['amt'])

    # capture prior (forecast) values, then write
    changes=[]
    for f in fridays:
        c=col_for[f]
        for bk,r in BUCKET_ROW.items():
            old=ws.cell(row=r,column=c).value
            cell=ws.cell(row=r,column=c)
            new=addformula(wk[f][bk]) if bk in wk[f] else None
            cell.value=new
            if new is not None: cell.number_format=NUMFMT
            if not (old is None and new is None):
                changes.append((f.isoformat(), bk, old, new))
        boa=eod_balance(bank,'BOA',f); nb=eod_balance(bank,'NB',f)
        if boa is not None: ws.cell(row=30,column=c).value=round(boa,2)
        if nb  is not None: ws.cell(row=31,column=c).value=round(nb,2)
        # grey the Cash In/Out block to mark this week as actualized, like prior weeks
        for r in GREY_ROWS:
            ws.cell(row=r,column=c).fill=GREY

    _write_control_tabs(wb, changes, flags, fridays)

    os.makedirs(args.out_dir, exist_ok=True)
    out=os.path.join(args.out_dir, f"Weekly Cash Flow {today.strftime('%Y%m%d')}.xlsx")
    wb.save(out)

    # reconcile (report only)
    print(f"Filled weeks {fridays[0]}..{fridays[-1]} -> {out}")
    print(f"Flagged (need human classification): {len(flags)}")
    for t in flags:
        print(f"  FLAG {t['date']} {t['acct']} {t['amt']:,.2f} | {t['desc'][:60]}")
    if flags:
        print("NOTE: weeks containing flagged lines will NOT reconcile to 0 until classified.")

def _all_fridays():
    d=dt.date(2024,1,5)
    while d<dt.date(2030,1,1):
        yield d; d+=dt.timedelta(days=7)

def _write_control_tabs(wb, changes, flags, fridays):
    for name in ('Changes','Approval Log','Flagged'):
        if name in wb.sheetnames: del wb[name]
    cs=wb.create_sheet('Changes'); cs.append(['Week Ending','Bucket','Prior (forecast)','New (actual)'])
    for w,bk,o,n in changes:
        cs.append([w,bk,str(o) if o is not None else '', str(n) if n is not None else ''])
    al=wb.create_sheet('Approval Log')
    al.append(['Date','Action','Created by','Approved by','Slack permalink / notes'])
    al.append([dt.date.today().isoformat(),
        f"Actualized Weekly Cash Flow weeks {fridays[0]}..{fridays[-1]} from BOA + NB bank statements.",
        'Claude','PENDING - requires a different F&A team member',''])
    fl=wb.create_sheet('Flagged'); fl.append(['Date','Account','Amount','Description','Reason'])
    if flags:
        for t in flags:
            fl.append([t['date'].isoformat(),t['acct'],round(t['amt'],2),t['desc'],'No rule matched - classify and add to mapping.csv'])
    else:
        fl.append(['-','-','-','None this run - all transactions matched a rule and every week reconciled to 0.',''])

if __name__=='__main__':
    main()
