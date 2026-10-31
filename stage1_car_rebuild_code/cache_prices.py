"""Offline stand-in for historical_prices.py: serves prices from car_price_cache.json
(the cache written by the June 2026 Stage 1 run) plus any extra series in extra_prices.json.
Same return convention as historical_prices.download_prices: (series, ticker_used)."""
from __future__ import annotations
import json, os
import pandas as pd

_CACHE_PATH = os.environ.get("PRICE_CACHE_SOURCE", "car_price_cache.json")
_EXTRA_PATH = os.environ.get("EXTRA_PRICES", "")
_SERIES: dict[str, pd.Series] = {}
LOG: list[tuple] = []

def _load():
    if _SERIES:
        return
    raw = json.load(open(_CACHE_PATH))
    if _EXTRA_PATH and os.path.exists(_EXTRA_PATH):
        raw.update(json.load(open(_EXTRA_PATH)))
    by_ticker: dict[str, dict] = {}
    for key, prices in raw.items():
        if not prices:
            continue
        t = key.split("|")[0]
        by_ticker.setdefault(t, {}).update(prices)
    for t, prices in by_ticker.items():
        s = pd.Series(list(prices.values()), index=pd.to_datetime(list(prices.keys()))).sort_index()
        _SERIES[t] = s[~s.index.duplicated()]

def download_prices(tickers, start, end, *, fmp_api_key=None):
    _load()
    for t in [t for t in tickers if t]:
        s = _SERIES.get(t)
        if s is None:
            LOG.append((t, start, end, "absent"))
            continue
        w = s[(s.index >= pd.Timestamp(start)) & (s.index < pd.Timestamp(end))]   # yfinance: end exclusive
        if len(w) >= 5:
            LOG.append((t, start, end, "ok"))
            return w, t
        LOG.append((t, start, end, "too few"))
    return pd.Series(dtype=float), None
