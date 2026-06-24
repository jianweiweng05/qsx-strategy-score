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

## Audited Example

From the internal `qsx-lab` audit:

```text
Universe: Top150 liquidity crypto, >=730 daily bars, 65 assets
Execution: delay-1, 10 bps turnover cost

Before Overlay
CAGR: 31.2%
Max Drawdown: -81.8%
Calmar: 0.38
Avg Exposure: 100.0%

After Overlay
CAGR: 38.2%
Max Drawdown: -55.6%
Calmar: 0.69
Avg Exposure: 48.4%
```

Your result may differ. The purpose is to test whether the overlay improves risk-adjusted performance on your own strategy.

## Preview Scope

The open-source repository does not include the production controller sequence or private overlay engine. The preview is designed as a hosted lite simulation so users can test whether their own uploaded return path is a promising Overlay candidate.
