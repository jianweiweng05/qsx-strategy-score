"""Generate README scorecard assets from the real PNG renderer.

This script keeps the public screenshots in sync with the product output:

    python scripts/generate_readme_assets.py

It intentionally uses only local example CSVs and synthetic benchmark curves, so
refreshing README assets does not require network access or a bundled market
data directory.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qsx_strategy_score import build_triage_diagnostics, load_returns, score_unified
from qsx_strategy_score.metrics import benchmark_compare
from qsx_strategy_score.report import render_unified_png


ASSET_DIR = ROOT / "assets" / "readme"
EXAMPLE_DIR = ROOT / "examples"


def _synthetic_close(returns: pd.Series, *, scale: float = 1.0, drift: float = 0.0,
                     mode: str = "scaled") -> pd.Series:
    """Create a deterministic benchmark close path from a local return series."""
    if mode == "wave":
        n = len(returns)
        wave = np.sin(np.linspace(0.0, 10.0 * np.pi, n))
        wave += 0.45 * np.cos(np.linspace(0.0, 23.0 * np.pi, n))
        wave = wave / max(float(np.std(wave)), 1e-12)
        bench_returns = pd.Series(drift + scale * wave, index=returns.index).clip(-0.08, 0.08)
    else:
        bench_returns = returns.astype(float) * scale + drift
    close = 100.0 * (1.0 + bench_returns).cumprod()
    close.index = returns.index
    close.name = "close"
    return close


def _render_card(example: str, out_name: str, *,
                 benchmark_scale: float | None = None,
                 benchmark_drift: float = 0.0,
                 benchmark_mode: str = "scaled") -> Path:
    returns, meta = load_returns(EXAMPLE_DIR / example)
    benchmark = None
    if benchmark_scale is not None:
        benchmark = benchmark_compare(
            returns,
            _synthetic_close(
                returns,
                scale=benchmark_scale,
                drift=benchmark_drift,
                mode=benchmark_mode,
            ),
        )
    report = score_unified(returns, "crypto", meta=meta, benchmark=benchmark)
    triage = build_triage_diagnostics(
        returns,
        report,
        meta=meta,
        benchmark=benchmark,
        lang="en",
    ).to_dict()
    out = ASSET_DIR / out_name
    render_unified_png(
        report,
        returns,
        str(out),
        cta="quantscopex.com/report",
        bench=benchmark,
        lang="en",
        triage=triage,
    )
    print(f"wrote {out.relative_to(ROOT)}")
    return out


def _compose_overview(cards: list[Path], out_path: Path) -> None:
    from PIL import Image

    loaded = [Image.open(p).convert("RGB") for p in cards]
    thumb_w = 800
    thumb_h = 450
    gap = 38
    pad = 38
    bg = "#070d14"
    sheet = Image.new("RGB", (pad * 2 + thumb_w * 2 + gap, pad * 2 + thumb_h * 2 + gap), bg)
    positions = [
        (pad, pad),
        (pad + thumb_w + gap, pad),
        (pad, pad + thumb_h + gap),
        (pad + thumb_w + gap, pad + thumb_h + gap),
    ]
    for im, pos in zip(loaded, positions):
        sheet.paste(im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), pos)
    sheet.save(out_path)
    print(f"wrote {out_path.relative_to(ROOT)}")


def _compose_stack(cards: list[Path], out_path: Path) -> None:
    from PIL import Image

    loaded = [Image.open(p).convert("RGB") for p in cards]
    card_w = 1600
    card_h = 900
    gap = 50
    pad = 50
    bg = "#070d14"
    sheet = Image.new("RGB", (card_w + pad * 2, card_h * len(loaded) + gap * (len(loaded) - 1) + pad * 2), bg)
    y = pad
    for im in loaded:
        sheet.paste(im.resize((card_w, card_h), Image.Resampling.LANCZOS), (pad, y))
        y += card_h + gap
    sheet.save(out_path)
    print(f"wrote {out_path.relative_to(ROOT)}")


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    cards = [
        _render_card(
            "sample_returns.csv",
            "sample-card-real-edge.png",
            benchmark_scale=0.004,
            benchmark_drift=0.0006,
            benchmark_mode="wave",
        ),
        _render_card(
            "strategy_beta.csv",
            "sample-card-beta-trap-clean.png",
            benchmark_scale=1.0,
        ),
        _render_card(
            "sample_flagged.csv",
            "sample-card-flagged-clean.png",
            benchmark_scale=0.2,
        ),
        _render_card(
            "strategy_alpha.csv",
            "sample-card-benchmark-needed.png",
        ),
    ]
    _compose_overview(cards, ASSET_DIR / "sample-scorecard-overview.png")
    _compose_stack(cards, ASSET_DIR / "sample-scorecard-stack.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
