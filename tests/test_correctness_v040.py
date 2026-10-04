"""The seven reproduced failure families and supported-input boundaries.

Synthetic examples establish invariants, not external calibration accuracy.
"""
from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import pytest

from qsx_strategy_score import __version__, load_returns, score_unified, build_triage_diagnostics
from qsx_strategy_score import metrics
from qsx_strategy_score.io import InputError, load_prices
from qsx_strategy_score.overlay_client import OverlayPreviewError, run_overlay_preview
from qsx_strategy_score.scoring import _random_control_gate
from qsx_strategy_score.report import render_unified_text, render_unified_png, render_free_pdf
from qsx_strategy_score.i18n import SUPPORTED_LANGS, t


def read_frame(frame, **kwargs):
    return load_returns(io.StringIO(frame.to_csv(index=False)), **kwargs)


def trades():
    return pd.DataFrame(dict(
        entry_time=["2020-01-01", "2020-02-01", "2020-03-01"],
        exit_time=["2020-01-10", "2020-02-10", "2020-03-10"],
        pnl_pct=[10.0, -5.0, 10.0], symbol=["BTC"] * 3))


def paired_fixture(n=1600, beta=0.5, alpha=0.0005):
    index = pd.date_range("2020-01-01", periods=n, freq="D")
    asset = pd.Series(np.random.default_rng(42).normal(-0.001, 0.02, n), index=index)
    returns = beta * asset + alpha
    return returns, metrics.equity_curve(asset)


def test_a_overlap_rejected_instead_of_compounded():
    frame = trades()
    frame["entry_time"] = "2020-01-01"
    with pytest.raises(InputError, match="overlapping"):
        read_frame(frame)


@pytest.mark.parametrize("column,value,reason", [
    ("entry_time", "not-a-date", "every trade"),
    ("entry_time", None, "every trade"),
    ("exit_time", None, "every trade"),
    ("entry_time", "2030-01-01", "after exit"),
    ("symbol", "ETH", "multi-symbol"),
])
def test_a_all_trades_are_checked(column, value, reason):
    frame = trades()
    frame.loc[1, column] = value
    with pytest.raises(InputError, match=reason):
        read_frame(frame)


def test_a_handoff_and_intraday_nonoverlap_are_valid_descriptions():
    frame = trades()
    frame.loc[1, "entry_time"] = frame.loc[0, "exit_time"]
    returns, meta = read_frame(frame)
    report = score_unified(returns, meta=meta)
    assert report.display is None and report.tier is None
    assert report.to_dict()["path_risk"] is None
    assert report.meta["trade_summary"]["win_rate"] == pytest.approx(2 / 3)
    assert all(p["value"] is None for p in report.to_dict()["pillars"].values())
    triage = build_triage_diagnostics(returns, report, meta).to_dict()
    assert triage["next_step"]["primary_action"]["id"] == "add_account_path"
    assert triage["edge_persistence"]["score"] is None
    assert "compound_without_top3" not in triage["dependency_lite"]
    # Retaining attrs without the separate metadata must still close the gate.
    assert score_unified(returns).display is None
    json.dumps(report.to_dict(), allow_nan=False)


@pytest.mark.parametrize("beta", [-1.0, 1.0, -0.5, 0.5])
def test_b_static_exposure_is_never_a_timing_edge(beta):
    returns, prices = paired_fixture(beta=beta, alpha=0)
    comparison = metrics.benchmark_compare(returns, prices)
    rc = _random_control_gate(comparison)
    assert not rc["available"]
    assert rc["reason_code"] in {"UNSUPPORTED_OR_SATURATED_EXPOSURE", "STATIC_EXPOSURE_NOT_BEATEN"}
    report = score_unified(returns, benchmark=comparison)
    assert report.meta["random_p"] is None
    assert report.tier is None
    assert not report.meta["evidence"]["random_control_available"]
    if beta == -1:
        assert report.display > 59  # missing control does not itself punish path quality
        assert report.grade == "PROVISIONAL"


def test_b_small_negative_beta_keeps_direction_and_monte_carlo_tail_is_nonzero():
    returns, prices = paired_fixture(beta=-0.2, alpha=0.0008)
    rc = _random_control_gate(metrics.benchmark_compare(returns, prices))
    assert rc["available"]
    assert rc["beta"] == pytest.approx(-0.2)
    assert rc["exposure"] == pytest.approx(0.2)
    assert rc["random_p_value"] == (rc["random_exceedances"] + 1) / (rc["random_sims"] + 1)
    assert rc["random_p_value"] > 0
    assert "unknown" in rc["cost_basis"]


