# Equity and Distributional Impacts

This document names who this application currently serves, who it
excludes, and where its financial results may look different depending on
who bears the cost versus who captures the benefit. See
[docs/RED-TEAM-REVIEW.md §6](RED-TEAM-REVIEW.md) for the full adversarial
findings this document summarizes and extends.

Where a distributional effect is not currently quantified by this
project, this document says so explicitly rather than inventing a number.

## Who can participate

This application's core purchase-decision flow assumes:

- **Single-family homeownership with roof control.** There is currently no
  renter-facing path, no condominium/shared-roof scenario, and no
  acknowledgment inside the input flow that a large share of Ontario
  households cannot act on this tool's central comparison at all.
- **Access to credit or cash for an upfront purchase.** The financing
  model assumes a household can either pay cash or qualify for a loan at
  the assumed rate; it does not model credit-access barriers.
- **English literacy and digital access.** The site is English-only and
  requires a reasonably capable browser and internet connection.
- **A single-family detached or similar structure**, not an apartment or
  multi-unit building where individual roof allocation is impractical.

**Homeowners versus renters:** Renters cannot install solar or a battery
on a property they do not own, and typically cannot benefit from
net-metering credits tied to a specific electrical account they do not
control. This tool does not currently model any renter-relevant
alternative (e.g., a green power purchase option, or advocating for
landlord-installed systems).

**Detached homes versus apartments:** Apartment and condominium residents
face structural barriers (shared roof, body-corporate approval,
individual metering) this tool does not address. Community or shared
solar arrangements — where a resident buys into a share of an off-site or
building-scale system without personal roof access — are a real
alternative in some jurisdictions but are **not modelled here**.

**Suitable versus unsuitable roofs:** The tool asks for orientation and
shading estimates but does not assess structural capacity, age, or
whether roof replacement is imminent — a barrier disproportionately
affecting older housing stock, which is not evenly distributed across
income levels.

## Who pays

**Private household value versus system/utility/government value.** Every
dollar figure this tool computes is the *private* value to the
participating household — never the cost or benefit to the electricity
system, other ratepayers, or government as a whole. These are kept
conceptually separate:

- **Utility value**: not modelled. Whether a household's solar/battery
  reduces or increases a distributor's operating or capital costs is
  outside this tool's scope.
- **Grid value**: partially represented via the value-stream schema's
  `local_flexibility` and `capacity_payment` categories
  (`assumptions/value_streams/`), but these figures describe a
  *potential payment to the household*, not the underlying grid
  cost-benefit calculation behind that payment.
- **Government expenditure**: incentive programmes (where they exist) are
  publicly funded; this tool does not track or disclose the aggregate
  cost of any incentive programme, only the individual household's
  eligible benefit.
- **Cost to other ratepayers**: net-metering credits, and any future
  VPP/capacity/flexibility payment, may be funded in whole or in part
  through distribution or transmission charges paid by all ratepayers,
  including those who cannot or do not adopt solar/storage. **This
  project does not currently quantify that cost-shifting.** It is a real
  and legitimate concern (see
  [docs/RED-TEAM-REVIEW.md §3.5](RED-TEAM-REVIEW.md)) that this document
  records as an open, unquantified limitation rather than either ignoring
  it or inventing a figure.
- **Societal environmental value**: not modelled — see
  [docs/ENVIRONMENTAL-CLAIMS-POLICY.md](ENVIRONMENTAL-CLAIMS-POLICY.md)
  and [MODEL_CARD.md](../MODEL_CARD.md) "Environmental accounting."

## Collective purchasing and wealth bias

`assumptions/collective_purchasing.yaml` and
`model/collective_purchasing.py` model group-purchase discounts as a
mechanical percentage reduction on eligible cost components, scaled by
group size. **This mechanism does not account for who is able to organize
or join such a group.** Coordinating a 5-, 10-, or 20-household purchase
typically requires:

- Existing homeownership (see above).
- Social capital and time to organize neighbours.
- Pre-existing interest in or knowledge of solar, often correlated with
  higher income and education.

