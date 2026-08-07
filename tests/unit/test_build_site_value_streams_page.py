"""Tests for the value-streams.html page context builder
(_build_value_streams_context in build_site.py) - confirms the project's
own governance commitment (only `current`-status value streams appear as
"currently available"; speculative streams are visibly separated, never
silently included) is actually true in the rendered page context, not
just documented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ontario_home_energy_futures.model.value_streams import ValueStreamStatus
from ontario_home_energy_futures.site.build_site import _build_value_streams_context
from ontario_home_energy_futures.site.context import SiteData

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(scope="module")
def site_data():
    return SiteData(REPO_ROOT)


def test_all_sixteen_streams_accounted_for(site_data):
    ctx = _build_value_streams_context(site_data)
    assert ctx["total_stream_count"] == 16
    assert len(ctx["current_value_stream_rows"]) + len(ctx["not_available_value_stream_rows"]) <= 16


def test_current_stream_count_matches_current_rows(site_data):
    ctx = _build_value_streams_context(site_data)
    assert ctx["current_stream_count"] == len(ctx["current_value_stream_rows"])
    assert ctx["current_stream_count"] == 8


def test_no_unsupported_stream_appears_in_either_group(site_data):
    ctx = _build_value_streams_context(site_data)
    all_stream_ids = {s.id for s in site_data.value_streams.values() if s.status == ValueStreamStatus.UNSUPPORTED}
    assert all_stream_ids == set()  # sanity: no unsupported streams exist in the fixture set today

    rendered_ids = {r["id"] for r in ctx["current_value_stream_rows"]} | {
        r["id"] for r in ctx["not_available_value_stream_rows"]
    }
    unsupported_ids = {
        s.id for s in site_data.value_streams.values() if s.status == ValueStreamStatus.UNSUPPORTED
    }
    assert not (rendered_ids & unsupported_ids)


def test_current_group_never_contains_speculative_status(site_data):
    ctx = _build_value_streams_context(site_data)
    speculative_statuses = {
        ValueStreamStatus.PILOT, ValueStreamStatus.PROPOSED,
        ValueStreamStatus.DEMONSTRATED_ELSEWHERE, ValueStreamStatus.ILLUSTRATIVE_SCENARIO,
        ValueStreamStatus.CLOSED,
    }
    by_id = site_data.value_streams
    for row in ctx["current_value_stream_rows"]:
        assert by_id[row["id"]].status not in speculative_statuses


def test_not_available_group_never_contains_current_status(site_data):
    ctx = _build_value_streams_context(site_data)
    by_id = site_data.value_streams
    for row in ctx["not_available_value_stream_rows"]:
        assert by_id[row["id"]].status != ValueStreamStatus.CURRENT


def test_every_row_has_a_source_title_never_blank(site_data):
    ctx = _build_value_streams_context(site_data)
    for row in ctx["current_value_stream_rows"] + ctx["not_available_value_stream_rows"]:
        assert row["source_title"]
        assert row["source_title"] != "See notes"  # the old, uninformative fallback
