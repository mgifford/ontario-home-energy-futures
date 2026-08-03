# Data Sources

Every dataset used by Ontario Home Energy Futures is documented here: publisher,
licence, update frequency, retrieval mechanism, known limitations, and last
successful retrieval. Raw files are preserved under `data/raw/<source>/` and never
overwritten in place; each retrieval is hashed (SHA-256) and recorded in
`data/source-manifest.yaml`.

## Ontario Energy Board (OEB) — residential electricity rates

- **Publisher:** Ontario Energy Board
- **Dataset:** Current electricity rates, residential rate class
- **URL:** <https://www.oeb.ca/open-data/current-electricity-rates-residential-rate-class>
- **Data file:** <https://www.oeb.ca/_html/calculator/data/BillData.xml>
- **Licence:** Open Government Licence – Ontario
- **Update frequency:** Twice yearly (typically May and November), when the OEB
  revises regulated rates.
- **Retrieval mechanism:** Scheduled download of `BillData.xml` by
  `.github/workflows/update-data.yml` (Phase 2); Phase 1 ships a manually captured,
  clearly labelled illustrative fixture at `data/raw/oeb/billdata-fixture.xml`
  because this build environment has no scheduled network access.
  **This fixture must be verified against the live `BillData.xml` before Phase 1
  figures are treated as current.**
  See `data/raw/oeb/README.md` for details.
- **Transformation:** `src/ontario_home_energy_futures/normalize/oeb.py` parses the
  XML into provenance-stamped observation records with `measure`,
  `rate_plan`, `period_name`, `value`, `unit: CAD_per_kWh` or `CAD_per_day`.
- **Known limitations:** The illustrative fixture approximates 2026 rate levels;
  it is not a substitute for verified live data. `BillData.xml`'s schema is not
  publicly versioned, so parsing must fail safely (not publish) if its structure
  changes.
- **Last successful retrieval:** Not yet performed against the live endpoint in
  this environment. Fixture captured 2026-08-02.
- **Maintainer:** Project maintainers (see repository contributors).

## Ontario Energy Board — historical Regulated Price Plan (RPP) rates

- **Publisher:** Ontario Energy Board
- **Dataset:** Historical RPP electricity rates
- **URL:** <https://www.oeb.ca/open-data/historical-regulated-price-plan-electricity-rates>
- **Licence:** Open Government Licence – Ontario
- **Update frequency:** Twice yearly, alongside current rates.
- **Retrieval mechanism:** Manual download (Phase 1); scheduled download
  (Phase 2).
- **Transformation:** Normalized into the same observation schema as current
  rates, with `status: observed` and historical `period` values, feeding the
  monthly Ontario electricity tracker's forecast-vs-actual comparison.
- **Known limitations:** Historical RPP structures have changed over time
  (tier thresholds, time-of-use period definitions); comparisons across
  structural changes are approximate and labelled as such.
- **Last successful retrieval:** Not yet performed in this environment.
- **Maintainer:** Project maintainers.

## Ontario net-metering rules

- **Publisher:** Ontario Energy Board; Government of Ontario
- **Dataset:** Net metering consumer information; Ontario Regulation 541/05
- **URLs:**
  - <https://www.oeb.ca/consumer-information-and-protection/net-metering>
  - <https://www.ontario.ca/laws/regulation/050541>
- **Licence:** Open Government Licence – Ontario / Queen's Printer for Ontario
- **Update frequency:** As regulations change; not on a fixed schedule.
- **Retrieval mechanism:** Manual review; rules are encoded in
  `assumptions/ontario.yaml` and `src/ontario_home_energy_futures/model/net_metering.py`
  with citations, not scraped programmatically.
- **Transformation:** Rule parameters (credit expiry period, eligible charge
  categories) become named constants in `assumptions/ontario.yaml`.
- **Known limitations:** Regulatory text requires human interpretation; the
  eligible-charge categorization in this project's model should be re-verified
  against current OEB guidance and the selected distributor's own billing
  practice before being relied on for a real purchase decision.
- **Last successful retrieval:** Reviewed 2026-08-02 against publicly cached
  regulation text; live re-verification recommended before Phase 1 launch.
- **Maintainer:** Project maintainers.

## Hydro Ottawa — net metering and distributed energy resources

- **Publisher:** Hydro Ottawa
- **Dataset:** Net metering bill sample; distributed energy resource (DER) types
- **URLs:**
  - <https://hydroottawa.com/en/residential/rates-billing/your-bill-and-rates-explained/net-metering-bill-sample>
  - <https://hydroottawa.com/en/business/savings-incentives/distributed-energy-resources-ders/types-of-ders>
- **Licence:** Publicly published consumer information; no explicit open licence
  found. Used here only to derive documented rate-structure parameters, not
  reproduced verbatim.
- **Update frequency:** Irregular, tied to OEB rate changes.
- **Retrieval mechanism:** Manual review.
- **Transformation:** Rate structure parameters encoded in
  `assumptions/utilities/hydro-ottawa.yaml`.
- **Known limitations:** The DER page is published under Hydro Ottawa's business
  section; a residential-specific equivalent should be checked for each
  revision in case it supersedes the business page for residential net-metering
  mechanics. This project has not confirmed the current status of that
  residential-specific page.
- **Last successful retrieval:** Reviewed 2026-08-02.
- **Maintainer:** Project maintainers.

