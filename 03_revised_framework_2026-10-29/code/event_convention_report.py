"""Event-time conventions for the outcome label: evidence for the choice (Step 3).

For each transaction the market-adjusted abnormal return (stock minus SPY, as in
Stage 1) is rebuilt day by day from the June 2026 price cache around the first
trading session in which the market could act on the FDIC announcement (day r,
from the verified timing in the source ledger). The three candidate CARs are
then sums of these daily returns, and must equal the 02b rebuild:

  reaction-day [-1,+1]  r-1, r, r+1   (for a Friday-evening release: Fri, Mon, Tue)
  release [0,+1]        d, d+1        where d is the first trading day on or after the release date
  June [-1,+1]          d-1, d, d+1   (for a Friday-evening release: Thu, Fri, Mon)

Also reported: average abnormal returns by day relative to r (where the price
response sits), which labels each window change and why, and the labels under a
market model (beta from days r-130..r-11; at least 60 days) as a check on the
market-adjusted benchmark.

usage: python3 -I event_convention_report.py <research_folder> <framework_folder>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, FW = Path(sys.argv[1]), Path(sys.argv[2])
cache = json.load(open(ROOT / "00_original_stage1_2026-06-19/raw_pulls/car_price_cache.json"))
ev = pd.read_csv(ROOT / "02b_car_conventions_2026-10-29/Stage1_Cache_Only_Rebuild_90.csv")
ledger = pd.read_csv(FW / "data/Source_Verification_Ledger_90.csv")
assert set(ev.transaction_id) == set(ledger.transaction_id) and len(ev) == 90
ev["in_primary_panel"] = (ev.inclusion_exclusion_reason == "INCLUDED").astype(int)
# the timing used for the windows is the verified timing
assert (ev.set_index("transaction_id").announcement_timing == ledger.set_index("transaction_id").timing_class.reindex(ev.transaction_id)).all()


def series(key: str) -> pd.Series:
    v = cache.get(key) or {}
    s = pd.Series(v, dtype=float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


spy = series("SPY")


def stock_for(ticker: str, day: pd.Timestamp) -> pd.Series:
    """Same lookup as Stage 1: the full series if it covers the event, else a cached window around it."""
    full = series(ticker)
    if len(full) and full.index.min() <= day - pd.Timedelta(days=10) and full.index.max() >= day + pd.Timedelta(days=10):
        return full
    for k in cache:
        p = k.split("|")
        if len(p) == 3 and p[0] == ticker and pd.Timestamp(p[1]) <= day <= pd.Timestamp(p[2]) and cache[k]:
            return series(k)
    raise KeyError(f"no prices for {ticker} around {day.date()}")


rows, ar_by_day = [], []
for r in ev.itertuples():
    ann = pd.Timestamp(r.announcement_date)
    s = stock_for(r.ticker, ann)
    a = pd.DataFrame({"stock": s, "market": spy}).dropna()
    ar = a.stock.pct_change() - a.market.pct_change()
    d = a.index.get_loc(a.index[a.index >= ann][0])           # first trading day on/after the release date
    rr = a.index.get_loc(pd.Timestamp(r.first_reaction_date))  # first session that could react
    car_c = ar.iloc[rr - 1:rr + 2].sum()
    car_b = ar.iloc[d:d + 2].sum()
    car_a = ar.iloc[d - 1:d + 2].sum()
    # market model on r-130..r-11 (stock and SPY returns), at least 60 days
    est = pd.DataFrame({"s": a.stock.pct_change(), "m": a.market.pct_change()}).iloc[max(1, rr - 130):rr - 10].dropna()
    if len(est) >= 60:
        beta, alpha = np.polyfit(est.m, est.s, 1)
        mm = a.stock.pct_change() - (alpha + beta * a.market.pct_change())
        car_c_mm = mm.iloc[rr - 1:rr + 2].sum()
    else:
        beta = alpha = car_c_mm = np.nan
    rows.append({
        "transaction_id": r.transaction_id, "in_primary_panel": r.in_primary_panel, "failed_bank_name": r.failed_bank_name, "ticker": r.ticker,
        "release_date": r.announcement_date, "timing_class": r.announcement_timing,
        "day_d_first_trading_on_or_after_release": a.index[d].date(), "day_r_first_reaction": a.index[rr].date(),
        "sessions_r_minus_d": rr - d,
        "ar_r_minus_2": ar.iloc[rr - 2], "ar_r_minus_1": ar.iloc[rr - 1], "ar_r": ar.iloc[rr], "ar_r_plus_1": ar.iloc[rr + 1],
        "car_reaction_m1p1": car_c, "car_release_0p1": car_b, "car_release_m1p1_june": car_a,
        "car_reaction_m1p1_market_model": car_c_mm, "mm_beta": beta, "mm_est_days": len(est),
        "car_02b_reaction": r.car_reaction_m1p1, "car_02b_0p1": r.car_0p1, "car_02b_june": r.car_3day,
        "acquirer_day": f"{r.ticker}|{a.index[rr].date()}",
    })
    for k in range(-5, 6):
        ar_by_day.append({"transaction_id": r.transaction_id, "in_primary_panel": r.in_primary_panel, "acquirer_day": f"{r.ticker}|{a.index[rr].date()}",
                          "rel_day": k, "ar": ar.iloc[rr + k]})

t = pd.DataFrame(rows)
for new, old in (("car_reaction_m1p1", "car_02b_reaction"), ("car_release_0p1", "car_02b_0p1"),
                 ("car_release_m1p1_june", "car_02b_june")):
    assert np.allclose(t[new], t[old], atol=1e-9), f"{new} differs from the 02b rebuild"
t = t.drop(columns=["car_02b_reaction", "car_02b_0p1", "car_02b_june"])
for c, y in (("car_reaction_m1p1", "y_reaction_m1p1"), ("car_release_0p1", "y_release_0p1"),
             ("car_release_m1p1_june", "y_release_m1p1_june"), ("car_reaction_m1p1_market_model", "y_reaction_m1p1_market_model")):
    t[y] = (t[c] > 0).astype(int)
t["flip_june_vs_reaction"] = (t.y_release_m1p1_june != t.y_reaction_m1p1).astype(int)
t["flip_release01_vs_reaction"] = (t.y_release_0p1 != t.y_reaction_m1p1).astype(int)
t["flip_june_vs_release01"] = (t.y_release_m1p1_june != t.y_release_0p1).astype(int)
t["flip_market_model"] = (t.y_reaction_m1p1_market_model != t.y_reaction_m1p1).astype(int)
t.sort_values(["in_primary_panel", "transaction_id"], ascending=[False, True]).to_csv(FW / "data/Event_Convention_Comparison_90.csv", index=False)

L: list[str] = []
def say(s=""):
    print(s); L.append(s)

A = pd.DataFrame(ar_by_day)
for title, tt, aa in (("PRIMARY PANEL (55 transactions)", t[t.in_primary_panel == 1], A[A.in_primary_panel == 1]),
                      ("BROADER PANEL (90 transactions)", t, A)):
    say(f"=== {title}; market-adjusted returns (stock minus SPY) ===")
    say(f"timing (verified): {tt.timing_class.value_counts().to_dict()}; sessions from day d to day r: {tt.sessions_r_minus_d.value_counts().to_dict()}")
    dup = tt.acquirer_day.value_counts()
    say(f"acquirer-days: {tt.acquirer_day.nunique()} distinct (same buyer, same day: "
        + "; ".join(f"{k} x{v}" for k, v in dup.items() if v > 1) + ")")
    say("\n1. Average abnormal return by session relative to r (first session that could react)")
    g2 = aa.groupby(["acquirer_day", "rel_day"]).ar.mean().groupby("rel_day")
    say(f"  {'day':>4} {'mean AR, deals':>15} {'t':>6} {'% > 0':>6} | {'mean AR, acquirer-days':>23} {'t':>6} {'median':>8}")
    for k in range(-5, 6):
        x, y = aa[aa.rel_day == k].ar, g2.get_group(k)
        say(f"  {k:>+4d} {x.mean():>15.4f} {x.mean() / (x.std(ddof=1) / np.sqrt(len(x))):>6.2f} {100 * (x > 0).mean():>5.0f}% | "
            f"{y.mean():>23.4f} {y.mean() / (y.std(ddof=1) / np.sqrt(len(y))):>6.2f} {y.median():>8.4f}")
    pre = aa[aa.rel_day.isin([-2, -1])].groupby("transaction_id").ar.sum()
    pre_g = aa[aa.rel_day.isin([-2, -1])].groupby(["acquirer_day", "transaction_id"]).ar.sum().groupby("acquirer_day").mean()
    say(f"  pre-news drift, CAR over r-2..r-1: mean {pre.mean():.4f} (t {pre.mean() / (pre.std(ddof=1) / np.sqrt(len(pre))):.2f}); "
        f"acquirer-days {pre_g.mean():.4f} (t {pre_g.mean() / (pre_g.std(ddof=1) / np.sqrt(len(pre_g))):.2f})")
    say("\n2. Labels (value created = CAR > 0)")
    for c, nm in (("y_reaction_m1p1", "reaction-day [-1,+1] (r-1, r, r+1)"), ("y_release_0p1", "release [0,+1] (d, d+1)"),
                  ("y_release_m1p1_june", "June [-1,+1] (d-1, d, d+1)"), ("y_reaction_m1p1_market_model", "reaction-day [-1,+1], market model")):
        say(f"  {nm:40s} {int(tt[c].sum())} positive / {int((1 - tt[c]).sum())} not")
    say(f"  label changes: June vs reaction-day {int(tt.flip_june_vs_reaction.sum())}; release [0,+1] vs reaction-day "
        f"{int(tt.flip_release01_vs_reaction.sum())}; June vs release [0,+1] {int(tt.flip_june_vs_release01.sum())}; "
        f"market model vs market-adjusted (reaction-day) {int(tt.flip_market_model.sum())}")
    fl = tt[tt.flip_june_vs_reaction == 1]
    say(f"  the {len(fl)} June-vs-reaction changes: {int((fl.y_release_m1p1_june > fl.y_reaction_m1p1).sum())} positive -> not, "
        f"{int((fl.y_release_m1p1_june < fl.y_reaction_m1p1).sum())} not -> positive; all from after-close releases: "
        f"{bool((fl.timing_class == 'AFTER_CLOSE').all())}")
    say(f"  median |CAR| (reaction-day): all {tt.car_reaction_m1p1.abs().median():.4f}; label-changing deals "
        f"{fl.car_reaction_m1p1.abs().median():.4f}")
    say(f"  market-model estimation: {int(tt.mm_est_days.ge(60).sum())} of {len(tt)} with >= 60 days; median beta {tt.mm_beta.median():.2f}")
    say("")

say("3. What each window contains, by timing class (sessions relative to r)")
say("  AFTER_CLOSE: June = r-2, r-1, r (two sessions before the news, one after); release [0,+1] = r-1, r;")
say("               reaction-day = r-1, r, r+1")
say("  PRE_OPEN / NON_TRADING_DAY (First Republic, SVB): June = r-1, r, r+1; release [0,+1] = r, r+1; reaction-day = r-1, r, r+1")
say("  Only the reaction-day window has the same position relative to the news for every transaction.")

(FW / "data/Event_Convention_Report.txt").write_text("\n".join(L) + "\n")
