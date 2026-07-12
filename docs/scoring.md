# Scoring Model

QSX Strategy Score is a fast screening layer for trading backtests. It reads a return curve, equity curve, or trade log and produces a 0-100 score with a plain-English verdict.

The free score is built around four questions:

1. Is the return path profitable and risk-adjusted enough to be worth investigating?
2. Does the curve look too clean, too concentrated, or too good to be true?
3. Is the drawdown profile acceptable for the reported return?
4. Does the strategy beat buy-and-hold and random timing when a benchmark is available?

The score is intentionally conservative. A backtest can have attractive returns and still be capped if it fails the random-timing test, depends heavily on buy-and-hold exposure, has too little sample, or looks implausibly smooth.

## Outputs

- QSX Score from 0 to 100
- Grade: GOLD, SILVER, BRONZE, NEEDS WORK, or FLAGGED
- Headline verdict
- Return quality score
- Overfit-risk detection
- Drawdown control score
- Edge vs buy-and-hold/random timing
- Sample sufficiency
- Edge persistence lite
- Dependency lite
- Monte Carlo stress summary
- JSON report
- Shareable PNG scorecard

## Evidence and grades

The 0-100 number is a **path-quality score**, not a certificate that a strategy has alpha.

- `GOLD`, `SILVER`, and `BRONZE` require a comparable asset benchmark, a completed available random-control check, adequate history/sample evidence, and a strategy that passes the available edge checks.
- `PROVISIONAL` means the return path can still have a useful numeric score, but required evidence such as a benchmark, comparable overlap, random-control result, or sufficient history is incomplete.
- `NEEDS WORK` and `FLAGGED` remain stronger negative outcomes: a material free check failed or the input needs methodology verification.

See the [calibration policy](calibration.md) for the full eligibility rules and known limits.

## Sample Scorecards

The README shows the compact overview. The full sample wall below shows four common outcomes: real edge candidate, beta trap, too-clean-to-trust, and benchmark-needed.

![QSX Strategy Score sample scorecards](../assets/readme/sample-scorecard-stack.png)

## Common Outcomes

`PASS` means the uploaded curve passed the available free checks. It still needs live or out-of-sample evidence before production use.

`NEEDS WORK` means the curve has a material weakness such as deep drawdown, weak timing evidence, high benchmark dependency, thin sample, or unstable return concentration.

`FLAGGED` means the curve looks suspicious enough that the backtest method should be checked before trusting any score.
