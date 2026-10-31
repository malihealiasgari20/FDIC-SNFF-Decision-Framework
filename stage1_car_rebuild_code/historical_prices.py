"""Historical price download with yfinance and optional FMP fallback. (Unchanged in the 2026-10 revision.)"""

from __future__ import annotations

import os
import time

import pandas as pd
import requests
import yfinance as yf

REQUEST_DELAY = 0.15


def download_prices_yfinance(ticker: str, start: str, end: str) -> pd.Series:
    data = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if data.empty:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
        if not hist.empty:
            data = hist
    if data.empty:
        return pd.Series(dtype=float)
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"][ticker] if ticker in data["Close"].columns else data["Close"].iloc[:, 0]
    else:
        close = data["Close"]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.dropna().sort_index()


def download_prices_fmp(ticker: str, start: str, end: str, api_key: str) -> pd.Series:
    url = (
        "https://financialmodelingprep.com/api/v3/historical-price-full/"
        f"{ticker}?from={start}&to={end}&apikey={api_key}"
    )
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        return pd.Series(dtype=float)
    payload = resp.json()
    rows = payload.get("historical") or []
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    series = pd.Series(df["adjClose"].astype(float).values, index=df["date"])
    series.index = series.index.tz_localize(None)
    return series


def download_prices(
    tickers: list[str],
    start: str,
    end: str,
    *,
    fmp_api_key: str | None = None,
) -> tuple[pd.Series, str | None]:
    """Try tickers in order; return (prices, ticker_used)."""
    tickers = [t for t in tickers if t]
    for ticker in tickers:
        series = download_prices_yfinance(ticker, start, end)
        if len(series) >= 5:
            return series, ticker
        time.sleep(REQUEST_DELAY)

    key = fmp_api_key or os.environ.get("FMP_API_KEY")
    if key:
        for ticker in tickers:
            series = download_prices_fmp(ticker, start, end, key)
            if len(series) >= 5:
                return series, ticker
            time.sleep(REQUEST_DELAY)

    return pd.Series(dtype=float), None
