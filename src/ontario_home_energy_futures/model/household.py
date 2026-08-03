"""Household consumption model.

Implements ``D_m = B_m + EV_m + HP_m + WH_m + AC_m + O_m - EE_m`` (see
METHODOLOGY.md section 2). EV/heat-pump/water-heater/cooling additions are
computed as documented annual kWh totals spread across months using a simple
seasonal shape (not an hourly simulation — see module docstring in
``solar.py`` and METHODOLOGY.md section 3 for the hourly-readiness note).
"""

from __future__ import annotations

from dataclasses import dataclass, field

MONTHS = tuple(range(1, 13))


@dataclass(frozen=True)
class ElectricVehicleInputs:
    annual_km: float
    efficiency_kwh_per_100km: float
    home_charging_share: float

    def annual_kwh(self) -> float:
        return (self.annual_km / 100.0) * self.efficiency_kwh_per_100km * self.home_charging_share


@dataclass(frozen=True)
class HeatPumpInputs:
    annual_heating_kwh_equivalent: float
    seasonal_cop: float

    def annual_kwh(self) -> float:
        if self.seasonal_cop <= 0:
            raise ValueError("seasonal_cop must be positive")
        return self.annual_heating_kwh_equivalent / self.seasonal_cop


@dataclass(frozen=True)
class HouseholdInputs:
    """A household's monthly baseline consumption plus optional additions.

    ``baseline_monthly_kwh`` must have exactly 12 entries keyed 1-12.
    """

    baseline_monthly_kwh: dict[int, float]
    ev: ElectricVehicleInputs | None = None
    heat_pump: HeatPumpInputs | None = None
    water_heater_annual_kwh: float = 0.0
    cooling_annual_kwh: float = 0.0
    other_annual_kwh: float = 0.0
    efficiency_savings_annual_kwh: float = 0.0


def spread_annual_kwh(annual_kwh: float, seasonal_shape: dict[int, float]) -> dict[int, float]:
    """Spread an annual kWh total across 12 months using a documented
    seasonal shape (fractions summing to ~1.0).
    """
    total_share = sum(seasonal_shape.get(m, 0.0) for m in MONTHS)
    if not (0.98 <= total_share <= 1.02):
        raise ValueError(f"seasonal_shape must sum to ~1.0, got {total_share}")
    return {m: annual_kwh * seasonal_shape.get(m, 0.0) for m in MONTHS}


def baseline_from_standard_profile(monthly_kwh: float) -> dict[int, float]:
    """A "quick estimate" standard profile: the same kWh every month."""
    return {m: float(monthly_kwh) for m in MONTHS}


def baseline_from_annual(annual_kwh: float, seasonal_shape: dict[int, float]) -> dict[int, float]:
    """An "annual estimate" spread across months with the documented
    seasonal shape.
    """
    return spread_annual_kwh(annual_kwh, seasonal_shape)


def calculate_monthly_demand(
    inputs: HouseholdInputs, *, seasonal_shape: dict[int, float]
) -> dict[int, float]:
    """Return total household demand per month (1-12) in kWh, per
    ``D_m = B_m + EV_m + HP_m + WH_m + AC_m + O_m - EE_m``.
    """
    if set(inputs.baseline_monthly_kwh) != set(MONTHS):
        raise ValueError("baseline_monthly_kwh must have exactly keys 1-12")

    ev_monthly = (
        spread_annual_kwh(inputs.ev.annual_kwh(), seasonal_shape) if inputs.ev else {m: 0.0 for m in MONTHS}
    )
    hp_monthly = (
        spread_annual_kwh(inputs.heat_pump.annual_kwh(), seasonal_shape)
        if inputs.heat_pump
        else {m: 0.0 for m in MONTHS}
    )
    wh_monthly = spread_annual_kwh(inputs.water_heater_annual_kwh, seasonal_shape)
    ac_monthly = spread_annual_kwh(inputs.cooling_annual_kwh, seasonal_shape)
    other_monthly = spread_annual_kwh(inputs.other_annual_kwh, seasonal_shape)
    ee_monthly = spread_annual_kwh(inputs.efficiency_savings_annual_kwh, seasonal_shape)

    return {
        m: (
            inputs.baseline_monthly_kwh[m]
            + ev_monthly[m]
            + hp_monthly[m]
            + wh_monthly[m]
            + ac_monthly[m]
            + other_monthly[m]
            - ee_monthly[m]
        )
        for m in MONTHS
    }
