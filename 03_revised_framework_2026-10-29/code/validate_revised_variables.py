"""Checks for the revised SNFF inputs and features. No outcome is modeled here.

1. Data checks: identifiers, timing (failed-bank report public before the
   failure; buyer reports at least 90 days old; FDIC 'as of' figures), units and ranges, source coding of
   loss share, support and announcement timing, and the event day.
2. Redundancy: correlations among the measured predictors (the July set had
   three exact transformations of NPL).
3. The revised Q and K rules keep the content of the July rules: recomputed on
   the July 65-row inputs, they select the same transactions (Q differs only
   where NPL > 50%, which the July A >= 0.5 condition dropped).
4. Fold safety: features fitted on training rows do not change when the other
   rows change.
5. Rule coverage on both panels (thresholds from all rows; descriptive).

usage: python3 -I validate_revised_variables.py <research_folder> <framework_folder>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, FW = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(FW / "code"))
from snff_revised_features import RAW_CONTINUOUS, RevisedSpider  # noqa: E402

lines: list[str] = []
def say(s=""):
    print(s); lines.append(s)

p55 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Primary55.csv")
b90 = pd.read_csv(FW / "data/SNFF_Revised_Inputs_Broader90.csv")
fails = 0
def check(name, ok):
    global fails
    fails += (not ok)
    say(f"  [{'ok' if ok else 'FAIL'}] {name}")

say("1. Data checks")
for nm, d in (("primary 55", p55), ("broader 90", b90)):
    fd = pd.to_datetime(d.failure_date)
    check(f"{nm}: unique ids, {len(d)} rows", d.transaction_id.is_unique)
    check(f"{nm}: no missing measured predictor", not d[RAW_CONTINUOUS].isna().any().any())
    check(f"{nm}: failed-bank report public before the failure (30-day filing deadline passed)",
          bool(((fd - pd.to_datetime(d.failed_report_date)).dt.days > 30).all()))
    check(f"{nm}: buyer report at least 90 days before failure",
          bool(((fd - pd.to_datetime(d.buyer_report_date_lag90)).dt.days >= 90).all()))
    check(f"{nm}: latest buyer report before failure", bool((pd.to_datetime(d.buyer_report_date_latest) < fd).all()))
    check(f"{nm}: deposit and NPL changes span two quarters ending at the public report",
          bool(d.dynamics_span_days.between(181, 184).all()))
    check(f"{nm}: NPL in [0, 100] %", bool(d.N_npl_pct.between(0, 100).all()))
    check(f"{nm}: buyer capital in [3, 25] %", bool(d.C_buyer_capital_pct.between(3, 25).all()))
    check(f"{nm}: deposits in USD bn (0.01 to 1,000)", bool(d.G_deposits_usd_bn.between(0.01, 1000).all()))
    check(f"{nm}: relative size positive", bool((d.E_relative_size > 0).all()))
    check(f"{nm}: loss share, support and timing coded from the FDIC release for every row",
          bool(d.F_loss_share.isin([0, 1]).all() and (d.F_status == "SOURCE_CODED_FDIC_RELEASE").all()
               and (d.H_status == "SOURCE_CODED_FDIC_RELEASE").all() and (d.timing_status == "VERIFIED_FDIC_RELEASE").all()))
    ann, rea = pd.to_datetime(d.announcement_date), pd.to_datetime(d.first_reaction_date)
    ok_day = np.where(d.announcement_timing == "PRE_OPEN", rea == ann, rea > ann)
    check(f"{nm}: day 0 is the first session after the verified announcement (same day only for pre-open)", bool(ok_day.all()))
    check(f"{nm}: y = 1 exactly when the reaction-day CAR[-1,+1] > 0", bool((d.y == (d.car_reaction_m1p1 > 0)).all()))
for nm, d in (("primary 55", p55), ("broader 90", b90)):
    say(f"  {nm}: value created {int(d.y.sum())} / not {int((1 - d.y).sum())} (reaction-day [-1,+1], primary); "
        f"release [0,+1] {int(d.y_release_0p1.sum())} / {int((1 - d.y_release_0p1).sum())}; "
        f"June [-1,+1] {int(d.y_release_m1p1_june.sum())} / {int((1 - d.y_release_m1p1_june).sum())}")
    say(f"  {nm}: loss share {int(d.F_loss_share.sum())} of {len(d)}; government support narrow {int(d.H_support_narrow.sum())}, "
        f"broad {int(d.H_support_broad.sum())}")

say("  failed-bank report P: the quarter before Stage 1's Q-1 for "
    f"{int((1 - p55.failed_report_is_stage1_q1).sum())} of 55 and {int((1 - b90.failed_report_is_stage1_q1).sum())} of 90")
# The FDIC release states the failed bank's total assets (and often deposits) "as of" a date.
# Read 2026-10-29 (archive.fdic.gov / GovDelivery). Values in USD millions as printed (rounded).
release_asof = {
    "PA-0161": ("PR-120-2011", "2011-03-31", 192.5, 189.5), "PA-0162": ("PR-120-2011", "2011-03-31", 186.3, 162.1),
    "PA-0112": ("PR-21-2012", "2011-12-31", 278.9, None), "PA-0115": ("PR-13-2012", "2011-09-30", 272.6, None),
    "PA-0020": ("PR-4-2017", "2016-09-30", 126.4, None), "PA-0165": ("PR-117-2011", "2011-03-31", 959.3, 887.5),
    "PA-0439": ("PR-125-2009", "2009-03-31", 1900.0, 1600.0),
}
x = b90.set_index("transaction_id")
ok = []
for k, (pr, asof, a, dep) in release_asof.items():
    r = x.loc[k]
    tol_a = 50.0 if a >= 1000 else 0.051  # releases round billions to one decimal
    good = (r.failed_report_date == asof and abs(r.failed_assets_usd_bn * 1000 - a) <= tol_a
            and (dep is None or abs(r.G_deposits_usd_bn * 1000 - dep) <= tol_a))
    ok.append(good)
    say(f"    {k} {pr}: release as of {asof}, assets {a}, deposits {dep}; input report {r.failed_report_date}, "
        f"assets {r.failed_assets_usd_bn * 1000:.1f}, deposits {r.G_deposits_usd_bn * 1000:.1f} (Stage 1 Q-1 {r.failed_report_date_q1})")
check("failed-bank report and figures match the 'as of' statement of the FDIC release (7 checked; 6 failed within 30 days of a quarter-end)", all(ok))

say("\n2. Correlations among the measured predictors (primary 55)")
c_p = p55[RAW_CONTINUOUS].corr(method="pearson")
c_s = p55[RAW_CONTINUOUS].corr(method="spearman")
off = ~np.eye(len(RAW_CONTINUOUS), dtype=bool)
say(f"  largest |Pearson| off-diagonal: {np.abs(c_p.values[off]).max():.2f}; largest |Spearman|: {np.abs(c_s.values[off]).max():.2f}")
say(c_s.round(2).to_string())
check("no pair of measured predictors with |Spearman| >= 0.9", np.abs(c_s.values[off]).max() < 0.9)

say("\n3. Revised Q and K select the same transactions as the July rules (July 65-row inputs, all-row thresholds)")
j = pd.read_csv(ROOT / "01_stage2_regenerated_2026-10-28/Stage2_SNFF_Model_Inputs_strict65.csv")
mm = lambda x: (x - x.min()) / (x.max() - x.min() + 1e-12)
D_n, A, N_n = mm(j.purchase_discount_pct), j.asset_quality_score, mm(j.npl_ratio_pct)
C_n, M_n = mm(j.buyer_capital_ratio_pct), mm(j.integration_speed_months)
F = j.fdic_loss_share_flag
q_july = (D_n >= D_n.quantile(0.75)) & (F == 1) & (A >= 0.5)
q_new = (N_n >= N_n.quantile(0.75)) & (F == 1)
diff_q = j.loc[q_july != q_new, ["transaction_id", "failed_bank_name", "npl_ratio_pct"]]
say(f"  Q: July selects {int(q_july.sum())}, revised selects {int(q_new.sum())}; differ on {len(diff_q)} row(s)"
    + (": " + "; ".join(f"{r.transaction_id} {r.failed_bank_name} (NPL {r.npl_ratio_pct:.1f}%)" for r in diff_q.itertuples()) if len(diff_q) else ""))
check("Q differs only where NPL > 50%", bool((diff_q.npl_ratio_pct > 50).all()))
r = j.deal_size_ratio
cap = r.quantile(0.95)
E_n = mm(r.clip(upper=cap))
k_july = (M_n > M_n.quantile(0.75)) & (C_n < C_n.quantile(0.25))
k_new = (E_n > E_n.quantile(0.75)) & (C_n < C_n.quantile(0.25))
say(f"  K: July selects {int(k_july.sum())}, revised form on the same size ratio selects {int(k_new.sum())}; differ on {int((k_july != k_new).sum())}")
check("K identical when fed the same size ratio", bool((k_july == k_new).all()))

say("\n4. Fold safety")
full = p55.copy()
rng = np.random.default_rng(0)
tr = rng.choice(len(full), size=45, replace=False)
te = np.setdiff1d(np.arange(len(full)), tr)
m1 = RevisedSpider().fit(full.iloc[tr])
a1 = m1.transform(full.iloc[te])
pert = full.copy()
for c in RAW_CONTINUOUS:
    pert.loc[pert.index[te], c] = pert.loc[pert.index[te], c] * 7 + 3
m2 = RevisedSpider().fit(pert.iloc[tr])
check("parameters fitted on the training rows ignore the other rows", m1.params == m2.params)
a_single = pd.concat([m1.transform(full.iloc[[i]]) for i in te])
check("each scored row depends only on itself and the training fit", np.allclose(a_single.S_final, a1.S_final))
check("S_final within [0, 1]", bool(a1.S_final.between(0, 1).all()))

say("\n5. Rule coverage (thresholds from all rows of each panel; descriptive)")
for pn, dd in (("primary 55", p55), ("broader 90", b90)):
    for name, kw in [("default (U without H)", {}), ("U with H, narrow", {"u_requires_h": True}),
                     ("U with H, broad", {"u_requires_h": True, "h_col": "H_support_broad"})]:
        m = RevisedSpider(**kw).fit(dd)
        f = m.transform(dd)
        say(f"  {pn}, {name:22s} L={int(f.L_flag.sum())} T={int(f.T_flag.sum())} Q={int(f.Q_rule.sum())} "
            f"U={int(f.U_rule.sum())} Z={int(f.Z_rule.sum())} K={int(f.K_rule.sum())}")

say(f"\n{'ALL CHECKS PASSED' if fails == 0 else f'{fails} CHECK(S) FAILED'}")
(FW / "data/Revised_Variables_Validation_Report.txt").write_text("\n".join(lines) + "\n")
sys.exit(1 if fails else 0)
