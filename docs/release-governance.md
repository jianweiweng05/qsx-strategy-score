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

## Rollback

If a released scoring rule is materially wrong, publish a corrective release with clear migration notes. Do not hide the previous result: preserve its tag, explain the correction in the changelog, and add a regression case before reissuing the rule.
