# Model Card: Ontario Home Energy Futures

This model card describes what Ontario Home Energy Futures is, what it is
for, what it is not for, and what it does and does not know. It is written
for three audiences at once: the household using the tool, an external
reviewer auditing it, and a future contributor extending it. See
[docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) for the detailed
adversarial critique this card summarizes, and
[data/governance/claims.yaml](data/governance/claims.yaml) /
[data/governance/assumptions.yaml](data/governance/assumptions.yaml) for
the machine-readable registers behind every claim and default this card
references.

## Intended use

A planning and scenario-exploration aid for an Ontario homeowner with roof
control, deciding whether and when to consider solar, a home battery, or a
bidirectional EV, and how a neighbourhood group purchase might change that
decision. It is meant to be used alongside — never instead of — a real
contractor quote, distributor confirmation, and independent financial
advice.

## Prohibited use

This tool must not be used as, or represented as:

- **A contractor quote.** Every dollar figure is a modelled estimate, not
  a binding price.
- **Financial advice.** It does not know your full financial situation,
  risk tolerance, or alternatives.
- **Legal advice.** It does not interpret your specific contract, lease,
  condominium bylaw, or insurance policy.
- **An engineering assessment.** It does not evaluate your roof structure,
  electrical panel capacity, or shading in the way a site visit would.
- **A roof inspection.** Orientation/shading/pitch inputs are
  self-reported estimates, not a measured survey.
- **A guarantee of grid connection.** Interconnection approval, export
  limits, and net-metering eligibility are determined by your
  distributor, not by this tool — see
  [DATA_SOURCES.md](DATA_SOURCES.md) and confirm directly with Hydro
  Ottawa (or your distributor) before purchasing anything.
- **A prediction of future electricity rates, solar costs, or programme
  availability.** Every forward-looking figure is a labelled scenario or
  estimate, never a forecast presented as fact.
- **A guarantee of programme eligibility**, including net metering, any
  incentive, or any future grid-service programme.
- **A substitute for utility confirmation.** Always confirm rate plan,
  net-metering terms, and connection requirements directly with your
  distributor before signing a contract.
