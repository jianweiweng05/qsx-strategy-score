"""Bundled asset library: daily OHLC for mainstream assets, used ONLY to
power the 'skill vs luck' dimension (benchmark + random-control) of the scorer.

Two free, no-account, no-apikey sources:
  * crypto            -> Binance public klines  (api.binance.com/api/v3/klines)
  * US equities/ETFs  -> Yahoo v8 chart         (query1/query2.finance.yahoo.com)
  * futures/indices   -> Yahoo (^GSPC, GC=F, ...)

Yahoo's chart endpoint is undocumented and can reject unauthenticated requests
with 401/403 or a `chart.error` JSON body. Refresh errors are surfaced in the
asset manifest so users can distinguish upstream blocking from real missing data.

The data is pulled with the stdlib only (urllib + json) — NOT yfinance, which is
fragile and currently broken in this env. Pulls are incremental: a refresh only
fetches bars newer than what is already on disk.

Data location (never committed to git):
    $QSX_SCORE_DATA_DIR  or  ~/.qsx_score/assets/
        BTC.csv  ETH.csv  ...  (date,open,high,low,close,volume)
        manifest.json        (per-asset rows/start/end/source + last_refreshed)

This module is the data layer only. Asset *recognition* (filename + correlation
fingerprint) lives in asset_library.py.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) qsx-score/0.1"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
YAHOO_CHART_FALLBACK = "https://query2.finance.yahoo.com/v8/finance/chart/{sym}"
_CRYPTO_FLOOR_MS = 1_388_534_400_000  # 2014-01-01: don't ask Binance before this


# --------------------------------------------------------------------------- #
# manifest of assets
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Asset:
    key: str            # canonical short name + on-disk filename stem (e.g. "BTC")
    name: str           # human label
    asset_class: str    # crypto | equity | etf | index | commodity | fx
    source: str         # "binance" | "yahoo"
    symbol: str         # source ticker (BTCUSDT, AAPL, ^GSPC, GC=F)
    profile: str        # scoring profile (crypto|altcoin|stock_index|other)
    aliases: tuple = ()  # extra tokens for filename recognition


def _a(key, name, asset_class, source, symbol, profile, aliases=()):
    return Asset(key, name, asset_class, source, symbol, profile, tuple(aliases))


# Liquid mainstream assets covering the bulk of retail / semi-pro backtests.
# Some public sources may be unavailable in a given region — refresh() skips
# failures gracefully and preserves existing local files.
ASSETS: List[Asset] = [
    # --- crypto majors (Binance) -----------------------------------------
    _a("BTC", "Bitcoin", "crypto", "binance", "BTCUSDT", "crypto",
       ("XBT", "BTCUSD", "BTCUSDT", "BTCPERP", "BTCUSDTPERP", "XBTUSD")),
    _a("ETH", "Ethereum", "crypto", "binance", "ETHUSDT", "crypto",
       ("ETHUSD", "ETHUSDT", "ETHPERP")),
    _a("SOL", "Solana", "crypto", "binance", "SOLUSDT", "altcoin", ("SOLUSD", "SOLUSDT")),
    _a("BNB", "BNB", "crypto", "binance", "BNBUSDT", "altcoin", ("BNBUSD", "BNBUSDT")),
    _a("XRP", "XRP", "crypto", "binance", "XRPUSDT", "altcoin", ("XRPUSD", "XRPUSDT")),
    _a("DOGE", "Dogecoin", "crypto", "binance", "DOGEUSDT", "altcoin", ("DOGEUSD", "DOGEUSDT")),
    _a("ADA", "Cardano", "crypto", "binance", "ADAUSDT", "altcoin", ("ADAUSD", "ADAUSDT")),
    _a("AVAX", "Avalanche", "crypto", "binance", "AVAXUSDT", "altcoin", ("AVAXUSD", "AVAXUSDT")),
    _a("LINK", "Chainlink", "crypto", "binance", "LINKUSDT", "altcoin", ("LINKUSD", "LINKUSDT")),
    _a("DOT", "Polkadot", "crypto", "binance", "DOTUSDT", "altcoin", ("DOTUSD", "DOTUSDT")),
    _a("LTC", "Litecoin", "crypto", "binance", "LTCUSDT", "altcoin", ("LTCUSD", "LTCUSDT")),
    _a("TRX", "TRON", "crypto", "binance", "TRXUSDT", "altcoin", ("TRXUSD", "TRXUSDT")),
    _a("BCH", "Bitcoin Cash", "crypto", "binance", "BCHUSDT", "altcoin", ("BCHUSD", "BCHUSDT")),
    _a("XLM", "Stellar", "crypto", "binance", "XLMUSDT", "altcoin", ("XLMUSD", "XLMUSDT")),
    _a("ATOM", "Cosmos", "crypto", "binance", "ATOMUSDT", "altcoin", ("ATOMUSD", "ATOMUSDT")),
    _a("UNI", "Uniswap", "crypto", "binance", "UNIUSDT", "altcoin", ("UNIUSD", "UNIUSDT")),
    _a("NEAR", "NEAR", "crypto", "binance", "NEARUSDT", "altcoin", ("NEARUSD", "NEARUSDT")),
    _a("APT", "Aptos", "crypto", "binance", "APTUSDT", "altcoin", ("APTUSD", "APTUSDT")),
    _a("ARB", "Arbitrum", "crypto", "binance", "ARBUSDT", "altcoin", ("ARBUSD", "ARBUSDT")),
    _a("OP", "Optimism", "crypto", "binance", "OPUSDT", "altcoin", ("OPUSD", "OPUSDT")),
    _a("INJ", "Injective", "crypto", "binance", "INJUSDT", "altcoin", ("INJUSD", "INJUSDT")),
    _a("SUI", "Sui", "crypto", "binance", "SUIUSDT", "altcoin", ("SUIUSD", "SUIUSDT")),
    _a("ETC", "Ethereum Classic", "crypto", "binance", "ETCUSDT", "altcoin", ("ETCUSD", "ETCUSDT")),
    # --- US broad ETFs (Yahoo) --------------------------------------------
    _a("SPY", "S&P 500 ETF", "etf", "yahoo", "SPY", "stock_index", ("ES",)),
    _a("QQQ", "Nasdaq 100 ETF", "etf", "yahoo", "QQQ", "stock_index", ("NQ",)),
    _a("IWM", "Russell 2000 ETF", "etf", "yahoo", "IWM", "stock_index", ("RUT", "RTY")),
    _a("DIA", "Dow Jones ETF", "etf", "yahoo", "DIA", "stock_index", ("DJI", "YM")),
    # --- US mega-cap single stocks (Yahoo) --------------------------------
    _a("AAPL", "Apple", "equity", "yahoo", "AAPL", "other"),
    _a("MSFT", "Microsoft", "equity", "yahoo", "MSFT", "other"),
    _a("NVDA", "NVIDIA", "equity", "yahoo", "NVDA", "other"),
    _a("TSLA", "Tesla", "equity", "yahoo", "TSLA", "other"),
    _a("AMZN", "Amazon", "equity", "yahoo", "AMZN", "other"),
    _a("META", "Meta", "equity", "yahoo", "META", "other", ("FB",)),
    _a("GOOGL", "Alphabet", "equity", "yahoo", "GOOGL", "other", ("GOOG",)),
    _a("AMD", "AMD", "equity", "yahoo", "AMD", "other"),
    _a("NFLX", "Netflix", "equity", "yahoo", "NFLX", "other"),
    # --- indices (Yahoo, deep history) ------------------------------------
    _a("SPX", "S&P 500 Index", "index", "yahoo", "^GSPC", "stock_index", ("GSPC", "SPXUSD")),
    _a("NDX", "Nasdaq 100 Index", "index", "yahoo", "^NDX", "stock_index", ("GNDX",)),
    # --- commodities / futures (Yahoo) ------------------------------------
    _a("GC", "Gold", "commodity", "yahoo", "GC=F", "other", ("GOLD", "XAU", "XAUUSD", "GCUSD")),
    _a("SI", "Silver", "commodity", "yahoo", "SI=F", "other", ("SILVER", "XAG", "XAGUSD", "SIUSD")),
    _a("CL", "Crude Oil", "commodity", "yahoo", "CL=F", "other", ("WTI", "OIL", "USO", "CLUSD")),
    _a("HG", "Copper", "commodity", "yahoo", "HG=F", "other", ("COPPER",)),
    _a("NG", "Natural Gas", "commodity", "yahoo", "NG=F", "other", ("NATGAS",)),
    # --- fx / dollar ------------------------------------------------------
    _a("DXY", "US Dollar Index", "fx", "yahoo", "DX-Y.NYB", "other", ("DXY", "USDX", "DX")),
    _a("EURUSD", "EUR/USD", "fx", "yahoo", "EURUSD=X", "other", ("EURUSD", "EUR/USD", "EUR")),
    _a("USDJPY", "USD/JPY", "fx", "yahoo", "JPY=X", "other", ("USDJPY", "USD/JPY", "JPY")),
    _a("GBPUSD", "GBP/USD", "fx", "yahoo", "GBPUSD=X", "other", ("GBPUSD", "GBP/USD", "GBP")),
    _a("AUDUSD", "AUD/USD", "fx", "yahoo", "AUDUSD=X", "other", ("AUDUSD", "AUD/USD", "AUD")),
    # --- US sector ETFs --------------------------------------------------
    _a("XLF", "Financial Select Sector SPDR", "etf", "yahoo", "XLF", "stock_index", ("FINANCIALS",)),
    _a("XLK", "Technology Select Sector SPDR", "etf", "yahoo", "XLK", "stock_index", ("TECH", "TECHNOLOGY")),
    _a("XLE", "Energy Select Sector SPDR", "etf", "yahoo", "XLE", "stock_index", ("ENERGY",)),
    _a("XLV", "Health Care Select Sector SPDR", "etf", "yahoo", "XLV", "stock_index", ("HEALTHCARE",)),
    _a("XLI", "Industrial Select Sector SPDR", "etf", "yahoo", "XLI", "stock_index", ("INDUSTRIALS",)),
    _a("XLY", "Consumer Discretionary Select Sector SPDR", "etf", "yahoo", "XLY", "stock_index",
       ("DISCRETIONARY", "CONSUMERDISCRETIONARY")),
    _a("XLP", "Consumer Staples Select Sector SPDR", "etf", "yahoo", "XLP", "stock_index",
       ("STAPLES", "CONSUMERSTAPLES")),
    _a("XLU", "Utilities Select Sector SPDR", "etf", "yahoo", "XLU", "stock_index", ("UTILITIES",)),
    _a("XLB", "Materials Select Sector SPDR", "etf", "yahoo", "XLB", "stock_index", ("MATERIALS",)),
    _a("XLRE", "Real Estate Select Sector SPDR", "etf", "yahoo", "XLRE", "stock_index", ("REALESTATE",)),
    _a("XLC", "Communication Services Select Sector SPDR", "etf", "yahoo", "XLC", "stock_index",
       ("COMMUNICATIONS", "COMMUNICATIONSERVICES")),
    # --- international / bonds --------------------------------------------
    _a("CSI300", "China A-share ETF", "etf", "yahoo", "ASHR", "stock_index",
       ("HS300", "ASHR", "000300", "SHSE300")),
    _a("HSI", "Hang Seng Index", "index", "yahoo", "^HSI", "stock_index", ("HANGSENG", "HK50")),
    _a("EFA", "MSCI EAFE ETF", "etf", "yahoo", "EFA", "stock_index", ("DEVELOPEDMARKETS", "EAFA")),
    _a("EEM", "MSCI Emerging Markets ETF", "etf", "yahoo", "EEM", "stock_index",
       ("EMERGINGMARKETS", "EM")),
    _a("ACWI", "MSCI ACWI ETF", "etf", "yahoo", "ACWI", "stock_index", ("GLOBAL", "WORLD")),
    _a("VT", "Vanguard Total World Stock ETF", "etf", "yahoo", "VT", "stock_index", ("TOTALWORLD",)),
    _a("TLT", "US 20Y+ Treasury ETF", "etf", "yahoo", "TLT", "other", ("BONDS", "UST20")),
    _a("IEF", "US 7-10Y Treasury ETF", "etf", "yahoo", "IEF", "other", ("UST10", "TREASURY10")),
    _a("SHY", "US 1-3Y Treasury ETF", "etf", "yahoo", "SHY", "other", ("UST2", "TREASURY2")),
    _a("BIL", "US 1-3M Treasury Bill ETF", "etf", "yahoo", "BIL", "other", ("TBILL", "CASH")),
    _a("TIP", "US TIPS ETF", "etf", "yahoo", "TIP", "other", ("TIPS", "INFLATIONBONDS")),
    _a("AGG", "US Aggregate Bond ETF", "etf", "yahoo", "AGG", "other", ("COREBOND",)),
    _a("BND", "Vanguard Total Bond Market ETF", "etf", "yahoo", "BND", "other", ("TOTALBOND",)),
    _a("LQD", "Investment Grade Corporate Bond ETF", "etf", "yahoo", "LQD", "other",
       ("IGCREDIT", "CORPBOND")),
    _a("HYG", "High Yield Corporate Bond ETF", "etf", "yahoo", "HYG", "other",
       ("HIGYIELD", "JUNKBOND")),
]

ASSET_BY_KEY: Dict[str, Asset] = {a.key: a for a in ASSETS}


# --------------------------------------------------------------------------- #
# data directory
# --------------------------------------------------------------------------- #
def data_dir() -> Path:
    """Resolve the on-disk asset directory (env override, else ~/.qsx_score/assets).
    Created on demand. Never inside the git repo."""
    env = os.environ.get("QSX_SCORE_DATA_DIR")
    p = Path(env).expanduser() if env else (Path.home() / ".qsx_score" / "assets")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _asset_path(key: str) -> Path:
    return data_dir() / f"{key}.csv"


def _manifest_path() -> Path:
    return data_dir() / "manifest.json"


# --------------------------------------------------------------------------- #
# HTTP (stdlib only)
# --------------------------------------------------------------------------- #
def _http_json(url: str, timeout: float = 25.0, retries: int = 2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": _UA,
                    "Accept": "application/json,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:  # noqa: BLE001
                body = ""
            last = f"HTTP {e.code} {e.reason or ''}".strip()
            if body:
                last = f"{last}: {body}"
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"request failed ({last}): {url}")


def _now_ms() -> int:
    return int(time.time() * 1000)


# --------------------------------------------------------------------------- #
# source fetchers -> tidy OHLCV DataFrame indexed by normalized date
# --------------------------------------------------------------------------- #
def _empty_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume"],
                        index=pd.DatetimeIndex([], name="date"))


def fetch_binance(symbol: str, start_ms: int) -> pd.DataFrame:
    rows = []
    cur = max(int(start_ms), _CRYPTO_FLOOR_MS)
    now = _now_ms()
    while cur < now:
        url = f"{BINANCE_KLINES}?symbol={symbol}&interval=1d&startTime={cur}&limit=1000"
        data = _http_json(url)
        if not isinstance(data, list) or not data:
            break
        rows.extend(data)
        if len(data) < 1000:
            break
        cur = int(data[-1][6]) + 1  # next ms after last closeTime
    if not rows:
        return _empty_ohlcv()
    arr = np.array([[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows], dtype=float)
    idx = pd.to_datetime(arr[:, 0].astype("int64"), unit="ms").normalize()
    df = pd.DataFrame({"open": arr[:, 1], "high": arr[:, 2], "low": arr[:, 3],
                       "close": arr[:, 4], "volume": arr[:, 5]}, index=idx)
    df.index.name = "date"
    return df


def _yahoo_chart_result(payload: dict, symbol: str, host: str) -> list:
    chart = (payload.get("chart") or {}) if isinstance(payload, dict) else {}
    err = chart.get("error")
    if err:
        code = err.get("code") or "error"
        desc = err.get("description") or err.get("message") or "no description"
        raise RuntimeError(f"Yahoo chart error for {symbol} via {host}: {code}: {desc}")
    if chart.get("result") is None:
        raise RuntimeError(
            f"Yahoo chart returned no result for {symbol} via {host}; "
            "Yahoo may be blocking unauthenticated chart requests or requiring a fresh cookie/crumb."
        )
    return chart.get("result") or []


def fetch_yahoo(symbol: str, start_s: int) -> pd.DataFrame:
    sym = urllib.parse.quote(symbol, safe="")
    p1 = max(int(start_s), 0)
    errors = []
    res = []
    for template in (YAHOO_CHART, YAHOO_CHART_FALLBACK):
        host = urllib.parse.urlparse(template).netloc
        url = (template.format(sym=sym)
               + f"?period1={p1}&period2={int(time.time())}&interval=1d")
        try:
            j = _http_json(url)
            res = _yahoo_chart_result(j, symbol, host)
            break
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
    else:
        joined = " | ".join(errors)
        raise RuntimeError(f"Yahoo chart fetch failed for {symbol}: {joined}")
    if not res:
        return _empty_ohlcv()
    res = res[0]
    ts = res.get("timestamp") or []
    quote = (((res.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    if not ts or "close" not in quote:
        return _empty_ohlcv()
    idx = pd.to_datetime(np.asarray(ts, dtype="int64"), unit="s").normalize()
    df = pd.DataFrame({
        "open": quote.get("open"), "high": quote.get("high"), "low": quote.get("low"),
        "close": quote.get("close"), "volume": quote.get("volume"),
    }, index=idx)
    df.index.name = "date"
    df = df[pd.to_numeric(df["close"], errors="coerce").notna()]
    return df.astype(float)


def _fetch(asset: Asset, start_epoch_s: int) -> pd.DataFrame:
    if asset.source == "binance":
        return fetch_binance(asset.symbol, int(start_epoch_s) * 1000)
    if asset.source == "yahoo":
        return fetch_yahoo(asset.symbol, int(start_epoch_s))
    raise ValueError(f"unknown source {asset.source!r}")


# --------------------------------------------------------------------------- #
# load / save
# --------------------------------------------------------------------------- #
def _read_local(key: str) -> Optional[pd.DataFrame]:
    p = _asset_path(key)
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    return df[~df.index.duplicated(keep="last")]


def _write_local(key: str, df: pd.DataFrame) -> None:
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.to_csv(_asset_path(key), index=True)


def refresh_asset(asset: Asset, *, full: bool = False) -> dict:
    """Incrementally update one asset; returns a status dict. On any failure the
    existing local data is preserved and the error is reported (never raised)."""
    try:
        existing = None if full else _read_local(asset.key)
        if existing is not None and len(existing):
            # re-fetch from the last stored day (dedupe handles the overlap)
            start_s = int(existing.index[-1].timestamp())
        else:
            start_s = 0
        fresh = _fetch(asset, start_s)
        if existing is not None and len(existing):
            merged = pd.concat([existing, fresh])
        else:
            merged = fresh
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        merged = merged[pd.to_numeric(merged["close"], errors="coerce").fillna(0) > 0]
        if not len(merged):
            return dict(key=asset.key, ok=False, error="no data returned", rows=0)
        _write_local(asset.key, merged)
        return dict(key=asset.key, ok=True, rows=int(len(merged)),
                    start=str(merged.index[0].date()), end=str(merged.index[-1].date()),
                    source=asset.source, added=int(len(merged) - (len(existing) if existing is not None else 0)))
    except Exception as e:  # noqa: BLE001
        return dict(key=asset.key, ok=False, error=str(e), rows=0, source=asset.source)


def refresh(keys: Optional[List[str]] = None, *, full: bool = False,
            verbose: bool = True) -> dict:
    """Refresh the whole library (or a subset of keys). Writes manifest.json."""
    targets = [ASSET_BY_KEY[k] for k in keys] if keys else ASSETS
    results = []
    for asset in targets:
        r = refresh_asset(asset, full=full)
        results.append(r)
        if verbose:
            if r["ok"]:
                print(f"  ok   {asset.key:6s} {r['rows']:5d} rows  "
                      f"{r.get('start')}..{r.get('end')}  (+{r.get('added', 0)})")
            else:
                print(f"  FAIL {asset.key:6s} {r.get('error')}")
    ok = [r for r in results if r["ok"]]
    manifest = dict(
        last_refreshed=time.strftime("%Y-%m-%dT%H:%M:%S"),
        n_ok=len(ok), n_fail=len(results) - len(ok),
        assets={r["key"]: {k: r[k] for k in ("rows", "start", "end", "source") if k in r}
                for r in ok},
        failed={r["key"]: r.get("error") for r in results if not r["ok"]},
    )
    _manifest_path().write_text(json.dumps(manifest, indent=2))
    if verbose:
        print(f"\n{len(ok)}/{len(results)} assets ok -> {data_dir()}")
        if manifest["failed"]:
            print(f"failed: {', '.join(manifest['failed'])}")
    return manifest


# --------------------------------------------------------------------------- #
# public accessors (used by asset_library + scorer)
# --------------------------------------------------------------------------- #
def available_keys() -> List[str]:
    """Asset keys that currently have data on disk."""
    return sorted(a.key for a in ASSETS if _asset_path(a.key).exists())


def load_close(key: str) -> Optional[pd.Series]:
    """Daily close Series for `key`, or None if not downloaded."""
    df = _read_local(key)
    if df is None or not len(df):
        return None
    s = pd.to_numeric(df["close"], errors="coerce").dropna()
    s.name = key
    return s


def daily_returns(key: str) -> Optional[pd.Series]:
    s = load_close(key)
    if s is None or len(s) < 2:
        return None
    return s.pct_change().dropna()


def load_manifest() -> dict:
    p = _manifest_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Refresh the qsx-score asset library.")
    ap.add_argument("--full", action="store_true", help="re-download full history (ignore local)")
    ap.add_argument("--keys", nargs="*", help="only these asset keys (default: all)")
    args = ap.parse_args()
    print(f"data dir: {data_dir()}")
    refresh(keys=args.keys, full=args.full)
