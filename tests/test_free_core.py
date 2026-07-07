from __future__ import annotations

import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qsx_strategy_score import build_triage_diagnostics, load_returns, score_unified
from qsx_strategy_score.asset_library import key_from_filename
from qsx_strategy_score.i18n import MESSAGES, SUPPORTED_LANGS
from qsx_strategy_score.overlay_client import (
    OverlayPreviewError,
    normalize_daily_returns,
    run_overlay_preview,
    trade_log_to_daily_overlay_returns,
)
from qsx_strategy_score.metrics import benchmark_compare
from qsx_strategy_score.report import render_unified_png
from qsx_strategy_score.report_preflight import preflight_score_upload


def test_score_unified_and_triage_on_sample_returns():
    r, meta = load_returns(ROOT / "examples" / "sample_returns.csv")
    report = score_unified(r, "crypto", meta=meta)
    triage = build_triage_diagnostics(r, report, meta=meta).to_dict()

    assert 0 <= report.display <= 99.9
    assert report.grade in {"GOLD", "SILVER", "BRONZE", "NEEDS WORK", "FLAGGED"}
    assert "edge_persistence" in triage
    assert "evidence_confidence" in triage
    assert "pro_unlock_map" in triage


def test_trade_log_dependency_scan_is_available():
    df = pd.DataFrame({
        "entry_time": pd.date_range("2021-01-01", periods=80, freq="5D"),
        "exit_time": pd.date_range("2021-01-03", periods=80, freq="5D"),
        "pnl_pct": np.tile([2.0, -0.8, 1.2, -0.5, 4.0], 16),
        "symbol": ["DOGE"] * 80,
    })
    r, meta = load_returns(io.StringIO(df.to_csv(index=False)), filename="DOGE7H.csv")
    report = score_unified(r, "altcoin", meta=meta)
    triage = build_triage_diagnostics(r, report, meta=meta).to_dict()

    dep = triage["dependency_lite"]
    assert dep["available"] is True
    assert dep["type"] == "trade_dependency_scan"
    assert dep["n_trades"] == 80


def test_preflight_uses_free_loader_only():
    raw = (ROOT / "examples" / "sample_returns.csv").read_bytes()
    out = preflight_score_upload(raw, filename="sample_returns.csv")
    assert out["ready"] is True
    assert out["details"]["bundle"]["observations"] > 100


def test_overlay_client_normalizes_to_daily_minimal_csv():
    idx = pd.date_range("2024-01-01", periods=400 * 2, freq="12h")
    r = pd.Series(np.tile([0.01, -0.002], 400), index=idx)
    normalized = normalize_daily_returns(r)

    assert normalized.rows == 400
    assert normalized.csv.startswith("date,return\n")
    assert "2024-01-01" in normalized.csv
    assert len(normalized.sha256) == 64
    assert "entry" not in normalized.csv
    assert "symbol" not in normalized.csv


def test_overlay_trade_log_expands_holding_period_to_daily_path():
    df = pd.DataFrame({
        "entry_time": ["2019-10-26", "2021-01-01", "2024-12-01", "2025-06-01"],
        "exit_time": ["2019-11-19", "2021-04-13", "2025-03-11", "2025-06-22"],
        "pnl_pct": [-4.98, 71.86, 34.79, 2.35],
        "symbol": ["BTC"] * 4,
    })
    daily = trade_log_to_daily_overlay_returns(io.StringIO(df.to_csv(index=False)), filename="BTC10H.csv")
    normalized = normalize_daily_returns(daily)

    assert normalized.rows > 1800
    assert normalized.start == "2019-10-26"
    assert normalized.end == "2025-06-22"
    assert "entry_time" not in normalized.csv
    assert "symbol" not in normalized.csv


def test_overlay_trade_log_rejects_overlapping_positions():
    df = pd.DataFrame({
        "entry_time": ["2024-01-01", "2024-01-05", "2024-02-01"],
        "exit_time": ["2024-01-10", "2024-01-12", "2024-02-05"],
        "pnl_pct": [10.0, 10.0, 3.0],
        "symbol": ["BTC"] * 3,
    })

    with pytest.raises(OverlayPreviewError, match="overlapping positions"):
        trade_log_to_daily_overlay_returns(io.StringIO(df.to_csv(index=False)), filename="BTC_overlap.csv")


