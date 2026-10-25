# QSX Strategy Score

This repository contains extension **1.4.0** (`manifest.json`). It displays results from the hosted API, whose response identifies the scoring core separately (current released core: **v0.4.0**). Extension and core version numbers are independent. The store listing may publish a different extension version; the 2026-10-06 submission receipt recorded 1.4.0 pending review and 1.3.2 public, not today's store status.

Account returns and NAV receive supported historical screening checks. Accepted closed-trade logs show descriptive statistics only: account score/risk/ratings and Overlay are N/A. Results and artifacts support `en`, `zh`, `ja`, `ko`, `es`, and `pt-BR`; account diagnostic PDFs have three pages and descriptive trade PDFs have one.

Chrome extension for scoring strategy files with QSX Strategy Score.

Install the official, completely free Chrome extension from the Chrome Web Store:

https://chromewebstore.google.com/detail/qsx-strategy-score/ledfoflekcjogmfnmomcnlkinfpblgck

The popup also links to the free open-source Crypto Top/Bottom Risk Radar on TradingView:

https://www.tradingview.com/script/nY7jGyZu/

## Production Use

The production extension sends selected files to:

```text
https://www.quantscopex.com/api/score
```

The extension supports:

- CSV, TSV, TXT, and Excel strategy files
- return series, equity curves, and closed-trade logs
- common backtest exports from tools that can produce tabular strategy results
- automatic asset detection
- manual benchmark asset selection
- optional custom benchmark/K-line upload with `date + close/price`
- the same account score, evidence status, path-risk index (excluding search risk), and result route as the website
- next steps to collect free evidence, run an eligible Overlay Preview, or explore a $99 one-time Pro Audit, with UTM parameters
- native scorecard sharing and X / LinkedIn / Reddit share actions
- PNG scorecard and free diagnostic PDF downloads
- optional email delivery of both files with separate marketing consent

## Install For Local Testing

1. Open `chrome://extensions/`.
2. Enable Developer mode.
3. Click **Load unpacked**.
4. Select the `chrome-extension` directory inside your local checkout of this repository.
5. Open the extension popup and upload a strategy file.

## Chrome Web Store Checklist

- `manifest.json` host permissions are limited to the official website and TradingView; the scoring API is on `https://www.quantscopex.com/*`
- icons exist at 16x16, 48x48, and 128x128
- popup uses the website's `/api/score` proxy
- screenshots show upload, result, and next-step routing
- privacy policy discloses that user-selected files are uploaded to the hosted scoring API

## Privacy

The scoring API receives strategy files that users explicitly select and submit. See [Privacy Policy](../docs/privacy.md).
