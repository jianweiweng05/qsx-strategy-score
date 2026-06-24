"""Strategy upload ingestion.

Turns a user CSV/TSV/Excel upload into a clean periodic-returns Series plus a
`meta` dict.
Handles two input shapes (auto-detected, overridable):
  * returns : `date, return`
  * equity  : `date, equity`  (NAV / cumulative-return curve -> differenced)

Design rules baked in from the spec review:
  * ppy (annualization factor) is inferred from the DATA ONLY
    (observations / span_years); the asset-class profile never touches it.
  * the fragile "values in [-1, 1] => returns" heuristic is gone; detection
    uses sign, magnitude and level-autocorrelation, and REFUSES to guess when
    ambiguous (raises so the caller passes input_type explicitly).
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

import numpy as np
import pandas as pd

SECONDS_PER_YEAR = 365.25 * 86400.0

_DATE_HINTS = ("datetime", "date", "timestamp", "time", "dt", "bar")
_PRICE_HINTS = ("adj close", "adj_close", "close", "price", "last", "settle", "nav", "value")
_RETURN_HINTS = (
    "return", "returns", "return_pct", "ret", "ret_pct", "pnl_pct", "pnl",
    "profit_pct", "profit_ratio", "daily_ret", "daily_return", "strategy_ret",
    "strategy_return", "chg", "change",
)
_EQUITY_HINTS = ("equity", "nav", "balance", "cum", "value", "wealth", "capital", "curve")
_TEXT_ENCODINGS = ("utf-8-sig", "utf-16", "utf-16le", "gb18030", "latin1")
_TEXT_EXTENSIONS = (".csv", ".tsv", ".txt")
_EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm")
_SOURCE_FORWARD_MARKERS = ("leaky", "lookahead", "look_ahead", "future")
_COLUMN_FORWARD_PREFIXES = ("future_", "forward_", "target_", "next_")


class InputError(ValueError):
    """Raised when the uploaded file cannot be unambiguously interpreted."""


def normalize_column_name(column: object) -> str:
    """Stable, platform-tolerant schema key.

    Exports use names like ``Date/Time``, ``Net P&L %`` and ``Profit Ratio``.
    A single normalizer keeps scoring and preflight aligned.
    """
    value = str(column).strip().lower()
    value = value.replace("\ufeff", "")
    value = value.replace("（", "(").replace("）", ")").replace("％", "%")
    localized_replacements = (
        ("日期和时间", "datetime"),
        ("日期/时间", "datetime"),
        ("日期时间", "datetime"),
        ("交易编号", "trade_number"),
        ("交易号", "trade_number"),
        ("类型", "type"),
        ("信号", "signal"),
        ("方向", "direction"),
        ("价格", "price"),
        ("大小(数量)", "contracts"),
        ("大小(价值)", "position_value"),
        ("合约数", "contracts"),
        ("数量", "quantity"),
        ("净盈亏", "net_pnl"),
        ("净损益", "net_pnl"),
        ("净利润", "net_pnl"),
        ("有利波动", "run_up"),
        ("不利波动", "drawdown"),
        ("最大有利变动", "run_up"),
        ("最大不利变动", "drawdown"),
        ("累计", "cumulative"),
        ("百分比", "pct"),
        ("时间", "time"),
    )
    for src, dst in localized_replacements:
        value = value.replace(src, dst)
    value = value.replace("p&l", "pnl").replace("p/l", "pnl")
    value = value.replace("%", " pct ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    aliases = {
        "date_time": "datetime",
        "date_utc": "date",
        "time_utc": "time",
        "close_date": "exit_date",
        "close_time": "exit_time",
        "closing_time": "exit_time",
        "closed_time": "exit_time",
        "open_date": "entry_date",
        "open_time": "entry_time",
        "opening_time": "entry_time",
        "opened_time": "entry_time",
        "net_p_l": "net_pnl",
        "net_p_l_pct": "net_pnl_pct",
        "net_profit_pct": "net_pnl_pct",
        "profit_percent": "profit_pct",
        "pnl_percent": "pnl_pct",
        "pl_pct": "pnl_pct",
        "p_l_pct": "pnl_pct",
        "cum_profit": "cumulative_pnl",
        "cumulative_profit": "cumulative_pnl",
        "cumulative_pnl_pct": "cumulative_return",
        "portfolio_value": "equity",
        "portfolio_equity": "equity",
        "net_liquidation": "equity",
        "profit_ratio": "profit_ratio",
    }
    return aliases.get(value, value)


def normalize_columns(columns: list[object]) -> list[str]:
    names = [normalize_column_name(c) for c in columns]
    seen: dict[str, int] = {}
    out: list[str] = []
    for name in names:
        base = name or "column"
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return out


def _source_name(source, filename: Optional[str] = None) -> str:
    if filename:
        return str(filename)
    if isinstance(source, str):
        return source
    if hasattr(source, "__fspath__"):
        return str(source.__fspath__())
    name = getattr(source, "name", "")
    return str(name) if name else ""


def _extension(source, filename: Optional[str] = None) -> str:
    name = _source_name(source, filename).split("?", 1)[0].split("#", 1)[0].lower()
    for ext in _EXCEL_EXTENSIONS + _TEXT_EXTENSIONS:
        if name.endswith(ext):
            return ext
    return ""


def _rewind(source) -> None:
    if hasattr(source, "seek"):
        try:
            source.seek(0)
        except Exception:  # noqa: BLE001
            pass


def _peek_bytes(source, n: int = 8) -> bytes:
    if not (hasattr(source, "read") and hasattr(source, "seek")):
        return b""
    try:
        pos = source.tell()
        raw = source.read(n)
        source.seek(pos)
    except Exception:  # noqa: BLE001
        return b""
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, str):
        return raw.encode("utf-8", errors="ignore")
    return b""


def _looks_like_excel(source) -> bool:
    sig = _peek_bytes(source)
    return sig.startswith(b"PK\x03\x04") or sig.startswith(b"\xd0\xcf\x11\xe0")


def _equity_sanity(returns: pd.Series) -> None:
    """Final backstop for any path: refuse non-finite or implausibly large equity
    (a real strategy never compounds past ~1e9×; that means a units/format error)."""
    arr = np.asarray(returns, dtype=float)
    if not np.isfinite(arr).all():
        raise InputError("returns contain non-finite values after processing.")
    growth = float(np.prod(1.0 + arr))
    if (not np.isfinite(growth)) or growth > 1e9:
        raise InputError(
            "resulting equity is implausibly large (>1e9×) — almost always a units/format "
            "problem (percent treated as decimal) or the wrong column was scored.")


def _read_csv_smart(source) -> pd.DataFrame:
    """Read a CSV tolerant of BOM and non-comma delimiters. Tries comma first
    (fast path); if that collapses to one column, retries with EXPLICIT
    delimiters only (; tab |) — never auto-sniffs arbitrary characters, which
    would wrongly split a single-column file on a letter."""
    def _read(encoding: str, **kw):
        _rewind(source)
        return pd.read_csv(source, encoding=encoding, skipinitialspace=True, **kw)

    first_df = None
    first_error = None
    for encoding in _TEXT_ENCODINGS:
        try:
            df = _read(encoding)
        except Exception as e:  # noqa: BLE001
            first_error = first_error or e
            continue
        if first_df is None:
            first_df = df
        if df.shape[1] >= 2:
            return df
        for sep in (";", "\t", "|"):
            try:
                alt = _read(encoding, sep=sep)
            except Exception:  # noqa: BLE001
                continue
            if alt.shape[1] >= 2:
                return alt
    if first_df is not None:
        return first_df                                    # genuinely single-column
    detail = f": {first_error}" if first_error else ""
    raise InputError(f"could not parse the text file as CSV/TSV{detail}.")


def _normalise_excel_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.empty:
        return df
    cols = [str(c).strip() for c in df.columns]
    df = df.copy()
    df.columns = cols

    # Some broker/TV exports put title/metadata rows above the real header;
    # pandas then names most columns "Unnamed". Promote the best-looking row
    # among the first few rows when it clearly looks more like a schema.
    header_blob = " ".join(c.lower() for c in cols)
    hints = (
        _DATE_HINTS + _PRICE_HINTS + _RETURN_HINTS + _EQUITY_HINTS
        + ("entry", "exit", "symbol", "trade", "signal", "type", "profit", "drawdown", "run-up")
    )
    header_hits = sum(1 for h in hints if h in header_blob)
    unnamed = sum(1 for c in cols if not c or c.lower().startswith("unnamed"))
    best_i = None
    best_hits = header_hits
    for i in range(min(30, len(df))):
        row = df.iloc[i].astype(str).str.strip()
        row_blob = " ".join(str(v).lower() for v in row.tolist())
        hits = sum(1 for h in hints if h in row_blob)
        if hits > best_hits:
            best_i, best_hits = i, hits
    if best_i is not None and best_hits > header_hits and (unnamed >= max(1, len(cols) // 2) or header_hits == 0):
        header = df.iloc[best_i].astype(str).str.strip().tolist()
        df = df.iloc[best_i + 1:].copy()
        # Some exports write a title/header block in the left columns and the
        # actual data table in the right columns. When the promoted header cells
        # would land on all-empty columns, move the meaningful names onto the
        # columns that actually carry data before dropping blanks.
        def _valid_header_cell(v: object) -> bool:
            s = str(v).strip()
            return bool(s) and s.lower() not in {"nan", "nat", "none", "<na>"}

        meaningful = [str(v).strip() for v in header if _valid_header_cell(v)]
        nonempty_pos = [j for j in range(df.shape[1]) if df.iloc[:, j].notna().any()]
        header_pos = [j for j, v in enumerate(header) if _valid_header_cell(v)]
        if meaningful and len(meaningful) == len(nonempty_pos) and not all(j in nonempty_pos for j in header_pos):
            shifted = [str(v).strip() for v in header]
            for dest, name in zip(nonempty_pos, meaningful):
                shifted[dest] = name
            header = shifted
        df.columns = [str(v).strip() for v in header]
        df = df.dropna(how="all").dropna(axis=1, how="all")
    return df


def _normalize_user_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = normalize_columns(list(out.columns))
    return out


def _sheet_score(df: pd.DataFrame, sheet_name: str = "") -> int:
    cols = [str(c).lower() for c in df.columns]
    joined = " ".join(cols)
    sheet_key = normalize_column_name(sheet_name)
    score = 0
    if any(h in joined for h in _DATE_HINTS):
        score += 5
    if any(h in joined for h in _RETURN_HINTS + _EQUITY_HINTS + _PRICE_HINTS):
        score += 5
    if "entry" in joined and "exit" in joined:
        score += 4
    if "trade" in joined or "trade" in sheet_key:
        score += 4
    if "net_pnl" in joined and ("type" in joined or "signal" in joined):
        score += 5
    if len(df) >= 40:
        score += 2
    elif len(df) >= 3:
        score += 1
    return score


def _read_excel_smart(source, filename: Optional[str] = None) -> pd.DataFrame:
    """Read the first usable worksheet from an Excel workbook."""
    ext = _extension(source, filename)
    engines = ["openpyxl"] if ext in (".xlsx", ".xlsm") else ["xlrd"] if ext == ".xls" else ["openpyxl", "xlrd"]
    last_error = None
    sheets = None
    for engine in engines:
        try:
            _rewind(source)
            sheets = pd.read_excel(source, sheet_name=None, engine=engine)
            break
        except ImportError as e:
            last_error = e
            continue
        except Exception as e:  # noqa: BLE001
            last_error = e
            continue
    if sheets is None:
        hint = "install openpyxl for .xlsx/.xlsm or xlrd for legacy .xls"
        raise InputError(f"could not parse the Excel workbook ({hint}): {last_error}")

    best = None
    best_score = -1
    for sheet_name, sheet_df in sheets.items():
        df = _normalise_excel_frame(sheet_df)
        if df.shape[0] < 2 or df.shape[1] < 2:
            continue
        score = _sheet_score(_normalize_user_columns(df), sheet_name=str(sheet_name))
        if score > best_score:
            best = (sheet_name, df)
            best_score = score
    if best is None:
        raise InputError("Excel workbook has no usable sheet with at least two columns and two data rows.")
    return best[1]


def _read_table_smart(source, filename: Optional[str] = None) -> pd.DataFrame:
    ext = _extension(source, filename)
    if ext in _EXCEL_EXTENSIONS or _looks_like_excel(source):
        return _read_excel_smart(source, filename=filename)
    return _read_csv_smart(source)


def read_user_table(source, filename: Optional[str] = None) -> pd.DataFrame:
    """Read a user-uploaded strategy file (CSV/TSV/TXT/Excel) into a DataFrame."""
    return _normalize_user_columns(_read_table_smart(source, filename=filename))


def _coerce_numeric(s: pd.Series):
    """Best-effort numeric parse. Handles '1.2%', decimal-comma '0,01',
    thousands '1,234.5'. Returns (numeric_series, is_percent)."""
    name = normalize_column_name(getattr(s, "name", ""))
    name_is_pct = any(token in name for token in ("pct", "percent")) and "ratio" not in name
    if pd.api.types.is_numeric_dtype(s):
        num = pd.to_numeric(s, errors="coerce")
        return (num / 100.0, True) if name_is_pct else (num, False)
    t = s.astype(str).str.strip()
    pct = bool((t.str.endswith("%")).mean() > 0.5)
    t = t.str.replace("%", "", regex=False).str.replace(" ", "", regex=False)
    if bool((t.str.match(r"^-?\d+,\d+$")).mean() > 0.5):
        t = t.str.replace(",", ".", regex=False)           # decimal comma
    else:
        t = t.str.replace(",", "", regex=False)            # thousands separator
    num = pd.to_numeric(t, errors="coerce")
    if pct or name_is_pct:
        num = num / 100.0
    return num, bool(pct or name_is_pct)


def coerce_numeric_series(s: pd.Series):
    """Public wrapper around _coerce_numeric for downstream consumers (e.g. the
    QuantScopeX Pro report path) that need the same percent/decimal unit parsing.
    Returns (numeric_series, is_percent)."""
    return _coerce_numeric(s)


def _parse_dates(s: pd.Series) -> pd.Series:
    """Parse a date/time column robustly: ISO/strings AND Unix epoch.

    Many K-line exports (Binance, TradingView, exchange APIs) store the time as a
    Unix timestamp in seconds or milliseconds. Plain pd.to_datetime treats those
    integers as NANOSECONDS -> everything lands in 1970. Detect the magnitude and
    convert with the right unit.
    """
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() > 0.8 and num.notna().any():     # looks numeric -> likely epoch
        med = float(num.dropna().abs().median())
        if 20_000 <= med < 80_000:
            return pd.to_datetime(num, unit="D", origin="1899-12-30", errors="coerce")
        unit = ("s" if 1e8 <= med < 1e11 else
                "ms" if 1e11 <= med < 1e14 else
                "us" if 1e14 <= med < 1e17 else
                "ns" if 1e17 <= med < 1e20 else None)
        if unit:
            return pd.to_datetime(num, unit=unit, errors="coerce")
    return pd.to_datetime(s, errors="coerce", utc=False)


def _pick_date_column(df: pd.DataFrame, date_column: Optional[str]) -> str:
    if date_column is not None:
        if date_column not in df.columns:
            raise InputError(f"date column '{date_column}' not found; have {list(df.columns)}")
        return date_column
    for col in df.columns:
        if any(h in str(col).lower() for h in _DATE_HINTS):
            return col
    # fall back to the first column if it parses as a date
    first = df.columns[0]
    parsed = _parse_dates(df[first])
    if parsed.notna().mean() > 0.8:
        return first
    raise InputError(
        "could not find a date/time column. Pass date_column=... explicitly "
        f"(columns: {list(df.columns)})."
    )


def _pick_value_column(df: pd.DataFrame, date_col: str, column: Optional[str]) -> str:
    if column is not None:
        if column not in df.columns:
            raise InputError(f"value column '{column}' not found; have {list(df.columns)}")
        return column
    candidates = [c for c in df.columns if c != date_col
                  and pd.api.types.is_numeric_dtype(df[c])]
    if not candidates:
        # try to coerce non-numeric columns (handles '1.2%', decimal-comma, ...)
        for c in df.columns:
            if c == date_col:
                continue
            if _coerce_numeric(df[c])[0].notna().mean() > 0.8:
                candidates.append(c)
    if not candidates:
        raise InputError("no numeric value column found.")
    if len(candidates) == 1:
        return candidates[0]
    # prefer a clearly-named one
    for c in candidates:
        if any(h in str(c).lower() for h in _RETURN_HINTS + _EQUITY_HINTS):
            return c
    raise InputError(
        f"multiple numeric columns {candidates}; pass column=... to choose one."
    )


def _detect_input_type(name: str, s: pd.Series) -> Tuple[Optional[str], str]:
    """Return ('returns'|'equity'|None, reason)."""
    lname = str(name).lower()
    if any(h in lname for h in _RETURN_HINTS):
        return "returns", f"column name '{name}' looks like returns"
    if any(h in lname for h in _EQUITY_HINTS):
        return "equity", f"column name '{name}' looks like an equity/level series"

    vals = s.dropna()
    if (vals < 0).any():
        return "returns", "series contains negative values (an equity/NAV curve cannot)"
    # all >= 0 from here: disambiguate level-like curve vs small periodic returns
    med = float(vals.median()) if len(vals) else 0.0
    lvl_ac = vals.autocorr(lag=1) if len(vals) > 3 else float("nan")
    lvl_ac = float(lvl_ac) if lvl_ac == lvl_ac else 0.0
    if med > 0.5 or lvl_ac > 0.95:
        return "equity", f"all-positive and level-like (median={med:.3g}, lag1_ac={lvl_ac:.2f})"
    if med <= 0.5:
        return "returns", f"all-positive but small-magnitude (median={med:.3g})"
    return None, "ambiguous"


def _freq_label(sec: float) -> str:
    if sec <= 0:
        return "unknown"
    if sec < 3600 * 1.5:
        mins = sec / 60.0
        return f"~{mins:.0f}min" if mins < 90 else "~hourly"
    hours = sec / 3600.0
    if hours < 20:
        return f"~{hours:.0f}h"
    days = sec / 86400.0
    if days < 2:
        return "daily"
    if days < 9:
        return "weekly"
    if days < 45:
        return "monthly"
    return f"~{days:.0f}d"


def _forward_looking_input_warnings(df: pd.DataFrame, source_name: str = "") -> list[str]:
    """Catch explicit user/export hints that the uploaded result may contain
    forward-looking data. This cannot prove look-ahead bias, but if a filename or
    column literally says "leaky/future/lookahead", the free scorer should not
    present the curve as clean."""
    out: list[str] = []
    stem = re.sub(r"\.(csv|tsv|txt|xlsx|xls|xlsm)$", "", str(source_name).lower())
    if stem and any(marker in stem for marker in _SOURCE_FORWARD_MARKERS):
        out.append(
            "possible forward-looking marker in filename/path (leaky/future/lookahead); "
            "verify this is not a look-ahead or target-leak backtest before trusting the score"
        )
    cols = [str(c).lower() for c in df.columns]
    suspicious = [c for c in cols if any(c.startswith(prefix) for prefix in _COLUMN_FORWARD_PREFIXES)]
    if suspicious:
        shown = ", ".join(suspicious[:5])
        out.append(
            f"possible forward-looking column(s): {shown}; verify these are not future/target labels "
            "leaking into the scored return path"
        )
    return out


# --------------------------------------------------------------------------- #
# trade-log support
# --------------------------------------------------------------------------- #
_ENTRY_HINTS = (
    "entry_time", "entry_date", "entry_dt", "entry", "open_time", "opened",
    "open_date", "open_timestamp", "buy_date", "filled_time",
)
_EXIT_HINTS = (
    "exit_time", "exit_date", "exit_dt", "exit", "close_time", "closed",
    "close_date", "close_timestamp", "sell_date", "date_time", "datetime", "time",
)
_PCT_PNL_HINTS = (
    "net_pnl_pct", "pnl_pct", "pnl_percent", "return_pct", "ret_pct",
    "profit_pct", "pct_return",
)
_DEC_PNL_HINTS = (
    "profit_ratio", "return_ratio", "pnl_ratio", "net_pnl", "pnl", "return",
    "returns", "ret", "profit", "pl",
)
_EVENT_HINTS = ("type", "signal", "direction", "side")
_EXIT_EVENT_RE = r"\b(?:exit|close|closed|cover)\b|出场|平仓|离场"
_ENTRY_EVENT_RE = r"\b(?:entry|open|opened)\b|进场|开仓|入场"


def _match(cols, hints):
    low = {c: str(c).lower() for c in cols}
    for h in hints:
        for c in cols:
            if h in low[c]:
                return c
    return None


def _event_masks(df: pd.DataFrame, col: Optional[str]):
    if col is None or col not in df.columns:
        return None
    text = df[col].astype(str).str.strip().str.lower()
    exit_like = text.str.contains(_EXIT_EVENT_RE, regex=True, na=False)
    entry_like = text.str.contains(_ENTRY_EVENT_RE, regex=True, na=False)
    return exit_like, entry_like


def _event_exit_mask(df: pd.DataFrame, col: Optional[str]):
    masks = _event_masks(df, col)
    if masks is None:
        return None
    exit_like, entry_like = masks
    if bool(exit_like.any()):
        return exit_like
    if bool(entry_like.any()) and bool((~entry_like).any()):
        return ~entry_like
    return None


def _event_entry_mask(df: pd.DataFrame, col: Optional[str]):
    masks = _event_masks(df, col)
    if masks is None:
        return None
    _, entry_like = masks
    return entry_like if bool(entry_like.any()) else None


def _pick_event_column(df: pd.DataFrame, cols: list[str]) -> Optional[str]:
    candidates = [c for c in cols if any(h in str(c).lower() for h in _EVENT_HINTS)]
    for col in candidates:
        if _event_exit_mask(df, col) is not None:
            return col
    return candidates[0] if candidates else None


def _detect_trade_log(df: pd.DataFrame):
    """A trade log has BOTH an entry-time and an exit-time column (a returns or
    equity series never does). Returns dict(entry, exit, pnl, is_pct) or None.
    """
    cols = list(df.columns)
    entry = _match(cols, _ENTRY_HINTS)
    exit_ = _match(cols, _EXIT_HINTS)
    # TradingView's List of Trades export commonly has one Date/Time column and
    # one row per entry/exit event. The exit rows carry the realized Net P&L.
    event_col = _pick_event_column(df, cols)
    tv_event_log = entry is None and exit_ is not None and event_col is not None
    if (entry is None or exit_ is None or entry == exit_) and not tv_event_log:
        return None
    # exclude running-total / excursion / fee columns so we pick the PER-TRADE pnl
    bad = ("cum", "total", "mfe", "mae", "fee", "comm", "running")
    pcols = [c for c in cols if not any(b in str(c).lower() for b in bad)]
    pnl_pct = _match(pcols, _PCT_PNL_HINTS)
    if pnl_pct is not None:
        return dict(entry=entry, exit=exit_, pnl=pnl_pct, is_pct=True,
                    tv_event_log=tv_event_log, event_col=event_col)
    pnl_dec = _match(pcols, _DEC_PNL_HINTS)
    if pnl_dec is not None and not any(u in str(pnl_dec).lower() for u in ("usd", "usdt", "$")):
        if any(u in str(pnl_dec).lower() for u in ("pct", "percent")):
            return dict(entry=entry, exit=exit_, pnl=pnl_dec, is_pct=True,
                        tv_event_log=tv_event_log, event_col=event_col)
        if "ratio" in str(pnl_dec).lower():
            return dict(entry=entry, exit=exit_, pnl=pnl_dec, is_pct=False,
                        tv_event_log=tv_event_log, event_col=event_col)
        v, parsed_as_pct = _coerce_numeric(df[pnl_dec])
        v = v.dropna().abs()
        med = float(v.median()) if len(v) else 0.0
        # A generic column name with a median magnitude above 20 is either
        # currency PnL or percent at a scale where a wrong guess is ~100x off
        # (a MEDIAN per-trade return past 20% is not a plausible percent value).
        # Refuse to guess — require an explicit unit instead.
        if med > 20.0:
            return dict(entry=entry, exit=exit_, pnl=None, is_pct=False, reason=(
                f"trade-log column '{pnl_dec}' has a median magnitude of {med:.1f} — at this "
                "scale it could be currency PnL or percent returns, and guessing wrong is "
                "~100x off. Rename the column pnl_pct/return_pct (percent values) or supply "
                "decimal returns (0.032 = +3.2%)."))
        # magnitude guess: median > 1 reads as percent (3.2 -> 3.2%), else decimal
        # (0.032 -> 3.2%). The [0.5, 1] zone is genuinely ambiguous -> warn.
        return dict(entry=entry, exit=exit_, pnl=pnl_dec, is_pct=bool(parsed_as_pct or med > 1.0),
                    tv_event_log=tv_event_log, event_col=event_col,
                    unit_guessed=True, unit_ambiguous=0.5 < med <= 1.0)
    return dict(entry=entry, exit=exit_, pnl=None, is_pct=False,
                tv_event_log=tv_event_log, event_col=event_col)  # only absolute $ PnL


def _load_trade_log(df: pd.DataFrame, tl: dict, warnings: list):
    if tl["pnl"] is None:
        raise InputError(tl.get("reason") or (
            "detected a trade log, but it only has an absolute (USDT/$) PnL column "
            "and no % return. Add a pnl_pct/return_pct column, or upload a returns "
            "or equity-curve file instead."))
    source_df = df
    n_ignored_event_rows = 0
    tv_entry_by_trade: Optional[dict] = None
    trade_col: Optional[str] = None
    if tl.get("tv_event_log"):
        mask = _event_exit_mask(df, tl.get("event_col"))
        if mask is not None and bool(mask.any()):
            trade_col = _match(list(df.columns), ("trade_number", "trade_id", "trade", "id"))
            entry_mask = _event_entry_mask(df, tl.get("event_col"))
            if trade_col is not None and entry_mask is not None and tl.get("exit") in df.columns:
                entry_rows = df.loc[entry_mask].copy()
                if len(entry_rows):
                    entry_rows["_entry_dt"] = _parse_dates(entry_rows[tl["exit"]])
                    entry_rows = entry_rows.dropna(subset=["_entry_dt"]).sort_values("_entry_dt")
                    if len(entry_rows):
                        tv_entry_by_trade = (
                            entry_rows.groupby(trade_col)["_entry_dt"].first().to_dict()
                        )
            source_df = df.loc[mask].copy()
            n_ignored_event_rows = len(df) - len(source_df)
            warnings.append(
                f"TradingView-style event log: used {len(source_df)} exit/close row(s) "
                "and ignored entry/open rows."
            )

    dt = _parse_dates(source_df[tl["exit"]])  # PnL realised at exit
    entry_dt = _parse_dates(source_df[tl["entry"]]) if tl.get("entry") in source_df.columns else None
    if entry_dt is None and tv_entry_by_trade and trade_col is not None and trade_col in source_df.columns:
        mapped = source_df[trade_col].map(tv_entry_by_trade)
        parsed = _parse_dates(mapped)
        if parsed.notna().mean() >= 0.7:
            entry_dt = parsed
    pnl, parsed_as_pct = _coerce_numeric(source_df[tl["pnl"]])
    work_data = {"dt": dt, "v": pnl}
    if entry_dt is not None:
        work_data["entry_dt"] = entry_dt
    work = pd.DataFrame(work_data).dropna(subset=["dt", "v"]).sort_values("dt")
    n_dropped = len(source_df) - len(work)
    if len(work) < 3:
        raise InputError("fewer than 3 valid trades after cleaning.")
    rets = work["v"].to_numpy(dtype=float)
    guess_note = (" — unit GUESSED from magnitude; name the column pnl_pct or "
                  "return_pct (percent) vs pnl/return (decimal) to be explicit"
                  if tl.get("unit_guessed") else "")
    if tl["is_pct"] and not parsed_as_pct:
        rets = rets / 100.0
    if tl["is_pct"] or parsed_as_pct:
        warnings.append(f"trade log: '{tl['pnl']}' read as percent (÷100); per-trade equity "
                        f"compounds fully-reinvested{guess_note}")
    else:
        warnings.append(f"trade log: '{tl['pnl']}' read as decimal per-trade returns{guess_note}")
    if tl.get("unit_ambiguous"):
        warnings.append("trade log: per-trade magnitudes sit in the ambiguous 0.5-1.0 range — "
                        "if these are percent values the score is computed on ~100x the real "
                        "returns; rename the column to pnl_pct to force percent")
    bad = rets <= -1.0
    if bad.any():
        rets = np.where(bad, -0.999, rets)
        warnings.append(f"clipped {int(bad.sum())} trade(s) with return <= -100% to -99.9%")
    returns = pd.Series(rets, index=pd.DatetimeIndex(work["dt"].to_numpy()), name=str(tl["pnl"]))
    _equity_sanity(returns)
    idx = returns.index
    span_years = (idx[-1] - idx[0]).total_seconds() / SECONDS_PER_YEAR
    n = len(returns)
    ppy = n / span_years if span_years > 0 else 252.0
    sym_col = _match(list(df.columns), ("symbol", "ticker", "asset", "pair", "instrument"))
    symbol = None
    if sym_col is not None:
        sv = df[sym_col].dropna()
        symbol = str(sv.iloc[0]) if len(sv) else None
    valid_event_times = None
    if "entry_dt" in work.columns:
        event_times = work[["entry_dt", "dt"]].dropna().copy()
        event_times = event_times[event_times["entry_dt"] <= event_times["dt"]]
        if len(event_times) >= max(3, int(0.7 * n)):
            valid_event_times = event_times
    meta = dict(
        input_type="trade_log", caliber="closed_trade",
        value_column=str(tl["pnl"]), date_column=str(tl["exit"]), symbol=symbol,
        n=n, n_trades=n, span_years=float(span_years), ppy=float(ppy),
        bar_freq="per-trade", start=str(idx[0]), end=str(idx[-1]),
        n_dropped=int(n_dropped), n_ignored_event_rows=int(n_ignored_event_rows),
        warnings=warnings,
    )
    if valid_event_times is not None:
        meta["trade_entry_times"] = [str(x) for x in valid_event_times["entry_dt"]]
        meta["trade_exit_times"] = [str(x) for x in valid_event_times["dt"]]
        holding_days = (
            (valid_event_times["dt"] - valid_event_times["entry_dt"]).dt.total_seconds()
            / 86400.0
        )
        meta["trade_holding_days_median"] = float(holding_days.median())
        meta["trade_holding_days_mean"] = float(holding_days.mean())
    return returns, meta


def load_returns(
    source,
    *,
    input_type: str = "auto",
    column: Optional[str] = None,
    date_column: Optional[str] = None,
    filename: Optional[str] = None,
) -> Tuple[pd.Series, dict]:
    """Load `source` (path or file-like) into a clean returns Series + meta.

    Parameters
    ----------
    input_type : 'auto' | 'returns' | 'equity'
    column, date_column : explicit overrides if auto-detection picks wrong.

    Returns
    -------
    (returns, meta) where returns is a float Series indexed by a sorted
    DatetimeIndex, and meta carries ppy, span_years, n, input_type, warnings...
    """
    source_name = _source_name(source, filename)
    df = _normalize_user_columns(_read_table_smart(source, filename=filename))
    if df.shape[1] < 2:
        raise InputError("need at least a date column and a value column "
                         "(only one column found, even after delimiter sniffing).")
    warnings: list = _forward_looking_input_warnings(df, source_name)

    # trade log? (has both entry & exit columns) — handle before generic detection
    if input_type in ("auto", "trade_log"):
        tl = _detect_trade_log(df)
        if tl is not None:
            return _load_trade_log(df, tl, warnings)
        if input_type == "trade_log":
            raise InputError("input_type='trade_log' but no entry/exit columns were found.")

    date_col = _pick_date_column(df, date_column)
    val_col = _pick_value_column(df, date_col, column)

    dt = _parse_dates(df[date_col])
    vals, vals_were_pct = _coerce_numeric(df[val_col])
    if vals_were_pct:
        warnings.append(f"column '{val_col}' had '%' signs — parsed as percent (÷100)")
    work = pd.DataFrame({"dt": dt, "v": vals}).dropna()
    n_dropped = len(df) - len(work)
    if n_dropped:
        warnings.append(f"dropped {n_dropped} row(s) with unparseable date/value")
    if len(work) < 3:
        raise InputError("fewer than 3 valid rows after cleaning.")
    work = work.drop_duplicates(subset="dt", keep="last").sort_values("dt")
    s = pd.Series(work["v"].to_numpy(), index=pd.DatetimeIndex(work["dt"]), name=val_col)

    # decide returns vs equity
    if input_type == "auto":
        detected, reason = _detect_input_type(val_col, s)
        if detected is None:
            raise InputError(
                "could not tell whether this is a returns or an equity series. "
                "Re-run with input_type='returns' or input_type='equity'."
            )
        input_type = detected
        warnings.append(f"input_type auto-detected as '{input_type}' ({reason})")
    elif input_type not in ("returns", "equity"):
        raise InputError("input_type must be 'auto', 'returns', 'equity' or 'trade_log'.")

    if input_type == "equity":
        if (s <= 0).any():
            raise InputError("equity series must be strictly positive.")
        returns = s.pct_change().dropna()
    else:
        returns = s.astype(float)
        if (returns <= -1.0).any():
            raise InputError(
                "returns contain a period <= -100%, which makes equity zero or negative. "
                "Upload a valid equity curve, fix the return units, or clip/clean busted rows "
                "before scoring.")
        extreme_pos = returns > 3.0
        big_abs_share = float((returns.abs() > 1.0).mean())
        median_abs = float(returns.abs().median()) if len(returns) else 0.0
        p90_abs = float(returns.abs().quantile(0.90)) if len(returns) else 0.0
        if median_abs > 0.20 or p90_abs > 0.80:
            warnings.append(
                "return units look unusually large — if values like 5 mean 5%, divide by 100 "
                "or name the column return_pct before scoring."
            )
        if big_abs_share > 0.5:
            warnings.append(
                "most |return| > 1.0 — if these are percent values (e.g. 5 == 5%), "
                "divide by 100 before scoring."
            )
        elif extreme_pos.any():
            warnings.append(
                f"{int(extreme_pos.sum())} period(s) exceed +300%; kept as decimal returns. "
                "Verify this is not a percent-vs-decimal unit error."
            )

    returns = returns[np.isfinite(returns.to_numpy())]
    if len(returns) < 3:
        raise InputError("fewer than 3 usable returns after processing.")
    _equity_sanity(returns)

    # ppy from data ONLY
    idx = returns.index
    span_sec = (idx[-1] - idx[0]).total_seconds()
    span_years = span_sec / SECONDS_PER_YEAR
    n = len(returns)
    if span_years > 0:
        ppy = n / span_years
    else:
        ppy = 252.0
        warnings.append("degenerate time span; ppy fell back to 252.")
    # display-only bar frequency from the median spacing
    spacings = np.diff(idx.asi8) / 1e9  # nanoseconds -> seconds
    median_spacing = float(np.median(spacings)) if len(spacings) else 0.0

    meta = dict(
        input_type=input_type,
        value_column=val_col,
        date_column=date_col,
        n=n,
        span_years=float(span_years),
        ppy=float(ppy),
        bar_freq=_freq_label(median_spacing),
        start=str(idx[0]),
        end=str(idx[-1]),
        n_dropped=int(n_dropped),
        warnings=warnings,
    )
    return returns, meta


def load_prices(source, *, column: Optional[str] = None,
                date_column: Optional[str] = None) -> pd.Series:
    """Load an asset's K-line / price CSV into a positive close-price Series
    (DatetimeIndex). Accepts OHLC (uses the close) or a single price column."""
    df = _read_csv_smart(source)
    if df.shape[1] < 2:
        raise InputError("price CSV needs a date column and a price/close column.")
    date_col = _pick_date_column(df, date_column)
    if column is not None:
        if column not in df.columns:
            raise InputError(f"price column '{column}' not found; have {list(df.columns)}")
        price_col = column
    else:
        others = [c for c in df.columns if c != date_col]
        price_col = _match(others, _PRICE_HINTS)
        if price_col is None:                              # fall back to the last numeric column
            nums = [c for c in others if _coerce_numeric(df[c])[0].notna().mean() > 0.8]
            if not nums:
                raise InputError("no price/close column found in the asset CSV.")
            price_col = nums[-1]
    dt = _parse_dates(df[date_col])
    px, _ = _coerce_numeric(df[price_col])
    work = pd.DataFrame({"dt": dt, "p": px}).dropna()
    work = work[work["p"] > 0].drop_duplicates(subset="dt", keep="last").sort_values("dt")
    if len(work) < 2:
        raise InputError("fewer than 2 valid price rows in the asset CSV.")
    return pd.Series(work["p"].to_numpy(), index=pd.DatetimeIndex(work["dt"]), name=str(price_col))
