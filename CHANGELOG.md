# Changelog

All notable user-visible changes are recorded here. Before `v1.0`, scoring-policy changes may alter the displayed grade for the same input.

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
