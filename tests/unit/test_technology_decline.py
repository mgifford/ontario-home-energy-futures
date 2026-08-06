from pathlib import Path

import pytest

from ontario_home_energy_futures.model.technology_decline import (
    load_technology_components,
    project_component_cost,
    project_quote_by_component,
)

REPO_ROOT = Path(__file__).parent.parent.parent
COMPONENTS_FILE = REPO_ROOT / "assumptions" / "technology_components.yaml"


@pytest.fixture(scope="module")
def components():
    return load_technology_components(COMPONENTS_FILE)


def test_loads_all_twelve_components(components):
    assert len(components) == 12
    assert "complete_installed_solar" in components
    assert "home_battery_hardware" in components
    assert "ontario_installation_labour" in components
    assert "bidirectional_charger" in components


def test_real_and_nominal_remain_distinct(components):
    solar = components["complete_installed_solar"]
    projection = project_component_cost(
        component=solar, base_cost=20000, tier="reference", years=5, general_inflation=0.02
    )
    assert projection.real_cost != projection.nominal_cost


def test_zero_decline_produces_stable_real_cost(components):
    labour = components["ontario_installation_labour"]  # reference decline = 0%
    projection = project_component_cost(
        component=labour, base_cost=5000, tier="reference", years=10, general_inflation=0.0
    )
    assert projection.real_cost == 5000
    assert projection.nominal_cost == 5000


def test_module_decline_does_not_apply_to_labour(components):
    solar_module_decline = components["solar_modules"].reference_decline_real
    labour_decline = components["ontario_installation_labour"].reference_decline_real
    assert solar_module_decline != labour_decline
    assert solar_module_decline > labour_decline  # modules decline faster


def test_battery_decline_only_affects_future_purchase_not_owned_battery():
    # A battery already purchased (years=0) has no future decline applied -
    # confirmed by years=0 always returning the base cost unchanged.
    components = load_technology_components(COMPONENTS_FILE)
    battery = components["home_battery_hardware"]
    projection = project_component_cost(component=battery, base_cost=12000, tier="reference", years=0)
    assert projection.real_cost == 12000


def test_future_battery_decline_reduces_replacement_cost(components):
    battery = components["home_battery_hardware"]
    now = project_component_cost(component=battery, base_cost=12000, tier="reference", years=0)
    later = project_component_cost(component=battery, base_cost=12000, tier="reference", years=8)
    assert later.real_cost < now.real_cost


def test_faster_tier_declines_more_than_low_tier(components):
    solar = components["complete_installed_solar"]
    low = project_component_cost(component=solar, base_cost=20000, tier="low", years=10)
    faster = project_component_cost(component=solar, base_cost=20000, tier="faster", years=10)
    assert faster.real_cost < low.real_cost


def test_unknown_tier_rejected(components):
    solar = components["complete_installed_solar"]
    with pytest.raises(ValueError):
        project_component_cost(component=solar, base_cost=20000, tier="extreme", years=5)


def test_project_quote_by_component_handles_non_technology_line_items(components):
    quote = {
        "complete_installed_solar": 18000,
        "taxes": 2340,  # not a technology component - should pass through
    }
    result = project_quote_by_component(
        components=components, base_costs_by_component=quote, tier="reference", years=5
    )
    assert result["taxes"].real_cost == 2340
    assert result["complete_installed_solar"].real_cost < 18000
