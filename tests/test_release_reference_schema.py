#!/usr/bin/env python3
"""Check numerical release gate's frozen reference schema without third-party raw data.

This is a structural regression check, not a scientific/empirical replay.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/"provenance"/"expected_replay.json"
GATE=ROOT/"scripts"/"verify_real_data_release_gate.py"
def main():
    ref=json.loads(REFERENCE.read_text(encoding="utf-8"))
    root=ast.parse(GATE.read_text(encoding="utf-8"))
    matches=[n for n in ast.walk(root) if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=="eras" for t in n.targets)]
    assert len(matches)==1, f"Expected one era dictionary, found {len(matches)}"
    era_spec=ast.literal_eval(matches[0].value)
    observed=set(ref["industry_202609"]["eras"])
    required=set(era_spec)
    assert observed==required, f"Era keys mismatch, absent={sorted(required-observed)}, excess={sorted(observed-required)}"
    assert len(ref["french_202609"]["regions"])==6
    assert ref["french_202609"]["sample"]=={"n":431,"first":"199011","last":"202609"}
    assert ref["aqr_202605"]["sample_n"]==497
    assert ref["industry_202609"]["sample"]["n"]==1191
    assert len(ref["figure4_202609"]["calendar_periods"])==5
    assert len(ref["figure4_202609"]["same_month_market_states"])==4
    assert len(ref["figure6_202609"]["selected_periods"])==5
    assert ref["figure5_202609"]["rolling_120"]["percent"]==91.2
    assert ref["figure5_202609"]["rolling_240"]["percent"]==99.6
    print("PASS: frozen numeric-gate reference schema, all five eras, six regions, AQR and Figure 4-6 cells")

if __name__=="__main__":
    main()
