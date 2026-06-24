"""Asset recognition: given a strategy's returns (and optionally its filename),
figure out WHICH bundled asset it most likely traded — so the 'skill vs luck'
dimension (benchmark + random control) runs against the right asset.

Two signals, combined:
  1. filename  — parse a ticker out of the file name (BTC7H.csv, dogeusdt_trades.csv,
                 aapl_swing.csv). High precision when present.
  2. correlation fingerprint — a long/short-biased strategy tracks its underlying,
                 so the asset whose daily returns correlate most with the strategy's
                 (over the overlapping window) is the likely target.

Reliability lock: detection NEVER auto-commits silently. It returns a best guess
+ ranked alternatives + a confidence label + the evidence (corr, overlap), so the
UI can ask for a one-click confirm. If nothing correlates, it says so (low/none)
and the user picks from the list or uploads their own K-line — it does not force a
wrong match (matching a SOL strategy to ETH would silently corrupt the verdict).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from . import assets as _assets

MIN_OVERLAP = 60           # min overlapping daily points to trust a correlation
_PAIR_SUFFIX = ("USDT", "USDC", "BUSD", "PERP", "USD", "USDTPERP", "PERPUSDT")
_TF_RE = re.compile(r"^(?P<base>[A-Z0-9]+?)(?:\d+(?:MIN|MINS|MIN|M|H|D|W))$")
# build alias -> key map (longest aliases first so BTCUSDT beats BTC)
_ALIAS_TO_KEY = {}
for _asset in _assets.ASSETS:
    for _tok in (_asset.key, *_asset.aliases):
        _ALIAS_TO_KEY.setdefault(_tok.upper(), _asset.key)


@dataclass
class AssetMatch:
    key: str
    name: str
    asset_class: str
    corr: float = float("nan")     # signed daily-return correlation (NaN if unknown)
    overlap: int = 0               # overlapping daily points
    via: str = "correlation"       # "filename" | "correlation" | "filename+corr"

    @property
    def abscorr(self) -> float:
        return abs(self.corr) if self.corr == self.corr else 0.0


@dataclass
class Detection:
    best: Optional[AssetMatch]
    alternatives: List[AssetMatch] = field(default_factory=list)
    confidence: str = "none"          # high | medium | low | none
    needs_confirmation: bool = True
    reason: str = ""
    filename_key: Optional[str] = None

    def to_dict(self) -> dict:
        def _m(m):
            return None if m is None else dict(
                key=m.key, name=m.name, asset_class=m.asset_class,
                corr=(round(m.corr, 3) if m.corr == m.corr else None),
                overlap=m.overlap, via=m.via)
        return dict(confidence=self.confidence, needs_confirmation=self.needs_confirmation,
                    reason=self.reason, filename_key=self.filename_key,
                    best=_m(self.best), alternatives=[_m(m) for m in self.alternatives])


# --------------------------------------------------------------------------- #
# filename parsing
# --------------------------------------------------------------------------- #
def _strip_suffixes(tok: str) -> List[str]:
    """Yield candidate symbols from one filename token: the token itself, the
    token minus a trailing pair-suffix (DOGEUSDT->DOGE), and minus a trailing
    timeframe (BTC1D->BTC)."""
    out = [tok]
    for suf in sorted(_PAIR_SUFFIX, key=len, reverse=True):
        if tok.endswith(suf) and len(tok) > len(suf):
            out.append(tok[: -len(suf)])
            break
    m = _TF_RE.match(tok)
    if m:
        base = m.group("base")
        out.append(base)
        for suf in sorted(_PAIR_SUFFIX, key=len, reverse=True):
            if base.endswith(suf) and len(base) > len(suf):
                out.append(base[: -len(suf)])
                break
    return out


def key_from_filename(filename: Optional[str]) -> Optional[str]:
    """Best-effort asset key from a filename, or None. Uses delimiter/suffix-aware
    EXACT token matching (not substring) so 'options.csv' does not match OP."""
    if not filename:
        return None
    stem = re.split(r"[\\/]", str(filename))[-1]
    stem = re.sub(r"\.(csv|txt|tsv|json)$", "", stem, flags=re.IGNORECASE)
    raw = [t for t in re.split(r"[^A-Za-z0-9]+", stem.upper()) if t]
    hits: List[str] = []
    for tok in raw:
        for cand in _strip_suffixes(tok):
            if cand in _ALIAS_TO_KEY:
                k = _ALIAS_TO_KEY[cand]
                if k not in hits:
                    hits.append(k)
                break
    # one unambiguous hit is usable; multiple distinct hits -> let correlation decide
    return hits[0] if len(hits) == 1 else None


# --------------------------------------------------------------------------- #
# correlation fingerprint
# --------------------------------------------------------------------------- #
def _to_daily_returns(r: pd.Series) -> Optional[pd.Series]:
    if not isinstance(r.index, pd.DatetimeIndex) or len(r) < 3:
        return None
    idx = r.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    s = pd.Series(np.asarray(r, dtype=float), index=idx)
    days = s.index.normalize()
    # compound intraday returns within each calendar day; daily/coarser passes through
    daily = s.groupby(days).apply(lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0))
    daily.index = pd.DatetimeIndex(daily.index)
    return daily


def _corr_rank(strat_daily: pd.Series, keys: List[str]) -> List[AssetMatch]:
    matches: List[AssetMatch] = []
    for k in keys:
        ar = _assets.daily_returns(k)
        if ar is None:
            continue
        if getattr(ar.index, "tz", None) is not None:
            ar.index = ar.index.tz_localize(None)
        j = pd.concat([strat_daily, ar], axis=1, join="inner").dropna()
        if len(j) < MIN_OVERLAP:
            continue
        a = j.iloc[:, 0].to_numpy()
        b = j.iloc[:, 1].to_numpy()
        if np.std(a) == 0 or np.std(b) == 0:
            continue
        c = float(np.corrcoef(a, b)[0, 1])
        asset = _assets.ASSET_BY_KEY[k]
        matches.append(AssetMatch(k, asset.name, asset.asset_class, corr=c, overlap=int(len(j))))
    matches.sort(key=lambda m: m.abscorr, reverse=True)
    return matches


# --------------------------------------------------------------------------- #
# main entry
# --------------------------------------------------------------------------- #
def detect_asset(returns: pd.Series, filename: Optional[str] = None, *,
                 symbol: Optional[str] = None, max_alternatives: int = 4) -> Detection:
    """Identify the most likely traded asset. Strongest signal first: an explicit
    `symbol` carried in the upload (the user labeled their own data) > filename >
    return correlation. Always returns a confidence label and asks for confirmation
    (never silent)."""
    keys = _assets.available_keys()
    fname_key = key_from_filename(filename)
    if fname_key is not None and fname_key not in keys:
        fname_key = None  # named asset isn't downloaded; treat as no filename hit
    # the data's own symbol column is authoritative — reuse the filename tokenizer
    # (handles BTC, BTCUSDT, BTC/USDT, BTC-1d). Only trust it if the asset exists.
    sym_key = key_from_filename(symbol) if symbol else None
    if sym_key is not None and sym_key not in keys:
        sym_key = None

    strat_daily = _to_daily_returns(returns)
    ranked = _corr_rank(strat_daily, keys) if strat_daily is not None else []
    by_key = {m.key: m for m in ranked}

    # --- explicit symbol column wins: the upload says what it traded. Correlation
    # cannot confirm a sparse low-frequency trade log, but the declared symbol is the
    # user's own label — resolve it directly (still overridable in the UI). ---
    if sym_key is not None:
        fm = by_key.get(sym_key)
        a = _assets.ASSET_BY_KEY[sym_key]
        if fm is not None and fm.abscorr >= 0.30:
            best = AssetMatch(fm.key, fm.name, fm.asset_class, fm.corr, fm.overlap, via="symbol+corr")
            reason = (f"the file's symbol column says {sym_key} and it correlates "
                      f"{fm.corr:+.2f} — strong agreement.")
        elif fname_key == sym_key:
            best = AssetMatch(a.key, a.name, a.asset_class, via="symbol+filename")
            reason = f"both the file's symbol column and the filename say {sym_key}."
        else:
            best = AssetMatch(a.key, a.name, a.asset_class, via="symbol")
            reason = (f"the file's symbol column says {sym_key} — using it as the traded "
                      "asset (change it if that is wrong).")
        alts = [m for m in ranked if m.key != sym_key][:max_alternatives]
        return Detection(best=best, alternatives=alts, confidence="high",
                         needs_confirmation=True, reason=reason, filename_key=fname_key)

    if not ranked and fname_key is None:
        return Detection(best=None, confidence="none", needs_confirmation=True,
                         reason="no asset correlates with this strategy and the filename "
                                "has no recognizable ticker — pick the asset or upload its K-line.")

    top = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    margin = (top.abscorr - second.abscorr) if (top and second) else (top.abscorr if top else 0.0)

    # --- decide best + confidence ---------------------------------------
    if fname_key is not None:
        fm = by_key.get(fname_key)
        if fm is not None and fm.abscorr >= 0.30:
            best = AssetMatch(fm.key, fm.name, fm.asset_class, fm.corr, fm.overlap, via="filename+corr")
            conf = "high"
            reason = (f"filename says {fm.key} and it correlates {fm.corr:+.2f} "
                      f"over {fm.overlap} days — strong agreement.")
        elif fm is not None:
            best = AssetMatch(fm.key, fm.name, fm.asset_class, fm.corr, fm.overlap, via="filename")
            conf = "medium"
            reason = (f"filename says {fm.key}, but its correlation is only {fm.corr:+.2f}. "
                      "Confirm, or the strategy may trade a different asset than its name.")
        else:
            a = _assets.ASSET_BY_KEY[fname_key]
            best = AssetMatch(a.key, a.name, a.asset_class, via="filename")
            conf = "medium" if strat_daily is None else "low"
            reason = (f"filename says {fname_key}; not enough overlap to confirm by correlation. "
                      "Confirm or pick another.")
    else:
        best = AssetMatch(top.key, top.name, top.asset_class, top.corr, top.overlap, via="correlation")
        if top.abscorr >= 0.60 and margin >= 0.10:
            conf = "high"
            reason = (f"correlates {top.corr:+.2f} with {top.key} over {top.overlap} days, "
                      f"clearly above the next best ({margin:+.2f} margin).")
        elif top.abscorr >= 0.40:
            conf = "medium"
            reason = (f"most correlated with {top.key} ({top.corr:+.2f}), but {top.key} moves with "
                      "several assets — confirm which one you traded.")
        elif top.abscorr >= 0.25:
            conf = "low"
            reason = (f"weak correlation (best is {top.key} {top.corr:+.2f}); could be a different "
                      "asset, a market-neutral strategy, or noise. Confirm or upload K-line.")
        else:
            return Detection(best=None, alternatives=ranked[:max_alternatives], confidence="none",
                             reason="nothing correlates clearly — pick the asset or upload its K-line.")

    alts = [m for m in ranked if m.key != best.key][:max_alternatives]
    return Detection(best=best, alternatives=alts, confidence=conf,
                     needs_confirmation=True, reason=reason, filename_key=fname_key)


def asset_close(key: str) -> Optional[pd.Series]:
    """Daily close Series for a confirmed asset key (for benchmark_compare)."""
    return _assets.load_close(key)
