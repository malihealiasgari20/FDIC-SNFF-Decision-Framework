# Changelog

## Release 4.17 (2026-11-25)

### Publication release: licenses, quick verification, cleaned documentation; no analysis changes

Release 4.17 prepares the package for publication on GitHub and accompanies the final revised manuscript. No
analysis script, data file, result file or table changes: the 89 result files, the 14 tables, both figures and
every data file and analysis script are byte-identical to those of release 4.16, and every analysis script is
byte-identical to the code that produced the released results (`final_analysis.py` matches the checksum recorded in
`RUN_MANIFEST.json`).

Added:

| File | Content |
|---|---|
| `LICENSE` | MIT License for the code |
| `LICENSE-DATA.md` | CC BY 4.0 for the data compiled by the authors, the results, tables, figures and documentation; terms of the third-party sources; statement that historical stock prices are not redistributed |
| `stage1_car_rebuild_code/README.md` | Description of the Stage 1 provenance code (replaces the working notes `README_REVISION.md`) |

Removed, as not part of the research record:

| File | Reason |
|---|---|
| `GITHUB_PUBLISHING_GUIDE.md` | Instructions to the authors for uploading the package |
| `05_.../code/fill_manuscript.py`, `fill_reports.py` | Filled a manuscript template and internal report templates that are not in the package; the final manuscript is checked by `table_check.py` and `number_check.py` |
| `stage1_car_rebuild_code/README_REVISION.md` | Working notes of the October 2026 data audit, replaced by `README.md` |

Changed:

| File | Change |
|---|---|
| `reproduce.sh` | New `--quick` mode (under a minute): starts from the released results, reruns Model 2 in all 50 partitions (`cluster_influence_check.py`) and the comparison of included and excluded transactions, regenerates the tables and the figure, and runs the financing and manuscript checks; the full mode is unchanged |
| `README.md` | Rewritten: quick start, steps of `reproduce.sh`, repository layout, map of the manuscript's tables and figures to the files, data sources and redistribution, execution record, licenses. The key checksum of `final_analysis.py`, which had shown the release 4.4 value since release 4.5, now shows the value recorded in `RUN_MANIFEST.json`, as do all key checksums |
| `CITATION.cff` | Release 4.17 and its date (release 4.16 gave 2026-11-24, the README 2026-11-25), licenses, repository URL, abstract |
| `ENVIRONMENT.txt` | Execution dates and runtimes of the released results; the `date` field of `RUN_MANIFEST.json` explained as the fixed specification date |
| `02b_car_conventions_2026-10-29/README.md` | The June 2026 price cache is stated to be kept by the authors and not redistributed |
| `CHANGELOG.md` | This entry; the entries of releases 4.9 to 4.12 describe their manuscript revisions by topic |
| `05_.../code/number_check.py` | Checks that the manuscript cites release 4.17 and states the licenses; it now makes 633 checks (631 in 4.16); all pass |
| `MANIFEST.sha256` | Release 4.17 |

Verification: from a fresh extraction of the release ZIP, `sha256sum -c MANIFEST.sha256` passes, and
`bash reproduce.sh --quick` with the manuscript passes every step (event inputs, Model 2 in all 50 partitions, the
selection comparison, all 89 result files, the 14 tables, the FDIC-financing check, `table_check.py` and
`number_check.py`). The full mode was not rerun, because no analysis changed; its last runs are listed in
`ENVIRONMENT.txt`.

## Release 4.16 (2026-11-25)

### When the deal terms become public, in Sections III-B, V-D and VIII-F; no analysis changes

Release 4.16 accompanies the last two textual corrections. No analysis script, data file, result file or table changes:
the 89 result files and the 14 tables are byte-identical to those of release 4.15.

`number_check.py` checks that Section III-B, the investor's problem in Section V-D and the fourth limitation in Section
VIII-F say that the deal terms become public through the FDIC's announcement, the acquirer's later disclosures or, for
regulatory support, earlier announcements, and that SVB's support was announced two weeks before its acquisition; the
announcement-only wording is checked to be gone. It now makes 631 checks (624 in 4.15); all pass.

| File | Change |
|---|---|
| `05_.../code/number_check.py` | checks of the corrected passages and of the release cited |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.16 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.15 (2026-11-25)

### Price recovery stated as possible, and when investors learn the deal terms; no analysis changes

Release 4.15 accompanies two textual corrections to the manuscript. No analysis script, data file, result file or table
changes: the 89 result files and the 14 tables are byte-identical to those of release 4.14.

`number_check.py` checks the corrected passages: Section VII-F and the future work now say that the historical prices of
the 13 transactions of seven still-listed parents may be recoverable through improved ticker mapping and price retrieval,
and that a database of delisted securities may help for the other 26 (17 parents), rather than that the prices are
available; Section V-D now says that outside investors generally learn the deal terms from the FDIC announcement or later
acquirer disclosures, and that some support arrangements may be public before the announcement. The superseded wording
is checked to be gone. It now makes 624 checks (618 in 4.14); all pass.

| File | Change |
|---|---|
| `05_.../code/number_check.py` | checks of the corrected passages and of the release cited |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.15 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.14 (2026-11-25)

### Weight sensitivity by benchmark, the missing prices, and the bidder's information; no analysis changes

Release 4.14 accompanies three further corrections to the manuscript. No analysis script, data file, result file or
table changes: the 89 result files and the 14 tables are byte-identical to those of release 4.13.

`number_check.py` checks the corrected passages against the result files:

- Weight sensitivity (Abstract, Introduction, VII-E, Conclusion): the 2,025 alternatives apply to the Spider score and
  225 alternatives (226 sets with the reference) to the refitted Model 3. Against the S&P 500, 4 of the 226 sets rank
  above ridge regression, by at most 0.002 (best Model 3 AUC 0.634); against the bank-sector benchmark, all 226 rank
  above it, by 0.128 to 0.155, and all stay below one half (at most 0.435) (`weight_sensitivity_model3.csv`).
- Missing prices (Limitations, future work): the 26 and 13 excluded transactions are described by their parents' later
  status, without asserting that delisting caused each failed price retrieval.
- Bidder's information (Abstract, V-D, VII-D, Discussion): no statement that the deal terms were known only to the
  winning bidder contradicts SVB's publicly announced support.

It now makes 618 checks (603 in 4.13); all pass.

| File | Change |
|---|---|
| `05_.../code/number_check.py` | checks of the corrected passages and of the release cited |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.14 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.13 (2026-11-25)

### Checks for six qualified passages and the restructured abstract; no analysis changes

Release 4.13 accompanies the final consistency revision of the manuscript, which resolves six issues of the audit of
release 4.12. No analysis script, data file, result file or table changes: the 89 result files are byte-identical to
those of releases 4.8 to 4.12, and the 14 generated tables to those of release 4.12.

`number_check.py` checks the revised passages against the result files:

- Event level (Section VII-K, Conclusion): every fitted model's event-level AUC is below its transaction-level AUC
  against the S&P 500 and above it, but below one half, against the bank-sector benchmark; seven of the eight fitted
  models (all but the LASSO model, 0.518 against 0.472) move closer to one half against the S&P 500 and all eight
  against the bank-sector benchmark; the Spider score moves the other way under both (`table_event_level.csv`,
  `table_bank_event_level.csv`, `table_main_comparison.csv`, `table_bank_main_comparison.csv`).
