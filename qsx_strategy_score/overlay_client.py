"""Client for the QuantScopeX hosted crypto overlay preview.

The open-source scorer never ships the overlay series. It normalizes the user's
local upload into a daily date-return stream and sends only that minimal series
to the hosted preview endpoint.
"""
from __future__ import annotations

import hashlib
import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .io import (
    InputError,
    _coerce_numeric,
    _detect_trade_log,
    _event_entry_mask,
    _event_exit_mask,
    _match,
    _parse_dates,
    read_user_table,
)

DEFAULT_OVERLAY_PREVIEW_URL = "https://www.quantscopex.com/api/overlay/preview"
CLIENT_ID = "qsx-score-free/0.1.0"
SOURCE_ID = "github-open-source"
MIN_OVERLAY_PREVIEW_ROWS = 30


class OverlayPreviewError(RuntimeError):
    """Raised when the hosted overlay preview rejects or cannot process input."""


@dataclass
class NormalizedOverlayInput:
    csv: str
    sha256: str
    rows: int
    start: str
    end: str


def _date_key(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _round_trips_from_tv_event_log(df: pd.DataFrame, tl: dict) -> pd.DataFrame | None:
    event_col = tl.get("event_col")
    exit_mask = _event_exit_mask(df, event_col)
    entry_mask = _event_entry_mask(df, event_col)
    if exit_mask is None or entry_mask is None:
        return None
    trade_col = _match(list(df.columns), ("trade_number", "trade_id", "trade", "id"))
    if trade_col is None:
        return None

    dt = _parse_dates(df[tl["exit"]])
    pnl, parsed_as_pct = _coerce_numeric(df[tl["pnl"]])
    if tl.get("is_pct") and not parsed_as_pct:
        pnl = pnl / 100.0

    event_df = pd.DataFrame({
        "trade_id": df[trade_col].astype(str),
        "dt": dt,
        "ret": pnl,
        "is_entry": entry_mask,
        "is_exit": exit_mask,
    }).dropna(subset=["trade_id", "dt"])

    rows = []
    for _, group in event_df.groupby("trade_id", sort=False):
        entries = group[group["is_entry"]].sort_values("dt")
        exits = group[group["is_exit"]].sort_values("dt")
        if entries.empty or exits.empty:
            continue
        entry_row = entries.iloc[0]
        exit_row = exits.iloc[-1]
        if pd.isna(exit_row["ret"]):
            continue
        rows.append({
            "entry": entry_row["dt"],
            "exit": exit_row["dt"],
            "ret": float(exit_row["ret"]),
        })
    if not rows:
        return None
    return pd.DataFrame(rows)


def _reject_overlapping_trade_windows(work: pd.DataFrame) -> None:
    intervals = [
        (pd.Timestamp(row.entry), pd.Timestamp(row.exit))
        for row in work[["entry", "exit"]].itertuples(index=False)
    ]
    intervals.sort(key=lambda item: (item[0], item[1]))
    latest_end = intervals[0][1]
    for start_day, end_day in intervals[1:]:
        if start_day < latest_end:
            raise OverlayPreviewError(
                "Trade-log Overlay Preview does not support overlapping positions. "
                "Upload an equity curve or daily return series so the preview uses "
                "the aggregate strategy path."
            )
        if end_day > latest_end:
            latest_end = end_day


def trade_log_to_daily_overlay_returns(source, *, filename: str | None = None) -> pd.Series:
    """Expand a trade log into a continuous daily return path for overlay testing.

    The main free score deliberately treats trade logs as closed-trade samples.
    A risk overlay, however, acts through time. For preview only, we spread each
    trade's PnL geometrically across its entry-to-exit holding days and fill
    flat days with zero return.
    """
    try:
        df = read_user_table(source, filename=filename)
    except InputError as e:
        raise OverlayPreviewError(str(e)) from e
    tl = _detect_trade_log(df)
    if tl is None:
        raise OverlayPreviewError("Overlay preview could not detect a trade log.")
    tv_round_trips = None
    if tl.get("entry") is None and tl.get("tv_event_log"):
        tv_round_trips = _round_trips_from_tv_event_log(df, tl)
    if (tl.get("entry") is None or tl.get("exit") is None) and tv_round_trips is None:
        raise OverlayPreviewError("Trade-log overlay preview needs both entry and exit time columns.")
    if tl.get("pnl") is None:
        raise OverlayPreviewError(tl.get("reason") or "Trade-log overlay preview needs a percent/ratio PnL column.")

    if tv_round_trips is not None:
        work = tv_round_trips
    else:
        entry = _parse_dates(df[tl["entry"]])
        exit_ = _parse_dates(df[tl["exit"]])
        pnl, parsed_as_pct = _coerce_numeric(df[tl["pnl"]])
        if tl.get("is_pct") and not parsed_as_pct:
            pnl = pnl / 100.0
        work = pd.DataFrame({"entry": entry, "exit": exit_, "ret": pnl})
    work = work.dropna().sort_values("entry")
    work = work[work["exit"] >= work["entry"]]
    if len(work) < 3:
        raise OverlayPreviewError("Trade log has fewer than 3 valid entry/exit trades.")
    _reject_overlapping_trade_windows(work)

    rets = work["ret"].astype(float).to_numpy()
    rets = pd.Series(rets).clip(lower=-0.999).to_numpy()
    start = pd.to_datetime(work["entry"]).min().normalize()
    end = pd.to_datetime(work["exit"]).max().normalize()
    if pd.isna(start) or pd.isna(end) or end < start:
        raise OverlayPreviewError("Trade log has no usable date span for overlay preview.")

    daily_growth = pd.Series(1.0, index=pd.date_range(start, end, freq="D"))
    for (_, row), trade_ret in zip(work.iterrows(), rets):
        start_day = pd.Timestamp(row["entry"]).normalize()
        end_day = pd.Timestamp(row["exit"]).normalize()
        days = max(int((end_day - start_day).days) + 1, 1)
        daily_ret = (1.0 + float(trade_ret)) ** (1.0 / days) - 1.0
        daily_growth.loc[start_day:end_day] *= 1.0 + daily_ret

    out = daily_growth - 1.0
    out.name = "overlay_daily_return"
    return out


def normalize_daily_returns(returns: pd.Series, max_rows: int = 5000) -> NormalizedOverlayInput:
    """Convert arbitrary periodic returns into daily compounded returns.

    Intraday or trade-level returns are reduced locally before any network call:
    one row per calendar day, no filenames, no trade log columns, no strategy
    metadata.
    """
    if returns is None or len(returns) == 0:
        raise OverlayPreviewError("No returns available for overlay preview.")
    s = pd.Series(returns).dropna().astype(float)
    s = s[~s.index.isna()]
    arr = s.to_numpy(dtype=float)
    if not math.isfinite(float(arr.sum())):
        raise OverlayPreviewError("Returns contain non-finite values.")
    if (s <= -1.0).any():
        raise OverlayPreviewError("Returns contain a period <= -100%.")
    daily = (1.0 + s).groupby(pd.DatetimeIndex(s.index).normalize()).prod() - 1.0
    daily = daily.sort_index()
    if len(daily) < MIN_OVERLAY_PREVIEW_ROWS:
        raise OverlayPreviewError(f"Overlay preview needs at least {MIN_OVERLAY_PREVIEW_ROWS} daily return rows.")
    if len(daily) > max_rows:
        daily = daily.iloc[-max_rows:]

    lines = ["date,return"]
    for dt, ret in daily.items():
        value = float(ret)
        if not math.isfinite(value):
            raise OverlayPreviewError(f"Daily return on {_date_key(dt)} is not finite.")
        if value <= -1.0:
            raise OverlayPreviewError(f"Daily return on {_date_key(dt)} is <= -100%, so equity would be zero or negative.")
        lines.append(f"{_date_key(dt)},{value:.12g}")
    csv = "\n".join(lines) + "\n"
    sha = hashlib.sha256(csv.encode("utf-8")).hexdigest()
    return NormalizedOverlayInput(csv=csv, sha256=sha, rows=len(daily), start=_date_key(daily.index[0]), end=_date_key(daily.index[-1]))


def run_overlay_preview(
    returns: pd.Series,
    *,
    endpoint: str = DEFAULT_OVERLAY_PREVIEW_URL,
    timeout: int = 30,
    lang: str = "en",
) -> dict[str, Any]:
    normalized = normalize_daily_returns(returns)
    data = normalized.csv.encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "User-Agent": CLIENT_ID,
            "X-QSX-Client": CLIENT_ID,
            "X-QSX-Source": SOURCE_ID,
            "X-QSX-Lang": lang,
            "X-QSX-Input-SHA256": normalized.sha256,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise OverlayPreviewError(
                "Overlay Preview is temporarily rate-limited. Please wait a minute and try again."
            ) from e
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail")
        except Exception:  # noqa: BLE001
            detail = None
        raise OverlayPreviewError(detail or f"Overlay preview failed with HTTP {e.code}.") from e
    except Exception as e:  # noqa: BLE001
        raise OverlayPreviewError(f"Overlay preview request failed: {e}") from e

    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise OverlayPreviewError("Overlay preview returned an invalid response.")
    if payload.get("inputSha256") != normalized.sha256:
        raise OverlayPreviewError("Overlay preview checksum mismatch.")
    payload["_local"] = {
        "normalized_rows": normalized.rows,
        "normalized_start": normalized.start,
        "normalized_end": normalized.end,
        "input_sha256": normalized.sha256,
    }
    return payload
