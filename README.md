# Ontario Home Energy Futures

**An open solar and electricity cost explorer**

Ontario Home Energy Futures is a free, open-source planning tool that helps Ontario
households explore how electricity rates, changing consumption, solar installation
costs, financing, net metering, and neighbourhood group-purchase discounts could
affect their energy costs over the next 10–30 years.

It answers one question:

> Given current Ontario electricity costs, documented trends, and my household plans,
> what **range** of costs could I face over the next 20 years, with or without solar?

## What this application does

- Reconstructs a standardized Ontario electricity bill (time-of-use or tiered) from
  official Ontario Energy Board (OEB) rate data, broken into its component charges.
- Lets you describe your household (a standard consumption profile, an annual
  estimate, or a detailed 12-month estimate) and planned changes (EV, heat pump,
  electric water heating, cooling).
- Models solar production, Ontario net metering (including the 12-month credit
  expiry rule), financing (cash or loan), and neighbourhood group-purchase discounts
  (5%, 10%, or custom).
- Compares buying solar now, waiting one to five years, and staying on the grid,
  across low/reference/high/custom electricity-price scenarios and
  flat/moderate/faster/custom solar-cost-decline scenarios.
- Reports results as **ranges with explained assumptions**, not single predicted
  numbers or guaranteed savings.
- Works as a static site: every core calculation runs at build time from committed
  data, and a small JavaScript module optionally lets you recalculate instantly in
  the browser. The essential methodology and standard scenarios are available even
  with JavaScript disabled.

## What this application does not do

- It does not predict future electricity prices or solar costs. It shows ranges
  built from documented, editable scenario assumptions.
- It does not guarantee savings, payback periods, or investment returns.
- It does not treat Ontario's provincial demand-growth forecasts as retail-price
  forecasts.
- It does not require an account, collect analytics, or store your household bill
  data on a server. All personal inputs stay in your browser, or are entered as
  parameters in a locally saved/downloaded scenario file.
- It does not require an exact street address — only an Ontario region or
  forward-sortation area.
- It is not financial advice.

## Project relationship to `neighbourhood-solar`

This project grew out of discussion in
[mgifford/neighbourhood-solar#4](https://github.com/mgifford/neighbourhood-solar/issues/4).
`neighbourhood-solar` remains a separate, deliberately simple, static,
JavaScript-free organizing site for neighbourhood group-purchase initiatives.
Ontario Home Energy Futures is a separate, independent application with its own
repository, and does not change `neighbourhood-solar`'s architecture or scope. It
may later publish shareable summary links that `neighbourhood-solar` can point to.

## Architecture

- **Python 3.12+** (`src/ontario_home_energy_futures/`) for data collection,
  normalization, validation, the calculation model, and static-site generation.
- **Jinja2** templates render plain HTML (`web/templates/`).
- **YAML** documents every assumption and scenario (`assumptions/`, `scenarios/`).
- **CSV** provides downloadable normalized observations (`data/observations.csv`).
- **JSON** provides browser-readable generated data for the optional client-side
  calculator.
- **Plain CSS**, no third-party fonts, no CDNs (`web/static/styles.css`).
- **A small vanilla JavaScript module** (`web/static/calculator.js`) progressively
  enhances the static pages with instant recalculation. No framework, no build
  step, and no client-side charting library planned — charts are intended to be
  accessible inline SVG, always paired with an HTML data table, but this is not
  yet implemented (`src/ontario_home_energy_futures/charts/` is currently
  empty; see [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) section 8.3).
- **pytest** for model and data-pipeline tests. Playwright and axe-core specs are
  included for browser and accessibility testing.

Calculation logic (`src/ontario_home_energy_futures/model/`) is kept separate from
presentation logic (`src/ontario_home_energy_futures/site/`, `web/templates/`) so
the model can be tested independently of the site.

## Running it locally

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Building the static site

The site builds entirely offline from committed fixtures and assumption files —
no network access is required.

```bash
python build.py
```

This writes the static site to `dist/`. Open `dist/index.html` in a browser, or
serve the directory locally:

```bash
python -m http.server -d dist 8000
```

## Running tests

```bash
pytest
```

Unit and integration tests run under pytest and require no network access. Browser
and accessibility tests (`tests/accessibility/`) use Playwright and axe-core and
require `npm install` plus Playwright's browser binaries; see
[ACCESSIBILITY.md](ACCESSIBILITY.md) for setup.

## Updating data

Raw source snapshots live in `data/raw/`. Phase 1 ships offline fixtures captured
from the sources documented in [DATA_SOURCES.md](DATA_SOURCES.md). To refresh a
fixture:

1. Download the source file (e.g. the OEB `BillData.xml`) and place it under
   `data/raw/<source>/`, keeping the previous version — never overwrite a raw file
   in place.
2. Record the new file's SHA-256 hash and retrieval date in
   `data/source-manifest.yaml`.
3. Run `python -m ontario_home_energy_futures.normalize` to regenerate
   `data/observations.csv`.
4. Run `pytest tests/unit` to confirm the pipeline still validates.

The scheduled `update-data.yml` GitHub Actions workflow automates steps 1–3 for
sources with a stable retrieval mechanism, and fails safely (leaving previously
normalized data untouched) if a source format changes unexpectedly.

## Adding another Ontario distributor

Distributor rate structures live in `assumptions/utilities/<distributor-slug>.yaml`,
following the shape of `assumptions/utilities/hydro-ottawa.yaml`. Add a new file
with the distributor's fixed charge, variable delivery rate, time-of-use or tiered
energy rates, and source citations, then reference the new distributor slug from
the household input form. No code changes are required for a distributor whose
rate structure matches the existing time-of-use/tiered model.

## Adding or revising scenarios

Electricity-price and solar-cost-decline scenarios live in `scenarios/` as
versioned YAML files. To revise a scenario, create a new file (e.g.
`reference-2027-01.yaml`) with `supersedes: reference-2026-08` rather than editing
the old file in place — past projections must remain inspectable exactly as
published. See [METHODOLOGY.md](METHODOLOGY.md) for the scenario schema.

## Deploying the static output

`dist/` is a plain static site and can be deployed to GitHub Pages, or any static
host. The included `.github/workflows/deploy.yml` builds and publishes `dist/` to
GitHub Pages on pushes to `main`.

## Documentation

- [METHODOLOGY.md](METHODOLOGY.md) — how every calculation works, and its
  known limitations.
- [DATA_SOURCES.md](DATA_SOURCES.md) — every data source, its licence, and
  retrieval process.
- [ACCESSIBILITY.md](ACCESSIBILITY.md) — accessibility target, testing process,
  and known limitations.
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute.
- [CHANGELOG.md](CHANGELOG.md) — release history.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
