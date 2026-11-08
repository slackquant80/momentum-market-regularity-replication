# Momentum as a Market Regularity — reproducibility package

**Status:** Public standalone replication source repository. The offline smoke test passed on 2026-11-08. Zenodo metadata are prepared in `CITATION.cff`, but no tagged release or DOI has been published yet. Original publisher datasets are not bundled, and full raw-data replay requires the exact archived vintages.

This standalone public source package supports the provider-created *French momentum research factors* and the author's *12-industry ranking calculation* underlying the paper's empirical discussion. **It is not a stock-level recreation of the Kenneth French factor, an investable net-return fund simulation, or a replication of all cited historical studies.**

## Contents and scope

- `scripts/t20_french_official_202609_fig4_and_sector_era_audit.py` — orchestrates original-provider download, exact 202609 header check, 12-industry calculation, and US Mom market-state diagnostics. Calls the next two Python files in the same folder.
- `scripts/t20_12industry_official_live_source_check.py` — industry source parser, 12–2 ranking and synthetic long–short spread diagnostics; the synthetic wealth-path statistics are **not funded account performance**.
- `scripts/t20_conditional_mom_panel.py` — separately supplied official US Mom and FF3 monthly inputs, sample/figure-value consistency.
- `scripts/t20_mom_rolling_stability.py` — Figure 5 trailing-window analysis of the provider-constructed US Mom factor.
- `exhibits/` — byte-identical copies of the author-created Figure 4–6 SVG assets, retained for source-cell checks. Original author-code/figure licensing and third-party data-use boundaries are specified below.
- `scripts/verify_exhibit_labels.py` — deterministic checks for 16 source-to-figure SVG text labels (Figure 4: 9, Figure 5: 2, Figure 6: 5). This checks displayed labels, not full SVG geometry.
- `scripts/t20_french_international_momentum_replay.py` — six published international/US WML factors with historical regional diagnostics.
- `scripts/test_t20_international_momentum.py` — synthetic parser/contract tests, **not** a test of real-data result parity.
- `scripts/t20_crossasset_independent_replay.py` — AQR 202605 published TSMOM research-factor diagnostics using archived, independently verified AQR XLSX-to-CSV parity; the companion French 202605 FF3 input has separate provider-origin limitations.
- `scripts/verify_pinned_inputs.py` and `provenance/pinned_inputs.json` — deterministic local SHA-256 checks for original vintage source ZIP/CSV files; these are source-identity tests, not a replay of calculations.

## Data provenance and the frozen vintage

Official Kenneth French Data Library: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

AQR TSMOM provider source: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly . Attribution requested by AQR for its factor dataset: **AQR Capital Management, LLC.** AQR explains that the factor returns represent hypothetical research portfolios, not actual investment products. The original AQR spreadsheet's included Terms of Use still apply; the workbook and its extracted raw data are **not** distributed in this repository. Consult the provider before distributing source data. Kenneth French data are likewise referenced rather than copied here.

The manuscript's accepted regional, US and industry results use **September 2026** original publisher files, not whichever vintage the live official provider serves today. Publisher filenames (case-sensitive):

```text
F-F_Momentum_Factor_CSV.zip
F-F_Research_Data_Factors_CSV.zip
12_Industry_Portfolios_CSV.zip
Developed_ex_US_Mom_Factor_CSV.zip
Europe_Mom_Factor_CSV.zip
Japan_Mom_Factor_CSV.zip
Asia_Pacific_ex_Japan_MOM_Factor_CSV.zip
North_America_Mom_Factor_CSV.zip
```

**Important:** These public scripts intentionally demand the original `202609` source headers. After a provider update, ordinary re-download may fail rather than silently change historical numbers. Obtain rights-cleared *original September 2026 archived copies* and verify their original ZIP and CSV SHA256 against the author's frozen receipts. Those source files are **not redistributed here**.

## Setup and local checks

Use Python 3.13.5 for the recorded local test environment. The regional statistics require `numpy`, AQR factor diagnostics require **both `numpy` and `pandas`**, and the rolling chart requires `matplotlib`. `requirements.txt` now fixes exact tested versions. Other Python environments may work but are not claimed as verified.

```bash
python -m pip install -r requirements.txt
python scripts/run_release_smoke.py
python tests/test_verify_pinned_inputs.py
python tests/test_aqr_synthetic_contract.py
python scripts/verify_exhibit_labels.py
python scripts/verify_pinned_inputs.py --source-dir /path/to/202609_official_zip
python scripts/test_t20_international_momentum.py
python scripts/t20_french_international_momentum_replay.py --source-dir /path/to/202609_official_zip --output output/regional.json --strict-vintage 202609
python scripts/t20_french_official_202609_fig4_and_sector_era_audit.py --out output/us_industry_check.json
python scripts/t20_crossasset_independent_replay.py --aqr /path/to/archived_202605_aqr.csv --ff3 /path/to/archived_202605_ff3.csv --out output/aqr.json --pin-aqr-sha256
# Optional SINGLE-COMMAND bounded source+regional+AQR replay, requires ALL exact source files:
python scripts/verify_real_data_release_gate.py --french-dir /path/to/202609_official_zip --aqr-csv /path/to/archived_202605_aqr.csv --ff3-csv /path/to/archived_202605_ff3.csv --out output/release_gate
```

The integrated US/industry audit command requests the current live provider files and may intentionally return `OFFICIAL_FINAL_AUDIT_FAIL` if 202609 is no longer the latest vintage. This is **not an archived-vintage replay**. For Figure 4 and Figure 5, use the original downloaded CSV inputs with the scripts' documented command-line options. Output paths are local only; no data upload or GitHub Actions is required.

