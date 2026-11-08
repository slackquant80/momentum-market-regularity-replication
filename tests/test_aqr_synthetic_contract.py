#!/usr/bin/env python3
"""Offline AQR replay contract: synthetic 497-month data only (NOT paper result replay).

The Python implementation under test was independently verified byte-for-byte
against Git blob bcdbe5b6658814bad30e8ac7f93d84bd376c424b before running
these three cases. Command: python tests/test_aqr_synthetic_contract.py
"""
import csv
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/t20_crossasset_independent_replay.py"


def main():
    months = pd.period_range("1985-01", "2026-05", freq="M")
    assert len(months) == 497
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        aqr = home / "aqr.csv"
        ff3 = home / "ff3.csv"
        out = home / "result.json"
        with aqr.open("w", newline="") as file:
            w = csv.writer(file)
            w.writerow(["date", "TSMOM", "TSMOM_CM", "TSMOM_EQ", "TSMOM_FI", "TSMOM_FX"])
            for index, month in enumerate(months):
                value = .02 * math.sin(index * .13) + .003
                w.writerow([str(month.to_timestamp("M").date()),
                            value, value / 2, value * 2, value / 3, value / 4])
        with ff3.open("w", newline="") as file:
            w = csv.writer(file)
            w.writerow(["This file was created using the 202605 CRSP database."])
            for index, month in enumerate(months):
                w.writerow([str(month).replace("-", ""), -6 if index % 11 == 0 else 2.2,
                            0, 0, .4])
        command = [sys.executable, str(SCRIPT), "--aqr", str(aqr),
                   "--ff3", str(ff3), "--out", str(out)]
        completed = subprocess.run(command, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["sample"]["n"] == 497
        assert result["sample"]["first"] == "1985-01"
        assert result["sample"]["last"] == "2026-05"
        assert result["states"]["market_down5"]["n"] == 46
        print("PASS: synthetic 497-month AQR parser and end-to-end calculation")
        bad_hash = subprocess.run(command + ["--pin-aqr-sha256"], capture_output=True, text=True)
        assert bad_hash.returncode != 0 and "SHA256 mismatch" in bad_hash.stderr
        print("PASS: incorrect AQR SHA256 rejected")
        lines = aqr.read_text(encoding="utf-8").splitlines(keepends=True)
        aqr.write_text("".join(lines[:-1]), encoding="utf-8")
        incomplete = subprocess.run(command, capture_output=True, text=True)
        assert incomplete.returncode != 0 and "497-month vintage" in incomplete.stderr
        print("PASS: incomplete common sample rejected")
    print("THREE SYNTHETIC AQR PYTHON CONTRACT TESTS PASSED")


if __name__ == "__main__":
    main()
