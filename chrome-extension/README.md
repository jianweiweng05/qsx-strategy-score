# QSX Strategy Score

Version 1.3.2 completes Chinese, Japanese, Korean, Spanish, and Brazilian Portuguese result and artifact delivery, including dynamic anomaly messages and localized sample units. Grade, edge, headline, sharing controls, PNG, and the three-page PDF now keep the selected language. PDF files use the corrected measured-width CJK layout from public core v0.3.4.

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
