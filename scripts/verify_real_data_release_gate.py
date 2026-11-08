#!/usr/bin/env python3
"""Offline real-source numerical release gate for T20, no network and no Actions.

This checks pinned French 202609 archive identities, six regional factors,
author-constructed 12-industry rankings, and archived AQR 202605 factor
statistics. It does NOT re-render every manuscript SVG/table, nor establish
publication rights or certify a public software release.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REFERENCE = ROOT / "provenance" / "expected_replay.json"


def run(*args: object) -> None:
    completed = subprocess.run(
        [sys.executable, *map(str, args)], capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed: " + " ".join(map(str, args)) +
            "\nSTDOUT: " + completed.stdout[-2500:] +
            "\nSTDERR: " + completed.stderr[-2500:]
        )


def close(label: str, observed: float, expected: float, tolerance: float) -> None:
    if abs(float(observed) - float(expected)) > tolerance:
        raise ValueError(f"{label}: observed {observed}, frozen {expected}, tol={tolerance}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--french-dir", type=Path, required=True,
                        help="Directory with six official French 202609 ZIPs and FF3 ZIP")
    parser.add_argument("--aqr-csv", type=Path, required=True,
                        help="Archived exact 202605 AQR CSV, SHA256 pinned")
    parser.add_argument("--ff3-csv", type=Path, required=True,
                        help="202605 archived French FF3 monthly CSV")
    parser.add_argument("--out", type=Path, required=True,
                        help="Directory for local outputs; never commit raw sources")
    args = parser.parse_args()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if not args.french_dir.is_dir() or not args.aqr_csv.is_file() or not args.ff3_csv.is_file():
        raise SystemExit("INPUT_MISSING: no replay performed; supply all original files")
    raw_ff3 = args.ff3_csv.read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw_ff3)).encode() + b"\0" + raw_ff3).hexdigest()
    if git_blob != "880245826fe95c46e8345ff07d9b9fb276c02da2":
        raise ValueError("FF3 202605 input is not the pinned research-source Git blob")
    args.out.mkdir(parents=True, exist_ok=True)
    run(SCRIPTS / "verify_pinned_inputs.py", "--source-dir", args.french_dir,
        "--aqr-csv", args.aqr_csv)
    # Author-constructed 12-industry rankings, distinct from provider-created Mom.
    source_archive = args.french_dir / "12_Industry_Portfolios_CSV.zip"
    with zipfile.ZipFile(source_archive) as archive:
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(csv_members) != 1:
            raise ValueError("Expected exactly one official 12-industry CSV")
        industry_text = archive.read(csv_members[0]).decode("latin-1")
    spec = importlib.util.spec_from_file_location(
        "t20_industry", SCRIPTS / "t20_12industry_official_live_source_check.py"
    )
    industry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(industry_module)
    monthly_rows = industry_module.parse_monthly(industry_text)
    industry_monthly = industry_module.strategy(monthly_rows)
    industry_reference = reference["industry_202609"]
    sample = industry_reference["sample"]
    if (len(monthly_rows) != sample["monthly_source_rows"] or
            monthly_rows[0][0] != sample["source_first"] or
            monthly_rows[-1][0] != sample["source_last"] or
            len(industry_monthly) != sample["n"] or
            industry_monthly[0]["ym"] != sample["strategy_first"] or
            industry_monthly[-1]["ym"] != sample["strategy_last"]):
        raise ValueError("12-industry official sample identity mismatch")
    for name, bp in (("full_gross", 0), ("full_cost10bp", 10)):
        actual = industry_module.perf(industry_monthly, bp)
        expected = industry_reference[name]
        for metric in ("n", "mean_spread_month_pp", "synthetic_cagr_pct",
                       "synthetic_mdd_pct"):
            close("industry." + name + "." + metric,
                  actual[metric], expected[metric], 1e-6)
    eras = {
        "1927_1949": ("192707", "194912"),
        "1950_1979": ("195001", "197912"),
        "1980_1999": ("198001", "199912"),
        "2000_2019": ("200001", "201912"),
        "2024_202609": ("202401", "202609"),
    }
    for name, (lo, hi) in eras.items():
        subset = [row for row in industry_monthly if lo <= row["ym"] <= hi]
        actual = industry_module.perf(subset)
        expected = industry_reference["eras"][name]
        for metric in ("n", "mean_spread_month_pp"):
            close("industry." + name + "." + metric,
                  actual[metric], expected[metric], 1e-6)
    regional = args.out / "french_regional.json"
    run(SCRIPTS / "t20_french_international_momentum_replay.py",
        "--source-dir", args.french_dir, "--output", regional,
        "--strict-vintage", "202609")
    regional_data = json.loads(regional.read_text(encoding="utf-8"))
    correct = reference["french_202609"]
    if regional_data["common_sample"] != correct["sample"]:
        raise ValueError("French common sample differs from frozen study sample")
    for region, expected in correct["regions"].items():
        actual = regional_data["regions"][region]["common"]
        close(region + ".n", actual["n"], expected["n"], 0)
        close(region + ".mean_month_pct", actual["mean_month_pct"],
              expected["mean_month_pct"], 1e-8)
        close(region + ".hac12_t", actual["hac12_t"],
              expected["hac12_t"], 1e-6)
    aqr_path = args.out / "aqr.json"
    run(SCRIPTS / "t20_crossasset_independent_replay.py",
        "--aqr", args.aqr_csv, "--ff3", args.ff3_csv,
        "--out", aqr_path, "--pin-aqr-sha256")
    aqr = json.loads(aqr_path.read_text(encoding="utf-8"))
    benchmark = reference["aqr_202605"]
    close("aqr.n", aqr["sample"]["n"], benchmark["sample_n"], 0)
    close("aqr.mean", aqr["factors"]["TSMOM"]["mean_month_percent"],
          benchmark["mean_month_percent"], 1e-8)
    close("aqr.vol", aqr["factors"]["TSMOM"]["annual_vol_percent"],
          benchmark["annual_vol_percent"], 1e-8)
    close("aqr.HAC12", aqr["factors"]["TSMOM"]["hac12_t"],
          benchmark["hac12_t"], 0.0006)
    close("aqr.market_down5.n", aqr["states"]["market_down5"]["n"],
          benchmark["market_down5_n"], 0)
    close("aqr.market_down5.mean",
          aqr["states"]["market_down5"]["monthly_mean_percent"]["TSMOM"],
          benchmark["market_down5_tsmom_mean_percent"], 1e-8)
    close("aqr.blend8020.vol",
          aqr["hypothetical_mixes"]["0.2"]["annual_vol_percent"],
          benchmark["blend8020_vol_percent"], 1e-8)
    receipt = {
        "status": "REGIONAL_AQR_INDUSTRY_NUMERIC_GATE_PASS__FIGURES_NOT_REGENERATED",
        "industry_strategy_months_checked": len(industry_monthly),
        "industry_periods_checked": len(eras),
        "french_sample": regional_data["common_sample"],
        "french_regions_checked": len(correct["regions"]),
        "aqr_months_checked": aqr["sample"]["n"],
        "warnings": [
            "Not an official live-provider verification of French 202605 FF3",
            "Manuscript Figure 4, Figure 5 and Figure 6 SVGs are NOT regenerated by this gate",
            "Manuscript tables and exact figure-layout parity require separate QA",
            "Not a tradable funded performance simulation",
            "No public release rights are conferred by this receipt",
        ],
    }
    receipt_path = args.out / "release_numeric_gate.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
