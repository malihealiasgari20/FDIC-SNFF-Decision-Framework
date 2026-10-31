"""Build the revised (measured-only) SNFF input files.

Option B of the October 2026 revision: the framework uses only measured
historical financial information. Dropped: the July `purchase_discount_pct`
(0.6 x NPL %, not a deal discount), `asset_quality_score` (1 - NPL ratio, a
duplicate of NPL) and `integration_speed_months` (a rescaled size ratio built
from post-deal acquirer assets, not a duration). The rule-based liquidity and
structural flags of July (functions of the NPL median and deposits >= loans)
are replaced by measured changes in the failed bank's own call reports.

Timing (Step 3). Every balance-sheet input was public before the announcement.
The failed bank's figures come from its latest quarterly call report whose
30-day filing deadline fell before the failure date (report P). For 41 of the
90 transactions (25 of the 55) the bank failed within 30 days of a quarter-end,
so P is the quarter before Stage 1's Q-1; the FDIC's own releases cite that
earlier quarter for these banks (checked for six of them). Deposit change (L)
and NPL change (T) are measured over the two quarters ending at P, the longest
span the Stage 1 pull covers for every bank. The buyer's figures come from the
last quarter-end at least 90 days before the failure. The Step 2 values based on
Q-1 are kept with the suffix _q1 for sensitivity.

Inputs (read-only; paths relative to the research folder):
  02_corrected_audit_2026-10-29/.../Stage1_90Row_Historical_Buyer_Financial_Candidates.csv
      90-row listed-acquirer panel (55 in the 150-largest cohort), failed-bank
      Q-1 values from Stage 1, acquirer pre-failure values from the FDIC
      checkpoint (latest report before failure and last report >= 90 days
      before failure), cached CARs.
  02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_90.csv
      CARs under three event windows and the announcement timing class.
  00_original_stage1_2026-06-19/Stage1_Master_Financials_Completed.csv
      failed-bank call reports Q-1..Q-4 (June 2026 FDIC pull).
  03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv
      FDIC-release coding of loss share, bridge bank, systemic-risk exception
      and FDIC financing, and the verified announcement timing (Step 3), for
      all 90 transactions.
  01_stage2_regenerated_2026-10-28/Stage2_SNFF_Model_Inputs_broader105.csv
      the July flags, kept only as reference columns.

Primary outcome (Step 3 convention): CAR[-1,+1] around the first trading session
in which the market could act on the FDIC's announcement (Friday-evening
announcements: Fri-Mon-Tue). Alternatives kept: CAR[0,+1] around the release
date and the June 2026 CAR[-1,+1] around the release date.

usage: python3 -I build_revised_variables.py <research_folder> <output_folder>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
AUD = ROOT / "02_corrected_audit_2026-10-29/SNFF_Problem1_2026-10-29/Analysis"
S1 = ROOT / "00_original_stage1_2026-06-19"
S2 = ROOT / "01_stage2_regenerated_2026-10-28"

hist = pd.read_csv(AUD / "Stage1_90Row_Historical_Buyer_Financial_Candidates.csv", dtype={"acquirer_cert": str})
events = pd.read_csv(ROOT / "02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_90.csv")
fin = pd.read_csv(S1 / "Stage1_Master_Financials_Completed.csv")
ledger = pd.read_csv(ROOT / "03_revised_framework_2026-10-29/data/Source_Verification_Ledger_90.csv")
july = pd.read_csv(S2 / "Stage2_SNFF_Model_Inputs_broader105.csv")
assert len(hist) == 90 and hist.transaction_id.is_unique
assert len(events) == 90 and set(events.transaction_id) == set(hist.transaction_id)

df = hist.merge(events[["transaction_id", "car_0p1", "car_reaction_m1p1", "announcement_timing",
                        "first_reaction_date"]], on="transaction_id", how="left", validate="one_to_one")
# same June-convention CARs in both rebuilds
ev = events.set_index("transaction_id").loc[df.transaction_id]
assert np.allclose(ev.car_3day.values, df.car_3day.values, atol=1e-6)
qcols = [f"failed_{v}_q_minus_{k}" for k in (2, 3, 4) for v in ("assets", "deposits", "npl_ratio")]
q = fin[["transaction_id"] + [f"failed_q_minus_{k}_repdate" for k in (1, 2, 3, 4)] + qcols
        + ["failed_assets_q_minus_1", "failed_deposits_q_minus_1", "failed_npl_ratio_q_minus_1"]].rename(
    columns={"failed_assets_q_minus_1": "fin_assets_q1", "failed_deposits_q_minus_1": "fin_deposits_q1",
             "failed_npl_ratio_q_minus_1": "fin_npl_q1"})
df = df.merge(q, on="transaction_id", how="left", validate="one_to_one")
# the 29 Oct file carries the same Stage 1 Q-1 values
assert np.allclose(df.fin_assets_q1, df.failed_assets_q_minus_1)
assert np.allclose(df.fin_deposits_q1, df.failed_deposits_q_minus_1)
assert np.allclose(df.fin_npl_q1, df.failed_npl_ratio_q_minus_1)

out = pd.DataFrame({
    "transaction_id": df.transaction_id,
    "failed_bank_name": df.failed_bank_name,
    "failed_bank_cert": df.failed_bank_cert,
    "failure_date": df.failure_date,
    "acquirer_bank_name": df.acquirer_name,
    "acquirer_bank_cert": df.acquirer_cert,
    "listed_parent_ticker": df.ticker,
    "announcement_date": df.announcement_date,
    "in_primary_panel": (df.inclusion_exclusion_reason == "INCLUDED").astype(int),
    # outcomes (cached June 2026 prices); primary = reaction-day CAR[-1,+1]
    "announcement_timing": df.announcement_timing,
    "first_reaction_date": df.first_reaction_date,
    "car_reaction_m1p1": df.car_reaction_m1p1,
    "y": (df.car_reaction_m1p1 > 0).astype(int),
    "car_release_0p1": df.car_0p1,
    "y_release_0p1": (df.car_0p1 > 0).astype(int),
    "car_release_m1p1_june": df.car_3day,
    "y_release_m1p1_june": df.value_created_flag.astype(int),
})

# ---- failed-bank report public before the announcement --------------------------
FILING_DAYS = 30  # call reports are due 30 days after the quarter-end
fdate = pd.to_datetime(df.failure_date)
P_idx, B_idx = [], []
for i in range(len(df)):
    reps = {}  # date -> quarter index (Stage 1 repeats Q-1 as Q-2 when a report was never filed)
    for k in (4, 3, 2, 1):
        reps[pd.Timestamp(df[f"failed_q_minus_{k}_repdate"].iloc[i])] = k
    public = [d for d in reps if (fdate.iloc[i] - d).days > FILING_DAYS]
    pdate = max(public)
    bdate = (pdate - pd.DateOffset(months=6)) + pd.offsets.MonthEnd(0)
    assert bdate in reps, (df.transaction_id.iloc[i], pdate, bdate)
    P_idx.append(reps[pdate]); B_idx.append(reps[bdate])
P_idx, B_idx = np.array(P_idx), np.array(B_idx)
df = df.assign(fin_assets_q_minus_1=df.fin_assets_q1, fin_deposits_q_minus_1=df.fin_deposits_q1,
               fin_npl_ratio_q_minus_1=df.fin_npl_q1)
def at(var: str, idx: np.ndarray) -> np.ndarray:
    src = {1: f"fin_{var}_q_minus_1"} | {k: f"failed_{var}_q_minus_{k}" for k in (2, 3, 4)}
    return np.array([df[src[k]].iloc[i] for i, k in enumerate(idx)], dtype=float)
def at_date(idx: np.ndarray) -> pd.Series:
    return pd.Series([df[f"failed_q_minus_{k}_repdate"].iloc[i] for i, k in enumerate(idx)])
assets_P, dep_P, npl_P = at("assets", P_idx), at("deposits", P_idx), at("npl_ratio", P_idx)
dep_B, npl_B = at("deposits", B_idx), at("npl_ratio", B_idx)

# ---- measured predictors (report P; public before the announcement) -----------------
# N: credit quality of the failed bank, entered once (noncurrent loans / loans, %)
out["N_npl_pct"] = 100 * npl_P
# G: deposit franchise of the failed bank, USD billions (FDIC reports thousands)
out["G_deposits_usd_bn"] = dep_P / 1e6
# C: buyer capital, equity / assets of the acquiring bank at the last quarter-end
#    at least 90 days before the failure
out["C_buyer_capital_pct"] = 100 * df.lag90_conservative_equity_usd_thousands / df.lag90_conservative_assets_usd_thousands
# E: relative size of the acquisition (replaces the integration-months proxy)
out["E_relative_size"] = assets_P / df.lag90_conservative_assets_usd_thousands
# L: deposit change of the failed bank over the two quarters ending at P (%), negative = outflow
out["L_deposit_change_pct"] = 100 * (dep_P / dep_B - 1)
# T: change in the NPL ratio over the same two quarters (percentage points)
out["T_npl_change_pp"] = 100 * (npl_P - npl_B)
out["failed_report_date"] = at_date(P_idx).values
out["failed_report_date_base"] = at_date(B_idx).values
out["failed_report_lag_days"] = (fdate - pd.to_datetime(out.failed_report_date)).dt.days
out["failed_report_is_stage1_q1"] = (P_idx == 1).astype(int)
out["dynamics_span_days"] = (pd.to_datetime(out.failed_report_date) - pd.to_datetime(out.failed_report_date_base)).dt.days

# ---- Step 2 values from Stage 1's Q-1 (sensitivity; not public before the announcement
#      for the rows with failed_report_is_stage1_q1 = 0) ---------------------------------
out["N_npl_pct_q1"] = 100 * df.failed_npl_ratio_q_minus_1
out["G_deposits_usd_bn_q1"] = df.failed_deposits_q_minus_1 / 1e6
out["E_relative_size_q1"] = df.failed_assets_q_minus_1 / df.lag90_conservative_assets_usd_thousands
out["L_deposit_change_pct_q1"] = 100 * (df.failed_deposits_q_minus_1 / df.failed_deposits_q_minus_4 - 1)
out["T_npl_change_pp_q1"] = 100 * (df.failed_npl_ratio_q_minus_1 - df.failed_npl_ratio_q_minus_4)
out["dynamics_span_days_q1"] = (pd.to_datetime(df.failed_q_minus_1_repdate) - pd.to_datetime(df.failed_q_minus_4_repdate)).dt.days

# ---- deal terms (binary) ---------------------------------------------------
# F: FDIC loss-share agreement, from each deal's FDIC release (ledger, all 90)
lg = ledger.set_index("transaction_id")
assert set(lg.index) == set(out.transaction_id)
assert (lg.timing_class.reindex(out.transaction_id).values == out.announcement_timing.values).all()
out["F_loss_share"] = out.transaction_id.map(lg.loss_share).astype(int)
out["F_status"] = "SOURCE_CODED_FDIC_RELEASE"
# H: extraordinary government support. Narrow definition (default): bridge bank
#    or systemic-risk exception. Broad: also FDIC financing of the buyer.
out["H_support_narrow"] = out.transaction_id.map(lg.H_narrow_bridge_or_sre).astype(int)
out["H_support_broad"] = out.transaction_id.map(lg.H_broad_any_extraordinary_support).astype(int)
out["H_status"] = "SOURCE_CODED_FDIC_RELEASE"
out["timing_status"] = "VERIFIED_FDIC_RELEASE"
out["fdic_release"] = out.transaction_id.map(lg.fdic_pr)
out["fdic_release_url"] = out.transaction_id.map(lg.release_url)

# ---- sensitivity: buyer values from the latest report before failure ---------
out["C_buyer_capital_pct_latest"] = 100 * df.latest_report_date_pre_failure_equity_usd_thousands / df.latest_report_date_pre_failure_assets_usd_thousands
out["E_relative_size_latest"] = assets_P / df.latest_report_date_pre_failure_assets_usd_thousands

# ---- provenance -----------------------------------------------------------------
out["failed_report_date_q1"] = df.failed_q_minus_1_repdate
out["failed_report_date_q4"] = df.failed_q_minus_4_repdate
out["buyer_report_date_lag90"] = df.lag90_conservative_repdate
out["buyer_report_date_latest"] = df.latest_report_date_pre_failure_repdate
out["failed_assets_usd_bn"] = assets_P / 1e6
out["failed_assets_usd_bn_q1"] = df.failed_assets_q_minus_1 / 1e6
out["buyer_assets_usd_bn_lag90"] = df.lag90_conservative_assets_usd_thousands / 1e6

# ---- July values for reference only (never model inputs) ----------------------
ref = july.set_index("transaction_id")
for c in ["fdic_loss_share_flag", "govt_support_flag", "liquidity_crisis_flag", "structural_decline_flag"]:
    out[f"ref_july_{c}"] = out.transaction_id.map(ref[c]).astype("Int64")

out = out.sort_values(["in_primary_panel", "failed_assets_usd_bn"], ascending=[False, False]).reset_index(drop=True)
note = out.dynamics_span_days_q1 < 250
out["data_note"] = np.where(note, "Stage 1 repeats Q-1 as Q-2 (Q1 2024 report never filed); the _q1 changes span two quarters", "")

primary = out[out.in_primary_panel == 1]
assert len(primary) == 55 and int(primary.y_release_m1p1_june.sum()) == 41
assert (out.set_index("transaction_id").y == lg.y_reaction_m1p1.reindex(out.transaction_id)).all()
assert (out.in_primary_panel.values == lg.in_primary_panel.reindex(out.transaction_id).values).all()
out.to_csv(OUT / "SNFF_Revised_Inputs_Broader90.csv", index=False)
primary.to_csv(OUT / "SNFF_Revised_Inputs_Primary55.csv", index=False)
print(f"wrote {len(out)} and {len(primary)} rows; value created (reaction-day) {int(out.y.sum())} of 90, {int(primary.y.sum())} of 55; "
      f"loss share {int(out.F_loss_share.sum())} of 90, {int(primary.F_loss_share.sum())} of 55")
