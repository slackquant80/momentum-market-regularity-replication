#!/usr/bin/env python3
"""T20 private candidate original chart from authenticated original 202609 factors.
Gross vendor bytes must be supplied externally; never copied to the repository.
"""
import argparse
import math
from pathlib import Path
from html import escape
from t20_absolute_momentum_longrun import read_source, simulation

def make_chart(rows):
    main,_=simulation(rows,"abs12",10)
    market,_=simulation(rows,"market",10)
    avg=sum(x["weight"] for x in main)/len(main)
    matched,_=simulation(rows,"static",10,avg)
    assert len(main)==len(market)==len(matched)==1191
    def growth_and_dd(path):
        value=peak=1.
        result=[]
        for x in path:
            value*=1+x["ret"]
            peak=max(peak,value)
            result.append((value,value/peak-1))
        return result
    data={"12m absolute momentum":growth_and_dd(main),
          "US market buy & hold":growth_and_dd(market),
          "Exposure-matched static":growth_and_dd(matched)}
    palette={"12m absolute momentum":"#265c82",
             "US market buy & hold":"#b15a37",
             "Exposure-matched static":"#71848f"}
    n=len(main)
    max_log=max(math.log10(max(z[0],1e-12)) for items in data.values() for z in items)
    upper=max(4.,math.ceil(max_log))
    x=lambda i:98+1030*i/(n-1)
    yg=lambda v:365-252*(math.log10(max(v,1e-12)) + 1)/(upper+1)
    yd=lambda v:647+225*v
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="1215" height="765" viewBox="0 0 1215 765">',
       '<rect width="1215" height="765" fill="#fff"/>',
       '<g font-family="Liberation Sans,Arial,sans-serif" fill="#263b4b">',
       '<text x="90" y="43" font-size="23" font-weight="bold">Absolute momentum: nearly a century of market exposure and drawdowns</text>',
       '<text x="90" y="70" font-size="15" fill="#647984">July 1927–September 2026  ·  12-month market sign  ·  10bp per turn  ·  CRSP market and actual Treasury-bill returns</text>']
    colors=list(palette.items())
    for i,(name,c) in enumerate(colors):
        xx=95+i*343
        s.append(f'<line x1="{xx}" y1="99" x2="{xx+37}" y2="99" stroke="{c}" stroke-width="3"/>')
        s.append(f'<text x="{xx+45}" y="104" font-size="15">{escape(name)}</text>')
    for yy in [-1,0,1,2,3,4,5]:
        if yy>upper:continue
        y=365-252*(yy+1)/(upper+1)
        s.append(f'<line x1="98" y1="{y:.1f}" x2="1128" y2="{y:.1f}" stroke="#edf1f3"/>')
        s.append(f'<text x="84" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#647984">10^{yy}</text>')
    for dd in [-1,-.75,-.5,-.25,0]:
        y=yd(dd)
        s.append(f'<line x1="98" y1="{y:.1f}" x2="1128" y2="{y:.1f}" stroke="#edf1f3"/>')
        s.append(f'<text x="84" y="{y+4:.1f}" text-anchor="end" font-size="12" fill="#647984">{dd*100:.0f}%</text>')
    s.append('<text x="98" y="135" font-size="16" font-weight="bold">Compounded wealth of $1 (logarithmic scale)</text>')
    s.append('<text x="98" y="411" font-size="16" font-weight="bold">Underwater drawdown from preceding high</text>')
    for year in [1930,1950,1970,1990,2010,2026]:
        mid=f"{year}01" if year!=2026 else "202609"
        i=min(range(n),key=lambda k:abs(int(main[k]["month"][:4])*12+int(main[k]["month"][4:])-(int(mid[:4])*12+int(mid[4:]))))
        xx=x(i)
        s.append(f'<line x1="{xx:.1f}" y1="152" x2="{xx:.1f}" y2="647" stroke="#e4e9ec" stroke-dasharray="3 5"/>')
        s.append(f'<text x="{xx:.1f}" y="676" text-anchor="middle" font-size="13">{year}</text>')
    for name,values in data.items():
        color=palette[name]
        upper_path=" ".join(f"{x(i):.1f},{yg(v[0]):.1f}" for i,v in enumerate(values))
        dd_path=" ".join(f"{x(i):.1f},{yd(v[1]):.1f}" for i,v in enumerate(values))
        s.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="{upper_path}"/>')
        s.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.0" points="{dd_path}"/>')
    s.append('<text x="98" y="712" font-size="13" fill="#647984">Source: author calculations on the original Kenneth French September 2026 monthly 3-factor CSV (verified source hash).</text>')
    s.append('<text x="98" y="735" font-size="13" fill="#647984">Historical research market, not tradable SPY; monthly signal-to-return idealization; static control equity weight equals the ex-post average.</text>')
    s.append('</g></svg>')
    return "\n".join(s)+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True,type=Path)
    p.add_argument("--svg",required=True,type=Path)
    opt=p.parse_args()
    rows,_=read_source(opt.csv)
    svg=make_chart(rows)
    opt.svg.parent.mkdir(exist_ok=True,parents=True)
    opt.svg.write_text(svg,encoding="utf-8")
    print("Candidate SVG",opt.svg,"bytes",len(svg))
if __name__=="__main__":main()
