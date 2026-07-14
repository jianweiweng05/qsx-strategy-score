# QSX Strategy Score Chrome Web Store Listing

## Package

Upload:

```text
/Users/admin/free-score/dist/qsx-strategy-score-chrome-v1.1.0.zip
```

## Product Details

Title from package:

```text
QSX Strategy Score
```

Summary from package:

```text
Score trading strategy exports in 3 seconds. Overfit detection, drawdown risk, and edge vs random timing.
```

Description:

```text
QSX Strategy Score is a free strategy scorecard for traders and quant researchers.

Upload a CSV, TSV, TXT, or Excel strategy file and get a fast 0-100 score with practical diagnostics:

- Return quality, drawdown control, and overfit-risk checks
- A low-is-safer overfit-risk index shared with the QuantScopeX website
- Risk-adjusted return, buy-and-hold, and random-timing evidence when available
- Buy-and-hold benchmark comparison when an asset or price/K-line file is available
- Smart next-step routing to add evidence, QSX Overlay Preview, or Pro Strategy Audit

Supported input shapes include:

- Return series
- Equity or NAV curves
- Closed-trade logs
- Common tabular backtest exports from tools that can export CSV or Excel

Optional benchmark support:

You can let QSX auto-detect the traded asset, manually select a benchmark asset, or upload a custom price/K-line file with date and close/price columns. This helps compare the strategy against buy-and-hold and random timing instead of judging the backtest in isolation.

What this extension does not do:

- It does not place trades.
- It does not connect to broker accounts.
- It does not read passwords, cookies, browsing history, or account credentials.
- It only uploads files that you explicitly select and submit for scoring.

QSX Strategy Score is a screening tool, not investment advice. It measures historical or simulated strategy evidence and cannot predict future returns.
```

Category:

```text
Productivity
```

Language:

```text
English (United States)
```

Official website:

```text
https://www.quantscopex.com
```

Homepage URL:

```text
https://www.quantscopex.com/score
```

Support URL:

```text
https://www.quantscopex.com/faq
```

Mature content:

```text
Off / No
```

## Images

Store icon:

```text
/Users/admin/free-score/chrome-store-assets/store-icon-128.png
```

Screenshots, upload in this order:

```text
/Users/admin/free-score/chrome-store-assets/screenshot-01-upload-1280x800.png
/Users/admin/free-score/chrome-store-assets/screenshot-02-scorecard-1280x800.png
/Users/admin/free-score/chrome-store-assets/screenshot-03-risk-cases-1280x800.png
/Users/admin/free-score/chrome-store-assets/screenshot-04-overlay-path-1280x800.png
/Users/admin/free-score/chrome-store-assets/screenshot-05-smart-cta-1280x800.png
```

Small promo tile:

```text
/Users/admin/free-score/chrome-store-assets/promo-small-440x280.png
```

Marquee promo tile:

```text
/Users/admin/free-score/chrome-store-assets/promo-marquee-1400x560.png
```

Promo video:

```text
Leave blank for first submission.
```

## Privacy

Single purpose:

```text
QSX Strategy Score lets users upload a strategy file they choose and receive an overfit-aware strategy scorecard with risk, benchmark, and random-timing diagnostics.
```

Permission justification for `storage`:

```text
The extension uses Chrome storage only to remember user preferences such as API URL, selected language, and selected benchmark asset between sessions. It does not store uploaded strategy files after scoring.
```

Host permission justification for `https://www.quantscopex.com/*`:

```text
The extension sends user-selected strategy files and optional benchmark files to the QSX Strategy Score endpoint so the server can return the requested scorecard, evidence status, overfit-risk index, and benchmark comparison.
```

Host permission justification for `https://www.tradingview.com/*`:

```text
The extension injects its QSX Strategy Score button and upload dialog only on TradingView pages. It does not read account credentials, cookies, or private messages.
```

Privacy policy URL:

```text
https://www.quantscopex.com/privacy/chrome-extension
```

Data usage / privacy practice answers:

```text
User-provided content / User generated content: Yes
Reason: users select and upload strategy files and optional benchmark files for scoring.

Personally identifiable information: No
Health information: No
Authentication information: No
Personal communications: No
Location: No
Web history: No
User activity: No
Website content: No

Financial and payment information:
- Prefer "No" if the form has a separate User-provided content category, because the extension does not collect payment cards, bank accounts, or billing data.
- Use "Yes" only if Chrome's form treats user-uploaded trading/PnL files as financial information and gives no better category.
```

If Chrome asks whether the extension collects or transmits user-provided content, disclose:

```text
Yes. The extension transmits user-selected strategy files and optional benchmark files to https://www.quantscopex.com/api/score only after the user explicitly chooses a file and starts scoring. Files are used to generate the scorecard, evidence status, overfit-risk index, and benchmark comparison and are not sold.
```

Data use certification:

```text
Certify / agree.
```

Remote code:

```text
No remote code. The extension package contains all extension JavaScript. The API returns JSON score results, not executable code.
```

## Distribution

Visibility:

```text
Public
```

Regions:

```text
All regions
```

Pricing:

```text
Free
```

## Testing Instructions

```text
1. Install the extension and click the QSX Strategy Score toolbar icon.
2. Keep the default API URL: https://www.quantscopex.com.
3. Upload a CSV, TSV, TXT, or Excel strategy file such as a return series, equity curve, or closed-trade log.
4. Optionally select a benchmark asset or upload a price/K-line file with date and close/price columns.
5. Click Score strategy.
6. The extension displays a 0-100 score, grade, return quality, overfit risk, drawdown control, benchmark evidence, and recommended next step.
```

Test account:

```text
Not required. No login is needed.
```

## Version 1.1.0 Update Notes

```text
Version 1.1.0 moves the extension onto the same hosted scoring contract used by the QuantScopeX website. It replaces the legacy API route with the website score endpoint, aligns the displayed overfit-risk scale so lower values indicate lower risk, and adds the TradingView content-script registration required for the in-page score button.
```