def test_overlay_trade_log_allows_same_day_handoffs():
    df = pd.DataFrame({
        "entry_time": ["2024-01-01", "2024-01-10", "2024-02-01"],
        "exit_time": ["2024-01-10", "2024-01-20", "2024-02-05"],
        "pnl_pct": [4.0, 2.0, 3.0],
        "symbol": ["BTC"] * 3,
    })

    daily = trade_log_to_daily_overlay_returns(io.StringIO(df.to_csv(index=False)), filename="BTC_handoff.csv")

    assert daily.index[0] == pd.Timestamp("2024-01-01")
    assert daily.index[-1] == pd.Timestamp("2024-02-05")
    assert len(daily) == 36


def test_overlay_trade_log_rejects_intraday_overlap():
    df = pd.DataFrame({
        "entry_time": ["2024-01-01 09:00", "2024-01-10 10:00", "2024-02-01 09:00"],
        "exit_time": ["2024-01-10 16:00", "2024-01-20 16:00", "2024-02-05 16:00"],
        "pnl_pct": [4.0, 2.0, 3.0],
        "symbol": ["BTC"] * 3,
    })

    with pytest.raises(OverlayPreviewError, match="overlapping positions"):
        trade_log_to_daily_overlay_returns(io.StringIO(df.to_csv(index=False)), filename="BTC_intraday_overlap.csv")


def test_loader_accepts_raw_tradingview_multisheet_xlsx(tmp_path):
    path = tmp_path / "TradingView_LuxAlgo_CN.xlsx"
    summary = pd.DataFrame({
        "指标": ["初始资本", "净利润", "夏普比率"],
        "全部 USDT": [100, 33617.1, 0.439],
        "全部 %": [np.nan, 33617.1, np.nan],
    })
    trades = pd.DataFrame({
        "Trade number": [1, 1, 2, 2, 3, 3, 4, 4],
        "类型": ["多头出场", "多头进场", "空头出场", "空头进场", "多头出场", "多头进场", "空头出场", "空头进场"],
        "日期和时间": [
            "2020-01-10 08:00:00", "2020-01-01 08:00:00",
            "2020-02-20 08:00:00", "2020-02-01 08:00:00",
            "2020-03-15 08:00:00", "2020-03-01 08:00:00",
            "2020-04-18 08:00:00", "2020-04-01 08:00:00",
        ],
        "信号": ["Long TP", "Long", "Exit Short", "Short", "Long TP", "Long", "Short TS", "Short"],
        "价格 USDT": [110, 100, 90, 105, 130, 115, 85, 95],
        "大小（数量）": [1] * 8,
        "Net PnL USDT": [10, 10, 5, 5, -3, -3, 8, 8],
        "Net PnL %": [10, 10, 5, 5, -3, -3, 8, 8],
        "Cumulative PnL %": [10, 10, 15.5, 15.5, 12.0, 12.0, 21.0, 21.0],
    })
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="表现", index=False)
        trades.to_excel(writer, sheet_name="Trades", index=False)

    returns, meta = load_returns(path)
    report = score_unified(returns, "crypto", meta=meta)
    daily = trade_log_to_daily_overlay_returns(path, filename=str(path))
    normalized = normalize_daily_returns(daily)

    assert meta["input_type"] == "trade_log"
    assert list(returns.round(6)) == [0.10, 0.05, -0.03, 0.08]
    assert meta["n_trades"] == 4
    assert len(meta["trade_entry_times"]) == 4
    assert str(meta["trade_entry_times"][0]).startswith("2020-01-01")
    assert any("TradingView-style event log" in w for w in meta["warnings"])
    assert report.display >= 0
    assert len(daily) >= 100
    assert normalized.start == "2020-01-01"
    assert normalized.end == "2020-04-18"


def test_loader_accepts_rare_extreme_positive_daily_return():
    df = pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=40, freq="D"),
        "return": np.r_[np.repeat(0.002, 20), 3.9, np.repeat(-0.003, 19)],
    })
    r, meta = load_returns(io.StringIO(df.to_csv(index=False)))

    assert len(r) == 40
    assert float(r.max()) > 3.0
    assert any("exceed +300%" in w for w in meta.get("warnings", []))


