# Methodology

This document explains how Ontario Home Energy Futures calculates its results,
what every default assumption is, and where the model's known limitations are.
Every default described here is stored in an editable YAML file under
`assumptions/` or `scenarios/` — nothing described here is hidden in source code.

This is a **planning and scenario tool**. It does not predict future prices and
does not guarantee savings. Every dollar figure it reports is the output of a
labelled set of assumptions you can inspect and change.

## 1. Bill reconstruction

A standardized monthly bill is built as:

```
B_t = E_t + G_t + T_t + D_t + R_t + X_t − S_t
```

where `E_t` is the electricity/energy commodity charge, `G_t` generation and
capacity cost, `T_t` transmission, `D_t` distribution (fixed + variable delivery),
`R_t` regulatory charges, `X_t` tax, and `S_t` any subsidy or rebate (e.g. the
Ontario Electricity Rebate).

For Ontario residential customers, `G_t` and `T_t` are, in practice, embedded in
the OEB-regulated commodity/Global Adjustment charge rather than itemized
separately on a residential bill; this model keeps them as distinct internal
components (`src/ontario_home_energy_futures/model/bill.py`) so that future
Global-Adjustment-specific policy changes can be modelled without restructuring
the bill, while the rendered bill groups them under "electricity consumption
charge" to match what a household actually sees.

Two Hydro Ottawa rate plans are modelled in Phase 1:

- **Time-of-use (ToU):** off-peak / mid-peak / on-peak per-kWh rates applied to a
  representative load shape (see §3).
- **Tiered:** a lower rate up to a monthly threshold, a higher rate above it.

Ultra-low overnight pricing is included in the schema
(`assumptions/utilities/hydro-ottawa.yaml`) but is only activated once an
adequate load-profile is available, per the project's requirements; Phase 1 does
not present ultra-low overnight results because the representative overnight
load share has not been verified against a real Ottawa-region profile.

Fixed delivery charges apply regardless of consumption, including at 0 kWh net
consumption after solar. **This model never zeroes out the fixed delivery
charge because of solar production.**

## 2. Household consumption model

Monthly household demand is:

```
D_m = B_m + EV_m + HP_m + WH_m + AC_m + O_m − EE_m
```

`B_m` is baseline consumption (from a standard profile, an annual estimate spread
seasonally, or user-entered monthly values). `EV_m`, `HP_m`, `WH_m`, `AC_m`, `O_m`
are optional user-modelled additions (EV charging, heat pump, water heating,
cooling, other), and `EE_m` is any modelled efficiency saving.

**Phase 1 scope:** EV, heat pump, water heater, and cooling inputs are accepted
and produce a documented annual-kWh addition (see `assumptions/household-loads.yaml`
for the default assumptions behind each), spread across months using a simple
seasonal shape. This is **not** a hourly simulation. The data structures are
shaped so that Phase 3 can replace the seasonal-shape approximation with an
hourly synthetic load profile without changing the household-model interface,
but Phase 1 explicitly does not claim hourly accuracy.

Heat-pump electricity use is not estimated from floor area alone; it requires an
approximate current annual heating consumption and a seasonal efficiency
(coefficient of performance) input, because floor area alone is not a reliable
predictor.

## 3. Representative hourly/monthly load and solar shapes

The public interface presents monthly and annual results. The underlying data
model is designed around 8,760 hourly intervals so that Phase 3 can implement
direct self-consumption, time-of-use/ultra-low-overnight interaction, export,
EV charging, and battery dispatch without a rewrite.

For Phase 1:

- A documented representative hourly household load shape (labelled `status:
  estimate` in `assumptions/household-loads.yaml`) is scaled to the user's
  monthly/annual kWh.
- A documented representative hourly solar production shape (§4) is used.
- Hourly results are aggregated into monthly bills for display.

**This monthly aggregation is an approximation, not equivalent to a validated
hourly simulation, and is labelled as such wherever it appears.**

## 4. Solar production model

Monthly solar production:

```
S_m = K × Y_m × (1 − d)^y
```

`K` is installed DC capacity (kW), `Y_m` a location-specific monthly yield
(kWh per installed kW, from `assumptions/solar.yaml`), `d` the assumed annual
degradation rate, and `y` system age in years. Inputs include Ontario region,
system size, orientation, pitch, shading estimate, degradation, inverter
efficiency, and other system losses. No exact street address is requested or
required — only a region or forward-sortation area.