There is a real risk that collective-purchasing savings, as currently
modelled, primarily benefit households that already have the means and
social position to organize a group — while the tool's framing ("a
neighbourhood discount") could read as broadly accessible. This
document, and [docs/RED-TEAM-REVIEW.md §6.2](RED-TEAM-REVIEW.md), name
this risk explicitly. No design change has been made yet to mitigate it
(e.g., a feature supporting outreach to lower-income households as part of
a group purchase) — this is a named gap, not a solved problem.

## Income and financing

The financing model (`assumptions/financing.yaml`,
`model/financing.py`) uses a single illustrative loan rate/term by
default. It does not:

- Adjust for a household's actual creditworthiness or income.
- Warn when a modelled monthly payment would be unaffordable relative to
  typical household budgets (see
  [docs/RED-TEAM-REVIEW.md](RED-TEAM-REVIEW.md), "Deferred to next phase"
  — a financial-safety warning system is planned but not yet built).
- Distinguish households for whom a loan default would be catastrophic
  from those for whom it would be a manageable setback.

Low-income households considering financing should be especially cautious
using this tool's default assumptions, since the tool cannot currently
tell them whether a given payment is safe for their specific situation —
see [MODEL_CARD.md](../MODEL_CARD.md) "Financial risks" and "Prohibited
use."

## Disability-related energy needs

The battery/generator resilience discussion (`web/templates/battery_generator.html`)
currently asks about "critical load in watts" generically. It does not
have a labelled category for disability-related continuous-power needs —
refrigerated medication, powered mobility or medical equipment,
communication devices — which represent a materially different, often
higher-stakes backup requirement than general household convenience loads.
This is named as a gap to address in a future phase (see
[docs/RED-TEAM-REVIEW.md §6.4](RED-TEAM-REVIEW.md)), not yet implemented.

Related privacy note: any future disability/medical critical-load input
must never be encoded in a shareable URL or retained longer than needed —
see [MODEL_CARD.md](../MODEL_CARD.md) "Privacy."

## Rural, remote, and Indigenous communities

This tool's Phase 1 geographic scope is Ottawa/Hydro Ottawa specifically.
It makes no claim, and should make no claim, about rural, remote, or
northern Ontario reliability baselines, which can differ substantially
from an urban distributor's service territory. It similarly makes no
claim about Indigenous community energy programmes, jurisdictional
considerations, or eligibility rules that may differ from standard
IESO/OEB/distributor frameworks. These are named as explicitly out of
current scope — not silently assumed to be the same as the Ottawa case —
per [MODEL_CARD.md](../MODEL_CARD.md) "Geographic scope."

## Language and digital-access barriers

The application is English-only and requires internet access and a
reasonably modern browser. It does not currently support French (an
official language of Ontario/Canada) or any other language, and has no
low-bandwidth or offline-first fallback beyond what its static-site
architecture already provides incidentally (no JavaScript required for
core content — see [ACCESSIBILITY.md](../ACCESSIBILITY.md)).

## Community and non-ownership alternatives

The following alternatives to individual home ownership of solar/battery
equipment are **not currently modelled** by this tool, but are named here
so a reader understands the comparison set is incomplete:

- Community solar / shared solar gardens.
- Utility or third-party green-power purchase options.
- Renter-relevant advocacy (e.g., landlord incentive programmes).
- Cooperative or non-profit ownership models.

## Where distributional effects are unknown

This document explicitly states, rather than omits, that the following
are currently unknown or unquantified by this project:

- The magnitude of cost-shifting from solar/storage adopters to
  non-adopting ratepayers under current Ontario net-metering rules.
- Whether collective-purchasing participation in practice
  disproportionately favours higher-income households (a plausible risk,
  not a measured outcome).
- The distributional profile (by income, tenure, geography, or
  disability status) of Ontario households who have historically adopted
  residential solar.
- Whether any future VPP/capacity/flexibility payment programme, if
  implemented in Ontario, would be structured in a way that includes or
  excludes lower-income participants.

Where this project's own data or modelling could speak to one of these
questions in the future, it should be added with the same sourcing
discipline as every other claim in
[data/governance/claims.yaml](../data/governance/claims.yaml) — not
asserted without evidence.
