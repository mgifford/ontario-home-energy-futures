from pathlib import Path

import pytest

from ontario_home_energy_futures.model.compatibility import CompatibilityMatrix, Relationship

REPO_ROOT = Path(__file__).parent.parent.parent
COMPATIBILITY_FILE = REPO_ROOT / "assumptions" / "value_stream_compatibility.yaml"


@pytest.fixture(scope="module")
def matrix():
    return CompatibilityMatrix.from_yaml(COMPATIBILITY_FILE)


def test_self_consumption_and_net_metering_are_prohibited(matrix):
    decision = matrix.decide("avoided-retail-purchase", "ontario-net-metering-credit")
    assert decision.can_stack is False
    assert decision.relationship == Relationship.PROHIBITED
    assert decision.reason


def test_net_metering_and_dynamic_export_are_prohibited(matrix):
    decision = matrix.decide("ontario-net-metering-credit", "dynamic-export-compensation")
    assert decision.can_stack is False
    assert decision.relationship == Relationship.PROHIBITED


def test_vpp_availability_and_event_payment_can_coexist(matrix):
    decision = matrix.decide("vpp-availability-payment", "vpp-event-payment")
    assert decision.can_stack is True
    assert decision.relationship == Relationship.ALLOWED


def test_capacity_and_local_flexibility_can_coexist(matrix):
    decision = matrix.decide("capacity-market-revenue", "local-flexibility-payment")
    assert decision.can_stack is True


def test_unknown_pair_defaults_to_excluded(matrix):
    decision = matrix.decide("capacity-market-revenue", "vpp-event-payment")
    assert decision.can_stack is False
    assert decision.relationship == Relationship.UNKNOWN
    assert "excluded" in decision.reason or "not" in decision.reason.lower()


def test_unrecorded_pair_defaults_to_excluded_not_silently_allowed(matrix):
    # A pair never mentioned in the YAML at all - the dangerous case where a
    # missing entry must NOT silently permit stacking.
    decision = matrix.decide("household-efficiency-savings", "vpp-event-payment")
    assert decision.can_stack is False
    assert decision.relationship == Relationship.UNKNOWN


def test_stream_is_always_compatible_with_itself(matrix):
    decision = matrix.decide("vpp-event-payment", "vpp-event-payment")
    assert decision.can_stack is True


def test_relationship_is_symmetric(matrix):
    a_b = matrix.decide("avoided-retail-purchase", "ontario-net-metering-credit")
    b_a = matrix.decide("ontario-net-metering-credit", "avoided-retail-purchase")
    assert a_b.can_stack == b_a.can_stack
    assert a_b.relationship == b_a.relationship


def test_filter_stackable_excludes_prohibited_pair(matrix):
    kept, excluded = matrix.filter_stackable(["avoided-retail-purchase", "ontario-net-metering-credit"])
    assert kept == ["avoided-retail-purchase"]
    assert len(excluded) == 1
    assert excluded[0][0] == "ontario-net-metering-credit"


def test_filter_stackable_keeps_all_when_all_allowed(matrix):
    kept, excluded = matrix.filter_stackable(["vpp-availability-payment", "vpp-event-payment"])
    assert set(kept) == {"vpp-availability-payment", "vpp-event-payment"}
    assert excluded == []


def test_filter_stackable_excludes_unknown_pairs_with_reason(matrix):
    kept, excluded = matrix.filter_stackable(["capacity-market-revenue", "vpp-event-payment"])
    assert kept == ["capacity-market-revenue"]
    assert len(excluded) == 1
    assert excluded[0][2]  # non-empty explanation


def test_structural_rules_documented_for_reserve_and_ev_away(matrix):
    import yaml

    raw = yaml.safe_load(COMPATIBILITY_FILE.read_text(encoding="utf-8"))
    rule_ids = {r["id"] for r in raw["structural_rules"]}
    assert "reserve-not-dispatchable" in rule_ids
    assert "ev-away-not-dispatchable" in rule_ids
    assert "driving-energy-priority" in rule_ids
    assert "group-purchase-discount-is-one-time" in rule_ids
