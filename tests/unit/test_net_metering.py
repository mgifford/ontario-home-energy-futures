import pytest

from ontario_home_energy_futures.model.net_metering import NetMeteringLedger


def _period_seq(start_year: int, start_month: int, n: int) -> list[str]:
    periods = []
    y, m = start_year, start_month
    for _ in range(n):
        periods.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return periods


def test_no_solar_no_exports_no_credits():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    result = ledger.process_month(
        period="2026-01",
        solar_generation_kwh=0,
        household_demand_kwh=700,
        direct_self_consumption_kwh=0,
        eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    assert result.exported_kwh == 0
    assert result.credit_created_cad == 0
    assert result.grid_import_kwh == 700


def test_production_equals_consumption_no_export_no_import():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    result = ledger.process_month(
        period="2026-06",
        solar_generation_kwh=500,
        household_demand_kwh=500,
        direct_self_consumption_kwh=500,
        eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    assert result.exported_kwh == 0
    assert result.grid_import_kwh == 0


def test_export_creates_credit():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    result = ledger.process_month(
        period="2026-06",
        solar_generation_kwh=800,
        household_demand_kwh=300,
        direct_self_consumption_kwh=200,
        eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    assert result.exported_kwh == pytest.approx(600)
    assert result.credit_created_cad == pytest.approx(600 * 0.08)


def test_credit_used_against_next_month_import():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    # June: big export, big credit.
    ledger.process_month(
        period="2026-06", solar_generation_kwh=1000, household_demand_kwh=300,
        direct_self_consumption_kwh=250, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    # July: no solar, needs grid import, credit should offset the eligible charge.
    result = ledger.process_month(
        period="2026-07", solar_generation_kwh=0, household_demand_kwh=700,
        direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    assert result.credit_used_cad > 0
    assert result.eligible_charge_after_credits_cad < result.eligible_charge_before_credits_cad


def test_credit_never_offsets_ineligible_charges():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    ledger.process_month(
        period="2026-06", solar_generation_kwh=1000, household_demand_kwh=100,
        direct_self_consumption_kwh=100, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    result = ledger.process_month(
        period="2026-07", solar_generation_kwh=0, household_demand_kwh=100,
        direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=50,
    )
    # Ineligible charges pass through unchanged regardless of credit balance.
    assert result.ineligible_charges_cad == 50


def test_credit_expires_after_12_months():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    ledger.process_month(
        period="2026-01", solar_generation_kwh=1000, household_demand_kwh=50,
        direct_self_consumption_kwh=50, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=10,
    )
    balance_before_expiry = ledger._balance()
    assert balance_before_expiry > 0

    # Advance 11 more months with no further generation/import to consume credit.
    for period in _period_seq(2026, 2, 10):
        ledger.process_month(
            period=period, solar_generation_kwh=0, household_demand_kwh=0,
            direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
            ineligible_charges_cad=0,
        )
    # Still within 12 months (created 2026-01, now 2026-12 = 11 months later).
    assert ledger._balance() > 0

    # 2027-01 is exactly 12 months after 2026-01: tranche should expire.
    result = ledger.process_month(
        period="2027-01", solar_generation_kwh=0, household_demand_kwh=0,
        direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=0,
    )
    assert result.credit_expired_cad > 0
    assert ledger._balance() == 0


def test_multiple_credit_vintages_fifo():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    ledger.process_month(
        period="2026-01", solar_generation_kwh=200, household_demand_kwh=50,
        direct_self_consumption_kwh=50, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=0,
    )
    ledger.process_month(
        period="2026-02", solar_generation_kwh=200, household_demand_kwh=50,
        direct_self_consumption_kwh=50, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=0,
    )
    assert len(ledger._tranches) == 2
    assert ledger._tranches[0].created_period == "2026-01"


def test_oversized_system_produces_expired_credits():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    # Low household consumption, huge system: most production exported.
    for month in range(1, 13):
        period = f"2026-{month:02d}"
        ledger.process_month(
            period=period, solar_generation_kwh=1500, household_demand_kwh=200,
            direct_self_consumption_kwh=150, eligible_energy_rate_cad_per_kwh=0.08,
            ineligible_charges_cad=20,
        )
    # Continue past 12 months without enough consumption to use it all.
    for period in _period_seq(2027, 1, 6):
        ledger.process_month(
            period=period, solar_generation_kwh=1500, household_demand_kwh=200,
            direct_self_consumption_kwh=150, eligible_energy_rate_cad_per_kwh=0.08,
            ineligible_charges_cad=20,
        )
    assert ledger.total_credit_expired_cad > 0
    # Effective value per generated kWh should be well below the retail rate
    # because so much production goes unused/expired.
    assert ledger.effective_value_per_generated_kwh() < 0.08


def test_cross_year_expiry_boundary():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    ledger.process_month(
        period="2025-12", solar_generation_kwh=500, household_demand_kwh=50,
        direct_self_consumption_kwh=50, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=0,
    )
    for period in _period_seq(2026, 1, 11):
        ledger.process_month(
            period=period, solar_generation_kwh=0, household_demand_kwh=0,
            direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
            ineligible_charges_cad=0,
        )
    assert ledger._balance() > 0  # 2026-11 is 11 months after 2025-12
    result = ledger.process_month(
        period="2026-12", solar_generation_kwh=0, household_demand_kwh=0,
        direct_self_consumption_kwh=0, eligible_energy_rate_cad_per_kwh=0.08,
        ineligible_charges_cad=0,
    )
    assert result.credit_expired_cad > 0


def test_effective_value_per_kwh_zero_when_no_generation():
    ledger = NetMeteringLedger(export_credit_rate_cad_per_kwh=0.08)
    assert ledger.effective_value_per_generated_kwh() == 0.0
