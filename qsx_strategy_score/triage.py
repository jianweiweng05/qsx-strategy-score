"""Free due-diligence-lite diagnostics.

These helpers deliberately stop short of the proprietary Pro stack. They answer
"is this strategy worth a deeper audit?" using only the uploaded return path and
safe metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from . import metrics
from .i18n import t


@dataclass
class TriageDiagnostics:
    edge_persistence: dict
    evidence_confidence: dict
    dependency_lite: dict
    pro_unlock_map: dict

    def to_dict(self) -> dict:
        return {
            "edge_persistence": self.edge_persistence,
            "evidence_confidence": self.evidence_confidence,
            "dependency_lite": self.dependency_lite,
            "pro_unlock_map": self.pro_unlock_map,
        }


def _finite_series(r: pd.Series) -> pd.Series:
    return pd.Series(r).astype(float).replace([np.inf, -np.inf], np.nan).dropna()


def edge_persistence_lite(returns: pd.Series, ppy: float, *, lang: str = "en") -> dict:
    """Compare the recent third of the track record with the earlier sample."""
    r = _finite_series(returns)
    if len(r) < 120:
        return {
            "label": "unavailable",
            "label_local": t("unavailable", lang),
            "score": None,
            "reason": "Need at least 120 observations for a meaningful recent-vs-prior read.",
            "recent_sharpe": None,
            "prior_sharpe": None,
        }
    cut = max(int(len(r) * 0.67), len(r) - max(40, int(len(r) * 0.33)))
    prior = r.iloc[:cut]
    recent = r.iloc[cut:]
    if len(prior) < 60 or len(recent) < 40:
        return {
            "label": "unavailable",
            "label_local": t("unavailable", lang),
            "score": None,
            "reason": "Recent window is too short for a stable read.",
            "recent_sharpe": None,
            "prior_sharpe": None,
        }
    prior_sharpe = metrics.sharpe(prior, ppy)
    recent_sharpe = metrics.sharpe(recent, ppy)
    recent_cagr = metrics.cagr(recent, ppy)
    prior_cagr = metrics.cagr(prior, ppy)
    delta = recent_sharpe - prior_sharpe
    if recent_cagr <= 0 or delta <= -1.0:
        label = "deteriorating"
        score = 35
    elif delta <= -0.35:
        label = "weakening"
        score = 60
    else:
        label = "stable"
        score = 80
    return {
        "label": label,
        "label_local": t(label, lang),
        "score": score,
        "reason": (
            f"Recent Sharpe {recent_sharpe:.2f} vs prior {prior_sharpe:.2f}; "
            f"recent CAGR {recent_cagr * 100:.1f}% vs prior {prior_cagr * 100:.1f}%."
        ),
        "recent_sharpe": round(float(recent_sharpe), 3),
        "prior_sharpe": round(float(prior_sharpe), 3),
        "recent_cagr": round(float(recent_cagr), 4),
        "prior_cagr": round(float(prior_cagr), 4),
    }


def evidence_confidence(returns: pd.Series, meta: Optional[dict] = None, *,
                        benchmark_available: bool = False, lang: str = "en") -> dict:
    meta = dict(meta or {})
    n = int(len(pd.Series(returns).dropna()))
    input_type = str(meta.get("input_type") or "returns")
    span_years = float(meta.get("span_years") or 0.0)
    is_trade_log = input_type == "trade_log" or meta.get("caliber") == "closed_trade"
    points = 0
    reasons = []
    if n >= 500:
        points += 2
        reasons.append("long return path")
    elif n >= 120:
        points += 1
        reasons.append("usable sample")
    else:
        reasons.append("short sample")
    if span_years >= 2.0:
        points += 2
    elif span_years >= 1.0:
        points += 1
    if benchmark_available:
        points += 1
        reasons.append("asset benchmark available")
    if is_trade_log:
        reasons.append("closed-trade path only; intra-trade MTM is not visible")
    else:
        points += 1
        reasons.append("bar-level return/equity path")
    if points >= 5:
        level = "high"
    elif points >= 3:
        level = "medium"
    elif points >= 2:
        level = "limited"
    else:
        level = "low"
    return {
        "level": level,
        "level_local": t(level, lang),
        "score": min(100, points * 18),
        "reason": "; ".join(reasons),
        "input_type": input_type,
        "observations": n,
        "span_years": round(span_years, 2),
        "benchmark_available": bool(benchmark_available),
    }


def trade_dependency_scan(returns: pd.Series, meta: Optional[dict] = None, *,
                          lang: str = "en") -> dict:
    meta = dict(meta or {})
    r = _finite_series(returns)
    is_trade_log = meta.get("caliber") == "closed_trade" or meta.get("input_type") == "trade_log"
    if not is_trade_log:
        return {
            "available": False,
            "type": "returns_dependency_lite",
            "reason": "Trade dependency scan is available for trade logs. For return series, use concentration and edge persistence.",
        }
    pos = r[r > 0].sort_values(ascending=False)
    total_pos = float(pos.sum()) if len(pos) else 0.0
    top1 = float(pos.iloc[:1].sum() / total_pos) if total_pos > 0 else 0.0
    top3 = float(pos.iloc[:3].sum() / total_pos) if total_pos > 0 else 0.0
    top5 = float(pos.iloc[:5].sum() / total_pos) if total_pos > 0 else 0.0
    without_top3 = r.copy()
    if len(pos):
        without_top3.loc[pos.index[:3]] = 0.0
    gross_gain = float(r[r > 0].sum())
    gross_loss = float(abs(r[r < 0].sum()))
    profit_factor = gross_gain / gross_loss if gross_loss > 0 else float("inf")
    label = "high" if top3 < 0.45 else "medium" if top3 < 0.70 else "low"
    return {
        "available": True,
        "type": "trade_dependency_scan",
        "label": label,
        "label_local": t(label, lang),
        "n_trades": int(len(r)),
        "win_rate": round(float((r > 0).mean()), 4) if len(r) else None,
        "profit_factor": round(float(profit_factor), 3) if np.isfinite(profit_factor) else None,
        "top1_positive_pnl_share": round(top1, 4),
        "top3_positive_pnl_share": round(top3, 4),
        "top5_positive_pnl_share": round(top5, 4),
        "compound_without_top3": round(float(np.prod(1.0 + without_top3) - 1.0), 4),
        "reason": (
            f"Top 3 winning trades contribute {top3 * 100:.1f}% of positive PnL; "
            f"compound return without them is {(np.prod(1.0 + without_top3) - 1.0) * 100:.1f}%."
        ),
    }


def dependency_lite(returns: pd.Series, meta: Optional[dict] = None,
                    benchmark: Optional[dict] = None, *, lang: str = "en") -> dict:
    trade_scan = trade_dependency_scan(returns, meta, lang=lang)
    if trade_scan.get("available"):
        return trade_scan
    if benchmark is None or benchmark.get("strat") is None or benchmark.get("bnh") is None:
        return {
            "available": False,
            "type": "returns_dependency_lite",
            "reason": "Add the traded asset K-line to estimate beta/correlation vs hold.",
        }
    strat_curve = pd.Series(benchmark.get("strat_curve")).astype(float)
    hold_curve = pd.Series(benchmark.get("bnh_curve")).astype(float)
    sr = strat_curve.pct_change().dropna()
    hr = hold_curve.pct_change().dropna()
    joined = pd.concat([sr.rename("strategy"), hr.rename("hold")], axis=1).dropna()
    if len(joined) < 40 or joined["hold"].std(ddof=1) == 0:
        return {"available": False, "type": "returns_dependency_lite", "reason": "Benchmark overlap is too short."}
    corr = float(joined["strategy"].corr(joined["hold"]))
    beta = float(joined["strategy"].cov(joined["hold"]) / joined["hold"].var(ddof=1))
    label = "low" if abs(corr) < 0.25 else "medium" if abs(corr) < 0.55 else "high"
    return {
        "available": True,
        "type": "benchmark_beta_lite",
        "label": label,
        "label_local": t(label, lang),
        "correlation_to_hold": round(corr, 4),
        "beta_to_hold": round(beta, 4),
        "observations": int(len(joined)),
        "reason": f"Correlation to buy & hold is {corr:+.2f}; beta is {beta:+.2f}.",
    }


def pro_unlock_map(meta: Optional[dict] = None, *, dependency_available: bool = False,
                   benchmark_available: bool = False, lang: str = "en") -> dict:
    meta = dict(meta or {})
    is_trade_log = meta.get("caliber") == "closed_trade" or meta.get("input_type") == "trade_log"
    unlocks = [
        {
            "module": "HCRI Home Field",
            "why": "Maps when the strategy historically works or fails across market weather.",
            "requires": "strategy returns plus QuantScopeX Pro regime data",
            "free_status": "preview_only",
        },
        {
            "module": "Exposure X-Ray",
            "why": "Separates real alpha from dressed-up BTC/ETH/liquidity beta.",
            "requires": "daily return/equity path and Pro factor library",
            "free_status": "lite_available" if dependency_available else "locked",
        },
        {
            "module": "Black Swan Database",
            "why": "Checks behavior through named crisis windows, not just generic drawdown.",
            "requires": "dated strategy path and Pro event registry",
            "free_status": "locked",
        },
        {
            "module": "Cost & True MTM",
            "why": "Tests costs, slippage, and intra-trade mark-to-market drawdown.",
            "requires": "trade log plus bar data / execution assumptions",
            "free_status": "locked" if is_trade_log else "partially_visible",
        },
    ]
    return {
        "headline": t("pro_unlocks_short", lang),
        "cta": t("pro_cta", lang),
        "benchmark_available": bool(benchmark_available),
        "modules": unlocks,
    }


def build_triage_diagnostics(returns: pd.Series, report, meta: Optional[dict] = None,
                             benchmark: Optional[dict] = None, *, lang: str = "en") -> TriageDiagnostics:
    ppy = float((meta or {}).get("ppy") or getattr(report, "meta", {}).get("ppy") or 252.0)
    dep = dependency_lite(returns, meta, benchmark, lang=lang)
    ev = evidence_confidence(returns, meta, benchmark_available=benchmark is not None, lang=lang)
    ep = edge_persistence_lite(returns, ppy, lang=lang)
    unlocks = pro_unlock_map(
        meta,
        dependency_available=bool(dep.get("available")),
        benchmark_available=benchmark is not None,
        lang=lang,
    )
    return TriageDiagnostics(ep, ev, dep, unlocks)
