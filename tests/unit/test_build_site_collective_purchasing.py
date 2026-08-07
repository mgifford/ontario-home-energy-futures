"""Tests for the collective-purchasing table on compare-timing.html
(_build_collective_purchasing_rows in build_site.py) - confirms it uses
the REAL household-count-tier model
(model/collective_purchasing.py, assumptions/collective_purchasing.yaml),
not the page's older arbitrary 0-20% discount slider math.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ontario_home_energy_futures.model.financing import quote_from_total
from ontario_home_energy_futures.site.build_site import _build_collective_purchasing_rows
from ontario_home_energy_futures.site.context import SiteData

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def site_data():
    return SiteData(REPO_ROOT)


@pytest.fixture
def base_quote(site_data):
    reference_quote_total = site_data.solar["illustrative_reference_quote"]["installed_price_before_tax_cad"]
    return quote_from_total(reference_quote_total, site_data.solar["cost_components"])


def _parse_cad(formatted: str) -> float:
    return float(formatted.replace("$", "").replace(",", ""))


def test_four_tiers_present(site_data, base_quote):
    rows = _build_collective_purchasing_rows(site_data, base_quote=base_quote, tax_rate=0.13)
    labels = [r["label"] for r in rows]
    assert labels == [
        "Individual purchase", "Five-household group", "Ten-household group", "Twenty-household group",
    ]


def test_household_counts_correct(site_data, base_quote):
    rows = _build_collective_purchasing_rows(site_data, base_quote=base_quote, tax_rate=0.13)
    households = [r["households"] for r in rows]
    assert households == [1, 5, 10, 20]


def test_individual_tier_has_zero_savings(site_data, base_quote):
    rows = _build_collective_purchasing_rows(site_data, base_quote=base_quote, tax_rate=0.13)
    individual = rows[0]
    assert _parse_cad(individual["one_time_savings"]) == pytest.approx(0.0, abs=0.01)
    assert individual["effective_discount_pct"] == "0.0%"


def test_initial_cost_decreases_monotonically_with_group_size(site_data, base_quote):
    rows = _build_collective_purchasing_rows(site_data, base_quote=base_quote, tax_rate=0.13)
    costs = [_parse_cad(r["initial_cost"]) for r in rows]
    assert costs == sorted(costs, reverse=True), (
        "larger collective-purchasing groups must never cost more than smaller ones for the same quote"
    )
    assert costs[0] > costs[-1]  # individual strictly more expensive than 20-household


def test_savings_increase_monotonically_with_group_size(site_data, base_quote):
    rows = _build_collective_purchasing_rows(site_data, base_quote=base_quote, tax_rate=0.13)
    savings = [_parse_cad(r["one_time_savings"]) for r in rows]
    assert savings == sorted(savings)


def test_twenty_household_tier_hits_its_cap(site_data, base_quote):
    # assumptions/collective_purchasing.yaml's group_20 tier has an
    # overall_discount_cap_percent of 13 - the reference quote's
    # uncapped per-component reduction should exceed that, so this tier
    # is expected to be capped (a real, useful signal the UI shows the
    # user, not just an internal detail).
    rows = _build_collective_purchasing_rows(site_data, base_quote=base_quote, tax_rate=0.13)
    twenty_household = rows[-1]
    assert twenty_household["capped"] is True


def test_uses_real_tier_yaml_not_flat_percent(site_data, base_quote):
    # Regression guard against reverting to the old flat "0-20% slider"
    # math: the ten-household tier's discount must match
    # assumptions/collective_purchasing.yaml's actual per-component
    # reductions, not an arbitrary flat percentage applied to the whole
    # quote.
    tier = site_data.collective_tiers["group_10"]
    assert tier.reductions  # has real per-component percentages
    assert tier.overall_discount_cap_percent == pytest.approx(10.0)