Where detailed regional solar-resource data is unavailable, a single
Ottawa-region illustrative monthly yield profile is used
(`assumptions/solar.yaml`, `status: estimate`), documented as an approximation
pending integration of a proper Canadian solar-resource dataset (see
[DATA_SOURCES.md](DATA_SOURCES.md)).

## 5. Ontario net-metering credit ledger

Each month, solar production is split into:

1. **Direct self-consumption** — solar kWh used in the home at the time it is
   generated (estimated from the hourly household and solar shapes).
2. **Grid imports** — household demand not covered by direct self-consumption.
3. **Exported generation** — solar kWh not used directly, sent to the grid.

Exported generation becomes a **non-cash generation credit**, never a cash
payment. Credits are tracked as dated tranches:

```
opening credit
+ new credit from eligible exported electricity (this month)
− credit used against eligible imported-electricity charges (this month)
− credit expiring this month (12 months after creation)
= closing credit
```

Each tranche retains its creation month and expires exactly 12 months later if
unused, oldest tranche first (FIFO). Credits are applied **only** against the
eligible electricity-consumption (energy/commodity) charge on imported
electricity. They are never applied to fixed delivery charges, ineligible
variable delivery charges, regulatory charges, or taxes — this is enforced in
`model/net_metering.py` and must be re-verified against the selected
distributor's current billing practice and OEB rules before being relied upon
for a real decision (see [DATA_SOURCES.md](DATA_SOURCES.md)).

An oversized system (production far exceeding consumption) can and does produce
expired, unused credits in this model — the model does not artificially cap
system size to avoid that outcome, because showing that outcome is part of the
point.

The realized financial value of solar is reported as **effective dollars per
generated kWh**, which is typically lower than the full retail rate once
exports, credit expiry, and ineligible-charge exclusions are accounted for.
**Every generated kWh is not treated as having the same financial value.**

## 6. Solar purchase-cost and financing model

Installed cost is decomposed into panels, inverter, racking, electrical
equipment, labour, design/engineering, permitting, utility connection, installer
overhead, taxes, financing, optional battery, and other user-defined costs.
Users may enter a complete contractor quote or use the system-capacity-based
regional estimate.

A group-purchase discount (0%, 5%, 10%, or custom) applies only to the eligible
quote components identified in the quote breakdown — never automatically to
government fees, taxes, or financing charges.

Financing uses standard loan amortization (principal, rate, term) to compute
monthly payment, total interest, and year-by-year outstanding balance. Interest
avoided through a lower financed principal (from a group discount) is reported
as a separate line from the discount's direct price reduction — the discount is
not described as producing "exponential" interest growth or savings; it is a
linear reduction in principal whose downstream interest effect is calculated
directly from the amortization schedule.

For cash purchases, an opportunity-cost comparison (what the cash might have
earned invested elsewhere) is available only in an advanced section, and is
presented as an explicit, editable assumption — not a default, objective fact.

## 7. Electricity-price scenarios

Bill components are projected forward using separate real annual growth rates
for the energy charge, fixed delivery, and variable delivery components, plus a
separate general-inflation rate — never a single blended "electricity rate"
growth number. Four illustrative scenarios (low, reference, high, stress) plus a
user-defined custom scenario are provided in `scenarios/`. Each scenario file
records:

- Real annual change per bill component (not nominal — nominal is derived by
  compounding with the separately stated inflation assumption).
- The IESO provincial system-demand-growth figure it is shown alongside, purely
  as context (see §9) — **never used to derive the price-growth number itself.**
- A list of named uncertainties (generation procurement, nuclear refurbishment,
  transmission/distribution investment, data-centre connections, interest
  rates, extreme weather, government rebates) that could move the actual
  outcome away from the scenario.
- `status: scenario`, a `created_at` date, and a `supersedes` field pointing to
  any prior version it replaces. Published scenario files are never edited in
  place.

## 8. Solar-cost-decline scenarios

Installed-cost changes are modelled separately from underlying module-price
indices, because global module costs decline faster than complete Ontario
residential installed cost (which includes labour, permitting, connection, and
overhead that do not track module prices at the same rate).

```
C_y = C_0 × (1 − r)^y                    (real terms)
C_y,nominal = C_0 × (1 − r)^y × (1 + i)^y   (nominal terms)
```

Four illustrative real annual decline scenarios are provided: flat (0%),
moderate (−2%), faster (−4%), and custom. Each is a versioned YAML file, never
edited in place once published — this lets the site later show how an earlier
decline projection compared with what actually happened, without rewriting
history.

