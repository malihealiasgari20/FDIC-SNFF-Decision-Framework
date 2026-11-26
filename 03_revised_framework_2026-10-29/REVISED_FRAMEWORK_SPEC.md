# SNFF revised framework (Option B): measured inputs only

Prepared 2026-10-29 (Step 2: variables; Step 3: source verification and event
convention). Starting point: `Primary55_Measured_Only_Foundation_NOT_FINAL.csv`
from the 29 October corrected data audit, checked against the original files
before use (see "Checks on the starting data").

**Status.** Every model input is now measured or coded from a primary source
for the 55-transaction primary panel and the 90-transaction broader panel, and
the outcome uses one event-time convention for all transactions. No model has
been rerun. The decisions left for Step 4 are listed at the end.

## What changed and why

| July 2026 variable | Problem | Revised framework |
|---|---|---|
| `purchase_discount_pct` (D) | Computed as 0.6 x NPL %, not a deal price; real discounts exist for only 2 of 55 deals | Dropped |
| `asset_quality_score` (A) | 1 - NPL ratio: the NPL variable again | Dropped; NPL enters once (N) |
| `npl_ratio_pct` (N) | Measured at a report not yet public at the announcement for 25 of 55 deals | Kept; measured at the latest report public before the announcement |
| `deposit_base_usd_b` (G) | Millions labeled billions | Kept, in USD billions, same report as N |
| `buyer_capital_ratio_pct` (C) | Acquirer's first report after the failure, which includes the acquired bank | Acquiring bank's equity / assets at the last quarter-end at least 90 days before the failure |
| `integration_speed_months` (M) | A rescaled size ratio using post-deal acquirer assets, with a whole-sample cap; not a duration | Replaced by relative size E = failed-bank assets / acquiring-bank assets (pre-failure) |
| `fdic_loss_share_flag` (F) | 1 for every 2008-2013 failure outside the 20 hand-coded deals | Coded from each deal's FDIC release: 40 of 55 (66 of 90) with loss share |
| `govt_support_flag` (H) | Undefined boundary (bridge bank vs. FDIC financing) | Explicit definition from the releases (narrow by default) |
| `liquidity_crisis_flag` (L) | Outside the 20 hand-coded deals: NPL below median and deposits at least loans | Measured: deposit change of the failed bank over the two quarters ending at the public report |
| `structural_decline_flag` (T) | Outside the 20 hand-coded deals: NPL above median (NPL again) | Measured: change in the NPL ratio over the same two quarters |
| Outcome window | CAR[-1,+1] centered on the FDIC release date, which for after-close releases puts two of the three days before the news | CAR[-1,+1] centered on the first session that could react to the news (below) |

## Variables (`data/SNFF_Revised_Inputs_Primary55.csv`, `..._Broader90.csv`)

Report P is the failed bank's latest quarterly call report whose 30-day filing
deadline fell before the failure date, i.e. the latest report the market could
have seen. For 25 of the 55 deals (41 of 90) the bank failed within 30 days of a
quarter-end; P is then the quarter before Stage 1's Q-1.

