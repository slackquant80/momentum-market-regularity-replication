#!/usr/bin/env python3
"""Reproduce T20's independently computed cross-asset AQR TSMOM diagnostics.

Inputs must be fetched and saved separately. The archived May 2026 original
AQR workbook was independently verified against 497 CSV dates / 2,485 factor
return cells in a separate provenance audit (see provenance/pinned_inputs.json).
The matching French FF3 May 2026 archive is separately version-pinned but was
not independently re-downloaded from the provider. This script does not fetch
or redistribute either raw provider dataset, nor overwrite paper figures.
Source:
  AQR: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly
  AQR CSV mirror (2026-05): https://github.com/KonomiYuzu01/HMM/blob/93593ebb62973fc5a26b9c8af176bda90895e29c/data/aqr_tsmom_factors_monthly.csv
  French FF3 mirror (2026-05): https://github.com/BuyRisk/buyrisk.github.io/blob/5d694104e684da74a60f4f46e0a205f5933ab5f2/data/sources/french/F-F_Research_Data_Factors.csv
"""
import argparse, csv, hashlib, json, math, statistics
from pathlib import Path
import numpy as np
import pandas as pd

AQR_EXPECTED_SHA256 = "bef2a5871e2676de25fc25ff1dc1c3b4205604661210f171a38e6c23bd3993f7"
COLUMNS = ["TSMOM", "TSMOM_CM", "TSMOM_EQ", "TSMOM_FI", "TSMOM_FX"]

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read_aqr(p, *, pinned=False):
    if pinned and sha256(p) != AQR_EXPECTED_SHA256:
        raise ValueError("AQR input SHA256 mismatch; not the audited 2026-05 archived CSV")
    data = pd.read_csv(p)
    assert list(data.columns) == ["date"] + COLUMNS
    data["month"] = pd.to_datetime(data["date"]).dt.to_period("M")
    assert data["month"].is_unique and not data[COLUMNS].isna().any().any()
    return data.set_index("month")[COLUMNS].astype(float)

def read_ff3(p):
    rows = []
    with open(p, "r", encoding="latin-1") as f:
        for line in f:
            parts = [x.strip() for x in line.split(",")]
            if len(parts) < 5 or not(parts[0].isdigit() and len(parts[0]) == 6):
                continue
            try:
                month = pd.Period(parts[0], freq="M")
                r = float(parts[1]) / 100
                rf = float(parts[4]) / 100
            except (ValueError, TypeError):
                continue
            rows.append((month, r, rf))
    frame = pd.DataFrame(rows, columns=["month","Mkt_RF","RF"])
    if frame.empty:
        raise ValueError("No FF3 monthly data block found")
    return frame.set_index("month")

def hac_t(x, lag=12):
    z = np.array(x, dtype=float)
    n = len(z)
    u = z - z.mean()
    omega = np.mean(u * u)
    for l in range(1, min(lag, n - 1) + 1):
        omega += 2 * (1 - l/(lag+1)) * np.dot(u[l:], u[:-l]) / n
    return float(z.mean()/math.sqrt(omega/n))

def stats(x):
    z = np.asarray(x, dtype=float)
    return dict(n=len(z), mean_month_percent=float(z.mean()*100),
                annual_vol_percent=float(np.std(z, ddof=1)*np.sqrt(12)*100),
                annual_sharpe=float(z.mean()/np.std(z,ddof=1)*np.sqrt(12)),
                hac12_t=hac_t(z), positive_fraction=float((z>0).mean()))

def run(aqr, ff3):
    x = aqr.join(ff3[["Mkt_RF"]], how="inner").sort_index()
    if len(x)!=497 or str(x.index[0])!="1985-01" or str(x.index[-1])!="2026-05":
        raise ValueError("Expected exact common 1985-01..2026-05, 497-month vintage")
    if not all(x.index[i-1]+1 == x.index[i] for i in range(1,len(x))):
        raise ValueError("Missing monthly observation")
    result={"sample":{"first":str(x.index[0]),"last":str(x.index[-1]),"n":len(x)},
            "factors":{k:stats(x[k]) for k in COLUMNS},
            "market":stats(x["Mkt_RF"])}
    result["subperiods"]={}
    for name,start,end in [("1985_1999","1985-01","1999-12"),
                           ("2000_2019","2000-01","2019-12"),
                           ("2020_2026","2020-01","2026-05")]:
        y=x.loc[start:end]
        result["subperiods"][name]={k:stats(y[k]) for k in COLUMNS}
    result["states"]={}
    for name,sel in [("market_down5",x["Mkt_RF"]<=-.05),
                     ("market_down10",x["Mkt_RF"]<=-.10),
                     ("market_negative",x["Mkt_RF"]<0),
                     ("market_positive",x["Mkt_RF"]>=0),
                     ("market_up5",x["Mkt_RF"]>=.05)]:
        y=x.loc[sel]
        result["states"][name]={"n":len(y),
           "monthly_mean_percent":{k:float(y[k].mean()*100) for k in ["Mkt_RF"]+COLUMNS}}
    result["correlation_with_market"]={
        k:float(x[k].corr(x["Mkt_RF"])) for k in COLUMNS}
    result["hypothetical_mixes"]={}
    for w in [0,.1,.2,.3,.5]:
        y=(1-w)*x["Mkt_RF"]+w*x["TSMOM"]
        result["hypothetical_mixes"][str(w)]=stats(y)
    result["disclaimer"] = (
        "AQR-reported academic hypothetical excess-return series from an archived May 2026 original workbook with independently verified CSV cell parity; "
        "independently computed diagnostics, not independently constructed futures strategies. "
        "Monthly same-month market states are ex post. Blend is illustrative and ignores trading, "
        "financing, leverage and implementation details. Archived original May 2026 AQR XLSX/CSV byte-and-cell parity is verified; the current provider download and May 2026 French FF3 provider-byte parity were not independently verified."
    )
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aqr",required=True,type=Path)
    parser.add_argument("--ff3",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--pin-aqr-sha256",action="store_true")
    args=parser.parse_args()
    obj=run(read_aqr(args.aqr,pinned=args.pin_aqr_sha256),read_ff3(args.ff3))
    obj["input_sha256"]={"aqr":sha256(args.aqr),"ff3":sha256(args.ff3)}
    args.out.write_text(json.dumps(obj,indent=2),encoding="utf8")
    print(json.dumps({"n":obj["sample"]["n"],"marketDown5":obj["states"]["market_down5"]["n"],
                      "tsmomMean":obj["factors"]["TSMOM"]["mean_month_percent"]},indent=2))
if __name__=="__main__":
    main()
