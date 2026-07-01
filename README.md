# QSX Strategy Score

[![tests](https://github.com/jianweiweng05/qsx-strategy-score/actions/workflows/tests.yml/badge.svg)](https://github.com/jianweiweng05/qsx-strategy-score/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9--3.12-blue.svg)](pyproject.toml)

Free open-source strategy auditor for trading backtests.

Public preview: usable now as a local CLI and Streamlit app. Scoring thresholds and the hosted Overlay Preview may still change before v1.0.

[Try without installing](https://www.quantscopex.com/tools?utm_source=github&utm_medium=readme&utm_campaign=qsx_strategy_score&utm_content=hosted_tool) ·
[Run Overlay Preview](https://www.quantscopex.com/tools?utm_source=github&utm_medium=readme&utm_campaign=qsx_strategy_score&utm_content=overlay) ·
[Full audit report](https://www.quantscopex.com/report?utm_source=github&utm_medium=readme&utm_campaign=qsx_strategy_score&utm_content=audit_report) ·
[Security](SECURITY.md)

Upload a return curve, equity curve, or trade log. Get a fast **QSX Score** from 0 to 100, plus the checks that usually decide whether a backtest is worth more research.

- QSX Score and grade
- Overfit and too-good-to-be-true checks
- Buy-and-hold comparison
- Random timing test
- Monte Carlo stress test
- Shareable PNG scorecard
- Localized CLI, PNG scorecard, and web output (`en`, `zh`, `ja`, `ko`, `es`, `pt-BR`)
- Optional QSX Overlay Preview

Many strategies with a positive edge still fail because of poor risk sizing and exposure control. The optional Overlay Preview lets you test whether dynamic risk sizing may improve your own strategy.

![QSX Strategy Score sample outputs](assets/readme/sample-scorecard-overview.png)

## Positioning

QSX Strategy Score is not a replacement for QuantStats, pyfolio, or a full research notebook.

Use QuantStats when you want a detailed performance tear sheet. Use QSX Strategy Score when you want a fast screening answer:

```text
Is this backtest worth deeper due diligence, or does it look fragile, lucky, overfit, or mostly beta?
```

The output is intentionally compact: one score, the main failure modes, a shareable scorecard, and an optional QSX Overlay Preview.

Scorecards link to a full audit-report workflow at `quantscopex.com/report` for users who want deeper due diligence after screening.

## Overlay Preview

QSX Strategy Score can preview an external risk-sizing layer:

**QSX Crypto Universal Position Engine 1.0**

It is not an entry signal, exit signal, or coin selector. It is designed as an overlay that sits outside your original strategy:

```text
original strategy returns x QSX dynamic exposure = overlay-adjusted curve
```

Research audit example:

![QSX Overlay before and after](assets/readme/qsx-overlay-before-after.png)

Your result may differ. The purpose is to test whether the overlay improves risk-adjusted performance on your own strategy.

Overlay Preview rejects trade logs with overlapping per-position trades. Upload an equity curve or daily return series so the preview uses the aggregate strategy path.

## Install and Run

From this repository:

```bash
git clone https://github.com/jianweiweng05/qsx-strategy-score.git
cd qsx-strategy-score
python -m pip install -e ".[app,excel]"
```

Score a strategy:

```bash
qsx-score examples/strategy_alpha.csv --asset BTC --lang en
```

Supported languages:

```bash
qsx-score examples/strategy_alpha.csv --lang zh
qsx-score examples/strategy_alpha.csv --lang ja
qsx-score examples/strategy_alpha.csv --lang ko
qsx-score examples/strategy_alpha.csv --lang es
qsx-score examples/strategy_alpha.csv --lang pt-BR
```

Export a PNG scorecard and JSON report:

```bash
qsx-score examples/strategy_alpha.csv --asset BTC --out card.png --json report.json
```

Run the web app:

```bash
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

- [Case studies: three backtests, three verdicts](docs/case-studies.md)
- [Scoring model](docs/scoring.md)
- [QSX Overlay Preview](docs/overlay.md)
- [Privacy boundary](docs/privacy.md)
- [Security policy](SECURITY.md)
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

Free = screening, not proof. QSX Strategy Score is computed from the uploaded performance path; it does not inspect strategy code, raw market data, execution simulation, exchange fills, or the full parameter-search process.

It cannot prove the absence of code-level look-ahead, survivorship bias, unrealistic fills or slippage, hidden leverage, capacity constraints, manual selection, or train/validation contamination.

A high score is not investment advice. A flagged score does not prove a strategy is fake; it means the backtest method should be checked before trusting the result.

## License

MIT.
