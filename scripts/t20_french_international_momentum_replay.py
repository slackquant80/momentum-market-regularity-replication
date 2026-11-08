#!/usr/bin/env python3
"""T20: reproducible regional French momentum factor diagnostics.

Supply ONLY official Kenneth French CSV ZIP archives downloaded from
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html.

The study uses published *factor returns*, not underlying security-level portfolio
reconstruction. Never report a synthetic test as empirical evidence. Never silently
combine differing data vintages or infer strategy profitability from factor means.

Example:
 python t20_french_international_momentum_replay.py --source-dir ./official_zip \
     --output ./regional_evidence.json --strict-vintage 202609

Required files: F-F_Momentum_Factor_CSV.zip, Developed_ex_US_Mom_Factor_CSV.zip,
Europe_Mom_Factor_CSV.zip, Japan_Mom_Factor_CSV.zip,
Asia_Pacific_ex_Japan_MOM_Factor_CSV.zip, North_America_Mom_Factor_CSV.zip.
Emerging_Mom_Factor_CSV.zip can be added after confirmation of exact name and period.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path

import numpy as np

DATASETS={
    'US': 'F-F_Momentum_Factor_CSV.zip',
    'Developed ex US': 'Developed_ex_US_Mom_Factor_CSV.zip',
    'Europe': 'Europe_Mom_Factor_CSV.zip',
    'Japan': 'Japan_Mom_Factor_CSV.zip',
    'Asia Pacific ex Japan': 'Asia_Pacific_ex_Japan_MOM_Factor_CSV.zip',
    'North America': 'North_America_Mom_Factor_CSV.zip',
}
MISSING={-99.99,-999.0}

def sha256(content:bytes)->str:
    return hashlib.sha256(content).hexdigest()

def parse_french_csv(content:bytes):
    """Read first monthly 6-digit YYYYMM block; skip prose, daily and annual tables."""
    text=content.decode('latin-1',errors='replace')
    header=text[:1200]
    months={}
    started=False
    for line in csv.reader(io.StringIO(text)):
        if not line:
            if started: break
            continue
        key=line[0].strip()
        if re.fullmatch(r'(?:19|20)\d{4}',key):
            yy,mm=int(key[:4]),int(key[4:])
            if not 1<=mm<=12: raise ValueError(f'Invalid date: {key}')
            values=[]
            for raw in line[1:]:
                try: values.append(float(raw.strip()))
                except (ValueError,TypeError): pass
            if not values: raise ValueError(f'No numeric factor column in {key}')
            # Official monthly Mom-only datasets usually have one factor column.
            # Reject ambiguous multiple columns instead of guessing one.
            if len(values)!=1: raise ValueError(f'Ambiguous factor columns in {key}: {len(values)}')
            v=values[0]
            if v in MISSING or not math.isfinite(v): raise ValueError(f'Missing/invalid factor in {key}')
            if key in months: raise ValueError('Duplicate month '+key)
            months[key]=v/100.0
            started=True
        elif started:
            break
    if len(months)<24:raise ValueError('Expected at least 24 months of factor observations')
    keys=list(months)
    if keys != sorted(keys):raise ValueError('Non-monotonic monthly dates')
    for a,b in zip(keys,keys[1:]):
        ai=int(a[:4])*12+int(a[4:]);bi=int(b[:4])*12+int(b[4:])
        if bi!=ai+1:raise ValueError(f'Gapped monthly factor: {a}, {b}')
    return months,header

def load_zip(path:Path):
    raw=path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv') and not n.startswith('__MACOSX')]
        if len(names)!=1:raise ValueError(f'Expected exactly one CSV: {path.name}, got {names}')
        csv_content=z.read(names[0])
    monthly,head=parse_french_csv(csv_content)
    m=re.search(r'(?:20\d{4})\s+CRSP\s+database',head,re.I)
    vintage=m.group(1) if m and m.lastindex else (m.group(0)[:6] if m else None)
    return monthly, {'zip':path.name,'sha256_zip':sha256(raw),
      'sha256_csv':sha256(csv_content),'csv_name':names[0],
      'header':head[:240].replace('\r',''), 'crsp_vintage':vintage,
      'first':next(iter(monthly)), 'last':next(reversed(monthly)), 'n':len(monthly)}

def hac_t(x,lag=12):
    x=np.asarray(x,dtype=float)
    n=len(x);u=x-x.mean();variance=float(np.dot(u,u)/n)
    for j in range(1,min(lag,n-1)+1):
        variance+=2*(1-j/(lag+1))*float(np.dot(u[j:],u[:-j])/n)
    if variance<=0:return float('nan')
    return float(x.mean()/math.sqrt(variance/n))

def stats(x):
    a=np.asarray(x,dtype=float)
    mu=float(np.mean(a));sigma=float(np.std(a,ddof=1))
    return {'n':len(a),'mean_month_pct':mu*100,
      'annualized_vol_pct':sigma*math.sqrt(12)*100,
      'annualized_mean_over_vol':mu/sigma*math.sqrt(12) if sigma else None,
      'hac12_t':hac_t(a),'positive_month_fraction':float((a>0).mean()),
      'worst_month_pct':float(a.min()*100)}

def calc(data):
    names=list(data)
    common=sorted(set.intersection(*(set(d.keys()) for d in data.values())))
    if len(common)<24:raise ValueError('Not enough overlapping observations')
    for a,b in zip(common,common[1:]):
        if int(b[:4])*12+int(b[4:])!=int(a[:4])*12+int(a[4:])+1:
            raise ValueError('Common sample is not contiguous')
    eras=[('1991-1999','199101','199912'),('2000-2019','200001','201912'),
          ('2020 onward','202001','209912')]
    output={'common_sample':{'n':len(common),'first':common[0],'last':common[-1]},
       'regions':{},'overlapping_geographies':True}
    for name,vals in data.items():
        x=[vals[m] for m in common]
        intervals={label:stats([vals[m] for m in common if begin<=m<=end])
                   for label,begin,end in eras if sum(begin<=m<=end for m in common)>=24}
        rolling=[]
        for j in range(119,len(x)):
            rolling.append(sum(x[j-119:j+1])/120)
        output['regions'][name]={'common':stats(x),
          'rolling_10y_positive_share':sum(v>0 for v in rolling)/len(rolling) if rolling else None,
          'eras':intervals}
    output['interpretation']='Published regional WML factor diagnostics, not original-stock portfolio builds. Regions overlap geographically; not independent repeated experiments. Arithmetic Mom factor return cannot be assumed to be a tradable net portfolio.'
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--strict-vintage',default=None,help='Require source headers contain this 6-digit release (only when explicit)')
    args=p.parse_args()
    data={};provenance={}
    for name,filename in DATASETS.items():
        path=args.source_dir/filename
        if not path.is_file(): raise FileNotFoundError(f'Missing OFFICIAL ZIP: {path}')
        values,receipt=load_zip(path)
        if args.strict_vintage and args.strict_vintage not in receipt['header']:
            raise ValueError(f'{name}: expected source vintage {args.strict_vintage}; header {receipt["header"]}')
        data[name]=values;provenance[name]=receipt
    result=calc(data)
    result['provenance']=provenance
    result['analysis_vintage']='official original ZIP inputs (SHA256 recorded)'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print(f"PASS: {result['common_sample']['n']} months {result['common_sample']['first']}..{result['common_sample']['last']}; regions {len(data)}")
if __name__=='__main__': main()
