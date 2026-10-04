# Changelog

All notable user-visible changes are recorded here. Before `v1.0`, scoring-policy changes may alter the displayed grade for the same input.

## v0.4.0 — Account-path boundaries and matched daily comparisons

### Changed

- Closed-trade logs now return descriptive trade statistics only. `overall`, `display`, all quality pillars and path risk are `null`; no account CAGR, MTM drawdown, Monte Carlo, timing qualification or metal tier is inferred. Trade-log PNG/PDF exports show the same N/A boundary (one descriptive PDF page).
- Reject overlapping or multi-symbol logs, missing/reversed trade times, conflicting duplicate timestamps, non-finite observations, and returns at or below -100%. Exact duplicate period rows may be removed with an accurate count. No clipping of genuine losses or silently discarded invalid observations.
- Benchmark comparisons use common observed daily NAV endpoints in UTC before calculating returns. Mixed or incomplete intraday returns are rejected before account scoring, with or without a benchmark. Incompatible day cutoffs make the comparison unavailable. The benchmark, dependency read and random proxy use the same paired intervals.
- The random timing proxy preserves beta direction, requires both a daily same-beta static reference and, for intraday data, a matching native-frequency static reference, includes the first interval, and adds no asymmetric default transaction cost. It supports `0.15 <= abs(beta) < 1` only; unsupported, saturated, insolvent or degenerate references return N/A and cannot qualify for a metal tier. Finite-simulation tails use `(exceedances + 1) / (simulations + 1)`.
- Missing random evidence and insufficient samples no longer impose a score cap. Passing daily proxies is explicitly not a certification of timing skill. Other observed failures still apply. Filename/column-name hints cannot trigger a leakage penalty; a caller-confirmed `known_lookahead=True` can.
- Rename the displayed composite risk to **path risk (excludes search)**. Add JSON `path_risk`; retain `overfit_risk` as a deprecated equal-valued alias. Search trials default to unknown (`null`), with `search_trials_status` and a short DSR approximation note. An explicit count of 1 remains distinct from unknown.
- Disable trade-log Overlay Preview at both the UI and conversion entry point. Require an actual account return/NAV path.
- Cap Monte Carlo array sizes before allocation. Oversized requests return N/A with a reason; historical resampling profit share is not labelled a future probability.

### Reproducibility and migration

- Package/build/CLI core identity now share `_version.py` (`0.4.0`). Reports include the frozen rule ID, random seed, normalized input hash and benchmark snapshot hash. The Overlay request also reports the actual core version.
- Consumers must accept nullable scores and display N/A rather than converting null to zero. Do not reconstruct account metrics or equity from `closed_trade` returns downstream. Default omitted search counts to unknown.
- Chrome 1.4.0 source adapts nullable scores, path-risk labels and unknown search counts. Hosted service and site adapters are released separately from this package.
- The A–G synthetic regression families are required passing tests, not xfails. `VALIDATED` remains `False`; the planned 30 known cases and 50 independent blind strategies have not been evaluated. See [calibration policy](docs/calibration.md).

## Chrome 1.3.2 - Localized sample units

### Fixed

- Replaced the remaining English `bars` unit in Japanese, Korean, Spanish, and Brazilian Portuguese result metadata.

## Chrome 1.3.1 - Localized dynamic diagnostics

### Fixed

- Chrome now receives localized anomaly and risk messages from the shared service for all six supported languages, including autocorrelation, Sharpe, smoothness, CAGR, Calmar, and growth checks.

## v0.3.4 — Localized dynamic diagnostic flags

### Fixed

- Added selected-language text for dynamic anomaly flags (autocorrelation, Sharpe, smoothness, CAGR, Calmar, and growth) across the service, website, and Chrome extension.
- Preserved stable English machine messages while exposing `msg_local`, `problem_local`, and `direction_local` for clients.

## Chrome 1.3.0 - Complete multilingual artifacts

### Fixed