def test_loader_warns_on_likely_percent_as_decimal_returns():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20, freq="D"),
        "return": np.tile([2.0, -0.5, 1.2, -0.3], 5),
    })
    r, meta = load_returns(io.StringIO(df.to_csv(index=False)))
    report = score_unified(r, "crypto", meta=meta)

    assert any("return units look unusually large" in w for w in meta.get("warnings", []))
    assert any(f["code"] == "RETURN_UNIT_SUSPECT" for f in report.flags)
    assert report.display >= 0


def test_overlay_preview_429_has_friendly_message(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=40, freq="D")
    r = pd.Series(np.repeat(0.001, len(idx)), index=idx)

    def raise_429(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://www.quantscopex.com/api/overlay/preview",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"raw backend detail"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_429)

    with pytest.raises(OverlayPreviewError, match="temporarily rate-limited"):
        run_overlay_preview(r)


def test_overlay_preview_sends_github_source_header(monkeypatch):
    idx = pd.date_range("2024-01-01", periods=40, freq="D")
    r = pd.Series(np.repeat(0.001, len(idx)), index=idx)
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            payload = {
                "ok": True,
                "inputSha256": captured["request"].headers["X-qsx-input-sha256"],
            }
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(req, timeout=30):
        captured["request"] = req
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    out = run_overlay_preview(r, lang="zh")

    headers = captured["request"].headers
    assert headers["X-qsx-client"] == "qsx-score-free/0.1.0"
    assert headers["X-qsx-source"] == "github-open-source"
    assert headers["X-qsx-lang"] == "zh"
    assert out["_local"]["normalized_rows"] == 40


def test_yahoo_fetch_falls_back_to_query2(monkeypatch):
    from qsx_strategy_score import assets

    payload = {
        "chart": {
            "result": [{
                "timestamp": [1704067200, 1704153600],
                "indicators": {
                    "quote": [{
                        "open": [100.0, 101.0],
                        "high": [102.0, 103.0],
                        "low": [99.0, 100.0],
                        "close": [101.0, 102.0],
                        "volume": [1000, 1100],
                    }]
                },
            }],
            "error": None,
        }
    }
    calls = []

    def fake_http_json(url, *args, **kwargs):
        calls.append(url)
        if "query1.finance.yahoo.com" in url:
            raise RuntimeError("HTTP 403 Forbidden")
        return payload

    monkeypatch.setattr(assets, "_http_json", fake_http_json)

    out = assets.fetch_yahoo("SPY", 0)

    assert len(out) == 2
    assert calls[0].startswith("https://query1.finance.yahoo.com/")
    assert calls[1].startswith("https://query2.finance.yahoo.com/")


def test_yahoo_chart_error_is_reported(monkeypatch):
    from qsx_strategy_score import assets

    def fake_http_json(url, *args, **kwargs):
        return {
            "chart": {
                "result": None,
                "error": {
                    "code": "Unauthorized",
                    "description": "Invalid crumb",
                },
            }
        }

    monkeypatch.setattr(assets, "_http_json", fake_http_json)

    with pytest.raises(RuntimeError, match="Yahoo chart fetch failed for SPY"):
        assets.fetch_yahoo("SPY", 0)


def test_profile_docs_do_not_ship_dead_calmar_anchor():
    from qsx_strategy_score.profiles import PROFILES

    for profile in PROFILES.values():
        assert "calmar50" not in profile
        assert "sortino50" in profile


def test_cli_multilingual_json(tmp_path):
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "qsx_strategy_score.cli",
            str(ROOT / "examples" / "sample_returns.csv"),
            "--lang",
            "es",
            "--json",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out.read_text())
    assert data["lang"] == "es"
    assert "triage" in data
    assert "Triage" in proc.stdout or "QSX" in proc.stdout


def test_supported_languages_have_complete_core_messages():
    base = set(MESSAGES["en"])
    for lang in SUPPORTED_LANGS:
        assert not (base - set(MESSAGES[lang])), lang


