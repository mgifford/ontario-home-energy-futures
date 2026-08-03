"""Standardized monthly Ontario electricity bill reconstruction.

Implements ``B_t = E_t + G_t + T_t + D_t + R_t + X_t - S_t`` (see
METHODOLOGY.md section 1). For Ontario residential bills, G_t and T_t are
folded into the energy/commodity charge as they appear on an actual bill, but
kept as named zero components here so the schema stays forward-compatible
with jurisdictions or policy changes that itemize them separately.
"""

from __future__ import annotations

from dataclasses import dataclass

MONTH_DAYS = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
}

TOU_PERIOD_NAMES = ("off_peak", "mid_peak", "on_peak")


@dataclass(frozen=True)
class RateStructure:
    """A distributor's rate structure, as loaded from
    ``assumptions/utilities/<slug>.yaml``.
    """

    fixed_delivery_charge_cad_per_day: float
    variable_delivery_charge_cad_per_kwh: float
    regulatory_charge_cad_per_kwh: float
    rebate_cad_per_kwh: float
    hst_rate: float
    tou_rates_cad_per_kwh: dict[str, float]
    tiered_threshold_kwh: float
    tiered_threshold_kwh_winter: float
    tiered_winter_months: tuple[int, ...]
    tiered_rate_below_cad_per_kwh: float
    tiered_rate_above_cad_per_kwh: float


@dataclass(frozen=True)
class BillBreakdown:
    """One standardized monthly bill, broken into its component charges."""

    period: str  # "YYYY-MM"
    consumption_kwh: float
    electricity_energy_charge_cad: float
    fixed_delivery_charge_cad: float
    variable_delivery_charge_cad: float
    regulatory_charge_cad: float
    rebate_cad: float
    tax_cad: float
    total_cad: float
    effective_cents_per_kwh: float

    @property
    def non_electricity_charges_cad(self) -> float:
        return self.fixed_delivery_charge_cad + self.variable_delivery_charge_cad + self.regulatory_charge_cad


def _pre_tax_subtotal(
    energy_charge: float,
    fixed_delivery: float,
    variable_delivery: float,
    regulatory: float,
    rebate: float,
) -> float:
    return energy_charge + fixed_delivery + variable_delivery + regulatory + rebate


def calculate_tou_bill(
    *, period: str, consumption_kwh: float, hourly_shares: dict[str, float], rates: RateStructure
) -> BillBreakdown:
    """Reconstruct a time-of-use bill.

    ``hourly_shares`` maps each TOU period name to the fraction (0-1) of
    monthly consumption occurring in that period; the three fractions must
    sum to (approximately) 1.0.
    """
    total_share = sum(hourly_shares.get(name, 0.0) for name in TOU_PERIOD_NAMES)
    if not (0.99 <= total_share <= 1.01):
        raise ValueError(
            f"TOU hourly_shares must sum to ~1.0, got {total_share} for {hourly_shares}"
        )

    energy_charge = sum(
        consumption_kwh * hourly_shares.get(name, 0.0) * rates.tou_rates_cad_per_kwh[name]
        for name in TOU_PERIOD_NAMES
    )
    return _finish_bill(
        period=period,
        consumption_kwh=consumption_kwh,
        energy_charge=energy_charge,
        rates=rates,
    )


def calculate_tiered_bill(
    *, period: str, consumption_kwh: float, month: int, rates: RateStructure
) -> BillBreakdown:
    """Reconstruct a tiered bill for the given calendar month (1-12), which
    determines whether the summer or winter tier threshold applies.
    """
    threshold = (
        rates.tiered_threshold_kwh_winter
        if month in rates.tiered_winter_months
        else rates.tiered_threshold_kwh
    )
    below = min(consumption_kwh, threshold)
    above = max(0.0, consumption_kwh - threshold)
    energy_charge = (
        below * rates.tiered_rate_below_cad_per_kwh + above * rates.tiered_rate_above_cad_per_kwh
    )
    return _finish_bill(
        period=period,
        consumption_kwh=consumption_kwh,
        energy_charge=energy_charge,
        rates=rates,
    )


def _finish_bill(*, period: str, consumption_kwh: float, energy_charge: float, rates: RateStructure) -> BillBreakdown:
    year, month = (int(p) for p in period.split("-"))
    days_in_month = MONTH_DAYS[month]

    fixed_delivery = rates.fixed_delivery_charge_cad_per_day * days_in_month
    variable_delivery = consumption_kwh * rates.variable_delivery_charge_cad_per_kwh
    regulatory = consumption_kwh * rates.regulatory_charge_cad_per_kwh
    rebate = consumption_kwh * rates.rebate_cad_per_kwh  # negative value reduces the bill

    pre_tax = _pre_tax_subtotal(energy_charge, fixed_delivery, variable_delivery, regulatory, rebate)
    tax = pre_tax * rates.hst_rate
    total = pre_tax + tax

    effective_cents_per_kwh = (total / consumption_kwh * 100.0) if consumption_kwh else 0.0

    return BillBreakdown(
        period=period,
        consumption_kwh=consumption_kwh,
        electricity_energy_charge_cad=round(energy_charge, 4),
        fixed_delivery_charge_cad=round(fixed_delivery, 4),
        variable_delivery_charge_cad=round(variable_delivery, 4),
        regulatory_charge_cad=round(regulatory, 4),
        rebate_cad=round(rebate, 4),
        tax_cad=round(tax, 4),
        total_cad=round(total, 4),
        effective_cents_per_kwh=round(effective_cents_per_kwh, 4),
    )


def rate_structure_from_dict(data: dict) -> RateStructure:
    """Build a ``RateStructure`` from a parsed
    ``assumptions/utilities/<slug>.yaml`` dict.
    """
    tou = data["rate_plans"]["time_of_use"]["periods"]
    tiered = data["rate_plans"]["tiered"]
    return RateStructure(
        fixed_delivery_charge_cad_per_day=float(data["fixed_delivery_charge_cad_per_day"]),
        variable_delivery_charge_cad_per_kwh=float(data["variable_delivery_charge_cad_per_kwh"]),
        regulatory_charge_cad_per_kwh=float(data["regulatory_charge_cad_per_kwh"]),
        rebate_cad_per_kwh=float(data["rebate_cad_per_kwh"]),
        hst_rate=0.13,
        tou_rates_cad_per_kwh={p["name"]: float(p["rate_cad_per_kwh"]) for p in tou},
        tiered_threshold_kwh=float(tiered["threshold_kwh_per_month"]),
        tiered_threshold_kwh_winter=float(tiered["threshold_kwh_per_month_winter"]),
        tiered_winter_months=tuple(int(m) for m in tiered["winter_months"]),
        tiered_rate_below_cad_per_kwh=float(tiered["rate_below_threshold_cad_per_kwh"]),
        tiered_rate_above_cad_per_kwh=float(tiered["rate_above_threshold_cad_per_kwh"]),
    )


DEFAULT_TOU_HOURLY_SHARES = {
    "off_peak": 0.60,
    "mid_peak": 0.20,
    "on_peak": 0.20,
}
