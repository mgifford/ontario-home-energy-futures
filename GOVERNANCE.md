# Governance

This document describes how Ontario Home Energy Futures is maintained,
reviewed, and held accountable. It exists so a household, a regulator, an
advocate, or a contributor can understand who is responsible for a claim
in this tool and how to challenge or correct it.

## Public source code

The complete source code, build pipeline, and static-site output are
public in this repository. There is no closed component: the calculation
model, the assumptions, the scenario definitions, and the site-generation
code are all in the same public tree — nothing that affects a result is
hidden behind a private service or a proprietary calculation.

## Public model version

Every generated page displays a `model_version` and a `data_cutoff` date
in its footer (see `src/ontario_home_energy_futures/site/context.py`).
See [MODEL_CARD.md](MODEL_CARD.md) "Versioning" for the current
limitation that this version string is manually maintained and does not
yet automatically reflect every underlying change.

## Public assumptions

Every default numeric assumption used in a calculation lives in an
editable YAML file under `assumptions/` or `scenarios/` — never hardcoded
in Python, JavaScript, or a template (see
[CONTRIBUTING.md](CONTRIBUTING.md) "Ground rules"). The
[data/governance/assumptions.yaml](data/governance/assumptions.yaml)
register additionally records each assumption's confidence profile and
what it affects.

## Dated data sources

Every imported observation and every source file carries a `retrieved_at`
and (where applicable) `published_at` date, and a SHA-256 hash recorded in
`data/source-manifest.yaml` (see
`src/ontario_home_energy_futures/validate/provenance.py`). A raw source
file is never silently replaced — a revision is recorded as a new,
separately hashed entry.

## Historical scenario retention

Published scenario files (`scenarios/*.yaml`) are never edited in place.
A revision creates a new file with a `supersedes` field pointing to the
version it replaces (see [README.md](README.md) "Adding or revising
scenarios" and [CONTRIBUTING.md](CONTRIBUTING.md)). This means a past
projection remains inspectable exactly as it was published, and a future
"forecast versus actual" comparison (planned, not yet built) will be
possible without rewriting history.

## Changelog

[CHANGELOG.md](CHANGELOG.md) records notable changes by version. Every
release-worthy change should be reflected there, including corrections to
previously inaccurate documentation (see this phase's own changelog
entry for the SVG-chart documentation correction).

## Correction history

See [docs/CORRECTIONS.md](docs/CORRECTIONS.md) for the errata process and
public log of factual/data corrections, distinct from routine feature
development.

## Named maintainers

Repository contributors are recorded in the project's git history and
GitHub contributor list. This project does not currently have a formal
maintainer roster document beyond that; adding one (with named points of
contact for different concern areas — e.g., data provenance, accessibility,
model methodology) is recommended future governance work.

## Conflict of interest disclosure

See [CONFLICTS_OF_INTEREST.md](CONFLICTS_OF_INTEREST.md). This project
currently discloses no vendor funding, no installer partnerships, and no
affiliate relationships. Any future funding, partnership, or sponsorship
arrangement must be disclosed there before it takes effect, and must not
be permitted to influence default assumptions, pre-selected scenarios, or
displayed recommendations (see [MODEL_CARD.md](MODEL_CARD.md) "Prohibited
use").

## No undisclosed vendor funding

This is a standing commitment, not merely a current fact: this project
will not accept funding, equipment, or compensation from a solar
installer, battery manufacturer, financing provider, or aggregator
without public disclosure in
[CONFLICTS_OF_INTEREST.md](CONFLICTS_OF_INTEREST.md), and without such
funding being kept structurally separate from any assumption default,
scenario preselection, or comparative framing.

## Independent review

[docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) is the project's
internal adversarial self-review. The `review/` package
(`review/REVIEW-GUIDE.md` and its companion question sets) is designed to
let an *external* reviewer — a real consumer advocate, regulator, climate
specialist, equity advocate, or accessibility expert — independently
reproduce and challenge this project's claims. Independent review is
encouraged and its findings should be incorporated back into
`docs/RED-TEAM-REVIEW.md` and the claims/assumptions registers, not kept
separate.

## Review schedule

- Every entry in [data/governance/claims.yaml](data/governance/claims.yaml)
  and [data/governance/assumptions.yaml](data/governance/assumptions.yaml)
  carries a `review_due` (claims) or is subject to the cadence in
  [docs/ASSUMPTION-REVIEW.md](docs/ASSUMPTION-REVIEW.md) (assumptions).
- [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) should be revisited
  whenever a material new feature ships, and at minimum whenever a
  deferred item from its "Deferred to next phase" table is implemented
  (the corresponding row should be updated, not deleted).

## Stale-source warning (future automation, not yet built)

A future improvement — not implemented in this phase — would have the
build pipeline automatically flag any claim or source past its
`review_due` date, surfaced as a build warning or a dedicated status page.
Today, this is a manual process: the `review_due` fields exist in the
registers to make staleness *detectable* by a human reviewer, even though
detection is not yet automated.

## Issue reporting

- **General issues, feature requests:** open a GitHub issue.
- **Factual or data error:** see [docs/CORRECTIONS.md](docs/CORRECTIONS.md).
- **Accessibility problem:** see
  [ACCESSIBILITY.md §How to report a problem](ACCESSIBILITY.md).
- Do not include unredacted bills, exact addresses, or account numbers in
  any report — see [MODEL_CARD.md](MODEL_CARD.md) "Privacy."

## Reproducibility commitment

Because assumptions are versioned and never silently edited, a historical
result should remain reconstructable from the combination of (a) the git
commit or `model_version` in effect at the time, and (b) the specific
scenario/assumption file IDs used. This commitment is what
[docs/RED-TEAM-REVIEW.md §8](docs/RED-TEAM-REVIEW.md) (the
open-model/reproducibility persona) checks the project against.