def test_filename_resolves_asset_for_low_frequency_log():
    # A sparse / low-frequency series (e.g. a 46-trade log) can't be correlation-
    # confirmed against daily K-lines. The filename is then the best signal and
    # must AUTO-resolve (gate accepts high/medium), not get stuck at "low / add
    # the asset" — that was a real regression on TradingView/LuxAlgo BTC logs.
    from qsx_strategy_score import assets as _assets
    from qsx_strategy_score.asset_library import detect_asset
    if "BTC" not in _assets.available_keys():
        pytest.skip("asset price library not present locally")
    idx = pd.to_datetime(["2021-01-05", "2021-06-10", "2022-02-01",
                          "2023-08-15", "2024-03-20", "2025-01-09"])
    r = pd.Series([0.10, -0.05, 0.20, 0.03, -0.10, 0.08], index=idx)
    det = detect_asset(r, filename="LuxAlgo_BINANCE_BTCUSDT.P.csv")
    assert det.best is not None and det.best.key == "BTC"
    assert det.confidence in ("high", "medium")  # gate-acceptable


def test_spx_filename_resolves_to_index_not_spy_etf():
    assert key_from_filename("SPX_strategy_returns.csv") == "SPX"
    assert key_from_filename("SPY_strategy_returns.csv") == "SPY"


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_cli_text_json_and_png_render_for_each_language(tmp_path, lang):
    out_json = tmp_path / f"report-{lang}.json"
    out_png = tmp_path / f"report-{lang}.png"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "qsx_strategy_score.cli",
            str(ROOT / "examples" / "sample_returns.csv"),
            "--lang",
            lang,
            "--json",
            str(out_json),
            "--out",
            str(out_png),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "QSX Strategy Score" in proc.stdout
    data = json.loads(out_json.read_text())
    assert data["lang"] == lang
    assert out_png.exists()
    assert out_png.stat().st_size > 40_000


def test_unified_score_handles_marginal_edge_without_random_p():
    idx = pd.date_range("2024-01-01", periods=90, freq="D")
    r = pd.Series(np.r_[np.repeat(0.001, 45), np.repeat(-0.0002, 45)], index=idx)
    px = pd.Series(100 * (1 + pd.Series(np.repeat(0.0008, 90), index=idx)).cumprod(), index=idx)
    bench = benchmark_compare(r, px)

    report = score_unified(r, "other", benchmark=bench)

    assert report.meta["random_p"] is None
    assert report.lights["edge"] in {"hold_only", "lost"}
    assert report.display >= 0


def test_closed_trade_log_random_control_uses_event_windows():
    n = 46
    entries = pd.date_range("2019-11-18", periods=n, freq="45D")
    exits = entries + pd.Timedelta(days=20)
    df = pd.DataFrame({
        "entry_time": entries,
        "exit_time": exits,
        "pnl_pct": np.where(np.arange(n) % 6 == 0, -3.0, 7.0),
        "symbol": ["DOGE"] * n,
    })
    r, meta = load_returns(io.StringIO(df.to_csv(index=False)), filename="DOGE7H.csv")
    days = pd.date_range(entries.min() - pd.Timedelta(days=30),
                         exits.max() + pd.Timedelta(days=30), freq="D")
    daily = (
        0.0008
        + 0.015 * np.sin(np.linspace(0, 24, len(days)))
        + 0.008 * np.cos(np.linspace(0, 55, len(days)))
    )
    px = pd.Series(100 * np.cumprod(1 + daily), index=days)
    bench = benchmark_compare(r, px)

    report = score_unified(r, "crypto", meta=meta, benchmark=bench, random_sims=96)

    assert len(meta["trade_entry_times"]) == n
    assert report.meta["random_control_method"] == "event_window"
    assert report.meta["random_control_events"] == n
    assert report.meta["random_p"] is not None
    assert report.lights["edge"] != "hold_only"


def test_closed_trade_log_partial_benchmark_overlap_does_not_crash():
    n = 24
    entries = pd.date_range("2020-01-01", periods=n, freq="30D")
    exits = entries + pd.Timedelta(days=10)
    df = pd.DataFrame({
        "entry_time": entries,
        "exit_time": exits,
        "pnl_pct": np.tile([2.5, -1.0, 3.0, 0.8], 6),
        "symbol": ["BTC"] * n,
    })
    r, meta = load_returns(io.StringIO(df.to_csv(index=False)), filename="BTC_events.csv")
    days = pd.date_range("2020-06-01", "2021-10-31", freq="D")
    px = pd.Series(100 * np.cumprod(1 + 0.001 * np.sin(np.linspace(0, 12, len(days)))), index=days)
    bench = benchmark_compare(r, px)

    report = score_unified(r, "crypto", meta=meta, benchmark=bench, random_sims=64)

    assert bench is not None
    assert bench["partial"] is True
    assert report.display >= 0
    assert report.meta["random_control_method"] in {"event_window", None}


