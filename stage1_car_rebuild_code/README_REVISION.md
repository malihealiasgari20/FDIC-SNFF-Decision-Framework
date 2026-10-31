# Stage 1 CAR rebuild: revision 2026-10

These files replace their namesakes in the Stage 1 project folder
("FDIC Cursor 6 18 26"). They fix the outcome errors found in the October 2026
data audit (`../audit/stage1_audit_findings.csv`). The CAR formula itself is
unchanged: market-adjusted returns (stock minus SPY), summed over trading days
t-1, t, t+1, where t is the first trading day on or after the event date.

## What changed

| File | Change |
|---|---|
| `acquirer_ticker_map.py` | Whole-word name matching (the old substring test sent CertusBank and Synovus to U.S. Bancorp, and First California Bank to Zions); rules by FDIC certificate run first (separates the three different "First Citizens" banks); Flagstar 2023 -> NYCB (was TFC), Union Bank -> MUFG (was UNB), Sabadell -> SAB.MC (was SAN); new `parent_listing` column (US / FOREIGN / OTC / PRIVATE); listed parents proposed for acquirers coded private in June (the `VERIFY` rows and the Northbrook -> Wintrust name rule) are quarantined until the authors approve them. |
| `build_car_outcomes.py` | Event date comes from `event_date_overrides.csv` when present (bridge-bank sales announced after the failure date), otherwise the FDIC closing date as before; passes the acquirer certificate to the ticker map; logs `event_date_source`. |
| `build_public_modeling_dataset.py` | Uses the same CAR code; excludes foreign-listed and OTC parents by default (two flags at the top); keeps `ticker_match_method`, `parent_listing`, `event_date_source`, `event_trading_date` in the export; logs counts for the 150-largest sample separately. |
| `event_ticker_overrides.csv` | Old rows kept; EverBank (IPO 2012) and Great Western (owned by National Australia Bank in 2010) fixed; per-transaction corrections for every audited row; 22 acquirers that were coded private but appear to have had a listed parent, marked `VERIFY` (21 since PA-0327 was resolved as an OTC parent). |
| `event_date_overrides.csv` | New: SVB (sale announced 2023-03-26) and Signature Bank (2023-03-19). |
| `historical_prices.py` | Unchanged; included so the folder is complete. |
| `compare_outcomes.py` | New: lists dropped rows, added rows and outcome flips between the old and new files. |
| `acquirer_pre_failure_financials.py` | New: acquirer assets, deposits, equity and capital ratio from the last call report **before** the failure. The Stage 1 files use the first report on or after the failure, which already contains the acquired bank and any bargain-purchase gain. Reads the histories cached in `fdic_acquirer_pull_checkpoint.json`, so it runs offline if that file exists. |

Tested offline with simulated prices: the event-date override moves SVB's day 0
to 2023-03-27 and Signature's to 2023-03-20, CertusBank becomes private,
foreign/OTC parents are flagged and excluded, and the CAR of an unchanged row
matches a hand computation exactly. Real prices were not available in the test
environment, so the CAR values themselves must come from your run.

## How to run (needs internet; about 10 minutes)

1. Back up the project folder, or at least `Stage1_Final_Public_Modeling_Dataset_LOCKED.csv` and `car_price_cache.json`.
2. Copy the files in this folder into the project folder, replacing the old ones.
3. `pip install yfinance pandas numpy requests openpyxl`
4. Optional: `export FMP_API_KEY=...` (helps with delisted tickers).
5. `python build_car_outcomes.py` (150-row analytic sample; also rewrites `Stage1_Acquirer_Ticker_Map.csv`)
6. `python build_public_modeling_dataset.py` (all field-pass rows; writes `Stage1_Final_Public_Modeling_Dataset.csv`)
7. `python compare_outcomes.py Stage1_Final_Public_Modeling_Dataset_LOCKED.csv Stage1_Final_Public_Modeling_Dataset.csv`
8. Send back `Stage1_Final_Public_Modeling_Dataset.csv`, `Stage1_Public_Modeling_Build_Log.csv`,
   `Stage1_Outcome_Changes_2026_10.csv`, `Stage1_Master_Public_Outcomes_All.csv` and `Stage1_NO_PRICE_Audit.csv`.

9. `python acquirer_pre_failure_financials.py Stage1_Final_Public_Modeling_Dataset.csv`
   and send back `Stage1_Acquirer_PreFailure_Financials.csv`.

Then re-merge the Stage 2 variables (purchase discount, flags, integration
months) onto the new file by `transaction_id`, take the buyer capital ratio
from the `_pre` column, and rerun the models.

## What has already been checked from the June price cache

`car_price_cache.json` (in the Drive folder) holds every price series the June
run downloaded. `cache_prices.py` serves those series offline in place of
`historical_prices.py`. With it:

* The June results are reproduced exactly: all 469 statuses and all 105 CARs
  (largest difference 2e-7, from rounding in the JSON).
