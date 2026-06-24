"""Metric primitives.

Pure functions over a periodic-returns Series `r` (DatetimeIndex preferred).
No internal package imports, no scipy: PSR uses math.erf so the core depends
only on numpy + pandas. All functions are deterministic (bootstrap is seeded).
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

SQRT2 = math.sqrt(2.0)


# --------------------------------------------------------------------------- #
# basic performance / risk
# --------------------------------------------------------------------------- #
def equity_curve(r: pd.Series) -> pd.Series:
    """Rebased equity curve including the initial capital point at 1.0."""
    arr = np.asarray(r, dtype=float)
    vals = np.concatenate([[1.0], np.cumprod(1.0 + arr)])
    idx = getattr(r, "index", None)
    if isinstance(idx, pd.DatetimeIndex) and len(idx):
        if len(idx) > 1:
            step = idx[1] - idx[0]
            first = idx[0] - step if step != pd.Timedelta(0) else idx[0]
        else:
            first = idx[0]
        out_idx = idx.insert(0, first)
    else:
        out_idx = pd.RangeIndex(0, len(vals))
    return pd.Series(vals, index=out_idx, name="equity")


def cagr(r: pd.Series, ppy: float) -> float:
    arr = np.asarray(r, dtype=float)
    n = len(arr)
    if n == 0 or ppy <= 0:
        return 0.0
    growth = float(np.prod(1.0 + arr))
    if growth <= 0:
        return -1.0
    years = n / ppy
    if years <= 0:
        return 0.0
    return growth ** (1.0 / years) - 1.0


def sharpe(r: pd.Series, ppy: float) -> float:
    """Annualized Sharpe (rf=0)."""
    arr = np.asarray(r, dtype=float)
    if len(arr) < 2:
        return 0.0
    sd = np.std(arr, ddof=1)
    if sd < 1e-12:
        return 0.0
    return float(arr.mean() / sd * math.sqrt(ppy))


def sortino(r: pd.Series, ppy: float) -> float:
    arr = np.asarray(r, dtype=float)
    if len(arr) < 2:
        return 0.0
    downside = np.minimum(arr, 0.0)
    dd = math.sqrt(float(np.mean(downside ** 2)))
    if dd == 0:
        # no downside in sample: Sortino is infinite, not zero — returning 0
        # contradicted Sharpe on the same series (a curve with no losing bars
        # gets flagged by plausibility anyway)
        return float("inf") if arr.mean() > 0 else 0.0
    return float(arr.mean() / dd * math.sqrt(ppy))


def max_drawdown(eq: pd.Series) -> float:
    """Most-negative drawdown of an equity curve (<= 0)."""
    arr = np.asarray(eq, dtype=float)
    if len(arr) == 0:
        return 0.0
    peak = np.maximum.accumulate(arr)
    dd = arr / peak - 1.0
    return float(dd.min())


def calmar(r: pd.Series, ppy: float) -> float:
    """CAGR / |MDD|. Returns 0.0 when there is no drawdown (lab convention)."""
    # Value-only MDD: avoids building the discarded DatetimeIndex of equity_curve
    # on the per-iteration random-control loops. Bit-identical to
    # max_drawdown(equity_curve(r)).
    arr = np.asarray(r, dtype=float)
    if len(arr) == 0:
        mdd = 0.0
    else:
        eq = np.concatenate([[1.0], np.cumprod(1.0 + arr)])
        peak = np.maximum.accumulate(eq)
        mdd = float((eq / peak - 1.0).min())
    if mdd >= 0:
        return 0.0
    return cagr(r, ppy) / abs(mdd)


def win_rate(r: pd.Series) -> float:
    arr = np.asarray(r, dtype=float)
    if len(arr) == 0:
        return 0.0
    return float((arr > 0).mean())


def profit_factor(r: pd.Series) -> float:
    arr = np.asarray(r, dtype=float)
    gains = arr[arr > 0].sum()
    losses = -arr[arr < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def cvar(r: pd.Series, q: float = 0.05) -> float:
    """Mean of the worst q-tail of returns (typically negative)."""
    arr = np.sort(np.asarray(r, dtype=float))
    if len(arr) == 0:
        return 0.0
    k = max(1, int(math.floor(q * len(arr))))
    return float(arr[:k].mean())


# --------------------------------------------------------------------------- #
# significance / robustness primitives (A & B fixes)
# --------------------------------------------------------------------------- #
def sharpe_and_se(r: pd.Series):
    """Per-period Sharpe and its standard error (Lo 2002 iid approximation)."""
    arr = np.asarray(r, dtype=float)
    n = len(arr)
    if n < 2:
        return 0.0, float("inf")
    sd = np.std(arr, ddof=1)
    if not np.isfinite(sd) or sd < 1e-12:
        # degenerate dispersion: a 1e-19 float-noise std turns the mean into a
        # |Sharpe| ~ 1e15 and poisons every z-test downstream — abstain instead
        return 0.0, float("inf")
    sr = float(arr.mean() / sd)
    se = math.sqrt((1.0 + 0.5 * sr * sr) / n)
    return sr, se


def block_pos_frac(r: pd.Series, k_min: int = 4, k_max: int = 12) -> float:
    """Fraction of K equal-length time blocks that are net profitable.

    Count-based, so it stays meaningful on small samples where Sharpe ratios are
    pure noise.
    """
    arr = np.asarray(r, dtype=float)
    if len(arr) == 0:
        return 0.0
    k = int(min(k_max, max(k_min, len(arr) // 30)))
    k = min(k, len(arr))
    blocks = np.array_split(arr, k)
    return float(np.mean([b.sum() > 0 for b in blocks]))


def return_autocorr(r: pd.Series, lag: int = 1) -> float:
    """Lag-l autocorrelation; NaN-safe (returns 0.0 if undefined)."""
    s = pd.Series(np.asarray(r, dtype=float))
    sd = s.std(ddof=1)
    if len(s) <= lag + 2 or not np.isfinite(sd) or sd < 1e-12:
        return 0.0
    ac = s.autocorr(lag=lag)
    return float(ac) if ac == ac else 0.0  # NaN guard


def top_contributor_recurrence(r: pd.Series) -> dict:
    """Does the edge recur across many calendar buckets (robust convexity) or
    sit in a single window (fragile, one-off)?

    Buckets PnL (additive proxy) by year/quarter/month depending on span.
    """
    if not isinstance(r.index, pd.DatetimeIndex):
        return dict(recurrence=1.0, top_block_share=0.0, n_blocks=1, freq="-")
    dt = r.index
    span_years = max((dt[-1] - dt[0]).days / 365.25, 1e-9)
    freq = "Y" if span_years >= 3 else "Q" if span_years >= 1 else "M"
    pnl = r.groupby(pd.Grouper(freq=freq)).sum()
    pos = pnl.clip(lower=0)
    total = float(pos.sum())
    if total <= 0 or len(pnl) == 0:
        return dict(recurrence=0.0, top_block_share=1.0, n_blocks=int(len(pnl)), freq=freq)
    shares = pos / total
    return dict(
        recurrence=float((shares > 0.05).mean()),
        top_block_share=float(shares.max()),
        n_blocks=int(len(pnl)),
        freq=freq,
    )


def drop_top_k_keep(r: pd.Series, k: int) -> float:
    """Fraction of total growth that survives removing the k largest returns."""
    arr = np.sort(np.asarray(r, dtype=float))[::-1]  # descending
    if len(arr) <= k:
        return 0.0
    full = float(np.prod(1.0 + arr))
    dropped = float(np.prod(1.0 + arr[k:]))
    if full <= 1.0:  # no net gain to begin with
        return 1.0 if dropped >= full else 0.0
    return float(min(max((dropped - 1.0) / (full - 1.0), 0.0), 1.0))


# --------------------------------------------------------------------------- #
# statistical confidence primitives
# --------------------------------------------------------------------------- #
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def _moment_skew_kurt(arr: np.ndarray):
    """Population (biased) skewness and NON-excess kurtosis (normal == 3)."""
    m = arr.mean()
    d = arr - m
    m2 = float(np.mean(d ** 2))
    if m2 == 0:
        return 0.0, 3.0
    m3 = float(np.mean(d ** 3))
    m4 = float(np.mean(d ** 4))
    skew = m3 / (m2 ** 1.5)
    kurt = m4 / (m2 ** 2)
    return skew, kurt


def psr(r: pd.Series, sr_star: float = 0.0, clip_positive_skew: bool = False) -> float:
    """Probabilistic Sharpe Ratio: P(true Sharpe > sr_star) given this sample,
    adjusting for skew, (non-excess) kurtosis and sample length.
    Bailey & Lopez de Prado (2012). Returns a probability in [0, 1] (NaN if
    undefined).

    clip_positive_skew: when True, positive skewness is clamped to 0 in the
    denominator. Rationale: in the formula the -skew*SR term means POSITIVE skew
    (one huge winner) *inflates* apparent significance — exactly the wrong signal
    for an overfitting-aware score. Clamping neutralizes that while still letting
    NEGATIVE skew (fat left tail) deflate PSR as it should.
    """
    arr = np.asarray(r, dtype=float)
    n = len(arr)
    if n < 3:
        return float("nan")
    sd = np.std(arr, ddof=1)
    if not np.isfinite(sd) or sd < 1e-12:
        # degenerate dispersion (a ~1e-19 float-noise std) would blow SR up to ~1e15
        return float("nan")
    sr = float(arr.mean() / sd)  # per-period Sharpe
    skew, kurt = _moment_skew_kurt(arr)
    if clip_positive_skew:
        skew = min(skew, 0.0)
    denom_sq = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr
    denom = math.sqrt(denom_sq) if denom_sq > 1e-12 else 1e-6
    z = (sr - sr_star) * math.sqrt(n - 1) / denom
    return _norm_cdf(z)


_EULER_GAMMA = 0.5772156649015329


def _norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation, ~1e-9
    relative error) — keeps the no-scipy rule."""
    if not 0.0 < p < 1.0:
        return float("nan")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return ((((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
                / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0))
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -((((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
                 / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0))
    q = p - 0.5
    s = q * q
    return ((((((a[0] * s + a[1]) * s + a[2]) * s + a[3]) * s + a[4]) * s + a[5]) * q
            / (((((b[0] * s + b[1]) * s + b[2]) * s + b[3]) * s + b[4]) * s + 1.0))


def dsr_stats(r: pd.Series, clip_positive_skew: bool = True) -> Optional[dict]:
    """Precompute the per-period moments the DSR needs, so the trial-budget
    search can re-evaluate DSR(N) in O(1) per N."""
    arr = np.asarray(r, dtype=float)
    n = len(arr)
    if n < 3:
        return None
    sd = float(np.std(arr, ddof=1))
    if not np.isfinite(sd) or sd < 1e-12:
        # degenerate dispersion: abstain instead of emitting a ~1e15 Sharpe / DSR
        return None
    sr = float(arr.mean() / sd)
    skew, kurt = _moment_skew_kurt(arr)
    if clip_positive_skew:
        skew = min(skew, 0.0)  # same rationale as psr(): one huge winner must not inflate significance
    denom_sq = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr
    denom = math.sqrt(denom_sq) if denom_sq > 1e-12 else 1e-6
    # squared standard error of the per-period Sharpe — the default proxy for how
    # sibling trials' Sharpes scatter when the caller can't supply Var[SR_trials]
    se2 = (denom * denom) / (n - 1)
    return dict(sr=sr, n=n, denom=denom, se2=se2)


def dsr_from_stats(st: dict, n_trials: int, var_trials: Optional[float] = None) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014): PSR measured
    against SR* = the expected MAX per-period Sharpe of n_trials zero-skill
    siblings. n_trials <= 1 collapses to plain PSR vs 0."""
    n_trials = max(int(n_trials), 1)
    if n_trials <= 1:
        sr_star = 0.0
    else:
        v = st["se2"] if var_trials is None else max(float(var_trials), 0.0)
        sr_star = math.sqrt(v) * ((1.0 - _EULER_GAMMA) * _norm_ppf(1.0 - 1.0 / n_trials)
                                  + _EULER_GAMMA * _norm_ppf(1.0 - 1.0 / (n_trials * math.e)))
    z = (st["sr"] - sr_star) * math.sqrt(st["n"] - 1) / st["denom"]
    return _norm_cdf(z)


TRIAL_BUDGET_MAX = 1_000_000


def trial_budget_from_stats(st: dict, confidence: float = 0.95) -> int:
    """Largest number of search trials at which the DSR still clears
    `confidence` — "your Sharpe survives ~N trials of deflation". 0 means it
    fails even as a single, untried strategy. Capped at TRIAL_BUDGET_MAX."""
    if dsr_from_stats(st, 1) < confidence:
        return 0
    lo, hi = 1, 2
    while hi <= TRIAL_BUDGET_MAX and dsr_from_stats(st, hi) >= confidence:
        lo, hi = hi, hi * 2
    if hi > TRIAL_BUDGET_MAX:
        return TRIAL_BUDGET_MAX
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if dsr_from_stats(st, mid) >= confidence:
            lo = mid
        else:
            hi = mid
    return lo


def growth_concentration(r: pd.Series):
    """How concentrated is the profit across observations?

    Returns (effective_n, top1_share) from a Herfindahl index of each
    observation's POSITIVE contribution to log-growth. If one trade dominates,
    effective_n -> 1 (the track record effectively rests on a single bet); if
    growth is spread evenly, effective_n -> number of winners.
    """
    arr = np.asarray(r, dtype=float)
    g = np.clip(np.log1p(np.clip(arr, -0.999999, None)), 0.0, None)  # positive log-growth
    tot = float(g.sum())
    if tot <= 0:
        return 1.0, 1.0
    shares = g / tot
    hhi = float((shares ** 2).sum())
    eff_n = 1.0 / hhi if hhi > 0 else float(len(arr))
    return eff_n, float(shares.max())


def benchmark_compare(strat_returns: pd.Series, asset_close: pd.Series,
                      min_overlap_days: float = 20.0):
    """Strategy vs buy-and-hold of the asset, measured over the OVERLAPPING window
    of the two series (both sides measured on the same [start, end]).

    Robust to:
      * different timeframes — a 1d asset works against a 2h strategy; each series
        keeps its own bars, we only need the asset's closes inside the overlap.
      * mismatched / partial date ranges — we use the intersection, not an exact match.
      * timezone mismatch — trade-log dates are often tz-aware while a price CSV is
        naive; both are coerced to tz-naive before comparing.

    Returns None only if there is no real overlap (< min_overlap_days or too few
    points). Comparison is risk-adjusted (Calmar alpha + drawdown reduction);
    raw return capture is reported as context.
    """
    if not isinstance(strat_returns.index, pd.DatetimeIndex):
        return None
    if not isinstance(asset_close.index, pd.DatetimeIndex):
        return None
    sr, ac = strat_returns.copy(), asset_close.copy()
    if getattr(sr.index, "tz", None) is not None:
        sr.index = sr.index.tz_localize(None)
    if getattr(ac.index, "tz", None) is not None:
        ac.index = ac.index.tz_localize(None)
    sr = sr.sort_index()
    if sr.index.has_duplicates:
        sr = sr.groupby(level=0).apply(lambda x: float((1.0 + x).prod() - 1.0))
    ac = ac[~ac.index.duplicated(keep="last")].sort_index()

    lo, hi = max(sr.index[0], ac.index[0]), min(sr.index[-1], ac.index[-1])
    if hi <= lo:
        return None
    overlap_days = (hi - lo).total_seconds() / 86400.0
    sr_w = sr[(sr.index >= lo) & (sr.index <= hi)]
    ac_w = ac[(ac.index >= lo) & (ac.index <= hi)]
    if len(sr_w) < 3 or len(ac_w) < 2 or overlap_days < min_overlap_days:
        return None
    yrs = max(overlap_days / 365.25, 1e-9)

    def _stats(eq):
        eq = np.asarray(eq, dtype=float)
        total = float(eq[-1] / eq[0] - 1.0)
        cagr = float((eq[-1] / eq[0]) ** (1.0 / yrs) - 1.0) if eq[-1] > 0 else -1.0
        dd = float((eq / np.maximum.accumulate(eq) - 1.0).min())
        cal = cagr / abs(dd) if dd < 0 else 0.0
        return dict(total=total, cagr=cagr, mdd=dd, calmar=cal)

    s_eq = equity_curve(sr_w)
    s, b = _stats(s_eq.to_numpy()), _stats(ac_w.to_numpy())
    full_days = (sr.index[-1] - sr.index[0]).total_seconds() / 86400.0
    return dict(
        years=yrs, window_start=str(lo)[:10], window_end=str(hi)[:10],
        overlap_days=round(overlap_days, 1), partial=bool(overlap_days < 0.95 * full_days),
        strat=s, bnh=b, cal_alpha=s["calmar"] - b["calmar"],
        ret_capture=(s["total"] / b["total"]) if b["total"] not in (0.0,) else float("nan"),
        dd_reduction=((abs(b["mdd"]) - abs(s["mdd"])) / abs(b["mdd"])) if b["mdd"] < 0 else 0.0,
        strat_curve=s_eq / float(s_eq.iloc[0]),
        bnh_curve=ac_w / float(ac_w.iloc[0]),
    )


def monte_carlo(r: pd.Series, ppy: float, n_sims: int = 2000,
                block: Optional[int] = None, seed: int = 12345):
    """Monte Carlo on the strategy's OWN returns via moving-block bootstrap.

    Resamples the return series many times (blocks preserve short-run
    dependence) and reports the DISTRIBUTION of outcomes instead of the single
    realised path. Deterministic (seeded). Returns None if too few points.

    keys: n_sims, final_p{5,50,95} (equity multiple), cagr_p{5,50,95},
          maxdd_p50, maxdd_worst5 (5th pctile = bad tail), prob_loss,
          band_lo/band_mid/band_hi (per-step 5/50/95% equity envelope).
    """
    arr = np.asarray(r, dtype=float)
    n = len(arr)
    if n < 10 or ppy <= 0:
        return None
    n_sims = int(min(n_sims, max(300, 4_000_000 // n)))      # cap memory
    if block is None:
        block = max(1, int(round(math.sqrt(n))))
    block = min(block, n)
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(n_sims, n_blocks))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(n_sims, -1)[:, :n]
    sims = arr[idx]                                          # (n_sims, n)
    eq = np.cumprod(1.0 + sims, axis=1)
    eq = np.concatenate([np.ones((n_sims, 1)), eq], axis=1)
    final = eq[:, -1]
    span_years = n / ppy
    cagr = np.where(final > 0, final ** (1.0 / span_years) - 1.0, -1.0)
    peak = np.maximum.accumulate(eq, axis=1)
    dd = np.divide(eq, peak, out=np.zeros_like(eq), where=peak > 0) - 1.0
    maxdd = dd.min(axis=1)

    def _p(a, q):
        return float(np.percentile(a, q))

    return dict(
        n_sims=n_sims,
        final_p5=_p(final, 5), final_p50=_p(final, 50), final_p95=_p(final, 95),
        cagr_p5=_p(cagr, 5), cagr_p50=_p(cagr, 50), cagr_p95=_p(cagr, 95),
        maxdd_p50=_p(maxdd, 50), maxdd_worst5=_p(maxdd, 5),
        prob_loss=float((final < 1.0).mean()),
        band_lo=np.percentile(eq, 5, axis=0),
        band_mid=np.percentile(eq, 50, axis=0),
        band_hi=np.percentile(eq, 95, axis=0),
    )


def block_bootstrap_p5(
    r: pd.Series, ppy: float, B: int = 1000, block: Optional[int] = None, seed: int = 12345
) -> float:
    """5th percentile of annualized return under a moving-block bootstrap.

    Block bootstrap preserves short-run serial dependence. Seeded => the score
    is reproducible for a given CSV.
    """
    arr = np.asarray(r, dtype=float)
    n = len(arr)
    if n < 10 or ppy <= 0:
        return float("nan")
    if block is None:
        block = max(1, int(round(math.sqrt(n))))
    block = min(block, n)
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n / block))
    span_years = n / ppy
    out = np.empty(B)
    offs = np.arange(block)
    for b in range(B):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        idx = (starts[:, None] + offs[None, :]).ravel()[:n]
        growth = float(np.prod(1.0 + arr[idx]))
        out[b] = growth ** (1.0 / span_years) - 1.0 if growth > 0 else -1.0
    return float(np.percentile(out, 5))
