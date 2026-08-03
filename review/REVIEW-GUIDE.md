# Independent Review Guide

This package is for anyone conducting an external, independent review of
Ontario Home Energy Futures — a consumer advocate, a regulator, a climate
or lifecycle specialist, an equity advocate, an accessibility expert, or a
sceptical resident. It does not assume you trust this project's own
self-assessment in [docs/RED-TEAM-REVIEW.md](../docs/RED-TEAM-REVIEW.md);
it is designed to let you check the project's claims yourself.

## What you can do with this package

- **Reproduce standard results.** See "Reproduce a result" below.
- **Inspect assumptions.** Every default lives in
  [data/governance/assumptions.yaml](../data/governance/assumptions.yaml)
  (a curated register) and the underlying `assumptions/*.yaml` files (the
  actual source the code reads) — nothing is hidden in source code.
- **Challenge claims.** Every significant claim is listed in
  [data/governance/claims.yaml](../data/governance/claims.yaml) with its
  source, status, and review date. If you believe a claim is wrong,
  outdated, or overstated, see "Report an error" below.
- **Test adverse scenarios.** The test suite (`tests/`) already includes
  scenarios where solar, batteries, and immediate purchase all lose (see
  [SAMPLE-SCENARIOS.md](SAMPLE-SCENARIOS.md)) — you can run these
  yourself and inspect the actual numbers.
- **Identify hidden optimism.** Use the persona-specific question sets in
  this folder as a checklist against the live application and its source.
- **Report an error.** See [docs/CORRECTIONS.md](../docs/CORRECTIONS.md).
- **Propose alternative assumptions.** Every assumption is in an editable
  YAML file — you can fork the repository, change a value, rebuild, and
  compare results directly.
- **Review environmental claims.** See
  [docs/ENVIRONMENTAL-CLAIMS-POLICY.md](../docs/ENVIRONMENTAL-CLAIMS-POLICY.md)
  — as of this version, the application makes none, which you can verify
  by searching the `web/templates/` directory yourself.
- **Review distributional effects.** See
  [docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md](../docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md).

## Reproduce a result

```bash
git clone https://github.com/mgifford/ontario-home-energy-futures
cd ontario-home-energy-futures
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v            # run the full test suite; every number in this
                      # project should be traceable to a test or a
                      # documented, sourced assumption
python build.py      # build the static site offline from committed
                      # fixtures - no network access is used or required
```

The build is fully offline and deterministic: the same commit, the same
`assumptions/`/`scenarios/` files, and the same fixtures should always
produce the same `dist/` output. If you get a different result from the
same inputs, that itself is a finding worth reporting.

## Where to start, by persona

- **Consumer advocate:** [CONSUMER-ADVOCATE-QUESTIONS.md](CONSUMER-ADVOCATE-QUESTIONS.md)
- **Regulator:** [REGULATORY-QUESTIONS.md](REGULATORY-QUESTIONS.md)
- **Climate/lifecycle specialist:** [CLIMATE-REVIEW-QUESTIONS.md](CLIMATE-REVIEW-QUESTIONS.md)
- **Equity advocate:** [EQUITY-REVIEW-QUESTIONS.md](EQUITY-REVIEW-QUESTIONS.md)
- **Accessibility expert:** [ACCESSIBILITY-REVIEW-QUESTIONS.md](ACCESSIBILITY-REVIEW-QUESTIONS.md)
- **Anyone wanting worked examples first:** [SAMPLE-SCENARIOS.md](SAMPLE-SCENARIOS.md)

## What this project already knows it has not done

Read [docs/RED-TEAM-REVIEW.md](../docs/RED-TEAM-REVIEW.md)'s "Deferred to
next phase" table before spending time re-discovering a gap this project
has already named. Your review is most valuable where it finds something
*not* already listed there, or where it disagrees with this project's own
severity/status assessment of a listed item.

## This project does not claim to be unbiased

It documents its purpose, its assumptions, its governance, its known
biases and gaps, the evidence supporting it, the evidence it lacks, and
the decisions it should not be used to make — see
[MODEL_CARD.md](../MODEL_CARD.md). Your review should test whether that
self-description is accurate, not assume it is.
