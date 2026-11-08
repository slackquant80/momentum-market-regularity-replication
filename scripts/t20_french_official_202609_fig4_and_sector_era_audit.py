#!/usr/bin/env python3
"""Single bounded T20 final official source audit: 12 industries + Mom + FF3.

Data are downloaded transiently from Dartmouth official provider, checksummed,
never checked into repo. 12-industry rules are frozen; Mom ex-post market-state
figure is recomputed from existing T20 script, no optimization or new signals.
"""
import argparse,hashlib,io,json,pathlib,subprocess,sys,tempfile,urllib.request,zipfile,importlib.util,statistics
FILES={
  'industry':'12_Industry_Portfolios_CSV.zip',
  'mom':'F-F_Momentum_Factor_CSV.zip',
  'factors':'F-F_Research_Data_Factors_CSV.zip',
}
ROOT=pathlib.Path(__file__).resolve().parent
URL='https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/'
EXPECTED_LATEST='202609'

def pull(name):
    url=URL+name
    req=urllib.request.Request(url,headers={
        'User-Agent':'Mozilla/5.0 (Research dataset verification)',
        'Accept':'application/zip,application/octet-stream,*/*'})
    with urllib.request.urlopen(req,timeout=50) as response:
        if 'mba.tuck.dartmouth.edu' not in response.url:
            raise ValueError('Unexpected provider redirect: '+response.url)
        raw=response.read()
    z=zipfile.ZipFile(io.BytesIO(raw))
    members=[f for f in z.namelist() if f.lower().endswith('.csv')]
    if len(members)!=1:
        raise ValueError('Expected one CSV in official '+name+': '+str(members))
    data=z.read(members[0])
    if b'202609 CRSP database' not in data[:450]:
        raise ValueError('Expected latest 202609 CRSP database in '+name+': '+repr(data[:160]))
    return {'url':url,'zip_sha256':hashlib.sha256(raw).hexdigest(),
            'csv_sha256':hashlib.sha256(data).hexdigest(),'csv_bytes':data}

def load_module():
    path=ROOT/'t20_12industry_official_live_source_check.py'
    spec=importlib.util.spec_from_file_location('t20_official12',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=pathlib.Path,required=True)
    args=p.parse_args()
    result={'status':'UNKNOWN','official_vintage':'202609','official_source_domain':'mba.tuck.dartmouth.edu'}
    try:
        sources={key:pull(name) for key,name in FILES.items()}
        result['originals']={key:{k:v for k,v in entry.items() if k!='csv_bytes'}
                             for key,entry in sources.items()}
        mod=load_module()
        industry_data=mod.parse_monthly(sources['industry']['csv_bytes'].decode('latin-1'))
        industry=mod.strategy(industry_data)
        eras={
          '1927_1949':('192707','194912'),'1950_1979':('195001','197912'),
          '1980_1999':('198001','199912'),'2000_2019':('200001','201912'),
          '2010_2019':('201001','201912'),'2020_202609':('202001','202609'),
          '2024_202609':('202401','202609')
        }
        result['industry']={
            'monthly_source_rows':len(industry_data),'source_last':industry_data[-1][0],
            'full':mod.perf(industry),
            'full_cost10bp':mod.perf(industry,10),
            'eras':{name:mod.perf([r for r in industry if a<=r['ym']<=b])
                    for name,(a,b) in eras.items()},
        }
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d)
            mom=d/'F-F_Momentum_Factor.csv';mom.write_bytes(sources['mom']['csv_bytes'])
            factors=d/'F-F_Research_Data_Factors.csv';factors.write_bytes(sources['factors']['csv_bytes'])
            script=ROOT/'t20_conditional_mom_panel.py'
            res=subprocess.run([sys.executable,str(script),'--mom',str(mom),'--factors',
                              str(factors),'--vintage',EXPECTED_LATEST],
                              check=True,capture_output=True,text=True,timeout=60)
            info=json.loads(res.stdout)
            if info['n']!=1197 or info['start']!='192701' or info['end']!='202609':
                raise ValueError('Unexpected exact Mom/FF3 shared sample '+str([info['n'],info['start'],info['end']]))
            result['mom_factor_figure4']={
                'common_months':info['n'],'source_start':info['start'],'source_end':info['end'],
                'overall':info['conditional']['all'],
                'calendar_periods':info['figure4_calendar_subperiods'],
                'same_month_market_states':info['figure4_same_month_market_states'],
                'source_mom_sha256':info['mom_file_sha256'],
                'source_factors_sha256':info['factors_file_sha256'],
            }
        result['status']='OFFICIAL_FRENCH_202609_INDUSTRY_AND_MOM_FIG4_PYTHON_REPLAY_PASS'
    except Exception as e:
        result['status']='OFFICIAL_FINAL_AUDIT_FAIL'
        result['error']=type(e).__name__+': '+str(e)[:650]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
