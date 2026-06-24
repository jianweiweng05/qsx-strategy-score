"""Upload preflight checks for the free strategy triage.

The goal is to turn messy broker/export files into an explicit readiness result.
This module is intentionally metadata-only: it never returns uploaded rows or
cell values, only column names, counts, and safe diagnostics.
"""
from __future__ import annotations

import io
import re
from typing import Any, Optional

import numpy as np
import pandas as pd

from .io import InputError, normalize_columns, read_user_table


DATE_CANDIDATES = (
    "exit_date", "exit_dt", "exit_time", "close_time", "closed_time", "close_datetime",
    "date", "bar_dt", "datetime", "timestamp", "time", "entry_date", "entry_dt", "entry_time",
)
RETURN_CANDIDATES = (
    "return", "returns", "return_pct", "trade_return", "trade_return_pct",
    "strategy_ret", "strategy_return", "daily_ret", "daily_return", "ret", "ret_pct",
    "net_pnl_pct", "pnl_pct", "pnl", "profit_pct", "profit_ratio", "chg", "change",
)
EQUITY_CANDIDATES = ("equity", "nav", "balance", "cumulative_return", "cum_return", "value", "wealth")
PRICE_CANDIDATES = ("close", "adj_close", "price", "last", "settle")
POSITION_CANDIDATES = ("signal", "position", "qty", "quantity", "side")
TRADE_ID_CANDIDATES = ("trade_id", "order_id", "deal_id", "execution_id", "fill_id")

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"email|e_mail|mail", re.I)),
    ("phone", re.compile(r"phone|mobile|tel|whatsapp|wechat|weixin", re.I)),
    ("account", re.compile(r"account|acct|client|customer|user_id|uid|姓名|名字|客户|账户", re.I)),
    ("credential", re.compile(r"api[_-]?key|secret|token|password|private[_-]?key|mnemonic", re.I)),
    ("address", re.compile(r"wallet|address|addr|iban|swift", re.I)),
    ("note", re.compile(r"note|comment|remark|memo", re.I)),
)


def _issue(code: str, severity: str, message: str, field: Optional[str] = None) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "severity": severity, "message": message}
    if field:
        out["field"] = field
    return out


def _normalized_columns(df: pd.DataFrame) -> list[str]:
    return normalize_columns(list(df.columns))


def _first(cols: set[str], candidates: tuple[str, ...]) -> Optional[str]:
    for name in candidates:
        if name in cols:
            return name
    return None


def _numeric_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(values):
        return pd.to_numeric(values, errors="coerce")
    text = values.astype(str).str.strip()
    has_pct = text.str.endswith("%")
    text = text.str.replace("%", "", regex=False).str.replace(" ", "", regex=False)
    decimal_comma = text.str.match(r"^-?\d+,\d+$")
    if bool(decimal_comma.mean() > 0.5):
        text = text.str.replace(",", ".", regex=False)
    else:
        text = text.str.replace(",", "", regex=False)
    numeric = pd.to_numeric(text, errors="coerce")
    if bool(has_pct.mean() > 0.5):
        numeric = numeric / 100.0
    return numeric


def _detect_pii(df: pd.DataFrame) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    value_patterns: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
        ("credential", re.compile(r"(sk_live_|rk_live_|whsec_|api[_-]?key|secret|token)", re.I)),
        ("phone", re.compile(r"(?:\+?\d[\s().-]*){9,}")),
        ("wallet", re.compile(r"\b(?:0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{25,87})\b")),
    )
    for col in df.columns:
        found: str | None = None
        for kind, pattern in _PII_PATTERNS:
            if pattern.search(col):
                found = kind
                break
        normalized_col = str(col).lower()
        structural = any(token in normalized_col for token in (
            "date", "time", "timestamp", "dt", "entry", "exit", "open", "close",
            "return", "ret", "pnl", "price", "equity", "nav", "balance", "qty", "quantity",
        ))
        if found is None and not structural and not pd.api.types.is_numeric_dtype(df[col]):
            sample = " ".join(df[col].dropna().astype(str).head(50).tolist())
            for kind, pattern in value_patterns:
                if pattern.search(sample):
                    found = kind
                    break
        if found is not None:
            findings.append({"column": col, "kind": found})
    return findings


