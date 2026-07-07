"""Asset-class normalization anchors — grounded in MAINSTREAM industry standards.

IMPORTANT (why these numbers): the "50-point line" for each risk-adjusted-return
metric is set at the widely-accepted industry "acceptable/good" threshold, not at
the median of an unreachable elite-strategy corpus (which would make a normal,
solid strategy score near zero). Sources / rules used:

  * Sharpe ratio  — the common 1/2/3 rule: >1 good, >2 very good, >3 excellent.
    (Backtest Sharpe > ~5 usually signals overfitting -> see sharpe_absurd.)
  * Sortino       — >1 acceptable, >2 very good, >3 excellent.

These map through sat(x, x50) = x/(x+x50): score 0.50 at x = x50, ~0.67 at 2*x50,
~0.75 at 3*x50. So x50 = the industry "good" line. Return-efficiency anchors
(sharpe50, sortino50) are deliberately asset-agnostic — a Sharpe of 1 is "good"
regardless of asset class. Calmar is reported and used in benchmark/OOS checks,
but it is not a profile anchor because the public score's drawdown-risk pillar
already owns drawdown, recovery, and tail risk. What DOES vary by asset class is
drawdown / tail tolerance (crypto investors tolerate far deeper drawdowns than
equity investors).

The lab corpus is used only to (a) inform the methodology and (b) VALIDATE that
the score ranks known-good strategies above known-bad ones (AUC) — never to set
the absolute scale. `VALIDATED` flips True once that ranking check passes.
"""
from __future__ import annotations

ANCHORS_SOURCE = "industry_standard_v1"
VALIDATED = False  # set True after the corpus ranking validation (AUC) passes

# sharpe50 / sortino50 : the "good" line (industry, asset-agnostic) -> score 50.
# mdd50 / cvar50       : drawdown & per-period tail that score 0.5 (asset-specific).
# rec50                : recovery factor (total return / |MDD|) that scores 0.5.
# n_min                : min observations before INSUFFICIENT (SQN wants 100+, Calmar 36m).
# conc_tolerance       : single-bucket PnL share tolerated before a one-off penalty.
# sharpe_absurd        : annualized Sharpe above which "too good to be true" fires
#                        (backtest Sharpe > ~5 commonly indicates overfitting).
PROFILES = {
    "crypto": dict(
        sharpe50=1.0, sortino50=1.4, mdd50=0.35, rec50=3.0, cvar50=0.06,
        n_min=60, conc_tolerance=0.45, sharpe_absurd=6.0,
    ),
    "stock_index": dict(
        sharpe50=1.0, sortino50=1.4, mdd50=0.18, rec50=3.0, cvar50=0.03,
        n_min=60, conc_tolerance=0.40, sharpe_absurd=5.0,
    ),
    "altcoin": dict(
        sharpe50=1.0, sortino50=1.4, mdd50=0.45, rec50=3.0, cvar50=0.10,
        n_min=40, conc_tolerance=0.55, sharpe_absurd=6.0,
    ),
    "other": dict(
        sharpe50=1.0, sortino50=1.4, mdd50=0.25, rec50=3.0, cvar50=0.05,
        n_min=60, conc_tolerance=0.45, sharpe_absurd=5.0,
    ),
}

PROFILE_NAMES = list(PROFILES.keys())


def get_profile(name: str) -> dict:
    """Return anchors for `name`, falling back to the conservative 'other'."""
    return dict(PROFILES.get(name, PROFILES["other"]))
