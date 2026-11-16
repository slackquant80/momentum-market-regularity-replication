#!/usr/bin/env python3
"""T20 independent supplementary diagnostics of century own-trend rule.
Do not promote any regime-dependent result to an independent predictive test.
"""
import argparse
import json
import math
from pathlib import Path
from t20_absolute_momentum_longrun import read_source, simulation, performance

def newey_west_mean(a,lags=12):
    n=len(a);mean=sum(a)/n
    centered=[x-mean for x in a]
    longrun=sum(x*x for x in centered)/n
    for lag in range(1,min(lags,n-1)+1):
        gamma=sum(centered[t]*centered[t-lag] for t in range(lag,n))/n
        longrun+=2*(1-lag/(lags+1))*gamma
    if longrun<=0:raise ValueError("Invalid HAC long-run variance")
    se=math.sqrt(longrun/n)
    return {"annual_mean_active_return_pp":1200*mean,"annual_mean_active_se_pp":1200*se,
            "hac12_t":mean/se,
            "annual_mean_active_95pct_normal_ci_pp":[1200*(mean-1.96*se),1200*(mean+1.96*se)],
            "qualification":"conditional HAC estimate for monthly return differences; ex-post average-exposure-matched comparator, not an ex-ante investable strategy"}
def calculate(rows):
    rule,_=simulation(rows,'abs12',10)
    hold,_=simulation(rows,'market',10)
    avg=sum(x['weight'] for x in rule)/len(rule)
    static,_=simulation(rows,'static',10,avg)
    ranges=[('full','192707'),('post1950','195001'),('post1980','198001'),
            ('post2000','200001'),('post2010','201001')]
    windows={}
    for name,start in ranges:
        i=next(j for j,x in enumerate(rule) if x['month']==start)
        a,b,c=rule[i:],hold[i:],static[i:]
        windows[name]={
            "rule":performance(a),"buy_hold":performance(b),"matched_static":performance(c),
            "annual_mean_excess_vs_matched_hac12":newey_west_mean([x['ret']-y['ret'] for x,y in zip(a,c)]),
            "annual_mean_excess_vs_market_hac12":newey_west_mean([x['ret']-y['ret'] for x,y in zip(a,b)])}
    events=[('1929-1932','192909','193212'),('1973-1974','197301','197412'),
            ('1987','198701','198712'),('2000-2002','200001','200212'),
            ('2007-2009','200701','200912'),('2020','202001','202012'),
            ('2022','202201','202212')]
    regimes=[]
    for name,lo,hi in events:
        indices=[i for i,x in enumerate(rule) if lo<=x['month']<=hi]
        exits=[];entries=[];missed_positive_months=0;cash_protection_months=0
        for idx in indices:
            x=rule[idx]
            before=rule[idx-1]['weight'] if idx>0 else 0
            if before==1 and x['weight']==0:exits.append(x['month'])
            if before==0 and x['weight']==1:entries.append(x['month'])
            if x['weight']==0:
                if x['market']>x['bill']:missed_positive_months+=1
                elif x['market']<x['bill']:cash_protection_months+=1
        subset=lambda z:[z[i] for i in indices]
        combine=lambda z:100*(math.prod(1+x['ret'] for x in z)-1)
        regimes.append({
            "window":name,"months":len(indices),
            "risk_off_months":sum(rule[i]['weight']==0 for i in indices),
            "month_of_exit_to_bills":exits,"month_of_reentry_to_market":entries,
            "cash_missed_positive_market_excess_months":missed_positive_months,
            "cash_protected_negative_market_excess_months":cash_protection_months,
            "total_return_pct_rule":combine(subset(rule)),
            "total_return_pct_market":combine(subset(hold)),
            "total_return_pct_matched":combine(subset(static)),
            "scientific_limit":"retrospective window, not a predictive crisis selection or investor behavior measure"})
    return {"status":"INDEPENDENT_PRIVATE_SUPPLEMENT__NOT_MANUSCRIPT_ADOPTED",
            "source_sha256":"a3894d74d553cab812eabbe706bdbf443c97eb20b24b05e3e5f3ce47e46b90bb",
            "method":"match sample using market total returns Mkt-RF+RF and actual monthly bills; 12m lagged positive-return rule; 10bp weight turnover; HAC12 Bartlett on monthly active differences; static comparator weight estimated ex-post",
            "sample_windows":windows,"retrospective_crisis_case_panel":regimes}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    rows,_=read_source(a.csv)
    report=calculate(rows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    f=report['sample_windows']['full']
    print(json.dumps({"HAC12_full_vs_matched":f['annual_mean_excess_vs_matched_hac12'],
                      "HAC12_full_vs_market":f['annual_mean_excess_vs_market_hac12'],
                      "post2010":report['sample_windows']['post2010']['annual_mean_excess_vs_matched_hac12']},indent=2))
if __name__=="__main__":main()
