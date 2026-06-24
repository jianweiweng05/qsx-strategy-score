"""Generate small example CSVs for docs / demo / smoke-testing.

    python examples/make_samples.py
writes into examples/: sample_returns.csv, sample_equity.csv, sample_flagged.csv
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))


def _dates(n, start="2021-01-01"):
    return pd.date_range(start=start, periods=n, freq="D")


def main():
    rng = np.random.default_rng(20260530)

    # 1) a decent, diversified daily strategy (returns)
    r = rng.normal(0.0013, 0.011, 1100)
    pd.DataFrame({"date": _dates(1100), "strategy_ret": r}).to_csv(
        os.path.join(OUT, "sample_returns.csv"), index=False)

    # 2) the same kind of track record expressed as an equity/NAV curve
    r2 = rng.normal(0.0011, 0.013, 1000)
    eq = 10000.0 * np.cumprod(1 + r2)
    pd.DataFrame({"date": _dates(1001),
                  "equity": np.concatenate([[10000.0], eq])}).to_csv(
        os.path.join(OUT, "sample_equity.csv"), index=False)

    # 3) a suspiciously smooth (likely interpolated / overfit) curve -> FLAGGED
    n = 800
    eps = rng.normal(0.0, 0.0007, n)
    rf = np.empty(n); rf[0] = 0.0016
    for t in range(1, n):
        rf[t] = 0.0014 + 0.6 * (rf[t - 1] - 0.0014) + eps[t]
    pd.DataFrame({"date": _dates(n), "return": rf}).to_csv(
        os.path.join(OUT, "sample_flagged.csv"), index=False)

    print("wrote sample_returns.csv, sample_equity.csv, sample_flagged.csv to", OUT)


if __name__ == "__main__":
    main()
