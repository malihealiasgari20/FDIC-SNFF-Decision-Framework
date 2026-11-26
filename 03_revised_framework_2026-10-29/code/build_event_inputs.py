"""Acquisition-event inputs: one row per decision (release 4.3).

An acquisition event is every failed bank that one acquirer bought from the FDIC on one day. Its banks share one
announcement return (the event clusters of the cross-validation), and the acquirer decides on them together: U.S.
Bank's winning bids for the FBOP subsidiaries, for example, are linked bids in the FDIC's bid summaries. A score for
the decision must therefore describe the combined target, not average the banks' scores. For an event of several
banks the inputs are computed from the banks' consolidated call reports, with each input defined exactly as for one
bank (REVISED_FRAMEWORK_SPEC.md):

  G  deposits                total deposits at report P
  N  NPL ratio               total noncurrent loans / total net loans at P (each bank weighted by its loans)
  L  deposit change          total deposits at P / total deposits two quarters earlier - 1
  T  NPL ratio change        consolidated N at P minus consolidated N two quarters earlier
  E  relative size           total failed-bank assets at P / assets of the acquiring bank, counted once (when two
                             subsidiaries of one acquirer bought the banks, their combined assets)
  C  buyer capital           equity / assets of the acquiring bank (combined equity / combined assets for two)
  F, H, outcomes, report dates: terms common to the event's banks (checked)

Banks below the primary panel's size cut enter through their events: the FBOP subsidiaries outside the panel,
Lincoln Park Savings Bank (Wintrust, with Wheatland Bank) and Tifton Banking Company (Ameris, with Darby Bank &
Trust). Their amounts come from the same FDIC call reports as every other input.

Data: Multi_Bank_Event_Call_Reports.csv, the call-report amounts (FDIC BankFind API, USD thousands) of the 15 banks
in the four multi-bank events of the primary panel at report P and two quarters earlier. Before use, the script
checks that they reproduce each bank's assets, deposits, N, L, T and E in SNFF_Revised_Inputs_Broader90.csv, and
that the events are complete: no other failure in the 502-failure inclusion log was bought by the same acquiring
bank on the same day.

Outputs (data/):
  SNFF_Event_Inputs_Primary51.csv  the 51 events of the primary panel, each scored on every bank its acquirer
                                   bought that day: 47 single-bank events unchanged; FBOP (nine banks),
                                   Downey + PFF, Wheatland + Lincoln Park and Darby + Tifton consolidated
  SNFF_Event_Consolidations.csv    the consolidated multi-bank events, with FBOP also restricted to the four
                                   subsidiaries in the primary panel
  Event_Inputs_Report.txt          the checks and the consolidated inputs

usage: python3 -I build_event_inputs.py <research_folder> [<output_dir>]   (default: the data folder)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1]).resolve()
DATA = ROOT / "03_revised_framework_2026-10-29/data"
OUTD = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DATA
OUTD.mkdir(parents=True, exist_ok=True)
b90 = pd.read_csv(DATA / "SNFF_Revised_Inputs_Broader90.csv")
cr = pd.read_csv(DATA / "Multi_Bank_Event_Call_Reports.csv")
inc = pd.read_csv(ROOT / "02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_Inclusion_Log_502.csv")
TOL = 1e-9
report = []


def key(d: pd.DataFrame) -> pd.Series:
    return d.listed_parent_ticker.astype(str) + "|" + d.first_reaction_date.astype(str)


b90["event_id"] = key(b90)
p55 = b90[b90.in_primary_panel == 1]
assert len(p55) == 55 and p55.event_id.nunique() == 51

# ---------------------------------------------------------------- 1. the call reports reproduce the bank-level inputs
P = cr[cr.report == "P"].set_index("transaction_id")
B = cr[cr.report == "P-2"].set_index("transaction_id")
assert set(P.index) == set(B.index) and len(P) == 15
worst = 0.0
for tid, row in b90.set_index("transaction_id").loc[sorted(P.index)].iterrows():
    p, q = P.loc[tid], B.loc[tid]
    assert p.report_date == row.failed_report_date and q.report_date == row.failed_report_date_base, tid
    n_p = 100 * p.noncurrent_loans_usd_thousands / p.net_loans_usd_thousands
    n_b = 100 * q.noncurrent_loans_usd_thousands / q.net_loans_usd_thousands
    diffs = [p.assets_usd_thousands / 1e6 - row.failed_assets_usd_bn, p.deposits_usd_thousands / 1e6 - row.G_deposits_usd_bn,
             n_p - row.N_npl_pct, 100 * (p.deposits_usd_thousands / q.deposits_usd_thousands - 1) - row.L_deposit_change_pct,
             (n_p - n_b) - row.T_npl_change_pp, p.assets_usd_thousands / 1e6 / row.buyer_assets_usd_bn_lag90 - row.E_relative_size]
    worst = max(worst, max(abs(x) for x in diffs))
assert worst < TOL, worst
report.append(f"1. The call reports of the 15 banks reproduce their assets, deposits, N, L, T and E in the 90-transaction inputs "
              f"(largest absolute difference {worst:.1e}).")

# ---------------------------------------------------------------- 2. the events are complete
multi = b90.groupby("event_id").transaction_id.apply(sorted)
multi = multi[multi.map(len) > 1]
prim_multi = multi[multi.index.isin(p55.event_id)]
assert set(prim_multi.index) == {"USB|2009-11-02", "USB|2008-11-24", "WTFC|2010-04-26", "ABCB|2010-11-15"}
assert set(sum(prim_multi.tolist(), [])) == set(P.index)
inc["k"] = list(zip(inc.acquirer_cert.fillna(-1).astype(int), inc.failure_date))
same = inc[inc.k.isin(set(zip(p55.acquirer_bank_cert.astype(int), p55.failure_date)))]
outside = same[~same.transaction_id.isin(b90.transaction_id)]
assert outside.empty, outside[["transaction_id", "failed_bank_name"]]
report.append("2. Four events of the primary panel include more than one bank: " + "; ".join(
    f"{e} ({len(v)} banks, {int(p55.event_id.eq(e).sum())} in the primary panel)" for e, v in prim_multi.items())
    + ". No other failure in the 502-failure inclusion log was bought by an acquiring bank of the primary panel on the same day.")

# ---------------------------------------------------------------- 3. consolidation
COMMON = ["listed_parent_ticker", "announcement_date", "announcement_timing", "first_reaction_date", "failure_date",
          "car_reaction_m1p1", "y", "car_release_0p1", "y_release_0p1", "car_release_m1p1_june", "y_release_m1p1_june",
          "F_loss_share", "H_support_narrow", "H_support_broad", "failed_report_date", "failed_report_date_base"]
KEEP = ["event_id", "n_banks", "n_banks_in_primary_panel", "member_transaction_ids", "failed_bank_name", "acquirer_bank_name",
        "acquirer_bank_cert", "in_primary_panel", "N_npl_pct", "G_deposits_usd_bn", "C_buyer_capital_pct", "E_relative_size",
        "L_deposit_change_pct", "T_npl_change_pp", "failed_assets_usd_bn", "buyer_assets_usd_bn_lag90", "buyer_report_date_lag90"] + COMMON


def consolidate(rows: pd.DataFrame, label: str) -> dict:
    ids = sorted(rows.transaction_id)
    for c in COMMON:
        assert rows[c].nunique(dropna=False) == 1, (label, c)
    p, q = P.loc[ids], B.loc[ids]
    n_p = 100 * p.noncurrent_loans_usd_thousands.sum() / p.net_loans_usd_thousands.sum()
    n_b = 100 * q.noncurrent_loans_usd_thousands.sum() / q.net_loans_usd_thousands.sum()
    buyers = rows.drop_duplicates("acquirer_bank_cert")  # each acquiring bank counted once
    assert buyers.buyer_report_date_lag90.nunique() == 1
    b_assets = buyers.buyer_assets_usd_bn_lag90.sum()
    b_equity = (buyers.C_buyer_capital_pct / 100 * buyers.buyer_assets_usd_bn_lag90).sum()
    out = {c: rows[c].iloc[0] for c in COMMON}
    out.update({
        "event_id": rows.event_id.iloc[0], "n_banks": len(rows), "n_banks_in_primary_panel": int(rows.in_primary_panel.sum()),
        "member_transaction_ids": ";".join(ids), "failed_bank_name": label,
        "acquirer_bank_name": "; ".join(buyers.acquirer_bank_name), "acquirer_bank_cert": ";".join(buyers.acquirer_bank_cert.astype(str)),
        "in_primary_panel": int(rows.in_primary_panel.max()),
        "G_deposits_usd_bn": p.deposits_usd_thousands.sum() / 1e6, "failed_assets_usd_bn": p.assets_usd_thousands.sum() / 1e6,
        "N_npl_pct": n_p, "T_npl_change_pp": n_p - n_b,
        "L_deposit_change_pct": 100 * (p.deposits_usd_thousands.sum() / q.deposits_usd_thousands.sum() - 1),
        "buyer_assets_usd_bn_lag90": b_assets, "C_buyer_capital_pct": 100 * b_equity / b_assets,
        "E_relative_size": p.assets_usd_thousands.sum() / 1e6 / b_assets, "buyer_report_date_lag90": buyers.buyer_report_date_lag90.iloc[0],
    })
    return out


LABELS = {"USB|2009-11-02": "FBOP Corporation subsidiaries", "USB|2008-11-24": "Downey Savings and Loan; PFF Bank & Trust",
          "WTFC|2010-04-26": "Wheatland Bank; Lincoln Park Savings Bank", "ABCB|2010-11-15": "Darby Bank & Trust; Tifton Banking Company"}
cons = []
for e, ids in prim_multi.items():
    rows = b90[b90.transaction_id.isin(ids)]
    cons.append({"scope": "all banks bought that day", **consolidate(rows, LABELS[e])})
fb = b90[(b90.event_id == "USB|2009-11-02") & (b90.in_primary_panel == 1)]
assert len(fb) == 4
cons.append({"scope": "banks in the primary panel", **consolidate(fb, "FBOP Corporation subsidiaries in the primary panel")})
C = pd.DataFrame(cons)[["scope"] + KEEP]
C.to_csv(OUTD / "SNFF_Event_Consolidations.csv", index=False)

# ---------------------------------------------------------------- 4. the 51 events of the primary panel
ev = []
for e in pd.unique(p55.event_id):
    if e in prim_multi.index:
        ev.append(C[(C.event_id == e) & (C.scope == "all banks bought that day")].iloc[0].drop("scope").to_dict())
    else:
        r = p55[p55.event_id == e].iloc[0].to_dict()
        r.update({"n_banks": 1, "n_banks_in_primary_panel": 1, "member_transaction_ids": r["transaction_id"]})
        ev.append({k: r[k] for k in KEEP})
E51 = pd.DataFrame(ev)[KEEP].sort_values(["failed_assets_usd_bn"], ascending=False).reset_index(drop=True)
assert len(E51) == 51 and E51.event_id.is_unique and int(E51.n_banks.sum()) == 55 + 7 and int(E51.y.sum()) == 34
E51.to_csv(OUTD / "SNFF_Event_Inputs_Primary51.csv", index=False)
report.append(f"3. SNFF_Event_Inputs_Primary51.csv: 51 events ({int(E51.n_banks.sum())} banks: the 55 of the primary panel and the 7 "
              f"bought with them), {int(E51.y.sum())} with a positive CAR.")

# ---------------------------------------------------------------- report
cols = ["n_banks", "failed_assets_usd_bn", "G_deposits_usd_bn", "N_npl_pct", "L_deposit_change_pct", "T_npl_change_pp",
        "C_buyer_capital_pct", "E_relative_size"]
lines = ["Acquisition-event inputs (build_event_inputs.py, release 4.3)", ""] + report + ["", "Consolidated multi-bank events:"]
with pd.option_context("display.width", 200, "display.max_columns", 20):
    lines.append(C.set_index(["event_id", "scope"])[cols].round(4).to_string())
(OUTD / "Event_Inputs_Report.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
