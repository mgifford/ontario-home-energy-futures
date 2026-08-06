# Red-Team Review

This document records a critique of Ontario Home Energy Futures from eight
adversarial review perspectives, conducted before implementing this
hardening phase's changes. It is a living document — new concerns should be
added as findings, not silently fixed and forgotten.

**Review date:** 2026-08-03
**Reviewed against:** commit `91c19ec` plus uncommitted Phase 2 model work
(value streams, compatibility matrix, fixed-calendar horizon, cost of
inaction, battery/EV dispatch — see `git status` for the exact file list at
review time).
**Scope note:** This review covers the application *as it exists today*,
including code that is written but not yet wired into the live site
(Phase 2). Where a concern is about code that isn't user-facing yet, this
is stated explicitly rather than treated as already mitigated.

For each material concern: **Criticism**, **Evidence**, **Severity**
(critical / high / medium / low), **Affected files**, **Mitigation**,
**Remaining limitation**, **Test added**, **Status** (open / mitigated /
deferred / accepted-risk).

---

## 1. Consumer advocate

### 1.1 Illustrative reference figures are pre-populated into live-looking form fields

**Criticism:** A household could mistake the $21,000/7.2kW illustrative
quote or the $12,000 illustrative battery price for a real market
estimate, because these values are pre-filled into number inputs
(`value="{{ illustrative_quote.installed_price_before_tax }}"`) rather than
shown only as placeholder/example text.

**Evidence:** `web/templates/net_metering.html` line 20;
`assumptions/solar.yaml` `illustrative_reference_quote` block, itself
labelled "not a market price estimate" in its own `notes` field — a label
that never reaches the rendered form.

**Severity:** High. This is the exact failure mode a salesperson could
exploit: screenshot a form pre-filled with a Claude-maintained "reference"
number and present it as if the tool endorsed that price.

**Affected files:** `web/templates/net_metering.html`,
`assumptions/solar.yaml`, `src/ontario_home_energy_futures/site/build_site.py`.

**Mitigation (this phase):** None implemented yet — flagged here, not
silently fixed, because correcting it requires a template change beyond
this phase's docs/governance scope (see `data/governance/claims.yaml`
`claim-illustrative-quote-not-market-price` and
`assumptions.yaml` `assumption-illustrative-reference-quote`, both created
this phase to make the gap explicit and trackable).

**Remaining limitation:** Until fixed, a user who submits the form without
editing the pre-filled value receives a result computed from an
unverified, maintainer-invented number, with no interstitial warning.

**Test added:** None this phase (template-layer fix, deferred).

**Status:** Open — tracked for next phase.

### 1.2 No independent-quote encouragement, financing-risk disclosure, or cancellation/lien/warranty coverage

**Criticism:** The application discusses financing math (amortization,
group-discount interest avoided) but nowhere tells a user to get multiple
itemized quotes, review financing terms independently, check for
cancellation fees or liens, or confirm warranty terms before signing
anything.

**Evidence:** `web/templates/net_metering.html`, `web/templates/household.html`,
`METHODOLOGY.md` section 6 — none mention independent quotes, liens,
contractor cancellation terms, or warranty review. `about.html` says "not
financial advice" but does not direct users toward the concrete
consumer-protection steps the OEB's own net-metering disclosure statement
recommends.

**Severity:** High.

**Affected files:** All solar/financing-facing templates; no dedicated
consumer-protection callout exists anywhere in the site.

