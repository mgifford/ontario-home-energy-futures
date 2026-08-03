"""Value-stream compatibility matrix: the single place double-counting
rules are enforced.

See ``assumptions/value_stream_compatibility.yaml`` and METHODOLOGY.md
section 16. Any code that wants to sum revenue from two value streams for
the same underlying kWh/kW/period must call ``CompatibilityMatrix.can_stack``
first; an ``unknown`` relationship defaults to excluded, matching the
project brief's "where compatibility is unknown, exclude the combination
from default results and explain why."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml


class Relationship(str, Enum):
    ALLOWED = "allowed"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CompatibilityDecision:
    can_stack: bool
    relationship: Relationship
    reason: str


class CompatibilityMatrix:
    """Pairwise lookup of whether two value streams may both contribute
    revenue for the same kWh/kW/period.
    """

    def __init__(self, pairs: dict[frozenset[str], tuple[Relationship, str]]) -> None:
        self._pairs = pairs

    @classmethod
    def from_yaml(cls, path: Path) -> "CompatibilityMatrix":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        pairs: dict[frozenset[str], tuple[Relationship, str]] = {}
        for entry in raw.get("pairs", []):
            key = frozenset({entry["stream_a"], entry["stream_b"]})
            pairs[key] = (Relationship(entry["relationship"]), entry.get("reason", ""))
        return cls(pairs)

    def decide(self, stream_id_a: str, stream_id_b: str) -> CompatibilityDecision:
        """Return whether ``stream_id_a`` and ``stream_id_b`` may both
        contribute revenue for the same underlying kWh/kW/period.

        A stream is always compatible with itself under this lookup (the
        matrix only governs distinct-pair stacking); callers computing
        revenue for a single stream across multiple periods do not need to
        consult this method.

        An unrecorded pair (not present in the YAML at all) is treated the
        same as an explicit ``unknown`` entry: excluded by default, with a
        generated reason, so a missing YAML entry can never silently permit
        stacking.
        """
        if stream_id_a == stream_id_b:
            return CompatibilityDecision(True, Relationship.ALLOWED, "same stream")

        key = frozenset({stream_id_a, stream_id_b})
        if key not in self._pairs:
            return CompatibilityDecision(
                False,
                Relationship.UNKNOWN,
                f"no compatibility rule recorded for {stream_id_a!r} + {stream_id_b!r}; "
                "excluded from default results until verified",
            )

        relationship, reason = self._pairs[key]
        can_stack = relationship == Relationship.ALLOWED
        return CompatibilityDecision(can_stack, relationship, reason)

    def filter_stackable(self, stream_ids: list[str]) -> tuple[list[str], list[tuple[str, str, str]]]:
        """Given a list of value-stream ids a scenario wants to include
        simultaneously, return ``(kept_ids, excluded_pairs)`` where
        ``excluded_pairs`` lists ``(id_a, id_b, reason)`` for every pair
        found incompatible. Streams are kept unless they conflict with an
        already-kept stream, processed in input order - this is a
        deterministic, explainable reduction, not a search for the
        maximum stackable subset.
        """
        kept: list[str] = []
        excluded: list[tuple[str, str, str]] = []
        for candidate in stream_ids:
            conflict = None
            for already_kept in kept:
                decision = self.decide(candidate, already_kept)
                if not decision.can_stack:
                    conflict = (already_kept, decision.reason)
                    break
            if conflict is None:
                kept.append(candidate)
            else:
                excluded.append((candidate, conflict[0], conflict[1]))
        return kept, excluded
