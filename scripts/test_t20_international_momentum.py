from pathlib import Path
import io,zipfile,tempfile,subprocess,sys,json,argparse
from t20_french_international_momentum_replay import parse_french_csv,load_zip,DATASETS,calc

def make_zip(path,data):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('factor.csv',data)

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--us-mom-csv',type=Path,help='Optional exact official French 202609 US Mom CSV to validate actual results')
    args=parser.parse_args()
    if args.us_mom_csv:
        raw=args.us_mom_csv.read_bytes()
    else:
        dates=[f"{y}{m:02d}" for y in range(2022,2026) for m in range(1,13)]
        raw=("This file was created using the 202609 CRSP database.\n,Mom\n"+"".join(f"{d},{0.15+(i%5)*0.22:.2f}\n" for i,d in enumerate(dates))).encode()
    months,header=parse_french_csv(raw)
    if args.us_mom_csv:
        assert len(months)==1197 and list(months)[0]=='192701' and list(months)[-1]=='202609'
        assert abs(sum(months.values())/len(months)*100-0.6178111946532999)<1e-10
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp);z=folder/'official.zip';make_zip(z,raw)
        d,receipt=load_zip(z)
        assert d==months and receipt['first']==next(iter(months)) and receipt['last']==next(reversed(months))
        for name,filename in DATASETS.items():make_zip(folder/filename,raw)
        out=folder/'result.json'
        s=subprocess.run([sys.executable, str(Path(__file__).with_name('t20_french_international_momentum_replay.py')),
                 '--source-dir',str(folder),'--output',str(out),'--strict-vintage','202609'],text=True,capture_output=True)
        assert s.returncode==0,(s.stderr,s.stdout)
        result=json.loads(out.read_text())
        assert len(result['regions'])==len(DATASETS)
        expected=sum(months.values())/len(months)*100
        assert all(abs(z['common']['mean_month_pct']-expected)<1e-10 for z in result['regions'].values())
        first=next(iter(months)).encode()
        bad=raw.replace(first+b',',first+b',  -999.00,',1)
        try:parse_french_csv(bad)
        except ValueError:pass
        else:raise AssertionError('bad column data not rejected')
        second=list(months)[1].encode()
        bad=raw.replace(second+b',',b'202799,',1)
        try:parse_french_csv(bad)
        except ValueError:pass
        else:raise AssertionError('invalid month not rejected')
    print('PASS: '+('official US source replay; ' if args.us_mom_csv else 'synthetic-source parser; ')+'6-region synthetic contract; malformed CSV rejection')

if __name__=='__main__':run()
