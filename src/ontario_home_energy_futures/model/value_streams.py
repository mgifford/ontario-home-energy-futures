"""Normalized household energy value-stream model.

See METHODOLOGY.md section 15 and the value-stream YAML files under
``assumptions/value_streams/``. Every financial benefit a household can
receive is represented as one ``ValueStream`` record with a machine-readable
availability status, eligibility, compensation, and cost structure -
computed generically by ``calculate_value_stream_revenue`` rather than by
bespoke Python per programme, so adding a new programme means adding YAML,
not code.

This module intentionally does not decide which streams may be combined in
the same period - see ``compatibility.py`` for that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class ValueStreamStatus(str, Enum):
    """Availability/evidence status for a value stream. Exactly the seven
    values required by the project brief.
    """

    CURRENT = "current"
    CLOSED = "closed"
    PILOT = "pilot"
    PROPOSED = "proposed"
    DEMONSTRATED_ELSEWHERE = "demonstrated_elsewhere"
    ILLUSTRATIVE_SCENARIO = "illustrative_scenario"
    UNSUPPORTED = "unsupported"


# Statuses that may appear in a default, unlabelled savings total without
# the interface needing to attach a "hypothetical" warning. Everything else
# must be visually/textually separated from guaranteed/current value.
GUARANTEED_OR_CURRENT_STATUSES = frozenset({ValueStreamStatus.CURRENT})


@dataclass(frozen=True)
class ValueStreamEligibility:
    jurisdiction: str
    residential: bool
    aggregator_required: bool
    solar_required: bool
    battery_required: bool
    bidirectional_ev_allowed: bool
    minimum_export_kw: float | None
    minimum_usable_kwh: float | None


@dataclass(frozen=True)
class ValueStreamCompensation:
    enrollment_cad: float
    availability_cad_per_kw_month: float
    dispatch_cad_per_kwh: float | None
    annual_bonus_cad: float


@dataclass(frozen=True)
class ValueStreamCosts:
    aggregator_share_percent: float
    annual_fee_cad: float
    estimated_degradation_cad_per_kwh: float


@dataclass(frozen=True)
class ValueStreamEvents:
    expected_events_per_year: int
    maximum_events_per_year: int
    event_duration_hours: float
    minimum_notice_minutes: int


@dataclass(frozen=True)
class ValueStreamCustomerConstraints:
    minimum_backup_reserve_percent: float
    maximum_cycles_per_day: float
    opt_out_events_per_year: int | None


@dataclass(frozen=True)
class ValueStreamStacking:
    net_metering: str
    dynamic_export: str
    capacity_payment: str
    local_flexibility: str
    notes: str = ""


@dataclass(frozen=True)
class ValueStreamSource:
    type: str
    url: str | None
    title: str | None
    notes: str = ""


@dataclass(frozen=True)
class ValueStream:
    id: str
    name: str
    category: str
    status: ValueStreamStatus
    verified_at: str
    accepting_new_participants: bool
    eligibility: ValueStreamEligibility
    compensation: ValueStreamCompensation
    costs: ValueStreamCosts
    events: ValueStreamEvents | None
    customer_constraints: ValueStreamCustomerConstraints | None
    stacking: ValueStreamStacking
    source: ValueStreamSource
    tax_treatment: str
    combinable_with_other_streams: bool

    @property
    def is_speculative(self) -> bool:
        return self.status not in GUARANTEED_OR_CURRENT_STATUSES


def _load_one(path: Path) -> ValueStream:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    status_raw = raw["status"]
    eligibility_raw = raw["eligibility"]
    compensation_raw = raw["compensation"]
    costs_raw = raw["costs"]
    events_raw = raw.get("events")
    constraints_raw = raw.get("customer_constraints")
    stacking_raw = raw["stacking"]
    source_raw = raw["source"]

    return ValueStream(
        id=raw["id"],
        name=raw["name"],
        category=raw["category"],
        status=ValueStreamStatus(status_raw["type"]),
        verified_at=str(status_raw["verified_at"]),
        accepting_new_participants=bool(status_raw["accepting_new_participants"]),
        eligibility=ValueStreamEligibility(
            jurisdiction=eligibility_raw["jurisdiction"],
            residential=bool(eligibility_raw["residential"]),
            aggregator_required=bool(eligibility_raw["aggregator_required"]),
            solar_required=bool(eligibility_raw["solar_required"]),
            battery_required=bool(eligibility_raw["battery_required"]),
            bidirectional_ev_allowed=bool(eligibility_raw["bidirectional_ev_allowed"]),
            minimum_export_kw=eligibility_raw.get("minimum_export_kw"),
            minimum_usable_kwh=eligibility_raw.get("minimum_usable_kwh"),
        ),
        compensation=ValueStreamCompensation(
            enrollment_cad=float(compensation_raw["enrollment_cad"]),
            availability_cad_per_kw_month=float(compensation_raw["availability_cad_per_kw_month"]),
            dispatch_cad_per_kwh=(
                None if compensation_raw["dispatch_cad_per_kwh"] is None
                else float(compensation_raw["dispatch_cad_per_kwh"])
            ),
            annual_bonus_cad=float(compensation_raw["annual_bonus_cad"]),
        ),
        costs=ValueStreamCosts(
            aggregator_share_percent=float(costs_raw["aggregator_share_percent"]),
            annual_fee_cad=float(costs_raw["annual_fee_cad"]),
            estimated_degradation_cad_per_kwh=float(costs_raw["estimated_degradation_cad_per_kwh"]),
        ),
        events=(
            None if events_raw is None else ValueStreamEvents(
                expected_events_per_year=int(events_raw["expected_events_per_year"]),
                maximum_events_per_year=int(events_raw["maximum_events_per_year"]),
                event_duration_hours=float(events_raw["event_duration_hours"]),
                minimum_notice_minutes=int(events_raw["minimum_notice_minutes"]),
            )
        ),
        customer_constraints=(
            None if constraints_raw is None else ValueStreamCustomerConstraints(
                minimum_backup_reserve_percent=float(constraints_raw["minimum_backup_reserve_percent"]),
                maximum_cycles_per_day=float(constraints_raw["maximum_cycles_per_day"]),
                opt_out_events_per_year=constraints_raw.get("opt_out_events_per_year"),
            )
        ),
        stacking=ValueStreamStacking(
            net_metering=stacking_raw["net_metering"],
            dynamic_export=stacking_raw["dynamic_export"],
            capacity_payment=stacking_raw["capacity_payment"],
            local_flexibility=stacking_raw["local_flexibility"],
            notes=stacking_raw.get("notes", ""),
        ),
        source=ValueStreamSource(
            type=source_raw["type"],
            url=source_raw.get("url"),
            title=source_raw.get("title"),
            notes=source_raw.get("notes", ""),
        ),
        tax_treatment=raw["tax_treatment"],
        combinable_with_other_streams=bool(raw["combinable_with_other_streams"]),
    )


def load_value_streams(value_streams_dir: Path) -> dict[str, ValueStream]:
    """Load every ``*.yaml`` file in ``value_streams_dir`` into a dict keyed
    by value-stream id.
    """
    streams: dict[str, ValueStream] = {}
    for path in sorted(value_streams_dir.glob("*.yaml")):
        stream = _load_one(path)
        streams[stream.id] = stream
    return streams


def filter_by_status(
    streams: dict[str, ValueStream], allowed_statuses: set[ValueStreamStatus]
) -> dict[str, ValueStream]:
    """Return only the streams whose status is in ``allowed_statuses``.
    ``ValueStreamStatus.UNSUPPORTED`` should never be included in
    ``allowed_statuses`` for any bundle - callers building a default bundle
    should pass ``{ValueStreamStatus.CURRENT}``.
    """
    return {sid: s for sid, s in streams.items() if s.status in allowed_statuses}


@dataclass(frozen=True)
class ValueStreamRevenueResult:
    stream_id: str
    gross_revenue_cad: float
    aggregator_fee_cad: float
    annual_fee_cad: float
    degradation_cost_cad: float
    net_revenue_cad: float


def calculate_value_stream_revenue(
    stream: ValueStream,
    *,
    dispatched_kwh_for_grid: float,
    committed_kw: float,
    events_this_year: int,
) -> ValueStreamRevenueResult:
    """Generic revenue calculation from a value stream's YAML-defined
    compensation/costs/events fields - the same function computes every
    programme's revenue, so a new programme never needs new Python.

    ``events_this_year`` is clamped to the stream's
    ``events.maximum_events_per_year`` if defined, so an unrealistic event
    count can never inflate revenue past the programme's own stated cap.
    """
    if stream.events is not None:
        events_this_year = min(events_this_year, stream.events.maximum_events_per_year)

    availability_revenue = stream.compensation.availability_cad_per_kw_month * committed_kw * 12
    dispatch_rate = stream.compensation.dispatch_cad_per_kwh or 0.0
    dispatch_revenue = dispatch_rate * dispatched_kwh_for_grid
    bonus = stream.compensation.annual_bonus_cad

    gross_revenue = availability_revenue + dispatch_revenue + bonus

    aggregator_fee = gross_revenue * (stream.costs.aggregator_share_percent / 100.0)
    annual_fee = stream.costs.annual_fee_cad
    degradation_cost = stream.costs.estimated_degradation_cad_per_kwh * dispatched_kwh_for_grid

    net_revenue = gross_revenue - aggregator_fee - annual_fee - degradation_cost

    return ValueStreamRevenueResult(
        stream_id=stream.id,
        gross_revenue_cad=round(gross_revenue, 2),
        aggregator_fee_cad=round(aggregator_fee, 2),
        annual_fee_cad=round(annual_fee, 2),
        degradation_cost_cad=round(degradation_cost, 2),
        net_revenue_cad=round(net_revenue, 2),
    )
