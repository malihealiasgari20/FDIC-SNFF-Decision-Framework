"""Compare the June 2026 locked modeling file with the rebuilt one.

Usage:
    python compare_outcomes.py OLD.csv NEW.csv [--out changes.csv]

Prints, for the full file and for the 150-largest sample (INCLUDED rows):
rows dropped, rows added, outcome flips, and ticker or event-date changes.
"""

from __future__ import annotations

import argparse

import pandas as pd

KEY = "transaction_id"


def summarize(old: pd.DataFrame, new: pd.DataFrame, label: str) -> pd.DataFrame:
    o, n = old.set_index(KEY), new.set_index(KEY)
    dropped = sorted(set(o.index) - set(n.index))
    added = sorted(set(n.index) - set(o.index))
    both = sorted(set(o.index) & set(n.index))
    rows = []
    for t in dropped:
        rows.append({KEY: t, "change": "dropped", "bank": o.at[t, "failed_bank_name"],
                     "old_ticker": o.at[t, "ticker"], "new_ticker": None,
                     "old_car": o.at[t, "car_3day"], "new_car": None,
                     "old_flag": o.at[t, "value_created_flag"], "new_flag": None})
    for t in added:
        rows.append({KEY: t, "change": "added", "bank": n.at[t, "failed_bank_name"],
                     "old_ticker": None, "new_ticker": n.at[t, "ticker"],
                     "old_car": None, "new_car": n.at[t, "car_3day"],
                     "old_flag": None, "new_flag": n.at[t, "value_created_flag"]})
    for t in both:
        changes = []
        if o.at[t, "ticker"] != n.at[t, "ticker"]:
            changes.append("ticker")
        if str(o.at[t, "announcement_date"])[:10] != str(n.at[t, "announcement_date"])[:10]:
            changes.append("event_date")
        if o.at[t, "value_created_flag"] != n.at[t, "value_created_flag"]:
            changes.append("FLAG_FLIP")
        elif abs(float(o.at[t, "car_3day"]) - float(n.at[t, "car_3day"])) > 1e-6:
            changes.append("car_value")
        if changes:
            rows.append({KEY: t, "change": "+".join(changes), "bank": n.at[t, "failed_bank_name"],
                         "old_ticker": o.at[t, "ticker"], "new_ticker": n.at[t, "ticker"],
                         "old_car": o.at[t, "car_3day"], "new_car": n.at[t, "car_3day"],
                         "old_flag": o.at[t, "value_created_flag"], "new_flag": n.at[t, "value_created_flag"]})
    out = pd.DataFrame(rows)
    print(f"\n=== {label} ===")
    print(f"old rows {len(o)} (flag=1: {int((o.value_created_flag == 1).sum())}), "
          f"new rows {len(n)} (flag=1: {int((n.value_created_flag == 1).sum())})")
    print(f"dropped {len(dropped)}, added {len(added)}, "
          f"flag flips {int(out['change'].str.contains('FLAG_FLIP').sum()) if len(out) else 0}")
    if len(out):
        print(out.to_string(index=False))
    return out.assign(scope=label)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--out", default="Stage1_Outcome_Changes_2026_10.csv")
    a = ap.parse_args()
    old, new = pd.read_csv(a.old), pd.read_csv(a.new)
    parts = [summarize(old, new, "all public rows")]
    inc = "inclusion_exclusion_reason"
    parts.append(summarize(old[old[inc] == "INCLUDED"], new[new[inc] == "INCLUDED"],
                           "150-largest sample (the paper's main panel)"))
    pd.concat(parts).to_csv(a.out, index=False)
    print(f"\nSaved {a.out}")


if __name__ == "__main__":
    main()
