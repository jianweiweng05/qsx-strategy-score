# QSX Strategy Score

Free strategy auditor for trading backtests.

Status: public code release is being finalized. This repository currently hosts the landing README, methodology notes, and sample outputs before the first code release.

Upload a return curve, equity curve, or trade log. Get a fast **QSX Score** from 0 to 100, plus the checks that usually decide whether a backtest is worth more research.

- QSX Score and grade
- Overfit and too-good-to-be-true checks
- Buy-and-hold comparison
- Random timing test
- Monte Carlo stress test
- Shareable PNG scorecard
- Optional QSX Overlay Preview

Many strategies with a positive edge still fail because of poor risk sizing and exposure control. The optional Overlay Preview lets you test whether dynamic risk sizing may improve your own strategy.

![QSX Strategy Score sample outputs](assets/readme/sample-scorecard-overview.png)

## Overlay Preview

QSX Strategy Score can preview an external risk-sizing layer:

**QSX Crypto Universal Position Engine 1.0**

It is not an entry signal, exit signal, or coin selector. It is designed as an overlay that sits outside your original strategy:

```text
original strategy returns x QSX dynamic exposure = overlay-adjusted curve
```

Audited example from `qsx-lab`:

![QSX Overlay before and after](assets/readme/qsx-overlay-before-after.png)

Your result may differ. The purpose is to test whether the overlay improves risk-adjusted performance on your own strategy.

## CLI Preview

The public package is not released yet. The intended CLI interface is:

```bash
pipx install qsx-score-free
```

Score a strategy:

```bash
qsx-score examples/strategy_alpha.csv --asset BTC --lang en
```

Export a PNG scorecard and JSON report:

```bash
qsx-score examples/strategy_alpha.csv --asset BTC --out card.png --json report.json
```

Web app interface after the code release:

```bash
pip install -e ".[app,excel]"
streamlit run app/streamlit_app.py
```

## Example Result

```text
QSX Score: 59 / 100
Grade: NEEDS WORK

Headline:
Indistinguishable from random timing (p=0.32)
No proven timing edge.

Key problems:
- Max Drawdown: -83%
- Random timing test failed
- High dependency to buy-and-hold: corr +0.90, beta +0.82
```

This does not mean the strategy is useless. It means the uploaded return path looks more like asset beta plus risk exposure than proven timing edge.

## Input Formats

Returns:

```csv
date,return
2021-01-01,0.012
2021-01-02,-0.004
```

Equity curve:

```csv
date,equity
2021-01-01,10000
2021-01-02,10120
```

Trade log:

```csv
entry_time,exit_time,pnl_pct,side,symbol
2021-01-01,2021-02-01,3.2,LONG,DOGE
```

CSV, TSV, Excel, TradingView-style exports, return series, equity curves, and closed-trade logs are supported.

## Docs

- [Scoring model](docs/scoring.md)
- [QSX Overlay Preview](docs/overlay.md)
- [Privacy boundary](docs/privacy.md)
- [Methodology notes](docs/methodology.md)

## Free vs Pro

| Layer | Free | QuantScopeX Pro |
| --- | --- | --- |
| Role | Screening | Due diligence |
| Main question | Is this worth investigating? | What does it depend on, when does it fail, and can it be production-ready? |
| Input | Returns, equity, trade log | Strategy file, asset context, cost/execution assumptions |
| Output | Text, JSON, PNG scorecard | Deeper strategy due-diligence report |

Free = screening. Pro = due diligence.

## Important Limitations

QSX Strategy Score is computed from the uploaded performance path. It cannot prove that a backtest has no look-ahead bias, survivorship bias, unrealistic fills, hidden leverage, capacity issue, or in-sample selection.

A high score is not investment advice. A flagged score does not prove a strategy is fake; it means the backtest method should be checked before trusting the result.

## License

MIT.