## Statistics Canada — Electric Power Selling Price Index

- **Publisher:** Statistics Canada
- **Dataset:** Electric Power Selling Price Index (table 18-10-0204-01)
- **URL:** <https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810020401>
- **Web Data Service:** <https://www.statcan.gc.ca/en/developers/wds>,
  <https://www.statcan.gc.ca/en/developers/wds/user-guide>
- **Licence:** Statistics Canada Open Licence
- **Update frequency:** Monthly.
- **Retrieval mechanism:** Phase 2 — scheduled WDS API call. Not yet integrated.
- **Transformation:** Indexed to a base year; used only as a general market
  indicator on the "Current Ontario costs" page.
- **Known limitations:** This index tracks wholesale/industrial electric power
  selling prices at a national or provincial-aggregate level. **It is not a
  residential electricity bill or retail rate**, and this project must never
  present it as one. It is shown for context only, clearly labelled.
- **Last successful retrieval:** Not yet integrated (Phase 2).
- **Maintainer:** Project maintainers.

## Independent Electricity System Operator (IESO) — hourly demand and planning outlook

- **Publisher:** Independent Electricity System Operator
- **Datasets:**
  - Hourly Ontario electricity demand: <https://reports-public.ieso.ca/public/Demand/>
  - Annual Planning Outlook: <https://www.ieso.ca/-/media/Files/IESO/Document-Library/planning-forecasts/apo/2026/2026-Annual-Planning-Outlook.pdf>
- **Licence:** IESO public reports; used for citation and derived scenario
  parameters, not bulk reproduction.
- **Update frequency:** Hourly demand — daily. Annual Planning Outlook — annually.
- **Retrieval mechanism:** Phase 2 — scheduled download for hourly demand. Annual
  Planning Outlook figures are manually reviewed and recorded as versioned
  assumptions in `assumptions/ontario.yaml`, one file per publication year, never
  overwritten.
- **Transformation:** Provincial demand-growth scenarios (low/reference/high)
  are recorded as informational context alongside — never blended into —
  electricity-price scenarios.
- **Known limitations:** The 2026 Annual Planning Outlook's low/reference/high
  demand-growth-to-2050 figures (recorded in `assumptions/ontario.yaml` as
  approximately 38% / 65% / 92%) describe *provincial system demand*, not
  household consumption or retail price growth. This project explicitly does not
  convert one into the other. These figures should be re-verified against the
  published PDF; they are recorded here as a documented, sourced estimate
  pending that verification.
- **Last successful retrieval:** Not yet performed against the live PDF in this
  environment; figures recorded from the values specified in the project brief,
  flagged for verification.
- **Maintainer:** Project maintainers.

## Solar-cost evidence

- **Publishers:** International Energy Agency (IEA); International Renewable
  Energy Agency (IRENA); Natural Resources Canada (NRCan); National Renewable
  Energy Laboratory (NREL, U.S. Department of Energy); Ontario installer quotes
  contributed with permission; government incentive/programme documentation.
- **Licence:** Varies by publisher; cited individually in
  `assumptions/solar.yaml`.
- **Update frequency:** Annual or irregular, per publisher.
- **Retrieval mechanism:** Manual review; used to set illustrative real
  installed-cost decline scenarios (flat / moderate / faster / custom), not to
  apply global module-price indices directly to Ontario installed prices.
- **Transformation:** Encoded as `scenarios/solar-cost-decline/*.yaml` with
  explicit `status: scenario` labelling.
- **Known limitations:** Global module-price data moves faster than complete
  Ontario residential installed pricing (which includes labour, permitting,
  connection, and overhead that do not track module costs). This project
  deliberately does not apply a global module decline rate to full installed
  cost; see [METHODOLOGY.md](METHODOLOGY.md).
- **Last successful retrieval:** Illustrative values set 2026-08-02, pending
  sourcing of specific NRCan/IEA/IRENA figures for Phase 2.
- **Maintainer:** Project maintainers.

## Ontario solar-resource data

- **Publisher:** To be confirmed — intended source is Natural Resources Canada's
  photovoltaic potential dataset.
- **Licence:** Open Government Licence – Canada (expected).
- **Update frequency:** Static/rarely revised.
- **Retrieval mechanism:** Not yet integrated. Phase 1 uses a single illustrative
  regional monthly-yield profile for the Ottawa region, documented in
  `assumptions/solar.yaml` as `status: estimate`.
- **Known limitations:** A single regional profile does not capture
  forward-sortation-area-level variation. This is a known Phase 1 limitation.
- **Last successful retrieval:** Not yet integrated.
- **Maintainer:** Project maintainers.

## Contributed Ontario installer quotes

- **Publisher:** N/A — community-contributed.
- **Licence:** Contributed under this project's licence by the submitter.
- **Update frequency:** Ad hoc.
- **Retrieval mechanism:** Not yet implemented (Phase 2 quote-tracker schema is
  defined in `assumptions/solar.yaml` and the project brief; no submission
  pipeline exists in Phase 1).
- **Known limitations:** Any future aggregate statistic drawn from contributed
  quotes must carry a prominent small-sample warning per this project's
  requirements; homeowner name, exact address, utility account number,
  installer salesperson details, and full unredacted quotes must never be
  collected.
- **Last successful retrieval:** N/A.
- **Maintainer:** Project maintainers.
