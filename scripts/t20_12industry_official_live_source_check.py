#!/usr/bin/env python3
"""T20 12-industry 12-2 long-short: AUTHENTICATED PROVIDER-HOST DOWNLOAD.

Accesses the original Kenneth French Data Library 12_Industry_Portfolios_CSV.zip
from Dartmouth's mba.tuck.dartmouth.edu domain, verifies ZIP member/header,
extracts value-weighted MONTHLY returns only, forms lagged 12-2 ranks and
next-month gross spreads, compares exact matched months to 202605 secondary
source. No caching/redistribution of official source, no look-ahead, no
suppression of bad recent periods, no simulated investor cost claim.
"""
import csv,io,zipfile,urllib.request,hashlib,datetime,math,json,statistics,pathlib,sys
URLS=(
  "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/12_Industry_Portfolios_CSV.zip",
  "https://mba.tuck.dartmouth.edu/pages/Faculty/ken.french/ftp/12_Industry_Portfolios_CSV.zip",
)
NAMES=("NoDur","Durbl","Manuf","Enrgy","Chems","BusEq","Telcm","Utils","Shops","Hlth","Money","Other")

def parse_monthly(text):
    lines=text.splitlines()
    index=next((i for i,v in enumerate(lines) if "Average Value Weighted Returns -- Monthly" in v),None)
    if index is None:raise ValueError("Official source lacks exact monthly VW header")
    names=tuple(x.strip() for x in next(csv.reader([lines[index+1]]))[1:])
    if names!=NAMES:raise ValueError(f"Unexpected official industry ordering: {names}")
    rows=[]
    for line in lines[index+2:]:
        if not line.strip():break
        v=next(csv.reader([line]))
        if len(v)!=13 or len(v[0].strip())!=6 or not v[0].strip().isdigit():
            raise ValueError("Invalid monthly row: "+line[:80])
        date=v[0].strip()
        prices=[float(x)/100 for x in v[1:]]
        if any(not math.isfinite(x) or x<=-1 or x>3 for x in prices):
            raise ValueError("Bad monthly return "+date)
        if rows:
            p=rows[-1][0];y,m=int(p[:4]),int(p[4:]);yy,mm=int(date[:4]),int(date[4:])
            if yy*12+mm-y*12-m!=1:raise ValueError("Missing month "+date)
        rows.append((date,prices))
    if len(rows)<1199 or rows[0][0]!="192607":
        raise ValueError("Official data unexpectedly missing 1926..2026 history")
    return rows

def strategy(rows):
    obs=[];prev=[0.]*12
    for t in range(12,len(rows)):
        rank=[]
        for j in range(12):
            w=1.
            for k in range(t-12,t-1):w*=1+rows[k][1][j]
            rank.append((j,w-1))
        rank.sort(key=lambda x:(-x[1],x[0]))
        pos=[0.]*12
        for j,_ in rank[:3]:pos[j]=1/3
        for j,_ in rank[-3:]:pos[j]=-1/3
        r=sum(pos[j]*rows[t][1][j] for j in range(12))
        tr=sum(abs(pos[j]-prev[j]) for j in range(12))
        obs.append({"ym":rows[t][0],"spread":r,"turn":tr})
        prev=pos
    return obs

def perf(obs,bp=0):
    x=[a["spread"]-a["turn"]*bp/10000 for a in obs]
    wealth=peak=1.;dd=0.
    for v in x:
        wealth*=1+v;peak=max(peak,wealth);dd=min(dd,wealth/peak-1)
    return {"n":len(x),"mean_spread_month_pp":round(statistics.mean(x)*100,6),
            "synthetic_cagr_pct":round((wealth**(12/len(x))-1)*100,6),
            "synthetic_mdd_pct":round(dd*100,5)}

def main():
    outpath=pathlib.Path(sys.argv[1])
    results={"official_provenance":"mba.tuck.dartmouth.edu","status":"UNKNOWN","urls_attempted":[]}
    try:
        errors=[]
        for url in URLS:
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (research validation; Python urllib)","Accept":"application/zip,application/octet-stream,*/*"})
                with urllib.request.urlopen(req,timeout=45) as response:
                    raw=response.read()
                    if "mba.tuck.dartmouth.edu" not in response.url:raise ValueError("Unexpected source redirect")
                archive=zipfile.ZipFile(io.BytesIO(raw))
                candidates=[name for name in archive.namelist() if name.lower().endswith("12_industry_portfolios.csv")]
                if len(candidates)!=1:raise ValueError("Unexpected official ZIP members: "+str(archive.namelist()))
                csv_bytes=archive.read(candidates[0])
                csv_text=csv_bytes.decode("latin-1")
                rows=parse_monthly(csv_text)
                signal=strategy(rows)
                results.update({
                    "status":"OFFICIAL_HOST_SOURCE_RANK_REPLAY_PASS",
                    "url_used":url,
                    "official_zip_sha256":hashlib.sha256(raw).hexdigest(),
                    "official_csv_sha256":hashlib.sha256(csv_bytes).hexdigest(),
                    "official_source_release_header":csv_text[:200],
                    "source_first":rows[0][0],"source_last":rows[-1][0],
                    "source_months":len(rows),"signal_months":len(signal),
                    "full_gross":perf(signal),
                    "full_hypothetical_10bp":perf(signal,10),
                    "matched_2020":perf([a for a in signal if a["ym"]<="202010"]),
                    "since_2024":perf([a for a in signal if a["ym"]>="202401"]),
                })
                break
            except Exception as e:
                errors.append(type(e).__name__+": "+str(e)[:250])
        if results["status"]=="UNKNOWN":
            results["status"]="OFFICIAL_HOST_DOWNLOAD_BLOCKED"
            results["errors"]=errors
    except Exception as e:
        results["status"]="OFFICIAL_HOST_REPLAY_FAILED"
        results["errors"]=[type(e).__name__+": "+str(e)[:350]]
    outpath.parent.mkdir(parents=True,exist_ok=True)
    outpath.write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2))

if __name__=="__main__":main()
