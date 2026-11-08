#!/usr/bin/env python3
"""Six offline source-hash validator contract tests, with synthetic files only.

Run: python tests/test_verify_pinned_inputs.py
Source SHA of tested validator: 901e35b86ea13c7ee2a0b9b5d06ac0b3163526ad
No provider raw data are embedded or downloaded.
"""
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROG = Path(__file__).resolve().parents[1] / "scripts" / "verify_pinned_inputs.py"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def make_zip(data=b"yyyymm,mom\n202609,1\n"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("factor.csv", data)
    return output.getvalue()


def run_case(name, folder, manifest, expected_success, expected_status):
    completed = subprocess.run(
        [sys.executable, str(PROG), "--source-dir", str(folder),
         "--manifest", str(manifest)], capture_output=True, text=True, check=False
    )
    parsed = json.loads(completed.stdout)
    statuses = [item["status"] for item in parsed["files"]]
    passed = ((completed.returncode == 0) == expected_success
              and expected_status in statuses)
    print(f"{name}: {'PASS' if passed else 'FAIL'} "
          f"exit={completed.returncode}, statuses={statuses}")
    if not passed:
        raise AssertionError((completed.stdout, completed.stderr))


def main():
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        original_csv = b"yyyymm,mom\n202609,1\n"
        original_zip = make_zip()
        source_file = folder / "factor.zip"
        source_file.write_bytes(original_zip)
        receipt = {
            "french_archives": [{
                "filename": "factor.zip", "zip_sha256": sha(original_zip),
                "csv_sha256": sha(original_csv)
            }],
            "additional_french_ff3": {
                "url": "https://example.com/factor.zip",
                "zip_sha256": sha(original_zip),
                "csv_sha256": sha(original_csv)
            },
            "aqr": {"extracted_csv_sha256": ""}
        }
        manifest = folder / "manifest.json"
        manifest.write_text(json.dumps(receipt), encoding="utf-8")
        run_case("valid source", folder, manifest, True, "PASS")
        source_file.unlink()
        run_case("missing source", folder, manifest, False, "MISSING")
        source_file.write_bytes(b"not source")
        run_case("altered zip", folder, manifest, False, "ZIP_SHA256_MISMATCH")
        source_file.write_bytes(original_zip)
        receipt["french_archives"][0]["csv_sha256"] = "0" * 64
        receipt["additional_french_ff3"]["csv_sha256"] = "0" * 64
        manifest.write_text(json.dumps(receipt), encoding="utf-8")
        run_case("wrong CSV digest", folder, manifest,
                 False, "CSV_SHA256_MISMATCH")
        # Verify that optional frozen 12-industry original source is enforced.
        receipt["french_archives"][0]["csv_sha256"] = sha(original_csv)
        receipt["additional_french_ff3"]["csv_sha256"] = sha(original_csv)
        receipt["industry_202609"] = {
            "filename": "industry.zip",
            "zip_sha256": sha(original_zip),
            "csv_sha256": sha(original_csv)
        }
        industry = folder / "industry.zip"
        industry.write_bytes(original_zip)
        manifest.write_text(json.dumps(receipt), encoding="utf-8")
        run_case("industry source correct", folder, manifest, True, "PASS")
        industry.write_bytes(b"altered industry archive")
        run_case("industry source modified", folder, manifest,
                 False, "ZIP_SHA256_MISMATCH")
    print("SIX VALIDATOR CONTRACT TESTS PASSED")


if __name__ == "__main__":
    main()
