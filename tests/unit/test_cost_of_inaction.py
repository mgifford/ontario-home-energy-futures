import pytest

from ontario_home_energy_futures.model.cost_of_inaction import (
    DecisionCostInputs,
    calculate_cost_of_inaction,
    cost_of_inaction_excludes_unavailable_future_revenue,
)


def _decision(label, pv, nominal=None, grid_kwh=2000, solar_kwh=9000, incentives=0, revenue=0, residual=1000):
    return DecisionCostInputs(
        label=label,
        total_nominal_cad=nominal if nominal is not None else pv,
        total_present_value_cad=pv,
        grid_imports_kwh=grid_kwh,
        solar_generation_kwh=solar_kwh,
        incentives_received_cad=incentives,
        grid_service_revenue_cad=revenue,
        residual_value_cad=residual,
    )


def test_best_decision_has_zero_cost_of_inaction():
    decisions = [_decision("Buy now", pv=18000), _decision("Wait 3 years", pv=19500)]
    results = calculate_cost_of_inaction(decisions)
    assert results["Buy now"].additional_present_value_cad == 0


def test_worse_decision_shows_positive_additional_cost():
    decisions = [_decision("Buy now", pv=18000), _decision("Wait 3 years", pv=19500)]
    results = calculate_cost_of_inaction(decisions)
    assert results["Wait 3 years"].additional_present_value_cad == pytest.approx(1500)


def test_does_not_assume_buy_now_is_always_best():
    # If waiting is genuinely cheaper under the selected assumptions, "buy
    # now" must show a nonzero cost of inaction, not be hardcoded as best.
    decisions = [_decision("Buy now", pv=22000), _decision("Wait 3 years", pv=19000)]
    results = calculate_cost_of_inaction(decisions)
    assert results["Wait 3 years"].additional_present_value_cad == 0
    assert results["Buy now"].additional_present_value_cad == pytest.approx(3000)


def test_no_action_can_be_worst_without_special_casing():
    decisions = [
        _decision("Buy now", pv=18000, grid_kwh=500, solar_kwh=9000),
        _decision("No action", pv=25000, grid_kwh=2000, solar_kwh=0, residual=0),
    ]
    results = calculate_cost_of_inaction(decisions)
    no_action = results["No action"]
    assert no_action.additional_present_value_cad == pytest.approx(7000)
    assert no_action.solar_generation_forgone_kwh == pytest.approx(9000)
    assert no_action.grid_electricity_purchased_while_waiting_kwh == pytest.approx(1500)


def test_incentives_and_revenue_forgone_reported():
    decisions = [
        _decision("Buy now", pv=18000, incentives=500, revenue=200),
        _decision("Wait 3 years", pv=19000, incentives=0, revenue=0),
    ]
    results = calculate_cost_of_inaction(decisions)
    wait = results["Wait 3 years"]
    assert wait.current_incentives_forgone_cad == pytest.approx(500)
    assert wait.currently_available_revenue_forgone_cad == pytest.approx(200)


def test_residual_value_difference_can_be_negative():
    decisions = [
        _decision("Buy now", pv=18000, residual=3000),
        _decision("Wait 3 years", pv=19000, residual=1000),
    ]
    results = calculate_cost_of_inaction(decisions)
    assert results["Wait 3 years"].residual_value_difference_cad == pytest.approx(-2000)


def test_emissions_note_present_but_not_monetized():
    decisions = [_decision("Buy now", pv=18000), _decision("Wait 3 years", pv=19000)]
    results = calculate_cost_of_inaction(decisions)
    note = results["Wait 3 years"].emissions_consequence_note
    assert "emissions" in note.lower()
    assert "$" not in note  # never assigns a default dollar value


def test_empty_decisions_returns_empty_dict():
    assert calculate_cost_of_inaction([]) == {}


def test_future_revenue_excluded_when_programme_not_yet_available():
    # Buying in year 0, programme starts year 5 - not available during the
    # relevant early years for this decision.
    assert cost_of_inaction_excludes_unavailable_future_revenue(
        decision_purchase_year_offset=0, revenue_start_year_offset=5
    ) is True


def test_future_revenue_included_when_programme_already_available():
    assert cost_of_inaction_excludes_unavailable_future_revenue(
        decision_purchase_year_offset=6, revenue_start_year_offset=5
    ) is False


def test_future_revenue_excluded_when_no_start_year_recorded():
    assert cost_of_inaction_excludes_unavailable_future_revenue(
        decision_purchase_year_offset=10, revenue_start_year_offset=None
    ) is True
