"""Command-line entry point: `qsx-score path/to/strategy.csv`.

One product: upload a strategy CSV -> it auto-detects the asset you traded from
the bundled library (or you pass --asset / --benchmark) -> scores it on the
unified 4-question card (return quality, overfit-risk detection, drawdown risk, and the
skill-vs-luck edge vs hold/random)."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import __version__, build_triage_diagnostics, load_returns, score_unified
from . import assets as asset_lib
from .asset_library import detect_asset, asset_close
from .io import load_prices
from .metrics import benchmark_compare, monte_carlo
from .profiles import PROFILE_NAMES
from .report import render_free_pdf, render_unified_text, render_unified_png
from .i18n import SUPPORTED_LANGS, normalize_lang


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(
        prog="qsx-score",
        description="Score a trading strategy from a single returns/equity/trade CSV "
                    "(overfitting-aware, skill-vs-luck).",
    )
    p.add_argument("csv", nargs="?", default=None,
                   help="CSV with a date column + a returns/equity column (or a trade log)")
    p.add_argument("--profile", default="other", choices=PROFILE_NAMES,
                   help="asset-class calibration profile (default: other)")
    p.add_argument("--input-type", default="auto", choices=["auto", "returns", "equity", "trade_log"],
                   dest="input_type", help="override returns/equity auto-detection")
    p.add_argument("--lang", default="en", choices=SUPPORTED_LANGS,
                   help="output language (default: en)")
    p.add_argument("--column", default=None, help="value column name (if auto-pick is wrong)")
    p.add_argument("--date-column", default=None, dest="date_column", help="date column name")
    p.add_argument("--benchmark", default=None, metavar="CSV",
                   help="asset price/K-line CSV for the 'vs Buy & Hold / random' comparison")
    p.add_argument("--benchmark-column", default=None, dest="benchmark_column",
                   help="price column name in the benchmark CSV (default: auto/close)")
    p.add_argument("--asset", default=None,
                   help="force a bundled asset key for the edge comparison (e.g. BTC, ETH, SPY). "
                        "See --list-assets.")
    p.add_argument("--no-auto-asset", action="store_true", dest="no_auto_asset",
                   help="disable automatic asset detection from the strategy returns/filename")
    p.add_argument("--list-assets", action="store_true", dest="list_assets",
                   help="list the bundled asset library and exit")
    p.add_argument("--n-trials", default=1, type=int, dest="n_trials",
                   help="how many strategy/parameter trials you searched before picking this curve "
                        "(applies a multiple-testing penalty)")
    p.add_argument("--out", default=None, metavar="PNG", help="write a shareable PNG report card here")
    p.add_argument("--pdf", default=None, metavar="PDF", help="write a three-page free diagnostic PDF here")
    p.add_argument("--json", default=None, metavar="JSON", help="write the report JSON here")
    p.add_argument("--version", action="version", version=f"qsx-score {__version__}")
    a = p.parse_args(argv)
    lang = normalize_lang(a.lang)

    if a.list_assets:
        avail = set(asset_lib.available_keys())
        mani = asset_lib.load_manifest()
        through = f", data through ~{mani.get('last_refreshed', '?')[:10]}" if mani else ""
        print(f"bundled asset library ({len(avail)}/{len(asset_lib.ASSETS)} downloaded){through}:")
        for ast in asset_lib.ASSETS:
            mark = "✓" if ast.key in avail else " "
            print(f"  {mark} {ast.key:6s} {ast.asset_class:9s} {ast.name}")
        print("\ndownload / refresh:  python -m qsx_strategy_score.assets")
        return 0

    if not a.csv:
        print("error: a strategy CSV is required (or use --list-assets).", file=sys.stderr)
        return 2

    try:
        r, meta = load_returns(a.csv, input_type=a.input_type,
                               column=a.column, date_column=a.date_column)
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 2

    bench_cmp = None
    detection = None
    if a.benchmark:
        try:
            px = load_prices(a.benchmark, column=a.benchmark_column)
            bench_cmp = benchmark_compare(r, px)
            if bench_cmp is None:
                print("warning: benchmark prices do not overlap the strategy dates.", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"warning: could not load benchmark: {e}", file=sys.stderr)
    elif a.asset:
        px = asset_close(a.asset)
        if px is None:
            print(f"warning: asset '{a.asset}' not in the local library — run "
                  f"`python -m qsx_strategy_score.assets --keys {a.asset}`, or use --benchmark.",
                  file=sys.stderr)
        else:
            bench_cmp = benchmark_compare(r, px)
            if bench_cmp is None:
                print(f"warning: '{a.asset}' prices do not overlap the strategy dates.", file=sys.stderr)
    elif not a.no_auto_asset:
        try:
            detection = detect_asset(r, filename=a.csv)
        except Exception:  # noqa: BLE001
            detection = None
        if detection is not None and detection.best is not None \
                and detection.confidence in ("high", "medium"):
            px = asset_close(detection.best.key)
            if px is not None:
                bench_cmp = benchmark_compare(r, px)

    report = score_unified(r, a.profile, meta=meta, benchmark=bench_cmp, n_trials=a.n_trials)
    triage = build_triage_diagnostics(r, report, meta=meta, benchmark=bench_cmp, lang=lang).to_dict()
    print(render_unified_text(report, lang=lang, triage=triage))

    if detection is not None:
        if detection.best is not None:
            b = detection.best
            print(f"\n  \U0001F50D auto-detected asset: {b.key} ({b.name}) · confidence {detection.confidence}")
            alts = ", ".join(f"{m.key}({m.corr:+.2f})" for m in detection.alternatives[:3]
                             if m.corr == m.corr)
            if alts:
                print(f"     not right? try: {alts}  ·  override with  --asset KEY")
        else:
            print(f"\n  \U0001F50D no asset auto-detected — {detection.reason}")
            print("     pick one with  --asset KEY  (see --list-assets) or pass  --benchmark your_kline.csv")

    mc = monte_carlo(r, report.meta["ppy"])
    if mc:
        pp = ">99" if mc["prob_loss"] < 0.005 else f"{(1 - mc['prob_loss'])*100:.0f}"
        print(f"  Monte Carlo ({mc['n_sims']}x): CAGR 5-95% "
              f"{mc['cagr_p5']*100:.0f}%..{mc['cagr_p95']*100:.0f}%  ·  worst-5% MaxDD "
              f"{mc['maxdd_worst5']*100:.0f}%  ·  P(profit) {pp}%")

    for w in meta.get("warnings", []):
        print(f"  note: {w}", file=sys.stderr)

    if a.out:
        try:
            render_unified_png(
                report, r, a.out, bench=bench_cmp, lang=lang, triage=triage)
            print(f"\nwrote report card -> {a.out}")
        except Exception as e:  # noqa: BLE001
            print(f"warning: PNG not written: {e}", file=sys.stderr)
    if a.pdf:
        try:
            render_free_pdf(report, r, a.pdf, bench=bench_cmp, lang=lang, triage=triage)
            print(f"wrote free diagnostic PDF -> {a.pdf}")
        except Exception as e:  # noqa: BLE001
            print(f"warning: PDF not written: {e}", file=sys.stderr)
    if a.json:
        with open(a.json, "w") as f:
            out = report.to_dict()
            out["triage"] = triage
            out["lang"] = lang
            json.dump(out, f, indent=2, default=str, ensure_ascii=False)
        print(f"wrote report json -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
