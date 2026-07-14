# Chrome Web Store submission - 1.2.0

## Upload package

- File: `dist/qsx-strategy-score-chrome-v1.2.0.zip`
- Size: 56,755 bytes
- SHA-256: `9a1cc340fb907a01a0f446597299cddb3e663213ad3200c97fbe1fead640b2b7`
- Source commit: `fccbc9e4cb42a586a9a383e784ede3ae6bc9d897`

## What's new

Version 1.2.0 adds native sharing for the strategy scorecard, direct PNG and three-page PDF downloads, X/LinkedIn/Reddit share actions, and optional email delivery of both files. Email delivery is transactional; product updates require a separate optional checkbox. Scoring and artifacts use the same public QSX scoring core as GitHub and quantscopex.com.

## Single purpose

QSX Strategy Score lets a user upload a tabular strategy backtest and receive a free, overfitting-aware strategy score, benchmark comparison, and diagnostic result. Version 1.2.0 only adds ways to save or share that same result.

## Permission justification

- `storage`: saves the user's API base and language preference locally.
- `https://www.quantscopex.com/*`: calls the official scoring, scorecard, PDF, and optional email-delivery endpoints.
- `https://www.tradingview.com/*`: supports the existing TradingView page integration and free indicator link.

No new permission was added in 1.2.0. The extension does not execute remote code.

## Data handling disclosure

The strategy file and optional benchmark are sent only after an explicit scoring, share, download, or email action. Raw uploads are parsed in memory and are not retained by the scoring service. An email address is sent only when the user requests email delivery. It is added to the product-update contact list only when the separate marketing checkbox is selected.

Privacy policy: `https://www.quantscopex.com/privacy/chrome-extension`

## Reviewer steps

1. Open the extension popup.
2. Upload a CSV return series, equity curve, or closed-trade log.
3. Click **Score strategy** and wait for the result.
4. Use **PNG** or **3-page PDF** to verify downloads.
5. Use **Share scorecard**; unsupported desktop share environments fall back to a PNG download.
6. X, LinkedIn, and Reddit open their official share composers for the QuantScopeX score page.
7. Email delivery is optional and sends the PNG and PDF generated from the same uploaded result.
