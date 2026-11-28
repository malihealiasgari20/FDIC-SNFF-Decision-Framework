# FDIC-SNFF-Decision-Framework: replication package, release 4.18

Replication package for Y. Nejatbakhsh, M. Aliasgari, P. Safaee, and S. Shokoohyar, "Do Interaction Rules Improve
Decisions on FDIC-Assisted Bank Acquisitions? A Leakage-Controlled Evaluation of the Spider Network Filtering
Framework," revised manuscript for *IEEE Access* (Access-2026-56349).

Release 4.18, 2026-11-27. It contains the final datasets, the source-verification ledgers of FDIC press releases and
winning bids, the analysis code, every result of the final analysis (89 files), the 14 LaTeX tables and the
figures of the manuscript, the software versions, the reproduction script and SHA-256 checksums of every file
(`MANIFEST.sha256`). Historical stock prices are not redistributed (see [Data sources](#data-sources-and-redistribution)).

## Quick start

```bash
sha256sum -c MANIFEST.sha256           # integrity of every file
pip install -r requirements.txt        # Python 3.13.18; see ENVIRONMENT.txt
bash reproduce.sh --quick paper.tex    # under a minute
bash reproduce.sh paper.tex            # full reproduction, about 3.5 hours on one core
```

`paper.tex` is the manuscript's LaTeX source; it is optional, and without it step 6 is skipped. The manuscript is not
part of this package.

## What `reproduce.sh` does

| Step | Full mode | `--quick` |
|---|---|---|
| 1 | Checks every file against `MANIFEST.sha256` | same |
| 1b | Rebuilds the 51 acquisition events from the call reports (`build_event_inputs.py`) and requires the released files | same |
| 2 | Reruns `final_analysis.py` (about 2 hours), `cluster_influence_check.py`, `weight_sensitivity.py` (about 1.5 hours) and `selection_comparison.py` | Starts from the released results; reruns Model 2 in all 50 partitions (`cluster_influence_check.py`, which asserts every released Model 2 AUC) and `selection_comparison.py` |
| 3 | Requires every result file to be byte-identical to `05_manuscript_analysis_2026-10-29/results/` (`RUN_MANIFEST.json` equal in every field except the runtime) | same |
| 4 | Regenerates the LaTeX tables and the calibration figure and requires the tables to be identical | same |
| 5 | Checks the coding of FDIC financing of the buyer against the winning-bid record (`check_fdic_financing.py`) | same |
| 6 | With the manuscript: `table_check.py` (every table equals the generated table) and `number_check.py` (637 checks of the prose numbers and statements, computed from the results; `manuscript_anchors.json` gives the current wording of passages reworded after the checks were written) | same |

The PNG figures can differ in anti-aliasing between machines, because matplotlib renders text with the system's
FreeType library; they are reported but not counted, and their data are in the result tables. With library versions
other than those in `requirements.txt`, small differences in late decimals are possible (XGBoost in particular).

## Repository layout

| Path | Content |
|---|---|
| `03_revised_framework_2026-10-29/data/SNFF_Revised_Inputs_Primary55.csv` | Primary panel: 55 FDIC-assisted acquisitions (2008-2024) by acquirers with a U.S.-listed parent; inputs, deal terms, timing and outcomes |
| `03_revised_framework_2026-10-29/data/SNFF_Revised_Inputs_Broader90.csv` | Broader panel of 90 transactions (contains the 55) |
| `03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv` | For each of the 90 transactions, the FDIC press release, its wording on timing, loss sharing, bridge banks and FDIC financing, and the resulting coding |
| `03_revised_framework_2026-10-29/data/FDIC_Financing_Check_90.csv` | For each of the 90, the document that states the winning bid (FDIC bid summary, purchase and assumption agreement, acquirer's SEC filing or FDIC release), its URL, the bid as stated and whether it includes FDIC financing of the buyer; report in `FDIC_Financing_Check_Report.txt` |
| `03_revised_framework_2026-10-29/data/Multi_Bank_Event_Call_Reports.csv` | Call-report amounts (FDIC BankFind API) of the 15 banks in the four multi-bank acquisition events, with the query URL of each bank |
| `03_revised_framework_2026-10-29/data/SNFF_Event_Inputs_Primary51.csv` | The 51 acquisition events of the primary panel, each scored on the consolidated inputs of every bank its acquirer bought that day (`SNFF_Event_Consolidations.csv`, `Event_Inputs_Report.txt`) |
| `03_revised_framework_2026-10-29/data/Excluded39_Buyer_Call_Reports.csv`, `Excluded39_Parent_Status.csv` | The acquiring banks' call reports and the later status of the listed parents of the 39 eligible transactions whose prices were not collected (26 transactions of 17 parents later acquired and delisted; 13 of 7 parents still trading) |
| `03_revised_framework_2026-10-29/data/Parent_Crosswalk.csv` | Crosswalk of the 52 acquiring-parent tickers among the 94 transactions with a U.S.-listed parent to 51 holding companies at the date of each transaction (Hancock Holding Company appears as HBHC in 2009 and HWC in 2017), with the acquiring banks, their FDIC certificates and later corporate events (release 4.18) |
| `03_revised_framework_2026-10-29/data/SVB_Deposit_Stages.csv` | SVB's deposits and assets at its last call report, at failure and as assumed by First Citizens, with the source of each; only the first is in the information set |
| `03_revised_framework_2026-10-29/data/Event_Convention_Comparison_90.csv` | Daily abnormal returns around each announcement and the CARs under the primary window, two announcement-date windows and a market model |
| `03_revised_framework_2026-10-29/data/*.txt` | Validation reports for the variables, the event-time convention and the event inputs |
| `03_revised_framework_2026-10-29/REVISED_FRAMEWORK_SPEC.md`, `03_revised_framework_2026-10-29/code/` | Variable definitions; the Spider rules (`snff_revised_features.py`); the scripts that built the inputs and the ledger; `build_event_inputs.py`; `check_fdic_financing.py` |
| `05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv` | CARs against the equal-weighted bank-sector benchmark (a peer portfolio of 27 banks) |
| `05_manuscript_analysis_2026-10-29/code/` | `final_analysis.py` (every model, test, table input and figure), `cluster_influence_check.py`, `weight_sensitivity.py`, `selection_comparison.py`, `bank_benchmark_cars.py`, `make_tex_tables.py`, `make_figures.py`, `compare_clean_rerun.py`, `table_check.py` and `number_check.py` |
| `05_manuscript_analysis_2026-10-29/results/` | Every output of the final analysis, including `RUN_MANIFEST.json` (settings, seeds, sample counts, input checksums, software versions) |
| `05_manuscript_analysis_2026-10-29/tables/` | The LaTeX tables of the manuscript, `manuscript_numbers.json` and the calibration figure for both benchmarks |
| `05_manuscript_analysis_2026-10-29/*_log.txt`, `05_manuscript_analysis_2026-10-29/*_RERUN_COMPARISON.txt` | Logs of the final runs and the comparisons with second, independent runs (byte-identical) |
| `02b_car_conventions_2026-10-29/` | The 90-transaction panel rebuilt from the June 2026 price cache, and the files used for the sample-construction counts (closing prices removed) |
| `04b_step4_verification_2026-10-29/Loss_Share_Negatives_Corroboration.csv` | Acquirer filings that confirm the "no loss share" coding for eight transactions |
| `stage1_car_rebuild_code/` | The Stage 1 code that mapped acquirers to listed parents and computed the returns from prices (provenance; see its README) |
| `requirements.txt`, `ENVIRONMENT.txt` | Software versions and runtimes |
| `reproduce.sh`, `MANIFEST.sha256`, `.github/workflows/check-manifest.yml` | Reproduction script, checksums, and a GitHub Actions check of the checksums on every push |
| `CHANGELOG.md`, `CITATION.cff`, `AUTHORS.md`, `LICENSE`, `LICENSE-DATA.md` | History of the releases, citation metadata, authors, licenses |

The date suffix of each folder (2026-10-29) records when that stage of the research folder was created; the files in
it are those of this release.

## Manuscript tables and figures

| Manuscript | Generated file (`05_manuscript_analysis_2026-10-29/tables/`) | Result files (`05_manuscript_analysis_2026-10-29/results/` unless stated) |
|---|---|---|
| Table 1, Spider interaction rules | - | `03_revised_framework_2026-10-29/code/snff_revised_features.py`, `03_revised_framework_2026-10-29/REVISED_FRAMEWORK_SPEC.md` |
| Table 2, Model 4 decision policies | `tab_model4.tex` | `table_decision_policies.csv`, `table_event_level_decision_policies.csv` and their `table_bank_*` counterparts |
| Table 3, utility and the loss-to-benefit ratio | `tab_sensitivity.tex` | `table_cost_ratio_sweep.csv`, `table_bank_cost_ratio_sweep.csv` |
| Table 4, summary of the four models | - | descriptive |
| Table 5, variables and their distribution | - | `03_revised_framework_2026-10-29/data/SNFF_Revised_Inputs_Primary55.csv`; checked by `number_check.py` |
| Table 6, SVB-First Citizens | `tab_svb.tex` | `svb_case.json`, `table_svb_deposit_stages.csv`, `table_svb_deposit_breakeven.csv` |
| Table 7, model comparison under both benchmarks | `tab_main.tex` | `table_main_comparison.csv`, `table_bank_main_comparison.csv`, `main_by_repeat.csv`, `bank_main_by_repeat.csv` |
| Table 8, paired comparisons | `tab_paired.tex` | `table_paired_differences.csv`, `table_cluster_bootstrap.csv`, `table_bootstrap_refit.csv` and their `table_bank_*` counterparts |
| Table 9, permutation tests | `tab_perm.tex` | `table_permutation_test.csv`, `table_permutation_coprimary.csv`, `permutation_null.csv`, `bank_permutation_null.csv` |
| Table 10, ablation | `tab_ablation.tex` | `table_ablation.csv`, `table_bank_ablation.csv` |
| Table 11, robustness | `tab_robustness.tex` | `table_robustness.csv`, `table_broader90.csv`, `table_event_level.csv`, `table_fbop_influence.csv`, `table_risk_validation.csv` and the `table_bank_*` counterparts |
| Table 12, expert weights and adjustments | `tab_weights.tex` | `weight_sensitivity_*.csv`, `table_weight_sensitivity*.csv` |
| Table 13, included and excluded transactions | `tab_selection.tex` | `selection_characteristics_94.csv`, `table_selection_*.csv` |
| Table 14, Spider score and components | `tab_components.tex` | `table_spider_components.csv`, `table_bank_spider_components.csv` |
| Table 15, Risk component | `tab_risk.tex` | `table_risk_validation.csv`, `table_risk_thirds.csv`, `table_risk_influence.csv` |
| Table 16, multi-bank purchases | `tab_events.tex` | `table_multibank_events.csv` |
| Table 17, implications for users | - | descriptive |
| Table 18 (Appendix), the 55 transactions | `tab_appendix.tex` | `appendix_primary55.csv`, `bank_out_of_fold_predictions.csv`, `05_manuscript_analysis_2026-10-29/data/Bank_Benchmark_CAR_90.csv`; sources in `03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv` |
| Figure 1, calibration under both benchmarks | `figure_calibration_coprimary.png` (`make_figures.py`) | `table_calibration_bins.csv`, `table_bank_calibration_bins.csv` |
| Figure 2, SHAP values | - | `figure_shap_fullsample.png`, `table_shap_fullsample.csv` (`final_analysis.py`) |

`results/figure_calibration.png`, the calibration figure for the S&P 500 benchmark alone, is an output of
`final_analysis.py` kept so that the result set is complete; the manuscript uses the two-benchmark figure.

## Data sources and redistribution

All transaction-level banking and acquisition data come from public sources: the FDIC Failed Bank List, the FDIC
BankFind Suite API, FDIC press releases, bid summaries and purchase and assumption agreements, and the acquirers' SEC
filings. Each coded deal term carries the URL of its source document.

The outcome is the three-day cumulative abnormal return of the acquirer's listed parent against SPY (and, as the
co-primary benchmark, an equal-weighted bank-sector portfolio). Daily adjusted closing prices were retrieved in June
2026 from Yahoo Finance with the `yfinance` library, with Financial Modeling Prep as a fallback. **The price series
are not redistributed.** The package contains only the derived event-window returns, abnormal returns and CARs that
define the outcome; the closing-price columns of the Stage 1 rebuild were removed. Three steps therefore cannot be
rerun from this package: the Stage 1 return build (`stage1_car_rebuild_code/`), the event-window report
(`03_revised_framework_2026-10-29/code/event_convention_report.py`) and the bank-sector benchmark (`05_manuscript_analysis_2026-10-29/code/bank_benchmark_cars.py`). Their
outputs are included, and each script documents the price file it expects. The scripts that built the variables
(`03_revised_framework_2026-10-29/code/build_*.py`) read the June 2026 Stage 1 files, which contain the BankFind call-report pulls and are kept by
the authors. Every analysis reported in the manuscript runs from the included files.

## Execution record

| Run | Date | Runtime | Independent rerun |
|---|---|---|---|
| `final_analysis.py` and `cluster_influence_check.py` (last complete run, release 4.5) | 2026-11-23 | 95 minutes | byte-identical, 73 files (`CLEAN_RERUN_COMPARISON.txt`) |
| `weight_sensitivity.py` (release 4.6) | 2026-11-24 | about 91 minutes | byte-identical, 9 files (`WEIGHT_SENSITIVITY_RERUN_COMPARISON.txt`) |
| `selection_comparison.py` (release 4.18, parents counted by holding company) | 2026-11-27 | about 1 second | byte-identical, 7 files (`SELECTION_RERUN_COMPARISON.txt`) |
| Verification of release 4.18 (`reproduce.sh --quick` on a fresh extraction, with the manuscript) | 2026-11-27 | 16 seconds | - |

Python 3.13.18 on Linux (x86-64), single-threaded; seed base 5000; 50 repeats of grouped, stratified 5-fold
cross-validation with 3-fold inner tuning; 400 permutations; 500 bootstrap refits (`RUN_MANIFEST.json`). The `date`
field of `RUN_MANIFEST.json` (2026-10-30) is a fixed constant of `final_analysis.py` that identifies the analysis
specification; it is not the execution date and is identical in every rerun. Releases 4.9 to 4.17 change only the
manuscript checks and the documentation. Release 4.18 counts acquiring parents by holding company in the comparison of
included and excluded transactions, which changes two of its result files and Table 13; no other result has changed
since release 4.8 (`CHANGELOG.md`).

## Key checksums (SHA-256, as recorded in `RUN_MANIFEST.json`)

* `SNFF_Revised_Inputs_Primary55.csv`: `f93d500de579853bcc19fb8da1a1743b9b6ec17e9753ff68d99eef57be1ad1b0`
* `SNFF_Revised_Inputs_Broader90.csv`: `6877dd4158f3f8e75cd3bf6c8d00b6ff434f643d98365300f4a0e43ec2e25d08`
* `Source_Verification_Ledger_90.csv`: `5c6622e2c697b24f575c2726d04023b2cd5dc17fe3dd8eb151db4a730fbd09c9`
* `Event_Convention_Comparison_90.csv`: `0bccf63a34c549e4d7df97509665dad1e98f03494d40b9435d5d6ab8f97bba84`
* `SNFF_Event_Inputs_Primary51.csv`: `2c123dc2f091ac8fd07f2abf6857d4a3d2a37bb72abe16c961cde6b033ee2b1f`
* `SNFF_Event_Consolidations.csv`: `c1fa85f7689139e04b6fc6ce4e14e4c32e42058b9803194a0973b38d8bd2dd07`
* `SVB_Deposit_Stages.csv`: `5cf2bdb345c302ce9e5918aec2d9f0e8e847825f6cc117ecf0cf097f5542c993`
* `snff_revised_features.py`: `45d8d44195e04a5fb1ba29afd55eba8c237be398e0f49ed0043d10c4172424f5`
* `Bank_Benchmark_CAR_90.csv`: `0af900a1df3fac26585d92a448d0945d861e93a15b4c83d7e2be75f07918aded`
* `final_analysis.py`: `a89353367e5acbcc3a4e28cae3235252afaf94db585aed60edb1fdbdaa635ae1`

`MANIFEST.sha256` lists every file of the release.

## Releases

Release 4.0 (2026-10-30), which accompanied the submitted manuscript, remains available in the repository history
(tag `v4.0`). Release 4.18 supersedes it and contains every change of releases 4.1 to 4.17, which were prepared during the
revision; see `CHANGELOG.md`. Release 4.17 remains available (tag `v4.17`; Zenodo DOI
[10.5281/zenodo.24558799](https://doi.org/10.5281/zenodo.24558799)).

## Citation and license

Cite the article and this release as described in `CITATION.cff`. A DOI will be added when the release is archived.
The code is released under the MIT License (`LICENSE`); the data compiled by the authors, the results, tables,
figures and documentation under CC BY 4.0 (`LICENSE-DATA.md`), which also describes the terms of the third-party
sources.

## Authors

Yousef Nejatbakhsh (Rutgers University), Malihe Aliasgari (Kean University, corresponding author), Parsa Safaee
(Eindhoven University of Technology) and Sina Shokoohyar (Seton Hall University). See `AUTHORS.md`.

Contact: Malihe Aliasgari, Department of Mathematical Sciences, Kean University.

## Permanent Archive and DOI

Release 4.18 will be archived on Zenodo as a new version of the record, under its own DOI, which will be added here.
Release 4.17 is permanently archived under DOI [10.5281/zenodo.24558799](https://doi.org/10.5281/zenodo.24558799).

Researchers using the datasets, software, or statistical results are encouraged to cite both the original article and the archived replication package.