- Weights (Abstract, Introduction, VII-E, Discussion, Conclusion): the qualified statements, with 124 of the 1,000
  sign-preserving sets placing the score above one half, Model 3 refitted for 226 of the 2,026 sets, and no set beating
  ridge regression by more than 0.002; the unqualified phrases are gone.
- Selection (Introduction, V-A, Discussion, Limitations, Conclusion): the 39 transactions are described as those whose
  prices were not collected, with 26 (17 parents) delisted and 13 (7 parents) not retrieved, and the counts add up.
- Significance and power (VII-B, Limitations): the 0.65 to 0.66 null 95th percentiles are described as critical values,
  not as power, which was not estimated.
- Hypothetical payoffs (VII-J, VII-L, VIII-C): the remaining passages that stated decision costs as facts now call the
  payoffs hypothetical or assumed.
- Abstract: leads with the finding, keeps every reported figure, and stays within 250 words.

It now makes 603 checks (557 in 4.12); all pass.

| File | Change |
|---|---|
| `05_.../code/number_check.py` | checks of the revised passages and of the release cited |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.13 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.12 (2026-11-24)

### Pursue counts relative to n, a shortened manuscript and consistent terminology; no analysis changes

Release 4.12 accompanies the manuscript's revision for conciseness and editorial consistency.
No analysis script, data file or result file changes: the 89 result files are byte-identical to those of releases 4.8
to 4.11.

Tables 2 and 3 now state each Pursue count relative to the number of observations: the column header reads "Pursue
(of n)" in Table 2 and "Pursue (of 55)" in Table 3, and the note of Table 2 gives the reading, e.g., 3.1 of 55
transactions for Configuration 4A against the S&P 500 (from `table_decision_policies.csv`). Every row of both tables is
unchanged. The note of Table 6 calls the acquirer First Citizens, the caption of Table 11 reads "Samples", and the
note of Table 12 cites Eqs. (7) and (8) in the manuscript's style.

`number_check.py` follows the manuscript's shortened literature review, case study, discussion and conclusion, which
remove repeated passages but no reported number: the checks of sentences that were reworded now check the new wording,
and the checks of passages that were removed from the Discussion and Conclusion as repetitions of the Results now
check that the claims still hold or that the passages are gone. New checks cover the Pursue counts relative to n in Table
2 and Section VII-J, that "First-Citizens" appears only in the bank's official name, that AUC and F1 are defined at
their first use, the definitions of CRSP and SPY, the equation-reference style and the release cited. It now makes 557
checks (535 in 4.11); all pass.

| File | Change |
|---|---|
| `05_.../code/make_tex_tables.py` | Tables 2 and 3: Pursue counts headed "(of n)" and "(of 55)"; Table 2 note; Table 6 note (First Citizens); Table 11 caption; Table 12 note (Eqs.) |
| `05_.../tables/tab_model4.tex`, `tab_sensitivity.tex`, `tab_svb.tex`, `tab_robustness.tex`, `tab_weights.tex` | regenerated: headers, captions and notes only, every row unchanged |
| `05_.../code/number_check.py` | checks of the revised passages, the terminology, the abbreviations and the release cited |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.12 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.11 (2026-11-24)

### Checks for the restructured title, abstract, introduction, discussion and conclusion; no analysis changes

Release 4.11 accompanies the manuscript's revision that restructures the paper to lead with
its empirical finding: the Spider interaction features show no reliable improvement over logistic models on the same
inputs, and the ablation traces the shortfall to the interaction rules rather than the component scores. The title
changes to "Do Interaction Rules Improve Decisions on FDIC-Assisted Bank Acquisitions? A Leakage-Controlled Evaluation
of the Spider Network Filtering Framework". No analysis script, data file or result file changes: the 89 result files
are byte-identical to those of releases 4.8 to 4.10.

`number_check.py` checks the new title, the abstract's figures (the three models' AUCs against the S&P 500, the 2,025
alternative weightings, the 51 events), the introduction's contribution statement (the ablation's 0.630, 0.632 and 0.598
from `table_ablation.csv`; the 39 excluded transactions; the smallest Holm-adjusted p-value; the F1-tuned rule's 62.9%
approval of negatively received acquisitions and its utility of -0.184 under the hypothetical 3:1 payoffs, from
`table_decision_policies.csv`), the Discussion's lead sentence, the Conclusion's ablation sentence and the caption of
Table 17, and that the ablation's ordering (B within 0.005 of A, C below A against the S&P 500; C between A and one half
against the bank-sector benchmark) holds. It now makes 535 checks (518 in 4.10); all pass.

| File | Change |
|---|---|
| `05_.../code/number_check.py` | checks of the restructured passages and of the release cited |
| `README.md`, `CITATION.cff` | the revised title of the paper; release 4.11 |
| `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.11 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.10 (2026-11-24)

### The two Spider-score AUCs: a note relating them; no analysis changes

Release 4.10 accompanies the manuscript's revision of the Spider-score AUC notes. No analysis script, data file or result
file changes: the 89 result files are byte-identical to those of releases 4.8 and 4.9.

The Spider score has two AUCs in the manuscript. Table 7 reports its out-of-sample AUC, the mean over 50 partitions of
the repeated grouped cross-validation, with normalization bounds and thresholds fitted inside each training fold (0.423
against the S&P 500, 0.505 against the bank-sector benchmark; `table_main_comparison.csv`,
`table_bank_main_comparison.csv`). Table 14 reports its descriptive AUC on the full panel, with bounds and thresholds
fitted once on all 55 transactions (0.414 and 0.516; `table_spider_components.csv`, `table_bank_spider_components.csv`).
Neither uses the outcome, so the values differ only through how the bounds and thresholds are estimated.

| File | Change |
|---|---|
| `05_.../code/make_tex_tables.py` | Table 14: caption "Descriptive, Full-Panel AUC" and a note relating its Spider-score AUCs to Table 7's; Table 7: a note sentence pointing to Table 14 |
| `05_.../tables/tab_components.tex`, `tab_main.tex` | regenerated: caption and notes only, every row unchanged |
| `05_.../code/number_check.py` | checks the note, the new sentences in VII-A, VII-H and IX, and the release cited (518 checks; 510 in 4.9) |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.10 |

No analysis was rerun. A dry run of `reproduce.sh` on the release, with the manuscript, reproduces all 89 result files
and the tables and passes the FDIC-financing check, `table_check.py` (14 tables) and `number_check.py`.

## Release 4.9 (2026-11-24)

### Checks for four revised passages of the manuscript; no analysis changes

Release 4.9 accompanies the manuscript's revised discussion of the FBOP cluster, power, the decision problem and costs. No
analysis script, data file or result file changes: the 89 result files are byte-identical to those of release 4.8.
The changes are to the checks of the manuscript's numbers, to the captions and notes of two tables, and to the
documentation.

* The FBOP cluster and benchmark dependence (new Discussion subsection VIII-A). Every number in it comes from released
  results: `table_fbop_influence.csv` (AUCs with and without the cluster), `table_rank_by_group.csv` and
  `table_bank_rank_by_group.csv` (mean percentile ranks of the cluster and of the other positive and negative
  transactions), `table_event_level.csv` and `table_bank_event_level.csv` (the 51 events), `table_permutation_coprimary.csv`,
  `table_bootstrap_refit.csv` and `table_bank_bootstrap_refit.csv`, `table_multibank_events.csv` (the consolidated FBOP
  score), and `data/Bank_Benchmark_CAR_90.csv` (the cluster's CARs and the two benchmarks' window returns). The counts of
  positive-negative pairs (140 of 700 against the S&P 500, 64 of 624 against the bank-sector benchmark; 6% and 3% of the
  pairs at the event level) are computed from the labels.
* Statistical power and nonsignificant results (Abstract, VII-B, VII-E, VII-L, VIII, VIII-F, IX): the smallest
  Holm-adjusted p-value (0.13), the null distributions' 95th percentiles (0.65 to 0.66), and the refitting-bootstrap
  intervals, from `table_permutation_test.csv`, `table_permutation_coprimary.csv` and the bootstrap tables.
* The decision problem (Abstract, V-D, VIII-D, VIII-F, IX): the published-inputs AUCs under both benchmarks, from
  `table_robustness.csv` and `table_bank_robustness.csv`, and the Protection weights and rule Q's condition against
  their definitions.
* The cost scenario (Abstract, IV-D, VII-J, VIII-C, VIII-F, IX): the sweep's range (1:1 to 5:1) from
  `table_cost_ratio_sweep.csv` and the utilities' loss ratio (L = 3) from `table_decision_policies.csv`.

`number_check.py` also checks that the phrases the revision withdrew no longer appear (for example "show no ranking
ability", "rank them no better than chance", "conservative 3:1"). It now makes 510 checks (429 in 4.8); all pass.

### Files changed

| File | Change |
|---|---|
| `05_.../code/number_check.py` | checks of the four revised passages and of the release cited |
| `05_.../code/make_tex_tables.py` | Table 2 caption "Utility under the Hypothetical Payoffs"; its note "utility under the assumed payoffs"; Table 3 note "Each ratio is a hypothetical scenario" |
| `05_.../tables/tab_model4.tex`, `tab_sensitivity.tex` | regenerated: caption and notes only, every row unchanged |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256`, `reproduce.sh` | release 4.9 |