- Chinese, Japanese, Korean, Spanish, and Brazilian Portuguese now keep the selected language across score results, native/social sharing, PNG, PDF, and email artifact requests.
- Downloaded PDFs use the public core v0.3.3 measured-width CJK wrapping, punctuation-aware line breaking, and six-language headings.
- Added release regressions for language forwarding, localized result labels, and package version consistency.

## v0.3.3 — CJK punctuation line breaking

### Fixed

- Chinese closing punctuation now stays with the preceding line, so PDF headlines do not begin a line with a comma or full stop.

## v0.3.2 — PDF layout and multilingual artifact fix

### Fixed

- Free PDF text now wraps by measured font width, so long Chinese headlines and findings stay inside their panels.
- Findings advance by their rendered line count instead of fixed character assumptions.
- Japanese and Korean PDF font embedding no longer fails on CJK system fonts.
- All six supported languages now localize the PDF's fixed headings, metric labels, boundaries, and metadata.

## v0.3.1 — Complete multilingual score delivery

### Fixed

- Japanese, Korean, Spanish, and Brazilian Portuguese now keep their selected language through the Chrome score, scorecard, and PDF flows.
- Localized grade, edge, artifact, and headline fallbacks in both extension surfaces.
- Added regression coverage for all supported locales.

## Chrome 1.2.0 - Share and PDF delivery

### Added

- Native scorecard sharing plus X, LinkedIn, and Reddit actions.
- Direct PNG and three-page free diagnostic PDF downloads.
- Optional email delivery of both artifacts with separate marketing consent.
- All artifacts remain server-rendered by the same public scoring core as GitHub and the website.

## v0.3.0 — Shareable free diagnostic artifacts

### Added

- A three-page free diagnostic PDF generated by the same public scoring core as the CLI, PNG card, website, and Chrome extension.
- CLI `--pdf` export and Streamlit PNG/PDF download controls.

### Boundaries

- The free PDF summarizes the existing free result only. Execution-cost stress, regime attribution, peer ranking, capacity, and deployment readiness remain part of the Pro due-diligence report.

## v0.2.4 — Unified overfit-risk contract

### Added

- The score JSON now publishes `overfit_risk`, the same low-is-safe ordinal index shown on the shareable scorecard. Hosted clients should use this field instead of reinterpreting the positive `Credibility` pillar.

## v0.2.3 — Overfit-risk display scale

### Fixed

- The shareable scorecard now displays overfit risk on a risk-native scale: lower is safer. A credibility score of `99/100` therefore renders as `Overfit risk 1/100` in green.
- This is a display-only correction. It does not change the credibility pillar, overall score, grade, tier, or any scoring gate.

## v0.2.2 — CI correction

### Fixed

- Made the new qualified-evidence regression fixtures self-contained instead of depending on an optional bundled ETH price library. This restores clean CI installs and allows the release workflow to build the intended `0.2.2` package.

## v0.2.0 — Evidence-aware screening

### Changed

- A high path-quality score without comparable benchmark evidence now shows `PROVISIONAL`, not `GOLD`, `SILVER`, or `BRONZE`.
- Metal tiers now require a comparable benchmark, a completed available random-control check, adequate sample/history, and a demonstrated edge in the free checks.
- Headlines now describe benchmark and random timing as the available checks they are. Passing them still requires independent validation before deployment.
- The free 70/30 chronological split is described as a later-window check, not independent out-of-sample validation.

### Added

- Additive JSON fields: top-level `evidence`, `meta.candidate_tier`, `meta.evidence`, and `triage.next_step`.
- Result routing that first asks users to add free evidence, then recommends Overlay Preview for qualified risk-path questions or Pro for deeper due diligence.
- Public calibration and release-governance documentation.

### Migration note

An earlier high unbenchmarked result may now display the same numeric path-quality score with `grade: "PROVISIONAL"` and `tier: null`. This is intentional: it distinguishes an attractive curve from a fully evidenced strategy.
