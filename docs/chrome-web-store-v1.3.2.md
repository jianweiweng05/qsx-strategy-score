# Chrome Web Store submission - 1.3.2

## Upload package

- File: `dist/qsx-strategy-score-chrome-v1.3.2.zip`
- SHA-256: `b2c46de35893a23d86581aea85cb1db2d66afe549bbb33a53c3ea44deb391800`
- Source commit: `3804e997f5f3ae676174c833170042f8a2f82113`

## What's fixed

Version 1.3.2 is the complete multilingual correction package. It includes the 1.3.1 service-backed localization of dynamic anomaly and risk messages, and removes the remaining English `bars` unit from Japanese, Korean, Spanish, and Brazilian Portuguese result metadata.

The selected language now covers the result headline, grade, pillars, sample units, dynamic flags, sharing, PNG, PDF, and email artifacts. The hosted scoring service runs public core `v0.3.4` and returns `msg_local`, `problem_local`, and `direction_local` while preserving stable English machine fields.

## Verification

- Public core tests: `54 passed`.
- Live `/api/score` smoke passed for `zh`, `ja`, `ko`, `es`, and `pt-BR` using the flagged sample.
- Chrome locale/version tests and Node syntax checks passed.
- ZIP integrity passed; manifest version is `1.3.2`.