@pytest.mark.parametrize("beta", [0.0, 0.05, 1.5, -1.5])
def test_b_unsupported_exposures_abstain(beta):
    returns, prices = paired_fixture(beta=beta)
    rc = _random_control_gate(metrics.benchmark_compare(returns, prices))
    assert not rc["available"]
    assert rc["reason_code"] == "UNSUPPORTED_OR_SATURATED_EXPOSURE"


def test_c_daily_and_hourly_representations_compare_identically():
    daily, prices = paired_fixture(n=1000)
    hours = pd.date_range(daily.index[0] - pd.Timedelta(hours=23), periods=len(daily) * 24, freq="h")
    hourly = pd.Series(np.repeat(np.expm1(np.log1p(daily.to_numpy()) / 24), 24), index=hours)
    d = metrics.benchmark_compare(daily, prices)
    hourly_asset = pd.Series(np.repeat(np.expm1(np.log1p(prices.pct_change().dropna().to_numpy()) / 24), 24), index=hours)
    hourly_prices = metrics.equity_curve(hourly_asset)
    h = metrics.benchmark_compare(hourly, hourly_prices)
    unmatched = metrics.benchmark_compare(hourly, prices)
    assert _random_control_gate(unmatched)["reason_code"] == "NATIVE_STATIC_REFERENCE_UNAVAILABLE"
    for field in ("total", "cagr", "mdd", "calmar"):
        assert d["strat"][field] == pytest.approx(h["strat"][field], abs=1e-10)
        assert d["bnh"][field] == pytest.approx(h["bnh"][field], abs=1e-10)
    drc, hrc = _random_control_gate(d), _random_control_gate(h)
    assert drc["available"] and hrc["available"]
    assert drc["random_p_value"] == hrc["random_p_value"]
    assert drc["beta"] == pytest.approx(hrc["beta"], abs=1e-10)
    assert drc["paired_observations"] == hrc["paired_observations"] == 1000


def test_c_utc_conversion_preserves_instants_and_session_intervals():
    returns, prices = paired_fixture()
    shifted = returns.copy()
    shifted.index = shifted.index.tz_localize("UTC").tz_convert("Asia/Shanghai")
    plain = metrics.benchmark_compare(returns, prices)
    aware = metrics.benchmark_compare(shifted, prices)
    assert plain["strat"] == aware["strat"]
    # A Friday-to-Monday benchmark interval includes all strategy weekend PnL.
    bdays = prices[prices.index.dayofweek < 5]
    comparison = metrics.benchmark_compare(returns, bdays)
    paired, reason = metrics.paired_daily_returns(comparison["strat_curve"], comparison["bnh_curve"])
    assert reason is None
    monday = next(ts for ts in paired.index if ts.dayofweek == 0)
    expected = (1 + returns.loc[monday - pd.Timedelta(days=2):monday]).prod() - 1
    assert paired.loc[monday, "strat"] == pytest.approx(expected)


def test_c_incomplete_intraday_and_mismatched_day_cutoffs_abstain():
    daily, prices = paired_fixture(n=150)
    idx = pd.date_range(daily.index[0] - pd.Timedelta(hours=23), periods=len(daily) * 24, freq="h")
    hourly = pd.Series(np.repeat(np.expm1(np.log1p(daily.to_numpy()) / 24), 24), index=idx).drop(idx[300])
    diagnostics = {}
    assert metrics.benchmark_compare(hourly, prices, diagnostics=diagnostics) is None
    assert diagnostics["benchmark_unavailable_reason"] == "INCOMPLETE_INTRADAY_RETURNS"
    shifted = prices.copy()
    shifted.index += pd.Timedelta(hours=12)
    assert metrics.benchmark_compare(daily, shifted, diagnostics=diagnostics) is None
    assert diagnostics["benchmark_unavailable_reason"] == "DAILY_ENDPOINTS_UNAVAILABLE"


def test_c_partial_coverage_and_too_few_days_cannot_qualify():
    returns, prices = paired_fixture(n=400)
    comparison = metrics.benchmark_compare(returns, prices.iloc[50:])
    report = score_unified(returns, benchmark=comparison)
    assert comparison["partial"] and report.tier is None
    rc = _random_control_gate(metrics.benchmark_compare(returns.iloc[:100], prices.iloc[:101]))
    assert rc["reason_code"] == "INSUFFICIENT_PAIRED_DAYS"


def test_d_trade_overlay_never_reaches_network(monkeypatch):
    returns, _ = read_frame(trades())
    def unexpected(*args, **kwargs):
        pytest.fail("trade data reached the network")
    monkeypatch.setattr("urllib.request.urlopen", unexpected)
    with pytest.raises(OverlayPreviewError, match="Trade-log"):
        run_overlay_preview(returns)
    assert metrics.monte_carlo(returns, 252) is None


