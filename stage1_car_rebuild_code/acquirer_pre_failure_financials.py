"""Acquirer financials from the last call report BEFORE the failure date.

Why (2026-10 data audit): pull_acquirer_financials.py selects the first call
report on or after the failure date (FIRST_REPDTE_ON_OR_AFTER_FAILURE_DATE).
That report already contains the acquired bank and any bargain-purchase gain;
First-Citizens' report for 2023-03-31, used for SVB, shows total assets of
about $215B, roughly double its size before the deal. A model meant to be used
when the bid is decided can only use the buyer's financials as of the last
report before the failure.

This script re-selects the quarter from the per-certificate histories that
pull_acquirer_financials.py already cached in fdic_acquirer_pull_checkpoint.json,
so it needs no network access when that file is present; otherwise it queries
the FDIC BankFind API exactly as the original script does.

Usage:
    python acquirer_pre_failure_financials.py Stage1_Final_Public_Modeling_Dataset.csv
Writes Stage1_Acquirer_PreFailure_Financials.csv with one row per transaction:
pre-failure values (suffix _pre), the values currently in the file (suffix
_post) and the report dates, so the two can be compared and the model inputs
replaced.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import pandas as pd

CHECKPOINT = "fdic_acquirer_pull_checkpoint.json"
OUTPUT = "Stage1_Acquirer_PreFailure_Financials.csv"
API_BASE = "https://api.fdic.gov/banks/financials"
FIELDS = "CERT,REPDTE,ASSET,DEP,EQ,EQTOT,RBC1AAJ"


def load_histories() -> dict[str, list[dict]]:
    path = Path(CHECKPOINT)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")).get("cert_cache", {})
    return {}


def fetch_history(cert: str) -> list[dict]:
    import requests  # only needed without the checkpoint

    url = (f"{API_BASE}?filters={quote(f'CERT:{cert}')}&fields={FIELDS}"
           "&format=json&limit=10000&sort_by=REPDTE&sort_order=ASC")
    resp = requests.get(url, timeout=60, headers={"User-Agent": "FDIC-Stage1-Research/1.0"})
    resp.raise_for_status()
    out = []
    for item in resp.json().get("data", []):
        row = item.get("data", item)
        rep = pd.to_datetime(str(row.get("REPDTE")), errors="coerce")
        if pd.isna(rep):
            continue
        equity = row.get("EQTOT") if row.get("EQTOT") is not None else row.get("EQ")
        asset = row.get("ASSET")
        out.append({
            "REPDTE": rep.strftime("%Y-%m-%d"),
            "ASSET": asset, "DEP": row.get("DEP"), "EQTOT": equity,
            "acquirer_capital_ratio": (equity / asset) if asset and equity is not None else None,
        })
    time.sleep(0.25)
    return out


def last_before(records: list[dict], failure_date: pd.Timestamp) -> dict | None:
    before = [r for r in records if pd.Timestamp(r["REPDTE"]) < failure_date.normalize()]
    if not before:
        return None
    return max(before, key=lambda r: pd.Timestamp(r["REPDTE"]))


def main(path: str) -> None:
    df = pd.read_csv(path, dtype={"acquirer_cert": str})
    df["failure_date"] = pd.to_datetime(df["failure_date"])
    histories = load_histories()
    rows = []
    for _, r in df.iterrows():
        cert = str(r["acquirer_cert"]).replace(".0", "")
        if cert not in histories:
            try:
                histories[cert] = fetch_history(cert)
            except Exception as exc:  # noqa: BLE001
                print(f"{r['transaction_id']}: could not fetch CERT {cert}: {exc}")
                histories[cert] = []
        rec = last_before(histories[cert], r["failure_date"])
        rows.append({
            "transaction_id": r["transaction_id"],
            "acquirer_cert": cert,
            "failure_date": r["failure_date"].strftime("%Y-%m-%d"),
            "acquirer_repdate_pre": rec["REPDTE"] if rec else None,
            "acquirer_assets_pre": rec["ASSET"] if rec else None,
            "acquirer_deposits_pre": rec["DEP"] if rec else None,
            "acquirer_equity_pre": rec["EQTOT"] if rec else None,
            "acquirer_capital_ratio_pre": rec["acquirer_capital_ratio"] if rec else None,
            "acquirer_assets_post": r.get("acquirer_assets"),
            "acquirer_capital_ratio_post": r.get("acquirer_capital_ratio"),
        })
    out = pd.DataFrame(rows)
    out["assets_post_over_pre"] = out["acquirer_assets_post"] / out["acquirer_assets_pre"]
    out.to_csv(OUTPUT, index=False)
    print(f"Saved {OUTPUT}: {out['acquirer_repdate_pre'].notna().sum()} of {len(out)} rows with a pre-failure report")
    big = out.sort_values("assets_post_over_pre", ascending=False).head(10)
    print("\nLargest jumps in acquirer assets between the two reports:")
    print(big[["transaction_id", "acquirer_repdate_pre", "assets_post_over_pre",
               "acquirer_capital_ratio_pre", "acquirer_capital_ratio_post"]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Stage1_Final_Public_Modeling_Dataset.csv")
