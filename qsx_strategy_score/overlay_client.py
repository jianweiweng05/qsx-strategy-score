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

from ._version import __version__
from .metrics import account_return_grid_reason

DEFAULT_OVERLAY_PREVIEW_URL = "https://www.quantscopex.com/api/overlay/preview"
CLIENT_ID = f"qsx-score-free/{__version__}"
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


def trade_log_to_daily_overlay_returns(source, *, filename: str | None = None) -> pd.Series:
    """Closed trades cannot identify the account path needed by an overlay."""
    raise OverlayPreviewError(
        "Trade-log Overlay Preview is unavailable. Upload actual account daily "
        "returns or an equity curve; trade endpoints do not reveal drawdown."
    )


def normalize_daily_returns(returns: pd.Series, max_rows: int = 5000) -> NormalizedOverlayInput:
    """Convert arbitrary periodic returns into daily compounded returns.

    Intraday account returns are reduced locally before any network call:
    one row per calendar day, no filenames, no trade log columns, no strategy
    metadata.
    """
    if returns is None or len(returns) == 0:
        raise OverlayPreviewError("No returns available for overlay preview.")
    if returns.attrs.get("caliber") == "closed_trade" or returns.attrs.get("input_type") == "trade_log":
        raise OverlayPreviewError("Trade-log Overlay Preview is unavailable; upload account returns/NAV.")
    s = pd.Series(returns).astype(float)
    if not isinstance(s.index, pd.DatetimeIndex) or s.index.isna().any() or s.index.has_duplicates:
        raise OverlayPreviewError("Overlay needs unique, valid account-return timestamps.")
    if account_return_grid_reason(returns):
        raise OverlayPreviewError("INCOMPLETE_INTRADAY_RETURNS: provide complete account returns or observed NAV.")
    s.index = pd.to_datetime(s.index, utc=True).tz_localize(None)
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
            "X-QSX-Core-Version": __version__,
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