| Column | Definition | Source and timing |
|---|---|---|
| `N_npl_pct` | Noncurrent loans / loans of the failed bank, % | FDIC call report P |
| `G_deposits_usd_bn` | Deposits of the failed bank, USD bn | Report P |
| `C_buyer_capital_pct` | Equity / total assets of the acquiring bank, % | FDIC call report, last quarter-end at least 90 days before failure |
| `E_relative_size` | Failed-bank assets (P) / acquiring-bank assets (same report as C) | As above |
| `L_deposit_change_pct` | Deposits at P / deposits two quarters earlier - 1, %; negative = outflow | Failed-bank call reports (181-184 days apart) |
| `T_npl_change_pp` | NPL ratio at P minus NPL ratio two quarters earlier, percentage points | Same reports |
| `F_loss_share` | FDIC loss-share agreement in the deal (0/1) | FDIC press release (ledger) |
| `H_support_narrow` | Bridge bank or systemic-risk exception (0/1) | FDIC releases; 1 only for SVB |
| `H_support_broad` | Narrow, plus FDIC financing of the buyer | Adds First Republic ($50 bn five-year FDIC financing), Westernbank Puerto Rico and Eurobank (notes issued by the buyers to the FDIC); checked against the winning bid of all 90 transactions in `FDIC_Financing_Check_90.csv` (release 4.1) |
| `y`, `car_reaction_m1p1` | **Primary outcome**: CAR[-1,+1] around the first session that could react to the announcement; value created if > 0 | Cached prices (June 2026); 35 / 20 in the 55, 56 / 34 in the 90 |
| `y_release_0p1`, `car_release_0p1` | CAR[0,+1] around the first trading day on or after the release date | 39 / 16; 64 / 26 |
| `y_release_m1p1_june`, `car_release_m1p1_june` | The June 2026 window: CAR[-1,+1] around the same day | 41 / 14; 64 / 26 |
| `announcement_timing`, `first_reaction_date` | AFTER_CLOSE, PRE_OPEN or NON_TRADING_DAY, verified from the release; day 0 | Ledger |
| `failed_report_date`, `failed_report_date_base`, `failed_report_lag_days` | Report P, the report two quarters earlier, days from P to the failure | Stage 1 FDIC pull |
| `*_q1` | The Step 2 values from Stage 1's Q-1 (N, G, E) and Q-4 to Q-1 changes (L, T), for sensitivity | Not public at the announcement where `failed_report_is_stage1_q1` = 0 |
| `C_buyer_capital_pct_latest`, `E_relative_size_latest` | Buyer values from the latest report before failure (sensitivity) | FDIC checkpoint |
| `ref_july_*` | July flags, for comparison only; not model inputs | July code |

Units: FDIC reports dollar amounts in thousands; billions = thousands / 1,000,000.

## Step 3: source verification (`data/Source_Verification_Ledger_90.csv`)

For each of the 90 transactions the FDIC press release announcing the purchase
and assumption was read (FDIC press-release archive or the FDIC's GovDelivery
bulletins). The ledger records the PR number, date and link, the release's own
timing language, any send time, the loss-share statement, any bridge bank,
systemic-risk exception or FDIC financing of the buyer, and notes. 79 distinct
releases cover the 90 deals (one release covers the nine FBOP banks bought by
U.S. Bank; Downey and PFF, Darby and Tifton, and High Trust and One Georgia
share releases).

**Announcement timing.**

* 88 of 90 announcements came after the market close: 86 on a Friday evening and
  2 on a Thursday evening (Washington Mutual, LibertyPointe). Every one of these
  releases says the bank "was closed today" and gives depositor access or the
  FDIC hotline "this evening" (typically "until 9:00 p.m."). The five GovDelivery
  bulletins for these deals that carry a send time were sent after the close (Doral 4:31 p.m.
  EST; Montgomery 5:32 p.m. EDT; Central Bank of Georgia 5:02 p.m. EST; Mountain
  National 6:10 p.m. EDT; Republic First 6:17 p.m. EDT).
* First Republic: closed and sold before the Monday open (FDIC board statement
  sent 3:33 a.m. EDT, 1 May 2023): PRE_OPEN, day 0 is the same Monday.
* SVB: the sale of Silicon Valley Bridge Bank to First Citizens was announced on
  Sunday 26 March 2023: day 0 is Monday 27 March.
* Five Friday releases fall before a Monday holiday; day 0 is the Tuesday
  (Integrity, Vantus; and in the broader panel First Heritage, Capitol City,
  Harvest Community).
* Known earlier news: for Colonial, Bloomberg named BB&T as buyer at 11:23 a.m. on
  the Friday and the NYSE halted Colonial BancGroup before the open; that session
  is day -1 of the primary window. For Republic First the earliest dated report
  found (Reuters, citing the WSJ) is stamped 5:56 p.m. on the Friday, after the close.

