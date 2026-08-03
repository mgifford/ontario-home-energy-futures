import pytest

from ontario_home_energy_futures.model.bill import (
    DEFAULT_TOU_HOURLY_SHARES,
    RateStructure,
    calculate_tiered_bill,
    calculate_tou_bill,
)

RATES = RateStructure(
    fixed_delivery_charge_cad_per_day=0.4795,
    variable_delivery_charge_cad_per_kwh=0.0223,
    regulatory_charge_cad_per_kwh=0.0059,
    rebate_cad_per_kwh=-0.0227,
    hst_rate=0.13,
    tou_rates_cad_per_kwh={"off_peak": 0.076, "mid_peak": 0.122, "on_peak": 0.158},
    tiered_threshold_kwh=600,
    tiered_threshold_kwh_winter=1000,
    tiered_winter_months=(11, 12, 1, 2, 3, 4),
    tiered_rate_below_cad_per_kwh=0.087,
    tiered_rate_above_cad_per_kwh=0.104,
)


def test_tou_bill_has_all_components():
    bill = calculate_tou_bill(
        period="2026-07", consumption_kwh=700, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=RATES
    )
    assert bill.electricity_energy_charge_cad > 0
    assert bill.fixed_delivery_charge_cad > 0
    assert bill.variable_delivery_charge_cad > 0
    assert bill.regulatory_charge_cad > 0
    assert bill.rebate_cad < 0
    assert bill.tax_cad > 0
    assert bill.total_cad > 0


def test_fixed_delivery_charge_present_even_at_zero_consumption():
    bill = calculate_tou_bill(
        period="2026-07", consumption_kwh=0, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=RATES
    )
    assert bill.fixed_delivery_charge_cad > 0
    assert bill.electricity_energy_charge_cad == 0
    assert bill.effective_cents_per_kwh == 0


def test_tou_shares_must_sum_to_one():
    with pytest.raises(ValueError):
        calculate_tou_bill(
            period="2026-07",
            consumption_kwh=700,
            hourly_shares={"off_peak": 0.5, "mid_peak": 0.1, "on_peak": 0.1},
            rates=RATES,
        )


def test_tiered_bill_below_threshold():
    bill = calculate_tiered_bill(period="2026-07", consumption_kwh=500, month=7, rates=RATES)
    expected_energy = 500 * RATES.tiered_rate_below_cad_per_kwh
    assert bill.electricity_energy_charge_cad == pytest.approx(expected_energy, abs=0.01)


def test_tiered_bill_above_threshold_summer():
    bill = calculate_tiered_bill(period="2026-07", consumption_kwh=800, month=7, rates=RATES)
    expected_energy = (
        RATES.tiered_threshold_kwh * RATES.tiered_rate_below_cad_per_kwh
        + (800 - RATES.tiered_threshold_kwh) * RATES.tiered_rate_above_cad_per_kwh
    )
    assert bill.electricity_energy_charge_cad == pytest.approx(expected_energy, abs=0.01)


def test_tiered_bill_uses_winter_threshold_in_january():
    bill = calculate_tiered_bill(period="2026-01", consumption_kwh=800, month=1, rates=RATES)
    # 800 kWh is below the winter threshold of 1000, so all at the lower rate.
    expected_energy = 800 * RATES.tiered_rate_below_cad_per_kwh
    assert bill.electricity_energy_charge_cad == pytest.approx(expected_energy, abs=0.01)


def test_higher_consumption_increases_total():
    low = calculate_tou_bill(period="2026-07", consumption_kwh=500, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=RATES)
    high = calculate_tou_bill(period="2026-07", consumption_kwh=1500, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=RATES)
    assert high.total_cad > low.total_cad


def test_days_in_month_affects_fixed_charge():
    feb = calculate_tou_bill(period="2026-02", consumption_kwh=700, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=RATES)
    mar = calculate_tou_bill(period="2026-03", consumption_kwh=700, hourly_shares=DEFAULT_TOU_HOURLY_SHARES, rates=RATES)
    assert mar.fixed_delivery_charge_cad > feb.fixed_delivery_charge_cad
