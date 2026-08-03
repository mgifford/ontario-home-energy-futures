import pytest

from ontario_home_energy_futures.model.financing import (
    QuoteComponents,
    amortize_loan,
    apply_group_discount,
    interest_avoided_by_discount,
    quote_from_total,
)

SHARES = {
    "panels": 0.32, "inverter": 0.10, "racking": 0.08, "electrical_equipment": 0.06,
    "labour": 0.20, "design_and_engineering": 0.03, "permitting": 0.02,
    "utility_connection": 0.04, "installer_overhead": 0.15,
}


def test_quote_from_total_sums_back_to_total():
    quote = quote_from_total(21000, SHARES)
    assert quote.total() == pytest.approx(21000, abs=0.01)


def test_zero_discount_leaves_total_unchanged():
    quote = quote_from_total(21000, SHARES)
    result = apply_group_discount(quote, 0.0)
    assert result.total_after_discount == pytest.approx(quote.total(), abs=0.01)


def test_five_percent_discount_reduces_only_eligible_components():
    quote = quote_from_total(21000, SHARES)
    result = apply_group_discount(quote, 0.05)
    assert result.discount_amount == pytest.approx(quote.eligible_total() * 0.05, abs=0.01)
    assert result.ineligible_total == pytest.approx(quote.ineligible_total(), abs=0.01)


def test_ten_percent_discount_larger_than_five():
    quote = quote_from_total(21000, SHARES)
    five = apply_group_discount(quote, 0.05)
    ten = apply_group_discount(quote, 0.10)
    assert ten.discount_amount > five.discount_amount


def test_discount_never_touches_permitting_or_connection():
    quote = QuoteComponents(panels=5000, permitting=500, utility_connection=800)
    result = apply_group_discount(quote, 0.10)
    assert result.ineligible_total == pytest.approx(1300, abs=0.01)


def test_invalid_discount_rejected():
    quote = quote_from_total(21000, SHARES)
    with pytest.raises(ValueError):
        apply_group_discount(quote, 1.5)


def test_amortize_loan_zero_principal():
    schedule = amortize_loan(principal=0, annual_interest_rate=0.079, term_years=10)
    assert schedule.monthly_payment == 0
    assert schedule.total_interest == 0


def test_amortize_loan_pays_off_principal():
    schedule = amortize_loan(principal=18000, annual_interest_rate=0.079, term_years=10)
    assert schedule.balance_by_year[10] == 0
    assert schedule.total_interest > 0
    assert schedule.monthly_payment > 0


def test_higher_rate_means_more_interest():
    low = amortize_loan(principal=18000, annual_interest_rate=0.03, term_years=10)
    high = amortize_loan(principal=18000, annual_interest_rate=0.10, term_years=10)
    assert high.total_interest > low.total_interest


def test_zero_rate_loan_has_no_interest():
    schedule = amortize_loan(principal=12000, annual_interest_rate=0.0, term_years=5)
    assert schedule.total_interest == pytest.approx(0, abs=0.01)
    assert schedule.monthly_payment == pytest.approx(12000 / 60, abs=0.01)


def test_interest_avoided_by_discount_is_positive():
    quote = quote_from_total(21000, SHARES)
    discount = apply_group_discount(quote, 0.10)
    avoided = interest_avoided_by_discount(
        quote_before_discount=quote, discount=discount, down_payment_fraction=0.10,
        annual_interest_rate=0.079, term_years=10, tax_rate=0.13,
    )
    assert avoided > 0


def test_loan_extends_beyond_horizon_detectable_via_balance_by_year():
    schedule = amortize_loan(principal=18000, annual_interest_rate=0.079, term_years=15)
    # A 10-year planning horizon would see a non-zero balance at year 10.
    assert schedule.balance_by_year[10] > 0