**Protection.** Loss share: 40 of 55 and 66 of 90; none after 2012 except SVB
and First Republic. Government support: the narrow definition (bridge bank or
systemic-risk exception) applies to SVB only; the broad definition adds First
Republic, whose buyer received $50 bn of five-year FDIC financing (SVB's buyer
also issued the FDIC a $35 bn purchase money note and received a $70 bn FDIC
credit facility, First Citizens 8-K of 27 March 2023), and, since release 4.1,
Westernbank Puerto Rico and Eurobank, whose buyers issued the FDIC a five-year
$5.758 bn purchase money note at 2.50% (Banco Popular) and a one-year $715.5 mn
note at 0.881% (Oriental). Their FDIC releases do not mention the notes; the FDIC
bid summaries and the buyers' filings do. `data/FDIC_Financing_Check_90.csv`
records the document that states the winning bid of each of the 90 transactions
(the FDIC bid summary for 80; the P&A agreement, the acquirer's SEC filing or the
FDIC release for ten deals of August 2008 to April 2009) and whether that bid
includes FDIC financing of the buyer; `code/check_fdic_financing.py` checks it
against the ledger. Value or equity appreciation instruments paid to the FDIC are
not counted as support.

**Distress indicators and report timing.** N, L and T come from the failed
bank's FDIC call reports (the API queries are recorded in the Stage 1 raw pull).
Checking the "as of" statement in the FDIC releases showed that Stage 1's Q-1
report was not yet public when 25 of the 55 banks failed: the FDIC's own releases
cite the previous quarter for these banks. Under the 30-day filing rule the
inputs reproduce the release figures exactly (7 releases checked: High Trust, One
Georgia, Central Bank of Georgia, BankEast, Harvest Community, First Chicago,
Vineyard). Two other releases cite internal month-end figures (Warren Bank,
31 July 2009; United Commercial Bank, 23 October 2009), never the unpublished
quarter. The Q-1 values differ most where the NPL ratio jumped in the bank's last
quarter (Vineyard 23% public vs. 39% at Q-1; Colorado Capital 31% vs. 45%;
First NBC 16% vs. 26%). Rank correlation between public and Q-1 values: N 0.95,
G 0.995, E 0.999, L 0.90, T 0.85 (55 deals). Because the Stage 1 pull holds four
quarters, the changes L and T are measured over two quarters for every bank.

## Event-time convention (`data/Event_Convention_Report.txt`, `..._Comparison_90.csv`)

**Primary outcome.** Day 0 is the first trading session in which the market
could act on the verified FDIC announcement: the next session for after-close
announcements, the same day for First Republic's pre-open announcement, and the
next session for SVB's Sunday announcement. The outcome is the market-adjusted
CAR (stock minus SPY, as in Stage 1) over days -1, 0 and +1; value created if
the CAR is positive. For a Friday-evening release the window is Friday, Monday
and Tuesday.

**Why this convention.**

1. Day 0 must be the first day prices can reflect the news. Event-study practice
   extends the window to the day after the announcement to capture announcements
   made after the close (MacKinlay 1997); for after-hours announcements the price
   response appears one trading day after the announcement date (Berkman and
   Truong 2009).
2. It is the only one of the three windows with the same position relative to
   the news for every transaction: one session before, the reaction session, one
   after. The June window covers two sessions before the news and one after for
   the 88 after-close deals, but one before and two after for First Republic and
   SVB; the release-date [0,+1] window covers one before and one after for the
   after-close deals, but none before for First Republic and SVB.
3. It has precedent in this setting: for a Friday-evening release it equals the
   CAR[0,+2] of Molyneux and Zhou (2022), who date day 0 at the FDIC announcement;
   Cowan and Salotti (2015), who note the FDIC's practice of announcing closures
   on Friday evenings, report (0,+1) and (-1,+1) around the release date, which
   are the two robustness windows here.
4. The data agree on where the news is priced: in the 55 the mean abnormal return
   on day 0 is +4.0% (t = 2.75; 73% positive; median across acquirer-days +1.5%);
   no other session from -5 to +5 has |t| above 1.95. Day +1 averages -0.65%
   (t = -1.45).

**Robustness and sensitivity.** Labels in the 55 (90): reaction-day [-1,+1]
35/20 (56/34); release-date [0,+1] 39/16 (64/26); June [-1,+1] 41/14 (64/26);
reaction-day window with a market model (beta from days -130 to -11; median 1.25)
31/24 (49/41). The June window changes 14 of the 55 labels against the primary
(10 positive to not, 4 not to positive), all after-close deals; these are 11
distinct events (the four FBOP banks share one U.S. Bank return), and their CARs
are small (median |CAR| 0.9% against 3.3% for all deals). Sign labels near zero
are therefore window-dependent; Step 4 should report the three windows and the
market-model labels.

