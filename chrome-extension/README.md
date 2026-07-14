# QSX Strategy Score

Version 1.2.0 adds a core-rendered PNG scorecard, a three-page free diagnostic PDF, native file sharing, X/LinkedIn/Reddit links, and optional email delivery. These artifacts call the official website endpoints and are generated from the same public scoring core as the CLI and website.

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
- the same score, evidence status, overfit-risk index, and result route as the website
- smart Crypto Universal Overlay / Pro CTA routing with UTM parameters
- native scorecard sharing and X / LinkedIn / Reddit share actions
- PNG scorecard and three-page free diagnostic PDF downloads
- optional email delivery of both files with separate marketing consent

## Install For Local Testing

1. Open `chrome://extensions/`.
2. Enable Developer mode.
3. Click **Load unpacked**.
4. Select `/Users/admin/free-score/chrome-extension`.
5. Open the extension popup and upload a strategy file.

## Chrome Web Store Checklist

- `manifest.json` host permissions include only `https://www.quantscopex.com/*`
- icons exist at 16x16, 48x48, and 128x128
- popup uses the website's `/api/score` proxy
- screenshots show upload, result, and next-step routing
- privacy policy discloses that user-selected files are uploaded to the hosted scoring API

## Privacy

The scoring API receives strategy files that users explicitly select and submit. See [Privacy Policy](../docs/privacy.md).
