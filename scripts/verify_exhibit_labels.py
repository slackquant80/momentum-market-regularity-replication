#!/usr/bin/env python3
"""Check exact displayed SVG value labels against pre-verified original-source cells.

Offline, no provider download. Checks labels, not every plotted curve coordinate.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / "provenance/expected_replay.json").read_text(encoding="utf-8"))
EXHIBITS = ROOT / "exhibits"


def labels(filename: str) -> list[str]:
    root = ET.parse(EXHIBITS / filename).getroot()
    return [(node.text or "") for node in root.iter() if node.tag.endswith("text")]


def check(name: str, texts: list[str], expected: str) -> None:
    n = texts.count(expected)
    if n != 1:
        raise AssertionError(f"{name}: expected one instance of {expected!r}, observed {n}")


def main() -> None:
    count = 0
    fig4 = labels("t20_fig04_official_french_momentum_original.svg")
    for group in ("calendar_periods", "same_month_market_states"):
        for period, n, mean in REFERENCE["figure4_202609"][group]:
            value = f"{mean:+.2f}% (n={n})"
            check(f"Figure 4 {period}", fig4, value)
            count += 1
    fig5 = labels("t20_fig05_us_mom_rolling_stability_original.svg")
    for key in ("rolling_120", "rolling_240"):
        value = f'{REFERENCE["figure5_202609"][key]["percent"]:.1f}% of windows > 0'
        if not any(value in s for s in fig5):
            raise AssertionError(f"Figure 5 {key}: {value!r} not shown")
        count += 1
    fig6 = labels("t20_1927_2026_12industry_official_202609_VALIDATED.svg")
    for period, n, mean in REFERENCE["figure6_202609"]["selected_periods"]:
        value = f"{mean:+.3f} pp"
        check(f"Figure 6 {period}", fig6, value)
        if f"n={n}" not in fig6:
            raise AssertionError(f"Figure 6 {period}: n={n} missing")
        count += 1
    if count != 16:
        raise AssertionError(f"Expected exactly 16 display tests, got {count}")
    print(json.dumps({"status":"16_OF_16_EXHIBIT_LABELS_MATCH",
                      "figure4":9,"figure5":2,"figure6":5,
                      "scope":"SVG text labels only; curve geometry / full PDF inspection not certified"},
                     indent=2))


if __name__ == "__main__":
    main()
