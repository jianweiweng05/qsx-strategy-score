# v0.4.0 input and comparison contract

An account return at timestamp `t` is the return over the interval since the preceding endpoint, with deposits/withdrawals removed by the data producer. Equity/NAV observations must be positive account levels with consistent capital-flow treatment. The scorer cannot verify that provenance from two columns.

All parsed timestamps become UTC; an unzoned timestamp is interpreted as UTC. Invalid timestamps, missing/non-finite values and conflicting values at one timestamp are errors. Exact duplicate period rows may be removed and counted. Period losses at or below -100% are unsupported; never clip or delete a genuine loss to obtain a score.

Trade logs require every closed trade's entry and exit time, nonnegative duration, and finite percentage/decimal return greater than -100%. Intervals are `[entry, exit)`; an exit and next entry can share an instant. Overlapping positions, multiple symbols and ambiguous TradingView entry identifiers are rejected. Even an accepted nonoverlapping log supplies only trade descriptions. Per-trade percentage sums and win rates are not capital-weighted account PnL.

## Daily comparison

1. Build the strategy NAV using the observed initial NAV timestamp when supplied. Convert both timestamp indexes to UTC without moving their actual instants.
2. A daily benchmark with one stable UTC closing time determines the common cutoff. For an intraday benchmark, use 00:00 UTC. Varying cutoffs, including an unmodelled daylight-saving session change, are unsupported.
3. Select actual NAV observations at that cutoff separately on each side. Never take an earlier partial-day mark and call it a closing observation. Never fill empty days with zeros or prices with forward fills.
4. Intraday return inputs require a complete regular grid that divides 24 hours. Mixed grids, missing returns and session-gapped intraday returns are rejected at input/account-scoring admission, with or without a benchmark. Same-cutoff daily or session returns remain supported; an entirely omitted session cannot be inferred from the file alone. Independently observed NAV levels can bridge internal gaps; daily drawdowns remain limited by the observed endpoints.
5. Pair the common NAV endpoints, then calculate both interval returns from exactly the same start and end. A Friday-to-Monday benchmark interval compounds all strategy PnL between those endpoints. Missing strategy endpoints on the benchmark's observed calendar are unavailable.
6. Compare daily Calmar on this window. The random proxy needs at least 120 paired intervals. A benchmark covering less than 95% of the strategy span remains partial and cannot qualify a metal tier. Original-frequency account risk diagnostics remain separate; the total score is not promised invariant under arbitrary resampling.

The implementation assumes timestamps are correct interval ends. It cannot discover an undeclared timezone, systematically omitted observations, cash flows, stale prices or falsely labelled data. Unsupported calendar/cutoff cases return N/A rather than guessing a calendar.

## Random proxy and null values

The proxy supports signed regression beta with `0.15 <= abs(beta) < 1` (excluding a numerical tolerance near 1). Beta magnitude is a proxy, not measured invested time. Require the strategy's daily Calmar to exceed the same-beta static reference before testing random signed exposure. For intraday inputs, also require a complete shared native grid and construct a constant-exposure NAV at that original frequency before sampling its daily endpoints. Its daily Calmar must also be exceeded; this blocks rebalancing compounding from qualifying as timing. A daily-only benchmark cannot provide this reference for an intraday strategy, so the proxy is N/A. Daily NAV alone only supports comparison with a daily proxy; a passing result or metal tier does not certify true timing skill. Both references include the first interval. No default fee is charged only to the random reference; zero incremental reference costs and unknown actual costs are explicit metadata.

Degenerate, unsupported, non-finite or insolvent references return a typed reason in `meta.random_control_unavailable_reason`. No event-based fallback can give a closed-trade log account qualification. Finite simulation p-values use `(exceedances + 1) / (simulations + 1)` and expose both counts.

Sample insufficiency and missing random-control evidence withhold the metal tier without imposing a score cap. Consumers must render null as N/A. Closed-trade `overall`, `display`, `path_risk`, and quality pillars are null; `meta.trade_summary` contains the supported output. Downstream services must not compute account performance or a compounded account curve from these trade returns. `overfit_risk` remains an equal-valued compatibility alias of `path_risk`, whose scope excludes search. `n_trials=null` is unknown; explicit `1` is self-reported.

## Reproduction

Reports include `core_version`, `scoring_version`, profile, trial-count status, RNG defaults, normalized `input_hash`, and `benchmark_hash` for the source benchmark snapshot. The input hash includes the normalized return values/timestamps, input caliber, original NAV anchor and available trade entry/exit metadata; filenames are excluded. Retain raw source snapshots separately if byte-level provenance is required.

Default random control uses seed 12345 and 128 simulations; bootstrap routines also use seed 12345. Monte Carlo allows at most 4,000,000 elements per large work array, including padding, and at least 300 simulations. It skips oversized paths before RNG/index allocations. This is a per-array bound, not a claim about total process peak memory. The release tag, dependency versions and parameter overrides belong in every later calibration manifest.