**Pre-news drift.** Over the two sessions before day 0 the mean CAR is +1.05%
in the 55 (t = 2.11; counting each acquirer-day once, +1.21%, t = 2.28), and
+1.37% in the 90 (t = 1.91). The June window, which includes both sessions, is
the check on whether this drift (leakage or bank-sector moves against SPY)
drives any result.

**Shared returns.** Deals bought by the same acquirer on the same day share
one return: 51 acquirer-days among the 55 (U.S. Bank: four FBOP banks on
2 November 2009, Downey and PFF on 24 November 2008) and 78 among the 90. Folds
should be grouped by acquirer-day.

**Text for Section V-C (draft).** "Event day 0 is the first trading session in
which the market could react to the FDIC's announcement of the transaction. We
verified the timing of every announcement from the FDIC press release: 53 of the
55 were released after the close (52 on a Friday evening, Washington Mutual on a
Thursday evening), so day 0 is the next trading session; First Republic was
announced before the open on Monday 1 May 2023 and SVB's sale on Sunday 26 March
2023, so day 0 is that Monday. The outcome is the market-adjusted cumulative
abnormal return over days -1 to +1, and a transaction is labeled value-creating
if it is positive. Results are reported for two alternative windows, CAR[0,+1]
and CAR[-1,+1] around the release date (Cowan and Salotti 2015), and for
market-model abnormal returns."

## Spider Network, revised (`code/snff_revised_features.py`)

All normalization bounds, caps, quartile thresholds and the final rescaling are
fitted on the training fold and applied unchanged to the held-out fold.

Components (weights as in the paper):

* V = G_n (deposit franchise; the discount and asset-quality terms are gone)
* P = 0.60 F + 0.40 H
* R = 0.40 N_n + 0.25 L + 0.35 T, with L = 1 if the deposit change is in the
  training fold's bottom quartile and T = 1 if the NPL change is in its top quartile
