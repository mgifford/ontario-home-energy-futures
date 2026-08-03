"""Scenario C: group discount (same as Scenario B, 10% discount on eligible
installation components, 15-year financing).

Expected:
- Principal falls.
- Total interest falls.
- Ineligible fees are not discounted.
- The application reports immediate savings and avoided interest separately.
"""

from ontario_home_energy_futures.model.financing import (
    QuoteComponents,
    amortize_loan,
    apply_group_discount,
    interest_avoided_by_discount,
)

QUOTE = QuoteComponents(
    panels=6720, inverter=2100, racking=1680, electrical_equipment=1260,
    labour=4200, design_and_engineering=630, permitting=420,
    utility_connection=840, installer_overhead=3150,
)
TAX_RATE = 0.13
DOWN_PAYMENT_FRACTION = 0.10
RATE = 0.079
TERM_YEARS = 15


def test_principal_falls_with_discount():
    no_discount = apply_group_discount(QUOTE, 0.0)
    with_discount = apply_group_discount(QUOTE, 0.10)

    full_total = no_discount.total_after_discount * (1 + TAX_RATE)
    discounted_total = with_discount.total_after_discount * (1 + TAX_RATE)

    full_principal = full_total * (1 - DOWN_PAYMENT_FRACTION)
    discounted_principal = discounted_total * (1 - DOWN_PAYMENT_FRACTION)

    assert discounted_principal < full_principal


def test_total_interest_falls_with_discount():
    no_discount = apply_group_discount(QUOTE, 0.0)
    with_discount = apply_group_discount(QUOTE, 0.10)

    full_total = no_discount.total_after_discount * (1 + TAX_RATE)
    discounted_total = with_discount.total_after_discount * (1 + TAX_RATE)

    full_schedule = amortize_loan(
        principal=full_total * (1 - DOWN_PAYMENT_FRACTION), annual_interest_rate=RATE, term_years=TERM_YEARS
    )
    discounted_schedule = amortize_loan(
        principal=discounted_total * (1 - DOWN_PAYMENT_FRACTION), annual_interest_rate=RATE, term_years=TERM_YEARS
    )

    assert discounted_schedule.total_interest < full_schedule.total_interest


def test_ineligible_fees_not_discounted():
    result = apply_group_discount(QUOTE, 0.10)
    expected_ineligible = QUOTE.design_and_engineering + QUOTE.permitting + QUOTE.utility_connection
    assert result.ineligible_total == round(expected_ineligible, 2)


def test_immediate_savings_and_avoided_interest_reported_separately():
    discount = apply_group_discount(QUOTE, 0.10)
    avoided_interest = interest_avoided_by_discount(
        quote_before_discount=QUOTE, discount=discount, down_payment_fraction=DOWN_PAYMENT_FRACTION,
        annual_interest_rate=RATE, term_years=TERM_YEARS, tax_rate=TAX_RATE,
    )
    # These are two distinct, separately reported numbers - not the same
    # figure or a multiple that would suggest they were conflated.
    assert discount.discount_amount > 0
    assert avoided_interest > 0
    assert discount.discount_amount != avoided_interest