@pytest.mark.parametrize("reverse", [False, True])
def test_e_conflicting_duplicate_dates_never_depend_on_row_order(reverse):
    frame = pd.DataFrame(dict(date=["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-03"],
                              return_value=[-0.5, 0.01, 0.01, 0.01]))
    if reverse:
        frame = frame.iloc[::-1]
    with pytest.raises(InputError, match="conflicting"):
        read_frame(frame, input_type="returns")
    with pytest.raises(InputError, match="conflicting"):
        load_prices(io.StringIO(frame.rename(columns={"return_value": "close"}).to_csv(index=False)))


def test_e_exact_duplicate_count_and_nonfinite_or_ruin_rejection():
    frame = pd.DataFrame(dict(date=pd.date_range("2020-01-01", periods=4), returns=[0.01, -0.02, 0.03, 0.01]))
    r, meta = read_frame(pd.concat([frame, frame.iloc[[1]]]), input_type="returns")
    assert len(r) == 4 and meta["n_dropped"] == 1
    for value in [np.inf, -np.inf, np.nan, -1.0, -1.2]:
        bad = frame.copy()
        bad.loc[1, "returns"] = value
        with pytest.raises(InputError):
            read_frame(bad, input_type="returns")
        trade = trades()
        trade.loc[1, "pnl_pct"] = value * 100
        with pytest.raises(InputError):
            read_frame(trade)


def test_f_futures_filename_has_no_scoring_effect():
    returns, prices = paired_fixture(beta=-0.5)
    frame = pd.DataFrame(dict(date=returns.index, returns=returns.to_numpy()))
    reports = []
    for filename in ["btc.csv", "btc_futures.csv"]:
        r, meta = read_frame(frame, filename=filename)
        reports.append(score_unified(r, meta=meta, benchmark=metrics.benchmark_compare(r, prices)))
    assert reports[0].display == reports[1].display
    assert reports[0].grade == reports[1].grade
    assert reports[0].meta["input_hash"] == reports[1].meta["input_hash"]
    confirmed = score_unified(returns, meta={"known_lookahead": True})
    assert any(f["code"] == "FORWARD_LOOKING_INPUT" for f in confirmed.flags)


def test_g_search_unknown_and_path_risk_have_separate_contracts():
    returns, prices = paired_fixture(beta=-0.5, alpha=0.0005)
    comparison = metrics.benchmark_compare(returns, prices)
    unknown = score_unified(returns, benchmark=comparison)
    single = score_unified(returns, benchmark=comparison, n_trials=1)
    searched = score_unified(returns, benchmark=comparison, n_trials=10000)
    assert unknown.meta["n_trials"] is None and unknown.meta["dsr"] is None
    assert unknown.meta["search_trials_status"] == "unknown"
    assert single.meta["search_trials_status"] == "self_reported"
    assert single.meta["dsr"] > searched.meta["dsr"]
    assert single.to_dict()["path_risk"] == searched.to_dict()["path_risk"]
    assert "excluding_search" in searched.meta["path_risk_scope"]
    assert unknown.meta["core_version"] == __version__ == "0.4.0"
    assert len(unknown.meta["input_hash"]) == len(unknown.meta["benchmark_hash"]) == 64
    for lang in SUPPORTED_LANGS:
        assert t("search_unknown", lang) in render_unified_text(unknown, lang=lang)


def test_mc_allocation_guard_runs_before_rng(monkeypatch):
    r = pd.Series(np.zeros(100000))
    def unexpected(*args, **kwargs):
        pytest.fail("oversized simulation allocated RNG arrays")
    monkeypatch.setattr(np.random, "default_rng", unexpected)
    assert metrics.monte_carlo(r, 365) is None
    assert metrics.monte_carlo_unavailable_reason(r, 365) == "MC_MEMORY_LIMIT"


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_trade_descriptions_render_without_account_metrics(tmp_path, lang):
    fitz = pytest.importorskip("fitz")
    returns, meta = read_frame(trades())
    report = score_unified(returns, meta=meta)
    text = render_unified_text(report, lang=lang)
    assert "N/A" in text and t("trade_only_title", lang) in text
    assert "CAGR" not in text and "Sharpe" not in text
    png, pdf = tmp_path / "trade.png", tmp_path / "trade.pdf"
    render_unified_png(report, returns, str(png), lang=lang)
    render_free_pdf(report, returns, str(pdf), lang=lang)
    assert png.stat().st_size > 10000
    with fitz.open(pdf) as doc:
        assert doc.page_count == 1
        # Check rendered pixels as well as text extraction: malformed CFF-as-TTF
        # embedding can leave an extractable title with almost no visible glyphs.
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(100 / 72, 100 / 72))
        pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        title = pixels[int(pix.height * .15):int(pix.height * .24), int(pix.width * .065):int(pix.width * .7), :3]
        assert (title.min(axis=2) > 180).sum() > 500


