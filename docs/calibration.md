# Calibration policy

QSX Strategy Score is a **screening** tool for a return curve, equity curve, or closed-trade log. It helps decide whether a backtest deserves more investigation. It does not certify alpha or production readiness.

## What the score means

The 0–100 number is a **path-quality score**. It summarizes return quality, plausibility/overfit signals, and drawdown control in the uploaded path.

The grade separately describes whether the free evidence is sufficient to earn a public tier:

- `GOLD`, `SILVER`, `BRONZE`: the path passed the available free evidence gates.
- `PROVISIONAL`: the path may have a useful score, but key evidence is missing or incomplete.
- `NEEDS WORK`: a material free check failed.
- `FLAGGED`: the path looks implausible enough that the backtest method should be verified before trusting any score.

## Evidence required for a metal tier

A metal tier requires all of the following:

1. A comparable asset benchmark with adequate overlap.
2. A completed random-control check on that comparison.
3. A result that beats buy-and-hold and the available random control.
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