* B = C_n (pre-failure buyer capital)
* E = E_n (relative size, winsorized at the training fold's 95th percentile)
* S = 0.30 V + 0.20 P + 0.20 B - 0.20 R - 0.10 E

Rules:

| Rule | July form | Revised form | Adjustment |
|---|---|---|---|
| Q, protected credit risk | D >= D75, F = 1, A >= 0.5 | N >= N75 and F = 1 | +0.08 |
| U, recoverable distress | L = 1, T = 0, H = 1 | L = 1 and T = 0 | +0.07 |
| Z, structural-risk penalty | T = 1, C < C25 | Same, with measured T and pre-failure C | -0.10 |
| K, size-burden penalty | M > M75, C < C25 | E > E75 and C < C25 | -0.06 |

S* = S + 0.08 Q + 0.07 U - 0.10 Z - 0.06 K, rescaled to [0, 1] on the training fold.

Why the rules change the way they do:

* **Q keeps its content.** Because D = 0.6 x NPL and A = 1 - NPL, the July rule
  already selected high-NPL deals with loss share. Recomputed on the July 65-row
  data, the revised Q selects the same 14 deals plus Wheatland Bank (NPL 52%),
  which the July condition A >= 0.5 excluded. What changes is the
  interpretation: Q is protection of credit risk by loss sharing, not discount
  protection, and the paper's text must say so.
* **K keeps its content.** The July M was a monotone transform of the size ratio,
  so K selects the same 4 deals when fed the same ratio. The revision uses the
  buyer's pre-failure assets and fits the cap inside each fold.
* **U loses the H condition.** H = 1 for one deal (narrow) or two (broad), so the
  July U would select 0 or 1 of 55. Without H, U marks deposit-outflow failures
  without credit deterioration. H stays in P. `RevisedSpider(u_requires_h=True)`
  restores the July form.
* **Z** is unchanged in form.

Rule coverage (all-row thresholds, descriptive): 55 deals L 14, T 14, Q 11, U 11,
Z 1, K 5; 90 deals L 23, T 23, Q 19, U 16, Z 3, K 10. Z now fires for a single
deal in the primary panel.

Model inputs: the baseline models (Model 2 and the comparators) use the six
measured variables plus F and H (8 inputs, against 10 in July); Model 3 adds
S_final and the four rules (13).

## Acquisition events (release 4.3; `code/build_event_inputs.py`)

An acquisition event is every failed bank that one acquirer bought from the FDIC on one
day. Its banks share one announcement return (the event clusters of the cross-validation),
and the acquirer decides on them together: U.S. Bank's winning bids for the four FBOP
subsidiaries of the primary panel are marked "Linked: Yes" in the FDIC bid summaries, and
the FDIC announced the nine-bank sale as one transaction (PR-195-2009). The Spider score
of a bank is not additive over banks (deposits and relative size are sums; the flags and
rules switch at thresholds), so an event is scored on the consolidated call reports of its
banks, with every input defined as for one bank:

| Input | Event value |
|---|---|
| `G_deposits_usd_bn` | total deposits at report P |
| `N_npl_pct` | total noncurrent loans / total net loans at P (each bank weighted by its loans) |
| `L_deposit_change_pct` | total deposits at P / total deposits two quarters earlier - 1 |
| `T_npl_change_pp` | consolidated N at P minus consolidated N two quarters earlier |
| `E_relative_size` | total failed-bank assets at P / acquiring-bank assets, counted once (two Wintrust subsidiaries combined) |
| `C_buyer_capital_pct` | acquiring bank's equity / assets (combined equity / combined assets for two subsidiaries) |
| F, H, outcomes, report dates | common to the event's banks (checked) |

`data/Multi_Bank_Event_Call_Reports.csv` holds the call-report amounts (FDIC BankFind API,
retrieved 2026-11-23: assets, deposits, net loans and leases `LNLSNET`, noncurrent loans and
leases `NCLNLS`) of the 15 banks in the four multi-bank events of the primary panel, at
report P and two quarters earlier, with the query URL of each bank. `N_npl_pct` is
`NCLNLS / LNLSNET`, as in the Stage 1 pull. Before use, the builder checks that these
amounts reproduce every bank's assets, deposits, N, L, T and E in the 90-transaction
inputs (largest difference 9e-15), and that no other failure in the 502-failure inclusion
log was bought by an acquiring bank of the primary panel on the same day.

| Event | Banks | In the primary panel |
|---|---|---|
| USB, 2009-10-30 (FBOP) | 9 | California National, Park National, San Diego National, Pacific National |
| USB, 2008-11-21 | Downey Savings and Loan, PFF Bank & Trust | both |
| WTFC, 2010-04-23 | Wheatland Bank (Wheaton B&T), Lincoln Park Savings Bank (Northbrook B&T) | Wheatland |
| ABCB, 2010-11-12 | Darby Bank & Trust, Tifton Banking Company (Ameris Bank) | Darby |

Outputs: `data/SNFF_Event_Inputs_Primary51.csv` (the 51 events of the primary panel, 62
banks, 34 with a positive CAR; the 47 single-bank events are unchanged),
`data/SNFF_Event_Consolidations.csv` (the four consolidated events, and FBOP restricted to
its four panel banks) and `data/Event_Inputs_Report.txt`.

## SVB's deposits at three dates (release 4.4; `data/SVB_Deposit_Stages.csv`)

The Value input of every transaction is the failed bank's deposit base at its last public
call report (report P), the only deposit figure that is public before the failure and
measured the same way for all transactions. For SVB, the one bridge-bank sale of the
panel, the deposits changed sharply between that report and the sale. The file records
SVB's deposits and assets at three dates, with the document each figure comes from:

| Stage | Date | Deposits (USD bn) | Assets (USD bn) | In the information set | Source |
|---|---|---|---|---|---|
| last call report | 2022-12-31 | 175.378 | 209.026 | yes | FDIC BankFind call report (CERT 24735); equal to the inputs |
| at failure | 2023-03-10 | 119 | 167 | no | FDIC PR-23-2023 ("about $119 billion", "approximately $167 billion") |
| assumed by the acquirer | 2023-03-27 | 55.96 | 106.60 | no | First Citizens, Q1 2023 earnings release (deposits assumed; total assets acquired at estimated fair value) |

Only the first row is an input. The other two are dated after the failure and are used
only in a retrospective description of the SVB case (`final_analysis.py`, section "SVB
DEPOSIT STAGES"; Table 6, Panel B): each replaces the call-report deposits of the case, with
the assets of the same date in the relative size (which stays above its cap, so E is
unchanged), every other input unchanged, scored with the full-panel Spider fit and with a
fit on the other 54 transactions. A second variant also lets the deposit change L react,
measured from the report two quarters before P to the stage date. The panel's inputs are
not changed. Outputs: `results/table_svb_deposit_stages.csv` and
`results/table_svb_deposit_breakeven.csv` (deposits at which the case reaches the Pursue
threshold on each set of bounds).

## Two co-primary benchmarks (release 4.5)

Decision 6 below (SPY as the only benchmark) is superseded. Step 4 built a bank-sector
benchmark from the June 2026 price cache after all (`05_.../code/bank_benchmark_cars.py`,
`05_.../data/Bank_Benchmark_CAR_90.csv`): the equal-weighted daily return of the 27
U.S.-listed bank holding companies with complete price series in the cache, leaving out the
acquirer and every bank with its own reaction day within four days (24 to 27 constituents),
with the window and day 0 of the SPY-adjusted outcome. It labels 39 of the 55 transactions
positive; ten labels differ from the SPY-adjusted labels, in six event clusters, four of them
the FBOP subsidiaries. The submitted paper used it as a robustness check. Following a
reviewer's comment, release 4.5 reports the two outcomes as co-primary specifications and
repeats every analysis with the bank-sector labels (`final_analysis.py`, last section). The
bank-sector specification was elevated during the revision, after the results under both were
known; it was not designated in advance. Its constituents are banks that still traded in June
2026, so it is a peer portfolio rather than a published index.

## Sensitivity to the constants (release 4.6; `05_.../code/weight_sensitivity.py`)

The five component weights (0.30, 0.20, 0.20, 0.20, 0.10) and the four adjustments (+0.08, +0.07, -0.10,
-0.06) are expert choices, unchanged in every release; none was estimated from the outcomes. Release 4.6
evaluates alternatives, defined before any of them was evaluated, with the partitions of the main comparison for both
benchmarks: each constant changed alone (a weight times 0.5 or 1.5, the five then rescaled so that their
absolute values sum to one; an adjustment times 0, 0.5 or 1.5); equal weights, no adjustments, and both;
1,000 draws within +/-50% of every constant; 1,000 sign-preserving draws over the whole range (weights
uniform on the simplex, adjustments between zero and twice their value); and constants chosen inside each
training fold from either set of draws by the training-fold AUC, with a permutation test of that choice.
The weights inside the Protection and Risk components, the rule thresholds and the rules themselves are not
varied. The expert constants remain the specification of the framework.

## Included and excluded transactions (releases 4.7 and 4.8; `05_.../code/selection_comparison.py`)

Of the 150 largest eligible failures, 94 were acquired by a bank with a U.S.-listed parent. The price
data of the study cover 55 of them (the primary panel, with 28 listed parents). The other 39 have 24
listed parents, as recorded in `data/Excluded39_Parent_Status.csv`: 17 parents, with 26 of the
transactions, were later acquired and delisted; 7 parents, with 13 transactions, still trade, but their
prices were not retrieved (ten transactions of six parents first coded as privately held, and three of
New York Community Bancorp, whose history the price source moved to the ticker FLG). Transactions and
parents are counted separately throughout. The comparison measures every characteristic as for
the model inputs: the failed bank's from its last public call report (the rule reproduces the released
inputs of all 90 listed-acquirer transactions exactly) and the acquiring bank's assets and total equity
(EQTOT) from its call report at the last quarter-end at least 90 days before the failure
(`data/Excluded39_Buyer_Call_Reports.csv`, FDIC BankFind API, retrieved 2026-11-24; every value was
retrieved twice with identical results, and five reports of panel acquirers reproduce the released
inputs exactly). Inclusion is a property of the listed parent, so the permutation test reassigns it
across the 52 parents. The models' out-of-fold predictions are evaluated by acquirer size (at most or
above the median acquiring bank of all 94) and reweighted by the inverse of an estimated probability of
inclusion (logistic model on the acquiring bank's log assets and capital, the 2008-2010 period and the
NPL ratio); nothing is refitted, and no earlier result changes.

