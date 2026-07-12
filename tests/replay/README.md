# Replay test bags (P0.1)

Place curated `*.mcap` field bags here and committed baseline metrics under
`baselines/<bagname>.json`. `replay-ci.yml` runs `tools/metrics_extractor.py`
against each and fails the PR on regression.

**Do not commit large bags to git.** Use DVC or Git-LFS, or fetch from an
artifact/object store in CI. This directory is a placeholder for the wiring.
