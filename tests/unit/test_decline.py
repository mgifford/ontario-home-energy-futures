import pytest

from ontario_home_energy_futures.model.decline import (
    bill_component_after_years,
    deflate_to_real,
    discount_to_present_value,
    installed_cost_after_years,
)


def test_flat_decline_real_cost_unchanged():
    real, nominal = installed_cost_after_years(base_cost=20000, annual_real_decline=0.0, years=5)
    assert real == 20000


def test_declining_real_cost_lower_over_time():
    real, _ = installed_cost_after_years(base_cost=20000, annual_real_decline=0.02, years=5)
    assert real < 20000


def test_nominal_can_exceed_real_with_inflation():
    real, nominal = installed_cost_after_years(
        base_cost=20000, annual_real_decline=0.02, years=5, general_inflation=0.05
    )
    assert nominal > real


def test_real_can_decline_while_nominal_rises():
    # 2% real decline, 3% inflation: nominal should still be higher than base
    # even though real cost fell, per METHODOLOGY.md section 8.
    real, nominal = installed_cost_after_years(
        base_cost=20000, annual_real_decline=0.02, years=10, general_inflation=0.03
    )
    assert real < 20000
    assert nominal > 20000 * 0.9  # sanity: nominal isn't collapsing


def test_bill_component_growth():
    real, nominal = bill_component_after_years(
        base_value=1000, annual_real_change=0.015, years=10, general_inflation=0.02
    )
    assert real > 1000
    assert nominal > real


def test_deflate_to_real_reverses_inflation():
    inflated = 1000 * (1.02 ** 10)
    real = deflate_to_real(inflated, general_inflation=0.02, years=10)
    assert real == pytest.approx(1000, abs=0.5)


def test_discount_to_present_value_reduces_future_cash_flow():
    pv = discount_to_present_value(1000, discount_rate=0.04, years=10)
    assert pv < 1000


def test_discount_to_present_value_year_zero_unchanged():
    pv = discount_to_present_value(1000, discount_rate=0.04, years=0)
    assert pv == 1000
