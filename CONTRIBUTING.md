# Contributing to Ontario Home Energy Futures

Thank you for considering a contribution. This project is Ontario-specific,
vendor-neutral, and transparent about its assumptions — please keep contributions
consistent with those goals.

## Ground rules

- **No guarantees.** Do not add language that predicts a specific future price or
  promises savings. Results must be presented as ranges built from labelled
  assumptions.
- **No hidden assumptions.** Every default value used in a calculation must live in
  a documented, editable YAML file under `assumptions/` or `scenarios/`, not
  hardcoded in Python, JavaScript, or templates.
- **No silent revision.** Never edit a previously published scenario or assumption
  file to make a past projection look more accurate. Add a new versioned file with
  a `supersedes` reference instead.
- **No new dependencies without discussion.** This project intentionally avoids
  large JavaScript frameworks, client-side charting libraries, CDNs, third-party
  fonts, and runtime databases. Open an issue before adding a dependency.
- **No private data.** Do not add code that transmits or stores household bill
  data, exact addresses, or account numbers on a server.
- **Do not copy code from other projects** into this repository unless you have
  verified licence compatibility and say so explicitly in the pull request.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python build.py
```

## Making changes

1. Open an issue describing the change first for anything beyond a small fix.
2. Keep calculation logic (`src/ontario_home_energy_futures/model/`) separate from
   presentation logic (`web/templates/`, `src/ontario_home_energy_futures/site/`).
3. Add or update unit tests for any change to `model/`. Add or update integration
   tests if the change affects one of the reference scenarios documented in
   [METHODOLOGY.md](METHODOLOGY.md).
4. Run `pytest` and `python build.py` before opening a pull request.
5. If your change affects a rendered page, check it against
   [ACCESSIBILITY.md](ACCESSIBILITY.md)'s checklist.

## Adding a data source

See [DATA_SOURCES.md](DATA_SOURCES.md) for the required documentation (publisher,
licence, update frequency, retrieval mechanism, known limitations) and
[README.md](README.md#adding-another-ontario-distributor) for distributor-specific
guidance. Every imported observation must carry full provenance — see the
`data/source-manifest.yaml` schema.

## Adding or revising a scenario

See [README.md](README.md#adding-or-revising-scenarios). Scenario files are
versioned; do not edit a published scenario in place.

## Reporting a problem

Open a GitHub issue. For accessibility issues specifically, see
[ACCESSIBILITY.md](ACCESSIBILITY.md#how-to-report-a-problem).

## Code of conduct

Be respectful and constructive. This project serves households making real
financial decisions — accuracy, humility about uncertainty, and clarity matter
more than cleverness.
