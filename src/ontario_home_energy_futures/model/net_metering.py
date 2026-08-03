"""Ontario net-metering credit ledger.

See METHODOLOGY.md section 5. Exported solar generation becomes a non-cash
generation credit, tracked as dated tranches that expire 12 months after
creation if unused. Credits apply only against the eligible
electricity-energy charge on imported electricity — never against fixed
delivery, ineligible variable delivery, regulatory charges, or tax.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CREDIT_EXPIRY_MONTHS = 12


@dataclass
class CreditTranche:
    created_period: str  # "YYYY-MM"
    amount_cad: float


@dataclass
class MonthResult:
    period: str
    solar_generation_kwh: float
    direct_self_consumption_kwh: float
    exported_kwh: float
    grid_import_kwh: float
    eligible_charge_before_credits_cad: float
    credit_opening_balance_cad: float
    credit_created_cad: float
    credit_used_cad: float
    credit_expired_cad: float
    credit_closing_balance_cad: float
    eligible_charge_after_credits_cad: float
    ineligible_charges_cad: float


def _period_add_months(period: str, months: int) -> str:
    year, month = (int(p) for p in period.split("-"))
    total = (year * 12 + (month - 1)) + months
    new_year, new_month = divmod(total, 12)
    return f"{new_year:04d}-{new_month + 1:02d}"


class NetMeteringLedger:
    """Tracks generation credit tranches across a sequence of months,
    applying FIFO consumption and 12-month vintage expiry.
    """

    def __init__(self, *, export_credit_rate_cad_per_kwh: float) -> None:
        self._export_credit_rate = export_credit_rate_cad_per_kwh
        self._tranches: list[CreditTranche] = []
        self.total_generation_kwh = 0.0
        self.total_direct_self_consumption_kwh = 0.0
        self.total_exported_kwh = 0.0
        self.total_grid_import_kwh = 0.0
        self.total_credit_created_cad = 0.0
        self.total_credit_used_cad = 0.0
        self.total_credit_expired_cad = 0.0

    def _expire_tranches(self, current_period: str) -> float:
        expired = 0.0
        remaining: list[CreditTranche] = []
        for tranche in self._tranches:
            expiry_period = _period_add_months(tranche.created_period, CREDIT_EXPIRY_MONTHS)
            if expiry_period <= current_period:
                expired += tranche.amount_cad
            else:
                remaining.append(tranche)
        self._tranches = remaining
        return expired

    def _balance(self) -> float:
        return sum(t.amount_cad for t in self._tranches)

    def _consume(self, amount_needed: float) -> float:
        """Consume up to ``amount_needed`` dollars of credit, oldest first.
        Returns the amount actually consumed.
        """
        consumed = 0.0
        remaining: list[CreditTranche] = []
        for tranche in self._tranches:
            if consumed >= amount_needed:
                remaining.append(tranche)
                continue
            take = min(tranche.amount_cad, amount_needed - consumed)
            consumed += take
            leftover = tranche.amount_cad - take
            if leftover > 1e-9:
                remaining.append(CreditTranche(tranche.created_period, leftover))
        self._tranches = remaining
        return consumed

    def process_month(
        self,
        *,
        period: str,
        solar_generation_kwh: float,
        household_demand_kwh: float,
        direct_self_consumption_kwh: float,
        eligible_energy_rate_cad_per_kwh: float,
        ineligible_charges_cad: float,
    ) -> MonthResult:
        """Process one calendar month through the ledger, in period order.

        ``direct_self_consumption_kwh`` should come from
        ``solar.estimate_direct_self_consumption_kwh``.
        """
        exported_kwh = max(0.0, solar_generation_kwh - direct_self_consumption_kwh)
        grid_import_kwh = max(0.0, household_demand_kwh - direct_self_consumption_kwh)

        opening_balance = self._balance()
        expired_this_month = self._expire_tranches(period)

        eligible_charge_before = grid_import_kwh * eligible_energy_rate_cad_per_kwh

        new_credit = exported_kwh * self._export_credit_rate
        if new_credit > 0:
            self._tranches.append(CreditTranche(period, new_credit))

        used = self._consume(eligible_charge_before)
        eligible_charge_after = eligible_charge_before - used

        closing_balance = self._balance()

        self.total_generation_kwh += solar_generation_kwh
        self.total_direct_self_consumption_kwh += direct_self_consumption_kwh
        self.total_exported_kwh += exported_kwh
        self.total_grid_import_kwh += grid_import_kwh
        self.total_credit_created_cad += new_credit
        self.total_credit_used_cad += used
        self.total_credit_expired_cad += expired_this_month

        return MonthResult(
            period=period,
            solar_generation_kwh=round(solar_generation_kwh, 4),
            direct_self_consumption_kwh=round(direct_self_consumption_kwh, 4),
            exported_kwh=round(exported_kwh, 4),
            grid_import_kwh=round(grid_import_kwh, 4),
            eligible_charge_before_credits_cad=round(eligible_charge_before, 4),
            credit_opening_balance_cad=round(opening_balance, 4),
            credit_created_cad=round(new_credit, 4),
            credit_used_cad=round(used, 4),
            credit_expired_cad=round(expired_this_month, 4),
            credit_closing_balance_cad=round(closing_balance, 4),
            eligible_charge_after_credits_cad=round(eligible_charge_after, 4),
            ineligible_charges_cad=round(ineligible_charges_cad, 4),
        )

    def effective_value_per_generated_kwh(self) -> float:
        """Realized financial value per generated kWh: money actually saved
        (credits used, valued at generation) divided by total generation.
        Lower than the full retail rate once exports, expiry, and
        ineligible-charge exclusions are accounted for (METHODOLOGY.md
        section 5).
        """
        if self.total_generation_kwh <= 0:
            return 0.0
        return round(self.total_credit_used_cad / self.total_generation_kwh, 6)
