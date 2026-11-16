#!/usr/bin/env python3
"""Offline synthetic own-trend signal/clock check and frozen scientific receipt consistency.

No historic provider original 202609 raw data are shipped or falsely replayed.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from t20_absolute_momentum_longrun import sign, simulation, performance

def check():
    # 12 positive formation months, then a large return reversal.
    rows=[dict(month=f"2000{i+1:02}",market=.02,bill=.001) for i in range(12)]
    rows += [dict(month="200101",market=-.85,bill=.001),
             dict(month="200102",market=.12,bill=.001)]
    assert sign(rows,12)==1, "Signal at first scored month must look backward only"
    assert sign(rows,13)==0, "After a completed severe decline, exit to bills"
    path, meta=simulation(rows,"abs12",10)
    assert len(path)==2 and path[0]["weight"]==1 and path[1]["weight"]==0
    assert abs(path[0]["ret"]-(-.851))<1e-12, path[0] # -85% less 10bp entry
    assert abs(path[1]["ret"]-0.)<1e-12, path[1]       # +0.1% bill less 10bp exit
    assert abs(path[0]["turnover"]-1)<1e-12 and abs(path[1]["turnover"]-1)<1e-12
    assert meta["switches"]==2 and meta["mean_equity_exposure"]==.5
    gain=performance(path)
    assert gain["months"]==2 and gain["mdd_pct"]<0 and gain["cagr_pct"]<0

    p=ROOT/"provenance"/"t20_absolute_momentum_202609_source_locked_results.json"
    r=json.loads(p.read_text())
    assert r["original_source"]["source_months"]==1203
    assert r["original_source"]["first_eval_month"]=="192707"
    assert r["original_source"]["last_eval_month"]=="202609"
    assert r["original_source"]["original_csv_sha256"]=="a3894d74d553cab812eabbe706bdbf443c97eb20b24b05e3e5f3ce47e46b90bb"
    assert r["provenance_receipt"]["raw_provider_file_not_committed"] is True
    full=r["full_sample"]
    assert full["abs12_10bp"]["months"]==1191
    checks=[("abs12_10bp","cagr_pct",10.21914739),
            ("abs12_10bp","mdd_pct",-44.50462630),
            ("abs12_10bp","mean_equity_exposure",.755667506),
            ("market_10bp","cagr_pct",10.26388662),
            ("market_10bp","mdd_pct",-83.65224657),
            ("matched_exposure_10bp","cagr_pct",8.85171521),
            ("matched_exposure_10bp","mdd_pct",-73.00072646)]
    for k,field,number in checks:
        assert math.isclose(full[k][field],number,rel_tol=1e-8,abs_tol=1e-6), (k,field)
    p2=ROOT/"provenance"/"t20_absolute_momentum_202609_hac_crisis_results.json"
    d=json.loads(p2.read_text())
    h=d["sample_windows"]["full"]["annual_mean_excess_vs_matched_hac12"]
    assert 1.19<h["hac12_t"]<1.21
    assert h["annual_mean_active_95pct_normal_ci_pp"][0]<0<h["annual_mean_active_95pct_normal_ci_pp"][1]
    recent=d["sample_windows"]["post2010"]
    assert recent["rule"]["cagr_pct"]<recent["matched_static"]["cagr_pct"]
    assert recent["rule"]["mdd_pct"]<recent["matched_static"]["mdd_pct"]
    source=(ROOT/"exhibits"/"t20_fig07_absolute_momentum_1927_202609.svg").read_text()
    assert source.count("<polyline")==6 and "Underwater drawdown" in source
    print("T20_CENTURY_OWN_TREND_SYNTHETIC_CLOCK_AND_FROZEN_SOURCE_METADATA_PASS")
if __name__=="__main__":check()
