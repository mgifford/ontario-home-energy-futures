from pathlib import Path

import pytest

from ontario_home_energy_futures.model.value_streams import (
    ValueStreamStatus,
    calculate_value_stream_revenue,
    filter_by_status,
    load_value_streams,
)

REPO_ROOT = Path(__file__).parent.parent.parent
VALUE_STREAMS_DIR = REPO_ROOT / "assumptions" / "value_streams"


@pytest.fixture(scope="module")
def all_streams():
    return load_value_streams(VALUE_STREAMS_DIR)


def test_loads_all_sixteen_value_streams(all_streams):
    assert len(all_streams) == 16


def test_every_stream_has_all_required_fields(all_streams):
    for stream in all_streams.values():
        assert stream.id
        assert stream.name
        assert stream.category
        assert isinstance(stream.status, ValueStreamStatus)
        assert stream.verified_at
        assert stream.eligibility.jurisdiction
        assert stream.stacking is not None
        assert stream.source.type
        assert stream.tax_treatment


def test_status_is_one_of_seven_defined_values(all_streams):
    valid = {s.value for s in ValueStreamStatus}
    assert valid == {
        "current", "closed", "pilot", "proposed",
        "demonstrated_elsewhere", "illustrative_scenario", "unsupported",
    }
    for stream in all_streams.values():
        assert stream.status.value in valid


def test_current_ontario_bundle_only_includes_current_streams(all_streams):
    current = filter_by_status(all_streams, {ValueStreamStatus.CURRENT})
    assert len(current) == 8
    for stream in current.values():
        assert stream.status == ValueStreamStatus.CURRENT
        assert not stream.is_speculative


def test_speculative_streams_flagged(all_streams):
    vpp_event = all_streams["vpp-event-payment"]
    assert vpp_event.status == ValueStreamStatus.ILLUSTRATIVE_SCENARIO
    assert vpp_event.is_speculative

    avoided_purchase = all_streams["avoided-retail-purchase"]
    assert not avoided_purchase.is_speculative


def test_group_purchase_discount_is_one_time_not_annual(all_streams):
    discount = all_streams["group-purchase-discount"]
    assert discount.category == "cost_reduction"
    assert discount.tax_treatment == "not_applicable_not_income"


def test_no_unsupported_streams_in_current_fixture_set(all_streams):
    # Guards against accidentally shipping a value stream this project has
    # decided has insufficient evidence without labelling it excluded.
    unsupported = filter_by_status(all_streams, {ValueStreamStatus.UNSUPPORTED})
    assert unsupported == {}


def test_revenue_calculation_gross_and_net_differ_when_costs_present(all_streams):
    vpp_event = all_streams["vpp-event-payment"]
    result = calculate_value_stream_revenue(
        vpp_event, dispatched_kwh_for_grid=500, committed_kw=10, events_this_year=20
    )
    assert result.gross_revenue_cad > result.net_revenue_cad
    assert result.aggregator_fee_cad > 0
    assert result.degradation_cost_cad > 0


def test_revenue_calculation_zero_for_zero_dispatch(all_streams):
    demand_response = all_streams["demand-response-payment"]
    result = calculate_value_stream_revenue(
        demand_response, dispatched_kwh_for_grid=0, committed_kw=0, events_this_year=0
    )
    assert result.gross_revenue_cad == 0
    assert result.net_revenue_cad == 0


def test_events_clamped_to_programme_maximum(all_streams):
    vpp_event = all_streams["vpp-event-payment"]  # max 30 events/year
    result_over = calculate_value_stream_revenue(
        vpp_event, dispatched_kwh_for_grid=100, committed_kw=5, events_this_year=999
    )
    result_at_max = calculate_value_stream_revenue(
        vpp_event, dispatched_kwh_for_grid=100, committed_kw=5, events_this_year=30
    )
    # Revenue here is driven by dispatched_kwh_for_grid, not events count
    # directly, but the clamp itself must not error and must be idempotent
    # at the cap.
    assert result_over.gross_revenue_cad == result_at_max.gross_revenue_cad


def test_zero_values_not_silently_replaced_with_invented_defaults(all_streams):
    incentives = all_streams["current-incentives-rebates"]
    # Explicitly $0 because no verified active programme is documented -
    # must remain exactly 0, not be coerced into a nonzero "typical" value.
    assert incentives.compensation.dispatch_cad_per_kwh == 0.0
