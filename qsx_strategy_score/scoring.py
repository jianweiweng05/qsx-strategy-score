"""Scoring layer.

Collapses a returns Series into the unified QSX scorecard: three displayed
0-100 pillars, a 0-100 overall on a public grade scale, and a
GOLD/SILVER/BRONZE tier (or NEEDS WORK / FLAGGED). This is the project's IP.

score_unified() is the single live entry point. The displayed pillars are:
    Return quality   0.35   pure efficiency (Sharpe / Sortino)
    Credibility      0.40   robustness + consistency + plausibility
    Drawdown risk    0.25   drawdown, recovery, tail
Edge (vs buy & hold + vs random timing) is the protagonist: it drives the
headline and an edge light, and losing to hold / not beating random WITHHOLDS
the tier rather than adding points. Sample size / statistical significance is a
VETO (caps the score and withholds the tier), not an averaged pillar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import List, Optional

import numpy as np
import pandas as pd

from . import metrics
from .io import SECONDS_PER_YEAR
from .profiles import get_profile, ANCHORS_SOURCE, VALIDATED

T_SPLIT_MIN = 150  # min observations before a train/holdout split is trustworthy

_FLAG_MSG = {
    "INSUFFICIENT_FOR_SPLIT": "sample too short (<150) for a reliable train/holdout split — "
                              "Consistency ABSTAINS (excluded from the score, not assumed good)",
    "OVERFIT_SUSPECT_HOLDOUT": "holdout-period Sharpe is significantly worse than train — possible overfit",
    "ONE_OFF_EDGE": "most of the edge comes from a single time window and does not recur across the sample",
    "TOO_GOOD_TO_BE_TRUE": "results look too clean to be real — verify for look-ahead / "
                           "interpolation / unrealistic fills before trusting the score",
    "EDGE_FROM_FEW_TRADES": "most of the profit comes from a handful of trades (low effective "
                            "sample) — the track record is fragile",
    "UNDERPERFORMS_HOLD_RISKADJ": "lower Calmar than simply buying & holding the asset over this window",
    "OOS_NEGATIVE_RETURN": "holdout / OOS segment is not profitable",
    "RANDOM_CONTROL_NOT_BEATEN": "strategy does not clearly beat random long/flat exposure on the same asset",
    "MULTIPLE_TESTING_PENALTY": "score was penalized for parameter/search trials",
    "BACKGROUND_REQUIRED": "return scale is unusually large — verify starting capital, leverage, venue fills, capacity and whether this was selected from many variants",
    "FORWARD_LOOKING_INPUT": "input name or columns explicitly suggest future/leaky/look-ahead data — verify the backtest before trusting the score",
    "RETURN_UNIT_SUSPECT": "return units look unusually large — verify percent vs decimal input before trusting the score",
}


@dataclass
class SubScore:
    value: Optional[float]            # None == abstained (excluded from the overall)
    raw: dict
    flags: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# normalization helpers
# --------------------------------------------------------------------------- #
def sat(x: float, x50: float) -> float:
    """Saturating map [0, inf) -> [0, 1); == 0.5 at x == x50. Negatives clip to 0."""
    x = float(x)
    if math.isnan(x):
        return 0.0
    if math.isinf(x):
        return 1.0 if x > 0 else 0.0  # inf/(inf+x50) is nan, not the limit
    x = max(x, 0.0)
    return x / (x + x50) if x50 > 0 else 0.0


def lin(x: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    return min(max((float(x) - lo) / (hi - lo), 0.0), 1.0)


def _json_safe(o):
    """Make a value strictly JSON-serializable: numpy scalars -> python,
    non-finite floats (NaN/inf) -> None. Keeps --json output valid JSON."""
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    return o


# --------------------------------------------------------------------------- #
# sub-scores
# --------------------------------------------------------------------------- #
def _robustness(r: pd.Series, A: dict) -> SubScore:
    rec = metrics.top_contributor_recurrence(r)
    tol = A.get("conc_tolerance", 0.45)
    oneoff_pen = min(max((rec["top_block_share"] - tol) / (1.0 - tol), 0.0), 1.0)
    recurrence_score = min(rec["recurrence"] * 1.5, 1.0) * (1.0 - 0.5 * oneoff_pen)
    k = max(3, int(round(0.05 * len(r))))
    keep = metrics.drop_top_k_keep(r, k)
    keep_adj = keep if oneoff_pen > 0 else 1.0  # convex+recurring edge not punished by drop-k
    flags = []
    if rec["top_block_share"] > 0.6 and rec["recurrence"] < 0.25:
        flags.append("ONE_OFF_EDGE")
    v = 100.0 * (0.65 * recurrence_score + 0.35 * keep_adj)
    raw = dict(rec)
    raw.update(keep_after_drop=keep, drop_k=k)
    return SubScore(v, raw, flags)


def _consistency(r: pd.Series, T_split_min: int = T_SPLIT_MIN) -> SubScore:
    T = len(r)
    base = metrics.block_pos_frac(r)
    if T < T_split_min:
        # ABSTAIN: too few observations for a trustworthy train/holdout split.
        # value=None -> excluded from the overall (NOT scored as a confident 100).
        return SubScore(None, dict(block_pos_frac=base, T=T, split=False, abstained=True),
                        ["INSUFFICIENT_FOR_SPLIT"])
    cut = int(0.7 * T)
    sr_tr, se_tr = metrics.sharpe_and_se(r.iloc[:cut])
    sr_ho, se_ho = metrics.sharpe_and_se(r.iloc[cut:])
    se_diff = math.hypot(se_tr, se_ho)
    z = (sr_tr - sr_ho) / se_diff if se_diff > 0 else 0.0
    flags = []
    if sr_ho < 0 and z > 1.64:                       # significant decay AND holdout loses money
        flags.append("OVERFIT_SUSPECT_HOLDOUT")
        degr = max(0.0, 1.0 - (z - 1.64) / 3.0)
    elif z > 1.64:                                   # decays but holdout still positive
        degr = max(0.5, 1.0 - (z - 1.64) / 6.0)
    else:
        degr = 1.0
    v = 100.0 * (0.5 * base + 0.5 * degr)
    return SubScore(v, dict(block_pos_frac=base, sr_train=sr_tr, sr_holdout=sr_ho,
                            z=z, split=True), flags)


def _smoothness_flags(r: pd.Series, eq: pd.Series, ppy: float, A: dict,
                      is_trade_log: bool = False) -> list:
    out = []
    # The autocorrelation/stale check is a BAR-LEVEL-EQUITY artifact detector
    # (interpolated / stale marks). On a trade log, serial correlation between
    # consecutive trades is legitimate (winning/losing streaks in a trend), so
    # skip it there — the closed-trade caveat already covers intra-trade risk.
    if not is_trade_log:
        ac1 = metrics.return_autocorr(r, 1)
        if ac1 > 0.30:
            out.append(("STALE_OR_INTERPOLATED",
                        f"lag-1 return autocorr {ac1:.2f}: equity may be interpolated or stale-marked"))
    shp = metrics.sharpe(r, ppy)
    if shp > A.get("sharpe_absurd", 6.0):
        out.append(("SHARPE_TOO_GOOD",
                    f"annualized Sharpe {shp:.1f} is implausibly high for this asset class"))
    mdd = metrics.max_drawdown(eq)
    posf = metrics.win_rate(r)
    if posf > 0.90 and abs(mdd) < 0.03:
        out.append(("NEAR_MONOTONIC",
                    f"{posf:.0%} of periods positive with only {mdd:.1%} drawdown: suspiciously smooth"))
    return out


def _stat_conf(r: pd.Series, ppy: float, A: dict) -> SubScore:
    # PSR with positive-skew clamped: one huge winner must NOT inflate significance.
    p = metrics.psr(r, clip_positive_skew=True)
    bp5 = metrics.block_bootstrap_p5(r, ppy)
    eff_n, top1 = metrics.growth_concentration(r)
    p_score = p if p == p else 0.5
    if bp5 != bp5:
        bp5_score = 0.5
    elif bp5 > 0:
        bp5_score = 1.0
    else:
        bp5_score = lin(bp5, -0.20, 0.0)
    # counterweight: if profit rests on a few trades, effective_n is small -> low credit.
    conc_score = lin(eff_n, 3.0, 20.0)
    n = len(r)
    adeq = lin(n, A["n_min"], A["n_min"] * 4)
    v = 100.0 * (0.40 * p_score + 0.25 * bp5_score + 0.20 * conc_score + 0.15 * adeq)
    flags = ["EDGE_FROM_FEW_TRADES"] if eff_n < 5.0 else []   # the too-good brake lives in score_unified()
    return SubScore(v, dict(psr=p, bootstrap_p5=bp5, effective_n=round(eff_n, 1),
                            top1_share=round(top1, 3), n=n), flags)


def _plausibility(too_good: list, background: Optional[list] = None) -> SubScore:
    """Credibility / data-integrity brake.

    This is deliberately separate from Statistical Confidence: a huge, smooth
    backtest can be statistically significant while still being suspect because
    the *data generating process* may contain look-ahead, survivorship, leverage,
    stale marks, tiny-capacity mania trades, or other issues statistics alone
    cannot validate.
    """
    n = len(too_good)
    b = len(background or [])
    v = 99.0 if n == 0 else max(5.0, 100.0 - 35.0 * n)
    return SubScore(v, dict(red_flag_count=n, codes=[c for c, _ in too_good],
                            background_check_count=b,
                            background_codes=[c for c, _ in (background or [])]),
                    ["TOO_GOOD_TO_BE_TRUE"] if n else [])


def _implausible_flags(r: pd.Series, eq: pd.Series, span_years: float,
                       calmar: float, cagr: float) -> list:
    """Magnitude-based feasibility checks.

    These are NOT data-integrity flags by themselves. A meme-coin/event strategy
    can legitimately print huge returns on small capital; the correct response is
    to ask for capital/leverage/fill/capacity background, not to call the series
    leaking. Smoothness/pathology checks remain the hard integrity screen.
    """
    out = []
    total_mult = float(eq.iloc[-1]) if len(eq) else 1.0
    max_month = 0.0
    if isinstance(r.index, pd.DatetimeIndex):
        try:
            m = (1.0 + r).resample("M").prod() - 1.0
            if len(m):
                max_month = float(m.max())
        except Exception:  # noqa: BLE001
            pass
    if span_years >= 1.5 and cagr > 1.0:
        out.append(("BACKGROUND_CAGR",
                    f"CAGR {cagr*100:.0f}%/yr sustained over {span_years:.1f}y — verify starting capital, leverage, venue fills, capacity and whether this was selected from many variants"))
    if calmar > 10.0:
        out.append(("BACKGROUND_CALMAR",
                    f"Calmar {calmar:.0f} (>10) — verify mark-to-market drawdowns, leverage and fill assumptions before treating it as scalable"))
    if total_mult > 50.0:
        out.append(("BACKGROUND_GROWTH",
                    f"equity grew {total_mult:,.0f}x over the sample — verify capital base, leverage, venue liquidity and survivorship"))
    if max_month > 1.0:
        out.append(("BACKGROUND_EXTREME_MONTH",
                    f"a single month returned +{max_month*100:.0f}% — treat scalability as unverified until capital size and liquidity are known"))
    return out


def _risk(r: pd.Series, ppy: float, A: dict) -> SubScore:
    eq = metrics.equity_curve(r)
    mdd = metrics.max_drawdown(eq)
    total = float(eq.iloc[-1] - 1.0)
    rec = total / abs(mdd) if mdd < 0 else 0.0
    cv = metrics.cvar(r, 0.05)
    v = 100.0 * (0.5 * (1.0 - sat(abs(mdd), A["mdd50"]))
                 + 0.3 * sat(rec, A["rec50"])
                 + 0.2 * (1.0 - sat(abs(cv), A["cvar50"])))
    return SubScore(v, dict(mdd=mdd, recovery=rec, cvar5=cv, total_return=total), [])


def _benchmark(cmp: dict) -> SubScore:
    """Score 'did it beat buy-and-hold?' on a RISK-ADJUSTED basis: 60% Calmar
    alpha (strat - BnH), 40% drawdown reduction. 50 = matched holding."""
    ca = cmp["cal_alpha"]
    score_cal = 0.5 + 0.5 * math.tanh(ca / 2.0)            # 0 -> .50, +2 -> .88, -2 -> .12
    ddr = max(min(cmp["dd_reduction"], 1.0), -1.0)
    dd_term = 0.5 + 0.5 * ddr                              # avoided all DD -> 1, same -> .5
    v = 100.0 * (0.6 * score_cal + 0.4 * dd_term)
    flags = ["UNDERPERFORMS_HOLD_RISKADJ"] if cmp["strat"]["calmar"] < cmp["bnh"]["calmar"] else []
    return SubScore(v, dict(cal_alpha=ca, ret_capture=cmp["ret_capture"],
                            dd_reduction=cmp["dd_reduction"],
                            strat_calmar=cmp["strat"]["calmar"], bnh_calmar=cmp["bnh"]["calmar"],
                            strat_cagr=cmp["strat"]["cagr"], bnh_cagr=cmp["bnh"]["cagr"],
                            strat_mdd=cmp["strat"]["mdd"], bnh_mdd=cmp["bnh"]["mdd"]), flags)


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def _resolve_ppy(r: pd.Series, ppy: Optional[float], meta: dict) -> float:
    if ppy is not None:
        return float(ppy)
    if meta.get("ppy"):
        return float(meta["ppy"])
    if isinstance(r.index, pd.DatetimeIndex) and len(r) > 1:
        span = (r.index[-1] - r.index[0]).total_seconds() / SECONDS_PER_YEAR
        if span > 0:
            return len(r) / span
    return 252.0


def _append_flag(flags: List[dict], code: str, msg: Optional[str] = None,
                 severity: str = "warn", **extra) -> None:
    if any(f.get("code") == code for f in flags):
        return
    item = dict(code=code, msg=msg or _FLAG_MSG.get(code, code), severity=severity)
    item.update(extra)
    flags.append(item)


def _oos_gate(r: pd.Series, ppy: float) -> Optional[dict]:
    # 264 is the smallest n where the 70/30 split clears train>=120 AND oos>=80;
    # the old `< 240` guard implied the gate ran from 240, but n in [240, 263]
    # was silently skipped by the inner check below.
    if len(r) < 264:
        return None
    cut = int(0.70 * len(r))
    train, oos = r.iloc[:cut], r.iloc[cut:]
    if len(train) < 120 or len(oos) < 80:
        return None
    train_cal = metrics.calmar(train, ppy)
    oos_cal = metrics.calmar(oos, ppy)
    oos_cagr = metrics.cagr(oos, ppy)
    oos_sharpe = metrics.sharpe(oos, ppy)
    oos_mdd = metrics.max_drawdown(metrics.equity_curve(oos))
    ratio = (oos_cal / train_cal) if train_cal > 0 else float("nan")
    return dict(train_calmar=train_cal, oos_calmar=oos_cal, oos_cagr=oos_cagr,
                oos_sharpe=oos_sharpe, oos_mdd=oos_mdd, oos_train_ratio=ratio,
                train_n=len(train), oos_n=len(oos))


def _random_control_gate(benchmark: dict, *, meta: Optional[dict] = None,
                         sims: int = 128, seed: int = 12345,
                         cost_bps: float = 2.0) -> Optional[dict]:
    if not benchmark or benchmark.get("strat_curve") is None or benchmark.get("bnh_curve") is None:
        return None
    meta = dict(meta or {})
    try:
        event_rc = _event_random_control_gate(benchmark, meta=meta, sims=sims, seed=seed)
    except Exception:  # noqa: BLE001 - random control is optional evidence
        event_rc = None
    if event_rc is not None:
        return event_rc
    try:
        s_eq = pd.Series(benchmark["strat_curve"]).astype(float)
        b_eq = pd.Series(benchmark["bnh_curve"]).astype(float)
        joined = pd.concat([s_eq.pct_change(), b_eq.pct_change()], axis=1, join="inner").dropna()
        if len(joined) < 120:
            return None
        joined.columns = ["strat", "asset"]
        sr, ar = joined["strat"], joined["asset"]
        var = float(np.var(ar.to_numpy(), ddof=1))
        if var <= 0:
            return None
        beta = float(np.cov(sr.to_numpy(), ar.to_numpy(), ddof=1)[0, 1] / var)
        exposure = float(min(max(abs(beta), 0.15), 1.0))
        ppy = _resolve_ppy(ar, None, {})
        strat_cal = metrics.calmar(sr, ppy)
        rng = np.random.default_rng(seed)
        vals = ar.to_numpy(dtype=float)
        sims = int(max(32, min(sims, 512)))
        rand_cal = np.empty(sims)
        for i in range(sims):
            pos = rng.binomial(1, exposure, size=len(vals)).astype(float)
            traded = np.abs(np.diff(np.r_[0.0, pos]))
            rr = np.r_[0.0, pos[:-1]] * vals - traded * (cost_bps / 10000.0)
            rs = pd.Series(rr, index=ar.index)
            rand_cal[i] = metrics.calmar(rs, ppy)
        finite = np.isfinite(rand_cal)
        if not finite.any():
            return None
        rand_cal = rand_cal[finite]
        p_value = float((rand_cal >= strat_cal).mean())
    except Exception:  # noqa: BLE001 - degrade to unavailable instead of failing scoring
        return None
    return dict(
        exposure=exposure,
        strat_calmar=float(strat_cal),
        random_calmar_p50=float(np.percentile(rand_cal, 50)),
        random_calmar_p75=float(np.percentile(rand_cal, 75)),
        random_calmar_p95=float(np.percentile(rand_cal, 95)),
        random_p_value=p_value,
        random_sims=int(len(rand_cal)),
        method="bar_long_flat",
    )


def _event_random_control_gate(benchmark: dict, *, meta: dict,
                               sims: int = 128, seed: int = 12345) -> Optional[dict]:
    """Random timing control for closed-trade logs.

    Bar-level random long/flat requires many aligned bar returns. A low-frequency
    trade log may have only dozens of exits, but it still carries entry/exit
    durations. For those files, compare the realised trade sequence to random
    entry windows with the same holding periods on the same asset.
    """
    if meta.get("caliber") != "closed_trade":
        return None
    entries = meta.get("trade_entry_times") or []
    exits = meta.get("trade_exit_times") or []
    if len(entries) < 8 or len(entries) != len(exits):
        return None
    b_eq = pd.Series(benchmark["bnh_curve"]).astype(float)
    if not isinstance(b_eq.index, pd.DatetimeIndex):
        return None
    b_eq = b_eq[~b_eq.index.duplicated(keep="last")].sort_index()
    if len(b_eq) < 30 or float(b_eq.max()) <= 0:
        return None
    entry_idx = pd.to_datetime(pd.Series(entries), errors="coerce")
    exit_idx = pd.to_datetime(pd.Series(exits), errors="coerce")
    valid = entry_idx.notna() & exit_idx.notna() & (exit_idx >= entry_idx)
    if int(valid.sum()) < 8:
        return None
    holding_days = ((exit_idx[valid] - entry_idx[valid]).dt.total_seconds() / 86400.0)
    holding_days = holding_days.to_numpy(dtype=float)
    holding_days = holding_days[np.isfinite(holding_days)]
    if len(holding_days) < 8:
        return None
    asset_dates = pd.DatetimeIndex(b_eq.index)
    asset_ns = asset_dates.asi8
    asset_vals = b_eq.to_numpy(dtype=float)
    if not np.isfinite(asset_vals).all() or np.any(asset_vals <= 0):
        return None

    trade_returns = []
    rng = np.random.default_rng(seed)
    sims = int(max(64, min(sims, 512)))
    n_dates = len(asset_dates)
    for days in holding_days:
        hold_delta = pd.to_timedelta(max(days, 0.0), unit="D")
        latest_start_ns = (asset_dates[-1] - hold_delta).value
        max_start = int(np.searchsorted(
            asset_ns,
            latest_start_ns,
            side="right",
        ))
        max_start = max(1, min(max_start, n_dates - 1))
        starts = rng.integers(0, max_start, size=sims)
        end_targets = asset_dates[starts] + hold_delta
        ends = np.searchsorted(asset_ns, pd.DatetimeIndex(end_targets).asi8, side="left")
        ends = np.clip(ends, starts + 1, n_dates - 1)
        trade_returns.append(asset_vals[ends] / asset_vals[starts] - 1.0)
    rand_trade_matrix = np.vstack(trade_returns).T
    finite_rows = np.isfinite(rand_trade_matrix).all(axis=1)
    rand_trade_matrix = rand_trade_matrix[finite_rows]
    if len(rand_trade_matrix) < 32:
        return None

    actual_curve = pd.Series(benchmark["strat_curve"]).astype(float)
    actual_rets = actual_curve.pct_change().dropna()
    if len(actual_rets) < 3:
        return None
    ppy = float(meta.get("ppy") or len(actual_rets))
    strat_cal = metrics.calmar(actual_rets, ppy)
    rand_cal = np.empty(len(rand_trade_matrix))
    for i, rr in enumerate(rand_trade_matrix):
        rs = pd.Series(rr)
        rand_cal[i] = metrics.calmar(rs, ppy)
    finite = np.isfinite(rand_cal)
    if not finite.any():
        return None
    rand_cal = rand_cal[finite]
    p_value = float((rand_cal >= strat_cal).mean())
    return dict(
        exposure=1.0,
        strat_calmar=float(strat_cal),
        random_calmar_p50=float(np.percentile(rand_cal, 50)),
        random_calmar_p75=float(np.percentile(rand_cal, 75)),
        random_calmar_p95=float(np.percentile(rand_cal, 95)),
        random_p_value=p_value,
        random_sims=int(len(rand_cal)),
        random_events=int(len(holding_days)),
        method="event_window",
    )


# ===================================================================== #
# Unified report (v3): the merged, "4-question" product.
# ===================================================================== #
# One product, no v1/v2 toggle. The headline NUMBER stays rewarding (v1-style),
# but two GATES make it honest:
#
#   * the quality SCORE blends THREE pillars only — return quality, credibility,
#     drawdown risk — with credibility >= return (brand: reward robustness, not
#     flash). Drawdown is removed from the return pillar (Calmar double-counts it
#     with the risk pillar) so each pillar owns exactly one thing.
#   * SAMPLE/significance is a VETO, not an averaged pillar: too few obs / a
#     handful of trades caps the score and WITHHOLDS the tier (small sample =
#     "provisional", never a confident metal).
#   * EDGE (vs buy & hold + vs random timing) is the protagonist, not a 4th tile:
#     it drives the headline + a traffic light, and losing to hold / not beating
#     random WITHHOLDS the tier. Beating both lights the green trophy but adds no
#     points (it would double-count return/robustness). The random-timing test
#     needs an asset; without one the free luck signal comes from PSR/bootstrap.
#
# Tier is EARNED: only a clean OK verdict gets GOLD/SILVER/BRONZE; a tripped hard
# gate shows "未评级 · <reason>" so a metal can never sit next to a red light.
QUALITY_WEIGHTS = dict(return_quality=0.35, credibility=0.40, risk=0.25)
# ONE grade-aligned scale that is BOTH accurate and presentable: each pillar is
# mapped onto a school-grade curve (90s=excellent, 80s=good, 60s=pass, <60=red) and
# the total IS the weighted average of those three DISPLAYED pillars — so the bars
# reconcile with the score AND a good strategy naturally lands in the 80s
# (shareable). The mapping is monotonic, so good > random > reject ordering (the
# accuracy) is preserved. Tier = the band of that number; no hidden sub-gates.
# Gates instead CAP the number visibly (hard gate -> below passing; unproven edge
# can't reach GOLD; too-good is withheld), and the reason is shown.
TIER_GOLD, TIER_SILVER, TIER_BRONZE = 88.0, 80.0, 60.0
TIER_HARD_CAP = 59.0         # any hard gate -> below passing (NEEDS WORK)
TIER_SOFT_CAP = 87.0         # unproven/weak edge -> capped just below GOLD
TIER_FLAGGED_CAP = 59.0      # too-good-to-be-true never shows a passing number
# EXPERIENCE gate (Darwinex-style): GOLD/SILVER are EARNED with history. A lucky
# year can pass every statistical control on a 1y window (a fabricated/noise curve
# with a fortunate drift demonstrably minted a 93.8 GOLD pre-gate), so short or
# trade-concentrated records are capped at the Bronze band — withheld, not failed.
TIER_EXPERIENCE_CAP = 79.0   # short/concentrated track record -> Bronze at best
EXPERIENCE_MIN_YEARS = 2.0   # a metal above Bronze requires >= 2y of history
EXPERIENCE_MIN_EFF_N = 10.0  # ...and profit spread over >= 10 effective trades
EDGE_RANDOM_HARD_P = 0.20    # random-timing p above this = no demonstrable edge
EDGE_RANDOM_SOFT_P = 0.05    # soft..hard band = marginal (yellow)
# vs-hold uses the RISK-ADJUSTED benchmark subscore (60% Calmar alpha + 40% DD
# reduction; 50 == matched hold), NOT raw Calmar alpha — a drawdown-halving trend
# strategy must not be branded "lost" just for trailing a raging-bull Calmar.
EDGE_BENCH_LOST = 40.0       # below this = clearly worse than holding (hard gate)
EDGE_BENCH_MATCH = 50.0      # below this (but >=LOST) = roughly matched -> marginal

# Public display scale. The engine's internal score is calibrated to the corpus
# (good clusters ~55-72); a layperson reads a number like a school grade
# (90s=excellent, 80s=good, 60s=pass, <60=fail). So map internal -> a display
# grade where the TIER cutoffs land on intuitive grade bands, and any non-OK
# verdict renders BELOW 60 — the number can never contradict a red light.
#   internal 70(GOLD) -> 90 (优)   55(SILVER) -> 80 (良)   35(BRONZE) -> 60 (及格)
_DISPLAY_KNOTS_PASS = [(0.0, 40.0), (35.0, 60.0), (55.0, 80.0), (70.0, 90.0), (99.0, 100.0)]
_DISPLAY_KNOTS_FAIL = [(0.0, 0.0), (55.0, 59.0), (99.0, 59.0)]
GRADE_LABEL = {"GOLD": "GOLD", "SILVER": "SILVER", "BRONZE": "BRONZE",
               "CAUTION": "NEEDS WORK", "FLAGGED": "FLAGGED"}


def _lerp_knots(x: float, knots) -> float:
    if x <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x <= x1:
            return y1 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return knots[-1][1]


def to_display_score(internal: float, judgement: str) -> float:
    """Map an internal 0-99 score to the public grade scale (see above)."""
    knots = _DISPLAY_KNOTS_PASS if judgement == "OK" else _DISPLAY_KNOTS_FAIL
    d = _lerp_knots(float(internal), knots)
    if judgement != "OK":
        d = min(d, 59.0)
    return round(min(max(d, 0.0), 99.9), 1)
SAMPLE_MIN_EFF_N = 5.0       # profit must not rest on a handful of trades
PSR_LUCK_FLOOR = 0.90        # no-asset: PSR below this = hard to tell from luck


@dataclass
class UnifiedReport:
    overall: float
    judgement: str                 # OK | CAUTION | FLAGGED
    tier: Optional[str]            # GOLD/SILVER/BRONZE, or None when not earned
    headline: str
    return_quality: SubScore
    credibility: SubScore
    risk: SubScore
    edge: Optional[SubScore]       # vs hold/random; None when no asset supplied
    lights: dict                   # {'sample': ok|thin, 'edge': beat|lost|random_fail|marginal|luck_unclear|not_evaluated}
    flags: List[dict]
    meta: dict
    display: float = 0.0           # public grade-scale score (90s=优, 80s=良, 60s=及格, <60 fail)
    grade: str = ""               # human grade label (优/良/及格/未达标/存疑)

    def subscores(self) -> dict:
        d = {"Return quality": self.return_quality, "Credibility": self.credibility,
             "Drawdown risk": self.risk}
        if self.edge is not None:
            d["Edge vs hold/random"] = self.edge
        return d

    def to_dict(self) -> dict:
        def _v(s):
            return None if (s is None or s.value is None) else round(s.value, 1)
        return _json_safe(dict(
            overall=self.overall, display=self.display, grade=self.grade,
            judgement=self.judgement, tier=self.tier,
            headline=self.headline, lights=self.lights,
            pillars={k: dict(value=_v(s), raw=s.raw) for k, s in self.subscores().items()},
            flags=self.flags, meta=self.meta))


def _return_quality(r: pd.Series, ppy: float, A: dict) -> SubScore:
    """Pure efficiency — Sharpe/Sortino only. NO drawdown term (that lives in the
    risk pillar; Calmar would double-count it)."""
    shp = metrics.sharpe(r, ppy)
    srt = metrics.sortino(r, ppy)
    v = 100.0 * (0.65 * sat(shp, A["sharpe50"]) + 0.35 * sat(srt, A.get("sortino50", 1.4)))
    return SubScore(v, dict(sharpe=shp, sortino=srt), [])


def _credibility(robust: SubScore, cons: SubScore, plausibility: SubScore) -> SubScore:
    """Curve-fit / not-a-fluke: robustness + consistency + plausibility. Sample
    SIZE is deliberately NOT here (it is a gate, not an averageable component)."""
    parts = [(0.45, robust.value), (0.20, plausibility.value)]
    if cons.value is not None:                       # consistency abstains on tiny samples
        parts.append((0.35, cons.value))
    wsum = sum(w for w, _ in parts)
    v = sum(w * val for w, val in parts) / wsum if wsum else 0.0
    return SubScore(v, dict(robustness=robust.value, consistency=cons.value,
                            plausibility=plausibility.value),
                    list(robust.flags) + list(cons.flags))


def score_unified(returns: pd.Series, profile_name: str = "other", *,
                  ppy: Optional[float] = None, meta: Optional[dict] = None,
                  benchmark: Optional[dict] = None, n_trials: int = 1,
                  random_sims: int = 128, random_seed: int = 12345) -> UnifiedReport:
    r = returns.astype(float)
    meta = dict(meta or {})
    A = get_profile(profile_name)
    ppy = _resolve_ppy(r, ppy, meta)
    n = len(r)
    span_years = meta.get("span_years")
    if span_years is None:
        span_years = n / ppy if ppy > 0 else 0.0
    eq = metrics.equity_curve(r)
    cagr_full = metrics.cagr(r, ppy)

    # --- three quality pillars (reuse the engine) ---
    rq = _return_quality(r, ppy, A)
    robust = _robustness(r, A)
    cons = _consistency(r)
    stat_conf = _stat_conf(r, ppy, A)          # used only for the sample/luck GATE
    risk = _risk(r, ppy, A)
    is_tl = meta.get("caliber") == "closed_trade"
    too_good = _smoothness_flags(r, eq, ppy, A, is_trade_log=is_tl)
    background_flags = _implausible_flags(r, eq, span_years, metrics.calmar(r, ppy), cagr_full)
    plausibility = _plausibility(too_good, background_flags)
    if too_good:
        rq = replace(rq, value=min(rq.value, 50.0))
    cred = _credibility(robust, cons, plausibility)
    if too_good:
        # a 'too good to be true' curve is NOT credible — the veto must show on the
        # bar (red), not just in the verdict, so it can't sit at a high credibility.
        cred = replace(cred, value=min(cred.value, 28.0))
    rq = replace(rq, value=min(rq.value, 99.0))
    cred = replace(cred, value=min(cred.value, 99.0))
    risk = replace(risk, value=min(risk.value, 99.0))

    # map each pillar onto the public grade scale, THEN average -> the three bars
    # the user sees reconcile exactly with the total, and "good" lands in the 80s.
    rq = replace(rq, value=to_display_score(rq.value, "OK"))
    cred = replace(cred, value=to_display_score(cred.value, "OK"))
    risk = replace(risk, value=to_display_score(risk.value, "OK"))
    W = QUALITY_WEIGHTS
    overall = (W["return_quality"] * rq.value + W["credibility"] * cred.value
               + W["risk"] * risk.value)

    flags: List[dict] = []
    n_trials = max(int(n_trials or 1), 1)
    if n_trials > 1:
        overall -= min(18.0, 3.0 * math.log10(n_trials))
        _append_flag(flags, "MULTIPLE_TESTING_PENALTY", severity="info", n_trials=n_trials)

    # --- gate signals ---
    eff_n = stat_conf.raw.get("effective_n")
    psr = stat_conf.raw.get("psr")
    boot_p5 = stat_conf.raw.get("bootstrap_p5")
    # Deflated Sharpe (Bailey & Lopez de Prado 2014): discounts the Sharpe for the
    # SELECTION the user did before uploading (self-reported n_trials). trial_budget
    # = "how many search trials this Sharpe survives" — computed regardless, since
    # at n_trials=1 the DSR is just PSR vs 0 and the budget is still informative.
    _dsr_st = metrics.dsr_stats(r)
    dsr = metrics.dsr_from_stats(_dsr_st, n_trials) if _dsr_st else None
    trial_budget = metrics.trial_budget_from_stats(_dsr_st) if _dsr_st else None
    # Low-frequency / event strategies legitimately have FEW trades over a LONG
    # history. Judging them by the daily-bar n_min ("go get >100 observations") is
    # the high-frequency-ruler mistake: a multi-year track with a healthy effective-
    # trade count is not "too small". For a closed-trade log, gate sample adequacy on
    # TIME + effective trades; the raw trade count is the strategy's nature, not a
    # defect. (Free stays a rough read — this only stops the wrong "too few" verdict.)
    trades_per_year = (n / span_years) if span_years > 0 else float(n)
    is_low_frequency = is_tl and (n < 100 or trades_per_year < 50)
    if is_tl:
        sample_hard = (span_years < 1.0) or (eff_n is not None and eff_n < SAMPLE_MIN_EFF_N)
    else:
        sample_hard = (n < A["n_min"]) or (span_years < 1.0) or (eff_n is not None and eff_n < SAMPLE_MIN_EFF_N)
    oos = _oos_gate(r, ppy)
    edge_sub = _benchmark(benchmark) if benchmark is not None else None
    rc = _random_control_gate(benchmark, meta=meta, sims=random_sims, seed=random_seed) if benchmark is not None else None
    cal_alpha = float(edge_sub.raw.get("cal_alpha", 0.0)) if edge_sub is not None else None
    rand_p = float(rc["random_p_value"]) if rc else None

    # edge light
    if edge_sub is None:                                  # no asset -> free luck signal only
        if (psr == psr and psr is not None and psr < PSR_LUCK_FLOOR) or \
           (boot_p5 == boot_p5 and boot_p5 is not None and boot_p5 < 0):
            edge_light = "luck_unclear"
        else:
            edge_light = "not_evaluated"
    else:
        bench_v = edge_sub.value                          # 50 == matched hold (risk-adjusted)
        if bench_v < EDGE_BENCH_LOST:
            edge_light = "lost"
        elif rand_p is not None and rand_p > EDGE_RANDOM_HARD_P:
            edge_light = "random_fail"
        elif rc is None:
            edge_light = "hold_only"
        elif bench_v < EDGE_BENCH_MATCH or (rand_p is not None and rand_p > EDGE_RANDOM_SOFT_P):
            edge_light = "marginal"
        else:
            edge_light = "beat"
    lights = dict(sample=("thin" if sample_hard else "ok"), edge=edge_light)

    # --- the pillar-weighted base score (this is exactly what the 3 bars average to) ---
    uncapped = round(min(max(overall, 0.0), 99.0), 1)

    # --- gates name the problems (flags drive coaching); caps come next ---
    hard: List[str] = []
    soft: List[str] = []
    exp: List[str] = []
    if too_good:
        for code, msg in too_good:
            flags.append(dict(code=code, msg=msg, severity="warn"))
        _append_flag(flags, "TOO_GOOD_TO_BE_TRUE",
                     msg="results look too good to be real — treat as suspect (overfit / "
                         "survivorship / leverage / tiny-capital) until verified", severity="warn")
    forward_warnings = [
        str(w) for w in (meta.get("warnings") or [])
        if "forward-looking" in str(w).lower()
        or "look-ahead" in str(w).lower()
        or "target-leak" in str(w).lower()
    ]
    if forward_warnings:
        _append_flag(flags, "FORWARD_LOOKING_INPUT", msg=forward_warnings[0], severity="warn")
        hard.append("input explicitly suggests forward-looking/leaky data")
    unit_warnings = [
        str(w) for w in (meta.get("warnings") or [])
        if "return units look unusually large" in str(w).lower()
        or "most |return| > 1.0" in str(w).lower()
        or "percent-vs-decimal" in str(w).lower()
    ]
    if unit_warnings:
        _append_flag(flags, "RETURN_UNIT_SUSPECT", msg=unit_warnings[0], severity="info")
    if background_flags:
        _append_flag(flags, "BACKGROUND_REQUIRED",
                     msg="return scale is unusually large — verify starting capital, leverage, venue fills, capacity and whether this was selected from many variants",
                     severity="info")
        for code, msg in background_flags:
            _append_flag(flags, code, msg=msg, severity="info")
    if cagr_full <= 0:
        hard.append("not net profitable")
        _append_flag(flags, "NEGATIVE_RETURN",
                     msg="strategy is not net profitable over the sample", severity="warn")
    if sample_hard:
        hard.append("sample too small")
        bits = []
        if n < A["n_min"] or span_years < 1.0:
            bits.append(f"{n} obs / {span_years:.1f}y")
        if eff_n is not None and eff_n < SAMPLE_MIN_EFF_N:
            bits.append(f"~{eff_n:.1f} effective trades")
        _append_flag(flags, "INSUFFICIENT_SAMPLE",
                     msg="sample too small to trust the score — provisional ("
                         + "; ".join(bits) + ")", severity="warn")
    elif is_low_frequency:
        # Recognized as a low-frequency / event strategy (not a sample defect): say so
        # instead of demanding ">100 trades", which a low-freq strategy can never meet.
        _append_flag(flags, "LOW_FREQUENCY",
                     msg=f"low-frequency / event strategy — {n} trades over {span_years:.1f}y "
                         f"(~{trades_per_year:.0f}/yr); scored on the events you have, not a "
                         "high-frequency sample",
                     severity="info")
    if oos is not None and oos["oos_cagr"] <= 0:
        hard.append("lost money out-of-sample")
        _append_flag(flags, "OOS_NEGATIVE_RETURN", severity="warn")
    if edge_light == "lost":
        hard.append("did not beat buy & hold")
        _append_flag(flags, "UNDERPERFORMS_HOLD_RISKADJ", severity="warn")
    elif edge_light == "random_fail":
        hard.append("did not beat random timing")
        _append_flag(flags, "RANDOM_CONTROL_NOT_BEATEN", severity="warn",
                     random_p_value=round(rand_p, 4))
    elif edge_light == "marginal":
        soft.append("only a marginal edge over random")
        extra = {}
        if rand_p is not None:
            extra["random_p_value"] = round(rand_p, 4)
        _append_flag(flags, "RANDOM_CONTROL_WEAK_EDGE", severity="warn", **extra)
    elif edge_light == "hold_only":
        soft.append("random timing control unavailable")
        _append_flag(flags, "RANDOM_CONTROL_UNAVAILABLE",
                     msg="beat buy & hold, but random timing control could not run on this upload",
                     severity="info")
    elif edge_light == "luck_unclear":
        soft.append("no asset comparison; hard to tell from luck")
        _append_flag(flags, "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK",
                     msg="no asset benchmark and a low PSR — add the asset K-line to test vs "
                         "buy & hold / random timing", severity="info")
    elif edge_light == "not_evaluated":
        soft.append("no asset provided — edge not evaluated")
    if "OVERFIT_SUSPECT_HOLDOUT" in cons.flags:
        _append_flag(flags, "OVERFIT_SUSPECT_HOLDOUT", severity="warn")
    # DSR gate: only bites when the user REPORTS having searched (n_trials>1).
    # Self-reported, so honesty is rewarded with a verdict, not punished with
    # silence — below coin-flip means the search alone explains the result.
    if dsr is not None and n_trials > 1:
        if dsr < 0.50:
            hard.append(f"the {n_trials} reported search trials alone can explain "
                        f"this result (DSR {dsr:.0%})")
            _append_flag(flags, "DSR_FAIL",
                         msg=f"Deflated Sharpe {dsr:.0%} after {n_trials} reported trials — "
                             "selection luck alone can produce this Sharpe",
                         severity="warn")
        elif dsr < 0.95:
            soft.append(f"Sharpe does not clearly survive {n_trials} search trials "
                        f"(DSR {dsr:.0%})")
            _append_flag(flags, "DSR_OVERFIT_RISK",
                         msg=f"Deflated Sharpe {dsr:.0%} after {n_trials} reported trials — "
                             "below the 95% bar once the search is priced in",
                         severity="warn")
    # experience gate: not a defect, just "come back with more history" —
    # so it is informational, but it does cap the metal below SILVER.
    if cagr_full > 0 and not sample_hard:
        if span_years < EXPERIENCE_MIN_YEARS:
            exp.append(f"only {span_years:.1f}y of history — Gold/Silver need "
                       f"{EXPERIENCE_MIN_YEARS:.0f}y+")
            _append_flag(flags, "SHORT_TRACK_RECORD",
                         msg=f"track record is {span_years:.1f} years — a grade above Bronze "
                             f"requires >= {EXPERIENCE_MIN_YEARS:.0f} years (one good year is "
                             "not yet evidence of skill)",
                         severity="info")
        elif eff_n is not None and eff_n < EXPERIENCE_MIN_EFF_N:
            exp.append(f"profit concentrated in ~{eff_n:.0f} effective trades — "
                       "Gold/Silver need a broader base")
            _append_flag(flags, "LOW_EFFECTIVE_SAMPLE",
                         msg=f"profit rests on ~{eff_n:.0f} effective trades — a grade above "
                             f"Bronze requires >= {EXPERIENCE_MIN_EFF_N:.0f}",
                         severity="info")

    # --- one cap so the NUMBER matches the verdict; the cap reason is surfaced ---
    if too_good:
        cap = TIER_FLAGGED_CAP
    elif hard:
        cap = TIER_HARD_CAP                     # below BRONZE -> NEEDS WORK
    else:
        cap = 99.0
        if soft:
            cap = min(cap, TIER_SOFT_CAP)       # below GOLD until the edge is proven
        if exp:
            cap = min(cap, TIER_EXPERIENCE_CAP)  # Bronze band until the record is earned
    display = round(min(uncapped, cap), 1)
    capped = display < uncapped - 0.05
    overall = display                           # internal score == displayed score (one scale)
    judgement = "FLAGGED" if too_good else ("CAUTION" if hard else "OK")

    # --- tier: just the band of the (capped) number, no hidden sub-gates ---
    tier = None
    if judgement == "OK":
        if display >= TIER_GOLD:
            tier = "GOLD"
        elif display >= TIER_SILVER:
            tier = "SILVER"
        elif display >= TIER_BRONZE:
            tier = "BRONZE"

    # --- headline (the protagonist sentence) — bilingual so the site can render the
    # page language without a re-fetch (headline = English, headline_zh = Chinese) ---
    if too_good:
        headline = ("Looks too good to be true — verify the backtest (look-ahead / survivorship / "
                    "fills) before trusting any score.")
        headline_zh = "看着好得不真实——先核回测（未来函数 / 幸存者偏差 / 成交假设），再信任何分数。"
    elif cagr_full <= 0:
        headline = "Not net profitable over the sample."
        headline_zh = "整个样本上没赚钱。"
    elif edge_light == "lost":
        rcap = edge_sub.raw.get("ret_capture")
        cap = f" (captured {rcap:.1f}x of holding)" if (rcap == rcap and rcap is not None) else ""
        cap_zh = f"（只抓到持有的 {rcap:.1f} 倍）" if (rcap == rcap and rcap is not None) else ""
        headline = f"Did NOT beat buy & hold{cap} — most of the return is just owning the asset."
        headline_zh = f"没跑赢「买入持有」{cap_zh}——大部分收益只是持有这个资产本身。"
    elif edge_light == "random_fail":
        headline = f"Indistinguishable from random timing (p={rand_p:.2f}) — no proven timing edge."
        headline_zh = f"和随机择时无法区分（p={rand_p:.2f}）——未证明有择时优势。"
    elif dsr is not None and n_trials > 1 and dsr < 0.50:
        headline = (f"After {n_trials} search trials, this Sharpe is what selection luck "
                    f"produces (DSR {dsr:.0%}).")
        headline_zh = f"试了 {n_trials} 次海选后，这条夏普就是选优运气能做出来的（DSR {dsr:.0%}）。"
    elif sample_hard:
        headline = "Sample too small — score is provisional; not enough track record to trust."
        headline_zh = "样本太小——结论暂定；历史不足以信任。"
    elif oos is not None and oos["oos_cagr"] <= 0:
        headline = "Lost money out-of-sample — the in-sample edge did not hold up."
        headline_zh = "样本外亏钱——样本内的优势没撑住。"
    elif edge_light == "beat" and exp:
        headline = (f"Beat buy & hold and random timing — now prove it over "
                    f"{EXPERIENCE_MIN_YEARS:.0f}+ years of history.")
        headline_zh = f"跑赢了买入持有和随机择时——再用 {EXPERIENCE_MIN_YEARS:.0f}+ 年历史证明它。"
    elif edge_light == "beat":
        if rand_p is not None:
            headline = f"Beat buy & hold AND random timing (p={rand_p:.2f}) — a real, demonstrable edge."
            headline_zh = f"跑赢「买入持有」和「随机择时」（p={rand_p:.2f}）——真实、可验证的优势。"
        else:
            headline = "Beat buy & hold on a risk-adjusted basis."
            headline_zh = "风险调整后跑赢买入持有。"
    elif edge_light == "hold_only":
        headline = "Beat buy & hold, but random-timing evidence is not available."
        headline_zh = "跑赢买入持有，但随机择时证据不可用。"
    elif edge_light == "marginal":
        headline = "Barely beat holding / random timing — a weak, not-clearly-skill edge."
        headline_zh = "勉强跑赢持有 / 随机择时——优势弱，说不上是本事。"
    elif edge_light == "luck_unclear":
        if psr == psr and psr is not None:
            headline = f"Hard to tell from luck (PSR {psr:.2f}) — add the asset's K-line to test vs buy & hold."
            headline_zh = f"难以和运气区分（PSR {psr:.2f}）——加上资产 K 线来对比买入持有。"
        else:
            headline = "Add the asset's K-line to test vs buy & hold / random timing."
            headline_zh = "加上资产 K 线，对比买入持有 / 随机择时。"
    else:
        headline = "Add the K-line of the asset you traded to see if you beat holding / random timing."
        headline_zh = "加上你交易的那个资产的 K 线，看看有没有跑赢持有 / 随机择时。"

    meta.update(dict(
        headline_zh=headline_zh,
        ppy=float(ppy), n=int(n), span_years=float(span_years), cagr=float(cagr_full),
        profile=profile_name, scoring_version="unified_v3", quality_weights=dict(W),
        n_trials=n_trials, anchors_source=ANCHORS_SOURCE, validated=VALIDATED,
        edge_light=edge_light, sample_ok=(not sample_hard),
        low_frequency=bool(is_low_frequency),
        sample_unit=("trades" if meta.get("caliber") == "closed_trade" else "bars"),
        effective_n=(round(float(eff_n), 1) if eff_n is not None else None),
        uncapped_score=uncapped, capped=bool(capped), cap_reasons=(hard + soft + exp),
        random_p=(round(rand_p, 4) if rand_p is not None else None),
        random_control_method=(rc.get("method") if rc else None),
        random_control_sims=(int(rc["random_sims"]) if rc and rc.get("random_sims") is not None else None),
        random_control_events=(int(rc["random_events"]) if rc and rc.get("random_events") is not None else None),
        cal_alpha=(round(cal_alpha, 4) if cal_alpha is not None else None),
        dsr=(round(float(dsr), 4) if dsr is not None else None),
        trial_budget=(int(trial_budget) if trial_budget is not None else None),
        trial_budget_capped=bool(trial_budget is not None
                                 and trial_budget >= metrics.TRIAL_BUDGET_MAX),
    ))
    grade = (GRADE_LABEL.get(tier) if tier else
             (GRADE_LABEL["FLAGGED"] if judgement == "FLAGGED" else GRADE_LABEL["CAUTION"]))
    return UnifiedReport(overall, judgement, tier, headline, rq, cred, risk,
                         edge_sub, lights, flags, meta, display=display, grade=grade)
