#!/usr/bin/env python3
"""Deterministic T20 Figure 5, 10y/20y trailing means of gross US Mom.

Uses only externally supplied provider CSV bytes. No data downloads, forecasting,
strategy backtest, optimizer, or unpublished third-party file redistribution.
All windows overlap; displayed positive-window fractions are descriptive only.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date

MONTH = re.compile(r'^\d{6}$')

def parse_mom(path: Path, vintage: str):
    raw = path.read_bytes()
    txt = raw.decode('utf-8-sig', errors='replace')
    if f'using the {vintage} CRSP database' not in txt:
        raise ValueError('Mom input vintage is not the expected frozen CRSP release')
    rows = {}
    for fields in csv.reader(txt.splitlines()):
        if len(fields) != 2 or not MONTH.fullmatch(fields[0].strip()):
            continue
        key = fields[0].strip()
        val = float(fields[1])
        if not math.isfinite(val) or val in (-99.99, -999.0):
            raise ValueError(f'Invalid factor value: {key}')
        if key in rows:
            raise ValueError(f'Duplicate factor month: {key}')
        rows[key] = val
    expected = [f'{y:04d}{m:02d}' for y in range(1927, int(vintage[:4])+1)
                for m in range(1, 13) if y < int(vintage[:4]) or m <= int(vintage[4:])]
    if sorted(rows) != expected:
        raise ValueError('Factor monthly history not contiguous 192701 to vintage')
    return expected, [rows[k] for k in expected], hashlib.sha256(raw).hexdigest()

def roll(x, w):
    return [sum(x[i-w+1:i+1])/w for i in range(w-1,len(x))]

def analyze(months, vals):
    stats = {}
    for w in (120,240):
        means = roll(vals,w)
        pos = sum(v > 0 for v in means)
        negatives = [months[i+w-1] for i,v in enumerate(means) if v <= 0]
        stats[str(w)] = {
            'windows':len(means),'positive_windows':pos,
            'positive_fraction':pos/len(means), 'minimum_mean_pp':min(means),
            'maximum_mean_pp':max(means), 'nonpositive_window_ends':negatives,
        }
    # Complement the heavily overlapping windows with a fixed, disjoint 10y partition.
    blocks = []
    for start in range(0, len(vals) - 119, 120):
        mean = sum(vals[start:start+120]) / 120
        blocks.append({'from':months[start], 'to':months[start+119], 'mean_mom_pp':mean})
    stats['disjoint_120'] = {'complete_blocks':len(blocks),
                            'positive_blocks':sum(b['mean_mom_pp'] > 0 for b in blocks),
                            'blocks':blocks}
    return stats

def draw(path,months,vals,stats):
    plt.rcParams.update({'font.family':'DejaVu Sans', 'svg.fonttype':'none',
                         'svg.hashsalt':'t20-figure5-french-mom-202609-v1',
                         'font.size':11, 'axes.edgecolor':'#64747c',
                         'axes.labelcolor':'#2f4050', 'xtick.color':'#3d4c56',
                         'ytick.color':'#3d4c56'})
    fig,ax=plt.subplots(figsize=(8.3,3.4),dpi=150)
    fig.patch.set_facecolor('white')
    axis_dates=[date(int(k[:4]),int(k[4:]),1) for k in months]
    for w,col,label in [(120,'#344e63','10-year'),(240,'#8c9eac','20-year')]:
        means=roll(vals,w)
        ax.plot(axis_dates[w-1:],means,lw=1.6 if w==120 else 2.15,color=col,
                label=f'{label} mean   |   {100*stats[str(w)]["positive_fraction"]:.1f}% of windows > 0')
    ax.axhline(0,color='#3b3b3b',lw=0.9,ls='--',zorder=0)
    ax.xaxis.set_major_locator(mdates.YearLocator(10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.set_xlim(axis_dates[119],axis_dates[-1])
    ax.set_ylabel('Mean Mom return (% per month)',fontsize=11)
    ax.grid(axis='y',lw=.55,color='#e0e5ea')
    ax.legend(loc='lower right',bbox_to_anchor=(0.99,1.012),frameon=False,fontsize=10.7,ncol=1)
    ax.spines['top'].set_visible(False);ax.spines['right'].set_visible(False)
    ax.tick_params(axis='both',labelsize=10.8)
    fig.subplots_adjust(left=.105,right=.985,bottom=.17,top=.77)
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,format='svg',facecolor='white',
                metadata={'Date':'2026-09-30T00:00:00'})
    plt.close(fig)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mom',type=Path,required=True)
    ap.add_argument('--vintage',default='202609')
    ap.add_argument('--expected-sha256',default=None)
    ap.add_argument('--svg',type=Path,required=True)
    ap.add_argument('--receipt',type=Path,required=True)
    a=ap.parse_args()
    months,vals,h=parse_mom(a.mom,a.vintage)
    if a.expected_sha256 and h!=a.expected_sha256.lower():
        raise ValueError('Mom source SHA256 mismatch')
    stats=analyze(months,vals)
    if len(months)!=1197 or months[-1]!='202609' or months[0]!='192701':
        raise ValueError('Unexpected Figure 5 sample')
    if (stats['120']['positive_windows'] != 983 or stats['240']['positive_windows']!=954
            or stats['disjoint_120']['positive_blocks'] != 8 or stats['disjoint_120']['complete_blocks'] != 9):
        raise ValueError('Figure 5 frozen window-counts changed')
    draw(a.svg,months,vals,stats)
    out={'source_csv_sha256':h,'source_vintage':a.vintage,
         'monthly_source_count':len(months),'source_start':months[0],
         'source_end':months[-1], 'rolling':stats,
         'svg_sha256':hashlib.sha256(a.svg.read_bytes()).hexdigest(),
         'limitations':'Overlapping in-sample backward-looking windows of a gross research factor; not independent observations, out-of-sample forecast accuracy or realized net portfolio returns.'}
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.receipt.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='rolling'},indent=2))
if __name__=='__main__':main()
