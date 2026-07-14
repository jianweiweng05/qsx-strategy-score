# Privacy Policy

QSX Strategy Score analyzes strategy files that users choose to upload.

## Data Sent To The API

When you click **Score strategy** in the Chrome extension, the selected strategy file is sent to the QSX Strategy Score endpoint at `https://www.quantscopex.com/api/score` so the server can parse it and generate the score and benchmark comparison. Supported inputs include return series, equity curves, closed-trade logs, and tabular backtest exports. If you upload a custom benchmark/K-line file, that file is sent in the same request.

After scoring, the extension can request a shareable PNG scorecard or three-page PDF from `https://www.quantscopex.com/api/score/card` and `/api/score/pdf`. These requests resend the selected strategy and optional benchmark only when you click the corresponding share or download action. If you explicitly request email delivery, the same files and the email address you enter are sent to `/api/score/email`; the generated PNG and PDF are attached to that email. Product updates are optional and require a separate checkbox.

The extension also sends the selected language and optional benchmark asset symbol.

## Data Use

Uploaded files are used only to generate the requested strategy score and diagnostic response. QuantScopeX does not sell uploaded strategy files, trade logs, or benchmark files.

The API may keep ordinary server security logs, such as request timestamps, IP address, response status, and error diagnostics, for operations and abuse prevention.

## Data Retention

The scoring API processes uploaded files in memory for the request. The extension does not intentionally store uploaded files after scoring. Server logs may be retained for security and reliability monitoring.

## User Control

Files are uploaded only after the user selects a file and starts scoring. Users can avoid sending files to the hosted API by not using the Chrome extension scoring action.

## Overlay Preview Boundary

For QSX Overlay Preview and future Pro workflows, QuantScopeX may use a reduced `date,return` series or require a separate upload flow depending on the product page. Those flows should disclose their own upload boundary at the point of use.

See [Security Policy](../SECURITY.md) for vulnerability reporting and hosted API security details.
