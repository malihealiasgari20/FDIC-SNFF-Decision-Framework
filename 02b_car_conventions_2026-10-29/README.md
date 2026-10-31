# Cache-only CARs under three event-window conventions (2026-10-29)

`Stage1_Cache_Only_Rebuild_90.csv` is the 90-transaction listed-acquirer panel
rebuilt offline with the patched Stage 1 code (code bundle v2, with
`APPLY_PENDING_TICKER_MAPPINGS = True`, which adds the four Wintrust/Northbrook
deals, PA-0165 among them) and the June 2026 price cache
(`00_original_stage1_2026-06-19/raw_pulls/car_price_cache.json`). No prices were
downloaded.

Columns used by the revised framework:

| Column | Window (trading days) |
|---|---|
| `car_3day` | [-1,+1] around the first trading day on or after the announcement date (the June 2026 convention; Thu-Fri-Mon for a Friday-evening announcement) |
| `car_0p1` | [0,+1] around the same day (Fri-Mon) |
| `car_reaction_m1p1` | [-1,+1] around the first session in which the market could trade on the announcement (`first_reaction_date`; Fri-Mon-Tue for a Friday-evening announcement) |
| `announcement_timing` | AFTER_CLOSE (default), PRE_OPEN (First Republic) or NON_TRADING_DAY (SVB); checked against the FDIC release for all 90 transactions in `03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv` |

Checks: the 55 primary-panel CARs in `car_3day` equal the 29 October package
(within 1e-6); for the 52 Friday announcements `car_reaction_m1p1` equals that
package's shifted CAR (within 1e-6). For Washington Mutual (announced Thursday
evening) the package left the window unshifted; here it is shifted to Friday.
Holidays follow the market calendar (Integrity Bank and Vantus Bank react on the
Tuesday after Labor Day).

The revised framework uses `car_reaction_m1p1` as its primary outcome; the other
two windows are robustness checks (see `03_revised_framework_2026-10-29/REVISED_FRAMEWORK_SPEC.md`).

Full outputs of the same rebuild, for the sample-construction counts:
`Stage1_Cache_Only_Rebuild_All469_Outcomes.csv` (all 469 transactions with
complete call reports: parent listing, CAR status) and
`Stage1_Cache_Only_Rebuild_Inclusion_Log_502.csv` (the 150-largest cohort flag).
The 90 rows of `Stage1_Cache_Only_Rebuild_90.csv` are the U.S.-listed parents
with prices in these files.

## In the replication package

The three closing-price columns (`price_t_minus_1`, `price_t`, `price_t_plus_1`) of
`Stage1_Cache_Only_Rebuild_All469_Outcomes.csv` are removed, because prices are not
redistributed; every other column, including the returns and CARs, is unchanged. The other
three files are byte-identical to the research folder.
