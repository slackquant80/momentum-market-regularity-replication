#!/usr/bin/env python3
"""Single-command, offline T20 publication-candidate smoke QA.

Does not claim original-source full-data parity or publication permission.
Run from a clean checkout or GitHub working-tree ZIP after installing requirements.
"""
from __future__ import annotations

import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(*pieces: str) -> dict:
    p = subprocess.run(
        [sys.executable, *pieces], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    return {
        "command": " ".join(pieces),
        "exit": p.returncode,
        "passed": p.returncode == 0,
        "stdout_tail": p.stdout[-350:],
        "stderr_tail": p.stderr[-450:],
    }


def main() -> None:
    candidates = sorted((ROOT / "scripts").glob("*.py"))
    candidates += sorted((ROOT / "tests").glob("*.py"))
    syntax = []
    for path in candidates:
        try:
            py_compile.compile(str(path), doraise=True)
            syntax.append({"file": str(path.relative_to(ROOT)), "passed": True})
        except Exception as exc:
            syntax.append({"file": str(path.relative_to(ROOT)),
                           "passed": False, "error": str(exc)})
    tests = [command("tests/test_verify_pinned_inputs.py"),
             command("tests/test_aqr_synthetic_contract.py"),
             command("scripts/test_t20_international_momentum.py"),
             command("scripts/verify_exhibit_labels.py"),
             command("tests/test_release_reference_schema.py")]
    all_good = all(x["passed"] for x in syntax) and all(x["passed"] for x in tests)
    output = {
        "status": "OFFLINE_SMOKE_PASS" if all_good else "OFFLINE_SMOKE_FAIL",
        "python": sys.version.split()[0],
        "syntax_checked": len(syntax),
        "syntax": syntax,
        "tests": tests,
        "scope": ("Only offline parser/syntax/synthetic and displayed-SVG-label tests; "
                  "DOES NOT replay provider-original 202609 vintage raw data, "
                  "rebuild manuscript PDF, or grant rights to third-party sources"),
    }
    print(json.dumps(output, indent=2))
    if not all_good:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
