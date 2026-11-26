# Stage 1: announcement returns of the acquirers (provenance code)

This folder holds the code that mapped each FDIC-assisted acquirer to a listed parent and computed the announcement
returns from daily prices. It documents how the outcome variable was built. It cannot be rerun from this repository,
because the price series are not redistributed (see `../LICENSE-DATA.md`); its outputs, without the closing-price
columns, are in `../02b_car_conventions_2026-10-29/`.

## Outcome

The cumulative abnormal return (CAR) is the sum of market-adjusted daily returns (the parent's return minus that of
SPY) over trading days t-1, t and t+1. In this Stage 1 code, t is the first trading day on or after the event date.
The revised framework's primary outcome shifts the window to the first session in which the market could trade on the
announcement (`car_reaction_m1p1`; see `../02b_car_conventions_2026-10-29/README.md` and
`../03_revised_framework_2026-10-29/REVISED_FRAMEWORK_SPEC.md`).

## Files

| File | Role |
|---|---|
| `acquirer_ticker_map.py` | Maps each acquirer to its parent and ticker: whole-word name matching, rules by FDIC certificate first, and a `parent_listing` column (US / FOREIGN / OTC / PRIVATE) |
| `event_ticker_overrides.csv` | Per-transaction ticker and listing corrections, with the source of each (`source_url`) |
| `event_date_overrides.csv` | Announcement dates that differ from the FDIC closing date (the SVB and Signature bridge-bank sales) |
| `build_car_outcomes.py` | Computes the event dates and the CARs; logs the source of each event date |
| `build_public_modeling_dataset.py` | Builds the modeling dataset of all transactions with complete call reports; excludes foreign-listed and OTC parents by default |
| `acquirer_pre_failure_financials.py` | Acquirer assets, deposits, equity and capital ratio from the last call report before each failure (FDIC BankFind API) |
| `historical_prices.py` | Downloads daily adjusted closing prices: Yahoo Finance through `yfinance`, with Financial Modeling Prep as a fallback when the environment variable `FMP_API_KEY` is set |
| `cache_prices.py` | Serves previously downloaded price series offline in place of `historical_prices.py` |
| `compare_outcomes.py` | Lists added and dropped rows and outcome changes between two builds |

## Rerunning with your own price access

Rerunning needs internet access, `pip install yfinance pandas numpy requests openpyxl`, and optionally an FMP API key
(`export FMP_API_KEY=...`) for delisted tickers. Prices retrieved later may differ from those retrieved in June 2026,
because providers revise histories and stop serving delisted securities. The released returns and CARs are the
reference for every analysis in this repository.

The rebuild used for the paper applied every reviewed ticker mapping (`APPLY_PENDING_TICKER_MAPPINGS = True`); it gives
the 90 transactions with U.S.-listed parents and prices, of which 55 form the primary panel.