@pytest.mark.parametrize("with_benchmark", [False, True])
@pytest.mark.parametrize("mixed", [False, True])
def test_incomplete_returns_never_enter_account_scoring(with_benchmark, mixed):
    if mixed:
        idx = pd.date_range("2020-01-01", periods=161, freq="D").union(pd.DatetimeIndex(["2020-01-02 01:00"]))
    else:
        idx = pd.date_range("2020-01-01", periods=161 * 24, freq="h").delete(300)
    r = pd.Series(np.random.default_rng(8).normal(0.0001, 0.001, len(idx)), index=idx)
    prices = metrics.equity_curve(paired_fixture(n=170)[0])
    benchmark = metrics.benchmark_compare(r, prices) if with_benchmark else None
    with pytest.raises(ValueError, match="INCOMPLETE_INTRADAY_RETURNS"):
        score_unified(r, benchmark=benchmark)
    with pytest.raises(InputError, match="INCOMPLETE_INTRADAY_RETURNS"):
        read_frame(pd.DataFrame(dict(date=idx, returns=r.to_numpy())), input_type="returns")
    # Independent NAV levels bridge observation gaps without losing known PnL.
    r.attrs["input_type"] = "equity"
    assert score_unified(r).display is not None


def test_native_constant_half_exposure_cannot_qualify_as_timing():
    u = np.random.default_rng(42).normal(-0.0005, 0.01, 1600)
    bars = np.zeros((len(u), 24))
    bars[:, 0] = 0.06
    bars[:, 1] = (1 + u) / 1.06 - 1
    idx = pd.date_range("2020-01-01 01:00", periods=bars.size, freq="h")
    asset = pd.Series(bars.ravel(), index=idx)
    r = 0.5 * asset
    comparison = metrics.benchmark_compare(r, metrics.equity_curve(asset))
    rc = _random_control_gate(comparison)
    assert rc["beta"] == pytest.approx(0.4858490566)
    assert rc["strat_calmar"] > rc["static_calmar"]
    assert rc["native_static_reference"]["beta"] == pytest.approx(0.5)
    assert rc["reason_code"] == "NATIVE_STATIC_EXPOSURE_NOT_BEATEN"
    assert not rc["available"]
    report = score_unified(r, benchmark=comparison)
    assert report.tier is None and report.meta["random_p"] is None


def test_equity_initial_anchor_and_source_survive_missing_observations():
    idx = pd.date_range("2020-01-01", periods=170, freq="D")
    frame = pd.DataFrame(dict(date=idx, equity=np.cumprod(1 + np.random.default_rng(8).normal(0.001, 0.01, len(idx)))))
    frame = frame.drop(index=3)
    r, meta = read_frame(frame, input_type="equity")
    nav = metrics.equity_curve(r)
    assert nav.index[0] == idx[0]
    assert nav.attrs["input_type"] == "equity"
    assert nav.iloc[-1] == pytest.approx(frame.equity.iloc[-1] / frame.equity.iloc[0])
    paired, reason = metrics.paired_daily_returns(nav, nav.copy())
    assert reason is None
    assert paired.loc[idx[4], "strat"] == pytest.approx(frame.equity.loc[4] / frame.equity.loc[2] - 1)


def test_missing_control_and_thin_sample_do_not_cap_score():
    r, _ = paired_fixture(n=320, beta=0.5, alpha=0.0015)
    report = score_unified(r)
    assert not report.meta["sample_ok"]
    assert report.grade == "PROVISIONAL"
    assert report.display == report.meta["uncapped_score"]
    assert not report.meta["capped"]


def test_unavailable_control_has_specific_next_step_and_localized_text():
    from qsx_strategy_score.i18n import unavailable_reason
    r, prices = paired_fixture(beta=-1, alpha=0)
    report = score_unified(r, benchmark=metrics.benchmark_compare(r, prices))
    for lang in SUPPORTED_LANGS:
        triage = build_triage_diagnostics(r, report, lang=lang).to_dict()
        assert triage["next_step"]["primary_action"]["id"] == "review_comparison_limits"
        reason = unavailable_reason(report.meta["random_control_unavailable_reason"], lang)
        assert reason in triage["next_step"]["body"]
        assert reason in render_unified_text(report, lang=lang)


def test_custom_mc_unavailability_reason_matches_execution():
    r = pd.Series(np.random.default_rng(10).normal(0, 0.01, 100))
    for params, reason in [({"n_sims": 100}, "MC_TOO_FEW_SIMULATIONS"), ({"block": 0}, "MC_INVALID_BLOCK")]:
        assert metrics.monte_carlo(r, 365, **params) is None
        assert metrics.monte_carlo_unavailable_reason(r, 365, **params) == reason