### Reproduction

No analysis was rerun, because no analysis script or input changed. A dry run of `reproduce.sh` on the release, with
the manuscript, reproduces all 89 result files and the tables and passes the FDIC-financing check, `table_check.py`
(14 tables) and `number_check.py`.

## Release 4.8 (2026-11-24)

### New: balance and overlap diagnostics of the reweighting of included and excluded transactions

Release 4.7 reweighted the out-of-fold predictions of the 55 transactions of the panel by the inverse of their
estimated probability of inclusion among the 94 eligible transactions. Following the same reviewer comment, release
4.8 reports how well the weights balance the panel against all 94 and how much they rest on few transactions.
`selection_comparison.py` gains two outputs, computed after its five outputs of release 4.7, which are byte-identical
to those of 4.7; nothing is refitted.

* `05_.../results/table_selection_balance.csv`: for the four characteristics of the inclusion model (acquiring bank's
  log assets and capital, the 2008-2010 period, the NPL ratio) and five others (log failed-bank assets and deposits,
  NPL change, deposit change, log relative size), the mean of all 94, of the 39 excluded and of the 55 included,
  unweighted and with each weighting, and the standardized difference: mean of the included, weighted as in the
  column, minus the mean of all 94, divided by the standard deviation of all 94.
* `05_.../results/table_selection_weight_diagnostics.csv`: the range of the estimated inclusion probabilities in each
  group, the excluded transactions below the lowest included probability, and for each weighting (weights normalized
  to a mean of one) the smallest, median and largest weight, the largest weight's share of the total, and the
  effective sample size (squared sum of the weights over the sum of their squares).

Means and standardized differences of the included transactions from all 94 (absolute values below 0.1 are
conventionally read as balance):

| Characteristic | Mean, all 94 | Mean, excluded | Mean, included | Unweighted | Weighted | Truncated at p95 |
|---|---|---|---|---|---|---|
| log acquiring bank assets (model) | 2.42 | 1.48 | 3.08 | 0.376 | -0.156 | 0.022 |
| acquiring bank capital C, % (model) | 10.88 | 11.92 | 10.14 | -0.269 | 0.103 | -0.009 |
| failed in 2008-2010, share (model) | 0.74 | 0.85 | 0.67 | -0.164 | 0.072 | 0.007 |
| NPL ratio N, % (model) | 15.65 | 17.84 | 14.09 | -0.138 | 0.248 | -0.004 |
| log failed bank assets | 0.34 | -0.05 | 0.61 | 0.190 | -0.018 | 0.048 |
| log failed bank deposits G | 0.17 | -0.18 | 0.42 | 0.182 | -0.014 | 0.045 |
| NPL change T, pp | 4.69 | 4.46 | 4.85 | 0.020 | 0.556 | 0.165 |
| deposit change L, % | -4.01 | -3.79 | -4.17 | -0.015 | 0.090 | 0.036 |
| log relative size M | -2.08 | -1.53 | -2.47 | -0.258 | 0.166 | 0.020 |

Before weighting, seven of the nine differences are 0.1 or more in absolute value. The untruncated weights reverse the
sign of all four differences of the inclusion model and leave five of the nine at 0.1 or more, with 0.556 for the NPL
change; the truncated weights leave the four within 0.03 and the others within 0.05, except the NPL change (0.165).

Overlap: estimated inclusion probability 0.072-0.997 among the included and 0.040-0.872 among the
excluded; 3 excluded transactions (PA-0260, PA-0316, PA-0491) lie below the lowest included. Weights:
largest 7.38 (PA-0309), 13.4% of the total, effective sample 27.2 of 55; truncated at the 95th
percentile: largest 2.63, 4.8% of the total, effective sample 42.8.

The manuscript's table of the comparison (`tables/tab_selection.tex`) gains a row with the listed parents (28
included; 24 excluded: 17 later acquired, with 26 of the transactions, and 7 still listed, with 13), the effective
sample sizes in Panel B, and Panel C with the balance.

### Files changed

| File | Change |
|---|---|
| `05_.../code/selection_comparison.py` | two new outputs (above); its five earlier outputs are unchanged |
| `05_.../results/table_selection_balance.csv`, `table_selection_weight_diagnostics.csv` (new) | its new results |
| `05_.../selection_comparison_log.txt`, `05_.../SELECTION_RERUN_COMPARISON.txt` | the log of the run (two new lines) and the comparison with the second run |
| `05_.../code/make_tex_tables.py` | `tables/tab_selection.tex`: parents row, effective sample sizes, Panel C, revised note |
| `05_.../code/number_check.py` | checks the revised prose on the excluded transactions, the balance and overlap figures, and the release cited |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | section "Included and excluded transactions": transactions and parents counted separately (the 13 still-listed transactions have 7 parents, not 13), and the diagnostics |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.8 |
| `reproduce.sh` | release 4.8 |

### Rerun and reproduction

`final_analysis.py`, `cluster_influence_check.py` and `weight_sensitivity.py` are unchanged, so every result of
release 4.6 is unchanged and was not rerun. `selection_comparison.py` was run twice, each run from its own copy of
the package and on its own copy of the 4.6 results, in two separate processes; the two runs produce byte-identical
files (all seven), the five files of 4.7 are byte-identical to those released in 4.7, and the 82 result files of 4.6
are byte-identical in both. The first run is the release.

## Release 4.7 (2026-11-24)

### New: the 55 transactions of the panel and the 39 eligible transactions without price data

Of the 150 largest eligible failures, 94 were acquired by a bank with a U.S.-listed parent; the price data of the
study cover 55 (the primary panel). Following a reviewer's comment, release 4.7 compares them with the other 39.

