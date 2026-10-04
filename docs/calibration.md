# Calibration policy

QSX Strategy Score is a **screening** tool for a return curve, equity curve, or closed-trade log. It helps decide whether a backtest deserves more investigation. It does not certify alpha or production readiness.

## What the score means

The 0–100 number is a **path-quality score**. It summarizes return quality, path plausibility and consistency signals, and drawdown control in the uploaded path.

The grade separately describes whether the free evidence is sufficient to earn a public tier:

- `GOLD`, `SILVER`, `BRONZE`: the path passed the available free evidence gates.
- `PROVISIONAL`: the path may have a useful score, but key evidence is missing or incomplete.
- `NEEDS WORK`: a material free check failed.
- `FLAGGED`: the path looks implausible enough that the backtest method should be verified before trusting any score.

## Evidence required for a metal tier

A metal tier requires all of the following:

1. A comparable asset benchmark with adequate overlap.
2. A completed, nondegenerate daily signed-beta proxy on that comparison (at least 120 paired intervals; `0.15 <= abs(beta) < 1`).
3. A result that beats buy-and-hold, the same-beta static reference (including matched native-frequency compounding for intraday inputs), and the available random proxy.
4. Adequate sample size and at least two years of history.
5. Enough effective trades that profit is not concentrated in a handful of events.
6. No hard integrity, profitability, or later-window failure.

Missing any of these does not prove a strategy is bad. It means the correct free result is `PROVISIONAL`, not a metal award.

## What the free checks cannot prove

The scorer cannot inspect strategy code, raw market data, fills, leverage, funding, capacity, hidden parameter searches, manual selection, look-ahead bias, survivorship bias, or a genuinely independent walk-forward test.

Its chronological 70/30 split is a **later-window check** on the submitted path. It is not independent out-of-sample validation. Its random control is an available proxy based on the data supplied; it is not a full execution simulator.

## Calibration status

`VALIDATED` remains `False` until the score’s ordering has passed a documented external corpus test against independently labelled good and bad strategy examples. Public threshold changes must not silently flip this flag.

Future reproducible case studies should serve as regression examples, not an external calibration corpus.

## Changing a threshold or evidence rule

Any scoring-policy change must record:

- version and change rationale;
- affected grades and expected migration impact;
- before/after results for representative regression cases;
- tests covering the new rule;
- an entry in [CHANGELOG.md](../CHANGELOG.md).

The release process is defined in [release governance](release-governance.md).


## v0.4.0 boundaries

Only actual account returns/NAV receive account-path quality scores. Closed trades do not reveal account capital allocation or intra-trade MTM; they receive descriptive statistics and `ACCOUNT_PATH_REQUIRED`, with nullable scores and no metal tier. Overlapping, incomplete-time and multi-symbol logs are rejected instead of being compounded as a fictitious account.

The daily timing proxy is a screening comparison, not a position reconstruction. Regression beta is not measured occupancy. It preserves direction, uses a static beta reference, and assumes zero incremental reference cost; actual costs remain unknown. Near-zero, leveraged, saturated or insolvent references cannot qualify. A missing/unsupported random comparison or insufficient sample withholds the tier without reducing the path score. A passing proxy check is not a certification of timing skill. See [input and comparison contract](input-comparison-contract.md) for interval and missing-data rules.

`path_risk` excludes the search process. `overfit_risk` is a deprecated compatibility alias with the same restricted meaning. `n_trials=null` means unknown, not a verified count of one. The DSR is an approximation using the submitted curve's variance and capped positive skew; low DSR cannot establish the cause of an observed result. Historical bootstrap profit share is conditional on resampling the observed returns and is not a future forecast.

## Next independent pilot (not yet run)

Before accessing blind labels, lock the release tag/commit, rule ID, library versions, profile, self-reported/unknown search count, all RNG seeds, and the normalized input and benchmark hashes for each case. Register the 30 known-answer cases separately from the 50 blind strategies. The known cases test specified mathematical or data-handling properties; they do not estimate external predictive accuracy.

For the 50-strategy pilot, assign independent reviewers' labels before scoring, split by strategy family/source to avoid near-duplicate variants, and prohibit threshold tuning against these labels. Register exclusions and missing-data handling before inspecting scores; report N/A coverage separately from accepted-input results. Report the confusion table, case counts and uncertainty, not a population accuracy claim. If rules are changed after viewing the pilot, that corpus becomes development evidence and the next blind evaluation needs fresh families. Neither 30 nor 50 observations automatically changes `VALIDATED=False`.
