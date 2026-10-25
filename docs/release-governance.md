# Release governance

QSX Strategy Score is pre-v1.0. A release can change scoring behavior, but it must make the change visible and reproducible.

## When this policy applies

Follow this process for changes to score thresholds, caps, grades, tier eligibility, evidence rules, public headlines, or JSON semantics.

## Required release checks

1. Update [CHANGELOG.md](../CHANGELOG.md) with behavior and migration impact.
2. Update [calibration policy](calibration.md) if scoring or evidence semantics change.
3. Keep JSON changes additive where possible; document any changed meaning of an existing field.
4. Run `pytest -q` across the supported Python versions in CI.
5. Smoke-test CLI text, JSON, and PNG output for both benchmarked and unbenchmarked inputs.
6. Smoke-test each supported language and ensure no translation key falls back to its raw identifier.
7. Verify the Streamlit result path shows the right evidence state and next action.
8. Build source and wheel artifacts with `python -m build`.

## Release procedure

1. Merge the reviewed release commit to `main`.
2. Update the package version and changelog.
3. Create an annotated tag, for example `v0.2.0`.
4. Push the tag.
5. The tag workflow reruns tests, builds artifacts, uploads them to the workflow run, and creates the GitHub Release using the matching changelog section.
6. If the release workflow fails, do not retag silently. Fix the cause in a new commit, document the result, then create a corrective tag.

## Distribution status and PyPI prerequisites

The current `release.yml` builds wheel/sdist artifacts and attaches them to a **GitHub Release**. It has no PyPI upload step. As checked on 2026-10-25, the `qsx-score-free` PyPI JSON and simple-index endpoints returned 404. Use the tagged GitHub source-install instructions in the README until a registry release is verified; the package name in metadata is not proof of PyPI availability.

Before proposing a first PyPI publication:

1. Build from the reviewed release tag, check wheel/sdist metadata and install the wheel in an isolated environment. Confirm `qsx-score --version`, an unbenchmarked bundled example, and the account/trade N/A boundary.
2. Confirm the maintainer controls the target PyPI project name and has an authorized publishing method. No account, token, OAuth grant or Trusted Publisher is created by the current workflow; establishing one requires a separate owner decision. Do not expose existing credentials while checking readiness.
3. Obtain approval for the exact artifact version and publication target. Documentation-only fixes do not change the core version or silently replace existing v0.4.0 artifacts; a rebuilt distribution needs its own reviewed release identity.
4. After publication, verify the PyPI release and hashes, then install that exact version in a fresh environment before advertising a registry-only `pip install` command.

Core version (`qsx-score --version`), scoring-rule version and Chrome extension version are separate identities. Read the core version from the scoring response and the extension version from `chrome-extension/manifest.json`; verify the store listing separately.

## Proposed GitHub topics

Prepare these as separate topics, not one concatenated value: `python`, `quantitative-finance`, `algorithmic-trading`, `backtesting`, `strategy-analysis`, `risk-management`, `overfitting`, `deflated-sharpe-ratio`, `monte-carlo`, `tradingview`. This is a candidate list; changing repository metadata is a separate publishing action.

## Rollback

If a released scoring rule is materially wrong, publish a corrective release with clear migration notes. Do not hide the previous result: preserve its tag, explain the correction in the changelog, and add a regression case before reissuing the rule.