**Local offline test evidence (2026-11-08, isolated Python 3.13.5):** Verified exact Git Blob SHA identity of the staged Python source `scripts/verify_pinned_inputs.py` (`901e35b86ea13c7ee2a0b9b5d06ac0b3163526ad`) and the staged tests file `tests/test_verify_pinned_inputs.py` (`e0110ade81a7a15287fd4c51b07e992927c37432`). The exact staged test produced **6/6 PASS**: valid input, missing ZIP, altered ZIP, incorrect decompressed CSV, valid 12-industry input, and tampered 12-industry ZIP. Independently, the exact staged Python source `scripts/t20_crossasset_independent_replay.py` (`bcdbe5b6658814bad30e8ac7f93d84bd376c424b`) and test `tests/test_aqr_synthetic_contract.py` (`b5796022a69a21e0be3d82588fa0bd9b5b0eb349`) produced **3/3 PASS** on synthetic 497-month inputs, incorrect AQR source SHA and incomplete series. **9/9 current source-identical targeted contract checks passed.** These synthetic checks are NOT official-provider real-data full-program replay. The separate clean-Ubuntu `run_release_smoke.py` subsequently passed, as documented below. Independent original-source official results remain separately documented in source receipts.

**Prior original-source research verification:** The author previously executed the 202609 Kenneth French 12-industry and U.S. Mom analyses against the original official downloaded ZIP/CSV files; the 12-industry signal covered 1,191 months and the six regional factors covered a shared 431 months ending September 2026. Their original source hashes and reference statistics are preserved in `provenance/pinned_inputs.json` and `provenance/expected_replay.json`. These records are historical evidence; raw source files are not included. Figure 4–6 official-source display labels were independently compared against the authored SVGs on 2026-11-08: 16/16 labels matched, recorded in `provenance/figure4_6_source_label_audit_20261108.json`. The saved Python display-label script has now been executed and passed in the one-off clean Ubuntu smoke. The original-source ALL-INPUT numerical release gate has NOT been run on all archived raw inputs in this isolated environment.

**Independent clean Ubuntu offline smoke (2026-11-08): PASS.** One bounded, nonrecurring private GitHub-hosted Ubuntu job installed the pinned package dependencies in Python 3.13, compiled 13 Python files, and executed four offline test commands—source identity contracts, AQR synthetic end-to-end, international synthetic input contract and Figure 4–6 SVG label check—**all four exit 0**. The one-time workflow was removed after the successful run. This does not substitute for archived raw-data redistribution permissions or the source-vintage historical replay, which is separately documented.

**A complete clean-environment raw-data replay has not been executed on this public repository's exact file set.** The one-command real-source release gate now checks archived September 2026 French ZIP/CSV hashes, the exact May 2026 AQR CSV digest, the archived French May 2026 FF3 Git blob identity, six regional factor outputs and bounded AQR output metrics. It **has not yet been executed against all pinned historical inputs** and does not assert publication-level rights or chart parity. Its present numeric scope includes **six-region French, U.S. 12-industry ranking and AQR factor calculations** from strict archived originals. The separate SVG source-label checker checks Figure 4–6 displayed values, but full plotted-geometry, all research figures and manuscript tables require the publication-QA record; passing these gates alone does not approve release. Public repository: https://github.com/slackquant80/momentum-market-regularity-replication . No tag, GitHub release or Zenodo DOI exists yet.

## Scientific interpretation

The published French Mom/WML research factors are provider-constructed, gross long–short series. US industry analysis independently ranks **provider-constructed 12 industry portfolios**, not individual stocks. Region universes overlap; Japan is an important weak case. Past overlapping rolling 10-year windows cannot be interpreted as independent success probabilities. Costs, financing and short-borrowing are not represented by most gross factor statistics. Published-study redraws and conceptual figures are deliberately excluded from this **code-only candidate**. AQR multiasset reanalysis is included, but its 202605 source receipt and provider-origin qualification remain separate from the French 202609 factor analyses.

## Licenses and rights

- **Original author-created Python source in `scripts/` and `tests/`:** MIT, see the root [LICENSE](LICENSE).
- **Original author-created SVGs in `exhibits/`:** Creative Commons Attribution 4.0 International (CC BY 4.0), see [exhibits/LICENSE.md](exhibits/LICENSE.md).
- **Original author-written README and explanatory provenance narratives:** CC BY 4.0 to the extent copyrightable. Factual numbers and source hashes are not an assignment of rights to the underlying provider data.
- **External Kenneth French, AQR and other third-party datasets, third-party studies, marks, and upstream packages:** not relicensed by this repository; original raw archives are not included. Their own source terms apply.

The `CITATION.cff` declares MIT for the primary **software** record. This is not a grant of MIT rights to the separately CC BY 4.0-authored illustrations. The archive contains mixed-license material; read these per-path notices before reuse. The paper itself is a distinct manuscript and is not licensed here.

## Reproducibility and tagged-release gates

1. Run `python scripts/run_release_smoke.py` from a newly exported clean working tree. It passed in the independent one-off Ubuntu environment on 2026-11-08. Independently verify exact input archive checksums where original snapshots are available.
2. Replay of each included result and independent rounding/caption comparison with the frozen manuscript.
3. Confirm third-party source attribution and terms; never redistribute French/AQR raw source data. The author approved MIT for original Python code and CC BY 4.0 for author-created figures and original narrative.
4. The public repository was populated from an audited working-tree allowlist with fresh Git history, separate from the private research project. Original manuscript display and reference checks were completed independently; full archived-vintage end-to-end real-data verification is not claimed.
5. After confirming the mixed-license notices, publish a tagged software release for Zenodo archiving. Verify the actual resulting DOI and the Zenodo metadata before adding the DOI to this README. The paper PDF may retain its stable GitHub URL.

This package is evidence for a Foundation practitioner synthesis, not a claim of new underlying market return discovery.