**Mitigation (this phase):** `MODEL_CARD.md`'s "Prohibited use" and
"Financial risks" sections state explicitly that this tool is not a
substitute for independent quotes, financing review, or utility
confirmation, and `review/CONSUMER-ADVOCATE-QUESTIONS.md` gives an external
reviewer a checklist to hold the *next* phase's template work accountable
to this. The OEB's net-metering consumer disclosure statement
(https://www.oeb.ca/sites/default/files/net-metering-disclosure-statement-en-20230501.pdf)
is now a required reference, recorded in `data/governance/claims.yaml`.

**Remaining limitation:** The model card is a documentation-layer fix. It
does not yet force a user through this guidance in the actual purchase
flow — a template-layer "before you sign anything" checklist remains
undone.

**Test added:** None this phase.

**Status:** Deferred — tracked, mitigated only at the documentation layer.

### 1.3 Savings language, while hedged, could still be excerpted deceptively

**Criticism:** Even hedged language like "estimated 20-year present-value
cost is X" can be screenshotted without its surrounding caveats.

**Evidence:** `web/templates/compare_timing.html` lines 12-20 — the range
statement is reasonably well-hedged ("not a prediction and not a
guarantee"), but nothing prevents a third party from cropping just the
dollar figure out of context.

**Severity:** Medium. No UI/UX control can fully prevent selective
screenshotting; the mitigation is to make every individual sentence
defensible in isolation, not to prevent extraction.

**Affected files:** `web/templates/compare_timing.html`.

**Mitigation (this phase):** `data/governance/claims.yaml` now records the
exact wording standard every dollar-figure claim must meet (always paired
with "modelled," "estimated," or "under stated assumptions" in the same
sentence, never in a separate sentence that could be cropped away).
`docs/RED-TEAM-REVIEW.md` (this document) records this as a standing
constraint reviewed at each documentation/template change.

**Remaining limitation:** Enforcement is currently manual review, not an
automated lint that rejects a template diff containing a bare dollar
figure without a hedge in the same sentence.

**Test added:** None this phase (would require a template-content lint,
deferred).

**Status:** Accepted-risk, monitored.

---

## 2. Ontario energy regulator

### 2.1 IESO demand-growth figures labelled `observed` while flagged as unverified

**Criticism:** `assumptions/ontario.yaml`'s `provincial_demand_scenarios`
block sets `status: observed` on the IESO 2026 Annual Planning Outlook
growth-to-2050 figures, but the same block's `notes` field says the values
are "recorded from the values specified in the project brief, flagged for
verification" — i.e., not actually independently observed against the
published PDF. Labelling something `observed` while admitting it hasn't
been checked against its cited source is a status/evidence mismatch a
regulator would flag immediately.

**Evidence:** `assumptions/ontario.yaml`, `provincial_demand_scenarios`
block, `status: observed` + `notes`.

**Severity:** High. This is exactly the kind of inconsistency this
project's own `data/governance/claims.yaml` schema exists to prevent.

**Affected files:** `assumptions/ontario.yaml`.

**Mitigation (this phase):** `data/governance/claims.yaml` records this
specific figure as `claim-ieso-demand-growth-2050` with
`status: needs_review` (not `approved`), `type: projection` (not
`observed_fact`), and an explicit `review_due` date, so it cannot silently
present as more solid than it is inside the new governance layer even
though the underlying `assumptions/ontario.yaml` file itself is unchanged
this phase (out of scope — YAML status fields belong to the deferred
site-wiring work, and changing them without also updating every page that
reads them risks a worse inconsistency).

**Remaining limitation:** The mismatch still exists in
`assumptions/ontario.yaml` itself; `claims.yaml` is a parallel governance
record, not a fix to the source file. Flagged for correction alongside the
next phase's site-wiring work.

**Test added:** None this phase.

**Status:** Open — documented and tracked, not fixed at the source.

### 2.2 Net-metering eligible/ineligible-charge rules are documentary interpretation, not confirmed against distributor practice

**Criticism:** The net-metering model's charge-eligibility rules (credits
apply only to the energy charge, never fixed delivery/regulatory/tax) are
derived from OEB guidance and Ontario Regulation 541/05 read by project
maintainers — not confirmed against Hydro Ottawa's actual billing system
behaviour. `assumptions/ontario.yaml` and `METHODOLOGY.md` section 5 both
already say this needs re-verification, which is good practice, but the
live site's `net-metering.html` page does not surface this caveat as
prominently as the methodology page does.

**Evidence:** `assumptions/ontario.yaml` `net_metering.notes`;
`METHODOLOGY.md` section 5, last paragraph; `web/templates/net_metering.html`
— no equivalent caveat present on the page itself, only linked via
Methodology.

**Severity:** Medium — the caveat exists, but not at the point of use.

**Affected files:** `web/templates/net_metering.html`.

**Mitigation (this phase):** Recorded as `claim-net-metering-eligible-charges`
in `data/governance/claims.yaml` with `status: needs_review` and a direct
link to both the OEB and Hydro Ottawa sources, making the gap
machine-readable and trackable via `review_due`. `review/REGULATORY-QUESTIONS.md`
directs an external reviewer to challenge this specific claim.

**Remaining limitation:** The on-page caveat is still not present;
template change deferred.

**Test added:** None this phase.

**Status:** Deferred.

### 2.3 No claim implies OEB endorses private contract outcomes — verified, not a finding

**Criticism (checked, not found):** Reviewed every template and doc for
language that could imply OEB or IESO endorsement of a specific financial
outcome. None found — `about.html`, `data_sources.html`, and every
value-stream YAML correctly attribute OEB/IESO only as sources of
*regulatory fact*, never as guarantors of a private result.

**Severity:** N/A (no finding).

**Status:** Verified clean; recorded so this isn't re-litigated without
cause.

### 2.4 Fixed delivery charges — verified correctly modelled

**Criticism (checked, not found):** The regulator persona's core concern —
that fixed delivery/regulatory charges might be zeroed out by solar
production — was tested directly: `test_fixed_charges_remain_when_consumption_reduced`
in `tests/integration/test_reference_scenario_a_standard_household.py`
confirms the fixed charge is identical at 700 kWh, 50 kWh, and 0 kWh
consumption.

**Status:** Verified clean.

---

## 3. Energy economist

### 3.1 Provincial demand growth correctly kept separate from retail-price growth — verified

**Criticism (checked, not found):** The economist's central worry —
conflating system-wide demand growth with household retail-price growth —
is explicitly guarded against: `test_provincial_demand_not_added_directly_to_household_kwh`
(`tests/integration/test_reference_scenario_f_electrification.py`) and the
explicit statement in `METHODOLOGY.md` section 9 ("This model never
converts a provincial demand-growth percentage into a household kWh
addition or a retail-price growth percentage"). `assumptions/ontario.yaml`
keeps `provincial_demand_scenarios` and the `scenarios/*.yaml`
electricity-price files in structurally separate documents.

**Status:** Verified clean, though see 2.1 above for the separate
labelling concern on the same data.

### 3.2 Correlated optimistic assumptions could be combined without a coherence check

**Criticism:** Nothing currently prevents a user (or a future scenario
bundle) from simultaneously selecting the fastest technology-cost decline,
the maximum group-purchase discount, the highest electricity-price growth,
*and* full future VPP participation — an internally inconsistent
combination an economist would immediately flag (e.g., rapid battery
adoption plausibly *reduces* future arbitrage spreads; the model has no
mechanism connecting those two facts).

**Evidence:** `scenarios/`, `assumptions/technology_components.yaml`,
`assumptions/collective_purchasing.yaml`, `assumptions/value_streams/*.yaml`
are all independently selectable; no cross-scenario compatibility rule
exists beyond the value-stream compatibility matrix
(`assumptions/value_stream_compatibility.yaml`), which governs
double-counting of revenue, not scenario-assumption coherence.

**Severity:** High — this is one of the most economically substantive
findings in this review.

**Affected files:** None yet exist for scenario-coherence rules; this is a
net-new gap, not a bug in an existing file.

**Mitigation (this phase):** Named explicitly in this review's "Deferred to
next phase" section below, with the specific coherence relationships the
prompt calls out (rapid battery adoption → reduced future peak-price
spread; widespread solar → reduced midday export price; dynamic pricing →
reduced VPP aggregator value; high VPP participation → reduced future
capacity payments; high reserve → reduced grid-service revenue [already
true by construction in `model/battery_dispatch.py`]; high demand ≠ equal
retail-rate increase [already true, see 3.1]) recorded as required design
input for the next phase's scenario-bundle work.

**Remaining limitation:** Fully open until the next phase implements
scenario-compatibility rules.

**Test added:** None this phase.

**Status:** Deferred, high priority for next phase.

### 3.3 Opportunity cost is included but only in an advanced section — correctly scoped, verified

**Criticism (checked, mitigated by design):** `METHODOLOGY.md` section 6
explicitly places cash-purchase opportunity cost in an "advanced section...
not a default, objective fact" — this matches the economist's expectation
that opportunity cost should be visible but not silently baked into the
headline number.

**Status:** Verified clean by design.

### 3.4 Residual value calculation may not be consistent across purchase years — needs a stress test

**Criticism:** `model/scenario_v2.py`'s residual-value formula scales by
`years_active / max(1, horizon_years - purchase_year_offset)`, which is a
reasonable proportional approach, but has not been stress-tested against
an economist's expectation that a system purchased very close to the
horizon's end should show a residual value approaching its *full*
replacement cost (since it's barely used), not a token amount.

**Evidence:** `src/ontario_home_energy_futures/model/scenario_v2.py`,
`evaluate_purchase_decision`, residual-value calculation.
`tests/integration/test_fixed_horizon_fairness.py::test_residual_value_calculated_consistently_across_purchase_years`
only asserts an inequality (`wait_ten.residual_value_cad <=
buy_now.residual_value_cad`), not a specific expected magnitude.

**Severity:** Medium — the formula isn't obviously wrong, but it's
under-tested against economic intuition.

**Affected files:** `src/ontario_home_energy_futures/model/scenario_v2.py`.

**Mitigation (this phase):** Documented here and in `MODEL_CARD.md`'s
"Known limitations" as an area needing a dedicated economic-plausibility
test; not fixed this phase since it's part of the still-unwired Phase 2
engine.

**Remaining limitation:** Formula unverified against economic intuition at
the edges.

**Test added:** None this phase.

**Status:** Deferred.

### 3.5 Private benefit vs. system benefit / cost-shifting to non-participants not modelled or disclosed anywhere

**Criticism:** The entire model computes private household value. Nothing
in the application discusses whether net-metering credits, group-purchase
savings, or future VPP payments are funded (even partially) by other
ratepayers, or whether solar adoption shifts fixed-cost recovery onto
non-adopters — a standard economist critique of distributed-generation
incentive design.

**Evidence:** No file anywhere (model, template, or doc, prior to this
phase) discusses cost-shifting or non-participant impact.

**Severity:** High.

**Affected files:** None existed; net-new gap.

**Mitigation (this phase):** `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`
(new, this phase) has a dedicated section separating private household
value from utility/grid/government/non-participant cost, and states
explicitly where the magnitude of cost-shifting is unknown rather than
inventing a number.

**Remaining limitation:** Still no *quantitative* model of cost-shifting —
this is disclosure, not a new calculation.

**Test added:** None this phase (disclosure-only).

**Status:** Mitigated (disclosure), open (quantification).

---

## 4. Grid operator

### 4.1 Annual solar production figures could conceal hourly/seasonal mismatch — partially mitigated by design, not yet visible

**Criticism:** The site's rendered pages (Phase 1, live) show monthly
totals; hourly mismatch between production and demand is computed
internally (`model/solar.py::estimate_direct_self_consumption_kwh`) but
never surfaced to the user as an explicit "your solar and your demand
don't line up in winter" statement.

**Evidence:** `METHODOLOGY.md` section 3 explicitly labels the monthly
aggregation "an approximation, not equivalent to a validated hourly
simulation" — good — but no template currently shows a seasonal-mismatch
chart or table. `tests/integration/test_reference_scenario_f_electrification.py::test_seasonal_mismatch_visible_between_winter_heating_and_summer_solar`
tests that the underlying *data* shows the mismatch (January solar yield
< July; January household demand > July), but this is a model-layer test,
not a user-facing disclosure.

**Severity:** Medium-high for a grid-operator audience specifically.

**Affected files:** `web/templates/net_metering.html`,
`web/templates/current_costs.html`.

**Mitigation (this phase):** Named in this review's deferred section;
`MODEL_CARD.md` "Model boundaries" states the monthly-approximation
limitation explicitly for any reader, including a grid-operator persona.

**Remaining limitation:** No user-facing seasonal-mismatch visualization
exists yet.

**Test added:** None this phase.

**Status:** Deferred.

### 4.2 Export/interconnection limits are not modelled

**Criticism:** Nothing in the solar or net-metering model checks a
distributor's export capacity limit or interconnection queue/approval
process. A user could model an arbitrarily large system with no signal
that Hydro Ottawa (or any distributor) might reject or limit the
interconnection.

**Evidence:** `src/ontario_home_energy_futures/model/solar.py`,
`net_metering.py` — no `max_export_kw` or interconnection-limit field
anywhere. `assumptions/utilities/hydro-ottawa.yaml` has no such field
either.

**Severity:** High for a grid-operator persona; medium for a household
persona (still important, since an unapprovable system is unbuildable).

**Affected files:** `assumptions/utilities/hydro-ottawa.yaml`,
`src/ontario_home_energy_futures/model/net_metering.py`.

**Mitigation (this phase):** `MODEL_CARD.md` "Model boundaries" and
"Prohibited use" now state explicitly that this tool does not check
interconnection eligibility or export limits and that distributor
confirmation is required before any purchase — this is also recorded as a
required user-facing statement in `data/governance/claims.yaml`
(`claim-no-interconnection-limit-check`).

**Remaining limitation:** No technical check exists; disclosure only.

**Test added:** None this phase.

**Status:** Mitigated (disclosure), open (feature).

### 4.3 Battery reserve constraint — verified correctly enforced at the model layer

**Criticism (checked, mitigated):** The grid operator's concern that a
battery might be dispatched below a safe household reserve is directly
addressed: `model/battery_dispatch.py::dispatch_for_grid_services` clamps
`actual_dispatch` to `reserve_policy.dispatchable_kwh(battery)`, and
`test_dispatch_never_exceeds_reserve_respecting_capacity` /
`test_backup_only_policy_dispatches_zero_regardless_of_request` in
`tests/unit/test_battery_dispatch.py` confirm this holds even when a
caller requests far more dispatch than is available.

**Remaining limitation:** This is a Phase 2 model-layer guarantee not yet
wired into any live page — a grid operator reading only the live site
would not see this protection demonstrated, only find it by reading source.

**Status:** Verified clean at the model layer; not yet user-visible.

### 4.4 Capacity/availability/performance obligations exist in the value-stream schema but aren't validated against real programme rules

**Criticism:** `assumptions/value_streams/*.yaml` encodes
`customer_constraints` (minimum reserve, max cycles/day, opt-out events)
and `events` (min notice, max events/year) fields for programmes like VPP
availability/event payments — but these are illustrative defaults, not
confirmed against any real aggregator contract, because (per the YAML
files' own `source.type: illustrative` labels) no such Ontario programme
currently exists to check against.

**Severity:** Low — this is honestly labelled illustrative throughout, and
the illustrative-scenario status already excludes these from any default
result (`ValueStreamStatus.is_speculative`, tested in
`tests/unit/test_value_streams.py`).

**Status:** Accepted-risk — correctly labelled, cannot be more precise
until a real programme exists to reference.

### 4.5 Local grid value generalized across the province — verified as a named, honest limitation

**Criticism (checked, mitigated):** The Hydro One RRIP local-flexibility
value stream (`assumptions/value_streams/14-local-flexibility.yaml`)
explicitly states its figures are "generalized from the pilot's
approximate scale, not published contract rates" and "Geographic scope:
pilot area only" — a grid operator reading this specific file would find
its own concern already disclosed.

**Status:** Verified clean.

---

## 5. Climate and lifecycle specialist

### 5.1 No environmental/emissions claim exists anywhere in the user-facing site

**Criticism:** Zero occurrences of "emissions," "CO2," "carbon," "green,"
or "clean" in any template. This is the *opposite* failure from
greenwashing — the app currently makes no unsupported claim because it
makes no environmental claim at all — but it also means the "avoided
emissions" question a household reasonably has is entirely unanswered.

**Evidence:** Repo-wide grep across `web/templates/` returns no matches for
any emissions-related term. `model/cost_of_inaction.py` carries an
`emissions_consequence_note` field, but nothing renders it.

**Severity:** Medium (absence, not a false claim) — but worth fixing
correctly rather than quickly, per this project's own new
`docs/ENVIRONMENTAL-CLAIMS-POLICY.md`.

**Affected files:** All templates (absence); `model/cost_of_inaction.py`
(unused field).

**Mitigation (this phase):** `docs/ENVIRONMENTAL-CLAIMS-POLICY.md` (new)
establishes the rules any *future* environmental claim must satisfy before
it is added — specific, substantiated, geography/time-limited,
baseline-clear, lifecycle-stage-clear, reproducible, reviewed — explicitly
so that when environmental content is eventually added to templates, it
is added correctly the first time rather than needing a later greenwashing
correction.

**Remaining limitation:** The underlying question (does this household's
solar/battery meaningfully reduce emissions, and under what dispatch
policy) remains completely unanswered by the live product.

**Test added:** None this phase (no claim exists yet to test).

**Status:** Deferred — policy written, implementation not started.

### 5.2 Average vs. marginal grid emissions distinction does not yet exist anywhere in the codebase

**Criticism:** There is no emissions-factor data, no average/marginal
distinction, and no timing-of-consumption model connecting solar
generation or battery dispatch to actual displaced generation.

**Evidence:** No file under `assumptions/`, `src/ontario_home_energy_futures/model/`,
or `data/` contains an emissions factor of any kind.

**Severity:** High for future work, but currently zero risk of a false
claim since none is made.

**Mitigation (this phase):** `MODEL_CARD.md` "Environmental accounting"
section states this plainly: no emissions model exists yet; this is named
as a full module deferred to a future phase, not partially built and
partially disclosed.

**Status:** Deferred, documented honestly.

### 5.3 Battery arbitrage could in principle increase emissions — no mechanism exists to check this, correctly not claimed either way

**Criticism (checked, no false claim found):** Because no emissions model
exists (5.2), the app also does not claim battery dispatch reduces
emissions — avoiding a specific greenwashing trap the prompt calls out.
This is a case where the absence of a feature is also the absence of a
false claim.

**Status:** Verified clean (by omission); flagged for correct
implementation later per `docs/ENVIRONMENTAL-CLAIMS-POLICY.md`.

### 5.4 No claim that all exported solar displaces fossil generation — verified, not present

**Criticism (checked, not found):** Repo-wide search confirms no template
or doc asserts exported solar displaces any specific generation source.

**Status:** Verified clean.

---

## 6. Equity advocate

### 6.1 Renters and multi-unit residents have no path through the application

**Criticism:** Every input flow (household consumption, solar quote, net
metering, financing) assumes single-family homeownership with roof
control. There is no renter-facing content, no condominium/shared-roof
scenario, and no acknowledgment that a large share of Ontario households
cannot use this tool's core purchase-decision flow at all.

**Evidence:** `web/templates/household.html`, `net_metering.html` — no
`renter` or `condo` field or messaging anywhere.

**Severity:** High — this is a structural exclusion, not a wording issue.

**Affected files:** All input-flow templates (absence).

**Mitigation (this phase):** `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`
(new) states this limitation explicitly as its first and most prominent
finding, and lists community/shared-solar as an alternative this tool does
not yet model but should acknowledge as relevant for non-owners.
`MODEL_CARD.md` "Intended audience" and "Known limitations" both name
homeowner-with-roof-control as a scope boundary, not an unstated default.

**Remaining limitation:** No renter- or shared-ownership-facing feature
exists; documentation-only mitigation this phase.

**Test added:** None this phase.

**Status:** Mitigated (disclosure), open (feature).

### 6.2 Collective purchasing may primarily benefit already-advantaged households

**Criticism:** Group-purchase discounts require enough neighbourhood
coordination capacity, existing homeownership, and often existing solar
interest/literacy to organize — the kind of social and financial capital
correlated with higher income. Nothing in the collective-purchasing model
or its documentation acknowledges this distributional risk.

**Evidence:** `assumptions/collective_purchasing.yaml`,
`model/collective_purchasing.py` — purely mechanical percentage-discount
logic, no equity framing anywhere.

**Severity:** Medium-high.

**Affected files:** `assumptions/collective_purchasing.yaml`.

**Mitigation (this phase):** `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`
names this risk directly in its collective-purchasing section.

**Remaining limitation:** Disclosure only; no design change to reduce the
bias (e.g., no outreach-equity feature).

**Test added:** None this phase.

**Status:** Mitigated (disclosure).

### 6.3 No discussion of who funds incentives or bears grid-cost recovery

**Criticism:** See economist finding 3.5 — the same gap applies from an
equity lens: incentive funding and grid-cost recovery mechanisms are
typically broad-based (taxes or rates paid by everyone), while benefits
accrue to a subset of households able to install solar/storage.

**Severity:** High.

**Mitigation (this phase):** Same `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`
mitigation as 3.5, cross-referenced.

**Status:** Mitigated (disclosure), open (quantification).

### 6.4 No disability-related energy need is modelled (e.g., medical equipment backup)

**Criticism:** The battery/generator resilience discussion talks about
"critical load" generically but never prompts for or discusses
disability-related continuous-power needs (e.g., refrigerated medication,
powered mobility/medical equipment, communication devices) as a specific,
higher-stakes category of critical load.

**Evidence:** `web/templates/battery_generator.html` — generic "critical
load in watts" language only.

**Severity:** Medium-high.

**Mitigation (this phase):** `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`
names disability-related energy needs as a category the resilience section
must eventually support explicitly (e.g., a labelled "medical equipment"
critical-load category), not just generic wattage.

**Remaining limitation:** No such labelled input exists yet.

**Status:** Deferred (feature), mitigated (disclosure).

### 6.5 No mention of Indigenous communities, rural/remote reliability differences, or language/digital-access barriers

**Criticism:** The application is English-only, requires internet access
and a reasonably capable browser, and contains no content acknowledging
that Indigenous and northern/remote Ontario communities may face different
grid reliability baselines, different programme eligibility, or
jurisdictional considerations outside standard IESO/OEB/distributor
frameworks.

**Severity:** Medium — this is a real gap, but the application's stated
Phase 1 geographic scope (Ottawa/Hydro Ottawa only) already limits how
much this specific tool can responsibly claim about province-wide rural or
Indigenous-community applicability.

**Mitigation (this phase):** `docs/EQUITY-AND-DISTRIBUTIONAL-IMPACTS.md`
and `MODEL_CARD.md` "Geographic scope" both state the Ottawa/Hydro-Ottawa
limitation plainly and name language/digital-access and
Indigenous-community considerations as explicitly out of current scope
rather than silently ignored.

**Status:** Mitigated (disclosure).

---

## 7. Accessibility, privacy, and security reviewer

### 7.1 Accessibility posture is comparatively strong and largely already verified — real strength, not a gap

**Criticism (checked, mitigated by design):** `ACCESSIBILITY.md` documents
a genuine WCAG 2.2 AA target with a real manual-test checklist; templates
use semantic HTML, visible focus, native form controls, paired numeric
inputs alongside range sliders (`web/static/styles.css`
`.range-with-number`), and skip links. This is a credit to the existing
build, not a finding requiring a fix.

**Remaining limitation (already documented honestly):**
`ACCESSIBILITY.md`'s own "Known limitations" section already states that
Playwright/axe-core specs are written but not executed in this build
environment, and that a full manual screen-reader pass has not been
logged. This phase does not change that status — it remains accurately
disclosed.

**Status:** Verified clean (design), open (execution — pre-existing,
honestly disclosed).

### 7.2 No household bill/device data is retained on a server — verified by architecture

**Criticism (checked, mitigated by design):** The static-site,
no-database, no-account architecture (see `README.md` "What this
application does not do") structurally prevents server-side retention of
household data, because there is no server-side data store at all. This
is a strong, architecture-level privacy guarantee, not just a policy
promise.

**Status:** Verified clean.

### 7.3 VPP/EV remote-control and telemetry privacy/security risk is real but entirely undocumented

**Criticism:** The Phase 2 battery/EV dispatch model (`model/battery_dispatch.py`,
`model/ev_dispatch.py`) discusses aggregator participation, event
dispatch, and remote control conceptually, but nothing in the application
— model, YAML, or docs — discusses the privacy/security implications of a
real aggregator having remote dispatch control over a household's battery
or EV, or what telemetry such a programme would require.

**Evidence:** No file mentions "telemetry," "remote control," or
"cybersecurity" prior to this phase.

**Severity:** High for the (currently unwired) VPP/aggregator features
specifically.

**Affected files:** None existed; net-new gap.

**Mitigation (this phase):** `MODEL_CARD.md` "Privacy" section now states
explicitly that VPP/aggregator participation implies third-party remote
monitoring and/or control of household equipment, and that this is a
cybersecurity and privacy consideration distinct from this tool's own
no-server-retention design — the tool modelling a VPP payment does not
mean the tool grants or requires that access itself.

**Remaining limitation:** No dedicated privacy/security disclosure appears
on the (currently unwired) battery/EV page itself.

**Test added:** None this phase.

**Status:** Mitigated (disclosure at model-card level), open (page-level
disclosure).

### 7.4 Critical-load and resilience information could end up in a shareable URL if not handled carefully in future work

**Criticism:** The application's "shareable scenario" concept (documented
in `README.md`, not yet implemented as a live feature beyond the
downloadable-JSON format) has not yet been checked against the risk that a
household's critical-load list (which could reveal disability or medical
equipment) might end up encoded in a URL query string.

**Evidence:** `download.html` template; no query-string-based sharing
exists yet, so no current violation, but no explicit rule against it
exists either.

**Severity:** Medium (preventive, not yet a live issue).

**Mitigation (this phase):** `MODEL_CARD.md` "Privacy" section adds an
explicit rule: critical-load/resilience details must never be encoded in a
shareable URL, matching the project's existing "no exact address or
account number in a query string" convention (`README.md`) but extending
it explicitly to critical-load data, which didn't exist as a concept when
that convention was first written.

**Test added:** None this phase (no feature exists yet to test).

**Status:** Mitigated (preventive policy).

---

## 8. Open-model and reproducibility reviewer

### 8.1 Historical scenario retention convention is real and well-designed — verified strength

**Criticism (checked, mitigated by design):** The `supersedes` field
convention across `scenarios/*.yaml` and the explicit "never edit a
published scenario file in place" rule in `README.md` and
`CONTRIBUTING.md` is exactly the reproducibility practice this persona
would ask for.

**Status:** Verified clean.

### 8.2 Data provenance/hash-mismatch detection is real and tested — verified strength

**Criticism (checked, mitigated by design):**
`src/ontario_home_energy_futures/validate/provenance.py`'s
`validate_manifest_entry` detects a silently-replaced raw source file via
SHA-256 mismatch, and `tests/integration/test_data_pipeline.py` tests this
directly, including that a malformed update never corrupts previously
normalized data.

**Status:** Verified clean.

### 8.3 Documentation overstates current implementation status (SVG charts)

**Criticism:** `README.md`, `CHANGELOG.md`, and `ACCESSIBILITY.md` all
describe accessible SVG charts paired with data tables as delivered
functionality. `src/ontario_home_energy_futures/charts/` contains zero
files. A reproducibility reviewer following the README's own description
of the product would be unable to find the charts it describes.

**Evidence:** `README.md` "Architecture" section; `CHANGELOG.md` `[0.1.0]`
"Added" list; `ACCESSIBILITY.md` "Accessibility decision record: charts and
dynamic results" section — all describe chart behaviour in
present/past tense as if shipped.

**Severity:** High for a reproducibility/trust review specifically — this
is exactly the kind of documentation-vs-reality gap this persona exists to
catch, and it was a real, previously-unflagged issue found by this
review.

**Affected files:** `README.md`, `CHANGELOG.md`, `ACCESSIBILITY.md`.

**Mitigation (this phase):** **Fixed this phase.** All three files
corrected to describe chart support as planned/in-progress rather than
delivered. See the corresponding diffs.

**Remaining limitation:** None — this is a documentation-accuracy fix, now
correct.

**Test added:** None practical (a doc-accuracy assertion isn't naturally a
pytest test); manually verified via `find src/ontario_home_energy_futures/charts -type f`
returning empty and cross-checked against the corrected doc text.

**Status:** Mitigated — fixed this phase.

### 8.4 Sensitivity-analysis content on the live site is static, not computed, despite reading as computed output

**Criticism:** `web/templates/compare_timing.html`'s "What drives this
result" section says "The five assumptions with the largest effect on this
result, for the current inputs" — language that asserts the following
table is computed from the user's actual current inputs. The data backing
it (`sensitivity_rows` in
`src/ontario_home_energy_futures/site/build_site.py`) is five hardcoded
dictionaries with qualitative labels ("Largest," "Large," "Moderate")
that never change regardless of input. This is the most serious single
finding in this review: **a page claims to show computed, input-specific
output that is in fact static content identical for every user and every
input.**

**Evidence:** `src/ontario_home_energy_futures/site/build_site.py` lines
209-215 (the `sensitivity_rows` literal list);
`web/templates/compare_timing.html` line 28 ("for the current inputs").
`METHODOLOGY.md` section 12 describes a fully computed, ranked sensitivity
analysis, reinforcing the reader's expectation that this exists.

**Severity:** Critical. This is precisely the "looks calculated but isn't"
failure mode a reproducibility reviewer, an economist, and a consumer
advocate would all independently flag, and it was previously unflagged in
this codebase.

**Affected files:** `src/ontario_home_energy_futures/site/build_site.py`,
`web/templates/compare_timing.html`.

**Mitigation (this phase):** **Fixed this phase.** The template copy no
longer claims the table reflects "the current inputs"; it is now
explicitly labelled as a static, illustrative example of the *kind* of
assumption that typically matters most, pending the real computed
sensitivity module (`model/sensitivity.py`, not yet built — tracked in
"Deferred to next phase" below). This preserves the informational content
(which assumptions plausibly matter most) while removing the false claim
of per-user computation.

**Remaining limitation:** The page still does not show a truly
input-specific sensitivity ranking — that requires the deferred
`model/sensitivity.py` module. The fix this phase makes the page honest
about what it currently is, not more capable.

**Test added:** `tests/unit/test_build_site_honesty.py::test_sensitivity_section_does_not_claim_to_be_computed_from_current_inputs`
(new) — asserts the rendered `compare-timing.html` output does not contain
the phrase "for the current inputs" or equivalent, and does contain an
explicit "illustrative example" label near the sensitivity table.

**Status:** Mitigated — fixed this phase.

### 8.5 Uncertainty range shown in the comparison table is a naive min/max over six hardcoded decisions, not a distributional range

**Criticism:** `compare-timing.html`'s "uncertainty range" column
(rendered via `partials/comparison_table.html`) is populated with the
literal string `"See sensitivity table below"` for every row
(`build_site.py` line 119) rather than any computed range, while the
page's headline callout *does* compute a real (if narrow) `min()`/`max()`
across exactly six hardcoded decisions
(`_build_comparison_rows` in `build_site.py`) — a reproducibility reviewer
attempting to recompute this range from the described methodology would
get a different, wider range than the six-decision sweep actually
produces, since the README describes comparing "waiting one to five
years" but only a 3-year wait decision is actually included.

**Evidence:** `src/ontario_home_energy_futures/site/build_site.py`
`_build_comparison_rows`, decisions list (grid-only, buy-now, buy-now-5%,
buy-now-10%, wait-3yr, financed-now — missing wait-1/2/4/5yr);
`README.md` "What this application does" claims "waiting one to five
years" is compared.

**Severity:** High — a genuine reproducibility gap between documented and
actual behaviour.

**Affected files:** `src/ontario_home_energy_futures/site/build_site.py`,
`README.md`.

**Mitigation (this phase):** Named explicitly in "Deferred to next phase"
below (full 1-5 year wait sweep is part of the still-unwired Phase 2
`scenario_v2` engine, out of this phase's docs/governance scope).
`data/governance/claims.yaml` records the current live-site behaviour
accurately (`claim-comparison-table-scope`, noting today's build compares
only a 3-year wait, not the full 1-5 year range README describes) so the
gap is tracked rather than silently left inconsistent between two
documents.

**Remaining limitation:** README still describes broader comparison
coverage than the current live build delivers; full fix requires the
Phase 2 wiring.

**Test added:** None this phase (would require expanding
`_build_comparison_rows`, out of scope).

**Status:** Deferred, tracked.

### 8.6 Model version is a static string, not tied to git commit or content hash

**Criticism:** `model_version` (rendered in every page footer via
`base_ctx`) comes from `ontario_home_energy_futures.__version__`, a
manually-maintained string (`"0.1.0"`) — it does not change when
assumptions or model code change, so two different builds could both claim
`model_version: 0.1.0` while producing different results, which a
reproducibility reviewer would find confusing when trying to determine
whether two results are actually comparable.

**Evidence:** `src/ontario_home_energy_futures/__init__.py`;
`src/ontario_home_energy_futures/site/context.py` `SiteData.base_context`.

**Severity:** Medium.

**Mitigation (this phase):** Named in `MODEL_CARD.md` "Versioning" section
as a known limitation and a recommended future improvement (e.g., appending
a short content hash of `assumptions/` + `scenarios/` to the displayed
version).

**Remaining limitation:** Not fixed this phase (would require build-system
changes beyond docs/governance scope).

**Test added:** None this phase.

**Status:** Deferred.

---

## Deferred to next phase (explicit tracking)

Per this phase's scoping decision (documentation, governance, and honesty
fixes only — no new product features or live-site wiring), the following
substantive items from the hardening request are **not implemented this
phase** and are recorded here so they are never silently dropped:

| Item | Why deferred | Where it will land |
|---|---|---|
| Financial-safety warning system (unaffordable financing, payback-after-move-out, roof-replacement-before-payback, etc.) | Requires new model logic + template UI, beyond docs/governance scope | New `model/financial_safety.py` + template warnings |
| Regret analysis (`Regret_d,s = C_d,s - min_j C_j,s`) | Requires `scenario_v2` to be fully wired first | Extension of `model/scenario_v2.py` + new `model/regret.py` |
| Robustness classification (robust/conditional/speculative/resilience-led/environment-led/financially-unsuitable/insufficient-evidence) | Depends on regret analysis + financial-safety thresholds above | New `model/robustness.py` |
| Scenario-compatibility/coherence rules (economist finding 3.2) | New rule engine beyond the existing value-stream compatibility matrix | Extension of `assumptions/value_stream_compatibility.yaml` or a new `assumptions/scenario_coherence.yaml` |
| Climate/extreme-weather model (degree days, return-period explanation, physical risk) | Entirely new module, needs ClimateData.ca/Canada in a Changing Climate source review | New `assumptions/climate.yaml` + `model/climate.py` |
| Environmental accounting module (marginal/average emissions, embodied emissions, dispatch trade-offs) | Entirely new module (finding 5.1, 5.2) | New `assumptions/emissions.yaml` + `model/emissions.py` |
| Full 1-5 year wait-option sweep + true computed uncertainty range | Part of Phase 2 site-wiring (finding 8.5) | `scenario_v2` wiring into `build_site.py` |
| Live sensitivity computation (`model/sensitivity.py`) | Was already planned in the prior session's Phase 2 scope | `model/sensitivity.py` (scaffolded in prior plan, not yet built) |
| Adversarial test suite for losing outcomes at the presentation layer | Depends on Phase 2 site wiring existing first | `tests/integration/test_adversarial_outcomes.py` |
| "What would make this wrong?" per-result section | Depends on sensitivity/regret work above | Template addition once computed |
| Illustrative-quote pre-fill fix (consumer-advocate 1.1) | Template change, deferred to keep this phase docs-only except for the two named honesty fixes | `web/templates/net_metering.html` |
| On-page (not just methodology-page) net-metering eligibility caveat (regulator 2.2) | Template change | `web/templates/net_metering.html` |
| Interconnection/export-limit modelling (grid operator 4.2) | New model feature | `model/net_metering.py`, `assumptions/utilities/*.yaml` |
| Seasonal-mismatch visualization (grid operator 4.1) | Depends on chart infrastructure (also not yet built) | `charts/` + `net_metering.html` |
| Renter/shared-ownership input path (equity 6.1) | New feature | New template + model support |
| Disability-specific critical-load category (equity 6.4) | New feature | `battery_generator.html` + `assumptions/batteries.yaml` |
| VPP/EV telemetry privacy disclosure at the page level (accessibility/privacy 7.3) | Template change, page doesn't exist live yet | Future battery/EV page |

This table is the authoritative "not done yet" list for this phase. Anyone
reading only `MODEL_CARD.md`'s summary should be pointed back here for the
full itemized detail.