Release 4.8 adds the diagnostics of the reweighting. `results/table_selection_balance.csv` gives the
balance of the panel against all 94 before and after weighting, as standardized differences (mean of
the included, weighted as in the column, minus the mean of all 94, divided by the standard deviation of
all 94), for the four characteristics of the inclusion model and five others;
`results/table_selection_weight_diagnostics.csv` gives the range of the estimated inclusion
probabilities in each group, the excluded transactions below the lowest included probability, and the
largest weight, its share of the total and the effective sample size of each weighting. The weighted
figures represent all 94 only if, given the four characteristics, inclusion is unrelated to the outcome
and to the models' predictions, the inclusion model is correctly specified, and the two groups overlap;
the first two cannot be checked without the excluded transactions' prices, and the inclusion model
treats the 94 transactions as independent although inclusion is decided by their 52 parents.

## Checks (`data/Revised_Variables_Validation_Report.txt`)

All pass: failed-bank reports public before the failure (30-day filing deadline);
deposit and NPL changes span two quarters (181-184 days); every buyer report at
least 90 days old; the FDIC "as of" figures reproduced for 7 releases; loss
share, support and timing coded from the release for all 90; day 0 is the first
session after the verified announcement; y matches the sign of the primary CAR;
units and ranges; no pair of measured predictors with |Spearman| >= 0.9 (largest
0.51, N with T); fitted parameters do not depend on held-out rows. The three
CARs rebuilt day by day from the price cache equal the 02b rebuild exactly.

