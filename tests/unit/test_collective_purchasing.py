from pathlib import Path

import pytest

from ontario_home_energy_futures.model.collective_purchasing import (
    apply_collective_purchase,
    load_collective_tiers,
)

REPO_ROOT = Path(__file__).parent.parent.parent
TIERS_FILE = REPO_ROOT / "assumptions" / "collective_purchasing.yaml"

QUOTE = {
    "hardware": 8000,
    "labour": 4200,
    "customer_acquisition": 1500,
    "design": 630,
    "permitting": 420,
    "taxes": 1800,
    "utility_charges": 300,
}


@pytest.fixture(scope="module")
def tiers():
    return load_collective_tiers(TIERS_FILE)


def test_loads_four_tiers(tiers):
    assert set(tiers) == {"individual", "group_5", "group_10", "group_20"}


def test_individual_tier_has_zero_reduction(tiers):
    result = apply_collective_purchase(tier=tiers["individual"], base_costs_by_component=QUOTE)
    assert result.total_reduction_cad == 0
    assert result.total_reduced_cost == result.total_base_cost


def test_taxes_and_utility_charges_never_discounted(tiers):
    result = apply_collective_purchase(tier=tiers["group_10"], base_costs_by_component=QUOTE)
    taxes_row = next(r for r in result.by_component if r.component_id == "taxes")
    utility_row = next(r for r in result.by_component if r.component_id == "utility_charges")
    assert taxes_row.reduction_cad == 0
    assert utility_row.reduction_cad == 0


def test_five_ten_twenty_household_tiers_use_different_assumptions(tiers):
    r5 = apply_collective_purchase(tier=tiers["group_5"], base_costs_by_component=QUOTE)
    r10 = apply_collective_purchase(tier=tiers["group_10"], base_costs_by_component=QUOTE)
    r20 = apply_collective_purchase(tier=tiers["group_20"], base_costs_by_component=QUOTE)
    assert r5.total_reduction_cad < r10.total_reduction_cad < r20.total_reduction_cad


def test_overall_discount_respects_configured_cap(tiers):
    tier = tiers["group_10"]  # cap = 10%
    result = apply_collective_purchase(tier=tier, base_costs_by_component=QUOTE)
    assert result.effective_discount_percent <= tier.overall_discount_cap_percent + 1e-6


def test_cap_enforcement_scales_proportionally_when_triggered():
    from ontario_home_energy_futures.model.collective_purchasing import CollectiveTier

    aggressive_tier = CollectiveTier(
        id="aggressive", label="Aggressive", households=10,
        reductions={"hardware": 50, "labour": 50},  # would blow past any sane cap
        overall_discount_cap_percent=5,
    )
    quote = {"hardware": 10000, "labour": 10000}
    result = apply_collective_purchase(tier=aggressive_tier, base_costs_by_component=quote)
    assert result.capped is True
    assert result.effective_discount_percent == pytest.approx(5.0, abs=0.01)


def test_no_reduction_applied_when_component_not_in_reductions_map(tiers):
    result = apply_collective_purchase(
        tier=tiers["group_10"], base_costs_by_component={"unlisted_component": 1000}
    )
    assert result.total_reduction_cad == 0


def test_zero_base_cost_handled_without_division_error(tiers):
    result = apply_collective_purchase(tier=tiers["group_10"], base_costs_by_component={})
    assert result.total_base_cost == 0
    assert result.total_reduction_cad == 0