* The patched build, limited to prices already in the cache, gives 86 rows
  (62 positive / 24 not), of which 54 are in the 150-largest panel (40 / 14),
  with the ticker mappings that await the authors' sign-off quarantined (the
  default; `../audit/offline_rebuild_from_cache/Stage1_Final_Public_Modeling_Dataset_cache_only_strict.csv`).
  With all of them applied it gives 90 rows (64 / 26) and 55 in the panel
  (41 / 14) (`..._cache_only_v2.csv`). The difference is Wintrust's four
  Northbrook deals (PA-0165 in the panel, three below the asset threshold),
  the only pending mappings with cached prices. SVB's CAR with day 0 =
  2023-03-27 is +54.3% (FCNCA +53.7% that day).
* Still missing because the cache has no prices for them: Signature (NYCB/FLG;
  NYCB rose about 30% on 2023-03-20, so it will be positive), Sunrise (SNV),
  the two First California rows (FCAL), and the US-listed VERIFY acquirers
  (FFBC ×3, SSB ×2, HFWA, HOMB ×2, RBCAA, HTH; the delisted ones need FMP or
  CRSP). Your run fills these in; every other CAR should match the
  cache-only file exactly.

To repeat the offline check: put `cache_prices.py` next to the patched scripts
and run Python with `import sys, cache_prices; sys.modules["historical_prices"] = cache_prices`
before importing `build_public_modeling_dataset`.

## Changes after the 2026-10-28 reconstruction audit

* **Listing as of the event date.** Charter Financial (CHFN) was quoted on the
  OTC Bulletin Board until 2010-09-29, so PA-0327 (McIntosh Commercial Bank,
  2010-03-26) is an OTC parent and stays out of the US-exchange panel.
* **Source links.** `event_ticker_overrides.csv` now has a `source_url` column
  with the primary source found for 21 of the 22 VERIFY rows. They still need
  an author's sign-off; PA-0315 (Harris/BMO) and PA-0142 (SBNC) are excluded
  as foreign and OTC parents whatever the check shows.
* **Event-timing robustness.** `build_car_outcomes.py` now also writes
  `car_0p1` / `value_created_flag_0p1` (days 0 to +1, Cowan and Salotti's
  window) and `car_reaction_m1p1` / `value_created_flag_reaction` (days -1 to
  +1 around the first trading day on which the market could react: the next
  trading day for announcements made after the close). `event_date_overrides.csv`
  gives the timing where it differs from the FDIC's after-close default
  (First Republic before the open; SVB and Signature on Sundays). The primary
  outcome is unchanged. In the cache-only panel the alternatives change 4 and
  14 of the 54 labels (also 4 and 14 of 55 with the pending mappings applied;
  `../audit/offline_rebuild_from_cache/timing_robustness_cache_only.csv`),
  so the paper should report the model comparison under both.
* `../audit/offline_rebuild_from_cache/Stage1_Final_Public_Modeling_Dataset_cache_only_v2.csv`
  adds these columns; its primary columns are identical to the earlier
  cache-only file (SHA-256 b947a9fb…).

## Changes after the second review (2026-10-28)

* **Pending ticker mappings are no longer applied by default.** The earlier
  version applied every `VERIFY` override and the new Northbrook -> Wintrust
  name rule, although none had the authors' sign-off; that is why it reported
  90 rows / 55 in the panel. They are now quarantined (24 rows of the 469; 4
  of them have cached prices), giving 86 / 54. With
  `APPLY_PENDING_TICKER_MAPPINGS = True` the rebuild reproduces the earlier
  90-row file (CARs equal to within 2.3e-7, the JSON rounding noted above).

## Decisions for the authors

1. **Foreign-listed parents** (TD, Scotiabank, Compass/BBVA, Union Bank/MUFG,
   Sabadell, Harris/BMO): excluded by default (`EXCLUDE_FOREIGN_PARENTS = True`).
   The deals are immaterial to these parents and SPY is the wrong benchmark for
   their stocks. Set the flag to False to keep them.
2. **OTC parents** (First Citizens Bancorporation of South Carolina, FCBN;
   Southern BancShares, SBNC): excluded by default (`EXCLUDE_OTC_PARENTS = True`).
3. **VERIFY rows and the Northbrook name rule**: quarantined by default
   (`car_status` = `PENDING_TICKER_VERIFICATION`, counted in the build log).
   Check each against the source in `source_url` or the Federal Reserve's
   National Information Center (holding-company history). For each one you
   confirm, change the `VERIFY:` prefix of its `status_note` to `VERIFIED:`
   (for Northbrook, move the rule from `PENDING_NAME_RULES` to `TICKER_RULES`
   in `acquirer_ticker_map.py`); delete any you cannot confirm.
   `APPLY_PENDING_TICKER_MAPPINGS = True` applies all of them at once, for a
   sensitivity run only.
4. **Delisted acquirers**: Yahoo does not carry stocks that were later acquired
   (IBERIABANK, MB Financial, Umpqua, City National, FirstMerit, PrivateBancorp,
   CenterState, Heartland, and several of the VERIFY parents). CRSP through WRDS,
   or FMP with an API key, would recover them and remove a survivorship bias the
   paper otherwise has to report as a limitation.
