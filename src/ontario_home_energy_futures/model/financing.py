"""Solar purchase-cost and financing model.

See METHODOLOGY.md section 6. Group-purchase discounts apply only to
eligible quote components; financing uses standard amortization.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuoteComponents:
    """A solar quote broken into its cost components, before tax."""

    panels: float = 0.0
    inverter: float = 0.0
    racking: float = 0.0
    electrical_equipment: float = 0.0
    labour: float = 0.0
    design_and_engineering: float = 0.0
    permitting: float = 0.0
    utility_connection: float = 0.0
    installer_overhead: float = 0.0
    battery: float = 0.0
    other: float = 0.0

    ELIGIBLE_FIELDS = (
        "panels",
        "inverter",
        "racking",
        "electrical_equipment",
        "labour",
        "installer_overhead",
    )
    INELIGIBLE_FIELDS = (
        "design_and_engineering",
        "permitting",
        "utility_connection",
        "battery",
        "other",
    )

    def total(self) -> float:
        return sum(getattr(self, f) for f in self.ELIGIBLE_FIELDS + self.INELIGIBLE_FIELDS)

    def eligible_total(self) -> float:
        return sum(getattr(self, f) for f in self.ELIGIBLE_FIELDS)

    def ineligible_total(self) -> float:
        return sum(getattr(self, f) for f in self.INELIGIBLE_FIELDS)


def quote_from_total(total_before_tax: float, cost_component_shares: dict[str, float]) -> QuoteComponents:
    """Build a ``QuoteComponents`` by splitting a single total using the
    documented default proportional shares (used only when the user has not
    entered a full breakdown).

    ``cost_component_shares`` may come directly from
    ``assumptions/solar.yaml``'s ``cost_components`` block, which includes a
    non-numeric ``status`` metadata key alongside the share fractions; any
    key not recognized as a ``QuoteComponents`` field is ignored.
    """
    known_fields = QuoteComponents.ELIGIBLE_FIELDS + QuoteComponents.INELIGIBLE_FIELDS
    values = {
        field: total_before_tax * share
        for field, share in cost_component_shares.items()
        if field in known_fields
    }
    return QuoteComponents(**values)


@dataclass(frozen=True)
class DiscountResult:
    discount_fraction: float
    eligible_total_before_discount: float
    eligible_total_after_discount: float
    discount_amount: float
    ineligible_total: float
    total_after_discount: float


def apply_group_discount(quote: QuoteComponents, discount_fraction: float) -> DiscountResult:
    """Apply a group-purchase discount to only the eligible components of a
    quote. Government fees, taxes, and financing are never discounted.
    """
    if not (0.0 <= discount_fraction < 1.0):
        raise ValueError(f"discount_fraction must be in [0, 1), got {discount_fraction}")

    eligible_before = quote.eligible_total()
    eligible_after = eligible_before * (1.0 - discount_fraction)
    discount_amount = eligible_before - eligible_after
    ineligible = quote.ineligible_total()

    return DiscountResult(
        discount_fraction=discount_fraction,
        eligible_total_before_discount=round(eligible_before, 2),
        eligible_total_after_discount=round(eligible_after, 2),
        discount_amount=round(discount_amount, 2),
        ineligible_total=round(ineligible, 2),
        total_after_discount=round(eligible_after + ineligible, 2),
    )


@dataclass(frozen=True)
class LoanSchedule:
    principal: float
    annual_interest_rate: float
    term_years: int
    monthly_payment: float
    total_interest: float
    total_paid: float
    balance_by_year: dict[int, float]


def amortize_loan(*, principal: float, annual_interest_rate: float, term_years: int) -> LoanSchedule:
    """Standard fixed-rate monthly amortization."""
    if principal < 0:
        raise ValueError("principal must be non-negative")
    if term_years <= 0:
        raise ValueError("term_years must be positive")

    n_payments = term_years * 12
    monthly_rate = annual_interest_rate / 12.0

    if principal == 0:
        return LoanSchedule(
            principal=0.0,
            annual_interest_rate=annual_interest_rate,
            term_years=term_years,
            monthly_payment=0.0,
            total_interest=0.0,
            total_paid=0.0,
            balance_by_year={y: 0.0 for y in range(term_years + 1)},
        )

    if monthly_rate == 0:
        monthly_payment = principal / n_payments
    else:
        monthly_payment = (
            principal * monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)

    balance = principal
    balance_by_year = {0: round(balance, 2)}
    total_interest = 0.0

    for month in range(1, n_payments + 1):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        balance = max(0.0, balance - principal_payment)
        total_interest += interest_payment
        if month % 12 == 0:
            balance_by_year[month // 12] = round(balance, 2)

    total_paid = principal + total_interest

    return LoanSchedule(
        principal=round(principal, 2),
        annual_interest_rate=annual_interest_rate,
        term_years=term_years,
        monthly_payment=round(monthly_payment, 2),
        total_interest=round(total_interest, 2),
        total_paid=round(total_paid, 2),
        balance_by_year=balance_by_year,
    )


def interest_avoided_by_discount(
    *,
    quote_before_discount: QuoteComponents,
    discount: DiscountResult,
    down_payment_fraction: float,
    annual_interest_rate: float,
    term_years: int,
    tax_rate: float,
) -> float:
    """Total interest avoided by financing a smaller, discounted principal
    versus the full undiscounted principal, holding down-payment fraction,
    rate, and term fixed. Reported separately from the discount's direct
    price reduction (METHODOLOGY.md section 6).
    """
    full_total = quote_before_discount.total() * (1 + tax_rate)
    discounted_total = discount.total_after_discount * (1 + tax_rate)

    full_principal = full_total * (1 - down_payment_fraction)
    discounted_principal = discounted_total * (1 - down_payment_fraction)

    full_schedule = amortize_loan(
        principal=full_principal, annual_interest_rate=annual_interest_rate, term_years=term_years
    )
    discounted_schedule = amortize_loan(
        principal=discounted_principal, annual_interest_rate=annual_interest_rate, term_years=term_years
    )

    return round(full_schedule.total_interest - discounted_schedule.total_interest, 2)
