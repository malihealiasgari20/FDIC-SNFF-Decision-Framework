"""Bank-sector benchmark for the announcement CARs (response to review Issue 4).

The primary outcome adjusts acquirer returns by SPY. To check that bank-sector
movements (2008-2010 above all) do not drive the results, the same reaction-day
window [-1,+1] is recomputed with a bank-sector benchmark: the equal-weighted
daily return of the U.S.-listed bank holding companies with full price series in
the June 2026 price cache (no bank index or ETF is in the cache). For each
transaction the index leaves out the acquirer itself and every bank whose own
reaction day in the 90-transaction panel lies within four calendar days of the
transaction's reaction day, so that no constituent carries its own deal news.
Foreign-owned parents (BBVA, BNS, SAN, TD) are not constituents, nor are CYN and
EVER: their cached series start in 2021 and 2018 and belong to the non-bank
companies that later reused the tickers of City National and EverBank.

Returns are aligned exactly as in 03_.../code/event_convention_report.py (stock
and SPY on common dates); the SPY-adjusted CAR recomputed here must equal the
frozen primary CAR, which checks the alignment.

usage: python3 -I bank_benchmark_cars.py <research_folder> <out_csv>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
cache = json.load(open(ROOT / "00_original_stage1_2026-06-19/raw_pulls/car_price_cache.json"))
ev = pd.read_csv(ROOT / "03_revised_framework_2026-10-29/data/Event_Convention_Comparison_90.csv")
assert len(ev) == 90
FOREIGN = {"BBVA", "BNS", "SAN", "TD"}
NOT_BANKS = {"CYN", "EVER"}  # ticker reuse after the banks were acquired (series start 2021-10-20 and 2018-06-28)


def series(key: str) -> pd.Series:
    s = pd.Series(cache.get(key) or {}, dtype=float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def stock_for(ticker: str, day: pd.Timestamp) -> pd.Series:
    """Same lookup as Stage 1 and event_convention_report.py."""
    full = series(ticker)
    if len(full) and full.index.min() <= day - pd.Timedelta(days=10) and full.index.max() >= day + pd.Timedelta(days=10):
        return full
    for k in cache:
        p = k.split("|")
        if len(p) == 3 and p[0] == ticker and pd.Timestamp(p[1]) <= day <= pd.Timestamp(p[2]) and cache[k]:
            return series(k)
    raise KeyError(f"no prices for {ticker} around {day.date()}")


spy = series("SPY")
constituents = sorted(k for k, v in cache.items() if v and "|" not in k and k != "SPY" and k not in FOREIGN | NOT_BANKS)
prices = {k: series(k) for k in constituents}
reaction_days = [(t, pd.Timestamp(d)) for t, d in zip(ev.ticker, ev.day_r_first_reaction)]

rows = []
for r in ev.itertuples():
    ann = pd.Timestamp(r.release_date)
    day_r = pd.Timestamp(r.day_r_first_reaction)
    s = stock_for(r.ticker, ann)
    a = pd.DataFrame({"stock": s, "market": spy}).dropna()
    rr = a.index.get_loc(day_r)
    ret_s, ret_m = a.stock.pct_change(), a.market.pct_change()
    excluded = {r.ticker} | {t for t, d in reaction_days if abs((d - day_r).days) <= 4}
    use = [k for k in constituents if k not in excluded]
    panel = pd.DataFrame({k: prices[k].reindex(a.index) for k in use})
    ret_b = panel.pct_change(fill_method=None).mean(axis=1, skipna=True)
    n_b = panel.pct_change(fill_method=None).iloc[rr - 1:rr + 2].notna().sum(axis=1).min()
    window = slice(rr - 1, rr + 2)
    car_spy = (ret_s - ret_m).iloc[window].sum()
    car_bank = (ret_s - ret_b).iloc[window].sum()
    rows.append({"transaction_id": r.transaction_id, "in_primary_panel": r.in_primary_panel, "ticker": r.ticker,
                 "day_r_first_reaction": r.day_r_first_reaction, "car_reaction_m1p1_spy_check": car_spy,
                 "car_reaction_m1p1_bank": car_bank, "y_reaction_m1p1_bank": int(car_bank > 0),
                 "bank_index_return_window": ret_b.iloc[window].sum(), "spy_return_window": ret_m.iloc[window].sum(),
                 "index_constituents_min": int(n_b), "index_excluded": ";".join(sorted(excluded))})
t = pd.DataFrame(rows)
assert np.allclose(t.car_reaction_m1p1_spy_check, ev.car_reaction_m1p1, atol=1e-9), "alignment differs from the frozen CARs"
assert (t.index_constituents_min >= 20).all()
t.to_csv(OUT, index=False)
p = t[t.in_primary_panel == 1]
flips = int((p.y_reaction_m1p1_bank != ev[ev.in_primary_panel == 1].y_reaction_m1p1.to_numpy()).sum())
print(f"constituents: {len(constituents)} ({', '.join(constituents)}); per-event minimum {t.index_constituents_min.min()}")
print(f"primary 55: positive with bank benchmark {int(p.y_reaction_m1p1_bank.sum())} (SPY: {int(ev[ev.in_primary_panel == 1].y_reaction_m1p1.sum())}); "
      f"labels changed {flips}; corr(CAR spy, CAR bank) {np.corrcoef(p.car_reaction_m1p1_spy_check, p.car_reaction_m1p1_bank)[0, 1]:.3f}")