- **A lifecycle assessment**, unless and until a dedicated, documented
  lifecycle/emissions module exists (it does not yet — see "Environmental
  accounting" below).
- **A sales tool.** This project accepts no vendor funding, no installer
  partnerships, and no affiliate links (see
  [CONFLICTS_OF_INTEREST.md](CONFLICTS_OF_INTEREST.md)). If a contractor
  or salesperson presents output from this tool as an official quote or
  endorsement, that is a misuse of the tool, not an intended one.

**This disclaimer does not substitute for correcting misleading design.**
Where this card names a design gap (e.g., a pre-filled illustrative price
in a form field — see
[docs/RED-TEAM-REVIEW.md §1.1](docs/RED-TEAM-REVIEW.md#11-illustrative-reference-figures-are-pre-populated-into-live-looking-form-fields)),
that gap is tracked as an open defect to fix, not excused by this
disclaimer.

## Intended audience

Ontario homeowners with roof control considering solar/battery/EV
decisions; researchers and advocates studying Ontario residential energy
transition options; developers extending this open-source project. It is
**not** designed for renters, condominium residents without roof access,
or households outside Ontario — see "Known limitations" and
[docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md](docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md).

## Geographic scope

Ontario, Canada. As of this version, only Hydro Ottawa's rate structure is
modelled; the data schema supports additional distributors, but none are
yet added. Solar production uses a single illustrative Ottawa-region yield
profile — results for other Ontario regions are not yet regionally
differentiated. See [DATA_SOURCES.md](DATA_SOURCES.md).

## Planning horizon

Default 20 years, selectable at 10/20/25/30 years. Twenty years is a
modelling convention, **not** a claimed physical lifespan for solar
panels, batteries, or any other equipment. All decisions being compared
must share the same fixed calendar window (see
`model/horizon.py::FixedHorizon`) — a household that waits to purchase
never receives a longer effective comparison window than one that buys
immediately.

## Data sources

See [DATA_SOURCES.md](DATA_SOURCES.md) for the full per-source table. In
summary: Ontario Energy Board (rates, net-metering rules), Hydro Ottawa
(net-metering billing practice), Statistics Canada (contextual market
index only, not a retail rate), IESO (provincial demand-growth context,
Annual Planning Outlook). **As of this version, OEB/IESO/StatCan figures
are captured as offline illustrative fixtures, not live-fetched data** —
this must be verified against live sources before being treated as
current. This limitation is stated in every relevant source's own entry
in DATA_SOURCES.md and is not hidden.

## Model boundaries

- Monthly-level bill, solar, and net-metering calculations, built on a
  documented representative hourly shape for direct-self-consumption
  estimation — **not a validated hourly (8,760-interval) simulation**.
  See [METHODOLOGY.md §3](METHODOLOGY.md).
- No interconnection-capacity or export-limit check against distributor
  rules — confirm connection eligibility with your distributor directly.
  See [docs/RED-TEAM-REVIEW.md §4.2](docs/RED-TEAM-REVIEW.md).
- No emissions or lifecycle-impact model exists yet (see "Environmental
  accounting" below).
- No financial-safety/affordability warning system exists yet (see
  "Financial risks" below).
- Battery and EV grid-service dispatch is modelled at **monthly
  aggregate** granularity, not full hourly dispatch optimization — this
  is a deliberate, documented choice to avoid shipping unvalidated hourly
  assumptions ahead of real data (see
  `assumptions/batteries.yaml`, `hourly_dispatch_optimization_status:
  deferred_pending_validated_hourly_data`).
- Scenario-assumption coherence is not yet enforced across independent
  dials — a user (or a future scenario bundle) could combine several
  simultaneously-optimistic assumptions that are not economically
  consistent with each other. See
  [docs/RED-TEAM-REVIEW.md §3.2](docs/RED-TEAM-REVIEW.md).

## Main assumptions

Every numeric default is documented, sourced (where a source exists), and
editable — see [data/governance/assumptions.yaml](data/governance/assumptions.yaml)
for the full machine-readable register, and `assumptions/*.yaml` for the
underlying files the model actually reads. Nothing is hidden in source
code. Assumption confidence is recorded as three **separate** dimensions
(evidence quality, Ontario applicability, temporal stability) — never
collapsed into a single misleading score.

## Known limitations

See [docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) for the full,
itemized list with severity and status. The most significant, summarized:

- An illustrative reference solar quote and battery price are pre-filled
  into live form fields, which risks being mistaken for a real market
  price (open — see red-team review §1.1).
- The live comparison table currently sweeps only a subset of the "wait
  1-5 years" range the README describes (only a 3-year wait is
  currently computed); the sensitivity-analysis table shown on
  `compare-timing.html` is a static illustrative example, not computed
  from the user's actual inputs — this was corrected this phase to be
  clearly labelled as such (see red-team review §8.4).
- No scenario-coherence rules exist yet, so internally inconsistent
  combinations of optimistic assumptions are not flagged.
- No financial-safety warnings exist yet (unaffordable financing,
  payback-after-expected-move-out, roof-replacement-before-payback, etc.).
- Net-metering eligible/ineligible-charge rules are derived from
  documentary review, not confirmed against live Hydro Ottawa billing
  system behaviour.
- The IESO provincial demand-growth figures are recorded with a `status`
  label that is inconsistent with their own "pending verification" note
  — flagged, not yet corrected at the source (red-team review §2.1).

## Current programme coverage

Sixteen household value streams are modelled (see
`assumptions/value_streams/*.yaml`), each labelled with one of seven
availability statuses: `current`, `closed`, `pilot`, `proposed`,
`demonstrated_elsewhere`, `illustrative_scenario`, `unsupported`. **Only
the eight `current`-status streams may appear in a default result**:
avoided retail purchase (direct self-consumption), Ontario net-metering
credit, time-of-use/ultra-low-overnight bill shifting, current
incentives/rebates (currently $0 pending a verified active programme),
group-purchase discount, avoided-generator-cost (conditional, opt-in
only), household efficiency savings, and managed EV charging savings.

## Future scenario treatment

The remaining eight value streams (demand response, VPP availability, VPP
event payment, dynamic export compensation, capacity-market revenue,
local-distribution flexibility, bidirectional EV export, vehicle-to-home
avoided outage cost) are `pilot`, `proposed`, `demonstrated_elsewhere`, or
`illustrative_scenario` — none are currently generally available to
Ontario households. Every such value stream's YAML file states explicitly
that it must never appear in a default result. Where shown (in a future,
explicitly-labelled scenario), any result must state:

> This result depends materially on a programme or payment that is not
> currently available.

## Financial risks

This tool does not currently implement financial-safety guardrails (debt
affordability checks, payback-timing-vs-move-out-date warnings, or
income-sensitivity checks). Users should independently confirm that any
financing they consider is affordable under adverse conditions, understand
cancellation fees and liens, and obtain multiple itemized quotes before
signing a contract. See the Ontario Energy Board's net-metering consumer
disclosure statement:
<https://www.oeb.ca/sites/default/files/net-metering-disclosure-statement-en-20230501.pdf>.

## Environmental accounting

**No emissions or lifecycle-impact model exists in this version.** The
application makes no claim about avoided emissions, "green" or "clean"
outcomes, carbon neutrality, or environmental benefit of any kind. This is
a deliberate absence, not an oversight to be quietly filled later with an
unsubstantiated number — see
[docs/ENVIRONMENTAL-CLAIMS-POLICY.md](docs/ENVIRONMENTAL-CLAIMS-POLICY.md)
for the rules any future environmental claim in this project must satisfy
before it is added.

## Equity limitations

This tool assumes single-family homeownership with roof control and
does not currently support renters, condominium residents, or shared/
community-solar scenarios. Collective-purchasing savings may
disproportionately benefit households with the social and financial
capital to organize a group purchase. See
[docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md](docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md)
for the full discussion, including private-vs-system value separation and
explicit "unknown" markers where distributional effects have not been
quantified.

## Accessibility

Targets WCAG 2.2 AA. See [ACCESSIBILITY.md](ACCESSIBILITY.md) for the full
target, testing process, and known limitations (including that automated
Playwright/axe-core specs are written but not yet executed in this build
environment, and a full manual screen-reader pass has not yet been
logged).

## Privacy

- No server-side account, session, or household-data storage exists — the
  application is a static site with no backend database.
- No exact address or account number should ever appear in a shareable
  URL or downloaded scenario file (see [README.md](README.md)).
- **New this phase:** critical-load and resilience details (which could
  reveal disability or medical-equipment information) must never be
  encoded in a shareable URL, extending the existing no-address/no-account
  convention to this newer data category.
- If future virtual-power-plant (VPP) or aggregator features are added,
  participation implies third-party remote monitoring and/or dispatch
  control of household equipment by that programme's operator — a
  privacy and cybersecurity consideration distinct from, and not
  mitigated by, this tool's own no-server-retention architecture. This
  tool modelling a VPP payment does not itself grant or require that
  access.
- No household bill or device data should ever be sent to a third-party
  AI service without explicit, informed user consent (see
  [README.md](README.md) household input modes).

## Governance

See [GOVERNANCE.md](GOVERNANCE.md) for the full policy: public source code
and model version, dated and versioned assumptions, historical scenario
retention (published scenario files are never edited in place), a defined
correction process ([docs/CORRECTIONS.md](docs/CORRECTIONS.md)), and named
maintainer/conflict-of-interest disclosure
([CONFLICTS_OF_INTEREST.md](CONFLICTS_OF_INTEREST.md)).

## Versioning

The application exposes a `model_version` string
(`src/ontario_home_energy_futures/__init__.py`) on every page footer,
alongside a `data_cutoff` date. **Known limitation:** this version string
is currently maintained manually and does not automatically change when
underlying assumptions or model code change — two builds could report the
same `model_version` while producing different results. A future
improvement (not yet implemented) would tie the displayed version to a
content hash of `assumptions/` and `scenarios/`.

## How to report an error

Open a GitHub issue. For a factual or data error specifically, see
[docs/CORRECTIONS.md](docs/CORRECTIONS.md) for the dedicated errata
process. For an accessibility problem, see
[ACCESSIBILITY.md §How to report a problem](ACCESSIBILITY.md). Do not
include unredacted bills, exact addresses, or account numbers in any
report.

---

This model card does not claim the application is unbiased. It documents
what the application is for, what it assumes, how it is governed, what
biases and gaps are currently known (see
[docs/RED-TEAM-REVIEW.md](docs/RED-TEAM-REVIEW.md) for the full
adversarial account), what evidence supports it, what evidence it
currently lacks, and the decisions it should not yet be used to make.
