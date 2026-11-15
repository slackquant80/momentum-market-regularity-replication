#!/usr/bin/env python3
"""Figure 6: contiguous, non-overlapping periods from authenticated French 202609 replay.

The exact source-host September 2026 CSV was parsed and the fixed 12-2 industry
strategy rerun in archived GitHub Actions run 41792780016 (2026-11-04). The
source hashes and six-decimal period means are frozen in a separate receipt.
This plot regenerates that already independently executed official-source run;
it does not claim a successful re-download on November 15.
"""
import json
import pathlib
from html import escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "provenance/figure6_contiguous_official_202609_replay.json"
OUT = ROOT / "exhibits/t20_fig06_industry_contiguous_1927_202609_VERIFIED.svg"

def make_svg(data):
    old = data["periods"]
    latest = data["recent_period"]
    assert sum(row["n"] for row in old) + latest["n"] == data["full"]["n"] == 1191
    assert data["status"] == "EXACT_202609_PROVIDER_HOST_MONTHLY_STRATEGY_REPLAY_PASS_ARCHIVED"
    assert data["verification_run_id"] == 41792780016
    value = latest["mean_month_pp"]
    weighted = (data["full"]["n"] * data["full"]["mean_month_pp"]
                - sum(row["n"] * row["mean_month_pp"] for row in old)) / latest["n"]
    assert abs(weighted - value) < 0.000015, (weighted, value)
    assert latest["from"] == "202001" and latest["to"] == "202609"
    assert all(row["mean_month_pp"] > 0 for row in old)
    rows = old + [{"label":latest["label"],"n":latest["n"],"mean_month_pp":value}]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="780" viewBox="0 0 1180 780">',
             '<rect width="1180" height="780" fill="white"/>',
             '<g font-family="Liberation Serif,serif" fill="#243744">',
             '<text x="52" y="57" font-size="28" font-weight="bold">US industry momentum: contiguous historical periods, 1927–2026</text>',
             '<text x="52" y="88" font-size="18">12–2 month ranking · twelve value-weighted U.S. industries · long top three, short bottom three</text>',
             '<text x="52" y="120" font-size="15" fill="#647984">Author calculations · official French 202609 vintage · archived direct-source replay</text>',
             '<text x="53" y="168" font-size="18" font-weight="bold">Historical period</text>',
             '<text x="425" y="168" font-size="18" font-weight="bold">Mean monthly winner-minus-loser spread (percentage points)</text>',
             '<line x1="440" y1="188" x2="440" y2="580" stroke="#a4b2bc" stroke-width="1.6"/>']
    for i,row in enumerate(rows):
        y = 208 + 74*i
        v = row["mean_month_pp"]
        width = 680*v
        parts += [f'<text x="53" y="{y+23}" font-size="20">{escape(row["label"])}</text>',
                  f'<text x="280" y="{y+22}" font-size="15" fill="#70808d">n={row["n"]}</text>',
                  f'<rect x="440" y="{y}" width="{width:.2f}" height="35" fill="#467d91"/>',
                  f'<text x="{440+width+14:.2f}" y="{y+24}" font-size="18">{v:+.3f} pp</text>']
    parts += ['<line x1="50" y1="594" x2="1130" y2="594" stroke="#d2dbe1"/>',
              '<text x="52" y="632" font-size="19" font-weight="bold">Full sample: +0.427 pp/month over 1,191 months (Jul 1927–Sep 2026)</text>',
              '<text x="52" y="660" font-size="16">2020–2026: +0.769 pp/month, directly replayed on official Sept 2026 source (Nov 4 audit).</text>',
              '<text x="52" y="687" font-size="16">Nested short window Jan 2024–Sep 2026 (33 months): −0.079 pp/month (not an era partition).</text>',
              '<text x="52" y="714" font-size="16">Research gross spreads, not funded net returns; borrowing, financing, execution costs excluded.</text>',
              '<text x="52" y="745" font-size="13" fill="#647984">Provider ZIP/CSV SHA256 recorded; source replay: GitHub Actions 41792780016 (Nov 4, 2026).</text>',
              '<text x="52" y="763" font-size="13" fill="#647984">No selection of favorable or unfavorable subperiod start dates to determine the bar shown.</text>',
              '</g></svg>']
    return "\n".join(parts) + "\n"

if __name__ == "__main__":
    data=json.loads(SOURCE.read_text(encoding="utf-8"))
    svg=make_svg(data)
    OUT.write_text(svg, encoding="utf-8")
    print("CANDIDATE_FIG6_CONTIGUOUS_ERA_PASS", OUT)
