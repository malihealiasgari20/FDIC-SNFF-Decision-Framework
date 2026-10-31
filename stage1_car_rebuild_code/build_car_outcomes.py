"""Step 6: Build CAR outcome fields for publicly listed acquirers.

REVISION 2026-10 (data audit). Changes relative to the June 2026 version:
  * The event date is the date the acquisition became public. For ordinary
    P&A deals that is the FDIC closing date (unchanged). For bridge-bank
    resolutions the sale was announced later, so event_date_overrides.csv
    supplies the announcement date (SVB: 2023-03-26; Signature: 2023-03-19).
    The June version measured these two CARs around the failure date, i.e.
    during the March 2023 bank run, before any buyer was known.
  * The acquirer's FDIC certificate is passed to the ticker map, which now
    resolves certain acquirers by certificate (see acquirer_ticker_map.py).
  * Output carries parent_listing (US / FOREIGN / OTC / PRIVATE) and
    event_date_source.
The CAR itself is unchanged: market-adjusted daily returns (stock minus SPY),
summed over trading days t-1, t, t+1, where t is the first trading day on or
after the event date.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from acquirer_ticker_map import build_ticker_map
from historical_prices import download_prices

INPUT_SAMPLE = "Stage1_Master_Analytic_Sample.csv"
OUTPUT_CSV = "Stage1_Master_Outcomes_Completed.csv"
OUTPUT_XLSX = "Stage1_Master_Outcomes_Completed.xlsx"
OUTPUT_LOG = "Stage1_CAR_Build_Log.csv"
TICKER_MAP_CSV = "Stage1_Acquirer_Ticker_Map.csv"
PRICE_CACHE = "car_price_cache.json"
AUDIT_CSV = "Stage1_NO_PRICE_Audit.csv"
EVENT_DATE_OVERRIDES_CSV = "event_date_overrides.csv"

MARKET_TICKER = "SPY"
MARKET_START, MARKET_END = "2008-01-01", "2025-01-01"
REQUEST_DELAY = 0.15

CAR_FIELDS = [
    "price_t_minus_1", "price_t", "price_t_plus_1",
    "return_t_minus_1", "return_t", "return_t_plus_1",
    "market_return_t_minus_1", "market_return_t", "market_return_t_plus_1",
    "abnormal_return_t_minus_1", "abnormal_return_t", "abnormal_return_t_plus_1",
    "car_3day", "value_created_flag", "event_trading_date",
    # robustness windows (2026-10): the primary outcome above is unchanged
    "first_reaction_date", "car_0p1", "value_created_flag_0p1",
    "car_reaction_m1p1", "value_created_flag_reaction",
]


def compute_event_car(
    stock: pd.Series,
    market: pd.Series,
    announcement_date: pd.Timestamp,
    after_close: bool = True,
) -> dict:
    """Primary outcome: CAR over trading days t-1..t+1, t = first trading day on or after
    the announcement date. Robustness outputs: CAR over t..t+1 (Cowan and Salotti's [0,+1]),
    and CAR over r-1..r+1 where r is the first trading day on which the market could react
    (the next trading day when an announcement made after the close falls on a trading day)."""
    if stock.empty or market.empty:
        return {"status": "NO_PRICE_DATA"}

    aligned = pd.DataFrame({"stock": stock, "market": market}).dropna()
    if aligned.empty:
        return {"status": "NO_ALIGNED_PRICES"}

    event_day = pd.to_datetime(announcement_date).normalize()
    on_or_after = aligned.index[aligned.index >= event_day]
    if len(on_or_after) == 0:
        return {"status": "NO_TRADING_DAY_ON_OR_AFTER_EVENT"}

    event_idx = aligned.index.get_loc(on_or_after[0])
    if event_idx < 1 or event_idx + 1 >= len(aligned):
        return {"status": "INSUFFICIENT_EVENT_WINDOW"}

    stock_rets = aligned["stock"].pct_change()
    mkt_rets = aligned["market"].pct_change()
    abnormal = stock_rets - mkt_rets

    i = event_idx
    result = {
        "status": "CAR_COMPUTED",
        "announcement_date": event_day.strftime("%Y-%m-%d"),
        "event_trading_date": aligned.index[i].strftime("%Y-%m-%d"),
        "price_t_minus_1": float(aligned["stock"].iloc[i - 1]),
        "price_t": float(aligned["stock"].iloc[i]),
        "price_t_plus_1": float(aligned["stock"].iloc[i + 1]),
        "return_t_minus_1": float(stock_rets.iloc[i - 1]),
        "return_t": float(stock_rets.iloc[i]),
        "return_t_plus_1": float(stock_rets.iloc[i + 1]),
        "market_return_t_minus_1": float(mkt_rets.iloc[i - 1]),
        "market_return_t": float(mkt_rets.iloc[i]),
        "market_return_t_plus_1": float(mkt_rets.iloc[i + 1]),
        "abnormal_return_t_minus_1": float(abnormal.iloc[i - 1]),
        "abnormal_return_t": float(abnormal.iloc[i]),
        "abnormal_return_t_plus_1": float(abnormal.iloc[i + 1]),
    }
    result["car_3day"] = (
        result["abnormal_return_t_minus_1"]
        + result["abnormal_return_t"]
        + result["abnormal_return_t_plus_1"]
    )
    result["value_created_flag"] = int(result["car_3day"] > 0)

    result["car_0p1"] = float(abnormal.iloc[i] + abnormal.iloc[i + 1])
    result["value_created_flag_0p1"] = int(result["car_0p1"] > 0)
    j = i + 1 if (after_close and aligned.index[i] == event_day) else i
    result["first_reaction_date"] = aligned.index[j].strftime("%Y-%m-%d")
    if j + 1 < len(aligned):
        result["car_reaction_m1p1"] = float(abnormal.iloc[j - 1] + abnormal.iloc[j] + abnormal.iloc[j + 1])
        result["value_created_flag_reaction"] = int(result["car_reaction_m1p1"] > 0)
    return result


def load_event_date_overrides(path: str = EVENT_DATE_OVERRIDES_CSV) -> dict[str, tuple[pd.Timestamp, str, str]]:
    """transaction_id -> (event date, source note, announcement timing)."""
    p = Path(path)
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return {
        str(r["transaction_id"]): (pd.to_datetime(r["event_date"]), str(r.get("event_date_source", "")),
                                   str(r.get("announcement_timing", "AFTER_CLOSE") or "AFTER_CLOSE"))
        for _, r in df.iterrows()
    }


def event_date_for(row: pd.Series, overrides: dict) -> tuple[pd.Timestamp, str, str]:
    """Event date, its source, and announcement timing. FDIC closings are announced after
    the market close unless an override says otherwise (PRE_OPEN, NON_TRADING_DAY)."""
    tx = str(row["transaction_id"])
    if tx in overrides:
        date, note, timing = overrides[tx]
        return date, f"OVERRIDE: {note}", timing
    return pd.to_datetime(row["failure_date"]), "FDIC_CLOSING_DATE", "AFTER_CLOSE"


def load_price_cache() -> dict:
    path = Path(PRICE_CACHE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_price_cache(cache: dict) -> None:
    Path(PRICE_CACHE).write_text(json.dumps(cache, indent=2), encoding="utf-8")


def series_from_cache(cache: dict, key: str) -> pd.Series:
    prices = cache.get(key, {})
    if not prices:
        return pd.Series(dtype=float)
    idx = pd.to_datetime(list(prices.keys()))
    vals = [prices[k] for k in prices]
    return pd.Series(vals, index=idx).sort_index()


def get_stock_for_event(
    tickers: list[str],
    event_date: pd.Timestamp,
    cache: dict,
) -> tuple[pd.Series, str | None]:
    event_date = pd.to_datetime(event_date)
    start = (event_date - pd.Timedelta(days=120)).strftime("%Y-%m-%d")
    end = (event_date + pd.Timedelta(days=120)).strftime("%Y-%m-%d")

    for ticker in tickers:
        window_key = f"{ticker}|{start}|{end}"
        series = series_from_cache(cache, window_key)
        if series.empty:
            series = series_from_cache(cache, ticker)
        if not series.empty:
            window = series[
                (series.index >= event_date - pd.Timedelta(days=120))
                & (series.index <= event_date + pd.Timedelta(days=120))
            ]
            if len(window) >= 5:
                return window, ticker

        prices, used = download_prices([ticker], start, end)
        if not prices.empty:
            cache[window_key] = {d.strftime("%Y-%m-%d"): float(v) for d, v in prices.items()}
            time.sleep(REQUEST_DELAY)
            return prices, used or ticker

    combined, used = download_prices(tickers, start, end)
    if not combined.empty and used:
        cache[f"{used}|{start}|{end}"] = {
            d.strftime("%Y-%m-%d"): float(v) for d, v in combined.items()
        }
        return combined, used
    return pd.Series(dtype=float), None


def tickers_for_row(row: pd.Series) -> list[str]:
    candidates_raw = row.get("ticker_candidates")
    ticker = row.get("ticker")
    if pd.notna(candidates_raw) and str(candidates_raw).strip():
        return [t for t in str(candidates_raw).split("|") if t]
    if pd.notna(ticker):
        return [str(ticker)]
    return []


def car_row(row: pd.Series, market: pd.Series, cache: dict, date_overrides: dict) -> dict:
    """CAR fields for one transaction (shared with build_public_modeling_dataset.py)."""
    base = row.to_dict()
    event_date, event_source, timing = event_date_for(row, date_overrides)
    base["event_date_source"] = event_source
    base["announcement_timing"] = timing
    tickers = tickers_for_row(row)
    if not tickers:
        pending = str(row.get("ticker_match_method", "") or "").startswith("PENDING_VERIFICATION")
        base.update(
            {
                "ticker": None,
                "announcement_date": event_date.strftime("%Y-%m-%d"),
                # a proposed listed parent awaiting the authors' sign-off (acquirer_ticker_map.py, note 6)
                "car_status": "PENDING_TICKER_VERIFICATION" if pending else "PRIVATE_ACQUIRER_NO_TICKER",
                "car_3day": np.nan,
                "value_created_flag": np.nan,
            }
        )
        return base

    stock, used_ticker = get_stock_for_event(tickers, event_date, cache)
    car = compute_event_car(stock, market, event_date, after_close=(timing == "AFTER_CLOSE"))
    base["ticker"] = used_ticker or row.get("ticker")
    base["announcement_date"] = car.get("announcement_date", event_date.strftime("%Y-%m-%d"))
    base["car_status"] = car.get("status")
    base["ticker_attempted"] = "|".join(tickers)
    for field in CAR_FIELDS:
        base[field] = car.get(field, np.nan)
    return base


def main() -> None:
    sample = pd.read_csv(INPUT_SAMPLE)
    sample["failure_date"] = pd.to_datetime(sample["failure_date"])

    ticker_map = build_ticker_map(
        sample["acquirer_name"],
        sample["failure_date"],
        sample["transaction_id"],
        sample["acquirer_cert"] if "acquirer_cert" in sample.columns else None,
    )
    ticker_map.to_csv(TICKER_MAP_CSV, index=False)

    merged = sample.merge(
        ticker_map,
        on=["transaction_id", "acquirer_name", "failure_date"],
        how="left",
    )

    cache = load_price_cache()
    market, _ = download_prices([MARKET_TICKER], MARKET_START, MARKET_END)
    cache[MARKET_TICKER] = {d.strftime("%Y-%m-%d"): float(v) for d, v in market.items()}
    save_price_cache(cache)
    date_overrides = load_event_date_overrides()

    public_tickers = sorted(t for t in merged["ticker"].dropna().unique())
    print(f"Processing {len(merged)} rows ({len(public_tickers)} public tickers)...")

    car_rows = []
    audit_rows = []
    for _, row in merged.iterrows():
        base = car_row(row, market, cache, date_overrides)
        car_rows.append(base)
        status = base.get("car_status")
        if status not in ("CAR_COMPUTED", "PRIVATE_ACQUIRER_NO_TICKER", "PENDING_TICKER_VERIFICATION"):
            audit_rows.append(
                {
                    "transaction_id": row["transaction_id"],
                    "failure_date": row["failure_date"].strftime("%Y-%m-%d"),
                    "acquirer_name": row["acquirer_name"],
                    "ticker_attempted": base.get("ticker_attempted"),
                    "ticker_used": base.get("ticker"),
                    "car_status": status,
                    "recommended_action": "Set FMP_API_KEY env var and re-run, or pull from CRSP",
                }
            )

    save_price_cache(cache)
    result = pd.DataFrame(car_rows)
    result.to_csv(OUTPUT_CSV, index=False)
    result.to_excel(OUTPUT_XLSX, index=False, sheet_name="Outcomes")

    log = pd.DataFrame(
        [
            {"metric": "total_rows", "value": len(result)},
            {"metric": "public_acquirers_mapped", "value": int(result["ticker"].notna().sum())},
            {"metric": "private_or_unmapped", "value": int(result["ticker"].isna().sum())},
            {"metric": "pending_ticker_verification", "value": int((result["car_status"] == "PENDING_TICKER_VERIFICATION").sum())},
            {"metric": "car_computed", "value": int((result["car_status"] == "CAR_COMPUTED").sum())},
            {"metric": "no_price_data", "value": int((result["car_status"] == "NO_PRICE_DATA").sum())},
            {"metric": "event_date_overrides_used", "value": int(result["event_date_source"].str.startswith("OVERRIDE").sum())},
            {"metric": "value_created_flag_1", "value": int((result["value_created_flag"] == 1).sum())},
            {"metric": "value_created_flag_0", "value": int((result["value_created_flag"] == 0).sum())},
        ]
    )
    for listing, n in result["parent_listing"].value_counts().items():
        log.loc[len(log)] = {"metric": f"parent_listing_{listing}", "value": int(n)}
    log.to_csv(OUTPUT_LOG, index=False)

    if audit_rows:
        audit = pd.merge(
            pd.read_csv("event_ticker_overrides.csv"),
            pd.DataFrame(audit_rows),
            on="transaction_id",
            how="right",
        )
        audit.to_csv(AUDIT_CSV, index=False)
    else:
        pd.DataFrame(audit_rows).to_csv(AUDIT_CSV, index=False)

    print(log.to_string(index=False))
    print(f"\nSaved: {OUTPUT_CSV}, {AUDIT_CSV}")
    print("\nCAR status breakdown:")
    print(result["car_status"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
