"""QuantScopeX Strategy Score.

An open-source, overfitting-aware triage score for a trading strategy, computed
from a single returns, equity, or trade-log CSV.

Public API:
    load_returns(source, ...) -> (pd.Series, dict)
    score_unified(returns, profile_name="other", ...) -> UnifiedReport
    build_triage_diagnostics(returns, report, meta, benchmark) -> TriageDiagnostics
"""
from __future__ import annotations

from .io import load_returns
from .profiles import PROFILES, PROFILE_NAMES, get_profile, ANCHORS_SOURCE, VALIDATED
from .scoring import score_unified, SubScore, UnifiedReport
from .coaching import coaching
from .triage import build_triage_diagnostics, TriageDiagnostics
from .report import render_free_pdf

__version__ = "0.3.1"

__all__ = [
    "load_returns",
    "score_unified",
    "coaching",
    "build_triage_diagnostics",
    "render_free_pdf",
    "SubScore",
    "UnifiedReport",
    "TriageDiagnostics",
    "PROFILES",
    "PROFILE_NAMES",
    "get_profile",
    "ANCHORS_SOURCE",
    "VALIDATED",
    "__version__",
]