* `03_.../data/Excluded39_Parent_Status.csv`: for each of the 39, why the price data do not cover the parent (from
  the Stage 1 rebuild's ticker notes) and whether the parent was later acquired (26 transactions, 17 parents; event,
  date and source) or still trades (13 transactions: FFBC x3, SCBT/SSB x2, HFWA, HOMB x2, RBCAA, HTH, and
  NYCB/FLG x3).
* `03_.../data/Excluded39_Buyer_Call_Reports.csv`: assets, total equity (EQTOT) and bank equity (EQ) of the acquiring
  banks of the 39 at the last quarter-end at least 90 days before each failure (34 reports, FDIC BankFind API,
  retrieved 2026-11-24, with the query URL of each; every assets and bank-equity value was retrieved twice with
  identical results), and five reports of panel acquirers that reproduce the released buyer inputs exactly. The
  released buyer capital uses total equity, EQTOT: for two of the five checks it differs from EQ.
* `05_.../code/selection_comparison.py` (new; run after the final analysis, about one second): measures every
  characteristic of the 94 as for the model inputs (the failed-bank rule reproduces the released inputs of all 90
  listed-acquirer transactions exactly), compares the groups with a two-sided permutation test that reassigns
  inclusion across the 52 listed parents (10,000 permutations, seed 20261124), evaluates the released out-of-fold
  predictions of the 55 by acquirer size, and reweights them by the inverse of an estimated probability of
  inclusion (logistic model on the acquiring bank's log assets and capital, the 2008-2010 period and the NPL
  ratio). Nothing is refitted.

Median [quartiles]; AUC: probability that an included transaction has the higher value (two-sided permutation p;
Holm across the nine characteristics):

| Characteristic | Included (55) | Excluded (39) | AUC (p) | Parent acquired (26) | Parent listed (13) |
|---|---|---|---|---|---|
| failed in 2008-2010 (share) | 67% | 85% | 0.413 (0.076; Holm 0.302) | 92% | 69% |
| acquiring bank assets, USD bn | 15.82 [4.16, 88.19] | 4.04 [2.21, 9.29] | 0.766 (0.006; Holm 0.058) | 5.79 | 3.03 |
| acquiring bank capital C, % | 9.35 [8.60, 11.63] | 12.19 [9.66, 13.55] | 0.300 (0.028; Holm 0.223) | 10.30 | 12.48 |
| failed bank assets, USD bn | 1.11 [0.54, 3.56] | 0.60 [0.48, 1.17] | 0.662 (0.033; Holm 0.228) | 0.59 | 0.61 |
| failed bank deposits G, USD bn | 1.00 [0.50, 2.63] | 0.52 [0.42, 1.11] | 0.653 (0.043; Holm 0.250) | 0.50 | 0.54 |
| NPL ratio N, % | 13.96 [9.00, 17.23] | 15.10 [10.98, 20.91] | 0.426 (0.297; Holm 0.890) | 15.95 | 13.14 |
| NPL change T, pp | 2.80 [0.70, 6.56] | 4.38 [0.08, 6.72] | 0.488 (0.843; Holm 1.000) | 4.87 | 0.14 |
| deposit change L, % | -4.54 [-11.71, 1.06] | -5.39 [-8.94, 0.02] | 0.494 (0.924; Holm 1.000) | -5.01 | -6.68 |
| relative size M | 0.13 [0.03, 0.27] | 0.23 [0.11, 0.46] | 0.332 (0.042; Holm 0.250) | 0.19 | 0.37 |

Mean AUC over the 50 partitions (out-of-fold predictions of the main comparison; reweighting: effective sample
27.2 of 55, 42.8 with the weights truncated at their 95th percentile):

| Transactions | Model 2 | Ridge | Model 3 | Spider score |
|---|---|---|---|---|
| S&P 500, all 55 | 0.615 | 0.632 | 0.594 | 0.423 |
| S&P 500, acquiring bank <= USD 9.2 bn (19) | 0.321 | 0.358 | 0.319 | 0.478 |
| S&P 500, acquiring bank > USD 9.2 bn (36) | 0.744 | 0.755 | 0.717 | 0.419 |
| S&P 500, reweighted to all 94 | 0.389 | 0.405 | 0.386 | 0.490 |
| S&P 500, reweighted, truncated at p95 | 0.505 | 0.526 | 0.497 | 0.449 |
| bank-sector index, all 55 | 0.277 | 0.280 | 0.413 | 0.505 |
| bank-sector index, acquiring bank <= USD 9.2 bn (19) | 0.238 | 0.199 | 0.229 | 0.569 |
| bank-sector index, acquiring bank > USD 9.2 bn (36) | 0.283 | 0.304 | 0.489 | 0.490 |
| bank-sector index, reweighted to all 94 | 0.216 | 0.211 | 0.310 | 0.548 |
| bank-sector index, reweighted, truncated at p95 | 0.276 | 0.270 | 0.389 | 0.510 |

### Files changed

| File | Change |
|---|---|
| `03_.../data/Excluded39_Parent_Status.csv`, `03_.../data/Excluded39_Buyer_Call_Reports.csv` (new) | see above |
| `05_.../code/selection_comparison.py` (new) | the comparison |
| `05_.../results/selection_characteristics_94.csv`, `selection_inclusion_weights.csv`, `table_selection_comparison.csv`, `table_selection_size_classes.csv`, `table_selection_reweighted.csv` (new) | its results |
| `05_.../selection_comparison_log.txt`, `05_.../SELECTION_RERUN_COMPARISON.txt` (new) | the log of the run and the comparison with the second run |
| `05_.../code/make_tex_tables.py` | new table `tables/tab_selection.tex` |
| `05_.../code/number_check.py` | checks the new prose and the release cited |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | section "Included and excluded transactions" |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.7 |
| `reproduce.sh` | release 4.7; step 2 also runs `selection_comparison.py` |

### Rerun and reproduction

`final_analysis.py`, `cluster_influence_check.py` and `weight_sensitivity.py` are unchanged, so every result of
release 4.6 is unchanged and was not rerun. `selection_comparison.py` was run twice, each run from its own copy of
the package and on its own copy of the 4.6 results, in two separate processes; the two runs produce byte-identical new
files, and the 82 result files of 4.6 are byte-identical in both. The first run is the release.

## Release 4.6 (2026-11-24)

### New: sensitivity to the expert weights and interaction adjustments

