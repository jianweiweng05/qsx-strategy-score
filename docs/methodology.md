# Methodology Notes

QSX Strategy Score is a screening tool, not proof that a strategy is production-ready.

It can identify common warning signs from the performance path:

- Weak or missing edge against buy-and-hold
- Proxy random-control checks when an appropriate benchmark is available
- Excessive drawdown
- Suspiciously smooth or too-good-to-be-true curves
- Return concentration
- Thin sample
- High benchmark dependency
- Weak recent persistence

It cannot prove that a backtest has no look-ahead bias, survivorship bias, hidden parameter search, unrealistic fills, missing fees, leverage issues, or capacity limits. Its chronological 70/30 split is only a later-window check on the uploaded path, not independent walk-forward validation.

## Recommended Use

Use the free score as a first-pass filter:

1. Upload the strategy return path.
2. Check whether the score and headline are credible.
3. Review drawdown, random timing, benchmark dependency, and concentration warnings.
4. If the strategy has positive edge but poor exposure behavior, test Overlay Preview.
5. Only move promising candidates into deeper due diligence.

Free = screening. Pro = due diligence.
