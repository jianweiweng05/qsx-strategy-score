# QSX Overlay Preview

Many strategies with a positive edge still fail because of poor risk sizing and exposure control. QSX Overlay Preview tests whether an external dynamic exposure layer may improve the risk-adjusted performance of your uploaded strategy.

The preview is based on:

**QSX Crypto Universal Position Engine 1.0**

It is not a new entry signal, exit signal, or coin selector. It is intended to work as a risk-control layer outside the original strategy.

```text
original strategy returns x QSX dynamic exposure = overlay-adjusted curve
```

## What It Changes

The overlay does not rewrite your strategy logic. It changes exposure outside the strategy according to crypto market state.

Typical intent:

- Reduce exposure during high-risk, high-volatility, falling, or unstable regimes
- Restore exposure when market conditions improve
- Reduce the damage from deep drawdown periods
- Let the original strategy keep its own alpha while adding risk governance outside it

## Evidence and next step

Use the website's [published Controller evidence](https://www.quantscopex.com/tools?utm_source=github&utm_medium=docs&utm_campaign=qsx_strategy_score&utm_content=overlay_evidence) for the model version, data cutoff, asset coverage, costs and limitations. Old research-model figures are not interchangeable with the current subscription model. A historical improvement on one path does not guarantee future improvement.

The compatibility Preview is free and optional. The separate Risk Controller subscription ($79/month or $799/year) provides current model exposure, risk state and real change alerts. The $99 Pro Audit is a one-time strategy diagnosis, not a prerequisite or a monthly plan. BTC/ETH research ($149/month) includes Controller access; do not apply the Controller again to that model's final weights.

## Preview Scope

The open-source repository does not include the production controller sequence or private overlay engine. The preview is designed as a hosted lite simulation so users can test whether their own uploaded return path is a promising Overlay candidate.

All closed-trade logs are excluded from Overlay Preview, including sequential nonoverlapping trades. Trade endpoints cannot recover the intervening account drawdown. Supply actual account NAV or complete daily account returns, with consistent capital-flow treatment; do not geometrically interpolate trade PnL into daily returns. Unsupported or insufficient evidence remains N/A. See the [input contract](input-comparison-contract.md).
