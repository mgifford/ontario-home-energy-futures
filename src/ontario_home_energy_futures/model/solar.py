"""Monthly solar production model.

Implements ``S_m = K * Y_m * (1 - d)^y`` (see METHODOLOGY.md section 4). The
public interface is monthly; a representative hourly production shape is
also provided so ``net_metering.py`` can estimate direct self-consumption
without a full hourly simulation (see METHODOLOGY.md section 3 for the
explicit "approximation, not equivalent to hourly modelling" label).
"""

from __future__ import annotations

from dataclasses import dataclass

MONTHS = tuple(range(1, 13))

ORIENTATIONS = ("south", "southeast", "southwest", "east", "west", "north")
SHADING_LEVELS = ("none", "light", "moderate", "heavy")


@dataclass(frozen=True)
class SolarSystemInputs:
    capacity_kw_dc: float
    orientation: str
    shading: str
    degradation_annual: float
    inverter_efficiency: float
    other_system_losses: float
    pitch_factor: float = 1.0


def _derate_factor(inputs: SolarSystemInputs, orientation_factors: dict[str, float], shading_factors: dict[str, float]) -> float:
    if inputs.orientation not in orientation_factors:
        raise ValueError(f"unknown orientation {inputs.orientation!r}")
    if inputs.shading not in shading_factors:
        raise ValueError(f"unknown shading level {inputs.shading!r}")
    return (
        orientation_factors[inputs.orientation]
        * shading_factors[inputs.shading]
        * inputs.pitch_factor
        * inputs.inverter_efficiency
        * (1.0 - inputs.other_system_losses)
    )


def calculate_annual_monthly_production_kwh(
    inputs: SolarSystemInputs,
    *,
    regional_monthly_yield_kwh_per_kw: dict[int, float],
    orientation_factors: dict[str, float],
    shading_factors: dict[str, float],
    system_age_years: int,
) -> dict[int, float]:
    """Return solar production per calendar month (1-12) in kWh for a system
    of the given age (0 = newly installed).
    """
    if set(regional_monthly_yield_kwh_per_kw) != set(MONTHS):
        raise ValueError("regional_monthly_yield_kwh_per_kw must have keys 1-12")

    derate = _derate_factor(inputs, orientation_factors, shading_factors)
    degradation_multiplier = (1.0 - inputs.degradation_annual) ** system_age_years

    return {
        m: inputs.capacity_kw_dc * regional_monthly_yield_kwh_per_kw[m] * derate * degradation_multiplier
        for m in MONTHS
    }


def production_over_horizon_kwh(
    inputs: SolarSystemInputs,
    *,
    regional_monthly_yield_kwh_per_kw: dict[int, float],
    orientation_factors: dict[str, float],
    shading_factors: dict[str, float],
    horizon_years: int,
) -> dict[int, dict[int, float]]:
    """Return ``{system_age_year: {month: kwh}}`` for each year 0..horizon-1."""
    return {
        year: calculate_annual_monthly_production_kwh(
            inputs,
            regional_monthly_yield_kwh_per_kw=regional_monthly_yield_kwh_per_kw,
            orientation_factors=orientation_factors,
            shading_factors=shading_factors,
            system_age_years=year,
        )
        for year in range(horizon_years)
    }


def estimate_direct_self_consumption_kwh(
    *,
    monthly_solar_kwh: float,
    monthly_demand_kwh: float,
    hourly_solar_shape: dict[int, float],
    hourly_load_shape: dict[int, float],
) -> float:
    """Estimate direct (same-hour) self-consumption for one month using
    representative hourly shapes scaled to the month's totals.

    This is a documented approximation (METHODOLOGY.md section 3): it
    multiplies each hour's solar output by the household load shape rather
    than simulating 8,760 real hourly intervals, but is structured so a
    validated hourly model can replace it without changing this function's
    interface.
    """
    total = 0.0
    for hour, solar_fraction in hourly_solar_shape.items():
        solar_kwh_this_hour = monthly_solar_kwh * solar_fraction
        load_fraction = hourly_load_shape.get(hour, 0.0)
        # Approximate a single "day" hourly shape applied uniformly across
        # the month's days; both shapes are fractions of a day/of daylight
        # hours respectively, so this proxies same-hour overlap in kWh.
        load_kwh_this_hour = monthly_demand_kwh * load_fraction
        total += min(solar_kwh_this_hour, load_kwh_this_hour)
    return round(total, 4)