def test_forward_looking_filename_caps_score(tmp_path):
    path = tmp_path / "BTC_leaky_future_ma.csv"
    df = pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=400, freq="D"),
        "return": np.tile([0.02, -0.001, 0.015, 0.0], 100),
    })
    df.to_csv(path, index=False)

    r, meta = load_returns(path)
    report = score_unified(r, "crypto", meta=meta)

    assert any("forward-looking" in w for w in meta["warnings"])
    assert any(f["code"] == "FORWARD_LOOKING_INPUT" for f in report.flags)
    assert report.grade in {"NEEDS WORK", "FLAGGED"}
    assert report.judgement in {"CAUTION", "FLAGGED"}
    assert report.display <= 59.0


def test_unified_png_scorecard_renders_wide_card(tmp_path):
    pytest.importorskip("matplotlib")
    Image = pytest.importorskip("PIL.Image")

    r, meta = load_returns(ROOT / "examples" / "strategy_beta.csv")
    report = score_unified(r, "crypto", meta=meta)
    out = tmp_path / "scorecard.png"

    render_unified_png(report, r, str(out), lang="en")

    assert out.exists()
    with Image.open(out) as img:
        assert img.size == (1600, 900)


def test_coerce_numeric_series_is_public():
    # Downstream consumers (the QuantScopeX Pro report path) import this public
    # wrapper; it must stay exported with the (series, is_percent) contract.
    from qsx_strategy_score.io import coerce_numeric_series

    vals, is_pct = coerce_numeric_series(pd.Series(["1.2%", "-0.5%", "0.3%"]))
    assert is_pct is True
    assert vals.round(4).tolist() == [0.012, -0.005, 0.003]

    vals2, is_pct2 = coerce_numeric_series(pd.Series([0.01, -0.02, 0.03]))
    assert is_pct2 is False
    assert vals2.round(4).tolist() == [0.01, -0.02, 0.03]


def test_cap_reasons_zh_mirrors_cap_reasons(tmp_path):
    # The bilingual web UI reads meta.cap_reasons_zh directly (push model). A
    # forward-looking filename forces a hard cap so cap_reasons is non-empty.
    path = tmp_path / "BTC_leaky_future_ma.csv"
    pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=400, freq="D"),
        "return": np.tile([0.02, -0.001, 0.015, 0.0], 100),
    }).to_csv(path, index=False)
    r, meta = load_returns(path)
    report = score_unified(r, "crypto", meta=meta)

    en = report.meta["cap_reasons"]
    zh = report.meta["cap_reasons_zh"]
    assert isinstance(zh, list)
    assert len(zh) == len(en)
    assert len(zh) > 0  # this strategy is capped
    # zh must be a real localization (contains CJK), not an English passthrough
    assert any(any("一" <= ch <= "鿿" for ch in s) for s in zh)


def test_degenerate_series_metrics_abstain():
    # A near-constant return path (interpolated / stale equity, a fixed coupon)
    # has a ~1e-19 std, NOT exactly 0. The dispersion guards must abstain rather
    # than emit a ~1e15 Sharpe / PSR=1.0 / DSR at the trial-budget ceiling. sharpe
    # already guarded with sd<1e-12; psr/dsr_stats/return_autocorr must match it.
    from qsx_strategy_score import metrics

    for series in (
        pd.Series([0.001] * 300),                                              # exactly constant
        pd.Series([0.001 + (1e-19 if i % 2 else -1e-19) for i in range(300)]),  # float-noise std
    ):
        assert metrics.sharpe(series, 252) == 0.0
        assert metrics.return_autocorr(series) == 0.0
        assert np.isnan(metrics.psr(series))
        assert metrics.dsr_stats(series) is None
