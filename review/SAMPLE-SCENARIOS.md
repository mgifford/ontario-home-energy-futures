# Sample Scenarios

Worked examples an independent reviewer can reproduce directly from this
project's existing, tested reference scenarios (`tests/integration/`) and
model modules (`src/ontario_home_energy_futures/model/`). Every number
below is either an existing test's assertion or directly computable by
running the commands shown — none is invented for this document.

See [REVIEW-GUIDE.md](REVIEW-GUIDE.md) "Reproduce a result" for
environment setup.

## Reference Scenarios A–F (existing, tested)

These are this project's own standard reference scenarios, already
encoded as integration tests. Reviewing them is the fastest way to see
the model's actual behaviour rather than marketing language:

| Scenario | File | What it demonstrates |
|---|---|---|
| A — Standard household | `tests/integration/test_reference_scenario_a_standard_household.py` | Fixed delivery charges persist even at reduced consumption; nominal vs. real costs both available. |
| B — Solar now | `tests/integration/test_reference_scenario_b_solar_now.py` | Direct self-consumption and exports are tracked separately; credits offset only eligible charges; unused credits can expire. |
| C — Group discount | `tests/integration/test_reference_scenario_c_group_discount.py` | A 10% discount reduces principal and interest, but never discounts ineligible fees; direct savings and avoided interest are reported as two separate numbers. |
| D — Wait for lower cost | `tests/integration/test_reference_scenario_d_wait_for_lower_cost.py` | Grid costs continue during a wait period; buying now and waiting produce genuinely different, comparable totals. |
| E — Oversized system | `tests/integration/test_reference_scenario_e_oversized_system.py` | A system sized well above household demand produces high exports, expired credits, and a realized value per kWh below the full retail rate. |
| F — Electrification | `tests/integration/test_reference_scenario_f_electrification.py` | Adding an EV and heat pump increases household demand; provincial demand-growth figures are never added directly to household kWh; winter heating and summer solar show a visible seasonal mismatch. |

Run them yourself:

```bash
pytest tests/integration/test_reference_scenario_a_standard_household.py -v
pytest tests/integration/test_reference_scenario_e_oversized_system.py -v
```

## Where each major decision type can win (or lose)

A reviewer's core concern is often: *can this tool ever conclude that
solar or immediate purchase is the wrong choice?* Yes — this is tested
directly at the model layer:

- **"No action"/grid-only can be the lowest-cost outcome:**
  `tests/unit/test_cost_of_inaction.py::test_no_action_can_be_worst_without_special_casing`
  and `test_does_not_assume_buy_now_is_always_best` construct exactly
  this case and assert the model's `min()`-based comparison
  (`model/cost_of_inaction.py::calculate_cost_of_inaction`) does not
  special-case "buy now" as automatically best.
- **An oversized solar system underperforms a right-sized one financially:**
  see Scenario E above — `effective_value_per_generated_kwh()` drops below
  the full retail rate once exports and expired credits are accounted for.
- **Waiting can beat buying now:** Scenario D's structure supports this
  outcome (it depends on the specific price/decline assumptions selected —
  try varying `scenarios/solar-cost-decline/faster.yaml`'s decline rate
  against `scenarios/reference.yaml` yourself and observe when the
  comparison flips, or use `model/waiting.py::find_breakeven_decline_rate`
  directly).

## What is not yet demonstrable this way

Per [docs/RED-TEAM-REVIEW.md](../docs/RED-TEAM-REVIEW.md) "Deferred to
next phase," the following scenario types the original hardening request
asked for are **not yet reproducible** because the underlying feature
does not exist yet in the live/wired application:

- A smaller solar system outperforming a larger one (requires
  `scenario_v2`'s multi-size comparison, not yet wired).
- Efficiency-only outperforming solar (no dedicated efficiency-vs-solar
  comparison exists yet).
- Solar-without-battery outperforming solar-with-battery (battery
  dispatch exists at the model layer — `model/battery_dispatch.py` — but
  is not yet wired into a comparable scenario output).
- A generator being cheaper than a battery for rare backup use (no
  generator-vs-battery cost comparison is wired yet, though both have
  illustrative reference costs in `assumptions/generators.yaml` and
  `assumptions/batteries.yaml`).
- Regret analysis across scenarios (not yet implemented — see the
  red-team review's deferred table).

Reviewers are encouraged to construct these comparisons manually from the
existing model modules (`model/scenario.py`, `model/scenario_v2.py`,
`model/battery_dispatch.py`) to test whether the underlying math *would*
support the right answer once wired — that is itself a useful form of
review, and any inconsistency found this way should be reported per
[docs/CORRECTIONS.md](../docs/CORRECTIONS.md).
