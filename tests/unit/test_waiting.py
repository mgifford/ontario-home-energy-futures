import pytest

from ontario_home_energy_futures.model.waiting import find_breakeven_decline_rate, format_breakeven_statement


def test_breakeven_found_when_waiting_can_win():
    # Cost decreases linearly with rate; buy_now cost is between low and high.
    def npv_cost(rate: float) -> float:
        return 20000 - rate * 100000

    result = find_breakeven_decline_rate(npv_cost_for_decline_rate=npv_cost, npv_cost_buy_now=18000)
    assert result is not None
    assert 0.0 < result < 0.30
    assert npv_cost(result) == pytest.approx(18000, rel=0.01)


def test_breakeven_none_when_waiting_never_wins():
    def npv_cost(rate: float) -> float:
        return 30000 - rate * 1000  # even at high=0.30, cost stays above buy_now

    result = find_breakeven_decline_rate(npv_cost_for_decline_rate=npv_cost, npv_cost_buy_now=18000)
    assert result is None


def test_breakeven_zero_when_waiting_already_wins():
    def npv_cost(rate: float) -> float:
        return 10000 - rate * 1000

    result = find_breakeven_decline_rate(npv_cost_for_decline_rate=npv_cost, npv_cost_buy_now=18000)
    assert result == 0.0


def test_format_breakeven_statement_with_rate():
    text = format_breakeven_statement(
        breakeven_rate=0.053, wait_years=3, wait_until_year=2029, buy_now_year=2026
    )
    assert "5.3%" in text
    assert "2029" in text
    assert "2026" in text
    assert "at least" in text


def test_format_breakeven_statement_none():
    text = format_breakeven_statement(
        breakeven_rate=None, wait_years=3, wait_until_year=2029, buy_now_year=2026
    )
    assert "no plausible" in text