## 9. Provincial demand scenarios (context only)

The IESO Annual Planning Outlook publishes low/reference/high **provincial
system demand** growth scenarios to 2050 (recorded in
`assumptions/ontario.yaml`, sourced to the outlook's publication year). This
figure is influenced by data centres, AI computing, EV adoption, building
electrification, industrial development, population, economic activity,
efficiency, extreme heat, electrified winter heating, and government policy.

**This model never converts a provincial demand-growth percentage into a
household kWh addition or a retail-price growth percentage.** It is shown
alongside the electricity-price scenarios as explanatory context for *why*
future prices are uncertain, not as an input to the price calculation itself.

## 10. Twenty-year (and other horizon) planning comparison

The default planning horizon is 20 years; 10, 25, and 30-year horizons are also
available. **Twenty years is a default modelling horizon, not a claimed physical
panel lifespan.**

For each purchase-timing option `y` (buy now, wait 1–5 years, or grid-only), the
model computes:

```
Total cost_y = grid costs before installation
             + solar purchase and financing cost
             + grid costs after installation
             + maintenance and replacement
             − incentives
             − valid (unexpired, eligible) net-metering credits
```

Both undiscounted nominal cash flow and a discounted present value (using a
user-editable discount rate) are reported. The comparison objective minimizes
net present value across grid bills, solar cost, financing, maintenance,
replacement, incentives, and eligible credits — but the tool reports this as the
**lowest-cost result under the selected assumptions**, not as personalized
financial advice.

Panel degradation, inverter replacement, maintenance, optional battery
replacement, remaining system residual value at the end of the horizon, and an
optional decommissioning cost are all included as separately editable line
items.

## 11. Cost of waiting

Falling solar prices do not automatically make waiting the better choice,
because waiting also means continued grid bills, lost solar generation, greater
exposure to electricity-price increases during the waiting period, and possible
changes to incentives or financing rates.

The model solves for the minimum annual real solar-cost decline rate `r`
required for waiting `y` years to produce a lower NPV than buying now, holding
the other selected assumptions fixed, and reports it in the form:

> Under the selected assumptions, installed solar prices would need to fall by
> at least X% per year for Y years for waiting until <year> to cost less than
> buying in <year>.

This breakeven rate is always shown alongside the assumptions used to compute
it, and alongside the alternative of taking a 5% or 10% neighbourhood discount
now instead of waiting.

## 12. Sensitivity analysis

The model recomputes total cost while independently varying each of: electricity
price escalation, solar installed-cost decline, initial quote, group discount,
solar production, panel degradation, financing rate, discount rate, inverter
replacement cost/timing, household consumption, EV/heat-pump adoption, net
metering credit expiry, and incentives. Results are ranked by effect size and
shown as an accessible table (with an optional supplementary horizontal bar
chart), identifying the assumptions that most influence the result for the
current inputs.

## 13. Battery and generator boundaries (Phase 1 scope)

Phase 1 documents the battery and generator cost model and ownership
comparison structure (`assumptions/batteries.yaml`, `assumptions/generators.yaml`)
but does not yet implement validated hourly battery-dispatch optimization or a
full generator fuel-cost simulation — this is explicitly deferred to Phase 3, so
that Phase 1's data provenance and net-metering accuracy are not weakened by
rushing dispatch modelling ahead of validated hourly load and generation data.

Where a battery or generator figure is shown in Phase 1, it separates ordinary
energy economics (self-consumption increase, rate shifting) from backup and
resilience value, and **does not assign an invented dollar value to outage
resilience by default.**

## 14. Known limitations

- Household and solar hourly shapes are documented representative estimates,
  not measured for any individual home.
- Only Hydro Ottawa is currently modelled; the YAML schema supports additional
  distributors, but none are yet added.
- Ultra-low overnight pricing is defined in the schema but not yet exposed,
  pending a verified overnight load-share assumption.
- Solar-resource data uses a single Ottawa-region profile pending integration of
  a proper geographic dataset.
- Illustrative electricity-price and solar-cost-decline scenarios are modelling
  assumptions set by project maintainers, not official government or utility
  forecasts, and must be labelled as such everywhere they appear.
- Battery and generator dispatch modelling is deferred to Phase 3.
- Net-metering eligible-charge rules are encoded from documentary review and
  should be re-verified against current OEB and distributor billing practice
  before being relied upon for a real financial decision.
