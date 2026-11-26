# Data, results and documentation: license and third-party sources

## License of the authors' contributions

Except for the software (licensed under the MIT License, see `LICENSE`) and the third-party material described below,
the contents of this repository are licensed under the Creative Commons Attribution 4.0 International License
(CC BY 4.0, <https://creativecommons.org/licenses/by/4.0/>). This covers the datasets compiled by the authors (the
transaction panels, the source-verification ledger, the winning-bid record, the event consolidations and the other
files in the `data/` folders), the result files, the LaTeX tables, the figures and the documentation.

Copyright (c) 2026 Yousef Nejatbakhsh, Malihe Aliasgari, Parsa Safaee, and Sina Shokoohyar.

Please cite the article and this release as described in `CITATION.cff`.

## Third-party sources

The CC BY 4.0 license applies only to the authors' own compilation, coding and analysis. It grants no rights in the
underlying third-party material, which remains subject to its providers' terms.

| Source | Used for | What this repository contains |
|---|---|---|
| Federal Deposit Insurance Corporation (FDIC): Failed Bank List, BankFind Suite API, press releases, bid summaries and purchase and assumption agreements | Failed-bank and acquirer call-report figures, deal terms, announcement timing, winning bids | Figures and codings extracted from these public sources, with the URL of each source document |
| Acquirers' filings with the U.S. Securities and Exchange Commission (SEC EDGAR) and their earnings releases | Corroboration of loss-share and FDIC-financing codings, SVB deposit stages | Codings and figures extracted from the filings, with their URLs; the filings themselves are not included |
| Yahoo Finance (through the `yfinance` library), with Financial Modeling Prep as a fallback, retrieved in June 2026 | Daily adjusted closing prices of the acquirers' parents, SPY and the bank-sector peer portfolio | **No price series or price levels.** Only the derived event-window quantities that define the study's outcome: three-day stock and market returns around each announcement, daily abnormal returns, cumulative abnormal returns and the window returns of the benchmarks |

## Historical stock prices are not redistributed

The daily price series were obtained under the providers' terms of use and are not included in this repository. The
three closing-price columns of the Stage 1 rebuild were removed before release. The scripts that read prices
(`stage1_car_rebuild_code/`, `03_revised_framework_2026-10-29/code/event_convention_report.py` and
`05_manuscript_analysis_2026-10-29/code/bank_benchmark_cars.py`) are included as documentation of how the returns were
computed; rerunning them requires the user's own access to historical price data. Every other analysis in the
repository runs from the included files.
