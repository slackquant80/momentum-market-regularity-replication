#!/usr/bin/env python3
"""T20: independent long-history own-trend long-equity/long-bills evidence.

Input must be byte-identical to the Kenneth French 202609 original 3-factor
monthly CSV. Do not commit, publish, or upload the provider's raw CSV.
Research-market and bill proxies are not executable historical ETF accounts.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import stdev

PINNED_SHA256 = "a3894d74d553cab812eabbe706bdbf443c97eb20b24b05e3e5f3ce47e46b90bb"
PERIODS = [
    ("1927-1949","192707","194912"),("1950-1979","195001","197912"),
    ("1980-1999","198001","199912"),("2000-2019","200001","201912"),
    ("2020-2026","202001","202609"),
]
CRISES = [
    ("1929-1932","192909","193212"),("1973-1974","197301","197412"),
    ("1987","198701","198712"),("2000-2002","200001","200212"),
    ("2007-2009","200701","200912"),("2020","202001","202012"),
    ("2022","202201","202212"),
]

def read_source(path):
    raw=path.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest != PINNED_SHA256: raise ValueError(f"Original 202609 data SHA256 mismatch: {digest}")
    lines=raw.decode("utf-8-sig").splitlines()
    if "This file was created using the 202609 CRSP database." not in lines[0]:
        raise ValueError("Wrong archived source vintage")
    start=next(i for i,v in enumerate(lines) if v.strip()==",Mkt-RF,SMB,HML,RF")
    rows=[]
    for line in lines[start+1:]:
        if not line.strip(): break
        cells=next(csv.reader([line]))
        if len(cells)!=5 or not re.fullmatch(r"\d{6}",cells[0].strip()):
            raise ValueError("Malformed monthly row")
        mm=cells[0].strip()
        market=(float(cells[1])+float(cells[4]))/100
        bill=float(cells[4])/100
        if not all(math.isfinite(z) and z>-1 for z in (market,bill)):
            raise ValueError("Impossible source return")
        rows.append(dict(month=mm,market=market,bill=bill))
    if len(rows)!=1203 or rows[0]["month"]!="192607" or rows[-1]["month"]!="202609":
        raise ValueError("Unexpected 192607-202609 monthly coverage")
    for x,y in zip(rows,rows[1:]):
        a,b=x["month"],y["month"]
        if (int(b[:4])*12+int(b[4:]))-(int(a[:4])*12+int(a[4:]))!=1:
            raise ValueError("Missing/duplicated monthly period")
    return rows,digest

def sign(rows,t,lookback=12,reference="zero"):
    # Strictly at completed month t-1; realization uses t.
    growth=math.prod(1+rows[k]["market"] for k in range(t-lookback,t))
    baseline=(math.prod(1+rows[k]["bill"] for k in range(t-lookback,t))
              if reference=="bills" else 1.)
    return int(growth>baseline)

def performance(series):
    if not series: raise ValueError("Empty evaluation path")
    value=peak=1.
    mdd=0.;trough=None;underwater=run=longest=0
    for x in series:
        value*=1+x["ret"]
        peak=max(peak,value)
        dd=value/peak-1
        if dd<mdd: mdd=dd;trough=x["month"]
        if value < peak-1e-12:
            underwater+=1;run+=1;longest=max(longest,run)
        else: run=0
    n=len(series)
    avg=sum(x["ret"] for x in series)/n
    vol=stdev(x["ret"] for x in series)*math.sqrt(12) if n>1 else 0.
    excess=sum(x["ret"]-x["bill"] for x in series)/n
    cagr=value**(12/n)-1
    return dict(months=n,from_month=series[0]["month"],through_month=series[-1]["month"],
                cagr_pct=100*cagr,vol_pct=100*vol,sharpe=12*excess/vol if vol else None,
                mdd_pct=100*mdd,calmar=cagr/abs(mdd) if mdd else None,
                longest_underwater_months=longest,underwater_fraction=underwater/n,
                maxdd_trough=trough,end_wealth=value)

def simulation(rows,rule,side_bp=10,static_weight=None):
    previous_weight=0.
    previous_market_bill=None
    path=[];turn=0.
    for t in range(12,len(rows)):
        if rule=="abs12": wt=sign(rows,t)
        elif rule=="abs6":wt=sign(rows,t,6)
        elif rule=="relative12":wt=sign(rows,t,12,"bills")
        elif rule=="lag12":wt=sign(rows,t-1) if t>12 else 0
        elif rule=="market":wt=1.
        elif rule=="bills":wt=0.
        elif rule=="static":wt=float(static_weight)
        else:raise ValueError(rule)
        x=rows[t]
        if rule=="static" and previous_market_bill is not None:
            pm,pb=previous_market_bill["market"],previous_market_bill["bill"]
            post_return_weight=previous_weight*(1+pm)/(1+previous_weight*pm+(1-previous_weight)*pb)
            turnover=abs(wt-post_return_weight)
        else:
            turnover=abs(wt-previous_weight)
        r=wt*x["market"]+(1-wt)*x["bill"]-(side_bp/10000)*turnover
        path.append(dict(month=x["month"],ret=r,bill=x["bill"],market=x["market"],
                         weight=wt,turnover=turnover))
        previous_weight=wt
        previous_market_bill=x
        turn+=turnover
    return path,dict(mean_equity_exposure=sum(x["weight"] for x in path)/len(path),
                     annual_turnover=12*turn/len(path),
                     switches=sum(x["turnover"]>.5 for x in path) if rule!="static" else None)

def analyze(rows):
    modes=[
        ("abs12_10bp","abs12",10,None),("market_10bp","market",10,None),
        ("bills","bills",0,None),("fixed80_10bp","static",10,.8),
        ("abs12_0bp","abs12",0,None),("abs12_20bp","abs12",20,None),
        ("abs6_10bp","abs6",10,None),("relative12_10bp","relative12",10,None),
        ("lag12_10bp","lag12",10,None),
    ]
    paths={};meta={}
    for name,mode,bp,static in modes:
        paths[name],meta[name]=simulation(rows,mode,bp,static)
    avg_weight=meta["abs12_10bp"]["mean_equity_exposure"]
    paths["matched_exposure_10bp"],meta["matched_exposure_10bp"]=simulation(rows,"static",10,avg_weight)
    headline={name:{**performance(path),**meta[name]} for name,path in paths.items()}
    periods={}
    for name,start,end in PERIODS:
        periods[name]={mode:performance([x for x in paths[mode] if start<=x["month"]<=end])
            for mode in ("abs12_10bp","market_10bp","matched_exposure_10bp")}
    events=[]
    for name,start,end in CRISES:
        active=[x for x in paths["abs12_10bp"] if start<=x["month"]<=end]
        static=[x for x in paths["market_10bp"] if start<=x["month"]<=end]
        ret=lambda arr:100*(math.prod(1+x["ret"] for x in arr)-1)
        events.append(dict(window=name,months=len(active),strategy_return_pct=ret(active),
                           market_return_pct=ret(static),
                           risk_off_months=sum(x["weight"]==0 for x in active),
                           switches=sum(x["turnover"]>.5 for x in active)))
    # Overlapping ten-year windows are descriptive ONLY; not independent observations.
    rolling=[]
    strategy=paths["abs12_10bp"];buy=paths["market_10bp"];fixed=paths["matched_exposure_10bp"]
    for end in range(119,len(strategy)):
        a=performance(strategy[end-119:end+1])
        b=performance(buy[end-119:end+1])
        c=performance(fixed[end-119:end+1])
        rolling.append(dict(end=strategy[end]["month"],
                            rule_cagr=a["cagr_pct"],market_cagr=b["cagr_pct"],matched_cagr=c["cagr_pct"],
                            rule_mdd=a["mdd_pct"],market_mdd=b["mdd_pct"],matched_mdd=c["mdd_pct"]))
    return {
      "status":"PRIVATE_RESEARCH_CANDIDATE__NOT_YET_MANUSCRIPT_ADOPTED",
      "original_source":{"provider":"Kenneth French; 202609 CRSP F-F Research Data Factors monthly",
                         "original_csv_sha256":PINNED_SHA256,"source_months":len(rows),
                         "first_source_month":rows[0]["month"],"last_source_month":rows[-1]["month"],
                         "first_eval_month":paths["abs12_10bp"][0]["month"],
                         "last_eval_month":paths["abs12_10bp"][-1]["month"],
                         "raw_provider_data_redistributed":False},
      "scientific_contract":{"rule":"previous 12 completed market total monthly returns compounded >0; invest next month in market else bill",
                            "market":"Mkt-RF + RF","cash":"Actual historical monthly RF",
                            "monthly_information_clock":"idealized end-of-month information to next monthly return; next-session executable timing not proven",
                            "cost":"10bp per unit absolute weight turnover, first entry charged; 0/20bp sensitivity",
                            "baselines":"market, bills, fixed 80/20, ex-post mean-equity-weight matched static; matched is not ex ante",
                            "risks":"CRSP historical proxy not actual ETF; fixed cost is illustrative; unobserved actual investor behavior"},
      "full_sample":headline,"calendar_partitions":periods,"crisis_windows":events,
      "rolling_10y":{
        "overlapping_windows":len(rolling),
        "fraction_rule_cagr_gt_market":sum(x["rule_cagr"]>x["market_cagr"] for x in rolling)/len(rolling),
        "fraction_rule_mdd_gt_market":sum(x["rule_mdd"]>x["market_mdd"] for x in rolling)/len(rolling),
        "fraction_rule_cagr_gt_matched":sum(x["rule_cagr"]>x["matched_cagr"] for x in rolling)/len(rolling),
        "fraction_rule_mdd_gt_matched":sum(x["rule_mdd"]>x["matched_mdd"] for x in rolling)/len(rolling),
        "worst_rule_cagr_pct":min(x["rule_cagr"] for x in rolling),
        "worst_market_cagr_pct":min(x["market_cagr"] for x in rolling),
        "worst_rule_mdd_pct":min(x["rule_mdd"] for x in rolling),
        "disclaimer":"120-month windows overlap substantially; these are not independent success trials"},
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    rows,digest=read_source(args.csv)
    report=analyze(rows)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"verified_sha256":digest,"source":report["original_source"],
        "full_sample":report["full_sample"],"rolling_10y":report["rolling_10y"]},indent=2))
if __name__=="__main__":main()
