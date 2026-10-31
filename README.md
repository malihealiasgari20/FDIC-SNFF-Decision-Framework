# Replication package, release 4.0 (2026-10-30)

For: Y. Nejatbakhsh, M. Aliasgari, P. Safaee, and S. Shokoohyar, "An Interaction-Aware
Decision Framework for FDIC-Assisted Distressed Bank Acquisitions: Empirical Evidence from
the FDIC Failed-Bank Panel and the SVB--First Citizens Case," prepared for submission to IEEE Access.

This package is one fixed release. It contains the final datasets, the source ledger of
FDIC press releases, the code, every output of the final analysis, the generated LaTeX
tables, the software versions, and SHA-256 checksums of every file (`MANIFEST.sha256`).
Cite the paper and this release using `CITATION.cff`. A persistent DOI and the approved licenses will be added when the corresponding author publishes the archival record.

## Contents

| Path | Content |
|---|---|
| `03_revised_framework_2026-10-29/data/SNFF_Revised_Inputs_Primary55.csv` | Primary panel: 55 FDIC-assisted acquisitions (2008-2024) by acquirers with a U.S.-listed parent; inputs, deal terms, timing and outcomes |
| `03_revised_framework_2026-10-29/data/SNFF_Revised_Inputs_Broader90.csv` | Broader panel of 90 transactions (contains the 55) |
| `03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv` | Source ledger: for each of the 90 transactions, the FDIC press release, its wording on timing, loss sharing, bridge banks and FDIC financing, and the resulting coding |
| `03_revised_framework_2026-10-29/data/Event_Convention_Comparison_90.csv` | Daily abnormal returns around each announcement and the CARs under the primary window, two announcement-date windows and a market model |
| `03_revised_framework_2026-10-29/data/*.txt` | Validation reports for the variables and the event-time convention |
| `03_revised_framework_2026-10-29/REVISED_FRAMEWORK_SPEC.md`, `code/` | Variable definitions, Spider rules (`snff_revised_features.py`) and the scripts that built the inputs and the ledger |
| `05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv` | CARs against the equal-weighted bank-sector benchmark (`code/bank_benchmark_cars.py`) |
| `05_manuscript_analysis_2026-10-29/code/` | `final_analysis.py` (every model, test, table input and figure), `cluster_influence_check.py`, `bank_benchmark_cars.py`, `make_tex_tables.py` (LaTeX tables), `compare_clean_rerun.py`, and the scripts that insert the results into the manuscript and check its prose numbers (`fill_manuscript.py`, `number_check.py`, `fill_reports.py`; the manuscript itself is not part of this package) |
| `05_manuscript_analysis_2026-10-29/results/` | Every output of the final analysis, including `RUN_MANIFEST.json` (settings, seeds, sample counts, input checksums, software versions) |
| `05_manuscript_analysis_2026-10-29/tables/` | The LaTeX tables of the manuscript and `manuscript_numbers.json` |
| `05_manuscript_analysis_2026-10-29/run_log.txt`, `CLEAN_RERUN_COMPARISON.txt` | Log of the final run and the comparison with a rerun from a fresh copy (every output byte-identical) |
| `02b_car_conventions_2026-10-29/` | The 90-transaction panel rebuilt from the June 2026 price cache, and the files used for the sample-construction counts (closing prices removed) |
| `04b_step4_verification_2026-10-29/Loss_Share_Negatives_Corroboration.csv` | Acquirer filings that confirm the "no loss share" coding for eight transactions |
| `stage1_car_rebuild_code/` | The Stage 1 code that built the CARs from prices and the FDIC data (provenance) |
| `requirements.txt`, `ENVIRONMENT.txt` | Software versions of the final run |
| `reproduce.sh` | Verifies the checksums, reruns the final analysis, and compares every output with this release |

## Reproduce

```
pip install -r requirements.txt        # Python 3.13.17
bash reproduce.sh                      # about 77 minutes on one core
```

`reproduce.sh` checks `MANIFEST.sha256`, reruns `final_analysis.py` and
`cluster_influence_check.py` into a temporary folder, requires every output to be
byte-identical to `05_manuscript_analysis_2026-10-29/results/` (the manifest must agree
in every field but the runtime), and regenerates the LaTeX tables and compares them with
`tables/`. With other library versions, small differences in late decimals are possible.

Three steps cannot be rerun from this package, because they read daily prices, which are
not redistributed: the Stage 1 CAR build (`stage1_car_rebuild_code/`), the event-window
report (`03_.../code/event_convention_report.py`) and the bank-sector benchmark
(`05_.../code/bank_benchmark_cars.py`). Their outputs are included, and each script
documents the price file it expects. Prices were retrieved from Yahoo Finance with the
yfinance library in June 2026, with Financial Modeling Prep as a fallback. The scripts that
built the variables (`03_.../code/build_*.py`) read the June 2026 Stage 1 files, which
contain the BankFind call-report pulls and are kept by the authors.

## Key checksums (SHA-256, also in RUN_MANIFEST.json)

* `SNFF_Revised_Inputs_Primary55.csv`: `90642ca00fb2831d3133e34c2bc59d55af4b895257abfdcae33910fbb40c8b84`
* `SNFF_Revised_Inputs_Broader90.csv`: `be9335f34cd0d2dcc3cba81fa7e994078d3dac70011725ed66944fed1137696a`
* `Source_Verification_Ledger_90.csv`: `64ba69e18b1d4527a439adae987109c208b866960287d6ef5a20c1994f3c1aca`
* `Event_Convention_Comparison_90.csv`: `0bccf63a34c549e4d7df97509665dad1e98f03494d40b9435d5d6ab8f97bba84`
* `snff_revised_features.py`: `45d8d44195e04a5fb1ba29afd55eba8c237be398e0f49ed0043d10c4172424f5`
* `Bank_Benchmark_CAR_90.csv`: `0af900a1df3fac26585d92a448d0945d861e93a15b4c83d7e2be75f07918aded`
* `final_analysis.py`: `98d2522a895989b1bef61a35820756ed46a5793023d827666f58ded13280a129`

## Authors, credit, and repository ownership

The scientific authors are **Yousef Nejatbakhsh, Malihe Aliasgari, Parsa Safaee, and Sina Shokoohyar**, in the manuscript's author order. See `CITATION.cff` and `AUTHORS.md`. Repository ownership and GitHub collaboration are distinct from scientific authorship.

The intended repository owner is **Malihe Aliasgari**, the manuscript's corresponding author. **Yousef Nejatbakhsh** (`@Nejatbakhsh-y`) should be invited as a GitHub collaborator by the repository owner. See `GITHUB_PUBLISHING_GUIDE.md`.

## Contact

Malihe Aliasgari, Department of Mathematical Sciences, Kean University (corresponding author).
