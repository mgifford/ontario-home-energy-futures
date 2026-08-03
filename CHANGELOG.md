# Changelog

All notable changes to this project are documented in this file.

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
- 20-year (and 10/25/30-year) buy-now vs. wait 1–5 years vs. grid-only comparison
  engine, with nominal and discounted (NPV) results.
- Cost-of-waiting breakeven calculation.
- Data provenance schema and validator; offline-buildable fixtures.
- Accessible HTML site: 12 pages, accessible SVG charts paired with data tables,
  no-JavaScript baseline comparison tables.
- pytest unit and integration test suites, including reference Scenarios A–F.
- Playwright and axe-core accessibility test specifications.
- GitHub Actions workflows for tests, scheduled data updates, and GitHub Pages
  deployment.

### Known limitations

See "Known limitations" and "Work explicitly deferred" in the project's Phase 1
implementation report, and [METHODOLOGY.md](METHODOLOGY.md#known-limitations).
