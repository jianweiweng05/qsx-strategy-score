# Security Policy

## Supported Scope

QSX Strategy Score is an open-source local scorer. The core 0-100 score runs on the user's machine from the uploaded return, equity, or trade-log file.

The optional QSX Overlay Preview is different: it calls the QuantScopeX hosted preview API.

## Data Boundary

For QSX Overlay Preview, the app normalizes the upload locally before any network call.

```text
Only normalized date-return series are transmitted.
Raw files, filenames, strategy code, trade logs and account information remain local.
```

The open-source app also sends lightweight request headers such as client version, source, language, and an input checksum so QuantScopeX can monitor GitHub-driven usage and API reliability without receiving raw files.

## Reporting a Vulnerability

Please report security issues privately instead of opening a public GitHub issue.

Email: security@quantscopex.com

Include:

- A short description of the issue
- Steps to reproduce
- The affected version or commit
- Whether the issue involves local scoring, file parsing, or the hosted Overlay Preview API

We will acknowledge valid reports as soon as practical and prioritize issues that could expose raw uploads, strategy code, account information, or hosted API misuse.

## Responsible Use

Do not upload account exports, API keys, secrets, private keys, brokerage credentials, or personally identifiable information. The scorer only needs returns, equity, or trade-level performance fields.
