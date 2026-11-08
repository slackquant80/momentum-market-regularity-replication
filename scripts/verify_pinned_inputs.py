#!/usr/bin/env python3
"""Verify independently obtained source files against T20's pinned vintage receipt.

Strict checksum check, NOT a scientific result replay. No downloads or uploads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_zip(directory: Path, item: dict) -> dict:
    path = directory / item["filename"]
    if not path.is_file():
        return {"file": item["filename"], "status": "MISSING"}
    raw = path.read_bytes()
    if sha256(raw) != item["zip_sha256"]:
        return {"file": item["filename"], "status": "ZIP_SHA256_MISMATCH"}
    with zipfile.ZipFile(path) as archive:
        csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(csv_names) != 1:
            return {"file": item["filename"], "status": "CSV_MEMBER_COUNT_MISMATCH"}
        if sha256(archive.read(csv_names[0])) != item["csv_sha256"]:
            return {"file": item["filename"], "status": "CSV_SHA256_MISMATCH"}
    return {"file": item["filename"], "status": "PASS"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "provenance/pinned_inputs.json")
    parser.add_argument("--aqr-csv", type=Path, default=None)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    results = [check_zip(args.source_dir, entry) for entry in manifest["french_archives"]]
    if "industry_202609" in manifest:
        results.append(check_zip(args.source_dir, manifest["industry_202609"]))
    for key, item in [("FF3", manifest["additional_french_ff3"])]:
        f = args.source_dir / Path(item["url"]).name
        if not f.is_file():
            results.append({"file": f.name, "status": "MISSING"})
        elif sha256(f.read_bytes()) == item["zip_sha256"]:
            with zipfile.ZipFile(f) as z:
                members = [name for name in z.namelist() if name.lower().endswith(".csv")]
                status = "PASS" if len(members) == 1 and sha256(z.read(members[0])) == item["csv_sha256"] else "CSV_SHA256_MISMATCH"
            results.append({"file": f.name, "status": status})
        else:
            results.append({"file": f.name, "status": "ZIP_SHA256_MISMATCH"})
    if args.aqr_csv is not None:
        val = sha256(args.aqr_csv.read_bytes())
        results.append({"file": args.aqr_csv.name, "status": "PASS" if val == manifest["aqr"]["extracted_csv_sha256"] else "CSV_SHA256_MISMATCH"})
    ok = all(x["status"] == "PASS" for x in results)
    print(json.dumps({"status": "SOURCE_BYTES_PASS" if ok else "SOURCE_BYTES_FAIL", "files": results}, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
