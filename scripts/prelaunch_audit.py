from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
import multiprocessing as mp
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Optional private audit roots. Public runs default to repository examples only.
#   QSX_AUDIT_QSX_SCORE_DIR=/path/to/internal/qsx-score
#   QSX_AUDIT_DATA_DIR=/path/to/private/csvs
def _optional_env_path(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    return Path(raw).expanduser()


EXTERNAL_QSX_SCORE = _optional_env_path("QSX_AUDIT_QSX_SCORE_DIR")
EXTERNAL_DATA = _optional_env_path("QSX_AUDIT_DATA_DIR")

sys.path.insert(0, str(ROOT))

from qsx_strategy_score import build_triage_diagnostics, load_returns, score_unified
from qsx_strategy_score.asset_library import asset_close, detect_asset
from qsx_strategy_score.assets import ASSET_BY_KEY
from qsx_strategy_score.i18n import SUPPORTED_LANGS
from qsx_strategy_score.metrics import benchmark_compare, monte_carlo
from qsx_strategy_score.overlay_client import (
    normalize_daily_returns,
    run_overlay_preview,
    trade_log_to_daily_overlay_returns,
)
from qsx_strategy_score.report import render_unified_png, render_unified_text


_WORKER_OUT_DIR: Path | None = None
_WORKER_PNG_IDS: set[str] = set()
_WORKER_ONLINE_OVERLAY_IDS: set[str] = set()
_WORKER_MC_IDS: set[str] = set()


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def _asset_from_filename(path: Path) -> str | None:
    tokens = re.split(r"[^A-Za-z0-9]+", path.stem.upper())
    best = None
    for tok in tokens:
        if tok in ASSET_BY_KEY:
            best = tok
            break
        m = re.match(r"^([A-Z]+)(?:\d+[HDWM]|USDT|USD)$", tok)
        if m and m.group(1) in ASSET_BY_KEY:
            best = m.group(1)
            break
    return best


def _profile_for_asset(asset_key: str | None, source: str, path: Path, meta: dict | None = None) -> str:
    if asset_key and asset_key in ASSET_BY_KEY:
        return ASSET_BY_KEY[asset_key].profile
    name = str(path).upper()
    if source in {"desktop_data", "external_data"}:
        sym = str((meta or {}).get("symbol") or "").upper()
        if sym in ASSET_BY_KEY:
            return ASSET_BY_KEY[sym].profile
    if any(x in name for x in ("BTC", "ETH")):
        return "crypto"
    if any(x in name for x in ("SOL", "DOGE", "ADA", "AVAX", "XRP", "BNB", "LINK", "DOT", "LTC", "TRX", "BCH", "XLM", "ATOM", "UNI", "NEAR", "APT", "ARB", "OP", "INJ", "SUI", "ETC")):
        return "altcoin"
    if any(x in name for x in ("CSI300", "A_SHARE", "SPY", "QQQ", "NDX", "SPX", "INDEX", "EQUITY")):
        return "stock_index"
    return "other"


def discover_inputs(limit: int | None = None) -> list[dict]:
    rows: list[dict] = []
    for p in sorted((ROOT / "examples").glob("*.csv")):
        rows.append({
            "source": "examples",
            "group": "examples",
            "path": str(p),
            "name": p.stem,
            "expected_input": "auto",
        })
    if EXTERNAL_QSX_SCORE and EXTERNAL_QSX_SCORE.exists():
        for p in sorted((EXTERNAL_QSX_SCORE / "reports").glob("*/returns/*.csv")):
            rows.append({
                "source": "external_qsx_score",
                "group": p.parents[1].name,
                "path": str(p),
                "name": p.stem,
                "expected_input": "returns",
            })
    if EXTERNAL_DATA and EXTERNAL_DATA.exists():
        for p in sorted(EXTERNAL_DATA.glob("*.csv")):
            rows.append({
                "source": "external_data",
                "group": "external_data",
                "path": str(p),
                "name": p.stem,
                "expected_input": "auto",
            })
    return rows[:limit] if limit else rows


def _load_overlay_series(path: Path, returns: pd.Series, meta: dict) -> pd.Series:
    if meta.get("input_type") == "trade_log" or meta.get("caliber") == "closed_trade":
        return trade_log_to_daily_overlay_returns(path, filename=str(path))
    return returns


def _collect_subscores(report) -> dict[str, float | None]:
    return {
        "return_quality": _safe_float(report.return_quality.value),
        "credibility": _safe_float(report.credibility.value),
        "drawdown_risk": _safe_float(report.risk.value),
        "edge_score": _safe_float(report.edge.value) if report.edge is not None else None,
    }


def _safe_id(item: dict) -> str:
    raw = f"{item.get('source','')}_{item.get('group','')}_{Path(item.get('path','')).stem}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)[:180]


def _init_worker(out_dir: str, png_ids: set[str], online_overlay_ids: set[str], mc_ids: set[str]) -> None:
    global _WORKER_OUT_DIR, _WORKER_PNG_IDS, _WORKER_ONLINE_OVERLAY_IDS, _WORKER_MC_IDS
    _WORKER_OUT_DIR = Path(out_dir)
    _WORKER_PNG_IDS = set(png_ids)
    _WORKER_ONLINE_OVERLAY_IDS = set(online_overlay_ids)
    _WORKER_MC_IDS = set(mc_ids)


def _score_one_worker(item: dict) -> tuple[dict, dict | None]:
    assert _WORKER_OUT_DIR is not None
    return _score_one(item, _WORKER_OUT_DIR, _WORKER_PNG_IDS, _WORKER_ONLINE_OVERLAY_IDS, _WORKER_MC_IDS)


def _score_one(
    item: dict,
    out_dir: Path,
    png_ids: set[str],
    online_overlay_ids: set[str],
    mc_ids: set[str],
) -> tuple[dict, dict | None]:
    path = Path(item["path"])
    item_id = _safe_id(item)
    started = time.time()
    row: dict[str, Any] = {
        **item,
        "item_id": item_id,
        "ok": False,
        "error": "",
        "elapsed_sec": None,
    }
    detail: dict[str, Any] | None = None
    try:
        r, meta = load_returns(path)
        detection = detect_asset(r, filename=str(path), symbol=meta.get("symbol"))
        asset_key = detection.best.key if detection.best is not None else _asset_from_filename(path)
        profile = _profile_for_asset(asset_key, item["source"], path, meta)
        bench = None
        benchmark_status = "not_available"
        if asset_key:
            px = asset_close(asset_key)
            if px is not None:
                bench = benchmark_compare(r, px)
                benchmark_status = "ok" if bench is not None else "no_overlap"
            else:
                benchmark_status = "asset_not_downloaded"
        report = score_unified(r, profile, meta=meta, benchmark=bench)
        triage = build_triage_diagnostics(r, report, meta=meta, benchmark=bench, lang="zh").to_dict()
        mc = monte_carlo(r, report.meta["ppy"]) if item_id in mc_ids else None
        subs = _collect_subscores(report)

        overlay_status = "not_run"
        overlay_rows = None
        overlay_error = ""
        overlay_sha = ""
        overlay_online_status = "not_run"
        overlay_online_error = ""
        overlay_online_keys = ""
        try:
            overlay_series = _load_overlay_series(path, r, meta)
            normalized = normalize_daily_returns(overlay_series)
            overlay_status = "normalized"
            overlay_rows = normalized.rows
            overlay_sha = normalized.sha256
            if item_id in online_overlay_ids:
                try:
                    payload = run_overlay_preview(overlay_series, lang="zh", timeout=30)
                    overlay_online_status = "ok"
                    overlay_online_keys = ",".join(sorted(str(k) for k in payload.keys()))
                    (out_dir / "overlay_online").mkdir(exist_ok=True)
                    with open(out_dir / "overlay_online" / f"{item_id}.json", "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
                except Exception as e:  # noqa: BLE001
                    overlay_online_status = "error"
                    overlay_online_error = str(e)
        except Exception as e:  # noqa: BLE001
            overlay_status = "error"
            overlay_error = str(e)

        lang_status = {}
        lang_lengths = {}
        for lang in SUPPORTED_LANGS:
            try:
                txt = render_unified_text(report, lang=lang, triage=triage)
                lang_status[lang] = "ok"
                lang_lengths[lang] = len(txt)
            except Exception as e:  # noqa: BLE001
                lang_status[lang] = f"error: {e}"
                lang_lengths[lang] = None

        png_status = "not_sampled"
        png_error = ""
        png_path = ""
        if item_id in png_ids:
            try:
                png_dir = out_dir / "png_cards"
                png_dir.mkdir(exist_ok=True)
                png_path = str(png_dir / f"{item_id}.png")
                render_unified_png(report, r, png_path, bench=bench, lang="zh", triage=triage)
                png_status = "ok"
            except Exception as e:  # noqa: BLE001
                png_status = "error"
                png_error = str(e)

        flags = [f.get("code") for f in report.flags if f.get("code")]
        warn_flags = [f.get("code") for f in report.flags if f.get("severity") == "warn" and f.get("code")]
        cap_reasons = report.meta.get("cap_reasons") or []
        row.update({
            "ok": True,
            "input_type": meta.get("input_type"),
            "caliber": meta.get("caliber", ""),
            "value_column": meta.get("value_column"),
            "date_column": meta.get("date_column"),
            "symbol": meta.get("symbol", ""),
            "n": meta.get("n"),
            "n_dropped": meta.get("n_dropped"),
            "span_years": round(float(meta.get("span_years") or 0.0), 4),
            "bar_freq": meta.get("bar_freq"),
            "warnings_count": len(meta.get("warnings") or []),
            "warnings": " | ".join(meta.get("warnings") or []),
            "asset_key": asset_key or "",
            "asset_detection_confidence": detection.confidence,
            "asset_detection_via": detection.best.via if detection.best is not None else "",
            "asset_detection_reason": detection.reason,
            "profile": profile,
            "benchmark_status": benchmark_status,
            "benchmark_overlap_days": bench.get("overlap_days") if bench else None,
            "benchmark_cal_alpha": round(float(bench.get("cal_alpha")), 6) if bench else None,
            "benchmark_ret_capture": round(float(bench.get("ret_capture")), 6) if bench and _safe_float(bench.get("ret_capture")) is not None else None,
            "score": report.display,
            "grade": report.grade,
            "judgement": report.judgement,
            "tier": report.tier or "",
            "headline": report.headline,
            "headline_zh": report.meta.get("headline_zh", ""),
            "edge_light": report.lights.get("edge"),
            "sample_light": report.lights.get("sample"),
            "cagr": round(float(report.meta.get("cagr") or 0.0), 6),
            "effective_n": report.meta.get("effective_n"),
            "random_p": report.meta.get("random_p"),
            "cal_alpha": report.meta.get("cal_alpha"),
            "trial_budget": report.meta.get("trial_budget"),
            "capped": report.meta.get("capped"),
            "uncapped_score": report.meta.get("uncapped_score"),
            "cap_reasons": " | ".join(str(x) for x in cap_reasons),
            "flags": " | ".join(flags),
            "warn_flags": " | ".join(warn_flags),
            "triage_edge_persistence": (triage.get("edge_persistence") or {}).get("label"),
            "triage_evidence_confidence": (triage.get("evidence_confidence") or {}).get("level"),
            "triage_dependency_available": (triage.get("dependency_lite") or {}).get("available"),
            "triage_dependency_type": (triage.get("dependency_lite") or {}).get("type"),
            "overlay_status": overlay_status,
            "overlay_rows": overlay_rows,
            "overlay_sha256": overlay_sha,
            "overlay_error": overlay_error,
            "overlay_online_status": overlay_online_status,
            "overlay_online_error": overlay_online_error,
            "overlay_online_keys": overlay_online_keys,
            "lang_status": json.dumps(lang_status, ensure_ascii=False, sort_keys=True),
            "lang_lengths": json.dumps(lang_lengths, ensure_ascii=False, sort_keys=True),
            "png_status": png_status,
            "png_path": png_path,
            "png_error": png_error,
            "mc_prob_loss": round(float(mc.get("prob_loss")), 6) if mc else None,
            "mc_cagr_p5": round(float(mc.get("cagr_p5")), 6) if mc else None,
            "mc_maxdd_worst5": round(float(mc.get("maxdd_worst5")), 6) if mc else None,
            **subs,
        })
        detail = {
            "path": str(path),
            "meta": meta,
            "report": report.to_dict(),
            "triage": triage,
            "detection": detection.to_dict(),
            "benchmark": None if bench is None else {
                k: v for k, v in bench.items()
                if k not in {"strat_curve", "bnh_curve"}
            },
        }
    except Exception as e:  # noqa: BLE001
        row.update({"error": str(e)})
    finally:
        row["elapsed_sec"] = round(time.time() - started, 4)
    return row, detail


def _summarize(df: pd.DataFrame) -> dict[str, Any]:
    ok = df[df["ok"] == True].copy()  # noqa: E712
    failed = df[df["ok"] != True].copy()  # noqa: E712
    summary: dict[str, Any] = {
        "total_inputs": int(len(df)),
        "ok": int(len(ok)),
        "failed": int(len(failed)),
        "success_rate": round(float(len(ok) / len(df)), 6) if len(df) else 0.0,
    }
    for col in ["source", "group", "input_type", "grade", "judgement", "edge_light", "sample_light", "profile", "benchmark_status", "overlay_status", "overlay_online_status", "png_status"]:
        if col in df.columns:
            summary[f"{col}_counts"] = df[col].fillna("").astype(str).value_counts().to_dict()
    if len(ok):
        score = pd.to_numeric(ok["score"], errors="coerce")
        summary["score_distribution"] = {
            "mean": round(float(score.mean()), 4),
            "median": round(float(score.median()), 4),
            "p05": round(float(score.quantile(0.05)), 4),
            "p25": round(float(score.quantile(0.25)), 4),
            "p75": round(float(score.quantile(0.75)), 4),
            "p95": round(float(score.quantile(0.95)), 4),
            "min": round(float(score.min()), 4),
            "max": round(float(score.max()), 4),
        }
        summary["score_by_source"] = ok.groupby("source")["score"].agg(["count", "mean", "median", "min", "max"]).round(4).to_dict("index")
        summary["score_by_group"] = ok.groupby("group")["score"].agg(["count", "mean", "median", "min", "max"]).round(4).to_dict("index")
        summary["top_scores"] = ok.sort_values("score", ascending=False).head(20)[["source", "group", "name", "score", "grade", "judgement", "edge_light", "asset_key", "flags"]].to_dict("records")
        summary["bottom_scores"] = ok.sort_values("score", ascending=True).head(20)[["source", "group", "name", "score", "grade", "judgement", "edge_light", "asset_key", "flags"]].to_dict("records")
        flag_counter = Counter()
        for flags in ok["flags"].fillna("").astype(str):
            for code in [x.strip() for x in flags.split("|") if x.strip()]:
                flag_counter[code] += 1
        summary["flag_counts"] = dict(flag_counter.most_common())
        warning_counter = Counter()
        for warnings in ok["warnings"].fillna("").astype(str):
            for msg in [x.strip() for x in warnings.split("|") if x.strip()]:
                warning_counter[msg] += 1
        summary["loader_warning_counts_top20"] = dict(warning_counter.most_common(20))
        cap_counter = Counter()
        for reasons in ok["cap_reasons"].fillna("").astype(str):
            for msg in [x.strip() for x in reasons.split("|") if x.strip()]:
                cap_counter[msg] += 1
        summary["cap_reason_counts"] = dict(cap_counter.most_common())
    return summary


def _write_markdown(summary: dict[str, Any], out_dir: Path) -> None:
    lines: list[str] = []
    lines.append("# QSX Free Scorer Prelaunch Audit")
    lines.append("")
    lines.append(f"- Run time: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    lines.append(f"- Inputs tested: {summary['total_inputs']}")
    lines.append(f"- Success: {summary['ok']} ({summary['success_rate']:.2%})")
    lines.append(f"- Failed: {summary['failed']}")
    lines.append("")
    if "score_distribution" in summary:
        sd = summary["score_distribution"]
        lines.append("## Score Distribution")
        lines.append("")
        lines.append("| metric | value |")
        lines.append("| --- | ---: |")
        for k in ["mean", "median", "p05", "p25", "p75", "p95", "min", "max"]:
            lines.append(f"| {k} | {sd[k]} |")
        lines.append("")
    for key, title in [
        ("source_counts", "Sources"),
        ("group_counts", "Groups"),
        ("input_type_counts", "Input Types"),
        ("grade_counts", "Grades"),
        ("judgement_counts", "Judgements"),
        ("edge_light_counts", "Edge Lights"),
        ("benchmark_status_counts", "Benchmark Status"),
        ("overlay_status_counts", "Overlay Local Normalization"),
        ("overlay_online_status_counts", "Overlay Online Smoke"),
        ("png_status_counts", "PNG Card Sampling"),
    ]:
        data = summary.get(key) or {}
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| value | count |")
        lines.append("| --- | ---: |")
        for k, v in data.items():
            lines.append(f"| {k or '(blank)'} | {v} |")
        lines.append("")
    for key, title in [
        ("flag_counts", "Flag Counts"),
        ("cap_reason_counts", "Cap Reasons"),
        ("loader_warning_counts_top20", "Loader Warnings Top 20"),
    ]:
        data = summary.get(key) or {}
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| code/message | count |")
        lines.append("| --- | ---: |")
        for k, v in data.items():
            lines.append(f"| {str(k).replace('|', '/')} | {v} |")
        lines.append("")
    for key, title in [("top_scores", "Top 20"), ("bottom_scores", "Bottom 20")]:
        rows = summary.get(key) or []
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| score | grade | source | group | name | edge | asset | flags |")
        lines.append("| ---: | --- | --- | --- | --- | --- | --- | --- |")
        for r in rows:
            lines.append(
                f"| {r.get('score')} | {r.get('grade')} | {r.get('source')} | {r.get('group')} | "
                f"{r.get('name')} | {r.get('edge_light')} | {r.get('asset_key')} | {str(r.get('flags','')).replace('|','/')} |"
            )
        lines.append("")
    (out_dir / "audit_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(ROOT / "reports" / f"prelaunch_audit_{time.strftime('%Y%m%d_%H%M%S')}"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--png-samples", type=int, default=24)
    parser.add_argument("--mc-samples", type=int, default=80)
    parser.add_argument("--overlay-online-samples", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = discover_inputs(limit=args.limit)

    # Deterministic, coverage-oriented samples for PNG and hosted overlay smoke.
    ids = [_safe_id(x) for x in inputs]
    png_ids = set(ids[: max(0, args.png_samples // 3)])
    png_ids |= set(ids[len(ids) // 2: len(ids) // 2 + max(0, args.png_samples // 3)])
    png_ids |= set(ids[-max(0, args.png_samples - len(png_ids)):])
    mc_ids = set(ids[: max(0, args.mc_samples // 3)])
    mc_ids |= set(ids[len(ids) // 2: len(ids) // 2 + max(0, args.mc_samples // 3)])
    mc_ids |= set(ids[-max(0, args.mc_samples - len(mc_ids)):])
    external_data_ids = [_safe_id(x) for x in inputs if x["source"] in {"desktop_data", "external_data"}]
    overlay_online_ids = set(external_data_ids[: args.overlay_online_samples])

    rows = []
    details = []
    started = time.time()
    if args.workers <= 1:
        for i, item in enumerate(inputs, start=1):
            row, detail = _score_one(item, out_dir, png_ids, overlay_online_ids, mc_ids)
            rows.append(row)
            if detail is not None:
                details.append(detail)
            if args.progress_every and (i % args.progress_every == 0 or i == len(inputs)):
                ok = sum(1 for r in rows if r.get("ok"))
                print(f"[{i}/{len(inputs)}] ok={ok} failed={i-ok} elapsed={time.time()-started:.1f}s", flush=True)
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(
            processes=args.workers,
            initializer=_init_worker,
            initargs=(str(out_dir), png_ids, overlay_online_ids, mc_ids),
        ) as pool:
            for i, (row, detail) in enumerate(pool.imap_unordered(_score_one_worker, inputs, chunksize=4), start=1):
                rows.append(row)
                if detail is not None:
                    details.append(detail)
                if args.progress_every and (i % args.progress_every == 0 or i == len(inputs)):
                    ok = sum(1 for r in rows if r.get("ok"))
                    print(f"[{i}/{len(inputs)}] ok={ok} failed={i-ok} elapsed={time.time()-started:.1f}s", flush=True)

    df = pd.DataFrame(rows)
    results_path = out_dir / "audit_results.csv"
    df.to_csv(results_path, index=False)

    with open(out_dir / "audit_details_sample.json", "w", encoding="utf-8") as f:
        json.dump(details[:250], f, indent=2, ensure_ascii=False, default=str)

    summary = _summarize(df)
    summary["elapsed_sec"] = round(time.time() - started, 3)
    with open(out_dir / "audit_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    _write_markdown(summary, out_dir)
    print(json.dumps({
        "out_dir": str(out_dir),
        "results": str(results_path),
        "summary": str(out_dir / "audit_summary.json"),
        "markdown": str(out_dir / "audit_summary.md"),
        "total": len(df),
        "ok": int(df["ok"].sum()) if "ok" in df.columns else 0,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