The Spider score uses expert constants: S = 0.30 V + 0.20 P + 0.20 B - 0.20 R - 0.10 E and
S* = S + 0.08 Q + 0.07 U - 0.10 Z - 0.06 K. Following a reviewer's comment, the new script
`05_.../code/weight_sensitivity.py` evaluates alternatives, defined before any of them was evaluated, with the
design of the main comparison (the 50 partitions of each benchmark, Model 3's inner tuning unchanged). The expert constants
remain the reference specification, and no constant is chosen on the full sample:

* each constant changed alone (a weight times 0.5 or 1.5, the five then rescaled to sum to one; an adjustment
  times 0, 0.5 or 1.5), equal weights, no adjustments, and both;
* 1,000 draws within +/-50% of every constant (seed 20261124) and 1,000 sign-preserving draws over the whole
  range (weights uniform on the simplex, adjustments between zero and twice their value; seed 20261125);
* constants chosen inside each training fold from either set by the training-fold AUC, scored on the held-out
  fold, with a permutation test that reruns the choice on 400 cluster permutations (the draws and partitions of
  the main permutation test, whose Spider-score null it reproduces exactly).

The Spider score and Configuration 4A are evaluated for every variant; Model 3 and Configurations 4B and 4C are
refitted for the reference, the 25 structured variants and the first 100 draws of each random set. The
reference reproduces the released Spider-score, Model 3 and policy results of both benchmarks exactly (the
script stops otherwise). Mean AUC over 50 partitions (median [min, max] over a set):

| Constants | Spider, SPY | Model 3, SPY | Model 3 - ridge, SPY | Spider, bank | Model 3, bank | Model 3 - ridge, bank |
|---|---|---|---|---|---|---|
| expert constants (reference) | 0.423 | 0.594 | -0.038 | 0.505 | 0.413 | 0.133 |
| one constant changed (22) | 0.426 [0.398, 0.462] | 0.594 [0.589, 0.604] | -0.038 [-0.043, -0.029] | 0.505 [0.463, 0.545] | 0.413 [0.411, 0.418] | 0.133 [0.131, 0.138] |
| equal weights / no adjustments (3) | 0.390 [0.355, 0.396] | 0.602 [0.595, 0.604] | -0.030 [-0.037, -0.028] | 0.491 [0.472, 0.504] | 0.415 [0.412, 0.416] | 0.136 [0.132, 0.136] |
| random within +/-50% (1,000; Model 3: 100) | 0.425 [0.357, 0.507] | 0.595 [0.587, 0.613] | -0.037 [-0.045, -0.020] | 0.503 [0.443, 0.549] | 0.413 [0.410, 0.421] | 0.134 [0.130, 0.141] |
| random, sign-preserving (1,000; Model 3: 100) | 0.419 [0.267, 0.607] | 0.597 [0.586, 0.634] | -0.035 [-0.047, 0.002] | 0.485 [0.393, 0.614] | 0.414 [0.408, 0.435] | 0.134 [0.128, 0.155] |

| Constants chosen inside the training folds | SPY | bank |
|---|---|---|
| chosen in each training fold from the +/-50% draws | 0.462 (training folds 0.516; two-sided p 0.82) | 0.483 (training folds 0.579; two-sided p 0.94) |
| chosen in each training fold from the sign-preserving draws | 0.541 (training folds 0.627; two-sided p 0.78) | 0.471 (training folds 0.634; two-sided p 0.98) |

### Files changed

| File | Change |
|---|---|
| `05_.../code/weight_sensitivity.py` (new) | the sensitivity analysis, run after `final_analysis.py` and `cluster_influence_check.py` |
| `05_.../results/weight_sensitivity_*.csv`, `table_weight_sensitivity*.csv` (9 new files) | its results |
| `05_.../weight_sensitivity_log.txt`, `05_.../WEIGHT_SENSITIVITY_RERUN_COMPARISON.txt` (new) | the log of the run and the comparison with the second run |
| `05_.../code/make_tex_tables.py` | new table `tables/tab_weights.tex` |
| `05_.../code/number_check.py` | checks the new prose and the release cited |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | section "Sensitivity to the constants" |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.6 |
| `reproduce.sh` | release 4.6; step 2 also runs `weight_sensitivity.py` |

### Rerun and reproduction

`final_analysis.py` is unchanged, so every result of release 4.5 is unchanged and was not rerun.
`weight_sensitivity.py` was run twice, from the same copy of the package, in two separate processes (about
91 minutes each, run concurrently), each on its own copy of the 4.5 results; the two runs produce byte-identical
new files, and the 73 result files of 4.5 are byte-identical in both. The first run is the release.

## Release 4.5 (2026-11-23)

### New: the bank-sector benchmark as a co-primary outcome

The submitted paper used the SPY-adjusted CAR as its primary outcome and the bank-sector benchmark
(`05_.../data/Bank_Benchmark_CAR_90.csv`, unchanged) only as a robustness check. Following a reviewer's
comment, the revision reports the two as co-primary specifications. The bank-sector specification was
elevated during the revision; it was not designated as co-primary in advance. `final_analysis.py` (new
last section; every earlier result unchanged) repeats with the bank-sector labels, with the same design
and seeds, every analysis reported for the SPY outcome:

* all eight models and the Spider score (`bank_main_by_repeat.csv`, `table_bank_main_comparison.csv`,
  out-of-fold predictions, calibration bins, the FBOP rank), checked against the bank row of the
  robustness run, which the three core models reproduce exactly;
* the Model 4 policies and the cost-ratio sweep; the paired differences and the conditional cluster
  bootstrap; the refitting cluster bootstrap (500 replicates); the permutation test with the complete
  nested procedure (400 permutations x 3 partitions), with `table_permutation_coprimary.csv` giving
  one- and two-sided p-values for both benchmarks, Holm-adjusted within each, and the permutation
  distribution of Model 3's differences from Models 2 and ridge;
* the influence of the FBOP cluster on Models 2, ridge and 3 and the Spider score under both
  benchmarks (`table_fbop_influence.csv`; `cluster_influence_check.py` still checks Model 2);
* the robustness variants, the ablation, the broader panel, the 51 acquisition events with their
  policies, and the component AUCs.

Mean AUC and Brier score over 50 partitions:

| Model | AUC, SPY | AUC, bank | Brier, SPY | Brier, bank |
|---|---|---|---|---|
| Logistic regression (L2, C=1) | 0.615 | 0.277 | 0.238 | 0.273 |
| LASSO logistic | 0.518 | 0.461 | 0.249 | 0.217 |
| Ridge logistic | 0.632 | 0.280 | 0.225 | 0.234 |
| Decision tree | 0.585 | 0.383 | 0.291 | 0.326 |
| Random forest | 0.605 | 0.338 | 0.231 | 0.234 |
| XGBoost | 0.604 | 0.351 | 0.243 | 0.259 |
| LR + pairwise interactions | 0.632 | 0.396 | 0.216 | 0.248 |
| SNFF + LR (Model 3) | 0.594 | 0.413 | 0.232 | 0.232 |
| Spider score alone (Model 1) | 0.423 | 0.505 | --- | --- |

Permutation test (mean AUC over the three test partitions; two-sided p):

| Model | SPY | p | Bank | p |
|---|---|---|---|---|
| Model 2 (L2, C=1) | 0.635 | 0.24 | 0.350 | 0.21 |
| Ridge (C tuned) | 0.668 | 0.14 | 0.353 | 0.22 |
| Model 3 (Spider + LR) | 0.600 | 0.36 | 0.427 | 0.52 |
| Spider score (Model 1) | 0.421 | 0.36 | 0.507 | 0.94 |

Mean AUC with and without the FBOP cluster:

| Model | SPY, 55 | SPY, without FBOP | Bank, 55 | Bank, without FBOP |
|---|---|---|---|---|
| Model 2 (L2, C=1) | 0.615 | 0.498 | 0.277 | 0.418 |
| Ridge (C tuned) | 0.632 | 0.516 | 0.280 | 0.417 |
| Model 3 (Spider + LR) | 0.594 | 0.456 | 0.413 | 0.472 |
| Spider score (Model 1) | 0.423 | 0.460 | 0.505 | 0.475 |

Model 4 policies (mean number pursued, utility at 3:1):

| Policy | SPY | Bank |
|---|---|---|
| 4A: fixed Spider thresholds | 3.1, 0.041 | 2.9, 0.030 |
| 4B: F1-tuned threshold | 40.2, -0.184 | 50.2, -0.221 |
| 4C: cost-based threshold (3:1) | 11.8, -0.071 | 16.1, -0.066 |
| Pursue all | 55.0, -0.455 | 55.0, -0.164 |
| Pursue none | 0.0, 0.000 | 0.0, 0.000 |

### Files changed

| File | Change |
|---|---|
| `05_.../code/final_analysis.py` | bank-benchmark co-primary section, run last |
| `05_.../code/make_tex_tables.py` | Tables 2, 3, 7-12 with an S&P 500 panel and a bank-sector panel (Table 2: Panels A-D); Table 13 labels; the appendix table gives the bank-sector CAR and label of each transaction |
| `05_.../code/make_figures.py` (new) | the calibration figure for both benchmarks, `tables/figure_calibration_coprimary.png`, drawn from the quintile bins of both |
| `05_.../code/number_check.py` | checks the new prose on the two benchmarks and the release cited |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | section "Two co-primary benchmarks" (decision 6, SPY only, superseded) |
| `05_.../results/`, `tables/`, `run_log.txt`, `CLEAN_RERUN_COMPARISON.txt` | complete rerun |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.5 |
| `reproduce.sh` | release 4.5; step 4 also redraws the calibration figure (compared, but not counted, like the figures in `results/`) |

### Rerun and reproduction

`final_analysis.py` and `cluster_influence_check.py` were run twice, from the same copy of the
package, in two separate processes (95 minutes each, run concurrently). The two runs produce
byte-identical result files (73 files; `RUN_MANIFEST.json` equal except the runtime). The
first run is the release. Compared with release 4.4, the 44 result files of 4.4 other than
`RUN_MANIFEST.json` are byte-identical, the 28 bank-benchmark files are new, and `RUN_MANIFEST.json`
differs in the checksum of `final_analysis.py` and the runtime.

## Release 4.4 (2026-11-23)

### New: SVB's deposits at three dates (retrospective)

The Value input is the failed bank's deposit base at its last public call report, the only deposit
figure that is public before the failure and measured the same way for every transaction. For SVB,
the one bridge-bank sale of the panel, deposits fell from $175.4 billion at that report (December 31,
2022) to about $119 billion at failure (March 10, 2023, FDIC PR-23-2023) and $55.96 billion assumed
by First Citizens (March 27, 2023, First Citizens' Q1 2023 earnings release). Release 4.4 records
the three figures and their sources and scores the later two retrospectively, one at a time, in place
of the call-report figure of the SVB case. They are dated after the failure, lie outside the
information set, and are used nowhere else; the panel's inputs are unchanged.

* `03_.../data/SVB_Deposit_Stages.csv`: SVB's deposits and assets at the three dates, with the
  document and URL of each figure (the call-report row is checked against the inputs).
* `final_analysis.py` (new last section, no random numbers; every earlier result unchanged) writes
  `table_svb_deposit_stages.csv` (each figure scored with the full-panel Spider fit of Table 6 and
  with a fit on the other 54 transactions; the assets of the same date enter the relative size, which
  stays above its cap) and `table_svb_deposit_breakeven.csv` (deposits at which the case reaches the
  Pursue threshold on each set of bounds).

SVB case with the deposits of each date (variant: deposits and assets):

| Deposits at | USD bn | V | S* | Rank of S* (of 55) | S~, bounds of all 55 | S~, bounds of other 54 |
|---|---|---|---|---|---|---|
| Last call report, 2022-12-31 | 175.378 | 0.931 | 0.443 | 1 | 1.000 Pursue | 1.000 Pursue |
| At failure, 2023-03-10 | 119 | 0.632 | 0.353 | 2 | 0.831 Pursue | 0.975 Pursue |
| Assumed by First Citizens, 2023-03-27 | 55.96 | 0.296 | 0.252 | 4 | 0.641 Caution | 0.753 Pursue |

Deposits needed for the Pursue zone: $75.6 billion on the bounds of all 55,
$40.9 billion on those of the other 54. Letting the deposit change L react as
well (rule U) adds 0.020 to each substituted S* and changes no zone.

### Files changed

| File | Change |
|---|---|
| `03_.../data/SVB_Deposit_Stages.csv` | new |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | section on SVB's deposits at three dates |
| `05_.../code/final_analysis.py` | SVB deposit-stages section, run last; the manifest records the checksum of the new data file |
| `05_.../code/make_tex_tables.py` | new `tab_svb.tex` (Table 6, Panels A and B), generated from the results |
| `05_.../code/table_check.py` | compares every tabular of a table (Table 6 has two) |
| `05_.../code/number_check.py` | checks the new prose on the SVB case and the release cited |
| `05_.../results/`, `tables/`, `run_log.txt`, `CLEAN_RERUN_COMPARISON.txt` | complete rerun |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `reproduce.sh`, `MANIFEST.sha256` | release 4.4 |

### Rerun and reproduction

`final_analysis.py` and `cluster_influence_check.py` were run twice, from the same copy of the
package, in two separate processes (79 minutes each, run concurrently). The two runs produce
byte-identical result files (45 files; `RUN_MANIFEST.json` equal except the runtime). The
first run is the release. Compared with release 4.3, the 42 result files of 4.3 other than
`RUN_MANIFEST.json` are byte-identical, the two SVB deposit-stage files are new, and
`RUN_MANIFEST.json` differs in the checksum of `final_analysis.py`, the added checksum of
`SVB_Deposit_Stages.csv` and the runtime.

## Release 4.3 (2026-11-23)

### New: the acquisition event as the unit of decision

An acquirer that buys several failed banks from the FDIC on one day makes one decision, and the
market prices it with one return: U.S. Bank's winning bids for the four FBOP subsidiaries of the
primary panel are linked bids in the FDIC bid summaries, and the FDIC announced the sale of all nine
FBOP banks as one transaction. The Spider score is not additive over banks (deposits and relative
size are sums; the flags and rules switch at thresholds), so an average of bank scores, even
asset-weighted, does not score that decision. Release 4.3 scores an acquisition event on the
consolidated call reports of all the banks its acquirer bought that day (definitions in
`03_.../REVISED_FRAMEWORK_SPEC.md`, section "Acquisition events").

* `03_.../data/Multi_Bank_Event_Call_Reports.csv`: assets, deposits, net loans and noncurrent loans
  of the 15 banks in the four multi-bank events of the primary panel, at the last public report and
  two quarters earlier (FDIC BankFind API, retrieved 2026-11-23, with the query URL of each bank).
  They reproduce every bank's inputs in the 90-transaction file to 9e-15.
* `03_.../code/build_event_inputs.py` builds `SNFF_Event_Inputs_Primary51.csv` (the 51 events of the
  primary panel, 62 banks, 34 events with a positive CAR), `SNFF_Event_Consolidations.csv` and
  `Event_Inputs_Report.txt`, after checking the call reports against the inputs and the events'
  completeness against the 502-failure inclusion log.
* `final_analysis.py` (new last section; every earlier result unchanged) writes
  `table_multibank_events.csv` (each bank alone, the consolidated event, and the simple and
  asset-weighted means of the bank scores, with the full-panel Spider fit of the SVB case) and
  repeats the model comparison and the Model 4 policies on the 51 events with the same seeds
  (`event_level_by_repeat.csv`, `table_event_level.csv`, `event_level_decision_policies_by_repeat.csv`,
  `table_event_level_decision_policies.csv`).

Rescaled Spider score and Model 1 band (banks alone; consolidated event; mean of the bank scores,
simple / asset-weighted):

| Event | Banks alone | Consolidated | Mean of bank scores |
|---|---|---|---|
| FBOP subsidiaries (U.S. Bank, 2009-10-30) | 0.511 Caution; 0.506 Caution; 0.510 Caution; 0.508 Caution; 0.505 Caution; 0.495 Caution; 0.487 Caution; 0.508 Caution; 0.289 Avoid | 0.527 Caution | 0.480 Caution / 0.508 Caution |
| Downey, PFF (U.S. Bank, 2008-11-21) | 0.474 Caution; 0.366 Avoid | 0.473 Caution | 0.420 Caution / 0.450 Caution |
| Wheatland, Lincoln Park (Wintrust, 2010-04-23) | 0.281 Avoid; 0.526 Caution | 0.312 Avoid | 0.404 Caution / 0.359 Avoid |
| Darby, Tifton (Ameris, 2010-11-12) | 0.536 Caution; 0.710 Pursue | 0.517 Caution | 0.623 Caution / 0.568 Caution |

FBOP restricted to its four banks in the primary panel: 0.527 Caution.

Mean AUC over 50 partitions (transactions; transactions with each event's predictions averaged;
acquisition events with consolidated inputs):

| Model | 55 transactions | Averaged by event | 51 events |
|---|---|---|---|
| Logistic regression (L2, C=1) | 0.615 | 0.551 | 0.541 |
| LASSO logistic | 0.518 | 0.479 | 0.472 |
| Ridge logistic | 0.632 | 0.575 | 0.561 |
| Decision tree | 0.585 | 0.533 | 0.566 |
| Random forest | 0.605 | 0.569 | 0.560 |
| XGBoost | 0.604 | 0.573 | 0.556 |
| LR + pairwise interactions | 0.632 | 0.568 | 0.548 |
| SNFF + LR (Model 3) | 0.594 | 0.529 | 0.509 |
| Spider score alone (Model 1) | 0.423 | 0.450 | 0.445 |

Model 4 policies (mean number pursued, utility at 3:1):

| Policy | 55 transactions | 51 events |
|---|---|---|
| 4A: fixed Spider thresholds | 3.1, 0.041 | 3.0, 0.036 |
| 4B: F1-tuned threshold | 40.2, -0.184 | 41.6, -0.313 |
| 4C: cost-based threshold (3:1) | 11.8, -0.071 | 11.8, -0.073 |
| Pursue all | 55.0, -0.455 | 51.0, -0.333 |
| Pursue none | 0.0, 0.000 | 0.0, 0.000 |

### Files changed

| File | Change |
|---|---|
| `03_.../data/Multi_Bank_Event_Call_Reports.csv`, `SNFF_Event_Inputs_Primary51.csv`, `SNFF_Event_Consolidations.csv`, `Event_Inputs_Report.txt` | new |
| `03_.../code/build_event_inputs.py` | new |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | section on acquisition events |
| `05_.../code/final_analysis.py` | acquisition-event section, run last; the manifest records the event counts and the checksums of the two event input files |
| `05_.../code/make_tex_tables.py` | Table 2 in two panels (transactions, events); Table 11 with the event row; new `tab_events.tex` |
| `05_.../code/number_check.py` | checks the new prose on acquisition events and the release cited |
| `05_.../results/`, `tables/`, `run_log.txt`, `CLEAN_RERUN_COMPARISON.txt` | complete rerun |
| `reproduce.sh` | new step 1b rebuilds the event inputs and compares them with the released files |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.3 |

### Rerun and reproduction

`final_analysis.py` and `cluster_influence_check.py` were run twice, from the same copy of the
package, in two separate processes (62 minutes each, run concurrently). The two runs produce
byte-identical result files (43 files; `RUN_MANIFEST.json` equal except the runtime). The
first run is the release. Compared with release 4.2, the 37 result files of 4.2 other than
`RUN_MANIFEST.json` are byte-identical, the five event-level files are new, and `RUN_MANIFEST.json`
differs in the checksum of `final_analysis.py`, the two added input checksums, the added event
counts and the runtime.

## Release 4.2 (2026-11-23)

### New: the Spider components on the 28 transactions with their own announcement return

Seven of the 35 broader-panel transactions outside the primary panel share the listed parent and
reaction day, and therefore the CAR, with a primary-panel transaction, so their outcomes are not
new observations:

* PA-0382, PA-0383, PA-0384, PA-0389, PA-0390: the five FBOP subsidiaries that U.S. Bank bought on
  30 October 2009 together with the four FBOP subsidiaries in the primary panel (PA-0385 to PA-0388);
* PA-0311 Lincoln Park Savings Bank, bought by Wintrust on the day it bought Wheatland Bank (PA-0309);
* PA-0225 Tifton Banking Company, bought by Ameris on the day it bought Darby Bank & Trust (PA-0224).

`final_analysis.py` now also evaluates the component AUCs (manuscript Table 12) and the Risk
component under the five outcome definitions (Table 13) on the other 28 transactions (27 event
clusters, 20 with a positive CAR). The 28 are evaluated after the 55 and the 35, so the permutation
draws behind the earlier results, and those results, are unchanged. The seven, with the
primary-panel transactions of the same event, are listed in `results/broader_only_shared_events.csv`.
Tables 12 and 13 now show the 28 instead of the 35; `tables/manuscript_numbers.json` keeps the 35
and adds the 28.

Components, AUC against a positive CAR (two-sided p, 10,000 permutations of outcomes across event
clusters):

| Component | Primary 55 | Other 35 | Other 28 |
|---|---|---|---|
| Spider score | 0.414 (0.35) | 0.507 (0.96) | 0.562 (0.62) |
| Value V | 0.533 (0.72) | 0.464 (0.31) | 0.438 (0.21) |
| Protection P | 0.454 (0.54) | 0.464 (0.71) | 0.537 (0.91) |
| Buyer strength B | 0.537 (0.66) | 0.714 (0.06) | 0.650 (0.23) |
| Risk R | 0.699 (0.04) | 0.724 (0.04) | 0.694 (0.11) |
| Execution E | 0.600 (0.29) | 0.675 (0.30) | 0.562 (0.63) |

Risk component under the five outcome definitions:

| Outcome | Primary 55 | Other 35 | Other 28 |
|---|---|---|---|
| SPY, reaction day (primary) | 0.699 (0.04) | 0.724 (0.04) | 0.694 (0.11) |
| Bank-sector index, reaction day | 0.514 (0.90) | 0.561 (0.66) | 0.644 (0.30) |
| Market model, reaction day | 0.644 (0.14) | 0.637 (0.22) | 0.567 (0.57) |
| SPY, [0,+1] around release date | 0.423 (0.47) | 0.572 (0.57) | 0.667 (0.16) |
| SPY, [-1,+1] around release date | 0.343 (0.13) | 0.562 (0.62) | 0.658 (0.17) |

### Files changed

| File | Change |
|---|---|
| `05_.../code/final_analysis.py` | the 28 as a third deal set in the component and Risk-direction loops (evaluated last); writes `broader_only_shared_events.csv` |
| `05_.../code/make_tex_tables.py` | Tables 12 and 13 show the 28 instead of the 35; deal sets selected by name |
| `05_.../code/number_check.py` | checks the revised sentences on the 35 and the 28, and the release cited |
| `05_.../code/fill_manuscript.py`, `fill_reports.py` | select the 35 by name (they would otherwise be ambiguous with a third deal set); output unchanged |
| `05_.../results/` | complete rerun of `final_analysis.py` and `cluster_influence_check.py` |
| `05_.../tables/` | regenerated: `tab_components.tex`, `tab_risk.tex` and `manuscript_numbers.json` change |
| `05_.../run_log.txt`, `CLEAN_RERUN_COMPARISON.txt` | log of the final run; comparison with an independent second run |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `reproduce.sh`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.2 |

The inputs, the Spider rules and `cluster_influence_check.py` are unchanged.

### Rerun and reproduction

`final_analysis.py` and `cluster_influence_check.py` were run twice, from the same copy of the
package, in two separate processes (60 minutes each, run concurrently). The two runs produce
byte-identical result files (38 files; `RUN_MANIFEST.json` equal except the runtime). The
first run is the release.

Compared with release 4.1: `table_spider_components.csv` and `table_risk_validation.csv` keep every
row of 4.1 unchanged and add the rows for the 28 (6 and 5 rows); `broader_only_shared_events.csv`
is new; `RUN_MANIFEST.json` differs in the checksum of `final_analysis.py` and the runtime. The other
34 result files, the two PNG figures included, are byte-identical to release 4.1.

## Release 4.1 (2026-11-23)

### Correction: FDIC financing of the buyer for Westernbank Puerto Rico and Eurobank

Westernbank Puerto Rico (PA-0306, acquirer Banco Popular de Puerto Rico) and Eurobank (PA-0308,
acquirer Oriental Bank and Trust) were coded `fdic_buyer_financing = 0`, and so
`H_support_broad = 0`, in release 4.0. FDIC financing of the buyer had been coded from the FDIC
press releases (PR-97-2010, PR-95-2010), which do not mention it. The FDIC bid summaries list the
winning bid of each with a Financing Note and an Equity Appreciation Instrument, and the
acquirers' filings give the terms:

* Westernbank: Banco Popular issued the FDIC a five-year $5,758,084,000 purchase money note at
  2.50% (Popular 8-K signed 2010-05-06, Ex. 4.1); the FDIC received a cash-settled value
  appreciation instrument (Ex. 4.2).
* Eurobank: Oriental issued the FDIC a one-year $715,536,000 promissory note at 0.881%, fully
  recourse (Oriental press release of 2010-04-30 and 8-K signed 2010-05-06).

SVB's purchase money note was already coded as FDIC financing, so both follow the existing rule.
Value or equity appreciation instruments are consideration paid to the FDIC and are not counted
as support. The narrow definition (bridge bank or systemic-risk exception: SVB only) is unchanged.

### New: the winning bid of all 90 transactions checked for FDIC financing

`03_revised_framework_2026-10-29/data/FDIC_Financing_Check_90.csv` records, for each of the 90
transactions, the document that states the winning bid, its URL, the winning bid as stated, and
whether it includes FDIC financing of the buyer (a purchase money note or financing note issued by
the buyer to the FDIC) or an appreciation instrument paid to the FDIC.

* The FDIC bid summary was found for 80 transactions (45 of the primary panel, all 35 others).
* For the other ten, all in the primary panel and all closed between August 2008 and April 2009,
  no bid summary was found; the winning bid was read in the purchase and assumption agreement
  (6), the acquirer's SEC filing (3) or the FDIC release that states the price (1).
* Four winning bids include FDIC financing of the buyer: SVB (PA-0006), First Republic (PA-0004),
  Westernbank (PA-0306) and Eurobank (PA-0308). This equals the ledger's coding for all 90.

`03_revised_framework_2026-10-29/code/check_fdic_financing.py` checks the file against the ledger
and the model inputs (report: `data/FDIC_Financing_Check_Report.txt`).

### Files changed

| File | Change |
|---|---|
| `03_.../code/build_source_ledger.py` | evidence rows PA-0306, PA-0308: `fdic_buyer_financing` 1, evidence note |
| `03_.../data/Source_Verification_Ledger_90.csv` | the same; `H_broad_any_extraordinary_support` 1 (rebuilt by the builder) |
| `03_.../data/SNFF_Revised_Inputs_Primary55.csv`, `..._Broader90.csv` | `H_support_broad` 1 for the two rows |
| `03_.../data/Revised_Variables_Validation_Report.txt` | broad-support counts (2 -> 4) and rule coverage of "U with H, broad" (U 1 -> 2), recomputed with the script's own code (the script itself reads a Stage 2 file that is not in the package) |
| `03_.../data/FDIC_Financing_Check_90.csv`, `FDIC_Financing_Check_Report.txt`, `03_.../code/check_fdic_financing.py` | new (see above) |
| `03_.../REVISED_FRAMEWORK_SPEC.md` | definition of `H_support_broad` |
| `05_.../results/` | complete rerun of `final_analysis.py` and `cluster_influence_check.py` on the corrected inputs |
| `05_.../tables/` | regenerated by `make_tex_tables.py` |
| `05_.../run_log.txt`, `CLEAN_RERUN_COMPARISON.txt` | log of the final run; comparison with an independent second run |
| `05_.../code/number_check.py` | ignores revision highlighting (`\rev{...}`); checks the revised robustness sentences and the statements on the winning-bid check |
| `05_.../code/table_check.py` | new: checks that every table in the manuscript equals the table generated from the results |
| `05_.../code/compare_clean_rerun.py` | reports a PNG figure that differs in rendering without counting it as a failure (see below) |
| `README.md`, `CITATION.cff`, `ENVIRONMENT.txt`, `reproduce.sh`, `GITHUB_PUBLISHING_GUIDE.md`, `MANIFEST.sha256` | release 4.1 |

`final_analysis.py`, `cluster_influence_check.py`, `make_tex_tables.py` and the Spider rules are
unchanged. The `date` field of `RUN_MANIFEST.json` is set in `final_analysis.py` and still reads
2026-10-30, the date of the analysis code.

### Effect on the results

Only the two robustness variants that read `H_support_broad` change. Mean AUC over 50 repeats
(Table 11 of the manuscript):

| Variant | Model 2 | Ridge | Model 3 | Spider score |
|---|---|---|---|---|
| Broad support definition | 0.612 -> 0.583 | 0.632 -> 0.611 | 0.596 -> 0.577 | 0.421 -> 0.423 |
| Rule U requires support (broad) | 0.612 -> 0.583 | 0.632 -> 0.611 | 0.601 -> 0.590 | 0.396 -> 0.400 |

### Rerun and reproduction

`final_analysis.py` and `cluster_influence_check.py` were run twice on the corrected inputs, from
the same read-only copy of the package, in two separate processes. The two runs produce
byte-identical result files (37 files; `RUN_MANIFEST.json` equal except the runtime;
`05_.../CLEAN_RERUN_COMPARISON.txt`). The first run is the release.

Compared with release 4.0:

* `robustness_by_repeat.csv`: the 400 rows of the two broad-support variants change (of 1,800);
  `table_robustness.csv`: their 8 summary rows change (of 36), as in the table above.
* `appendix_primary55.csv`: `H_support_broad` for PA-0306 and PA-0308.
* `RUN_MANIFEST.json`: the checksums of the three corrected input files, Python 3.13.18 (4.0:
  3.13.17) and the runtime.
* `figure_calibration.png`, `figure_shap_fullsample.png`: anti-aliasing only. matplotlib 3.11.2
  renders text with the system FreeType, which differs from the machine of release 4.0; the
  figures' data (`table_calibration_bins.csv`, `table_shap_fullsample.csv`) are identical.
  `compare_clean_rerun.py` now reports a differing PNG figure without counting it as a failure.
* The other 31 result files are byte-identical to release 4.0.

`make_tex_tables.py` on the new results changes only the two rows of `tab_robustness.tex` (and
`manuscript_numbers.json`). `table_check.py` confirms that every table of the revised manuscript
equals the generated table, and `number_check.py` passes all 121 checks on the revised manuscript.

## Release 4.0 (2026-10-30)

First public release.