## Checks on the starting data

* The package's 18 checksums match.
* Failed-bank values in the foundation equal the Stage 1 originals (55/55);
  buyer values equal the 90-day picks (55/55); outcomes equal my cache-only
  rebuild with the Wintrust mapping applied (55/55, CARs within 1e-6).
* The pre-failure buyer figures come from the FDIC checkpoint, which is not in
  the package. Where the June 2026 pull holds the same bank and quarter, the
  values agree exactly (34 of 34 comparisons: assets, deposits, equity), and every
  pick is the expected quarter-end (no gaps in the histories). Known cases are
  plausible (First-Citizens $109 bn before SVB, $215 bn after).

## Decisions for Step 4

1. **Government support**: narrow definition (default) or broad.
2. **U rule**: without H (default) or the July form with H (selects 0 or 1 deal).
3. **Z rule**: fires for one primary-panel deal; keep, or merge into R.
4. **Folds grouped by acquirer-day** (the July folds were not grouped).
5. **PA-0165 (Wintrust)**: included, as in the 29 October package, on FDIC and
   SEC sources; using this panel means accepting that mapping.
6. **Benchmark**: SPY as in Stage 1. A bank-index benchmark would remove
   bank-sector moves but needs prices not in the June 2026 cache.
7. **Real deal terms**: the FDIC's bid summaries report the winning bid's asset
   discount and deposit premium; they could replace the dropped discount for the
   2009-2012 deals if wanted.

## References

* Berkman, H., Truong, C. (2009). Event day 0? After-hours earnings announcements. Journal of Accounting Research 47(1), 71-103.
* Cowan, A. R., Salotti, V. (2015). The resolution of failed banks during the crisis: Acquirer performance and FDIC guarantees, 2008-2013. Journal of Banking & Finance 54, 222-238.
* MacKinlay, A. C. (1997). Event studies in economics and finance. Journal of Economic Literature 35(1), 13-39.
* Molyneux, P., Zhou, T. M. (2022). Banking market reaction to auctions of failed banks. International Journal of Finance & Economics 27(1), 518-534.

## Reproduce

From the research folder (each script takes the research folder and writes into
`03_revised_framework_2026-10-29/data`):

```
python3 -I 03_revised_framework_2026-10-29/code/build_source_ledger.py . 03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv
python3 -I 03_revised_framework_2026-10-29/code/build_revised_variables.py . 03_revised_framework_2026-10-29/data
python3 -I 03_revised_framework_2026-10-29/code/event_convention_report.py . 03_revised_framework_2026-10-29
python3 -I 03_revised_framework_2026-10-29/code/validate_revised_variables.py . 03_revised_framework_2026-10-29
python3 -I 03_revised_framework_2026-10-29/code/build_event_inputs.py .
```