def _timezone_note(raw_dates: pd.Series, parsed: pd.Series) -> tuple[str, Optional[dict[str, Any]]]:
    raw = raw_dates.dropna().astype(str).head(200)
    has_offset = bool(raw.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", regex=True).any())
    if has_offset:
        return "explicit", None
    if parsed.dropna().empty:
        return "unknown", None
    return "naive_local", _issue(
        "timezone_assumption",
        "warning",
        "Time column has no timezone offset. The audit will treat timestamps as local/export time and use the observed date order; choose the traded asset/timezone if this changes daily boundaries.",
    )


def _return_unit_hint(values: pd.Series) -> Optional[str]:
    numeric = _numeric_series(values).replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if numeric.empty:
        return None
    q95 = float(numeric.abs().quantile(0.95))
    if q95 > 2.0:
        return "percent"
    if q95 <= 1.0:
        return "decimal"
    return "ambiguous"


def _detect_shape(cols: set[str]) -> str:
    date_col = _first(cols, DATE_CANDIDATES)
    return_col = _first(cols, RETURN_CANDIDATES)
    equity_col = _first(cols, EQUITY_CANDIDATES)
    price_col = _first(cols, PRICE_CANDIDATES)
    position_col = _first(cols, POSITION_CANDIDATES)
    entry_col = _first(cols, ("entry_date", "entry_dt", "entry_time", "open_date", "open_time"))
    exit_col = _first(cols, DATE_CANDIDATES)
    if (entry_col and exit_col and return_col) or (exit_col and return_col and _first(cols, POSITION_CANDIDATES)):
        return "trade_log"
    if date_col and equity_col:
        return "equity"
    if date_col and return_col:
        return "returns"
    if date_col and price_col and position_col:
        return "signal_price_preview"
    return "unknown"


def preflight_report_upload(raw: bytes, filename: Optional[str] = None,
                            asset_class: str = "auto") -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    fixes: list[str] = []
    details: dict[str, Any] = {
        "filename": filename or "",
        "bytes": len(raw),
        "rows": 0,
        "columns": [],
        "recognized": {},
        "time": {},
        "privacy": {"pii_columns": [], "dropped_by_engine": True},
    }

    try:
        df = read_user_table(io.BytesIO(raw), filename=filename)
    except InputError as e:
        return {
            "status": "blocked",
            "ready": False,
            "issues": [_issue("parse_error", "blocker", str(e))],
            "fixes": [],
            "details": details,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "blocked",
            "ready": False,
            "issues": [_issue("parse_error", "blocker", f"Could not read the strategy file: {e}")],
            "fixes": [],
            "details": details,
        }

    df = df.copy()
    original_columns = [str(c).strip() for c in df.columns]
    df.columns = _normalized_columns(df)
    cols = set(df.columns)
    details["rows"] = int(len(df))
    details["columns"] = df.columns.tolist()
    if original_columns != details["columns"]:
        fixes.append("Normalized column names for parsing.")

    pii = _detect_pii(df)
    details["privacy"]["pii_columns"] = pii
    if pii:
        issues.append(_issue(
            "pii_columns",
            "warning",
            "Potential personal/account fields were detected. They are not needed for scoring and are ignored by the audit engine.",
        ))

    date_col = _first(cols, DATE_CANDIDATES)
    return_col = _first(cols, RETURN_CANDIDATES)
    equity_col = _first(cols, EQUITY_CANDIDATES)
    price_col = _first(cols, PRICE_CANDIDATES)
    position_col = _first(cols, POSITION_CANDIDATES)
    trade_id_col = _first(cols, TRADE_ID_CANDIDATES)
    details["recognized"] = {
        "date": date_col,
        "return": return_col,
        "equity": equity_col,
        "price": price_col,
        "position": position_col,
        "trade_id": trade_id_col,
    }

    detected = _detect_shape(cols)
    details["detected_input_type"] = detected

    if date_col is None:
        issues.append(_issue(
            "missing_time",
            "blocker",
            "No usable time/date column was detected. Include a column such as date, timestamp, exit_time, or exit_date.",
        ))
    else:
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce", utc=False)
        valid_dates = int(parsed_dates.notna().sum())
        duplicate_dates = int(parsed_dates.dropna().duplicated().sum())
        tz_status, tz_issue = _timezone_note(df[date_col], parsed_dates)
        if tz_issue:
            issues.append(tz_issue)
        details["time"] = {
            "column": date_col,
            "valid": valid_dates,
            "invalid": int(len(df) - valid_dates),
            "duplicates": duplicate_dates,
            "timezone": tz_status,
            "start": str(parsed_dates.dropna().min()) if valid_dates else None,
            "end": str(parsed_dates.dropna().max()) if valid_dates else None,
        }
        if valid_dates == 0:
            issues.append(_issue("bad_time", "blocker", f"Column `{date_col}` could not be parsed as dates.", date_col))
        elif valid_dates < max(2, int(len(df) * 0.8)):
            issues.append(_issue("many_bad_times", "blocker", f"Too many rows in `{date_col}` have invalid dates.", date_col))
        if duplicate_dates:
            issues.append(_issue(
                "duplicate_times",
                "warning",
                f"{duplicate_dates} rows share a timestamp. Same-timestamp trade returns will be compounded into one bar for path analysis.",
                date_col,
            ))

    if detected == "unknown" and not ((date_col and return_col) or (date_col and equity_col) or (price_col and position_col)):
        issues.append(_issue(
            "unknown_shape",
            "blocker",
            "Could not identify a supported shape: date+return, date+equity, signal+price, or trade log with exit/entry time and PnL.",
        ))

    if return_col is not None:
        unit = _return_unit_hint(df[return_col])
        details["recognized"]["return_unit"] = unit
        numeric = _numeric_series(df[return_col])
        if numeric.notna().sum() < max(2, int(len(df) * 0.6)):
            issues.append(_issue("bad_returns", "blocker", f"Column `{return_col}` is not mostly numeric.", return_col))
        if unit == "percent":
            fixes.append(f"Detected `{return_col}` as percent-style returns and will scale it.")
        elif unit == "ambiguous":
            issues.append(_issue(
                "ambiguous_return_units",
                "warning",
                f"Return units in `{return_col}` look ambiguous. Values around 1-2 can mean 1-2% or 100-200%; review before trusting the report.",
                return_col,
            ))

    blockers = [i for i in issues if i["severity"] == "blocker"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    status = "blocked" if blockers else "warning" if warnings else "ready"
    return {
        "status": status,
        "ready": not blockers,
        "issues": issues,
        "fixes": fixes,
        "details": details,
    }


def preflight_score_upload(raw: bytes, filename: Optional[str] = None,
                           input_type: str = "auto") -> dict[str, Any]:
    """Shared data-cleaning preflight for the free scorer.

    It intentionally uses ``load_returns``: the free score and its preflight must
    accept/reject the exact same cleaned input path.
    """
    from .io import load_returns

    base = preflight_report_upload(raw, filename=filename, asset_class="auto")
    try:
        returns, meta = load_returns(io.BytesIO(raw), filename=filename, input_type=input_type or "auto")
    except InputError as e:
        return {
            "status": "blocked",
            "ready": False,
            "issues": [_issue("engine_reject", "blocker", str(e))],
            "fixes": base.get("fixes", []),
            "details": base.get("details", {}),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "status": "blocked",
            "ready": False,
            "issues": [_issue("engine_reject", "blocker", f"Could not build a clean return path: {e}")],
            "fixes": base.get("fixes", []),
            "details": base.get("details", {}),
        }

    details = dict(base.get("details") or {})
    details["bundle"] = {
        "input_type": meta.get("input_type"),
        "observations": int(len(returns.dropna())),
        "trade_rows": int(meta.get("n_trades") or 0),
        "periods_per_year": int(float(meta.get("ppy") or 0)),
        "asset_class": None,
    }
    details["time"] = {
        "column": meta.get("date_column"),
        "valid": int(meta.get("n") or len(returns.dropna())),
        "invalid": int(meta.get("n_dropped") or 0),
        "duplicates": int(base.get("details", {}).get("time", {}).get("duplicates") or 0),
        "timezone": base.get("details", {}).get("time", {}).get("timezone"),
        "start": meta.get("start"),
        "end": meta.get("end"),
    }
    if meta.get("n_ignored_event_rows"):
        details["time"]["ignored_event_rows"] = int(meta.get("n_ignored_event_rows") or 0)
    issues = [i for i in base.get("issues", []) if i.get("severity") != "blocker"]
    if len(returns.dropna()) < 3:
        issues.append(_issue("short_observations", "blocker", "Need at least 3 usable observations after cleaning."))
    blockers = [i for i in issues if i.get("severity") == "blocker"]
    warnings_out = list(meta.get("warnings") or [])
    fixes = list(base.get("fixes") or [])
    for warning in warnings_out:
        if "read as percent" in warning or "parsed as percent" in warning:
            fixes.append("Return units were standardized.")
        elif "dropped" in warning:
            fixes.append("Rows with invalid dates/values were removed.")
        elif "auto-detected" in warning:
            fixes.append("Input structure was detected automatically.")
    return {
        "status": "blocked" if blockers else "warning" if issues else "ready",
        "ready": not blockers,
        "issues": issues,
        "fixes": fixes,
        "details": details,
    }
