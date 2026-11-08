#!/usr/bin/env python3
"""T20 internal descriptive research; requires user-supplied rights-cleared French CSVs.

No downloads, no strategy optimizer, no cash flows, no investable performance.
Input: monthly US Mom and F-F Research Data Factors (Mkt-RF,SMB,HML,RF).
The provider snapshot must be fixed and reconciled before any public paper claim.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET

MONTH = re.compile(r"^\d{6}$")


def load_months(path: Path, columns: int, vintage: str):
    raw = path.read_bytes()
    content = raw.decode("utf-8-sig", errors="replace")
    if f"using the {vintage} CRSP database" not in content:
        raise ValueError(f"{path}: missing expected {vintage} CRSP header")
    months = {}
    for row in csv.reader(content.splitlines()):
        cells = [x.strip() for x in row]
        if len(cells) != columns + 1 or not MONTH.fullmatch(cells[0]):
            continue
        if int(cells[0][4:]) not in range(1, 13):
            raise ValueError(f"invalid YYYYMM {cells[0]}")
        vals = [float(x) for x in cells[1:]]
        if any(not math.isfinite(x) for x in vals):
            raise ValueError(f"nonfinite value {cells[0]}")
        if any(x in (-99.99, -999.0) for x in vals):
            continue
        if cells[0] in months:
            raise ValueError(f"duplicate month {cells[0]}")
        months[cells[0]] = vals
    return months, hashlib.sha256(raw).hexdigest()


def avg(xs):
    return sum(xs) / len(xs) if xs else None


def summarize(panel, condition):
    rows = [r for r in panel if condition(r)]
    return {
        "months": len(rows),
        "mean_mom_pp": avg([r["mom"] for r in rows]),
        "fraction_mom_positive": avg([int(r["mom"] > 0) for r in rows]),
        "mean_market_pct": avg([r["market"] for r in rows]),
    }


def capm(panel):
    x = [r["mkt_rf"] for r in panel]
    y = [r["mom"] for r in panel]
    xm, ym = avg(x), avg(y)
    var = sum((z - xm) ** 2 for z in x)
    beta = sum((a - xm) * (b - ym) for a, b in zip(x, y)) / var
    return {"monthly_intercept_pp": ym - beta * xm, "market_excess_beta": beta}


def verify_figure4(svg_path: Path, vintage: str, periods: dict, states: dict) -> dict:
    """Verify all nine displayed Figure 4 mean/count cells against computed inputs."""
    root = ET.parse(svg_path).getroot()
    svg_text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("text"))
    expected = {
        **periods,
        **states,
    }
    checked = []
    for key, item in expected.items():
        mean = item["mean_mom_pp"]
        count = item["months"]
        if mean is None or count <= 0:
            raise ValueError(f"Figure 4 group {key} has no valid monthly observations")
        label = f"{mean:+.2f}% (n={count})"
        if svg_text.count(label) != 1:
            raise ValueError(f"Figure 4 mismatch in {key}: expected exactly one {label}")
        checked.append({"group": key, "mean_and_n": label})
    if len(checked) != 9:
        raise ValueError(f"Expected exactly nine Figure 4 cells, found {len(checked)}")
    if f"CRSP vintage {vintage}" not in svg_text:
        raise ValueError(f"Figure 4 vintage label does not match {vintage}")
    return {"status": "EXACT_DISPLAY_CELL_MATCH", "cells_checked": checked,
            "svg_sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mom", type=Path, required=True, help="F-F_Momentum_Factor.csv")
    ap.add_argument("--factors", type=Path, required=True, help="F-F_Research_Data_Factors.csv")
    ap.add_argument("--vintage", default="202609", help="expected CRSP database YYYYMM header; requires exact input-vintage verification")
    ap.add_argument("--figure-svg", type=Path, default=None,
                    help="Optional source SVG: fail if any of nine displayed Figure 4 cells differs")
    ap.add_argument("--expected-mom-sha256", type=str, default=None,
                    help="Independently obtained exact provider Mom CSV SHA256; required for provenance PASS")
    ap.add_argument("--expected-factors-sha256", type=str, default=None,
                    help="Independently obtained matching F-F factor CSV SHA256; required for provenance PASS")
    args = ap.parse_args()

    mom, mom_sha = load_months(args.mom, 1, args.vintage)
    factors, factor_sha = load_months(args.factors, 4, args.vintage)
    provided = [args.expected_mom_sha256, args.expected_factors_sha256]
    if any(provided) and not all(provided):
        raise ValueError("Both expected input SHA256 hashes must be supplied together")
    provenance_status = "UNVERIFIED_SOURCE_HEADER_ONLY"
    if all(provided):
        for label, expected, actual in (
            ("Mom", args.expected_mom_sha256, mom_sha),
            ("F-F factors", args.expected_factors_sha256, factor_sha),
        ):
            if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
                raise ValueError(f"{label}: expected SHA256 must be 64 hex digits")
            if expected.lower() != actual:
                raise ValueError(f"{label}: raw input SHA256 mismatch")
        provenance_status = "MATCHES_INDEPENDENTLY_SUPPLIED_HASHES; PROVIDER_IDENTITY_EXTERNAL"
    shared = sorted(set(mom) & set(factors))
    if len(shared) < 100:
        raise ValueError("insufficient common monthly observations")
    # A paper figure claiming a complete 1927-to-vintage history must not silently
    # drop missing months through an inner join. Other descriptive runs remain
    # available without --figure-svg for shorter, explicitly bounded samples.
    if args.figure_svg is not None:
        if not re.fullmatch(r"\d{6}", args.vintage):
            raise ValueError("Figure 4 requires a YYYYMM vintage")
        ending_year, ending_month = int(args.vintage[:4]), int(args.vintage[4:])
        if not 1 <= ending_month <= 12:
            raise ValueError("Invalid Figure 4 vintage month")
        expected_months = [
            f"{year:04d}{month:02d}"
            for year in range(1927, ending_year + 1)
            for month in range(1, 13)
            if year < ending_year or month <= ending_month
        ]
        if shared != expected_months:
            missing = sorted(set(expected_months) - set(shared))
            extras = sorted(set(shared) - set(expected_months))
            raise ValueError(
                "Figure 4 requires uninterrupted 1927-01 to vintage coverage: "
                f"expected {len(expected_months)}, actual {len(shared)}, "
                f"missing first={missing[:5]}, unexpected first={extras[:5]}"
            )
    panel = [
        {
            "month": t, "mom": mom[t][0],
            "mkt_rf": factors[t][0],
            "smb": factors[t][1], "hml": factors[t][2],
            "rf": factors[t][3],
            "market": factors[t][0] + factors[t][3]
        } for t in shared
    ]
    sorted_mkt = sorted(r["market"] for r in panel)
    low = sorted_mkt[int(len(panel) * 0.1)]
    high = sorted_mkt[int(len(panel) * 0.9)]
    conditions = {
        "all": lambda r: True,
        "market_negative": lambda r: r["market"] < 0,
        "market_nonnegative": lambda r: r["market"] >= 0,
        "market_le_minus5": lambda r: r["market"] <= -5,
        "market_ge_plus5": lambda r: r["market"] >= 5,
        "market_bottom_decile": lambda r: r["market"] <= low,
        "market_top_decile": lambda r: r["market"] >= high,
        "mom_le_minus10": lambda r: r["mom"] <= -10,
        "post1950": lambda r: r["month"] >= "195001",
        "post1980": lambda r: r["month"] >= "198001",
        "post2000": lambda r: r["month"] >= "200001",
    }
    # Figure 4 uses five calendar groups and four contemporaneous market states.
    calendar_bins = {
        "1927_1949": ("192701", "194912"),
        "1950_1979": ("195001", "197912"),
        "1980_1999": ("198001", "199912"),
        "2000_2019": ("200001", "201912"),
        "2020_onward": ("202001", "999912"),
    }
    figure4_periods = {
        tag: summarize(panel, lambda r, lo=lo, hi=hi: lo <= r["month"] <= hi)
        for tag, (lo, hi) in calendar_bins.items()
    }
    figure4_states = {
        "market_le_minus5": summarize(panel, lambda r: r["market"] <= -5),
        "market_minus5_to_zero": summarize(panel, lambda r: -5 < r["market"] < 0),
        "market_zero_to_plus5": summarize(panel, lambda r: 0 <= r["market"] < 5),
        "market_ge_plus5": summarize(panel, lambda r: r["market"] >= 5),
    }
    if sum(v["months"] for v in figure4_periods.values()) != len(panel):
        raise ValueError("Figure 4 calendar groups do not partition sample")
    if sum(v["months"] for v in figure4_states.values()) != len(panel):
        raise ValueError("Figure 4 market groups do not partition sample")
    severe = sorted(panel, key=lambda r: r["mom"])[:10]
    result = {
        "interpretation": "DESCRIPTIVE / EX POST CONDITIONS / NON-INVESTABLE GROSS FACTOR",
        "source_vintage": args.vintage,
        "input_provenance_status": provenance_status,
        "mom_file_sha256": mom_sha,
        "factors_file_sha256": factor_sha,
        "start": shared[0], "end": shared[-1], "n": len(panel),
        "decile_thresholds_pct": {"low": low, "high": high},
        "conditional": {name: summarize(panel, predicate) for name, predicate in conditions.items()},
        "figure4_calendar_subperiods": figure4_periods,
        "figure4_same_month_market_states": figure4_states,
        "figure4_status": "REQUIRES PROVIDER INPUT HASH AND EXACT FIGURE MATCH",
        "top_10_mom_losses_all_market_positive": all(r["market"] > 0 for r in severe),
        "top_10_mom_losses": severe,
        "capm_ols_full_sample_in_sample": capm(panel),
        "sensitivity": {
            tag: {
                "negative_market": summarize(
                    subset, lambda r: r["market"] < 0),
                "strong_up_market": summarize(
                    subset, lambda r: r["market"] >= 5),
            }
            for tag, subset in {
                "1950_plus": [r for r in panel if r["month"] >= "195001"],
                "1980_plus": [r for r in panel if r["month"] >= "198001"],
                "2000_plus": [r for r in panel if r["month"] >= "200001"],
                "exclude_1932_2009": [
                    r for r in panel if r["month"][:4] not in ("1932", "2009")
                ],
            }.items()
        },
    }
    if args.figure_svg is not None:
        result["figure4_reconciliation"] = verify_figure4(
            args.figure_svg, args.vintage, figure4_periods, figure4_states)
        result["figure4_status"] = "RECOMPUTED_VALUES_MATCH_DISPLAYED_SVG; OFFICIAL_INPUT_PROVENANCE_SEPARATE"
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
