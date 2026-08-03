# Environmental Claims Policy

## Current status

**Ontario Home Energy Futures currently makes no environmental or
emissions claim of any kind.** No template, generated result, or piece of
copy in this application states or implies that solar, battery, or EV
adoption reduces emissions, is "green," "clean," or has any other
environmental benefit. See
[docs/RED-TEAM-REVIEW.md §5.1](RED-TEAM-REVIEW.md) and
[data/governance/claims.yaml](../data/governance/claims.yaml)'s
`claim-no-emissions-model-exists` entry.

This is a deliberate state, not an oversight waiting to be quietly filled
in. This document exists so that **when** an environmental claim or
emissions module is eventually added, it is added correctly the first
time, following Canadian greenwashing guidance, rather than needing a
later correction.

## Governing guidance

This policy follows the Competition Bureau of Canada's greenwashing
guidance for businesses:
<https://competition-bureau.canada.ca/en/deceptive-marketing-practices/greenwashing-guidance-businesses>.

## Requirements for any future environmental claim

Before any environmental or emissions-related claim is added to this
project (in a template, a generated result, documentation, or marketing
copy), it must be:

1. **Specific.** Name the exact quantity, mechanism, and scope (e.g. "this
   scenario's modelled solar self-consumption is X kWh/year, evaluated
   against Ontario's Y-year average grid emissions intensity") — never a
   vague assertion of environmental benefit.
2. **Properly substantiated.** Backed by a documented methodology and a
   cited, dated data source, following the same provenance discipline this
   project already applies to financial claims (see
   [data/governance/claims.yaml](../data/governance/claims.yaml)).
3. **Limited to the relevant geography.** An Ontario-specific claim must
   use Ontario-specific grid data, not a national or continental average,
   unless explicitly labelled otherwise.
4. **Limited to the relevant time period.** Emissions intensity varies by
   hour, season, and year; a claim must state which period it covers and
   must not imply permanence.
5. **Clear about comparison baselines.** State explicitly what is being
   compared to what (e.g. "compared to grid electricity at the time of
   consumption" vs. "compared to the province's annual average") — see
   the marginal-vs-average distinction below.
6. **Clear about omitted lifecycle stages.** If a claim covers only
   operational emissions, it must say so explicitly and must not be
   presented as a full lifecycle assessment unless one has actually been
   done.
7. **Reproducible.** Another person must be able to recompute the claim
   from the documented methodology and cited data, the same standard this
   project applies via [docs/CORRECTIONS.md](CORRECTIONS.md) and
   [GOVERNANCE.md](../GOVERNANCE.md).
8. **Reviewed before publication.** Every new environmental claim must be
   added to [data/governance/claims.yaml](../data/governance/claims.yaml)
   with a real `source_url`, and must not be marked `status: approved`
   until independently checked against that source — matching this
   project's existing claims-register discipline.

## Required methodological distinctions

Any future emissions module must distinguish, and never conflate:

- **Operational emissions** (electricity used/avoided during operation)
  vs. **embodied emissions** (manufacturing, transport, and installation
  of panels, batteries, inverters, and chargers).
- **Marginal grid emissions** (the emissions intensity of the generation
  actually displaced or added at the specific hour of consumption/export)
  vs. **annual average grid emissions** (the province's blended intensity
  across the whole year). **A solar kWh must never be claimed to avoid
  the annual average Ontario grid emissions intensity by default** — the
  marginal generator at the time of export may be very different from the
  annual average, and Ontario's own generation mix (heavily nuclear and
  hydro) means the annual average is not necessarily representative of
  what a given hour's exported solar kWh actually displaces.
- **Equipment replacement and battery degradation** — recurring embodied
  emissions from replacing an inverter or battery over the planning
  horizon must be included if any lifecycle claim is made, not treated as
  a one-time cost.
- **End-of-life treatment** — disposal or recycling impacts must be
  addressed or explicitly marked as excluded, not silently omitted.
- **Additionality** — whether a household's action actually causes an
  emissions reduction that would not otherwise have happened, versus
  simply shifting where/when existing clean generation is counted.
- **Timing of consumption** — battery arbitrage or EV charging shifted to
  a different hour can, in principle, *increase* net emissions if it draws
  from a higher-carbon marginal source at the new time; a future dispatch
  model must be able to represent this possibility, not assume every
  shift is beneficial.
- **Location of grid constraints** — local transmission/distribution
  constraints can change the effective marginal generator for a specific
  area; a province-wide average must not be presented as
  location-specific.

## Prohibited terms (without qualification and substantiation)

The following terms must not be used unqualified anywhere in this
project's user-facing content:

- "Green"
- "Zero impact"
- "Emissions-free"
- "Carbon neutral"
- "Cleanest"
- "Climate positive"
- "Guaranteed carbon savings"

## Narrow permitted exception

A claim may use the phrase **"zero operational emissions at the point of
generation"** to describe solar photovoltaic generation specifically,
*only if* the surrounding text makes explicit that this refers narrowly to
the point-of-generation operational stage, and does not extend to
embodied emissions, grid emissions displaced, or any lifecycle claim. This
phrase must never appear without that qualifying context in the same
paragraph.

## Enforcement

- Any pull request adding environmental or emissions-related copy must
  add a corresponding entry to
  [data/governance/claims.yaml](../data/governance/claims.yaml) in the
  same change.
- [docs/RED-TEAM-REVIEW.md](RED-TEAM-REVIEW.md) should be updated with a
  climate/lifecycle-specialist review of any new environmental claim
  before it ships, following the pattern already established for the
  financial claims reviewed there.
- Battery/EV dispatch policies, when implemented, must be selectable
  independently for financial optimization vs. emissions optimization
  (see [MODEL_CARD.md](../MODEL_CARD.md) "Environmental accounting"), and
  the application must be able to show these two objectives disagreeing —
  it must never silently collapse environmental impact into the financial
  result by default.
