import pytest

from ontario_home_energy_futures.model.horizon import FixedHorizon, assert_same_horizon


def test_end_year_computed_correctly():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert horizon.end_year == 2046


def test_calendar_years_covers_full_range():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    years = horizon.calendar_years
    assert years[0] == 2026
    assert years[-1] == 2045
    assert len(years) == 20


def test_buy_now_gets_full_horizon_active_years():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert horizon.years_active_for_purchase(0) == 20


def test_wait_three_years_gets_fewer_active_years_not_extended_window():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    # This is the core fairness fix: waiting 3 years within a fixed 20-year
    # window leaves only 17 years of solar-active service, NOT a fresh
    # 20-year window starting in 2029.
    assert horizon.years_active_for_purchase(3) == 17


def test_wait_ten_years_gets_ten_active_years():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert horizon.years_active_for_purchase(10) == 10


def test_purchase_at_horizon_end_gets_zero_active_years():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert horizon.years_active_for_purchase(20) == 0
    assert horizon.years_active_for_purchase(25) == 0


def test_negative_purchase_offset_rejected():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    with pytest.raises(ValueError):
        horizon.years_active_for_purchase(-1)


def test_buy_now_and_wait_ten_years_share_same_calendar_end():
    # The exact fairness assertion required by the project brief: every
    # purchase-year decision must use the same calendar end date.
    buy_now_horizon = FixedHorizon(base_year=2026, horizon_years=20)
    wait_ten_horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert buy_now_horizon.end_year == wait_ten_horizon.end_year == 2046
    assert_same_horizon(buy_now_horizon, wait_ten_horizon)  # should not raise


def test_assert_same_horizon_rejects_mismatched_horizons():
    a = FixedHorizon(base_year=2026, horizon_years=20)
    b = FixedHorizon(base_year=2029, horizon_years=20)  # would end 2049, not 2046
    with pytest.raises(ValueError):
        assert_same_horizon(a, b)


def test_calendar_year_for_offset():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert horizon.calendar_year_for_offset(0) == 2026
    assert horizon.calendar_year_for_offset(3) == 2029
    assert horizon.calendar_year_for_offset(19) == 2045


def test_is_purchase_within_horizon():
    horizon = FixedHorizon(base_year=2026, horizon_years=20)
    assert horizon.is_purchase_within_horizon(0) is True
    assert horizon.is_purchase_within_horizon(19) is True
    assert horizon.is_purchase_within_horizon(20) is False


def test_year_offsets_length_matches_horizon():
    horizon = FixedHorizon(base_year=2026, horizon_years=10)
    assert horizon.year_offsets() == list(range(10))
