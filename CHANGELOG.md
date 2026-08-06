# Changelog

All notable changes to this project are documented in this file.

## [Unreleased] — Hardening and red-team review — 2026-08-03

### Added

- [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md): adversarial critique
  from eight review perspectives (consumer advocate, Ontario energy
  regulator, energy economist, grid operator, climate/lifecycle
  specialist, equity advocate, accessibility/privacy/security reviewer,
  open-model/reproducibility reviewer), with explicit tracking of what
  remains deferred.
- [MODEL_CARD.md](MODEL_CARD.md): intended/prohibited use, scope,
  assumptions, limitations, and explicit "this is not..." statement.
- [data/governance/claims.yaml](data/governance/claims.yaml) and
  [data/governance/assumptions.yaml](data/governance/assumptions.yaml):
  machine-readable public claims and assumptions registers with
  three-dimensional confidence scoring (never collapsed into one score).
- [docs/ENVIRONMENTAL-CLAIMS-POLICY.md](docs/ENVIRONMENTAL-CLAIMS-POLICY.md),
  [docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md](docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md),
  [GOVERNANCE.md](GOVERNANCE.md), [CONFLICTS_OF_INTEREST.md](CONFLICTS_OF_INTEREST.md),
  [docs/CORRECTIONS.md](docs/CORRECTIONS.md), [docs/ASSUMPTION-REVIEW.md](docs/ASSUMPTION-REVIEW.md).
- `review/` package for independent external review (consumer-advocate,
  regulatory, climate, equity, and accessibility question sets, plus
  sample scenarios reproducible from the existing test suite).

### Fixed

- `compare-timing.html`'s "What drives this result" sensitivity table was
  presented as computed from the user's current inputs while actually
  being static content; corrected to be clearly labelled as an
  illustrative example. See [docs/CORRECTIONS.md](docs/CORRECTIONS.md).
- README.md, this file, and ACCESSIBILITY.md corrected to describe
  accessible SVG charts as planned, not delivered (none exist yet). See
  [docs/CORRECTIONS.md](docs/CORRECTIONS.md).

### Known limitations

This phase was scoped to documentation, governance, and two concrete
honesty fixes. Financial-safety warnings, regret analysis, scenario
coherence rules, the climate/extreme-weather model, the environmental
accounting module, and the full adversarial test suite are explicitly
deferred — see [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md)
"Deferred to next phase" for the complete, itemized list.

## [0.1.0] — Phase 1 prototype — 2026-08-02

### Added

- Static site scaffold (Python build, Jinja2 templates, plain CSS, one small
  vanilla JavaScript module).
- Ontario bill reconstruction model for Hydro Ottawa time-of-use and tiered
  residential rate plans, using illustrative rate fixtures pending live OEB data
  verification.
- Household consumption model (standard profiles, annual estimate, detailed
  12-month estimate) with EV/heat-pump/water-heater/cooling add-on inputs.
- Monthly solar production model.
- Ontario net-metering credit ledger with 12-month vintage expiry and eligible-charge
  restrictions.
- Financing model (cash, loan amortization, group-purchase discount).
- Solar-cost-decline scenarios (flat, moderate, faster, custom) and
  electricity-price scenarios (low, reference, high, stress/custom).
- 20-year (and 10/25/30-year) buy-now vs. wait vs. grid-only comparison engine,
  with nominal and discounted (NPV) results. The live comparison table currently
  evaluates a fixed set of decisions including a 3-year wait; a full 1–5 year
  wait sweep is designed for but not yet exposed on the live site (see
  [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) section 8.5).
- Cost-of-waiting breakeven calculation.
- Data provenance schema and validator; offline-buildable fixtures.
- Accessible HTML site: 12 pages, no-JavaScript baseline comparison tables.
  Accessible SVG charts paired with data tables are planned but not yet
  implemented (see [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md)
  section 8.3).
- pytest unit and integration test suites, including reference Scenarios A–F.
- Playwright and axe-core accessibility test specifications.
- GitHub Actions workflows for tests, scheduled data updates, and GitHub Pages
  deployment.

### Known limitations

See "Known limitations" and "Work explicitly deferred" in the project's Phase 1
implementation report, and [METHODOLOGY.md](METHODOLOGY.md#known-limitations).
